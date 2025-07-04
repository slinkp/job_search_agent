"""
Synthetic data generation for company classification.
Provides both random and LLM-based approaches for generating test data.
"""

import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, cast

import ulid
from anthropic import Anthropic
from anthropic.types import MessageParam
from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

# Default batch size for LLM generators
DEFAULT_BATCH_SIZE = 5


class CompanyType(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PRIVATE_UNICORN = "private unicorn"
    PRIVATE_FINANCE = "private finance"


class FitCategory(Enum):
    GOOD = "good"
    BAD = "bad"
    NEEDS_MORE_INFO = "needs_more_info"


def random_id():
    # Overkill but I like ULIDs.
    random_id = str(ulid.new())
    # Let's take the date portion and first random char.
    # But skip the first char just because it'll be "0" for a thousand years.
    # Oh no, a Y3084 bug! :-D
    return random_id[1:11]


@dataclass
class CompanyGenerationConfig:
    """Configuration for synthetic data generation."""

    # Ranges for numeric fields
    base_salary_range: tuple[int, int] = (90_000, 300_000)
    rsu_range: tuple[int, int] = (0, 300_000)
    bonus_range: tuple[int, int] = (0, 450_000)
    eng_size_range: tuple[int, int] = (30, 3000)
    total_size_range: tuple[int, int] = (100, 30000)

    # Probabilities
    prob_has_rsu: float = 0.5
    prob_has_bonus: float = 0.6
    prob_has_valuation: float = 0.8
    prob_has_size_data: float = 0.7

    # Company type distribution
    type_weights: Dict[CompanyType, float] = field(
        default_factory=lambda: {
            CompanyType.PUBLIC: 0.2,
            CompanyType.PRIVATE: 0.5,
            CompanyType.PRIVATE_UNICORN: 0.2,
            CompanyType.PRIVATE_FINANCE: 0.1,
        }
    )

    def __post_init__(self):
        if self.type_weights is None:
            self.type_weights = {
                CompanyType.PUBLIC: 0.2,
                CompanyType.PRIVATE: 0.5,
                CompanyType.PRIVATE_UNICORN: 0.2,
                CompanyType.PRIVATE_FINANCE: 0.1,
            }


class RandomCompanyGenerator:
    """Generates synthetic company data using random sampling."""

    # Real examples of remote policies from our data
    REMOTE_POLICIES = [
        "hybrid 3 days",
        "remote",
        "hybrid",
        '"remote first" w/ offices',
        "hybrid. work from office >= 50% time",
        "hybrid M-T-THu required",
        "office",
        "remote first",
        "relocation required",
    ]

    # Real NYC office locations from our data
    NYC_LOCATIONS = [
        "Union Square",
        "4 World Trade Center",
        "200 Fifth Avenue",
        "627 Broadway",
        "28 Liberty Street (Financial District)",
        "3 WTC",
        "130 5th Ave",
        "1 Vanderbilt",
        "Noho office",
        "Jersey City",
        "242 W 41st St, New York, NY 10036",
        None,
        None,
        None,
    ]

    def __init__(
        self, config: Optional[CompanyGenerationConfig] = None, seed: Optional[int] = None
    ):
        self.config = config or CompanyGenerationConfig()
        if seed is not None:
            random.seed(seed)

    def generate_company(self) -> Dict[str, Any]:
        """Generate a single synthetic company."""
        company_type = random.choices(
            list(CompanyType),
            weights=[self.config.type_weights[t] for t in CompanyType],
            k=1,
        )[0]

        # Generate base compensation
        base = random.randint(*self.config.base_salary_range)

        # RSUs
        rsu = (
            random.randint(*self.config.rsu_range)
            if company_type in (CompanyType.PUBLIC, CompanyType.PRIVATE_UNICORN)
            and random.random() < self.config.prob_has_rsu
            else 0
            )

        # Bonuses more likely in finance
        bonus = (
            random.randint(*self.config.bonus_range)
            if random.random() < self.config.prob_has_bonus
            else 0
        )

        # Calculate total comp
        total_comp = base + rsu + bonus

        # Generate company size data
        eng_size = (
            random.randint(*self.config.eng_size_range)
            if random.random() < self.config.prob_has_size_data
            else None
        )

        total_size = (
            max(
                eng_size * 3 if eng_size else 0,
                random.randint(*self.config.total_size_range),
            )
            if random.random() < self.config.prob_has_size_data
            else None
        )

        # Valuation more likely for certain company types
        valuation = None
        if company_type in (CompanyType.PRIVATE_UNICORN, CompanyType.PUBLIC):
            if random.random() < self.config.prob_has_valuation:
                valuation = total_comp * random.randint(1000, 5000)

        _random_id = random_id()
        return {
            "company_id": f"synthetic-{_random_id}",
            "name": f"Synthetic Company {_random_id}",
            "type": company_type.value,
            "valuation": valuation,
            "total_comp": total_comp,
            "base": base,
            "rsu": rsu,
            "bonus": bonus,
            "remote_policy": random.choice(self.REMOTE_POLICIES),
            "eng_size": eng_size,
            "total_size": total_size,
            "headquarters": "New York" if random.random() < 0.7 else None,
            "ny_address": random.choice(self.NYC_LOCATIONS),
            "ai_notes": None,  # Will be better handled by LLM approach
            "fit_category": None,
            "fit_confidence": None,
        }

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies."""
        return [self.generate_company() for _ in range(n)]


class LLMCompanyGenerator:
    """Generates synthetic company data using LLM."""

    SYSTEM_PROMPT = """
    You are an expert at generating synthetic but realistic tech company data for the NYC market.
    Generate company profiles that reflect real patterns in compensation, remote work policies,
    and office locations. Focus on maintaining realistic relationships between fields.

    Follow these business rules strictly:
    1. Company type distribution:
       - private: 50% (standard tech companies)
       - public: 20% (established tech companies)
       - private finance: 10% (fintech, trading firms)
       - private unicorn: 20% (high-growth startups valued >$1B)

    2. Compensation rules:
       - Total comp range: $160,000 to $600,000
       - RSU rules:
         - Only public and private unicorn companies give RSUs
         - Other types must have RSU = 0
       - Bonus rules:
         - private finance: high bonus ($100,000 - $450,000)
         - other types: lower bonus ($0 - $50,000)
       - Base salary should be reasonable given total comp target
    """

    BATCH_COMPANY_PROMPT = """
    Generate {batch_size} realistic tech company profiles for NYC. Ensure diversity across all companies in the batch - vary company types, compensation structures, remote policies, and office locations.

    Follow the same rules as single company generation:
    
    1. Use realistic compensation ranges for staff software engineers, based on company type:
       - public: high base + RSUs, moderate bonus
       - private: good base, no RSUs, low bonus
       - private unicorn: good base + RSUs, low bonus
       - private finance: highest base, no RSUs, very high bonus

    2. Make remote work policies specific and detailed.
       In-office from 0 days per week (for fully remote companies) to 5
       (for fully onsite companies).

    3. Use real office locations and neighborhoods.
       3a. Most generated companies should have an office in New York City metro area.
       3b. Some may have a headquarters elsewhere in the world, AND a satellite office in NYC.
       3c. Some may have no NYC office.

    4. {ai_notes_instruction}

    5. Ensure all numeric fields are realistic and correlated.
       - RSUs only for public/unicorn companies
       - High bonuses only for finance companies
       - Base salary should be market competitive

    6. CRITICAL: Ensure diversity across the batch. Don't repeat similar patterns.
       - Vary company types according to the probabilities
       - Vary compensation levels within realistic ranges  
       - Use different remote policies and office locations
       - Create unique company names

    Return the data as a JSON object with a "companies" array containing {batch_size} company objects, each with these exact fields:
    {{
        "companies": [
            {{
                "company_id": "synthetic-llm-XXXX",
                "name": "<a weird, creative, short combination of nouns and verbs>",
                "type": "public|private|private unicorn|private finance",
                "valuation": number or null,
                "total_comp": number,
                "base": number,
                "rsu": number,
                "bonus": number,
                "remote_policy": "string",
                "eng_size": number or null,
                "total_size": number or null,
                "headquarters": "string" or null,
                "ny_address": "string" or null,
                "ai_notes": "string" or null,
                "fit_category": null,
                "fit_confidence": null
            }}
            // ... {batch_size} total companies
        ]
    }}

    The numeric fields should follow these constraints:
    - base_salary_range: {base_salary_range}
    - rsu_range: {rsu_range}
    - bonus_range: {bonus_range}
    - eng_size_range: {eng_size_range}
    - total_size_range: {total_size_range}

    Company type distribution across the batch (FOLLOW THESE EXACTLY):
    - public: 20%
    - private: 50%
    - private unicorn: 20%
    - private finance: 10%

    Compensation rules (FOLLOW THESE EXACTLY):
    1. Total comp must be between $160,000 and $600,000
    2. RSUs:
       - Must be 0 for private and private finance companies
       - Can be >0 only for public and private unicorn
    3. Bonuses:
       - private finance: $100,000 to $450,000
       - other types: $0 to $50,000
    """

    def __init__(
        self,
        config: Optional[CompanyGenerationConfig] = None,
        model: str = "gpt-4.1-nano",  # Cheapest model by default
        provider: Literal["openai", "anthropic"] = "openai",
        ai_notes_probability: float = 0.6,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """Initialize the LLM generator with configuration.

        Args:
            config: Optional configuration for data generation
            model: Model to use. For OpenAI: gpt-4-turbo-preview, gpt-4-0125-preview, gpt-3.5-turbo
                  For Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229
            provider: Which LLM provider to use ("openai" or "anthropic")
            ai_notes_probability: Probability of requesting an AI story (default 0.6)
            batch_size: Number of companies to generate per LLM request (default 5)
        """
        self.config = config or CompanyGenerationConfig()
        self.model = model
        self.provider = provider
        self.ai_notes_probability = ai_notes_probability
        self.batch_size = max(1, min(batch_size, 20))  # Clamp between 1-20

        # Initialize appropriate client
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable must be set")
            self.openai_client = OpenAI()
            self.anthropic_client = None
        else:  # anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
            self.anthropic_client = Anthropic()
            self.openai_client = None

    def generate_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies in a single LLM request."""
        # Randomly decide whether to ask for AI notes
        ask_for_ai_notes = random.random() < self.ai_notes_probability
        # TODO: fix this to instruct it to give notes to N * ai_notes_probability companies
        if ask_for_ai_notes:
            ai_notes_instruction = "Include relevant AI/ML notes if applicable for some companies: whether and how AI is part of the company's product offerings, technical strategy, and/or tech stack."
        else:
            ai_notes_instruction = (
                "Do not include any AI/ML notes. Set ai_notes to null for all companies."
            )

        # Format batch prompt with config values
        prompt = self.BATCH_COMPANY_PROMPT.format(
            batch_size=batch_size,
            base_salary_range=self.config.base_salary_range,
            rsu_range=self.config.rsu_range,
            bonus_range=self.config.bonus_range,
            eng_size_range=self.config.eng_size_range,
            total_size_range=self.config.total_size_range,
            ai_notes_instruction=ai_notes_instruction,
        )

        start_time = time.time()
        print(
            f"Calling {self.provider} LLM for batch of {batch_size}...",
            end="",
            flush=True,
            file=sys.stderr,
        )

        temperature = (
            0.7  # Balance between creativity and consistency. Lower = more deterministic.
        )
        if self.model.startswith("o1") or self.model.startswith("o4"):
            temperature = 1.0  # O1 and O4 models don't support altering temperature.

        if self.provider == "openai":
            # Call OpenAI API with proper message types
            messages: List[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(
                    role="system", content=self.SYSTEM_PROMPT
                ),
                ChatCompletionUserMessageParam(role="user", content=prompt),
            ]

            # Call OpenAI API
            if not self.openai_client:
                raise ValueError("OpenAI client not initialized")
            response = cast(
                ChatCompletion,
                self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},  # Ensure JSON output
                ),
            )
            content = response.choices[0].message.content
        else:  # anthropic
            # Call Anthropic API with explicit JSON request
            message: MessageParam = {
                "role": "user",
                "content": f"{prompt}\n\nPlease respond with a valid JSON object only, no other text.",
            }
            if not self.anthropic_client:
                raise ValueError("Anthropic client not initialized")
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=f"{self.SYSTEM_PROMPT}\n\nYou must respond with a valid JSON object only, no other text.",
                messages=[message],
                temperature=temperature,
            )
            # Extract content from the first content block
            content = None
            if response.content and len(response.content) > 0:
                block = response.content[0]
                if hasattr(block, "text"):
                    content = block.text.strip()
                    # Try to find JSON in the response
                    try:
                        # Find the first { and last }
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            content = content[start:end]
                    except Exception as e:
                        print(
                            f"Warning: Failed to extract JSON from response: {e}",
                            file=sys.stderr,
                        )
                        content = None

        duration = time.time() - start_time
        print(f" done ({duration:.1f}s)", file=sys.stderr)

        if not content:
            raise ValueError("Empty response from LLM")

        try:
            batch_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response from LLM: {content}", file=sys.stderr)
            raise ValueError(f"Invalid JSON response from LLM: {e}")

        # Extract companies array from response
        if "companies" not in batch_data:
            raise ValueError("Batch response missing 'companies' array")

        companies = batch_data["companies"]
        if not isinstance(companies, list):
            raise ValueError("'companies' field must be an array")

        if len(companies) != batch_size:
            print(
                f"Warning: Expected {batch_size} companies, got {len(companies)}",
                file=sys.stderr,
            )

        # Process each company in the batch
        processed_companies = []
        for i, company_data in enumerate(companies):
            try:
                _random_id = random_id()
                # Ensure company name and id is unique.
                company_data["name"] = f"{company_data['name']} {_random_id}"
                company_data["company_id"] = f"synthetic-llm-{_random_id}"

                # Do not populate fit_category or fit_confidence
                company_data["fit_category"] = None
                company_data["fit_confidence"] = None

                # If we did not ask for ai_notes, set it to None regardless of LLM output
                if not ask_for_ai_notes:
                    company_data["ai_notes"] = None

                # Validate required fields
                required_fields = {
                    "company_id",
                    "name",
                    "type",
                    "total_comp",
                    "base",
                    "rsu",
                    "bonus",
                    "remote_policy",
                }
                if not all(field in company_data for field in required_fields):
                    raise ValueError(
                        f"Company {i}: Missing required fields: {required_fields - set(company_data.keys())}"
                    )

                # Validate and clamp numeric ranges
                company_data["base"] = max(
                    self.config.base_salary_range[0],
                    min(company_data["base"], self.config.base_salary_range[1]),
                )
                if company_data["rsu"] > 0:
                    company_data["rsu"] = max(
                        self.config.rsu_range[0],
                        min(company_data["rsu"], self.config.rsu_range[1]),
                    )
                if company_data["bonus"] > 0:
                    company_data["bonus"] = max(
                        self.config.bonus_range[0],
                        min(company_data["bonus"], self.config.bonus_range[1]),
                    )

                # Recalculate total comp to ensure it matches components
                company_data["total_comp"] = (
                    company_data["base"] + company_data["rsu"] + company_data["bonus"]
                )

                # Validate company type
                if company_data["type"] not in [t.value for t in CompanyType]:
                    raise ValueError(
                        f"Company {i}: Invalid company type: {company_data['type']}"
                    )

                processed_companies.append(company_data)

            except Exception as e:
                print(f"Warning: Skipping company {i} due to error: {e}", file=sys.stderr)
                continue

        return processed_companies

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies using batch processing with fallback."""
        if n <= 0:
            return []

        companies = []
        remaining = n
        batch_num = 0

        MAX_BATCHES = 100 # Safety net
        while remaining > 0:
            batch_num += 1
            current_batch_size = min(remaining, self.batch_size)

            print(
                f"\nGenerating batch {batch_num} ({current_batch_size} companies):",
                file=sys.stderr,
            )
            try:
                batch_companies = self.generate_batch(current_batch_size)
            except Exception as e:
                print(f"Batch {batch_num} generation failed: {e}", file=sys.stderr)
                continue

            companies.extend(batch_companies)
            remaining -= len(batch_companies)

            if batch_num > MAX_BATCHES and remaining > 0:
                print(
                    f"Warning: Reached maximum batch limit {MAX_BATCHES}, stopping with {len(companies)} companies",
                    file=sys.stderr,
                )
                break

        print(f"\nGenerated {len(companies)} companies total", file=sys.stderr)
        return companies


class HybridCompanyGenerator:
    """Combines random and LLM approaches for optimal synthetic data generation."""

    def __init__(
        self,
        config: Optional[CompanyGenerationConfig] = None,
        model: str = "gpt-3.5-turbo",
        provider: Literal["openai", "anthropic"] = "openai",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """Initialize the hybrid generator.

        Args:
            config: Optional configuration for data generation
            model: Model to use for LLM generation
            provider: LLM provider to use ("openai" or "anthropic")
            batch_size: Number of companies to generate per LLM request (default 5)
        """
        self.random_gen = RandomCompanyGenerator(config)
        self.llm_gen = LLMCompanyGenerator(
            config, model=model, provider=provider, batch_size=batch_size
        )

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies using hybrid approach."""
        if n <= 0:
            return []

        # Generate all random companies in bulk (fast)
        print(f"\nGenerating {n} companies using hybrid generator:", file=sys.stderr)
        random_companies = self.random_gen.generate_companies(n)

        # Generate all LLM companies using batching (efficient)
        print(f"Generating LLM data with batching...", file=sys.stderr)
        llm_companies = self.llm_gen.generate_companies(n)

        # Combine each pair of companies
        print(f"Combining results...", file=sys.stderr)
        combined_companies = []
        for i, (random_company, llm_company) in enumerate(zip(random_companies, llm_companies)):
            print(f"Processing company {i+1}/{n}", file=sys.stderr)

            # Create a hybrid company the same way generate_company does
            _random_id = random_id()
            # Combine the two approaches with improved logic:
            company = {
                # Use LLM's text fields and correlations
                "company_id": f"synthetic-hybrid-{_random_id}",
                "name": llm_company["name"],
                "remote_policy": llm_company["remote_policy"],
                "headquarters": llm_company["headquarters"],
                "ny_address": llm_company["ny_address"],
                "ai_notes": llm_company["ai_notes"],
                # Do not populate fit_category or fit_confidence
                "fit_category": None,
                "fit_confidence": None,
                # Use random generator's numeric and categorical fields as base
                "valuation": random_company["valuation"],
                "total_comp": random_company["total_comp"],
                "base": random_company["base"],
                "type": random_company["type"],
                "rsu": random_company["rsu"],
                "bonus": random_company["bonus"],
                "eng_size": random_company["eng_size"],
                "total_size": random_company["total_size"],
            }

            # Apply enhanced business rules
            # The random generator already handles RSUs for private companies

            if company["type"] == "private finance":
                # Finance companies should have higher bonuses
                min_bonus = 100_000
                max_bonus = 450_000
                company["bonus"] = max(
                    company["bonus"], random.randint(min_bonus, max_bonus)
                )
                # Adjust base to maintain reasonable total comp
                company["base"] = max(company["base"], 200_000)
                company["total_comp"] = company["base"] + company["bonus"]

            elif company["type"] in ["public", "private unicorn"]:
                # Public and unicorn companies should have significant RSUs
                min_rsu = 30_000
                max_rsu = 300_000
                company["rsu"] = max(company["rsu"], random.randint(min_rsu, max_rsu))
                # Adjust base to maintain reasonable total comp
                company["base"] = max(company["base"], 120_000)
                company["total_comp"] = (
                    company["base"] + company["rsu"] + company["bonus"]
                )

            # Ensure total comp is within reasonable range
            min_total = 160_000
            max_total = 600_000
            if company["total_comp"] < min_total:
                # Increase base to meet minimum
                company["base"] += min_total - company["total_comp"]
                company["total_comp"] = min_total
            elif company["total_comp"] > max_total:
                # Scale down components proportionally
                scale = max_total / company["total_comp"]
                company["base"] = int(company["base"] * scale)
                company["rsu"] = int(company["rsu"] * scale)
                company["bonus"] = int(company["bonus"] * scale)
                company["total_comp"] = max_total

            # Ensure engineering size is reasonable relative to total size
            if company["eng_size"] and company["total_size"]:
                min_eng_ratio = 0.1  # Engineering should be at least 10% of total
                max_eng_ratio = 0.5  # Engineering shouldn't be more than 50% of total
                eng_ratio = company["eng_size"] / company["total_size"]
                if eng_ratio < min_eng_ratio:
                    company["eng_size"] = int(company["total_size"] * min_eng_ratio)
                elif eng_ratio > max_eng_ratio:
                    company["eng_size"] = int(company["total_size"] * max_eng_ratio)

            combined_companies.append(company)

        return combined_companies
