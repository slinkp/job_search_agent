"""
Leverage AI to find info about prospective company / role.
"""

import datetime
import json
import logging
import os
import re
from typing import Optional, Literal, cast

import requests
from bs4 import BeautifulSoup
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import BaseChatModel
from ai.client_factory import get_chat_client
from tavily import TavilyClient  # type: ignore[import-untyped]

from models import CompaniesSheetRow, is_placeholder

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

logger = logging.getLogger(__name__)


# Tavily API has undocumented input limit of 400 for get_search_context(query)
# HACK: We have to be very careful to keep prompts under this limit.
GET_SEARCH_CONTEXT_INPUT_LIMIT = 400

# PROMPT_LIMIT
BASIC_COMPANY_PROMPT = """
For the company {company_info.company_identifier}, find:
 - The correct company name, which may be different than the name we were provided via email, if any.
 - City and country of the company's headquarters.
 - Address of the company's NYC office, if there is one.
 - Total number of employees worldwide.
 - Number of employees who are engineers.
"""

BASIC_COMPANY_FORMAT_PROMPT = """
Return these results as a valid JSON object, with the following keys and data types:
 - company_name: string or null
 - headquarters_city: string or null
 - nyc_office_address: string or null
 - total_employees: integer or null
 - total_engineers: integer or null

The value of nyc_office_address, if known, must be returned as a valid US mailing address with a street address,
city, state, and zip code.
The value of headquarters_city must be the city, state/province, and country of the company's headquarters, if known.
"""
# - the URLs of the pages that contain the information above
# """

FUNDING_STATUS_PROMPT = """
For the company {company_info.company_identifier}, find:
 - The company's public/private status.  If there is a stock symbol, it's public.
   If private and valued at over $1B, call it a "unicorn".
 - The company's latest valuation, in millions of dollars, if known.
 - The most recent funding round (eg "Series A", "Series B", etc.) if private.
"""

FUNDING_STATUS_FORMAT_PROMPT = """
Return these results as a valid JSON object, with the following keys and data types:
 - public_status: string "public", "private", "private unicorn" or null
 - valuation: string or null
 - funding_series: string or null
 """

EMPLOYMENT_PROMPT = """
For the company {company_info.company_identifier}, find:
    - the company's remote work policy
    - whether the company is currently hiring backend engineers
    - whether the company is hiring backend engineers with AI experience
    - the URL of the company's primary jobs page, preferably on their own website, if known.
"""

EMPLOYMENT_FORMAT_PROMPT = """
Return these results as a valid JSON object, with the following keys and data types:
    - remote_work_policy: string "hybrid", "remote", "in-person", or null
    - hiring_status: boolean or null
    - hiring_status_ai: boolean or null
    - jobs_homepage_url: string or null
    - citation_urls: list of strings
"""

INTERVIEW_STYLE_PROMPT = """
For the company {company_info.company_identifier}, find:
    - whether engineers are expected to do a systems design interview
    - whether engineers are expected to do a leetcode style coding interview
"""

INTERVIEW_STYLE_FORMAT_PROMPT = """
Return these results as a valid JSON object, with the following keys and data types:
    - interview_style_systems: boolean or null
    - interview_style_leetcode: boolean or null
    - citation_urls: list of strings
"""

AI_MISSION_PROMPT = """
Is the company {company_info.company_identifier} a company that uses AI?
Look for blog posts, press releases, news articles, etc. about whether and how AI
is used for the company's products or services, whether as public-facing features or
internal implementation. Another good clue is whether the company is hiring AI engineers.
"""

AI_MISSION_FORMAT_PROMPT = """
Return the result as a valid JSON object with the following keys and data types:
  - uses_ai: boolean or null
  - ai_notes: string or null
  - citation_urls: list of strings

ai_notes should be a short summary (no more than 100 words)
of how AI is used by the company, or null if the company does not use AI.
"""

