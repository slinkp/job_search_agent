import argparse
import dataclasses
import datetime
import decimal
import logging
import os
import os.path
import queue
import re
import subprocess
import tempfile
import time
from enum import IntEnum
from functools import wraps
from multiprocessing import Process, Queue
from typing import Any, Callable, Optional

from diskcache import Cache  # type: ignore
from pydantic import BaseModel, ValidationError

import company_researcher
import email_client
import levels_searcher
import linkedin_searcher
import models
import spreadsheet_client
from logsetup import setup_logging
from message_generation_rag import RecruitmentRAG
from models import CompaniesSheetRow, RecruiterMessage
from spreadsheet_client import MainTabCompaniesClient

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

cache = Cache(os.path.join(HERE, ".cache"))


class CacheStep(IntEnum):
    GET_MESSAGES = 0
    RAG_CONTEXT = 1
    BASIC_RESEARCH = 2
    LEVELS_RESEARCH = 3
    COMPENSATION_RESEARCH = 4
    FOLLOWUP_RESEARCH = 5
    REPLY = 6


@dataclasses.dataclass
class CacheSettings:
    no_cache: bool = False
    clear_cache: list[CacheStep] = dataclasses.field(default_factory=list)
    cache_until: CacheStep | None = None
    clear_all_cache: bool = False

    def should_cache_step(self, step: CacheStep) -> bool:
        if self.no_cache:
            return False
        if self.cache_until is None:
            return True
        return self.cache_until >= step

    def should_clear_cache(self, step: CacheStep) -> bool:
        if self.clear_all_cache:
            return True
        if self.clear_cache:
            return step in self.clear_cache
        return False


def disk_cache(step: CacheStep):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get cache settings from instance
            use_cache = self.cache_settings.should_cache_step(step)
            clear_cache = self.cache_settings.should_clear_cache(step)

            # Remove memory addresses from string representations
            args_str = re.sub(r" at 0x[0-9a-fA-F]+", "", str(args))
            kwargs_str = re.sub(r" at 0x[0-9a-fA-F]+", "", str(kwargs))
            key = f"{func.__name__}:{args_str}:{kwargs_str}"
            result = None

            if clear_cache:
                cache.delete(key)

            if use_cache:
                result = cache.get(key)
                if result is None:
                    logger.debug(f"Cache miss for {key}")
                else:
                    logger.debug(f"Cache hit for {key}")
                    # Validate cached Pydantic models
                    if isinstance(result, BaseModel):
                        try:
                            # Try to re-validate the model
                            # This will catch missing fields and type mismatches
                            result = result.__class__.model_validate(result.model_dump())
                            logger.debug(
                                f"Validated cached model: {result.__class__.__name__}"
                            )
                        except ValidationError as e:
                            logger.warning(
                                f"Cache validation failed, clearing entry: {e}"
                            )
                            cache.delete(key)
                            result = None

            if result is None:
                logger.debug(f"No cached result, running function for {key}...")
                result = func(self, *args, **kwargs)
                logger.debug(f"... Ran function for {key}")
            if use_cache:
                cache.set(key, result)

            return result

        return wrapper

    return decorator


def _process_wrapper(func, args, kwargs, result_queue, error_queue):
    # This needs to be a separate function to avoid pickling issues.
    try:
        result = func(*args, **kwargs)
        result_queue.put(result)
    except Exception as e:
        error_queue.put((type(e), str(e)))
        result_queue.put(None)  # Signal completion even on error


def run_in_process(func: Callable, *args, timeout=120, **kwargs) -> Any:
    """
    Run a function in a separate process and return its result.

    Args:
        func: The function to run
        timeout: Maximum time to wait for result in seconds
        *args, **kwargs: Arguments to pass to the function

    Returns:
        The result of running the function

    Raises:
        TimeoutError: If the function takes longer than timeout seconds
        Exception: If the function raises an exception
    """
    result_queue: Queue = Queue()
    error_queue: Queue = Queue()

    process = Process(
        target=_process_wrapper, args=(func, args, kwargs, result_queue, error_queue)
    )
    process.start()

    try:
        # Wait for result (will be None if there was an error)
        try:
            result = result_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(
                f"Function {func.__name__} timed out after {timeout} seconds"
            )

        # Check if there was an error
        try:
            exc_type, exc_msg = error_queue.get_nowait()
            raise exc_type(exc_msg)
        except queue.Empty:
            return result

    finally:
        time.sleep(0.5)
        if process.is_alive():
            logger.warning(f"Terminating still-running process {process.pid}...")
            process.terminate()
            process.join(timeout=1.0)
            if process.is_alive():
                logger.warning(f"Killing still-running process {process.pid}...")
                process.kill()


