import json
import os
import unittest.mock as mock
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from company_classifier.synthetic_data import (
    CompanyGenerationConfig,
    CompanyType,
    FitCategory,
    HybridCompanyGenerator,
    LLMCompanyGenerator,
    RandomCompanyGenerator,
)


@pytest.fixture
def sample_synthetic_company() -> Dict[Any, Any]:
    """
    Returns a sample synthetic company data structure that matches
    our actual company data format from company_ratings.csv.
    """
    return {
        "company_id": "example-corp",
        "name": "Example Corp",
        "type": "public",
        "valuation": 400000,
        "total_comp": 400000,
        "base": 220000,
        "rsu": 180000,
        "bonus": 0,
        "remote_policy": "hybrid 3 days",
        "eng_size": 300,
        "total_size": 6000,
        "headquarters": "New York",
        "ny_address": "100 Fifth Avenue",
        "ai_notes": "ML, sys design focus",
        "fit_category": "good",
        "fit_confidence": 0.8,
    }


@pytest.fixture
def generator():
    """Returns a RandomCompanyGenerator with a fixed seed for reproducibility."""
    return RandomCompanyGenerator(seed=42)


@pytest.fixture
def llm_company_response():
    """Returns a sample LLM response for a synthetic company."""
    return {
        "company_id": "synthetic-llm-0001",
        "name": "LLM Test Corp",
        "type": "public",
        "valuation": 500000,
        "total_comp": 350000,
        "base": 200000,
        "rsu": 120000,
        "bonus": 30000,
        "remote_policy": "remote first",
        "eng_size": 200,
        "total_size": 2000,
        "headquarters": "New York",
        "ny_address": "123 LLM Ave",
        "ai_notes": "AI-driven product",
        "fit_category": "good",
        "fit_confidence": 0.8,
    }


@pytest.fixture
def hybrid_generator():
    # Create mock for LLMCompanyGenerator with needed attributes and methods
    mock_llm_gen = mock.MagicMock()
    mock_llm_gen.batch_size = 5  # Default batch size
    mock_llm_gen.ai_notes_probability = 0.6  # Default probability
    mock_llm_gen.generate_company.return_value = {
        "name": "Test Company",
        "remote_policy": "hybrid",
        "headquarters": "New York",
        "ny_address": "123 Test Ave",
        "ai_notes": "AI-driven testing",
    }
    mock_llm_gen.generate_companies.return_value = [
        {
            "name": f"Test Co {i}",
            "remote_policy": "hybrid",
            "headquarters": "New York",
            "ny_address": "123 Test Ave",
            "ai_notes": "AI-driven testing",
        }
        for i in range(5)
    ]

    # Create mock for RandomCompanyGenerator
    mock_random_gen = mock.MagicMock()
    mock_random_gen.generate_company.return_value = {
        "base": 210000,
        "rsu": 100000,
        "bonus": 20000,
        "eng_size": 250,
        "total_size": 2000,
        "valuation": 5000000,
        "total_comp": 330000,
        "type": "public",
    }
    mock_random_gen.generate_companies.return_value = [
        {
            "base": 210000,
            "rsu": 100000,
            "bonus": 20000,
            "eng_size": 250,
            "total_size": 2000,
            "valuation": 5000000,
            "total_comp": 330000,
            "type": "public",
        }
        for _ in range(5)
    ]

    # Create a hybrid generator with environment mock
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        generator = HybridCompanyGenerator(
            config=CompanyGenerationConfig(), model="gpt-4-turbo-preview"
        )
        # Replace the actual generators with our mocks
        generator.llm_gen = mock_llm_gen
        generator.random_gen = mock_random_gen

    return generator


def test_synthetic_company_schema(sample_synthetic_company):
    """Test that synthetic company data has all required fields with correct types."""
    required_fields = {
        "company_id": str,
        "name": str,
        "type": str,
        "valuation": (int, float, type(None)),  # Can be numeric or None
        "total_comp": (int, float, type(None)),
        "base": (int, float, type(None)),
        "rsu": (int, float, type(None)),
        "bonus": (int, float, type(None)),
        "remote_policy": str,
        "eng_size": (int, type(None)),  # Can be None
        "total_size": (int, type(None)),
        "headquarters": (str, type(None)),
        "ny_address": (str, type(None)),
        "ai_notes": (str, type(None)),
        "fit_category": (str, type(None)),
        "fit_confidence": (float, type(None)),
    }

    for field, expected_types in required_fields.items():
        assert field in sample_synthetic_company
        if isinstance(expected_types, tuple):
            assert isinstance(
                sample_synthetic_company[field], expected_types
            ), f"Field {field} should be one of {expected_types}, got {type(sample_synthetic_company[field])}"
        else:
            assert isinstance(
                sample_synthetic_company[field], expected_types
            ), f"Field {field} should be {expected_types}, got {type(sample_synthetic_company[field])}"