COMPANY_PROMPTS = [
    BASIC_COMPANY_PROMPT,
    EMPLOYMENT_PROMPT,
    FUNDING_STATUS_PROMPT,
    INTERVIEW_STYLE_PROMPT,
    AI_MISSION_PROMPT,
]

COMPANY_PROMPTS_WITH_FORMAT_PROMPT = [
    (BASIC_COMPANY_PROMPT, BASIC_COMPANY_FORMAT_PROMPT),
    (EMPLOYMENT_PROMPT, EMPLOYMENT_FORMAT_PROMPT),
    (FUNDING_STATUS_PROMPT, FUNDING_STATUS_FORMAT_PROMPT),
    (INTERVIEW_STYLE_PROMPT, INTERVIEW_STYLE_FORMAT_PROMPT),
    (AI_MISSION_PROMPT, AI_MISSION_FORMAT_PROMPT),
]

# Add new prompt for extracting company info from email
EXTRACT_COMPANY_PROMPT = """
From this recruiter message, extract:
 - The company name being recruited for
 - The company's website URL, if mentioned
 - The role/position being recruited for
 - The recruiter's name and contact info

----- Recruiter message follows -----
 {message}
----- End of recruiter message -----
"""

EXTRACT_COMPANY_FORMAT_PROMPT = """
Return these results as a valid JSON object, with the following keys and data types:
 - company_name: string or null
 - company_url: string or null
 - role: string or null
 - recruiter_name: string or null
 - recruiter_contact: string or null
"""

TEMPERATURE = 0.7
TIMEOUT = 120


