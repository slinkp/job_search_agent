"""
Synthetic data generation for company classification.
Provides both random and LLM-based approaches for generating test data.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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
    """

    COMPANY_PROMPT = """
    Generate a realistic tech company profile for NYC with the following characteristics:
    
    1. Use realistic compensation ranges for staff software engineers, based on company type and stage
    2. Make remote work policies specific and detailed.
       In-office from 0 days per week (for fully remote companies) to 5
       (for fully onsite companies).
    3. Use real office locations and neighborhoods.
       3a. Most generated companies should have an office in New York City metro area.
       3b. Some may have a headquarters elsewhere in the world, AND a satellite office in NYC.
       3c. Some may have no NYC office.
    4. Include relevant AI/ML notes if applicable: whether and how AI is part of the company's
       product offerings, technical strategy, and/or tech stack.
    5. Ensure all numeric fields are realistic and correlated
    
    Current company type: {company_type}
    Target compensation range: {comp_range}
    
    Format the response as a JSON object matching this structure:
    {
        "company_id": "synthetic-...",
        "name": "...",
        "type": "...",
        "valuation": null or number,
        "total_comp": number,
        "base": number,
        "rsu": number,
        "bonus": number,
        "remote_policy": "...",
        "eng_size": null or number,
        "total_size": null or number,
        "headquarters": "..." or null,
        "ny_address": "...",
        "ai_notes": "..." or null,
        "fit_category": "good" or "bad" or "needs_more_info",
        "fit_confidence": 0.8
    }
    """

    def __init__(self, config: Optional[CompanyGenerationConfig] = None):
        self.config = config or CompanyGenerationConfig()
        # TODO: Initialize LLM client here

    def generate_company(self) -> Dict[str, Any]:
        """Generate a single synthetic company using LLM."""
        # TODO: Implement LLM-based generation
        raise NotImplementedError("LLM generation not yet implemented")

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies using LLM."""
        return [self.generate_company() for _ in range(n)]


class HybridCompanyGenerator:
    """Combines random and LLM approaches for optimal synthetic data generation."""

    def __init__(self, config: Optional[CompanyGenerationConfig] = None):
        self.random_gen = RandomCompanyGenerator(config)
        self.llm_gen = LLMCompanyGenerator(config)

    def generate_company(self) -> Dict[str, Any]:
        """
        Generate a single synthetic company using hybrid approach:
        1. Use random generation for numeric fields
        2. Use LLM for text fields and correlations
        3. Apply business rules to ensure realism
        """
        # TODO: Implement hybrid generation strategy
        raise NotImplementedError("Hybrid generation not yet implemented")

    def generate_companies(self, n: int) -> List[Dict[str, Any]]:
        """Generate multiple synthetic companies using hybrid approach."""
        return [self.generate_company() for _ in range(n)]