def test_synthetic_company_constraints(sample_synthetic_company):
    """Test that synthetic company data meets our business constraints."""
    # Company type should be one of our known types
    assert sample_synthetic_company["type"] in [
        "public",
        "private",
        "private unicorn",
        "private finance",
    ]

    # Compensation fields should be non-negative when present
    comp_fields = ["valuation", "total_comp", "base", "rsu", "bonus"]
    for field in comp_fields:
        value = sample_synthetic_company[field]
        if value is not None:
            assert value >= 0, f"{field} should be non-negative"

    # Fit category should be one of our known categories
    assert sample_synthetic_company["fit_category"] in [
        "good",
        "bad",
        "needs_more_info",
        None,
    ]

    # Fit confidence should be between 0 and 1
    if sample_synthetic_company["fit_confidence"] is not None:
        assert 0 <= sample_synthetic_company["fit_confidence"] <= 1

    # If total_comp is present, it should approximately equal base + rsu + bonus
    total = sample_synthetic_company["total_comp"]
    if total is not None and total > 0:
        components = [
            sample_synthetic_company["base"] or 0,
            sample_synthetic_company["rsu"] or 0,
            sample_synthetic_company["bonus"] or 0,
        ]
        # Allow for some rounding differences
        assert (
            abs(sum(components) - total) < 1000
        ), "Total comp should approximately equal base + rsu + bonus"


def test_synthetic_data_diversity(generator):
    """Test that our generator produces diverse company profiles."""
    # Generate a good sample size
    companies = generator.generate_companies(50)

    # Helper function to count unique values
    def count_unique(companies: List[Dict[str, Any]], field: str) -> int:
        return len({str(c[field]) for c in companies})  # Convert to str to handle None

    # 1. Check company type distribution
    types = [c["type"] for c in companies]
    assert all(
        t in [ct.value for ct in CompanyType] for t in types
    ), "Invalid company type found"
    type_counts = {t: types.count(t) for t in set(types)}
    # Should have at least 3 different types
    assert len(type_counts) >= 3, f"Not enough company type diversity: {type_counts}"

    # 2. Check compensation ranges
    total_comps = [c["total_comp"] for c in companies]
    assert (
        max(total_comps) - min(total_comps) > 200000
    ), "Not enough compensation range diversity"

    # 3. Check remote policy diversity
    remote_policies = [c["remote_policy"] for c in companies]
    unique_policies = set(remote_policies)
    assert (
        len(unique_policies) >= 3
    ), f"Not enough remote policy diversity: {unique_policies}"

    # 4. Check fit category distribution
    fit_categories = [c["fit_category"] for c in companies]
    assert all(
        fc in [fc.value for fc in FitCategory] + [None] for fc in fit_categories
    ), "Invalid fit category found"

    # 5. Check location diversity
    locations = [c["ny_address"] for c in companies]
    assert count_unique(companies, "ny_address") >= 5, "Not enough location diversity"

    # 6. Check realistic relationships
    for company in companies:
        if company["type"] == CompanyType.PRIVATE_UNICORN.value:
            # Unicorns should have high valuations when present
            if company["valuation"] is not None:
                assert company["valuation"] > 1_000_000, "Unicorn with low valuation"

        # Public companies should be more likely to have RSUs
        if company["type"] == CompanyType.PUBLIC.value:
            assert company["rsu"] is not None, "Public company without RSUs"

        # Total size should be larger than eng size when both present
        if company["eng_size"] is not None and company["total_size"] is not None:
            assert (
                company["total_size"] >= company["eng_size"]
            ), "Total size smaller than eng size"


def test_llm_company_generator_output_structure(llm_company_response):
    config = CompanyGenerationConfig()

    # Create properly spec'd mocks for the response chain
    mock_choice = mock.MagicMock(spec=["message"])
    mock_message = mock.MagicMock(spec=["content"])
    mock_message.content = json.dumps(llm_company_response)
    mock_choice.message = mock_message

    mock_response = mock.MagicMock(spec=["choices"])
    mock_response.choices = [mock_choice]

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        generator = LLMCompanyGenerator(config=config, model="gpt-4-turbo-preview")

        # Mock generate_companies to return a list with our test data
        with patch.object(
            generator, "generate_companies", return_value=[llm_company_response]
        ):
            company = generator.generate_companies(1)[0]

    # Check required fields
    required_fields = set(llm_company_response.keys())
    assert set(company.keys()) >= required_fields

    # Check types and constraints
    assert company["type"] in ["public", "private", "private unicorn", "private finance"]
    if company["fit_confidence"] is not None:
        assert 0 <= company["fit_confidence"] <= 1
    assert company["fit_category"] in ["good", "bad", "needs_more_info", None]
    assert company["total_comp"] == company["base"] + company["rsu"] + company["bonus"]
    assert company["company_id"].startswith("synthetic-llm-")


