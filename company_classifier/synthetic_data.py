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
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)


class CompanyType(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PRIVATE_UNICORN = "private unicorn"
    PRIVATE_FINANCE = "private finance"


class FitCategory(Enum):
    GOOD = "good"
    BAD = "bad"
    NEEDS_MORE_INFO = "needs_more_info"


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

        return {
            "company_id": f"synthetic-{random.randint(1000, 9999)}",
            "name": f"Synthetic Company {random.randint(1000, 9999)}",
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
            "fit_category": random.choice(list(FitCategory)).value,
            "fit_confidence": 0.8,  # Fixed for synthetic data
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

    COMPANY_PROMPT = """
    Generate a realistic tech company profile for NYC with the following characteristics:
    
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

    4. Include relevant AI/ML notes if applicable: whether and how AI is part of the company's
       product offerings, technical strategy, and/or tech stack.

    5. Ensure all numeric fields are realistic and correlated.
       - RSUs only for public/unicorn companies
       - High bonuses only for finance companies
       - Base salary should be market competitive

    Return the data as a JSON object with these exact fields (no additional fields):
    {{
        "company_id": "synthetic-llm-XXXX",
        "name": "Company name",
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
        "fit_category": "good|bad|needs_more_info",
        "fit_confidence": 0.8
    }}

    The numeric fields should follow these constraints from the config:
    - base_salary_range: {base_salary_range}
    - rsu_range: {rsu_range}
    - bonus_range: {bonus_range}
    - eng_size_range: {eng_size_range}
    - total_size_range: {total_size_range}

    Company type probabilities (FOLLOW THESE EXACTLY):
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
        model: str = "gpt-4-turbo-preview",
    ):
        """Initialize the LLM generator with configuration.

        Args:
            config: Optional configuration for data generation
            model: OpenAI model to use. One of: gpt-4-turbo-preview, gpt-4-0125-preview, gpt-3.5-turbo
        """
        self.config = config or CompanyGenerationConfig()
        self.model = model

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        self.client = OpenAI()

    def generate_company(self) -> Dict[str, Any]:
        """Generate a single synthetic company using LLM."""
        # Format prompt with config values
        prompt = self.COMPANY_PROMPT.format(
            base_salary_range=self.config.base_salary_range,
            rsu_range=self.config.rsu_range,
            bonus_range=self.config.bonus_range,
            eng_size_range=self.config.eng_size_range,
            total_size_range=self.config.total_size_range,
        )

        start_time = time.time()
        print(f"Calling LLM...", end="", flush=True, file=sys.stderr)

        # Call OpenAI API with proper message types
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=self.SYSTEM_PROMPT),
            ChatCompletionUserMessageParam(role="user", content=prompt),
        ]

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,  # Balance between creativity and consistency
            response_format={"type": "json_object"},  # Ensure JSON output
        )

        duration = time.time() - start_time
        print(f" done ({duration:.1f}s)", file=sys.stderr)

        # Parse response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
        company_data = json.loads(content)

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
            "fit_category",
            "fit_confidence",
        }
        if not all(field in company_data for field in required_fields):
            raise ValueError(
                f"Missing required fields in LLM response: {required_fields - set(company_data.keys())}"
            )

        # Validate numeric ranges
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
            raise ValueError(f"Invalid company type: {company_data['type']}")

        # Validate fit category
        if company_data["fit_category"] not in [t.value for t in FitCategory]:
            raise ValueError(f"Invalid fit category: {company_data['fit_category']}")

        return company_data

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies."""
        companies = []
        for i in range(n):
            print(f"\nGenerating company {i+1}/{n}:", file=sys.stderr)
            companies.append(self.generate_company())
        return companies


class HybridCompanyGenerator:
    """Combines random and LLM approaches for optimal synthetic data generation."""

    def __init__(
        self,
        config: Optional[CompanyGenerationConfig] = None,
        model: str = "gpt-4-turbo-preview",
    ):
        """Initialize the hybrid generator.

        Args:
            config: Optional configuration for data generation
            model: OpenAI model to use for LLM generation
        """
        self.random_gen = RandomCompanyGenerator(config)
        self.llm_gen = LLMCompanyGenerator(config, model=model)

    def generate_company(self) -> Dict[str, Any]:
        """
        Generate a single synthetic company using hybrid approach:
        1. Use random generation for numeric fields
        2. Use LLM for text fields and correlations
        3. Apply business rules to ensure realism
        """
        # Get base company from random generator for numeric fields
        random_company = self.random_gen.generate_company()

        # Get LLM company for text fields and correlations
        llm_company = self.llm_gen.generate_company()

        # Combine the two approaches:
        # 1. Use random generator's numeric fields
        # 2. Use LLM's text fields and correlations
        # 3. Ensure business rules are followed
        company = {
            # Use LLM's text fields
            "company_id": llm_company["company_id"],
            "name": llm_company["name"],
            "type": llm_company["type"],
            "remote_policy": llm_company["remote_policy"],
            "headquarters": llm_company["headquarters"],
            "ny_address": llm_company["ny_address"],
            "ai_notes": llm_company["ai_notes"],
            "fit_category": llm_company["fit_category"],
            "fit_confidence": llm_company["fit_confidence"],
            # Use random generator's numeric fields
            "valuation": random_company["valuation"],
            "total_comp": random_company["total_comp"],
            "base": random_company["base"],
            "rsu": random_company["rsu"],
            "bonus": random_company["bonus"],
            "eng_size": random_company["eng_size"],
            "total_size": random_company["total_size"],
        }

        # Apply business rules
        if company["type"] in ["private", "private finance"]:
            # Private companies shouldn't have RSUs
            company["rsu"] = 0

        if company["type"] == "private finance":
            # Finance companies should have higher random bonuses
            company["bonus"] = max(company["bonus"], random.randint(50000, 200000))

        # Recalculate total comp to ensure it matches components
        company["total_comp"] = company["base"] + company["rsu"] + company["bonus"]

        return company

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies using hybrid approach."""
        return [self.generate_company() for _ in range(n)]