class TavilyRAGResearchAgent:

    llm: BaseChatModel

    def __init__(self, verbose: bool = False, llm: Optional[BaseChatModel] = None):
        # set up the agent using centralized client factory (default to OpenAI gpt-4)
        self.llm = llm or get_chat_client(
            provider="openai",
            model="gpt-4",
            temperature=TEMPERATURE,
            timeout=TIMEOUT,
        )
        # Cache to reduce LLM calls.
        set_llm_cache(SQLiteCache(database_path=".langchain-cache.db"))
        self.verbose = verbose
        self.tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    def extract_json_from_response(self, content: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        content = content.strip()

        # Try to extract JSON from markdown code blocks
        if content.startswith("```json") and content.endswith("```"):
            # Extract content between ```json and ```
            json_content = content[7:-3].strip()
        elif content.startswith("```") and content.endswith("```"):
            # Handle generic code blocks
            lines = content.split("\n")
            if len(lines) >= 3:
                json_content = "\n".join(lines[1:-1])
            else:
                json_content = content[3:-3].strip()
        else:
            json_content = content

        return json.loads(json_content)

    def make_prompt(
        self, search_prompt: str, format_prompt: str, extra_context: str = "", **kwargs
    ):
        prompt = search_prompt.format(**kwargs)
        parts = [
            "You are a helpful research agent researching companies.",
            "You may use any context you have gathered in previous queries to answer the current question.",
            prompt,
        ]

        if extra_context:
            parts.append("Use this additional JSON context to answer the question:")
            parts.append(extra_context)

        parts.extend(
            [
                "You must always output a valid JSON object with exactly the keys specified.",
                "citation_urls should always be a list of strings of URLs that contain the information above.",
                "If any string json value other than a citation url is longer than 80 characters, write a shorter summary of the value",
                "unless otherwise clearly specified in the prompt.",
                "CRITICAL: Return ONLY raw JSON - do not wrap it in markdown code blocks or any other formatting.",
                "Do not use ```json or ``` markers. Output the JSON object directly.",
                "Your response must start with { and end with }.",
                'Example correct format: {"key1": "value1", "key2": null}',
                "Never include any explanation or elaboration before or after the JSON object.",
                format_prompt,
            ]
        )
        full_prompt = "\n".join(parts)
        logger.debug(f"Made full prompt:\n\n{full_prompt}\n\n")
        return full_prompt

    def extract_initial_company_info(self, message: str) -> dict:
        """Extract basic company info from recruiter message"""
        try:
            full_prompt = self.make_prompt(
                EXTRACT_COMPANY_PROMPT.format(message=message),
                EXTRACT_COMPANY_FORMAT_PROMPT,
                extra_context="",  # No need for search context when parsing message directly
            )
            result = self.llm.invoke(full_prompt)
            if not isinstance(result.content, str):
                raise ValueError(f"Expected string content, got {type(result.content)}")
            return self.extract_json_from_response(result.content)
        except Exception as e:
            logger.error(f"Error extracting company info: {e}")
            return {}

    def get_search_context(self, prompt: str) -> str:
        if len(prompt) > GET_SEARCH_CONTEXT_INPUT_LIMIT:
            logger.warning(
                f"Truncating prompt from {len(prompt)} to {GET_SEARCH_CONTEXT_INPUT_LIMIT} characters"
            )
            prompt = prompt[:GET_SEARCH_CONTEXT_INPUT_LIMIT]
            logger.debug(f"Prompt truncated: {prompt}")
        else:
            logger.debug(f"Prompt not truncated: {prompt}")

        context = self.tavily_client.get_search_context(
            query=prompt,
            max_tokens=1000 * 20,
            max_results=10,
            search_depth="advanced",
        )
        return context

    def _plaintext_from_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url.lstrip("/")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Referer": "https://www.linkedin.com/",
        }
        try:
            logger.info(f"Fetching URL for plaintext: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            logger.info(f"Fetched {len(text)} characters from {url}")
            return text
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error when fetching {url}: {e}")
            return f"SSL error occurred when accessing {url}"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error when fetching {url}: {e}")
            return f"Request error occurred when accessing {url}"

    def main(self, *, url: str = "", message: str = "") -> CompaniesSheetRow:
        """
        Research a company based on either a URL or a recruiter message.
        One of url or message must be provided.

        Args:
            url: Company URL to research
            message: Recruiter message to analyze
        """
        if all([url, message]) or not any([url, message]):
            raise ValueError("Exactly one of url or message must be provided")

        company_info = CompaniesSheetRow(
            url=url,
            updated=datetime.date.today(),
            current_state="10. consider applying",  # Default initial state
        )

        # Prefer plaintext from any non-LinkedIn URL found in the message, if provided
        content: str
        if not message:
            content = self._plaintext_from_url(url)
        else:
            # Extract URLs from message
            urls = set(u.strip(".,)\n ") for u in re.findall(r"https?://\S+", message))
            non_linkedin_urls = [u for u in urls if "linkedin.com" not in u.lower()]

            chosen_url = ""
            if non_linkedin_urls:
                # Prefer careers/jobs URLs first
                prioritized = [
                    u
                    for u in non_linkedin_urls
                    if any(
                        tok in u.lower()
                        for tok in ["/careers", "/jobs", "jobs.", "careers."]
                    )
                ]
                chosen_url = prioritized[0] if prioritized else non_linkedin_urls[0]

            if chosen_url:
                # Fetch plaintext and SUPPLEMENT the original message, not replace it
                fetched_text = self._plaintext_from_url(chosen_url)
                content = (
                    f"Extract company info from email message and referenced page.\n\n"
                    f"Referenced URL: {chosen_url}\n\n"
                    f"---- Begin email message ----\n{message}\n---- End email message ----\n"
                    f"---- Begin referenced page plaintext ----\n{fetched_text}\n---- End referenced page plaintext ----\n\n"
                )
            else:
                # Fall back to raw message content
                content = message

        data = self.extract_initial_company_info(content)
        company_info.name = data.get("company_name", "")
        company_info.url = data.get("company_url", url)
        company_info.recruit_contact = data.get("recruiter_name", "")

        logger.info(f"Initial company info: {company_info}")

        if is_placeholder(company_info.name) and not company_info.url:
            logger.warning(
                f"Not enough company info to proceed with research: {company_info.company_identifier}"
            )
            return company_info

        got_jobs_url = False
        for prompt, format_prompt in COMPANY_PROMPTS_WITH_FORMAT_PROMPT:
            try:
                context = self.get_search_context(
                    prompt.format(company_info=company_info)
                )
                logger.debug(f"  Got Context: {len(context)}")
                full_prompt = self.make_prompt(
                    prompt,
                    format_prompt,
                    extra_context=context,
                    company_info=company_info,
                )
                logger.debug(f"  Full prompt:\n\n {full_prompt}\n\n")
                logger.info(f"Invoking LLM with model type: {type(self.llm).__name__}")
                try:
                    result = self.llm.invoke(full_prompt)
                    logger.info("LLM invocation completed successfully")
                except Exception as e:
                    logger.error(f"LLM invocation failed with error: {e}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error(f"Error details: {str(e)}")
                    raise
                # TODO: Handle malformed JSON
                try:
                    if not isinstance(result.content, str):
                        raise ValueError(
                            f"Expected string content, got {type(result.content)}"
                        )
                    json_content: dict = self.extract_json_from_response(result.content)
                    logger.debug(f"  Content returned from llm:\n\n {json_content}\n\n")
                except Exception as e:
                    logger.error(
                        f"Error {e} parsing JSON raw string:\n'{result.content}'\n"
                    )
                    raise

                # Map the API response fields to CompaniesSheetRow fields
                self.update_company_info_from_dict(company_info, json_content)

                if not got_jobs_url and company_info.url:
                    got_jobs_url = True
                    # Redo basic company info extraction with the new jobs URL,
                    # as sometimes that gives us a more accurate company name
                    # (eg some recruiter messages don't include it).
                    redone_initial_data = self.extract_initial_company_info(
                        self._plaintext_from_url(company_info.url)
                    )
                    self.update_company_info_from_dict(company_info, redone_initial_data)
            except Exception as e:
                logger.error(f"Error processing prompt: {e}")
                raise
        return company_info

    def update_company_info_from_dict(
        self, company_info: CompaniesSheetRow, content: dict
    ):
        def update_field_from_key_if_present(fieldname, key):
            val = content.get(key, "")
            val = "" if val is None else val
            val = val.lower().strip() if isinstance(val, str) else val
            if val in (
                "",
                "null",
                "undefined",
                "unknown",
            ):
                return
            if fieldname in company_info.__class__.model_fields:
                setattr(company_info, fieldname, val)
            else:
                logger.warning(f"Skipping unknown field: {fieldname}")

        # Company name is a special case - only update if research found a better name
        new_name = (content.get("company_name") or "").strip()
        current_name = (company_info.name or "").strip()

        if new_name:
            # Check if new name is a generic host name that should be ignored
            normalized_new_name = new_name.lower().strip()
            if normalized_new_name == "notion" or normalized_new_name == "linkedin":
                logger.info(
                    f"Ignoring generic host name '{new_name}' - not updating company name"
                )
            else:
                # Track alternate names discovered during research
                if (
                    current_name
                    and new_name.lower().strip() != current_name.lower().strip()
                ):
                    # Store alternate name for later alias creation
                    if not hasattr(self, "_discovered_alternate_names"):
                        self._discovered_alternate_names = set()
                    self._discovered_alternate_names.add(new_name)
                    logger.info(
                        f"Discovered alternate name '{new_name}' for company (current: '{current_name}')"
                    )

                # Always assign new name if current is blank/None
                if not current_name:
                    logger.info(
                        f"Company name update: No existing name, setting to '{new_name}'"
                    )
                    company_info.name = new_name
                # Only replace existing name if new name is better
                elif is_placeholder(current_name):
                    if is_placeholder(new_name):
                        logger.info(
                            f"Not replacing '{current_name}' with placeholder '{new_name}'"
                        )
                    else:
                        logger.info(
                            f"Company name update: Replacing '{current_name} with better '{new_name}'"
                        )
                        company_info.name = new_name

        update_field_from_key_if_present("ny_address", "nyc_office_address")
        update_field_from_key_if_present("headquarters", "headquarters_city")
        update_field_from_key_if_present("eng_size", "total_engineers")
        update_field_from_key_if_present("total_size", "total_employees")

        # Funding info
        update_field_from_key_if_present("valuation", "valuation")
        update_field_from_key_if_present("funding_series", "funding_series")
        update_field_from_key_if_present("type", "public_status")

        # Interview type info
        update_field_from_key_if_present("sys_design", "interview_style_systems")
        update_field_from_key_if_present("leetcode", "interview_style_leetcode")

        update_field_from_key_if_present("url", "jobs_homepage_url")
        update_field_from_key_if_present("remote_policy", "remote_work_policy")
        # TODO: hiring_status, hiring_status_ai

        update_field_from_key_if_present("ai_notes", "ai_notes")

        logger.debug(f"  DATA SO FAR:\n{company_info}\n\n")
        return company_info

    def get_discovered_alternate_names(self) -> list[str]:
        """Get the set of alternate names discovered during research."""
        return sorted(getattr(self, "_discovered_alternate_names", set()))


def main(
    url_or_message: str,
    model: str,
    refresh_rag_db: bool = False,  # TODO: Unused
    verbose: bool = False,
    is_url: bool | None = None,
    provider: str | None = None,
) -> tuple[CompaniesSheetRow, list[str]]:
    """
    Research a company based on either a URL or a recruiter message.

    Args:
        url_or_message: Either a company URL or a recruiter message
        model: The LLM model to use
        refresh_rag_db: Whether to refresh the RAG database
        verbose: Whether to enable verbose logging
        is_url: Force interpretation as URL (True) or message (False). If None, will try to auto-detect.
    """
    TEMPERATURE = 0.7  # TBD what's a good range for this use case? Is this high?

    # Resolve provider if not explicitly provided
    resolved_provider = provider
    if resolved_provider is None:
        if model.lower().startswith("claude"):
            resolved_provider = "anthropic"
        elif model.lower().startswith("gpt"):
            resolved_provider = "openai"
        else:
            raise ValueError(f"Unknown model: {model}")

    llm: BaseChatModel = get_chat_client(
        provider=cast(Literal["openai", "anthropic", "openrouter"], resolved_provider),
        model=model,
        temperature=TEMPERATURE,
        timeout=TIMEOUT,
    )

    researcher = TavilyRAGResearchAgent(verbose=verbose, llm=llm)

    # Auto-detect if not specified
    if is_url is None:
        is_url = url_or_message.startswith(("http://", "https://"))

    if is_url:
        results = researcher.main(url=url_or_message)
    else:
        results = researcher.main(message=url_or_message)

    return results, researcher.get_discovered_alternate_names()


if __name__ == "__main__":
    import argparse

    from libjobsearch import SONNET_LATEST

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="URL of company or recruiter message to research")
    parser.add_argument(
        "--type",
        choices=["url", "message"],
        help="Force interpretation as URL or message. If not specified, will auto-detect.",
    )
    parser.add_argument(
        "--model",
        help="AI model to use",
        action="store",
        default=SONNET_LATEST,
        choices=[
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-7-sonnet-20250219",
            "claude-sonnet-4-20250514",
            "claude-sonnet-4-5",
            SONNET_LATEST,
        ],
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--refresh-rag-db",
        action="store_true",
        default=False,
        help="Force fetching data and refreshing the RAG database for this URL. Default is to use existing data.",
    )

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    is_url = None if args.type is None else (args.type == "url")

    data = main(
        args.input,
        model=args.model,
        refresh_rag_db=args.refresh_rag_db,
        verbose=args.verbose,
        is_url=is_url,
    )
    import pprint

    pprint.pprint(data)


# Vetting models:
# - gpt-4o:  status = unicorn, urls = careers, team, workplace, compensation, blog
# - gpt-4-turbo: status = private, urls = careers, about, blog
# Sometimes complain about being unable to open URLs.