def send_reply_and_archive(
    message_id: str, thread_id: str, reply: str, company_name: Optional[str] = None
) -> bool:
    """
    Send a reply to a recruiter email.

    Args:
        message_id: The Gmail message ID to reply to
        thread_id: The Gmail thread ID
        reply: The reply text to send
        company_name: Optional company name to create an event for

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Sending reply: {reply[:200]}...")

    try:
        email_searcher = email_client.GmailRepliesSearcher()
        email_searcher.authenticate()

        # Send the reply
        success = email_searcher.send_reply(thread_id, message_id, reply)

        if success:
            # Add label and archive
            email_searcher.label_and_archive_message(message_id)
            logger.info("Reply sent and archived successfully")

            # Create a REPLY_SENT event if company_name is provided
            if company_name:
                event = models.Event(
                    company_name=company_name,
                    event_type=models.EventType.REPLY_SENT,
                )
                models.company_repository().create_event(event)
                logger.info(f"Created REPLY_SENT event for {company_name}")

            return True
        else:
            logger.error("Failed to send reply")
            return False
    except Exception as e:
        logger.exception(f"Error sending reply: {e}")
        return False


def maybe_edit_reply(reply: str) -> str:
    """
    Open reply text in user's preferred editor for optional modification.
    Similar to git commit message editing experience.
    """

    # Get editor from environment, defaulting to vim
    editor = os.environ.get("EDITOR", "vim")

    # Create temporary file with the reply text
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tf:
        tf.write(reply)
        temp_path = tf.name

    try:
        logger.debug(f"Opening editor {editor} on {temp_path}...")
        # Split editor command to handle arguments properly
        editor_cmd = editor.split()

        # Open editor and wait for it to close
        subprocess.run(
            editor_cmd + [temp_path],
            check=True,
        )

        # Read potentially modified content
        with open(temp_path, "r") as f:
            edited_reply = f.read()
        logger.debug(f"...Editor returned {len(edited_reply)} chars")
        return edited_reply.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Editor returned error: {e}")
        return reply  # Return original on error
    finally:
        # Clean up temporary file
        os.unlink(temp_path)


class EmailResponseGenerator:

    def __init__(
        self,
        reply_rag_model: str,
        reply_rag_limit: int,
        loglevel: int,
        cache_settings: CacheSettings,
    ):
        logger.info("Initializing EmailResponder...")
        self.cache_settings = cache_settings
        self.reply_rag_model = reply_rag_model
        self.reply_rag_limit = reply_rag_limit
        self.loglevel = loglevel
        self.email_client = email_client.GmailRepliesSearcher()
        self.email_client.authenticate()
        old_replies = self.load_previous_replies_to_recruiters()
        self.rag = self._build_reply_rag(old_replies)
        logger.info("...EmailResponder initialized")

    def _build_reply_rag(
        self, old_messages: list[tuple[str, str, str]]
    ) -> RecruitmentRAG:  # Set up the RAG pipeline
        logger.info("Building RAG...")
        rag = RecruitmentRAG(old_messages, loglevel=self.loglevel)
        clear_rag_context = self.cache_settings.should_clear_cache(CacheStep.RAG_CONTEXT)
        if clear_rag_context:
            logger.info("Rebuilding RAG data from scratch...")
        else:
            logger.info("Reusing existing RAG data...")
        rag.prepare_data(clear_existing=clear_rag_context)
        rag.setup_chain(llm_type=self.reply_rag_model)
        logger.info("...RAG setup complete")
        return rag

    @disk_cache(CacheStep.GET_MESSAGES)
    def load_previous_replies_to_recruiters(self) -> list[tuple[str, str, str]]:
        logger.info("Fetching my previous replies from mail...")
        old_replies = self.email_client.get_my_replies_to_recruiters(
            max_results=self.reply_rag_limit
        )
        logger.info(f"Got my replies from mail: {len(old_replies)}")

        return old_replies

    @disk_cache(CacheStep.REPLY)
    def generate_reply(self, msg: str) -> str:
        logger.info("Generating reply...")
        result = self.rag.generate_reply(msg)
        logger.info("Reply generated")
        return result

    @disk_cache(CacheStep.GET_MESSAGES)
    def get_new_recruiter_messages(
        self, max_results: int = 100
    ) -> list[RecruiterMessage]:
        logger.info(f"Getting {max_results} new recruiter messages")
        return self.email_client.get_new_recruiter_messages(max_results=max_results)


def upsert_company_in_spreadsheet(
    company_info: CompaniesSheetRow, args: argparse.Namespace
):
    logger.info(f"Processing company for spreadsheet: {company_info.name}")
    if args.sheet == "test":
        config = spreadsheet_client.TestConfig
    else:
        config = spreadsheet_client.Config  # type: ignore
    client = MainTabCompaniesClient(
        doc_id=config.SHEET_DOC_ID,
        sheet_id=config.TAB_1_GID,
        range_name=config.TAB_1_RANGE,
    )

    # Check if the company already exists in the sheet.
    existing_rows = client.read_rows_from_google()
    company_name = company_info.name.lower().strip() if company_info.name else ""

    # Find the row index if the company exists
    existing_row_index = None
    for i, row in enumerate(existing_rows):
        if row and row.name and row.name.lower().strip() == company_name:
            existing_row_index = i
            break

    if existing_row_index is not None:
        # Company exists, update the row
        logger.info(
            f"Updating existing company in spreadsheet: {company_info.name} at row {existing_row_index + 1}"  # noqa: B950
        )
        client.update_row_partial(
            existing_row_index, company_info, skip_empty_update_values=True
        )
        logger.info(f"Updated company in spreadsheet: {company_info.name}")
    else:
        # Company doesn't exist, append a new row
        logger.info(f"Adding new company to spreadsheet: {company_info.name}")
        client.append_rows([company_info.as_list_of_str()])
        logger.info(f"Added company to spreadsheet: {company_info.name}")


class JobSearch:
    """
    Main entry points for this module.
    """

    def __init__(
        self, args: argparse.Namespace, loglevel: int, cache_settings: CacheSettings
    ):
        self.args = args
        self.email_responder = EmailResponseGenerator(
            reply_rag_model=args.model,
            reply_rag_limit=args.rag_message_limit,
            loglevel=loglevel,
            cache_settings=cache_settings,
        )
        self.cache_settings = cache_settings

    def main(self):
        args = self.args
        if args.test_messages:
            new_recruiter_email = args.test_messages
        else:
            logger.debug("Getting new recruiter messages...")
            new_recruiter_email = self.get_new_recruiter_messages(
                max_results=args.recruiter_message_limit
            )
            logger.debug("...Got new recruiter messages")

        for i, msg in enumerate(new_recruiter_email):
            logger.info(f"Processing message {i+1} of {len(new_recruiter_email)}...")
            if not msg.message.strip():
                logger.warning("Empty message, skipping")
                continue

            logger.info(
                f"==============================\n\nProcessing message:\n\n{msg.message}\n"
            )
            # TODO: pass subject too?

            company_info = self.research_company(msg, model=args.model)
            logger.info(f"------- RESEARCHED COMPANY:\n{company_info}\n\n")

            generated_reply = self.generate_reply(msg.message)
            logger.info(f"------ GENERATED REPLY:\n{generated_reply[:400]}\n\n")

            reply = maybe_edit_reply(generated_reply)
            logger.info(f"------ EDITED REPLY:\n{reply}\n\n")
            send_reply_and_archive(
                message_id=msg.message_id,
                thread_id=msg.thread_id,
                reply=reply,
                company_name=company_info.name,
            )
            upsert_company_in_spreadsheet(company_info, args)
            logger.info(f"Processed message {i+1} of {len(new_recruiter_email)}")

    def generate_reply(self, content: str) -> str:
        return self.email_responder.generate_reply(content)

    def research_company(
        self, message: str | RecruiterMessage, model: str, do_advanced=True
    ) -> models.Company:
        """
        Builds a Company object from raw text about the company, eg could be from a recruiter email.  # noqa: B950

        This does not update the company in the database, but it may create events in the db.
        """

        company_info: CompaniesSheetRow = self.initial_research_company(
            message, model=model
        )
        if not str(company_info.name or "").strip():
            # Just name it after microseconds since epoch and assume that in THIS application
            # those will never collide.
            unknown_company_name = "<UNKNOWN %s>" % int(time.time() * 1000 * 1000)
            logger.warning(f"Company name not found, using {unknown_company_name}")
            company_info.name = unknown_company_name
        logger.debug(f"Company info after initial research: {company_info}\n\n")

        research_errors: list[models.ResearchStepError] = []
        assert company_info.name is not None
        company = models.Company(
            name=company_info.name,
            details=company_info,
            status=models.CompanyStatus(research_errors=research_errors),
        )
        if isinstance(message, models.RecruiterMessage):
            company.recruiter_message = message
            company.message_id = message.message_id
        if not do_advanced:
            return company

        try:
            company_info = self.research_levels(company_info)
            logger.debug(f"Company info after levels research: {company_info}\n\n")
        except Exception as e:
            self._handle_research_error("levels_research", company, e)

        try:
            company_info = self.research_compensation(company_info)
            logger.debug(f"Company info after salary research: {company_info}\n\n")
        except Exception as e:
            self._handle_research_error("compensation_research", company, e)

        if self.is_good_fit(company_info):
            try:
                company_info = self.followup_research_company(company_info)
                logger.debug(f"Company info after followup research: {company_info}\n\n")
            except Exception as e:
                self._handle_research_error("followup_research", company, e)
        # Update company details with final research results
        company.details = company_info

        # Create a RESEARCH_COMPLETED event and set timestamp if no errors occurred
        if not research_errors:
            event = models.Event(
                company_name=company.name,
                event_type=models.EventType.RESEARCH_COMPLETED,
            )
            models.company_repository().create_event(event)
            logger.info(f"Created RESEARCH_COMPLETED event for {company.name}")

        return company

    def _handle_research_error(
        self, step_name: str, company: models.Company, e: Exception | str
    ) -> None:
        logger.exception(f"Error during {step_name} research")
        error = models.ResearchStepError(step=step_name, error=str(e))
        company_info = company.details
        # Create an event for the research error
        if company_info.name:
            event = models.Event(
                company_name=company_info.name,
                event_type=models.EventType.RESEARCH_ERROR,
                details=f"{step_name} research failed: {str(e)}",
            )
            models.company_repository().create_event(event)
        company.status.research_errors.append(error)
        company.status.research_failed_at = datetime.datetime.now(datetime.timezone.utc)

    @disk_cache(CacheStep.BASIC_RESEARCH)
    def initial_research_company(
        self, message: str | RecruiterMessage, model: str
    ) -> CompaniesSheetRow:
        logger.info("Starting initial research...")

        email_thread_link = ""
        if isinstance(message, RecruiterMessage):
            email_thread_link = message.email_thread_link
            message = message.message

        # TODO: Implement this:
        # - If there are attachments to the message (eg .doc or .pdf), extract the text from them
        #   and pass that to company_researcher.py too
        row = company_researcher.main(url_or_message=message, model=model, is_url=False)
        row.email_thread_link = email_thread_link
        return row

    @disk_cache(CacheStep.LEVELS_RESEARCH)
    def research_levels(self, row: CompaniesSheetRow) -> CompaniesSheetRow:
        now = datetime.datetime.now()
        logger.info("Finding equivalent job levels ...")
        equivalent_levels = list(
            run_in_process(levels_searcher.extract_levels, row.name) or []
        )
        if equivalent_levels:
            row.level_equiv = ", ".join(equivalent_levels)
            delta = datetime.datetime.now() - now
            logger.info(
                f"Found equivalent job levels: {row.level_equiv} in {delta.seconds} seconds"
            )
        else:
            logger.info(f"No equivalent job levels found for {row.name}")
        return row

    @disk_cache(CacheStep.COMPENSATION_RESEARCH)
    def research_compensation(self, row: CompaniesSheetRow) -> CompaniesSheetRow:
        now = datetime.datetime.now()
        logger.info("Finding salary data ...")
        now = datetime.datetime.now()
        salary_data = run_in_process(levels_searcher.main, company_name=row.name) or []
        salary_data = list(salary_data)  # Convert generator to list if needed

        delta = datetime.datetime.now() - now
        logger.info(
            f"Got {len(salary_data)} rows of salary data for {row.name} in {delta.seconds} seconds"  # noqa: B950
        )

        if salary_data:
            # Calculate averages from all salary entries.
            # TODO: We don't actually want an average, we want the best fit.
            total_comps = [entry["total_comp"] for entry in salary_data]
            base_salaries = [entry["salary"] for entry in salary_data if entry["salary"]]
            equities = [entry["equity"] for entry in salary_data if entry["equity"]]
            bonuses = [entry["bonus"] for entry in salary_data if entry["bonus"]]

            row.total_comp = (
                decimal.Decimal(int(sum(total_comps) / len(total_comps)))
                if total_comps
                else None
            )
            row.base = (
                decimal.Decimal(int(sum(base_salaries) / len(base_salaries)))
                if base_salaries
                else None
            )
            row.rsu = (
                decimal.Decimal(int(sum(equities) / len(equities))) if equities else None
            )
            row.bonus = (
                decimal.Decimal(int(sum(bonuses) / len(bonuses))) if bonuses else None
            )
        else:
            logger.warning(f"No salary data found for {row.name}")

        return row

    @disk_cache(CacheStep.FOLLOWUP_RESEARCH)
    def followup_research_company(
        self, company_info: CompaniesSheetRow
    ) -> CompaniesSheetRow:
        if not company_info.name:
            logger.warning(f"Company name not found: {company_info}, nothing else to do")
            return company_info

        logger.info(f"Doing followup research on: {company_info}")

        linkedin_contacts = (
            run_in_process(linkedin_searcher.main, company_info.name) or []
        )
        linkedin_contacts = linkedin_contacts[:4]

        company_info.maybe_referrals = "\n".join(
            [f"{c['name']} - {c['title']}" for c in linkedin_contacts]
        )

        return company_info

    def is_good_fit(self, company_info: CompaniesSheetRow) -> bool:
        # TODO: basic heuristic for now
        logger.info(f"Checking if {company_info.name} is a good fit...")
        return True

    def get_new_recruiter_messages(
        self, max_results: int = 100
    ) -> list[RecruiterMessage]:
        return self.email_responder.get_new_recruiter_messages(max_results=max_results)


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print verbose logging"
    )

    parser.add_argument(
        "--model",
        help="AI model to use",
        action="store",
        default="claude-3-5-sonnet-latest",
        choices=[
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-5-sonnet-latest",  # noqa: B950
        ],
    )
    DEFAULT_RAG_LIMIT = 20
    parser.add_argument(
        "--rag-message-limit",
        action="store",
        type=int,
        default=DEFAULT_RAG_LIMIT,
        help=f"Max number of old replies for training generated replies (default {DEFAULT_RAG_LIMIT})",  # noqa: B950
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Do not use any caching",
    )

    parser.add_argument(
        "--cache-until",
        type=lambda s: CacheStep[s.upper()],
        choices=list(CacheStep),
        help="Cache steps up to and including this step",
    )

    # Clear cache options
    parser.add_argument(
        "--clear-all-cache",
        action="store_true",
        help="Clear all cached data before running",
    )
    parser.add_argument(
        "--clear-cache",
        type=lambda s: CacheStep[s.upper()],
        choices=list(CacheStep),
        nargs="+",
        help="Clear cache for specific steps before running",
    )

    parser.add_argument(
        "--test-messages",
        action="append",
        help="Test messages to use instead of fetching from Gmail",
    )

    parser.add_argument(
        "--recruiter-message-limit",
        type=int,
        default=1,
        help="Number of recruiter messages to fetch if not using test-messages",
    )
    parser.add_argument(
        "-s",
        "--sheet",
        action="store",
        choices=["test", "prod"],
        default="prod",
        help="Use the test or production spreadsheet",
    )

    return parser


if __name__ == "__main__":
    parser = arg_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)
    if args.verbose:
        email_client.logger.setLevel(logging.DEBUG)

    # Clear all cache if requested (do this before any other operations)
    if args.clear_all_cache:
        logger.info("Clearing all cache...")
        cache.clear()

    cache_settings = CacheSettings(
        clear_all_cache=args.clear_all_cache,
        clear_cache=args.clear_cache,
        cache_until=args.cache_until,
        no_cache=args.no_cache,
    )

    job_searcher = JobSearch(args, loglevel=logger.level, cache_settings=cache_settings)
    job_searcher.main()