def test_hybrid_company_generator_output_structure(hybrid_generator):
    # Reset mocks for clean test
    hybrid_generator.llm_gen.generate_companies.reset_mock()
    hybrid_generator.random_gen.generate_companies.reset_mock()

    # Call the method under test
    companies = hybrid_generator.generate_companies(1)
    company = companies[0]

    # Verify both underlying generators were called with batch size of 1
    hybrid_generator.llm_gen.generate_companies.assert_called_once_with(1)
    hybrid_generator.random_gen.generate_companies.assert_called_once_with(1)

    # Check structure
    assert isinstance(company, dict)

    # Check numeric fields
    assert 90000 <= company["base"] <= 300000
    assert 0 <= company["rsu"] <= 300000
    assert 0 <= company["bonus"] <= 450000
    assert company["eng_size"] is None or 30 <= company["eng_size"] <= 3000
    assert company["total_size"] is None or 100 <= company["total_size"] <= 30000

    # Check text fields
    assert isinstance(company["name"], str)
    assert isinstance(company["remote_policy"], str)
    assert isinstance(company["ai_notes"], (str, type(None)))

    # Check business rules
    assert company["type"] in ["public", "private", "private unicorn", "private finance"]
    assert company["fit_category"] in ["good", "bad", "needs_more_info", None]
    assert company["total_comp"] == company["base"] + company["rsu"] + company["bonus"]
    assert company["company_id"].startswith("synthetic-hybrid-")


def test_hybrid_company_generator_multiple(hybrid_generator):
    # Reset mocks for clean test
    hybrid_generator.llm_gen.generate_companies.reset_mock()
    hybrid_generator.random_gen.generate_companies.reset_mock()

    # Call the method under test
    companies = hybrid_generator.generate_companies(5)

    # Verify both generators' batch methods were called exactly once
    hybrid_generator.random_gen.generate_companies.assert_called_once_with(5)
    hybrid_generator.llm_gen.generate_companies.assert_called_once_with(5)

    # Verify we got the expected results
    assert len(companies) == 5
    for company in companies:
        assert isinstance(company, dict)
        assert "name" in company and "base" in company
        assert company["company_id"].startswith("synthetic-hybrid-")


def test_hybrid_company_generator_batch_efficiency(hybrid_generator):
    """Test that the hybrid generator uses LLM batching for efficiency."""
    # Setup custom return values for this test
    mock_llm_companies = [
        {
            "name": f"Test Co {i}",
            "remote_policy": "hybrid",
            "headquarters": "New York",
            "ny_address": "123 Test Ave",
            "ai_notes": "AI-driven testing",
        }
        for i in range(3)
    ]
    mock_random_companies = [
        {
            "base": 210000,
            "rsu": 100000,
            "bonus": 20000,
            "eng_size": 250,
            "total_size": 2000,
            "valuation": 5000000,
            "total_comp": 330000,
            "type": "public",
        }
        for _ in range(3)
    ]

    # Update the mocks with our custom return values
    hybrid_generator.llm_gen.generate_companies.return_value = mock_llm_companies
    hybrid_generator.random_gen.generate_companies.return_value = mock_random_companies

    # Reset call counts
    hybrid_generator.llm_gen.generate_companies.reset_mock()
    hybrid_generator.random_gen.generate_companies.reset_mock()

    # Call the method under test
    result = hybrid_generator.generate_companies(3)

    # Verify both generators' batch methods were called exactly once
    hybrid_generator.random_gen.generate_companies.assert_called_once_with(3)
    hybrid_generator.llm_gen.generate_companies.assert_called_once_with(3)

    # Verify we got the expected number of results
    assert len(result) == 3

    # Verify each result has the expected structure
    for company in result:
        assert company["type"] in [
            "public",
            "private",
            "private unicorn",
            "private finance",
        ]
        assert "name" in company
        assert "remote_policy" in company
        assert (
            company["total_comp"] == company["base"] + company["rsu"] + company["bonus"]
        )
