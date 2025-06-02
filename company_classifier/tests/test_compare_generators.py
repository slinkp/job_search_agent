import csv
import json
import os
import types
from unittest.mock import patch

import pytest

from company_classifier.compare_generators import (
    generate_test_batch,
    get_model_info,
    process_companies_file,
)


def test_get_model_info():
    """Test model info lookup for both short and full names."""
    # Test short names
    assert get_model_info("haiku") == ("claude-3-5-haiku-latest", "anthropic")
    assert get_model_info("gpt-4-turbo") == ("gpt-4-turbo-preview", "openai")

    # Test full names
    assert get_model_info("claude-3-5-haiku-latest") == (
        "claude-3-5-haiku-latest",
        "anthropic",
    )
    assert get_model_info("gpt-4-turbo-preview") == ("gpt-4-turbo-preview", "openai")

    # Test invalid model
    with pytest.raises(ValueError):
        get_model_info("invalid-model")


def test_generate_test_batch_random(tmp_path):
    """Test generating a test batch with random generator."""
    output_file = generate_test_batch(
        generator_type="random",
        num_companies=2,
        output_dir=str(tmp_path),
    )

    assert os.path.exists(output_file)
    assert output_file.endswith("_test_batch.csv")

    # Check file contents
    with open(output_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 3  # Header + 2 companies


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"})
def test_generate_test_batch_llm(tmp_path):
    """Test generating a test batch with LLM generator."""
    # Mock the LLM response
    mock_response = {
        "company_id": "synthetic-llm-0001",
        "name": "Test Corp",
        "type": "public",
        "valuation": 1000000000,
        "total_comp": 350000,
        "base": 200000,
        "rsu": 120000,
        "bonus": 30000,
        "remote_policy": "remote first",
        "eng_size": 200,
        "total_size": 2000,
        "headquarters": "New York",
        "ny_address": "123 Test Ave",
        "ai_notes": "AI-driven product",
        "fit_category": "good",
        "fit_confidence": 0.8,
    }

    def mock_openai_chat_completion_create(*args, **kwargs):
        class MockResponse:
            class Choice:
                def __init__(self, content):
                    self.message = types.SimpleNamespace(
                        content=json.dumps(mock_response)
                    )

            def __init__(self, content):
                self.choices = [self.Choice(content)]

        return MockResponse(json.dumps(mock_response))

    with patch(
        "openai.resources.chat.completions.Completions.create",
        side_effect=mock_openai_chat_completion_create,
    ):
        output_file = generate_test_batch(
            generator_type="llm",
            num_companies=2,
            model="gpt-4-turbo",
            output_dir=str(tmp_path),
        )

    assert os.path.exists(output_file)
    assert output_file.endswith("_test_batch.csv")

    # Check file contents
    with open(output_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 3  # Header + 2 companies


def test_process_companies_file(tmp_path):
    """Test processing a CSV file of companies."""
    # Create a test CSV file
    csv_file = tmp_path / "test_companies.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_id",
                "name",
                "type",
                "valuation",
                "total_comp",
                "base",
                "rsu",
                "bonus",
                "remote_policy",
                "eng_size",
                "total_size",
                "headquarters",
                "ny_address",
                "ai_notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "company_id": "test-1",
                "name": "Test Corp 1",
                "type": "public",
                "valuation": "1000000",
                "total_comp": "350000",
                "base": "200000",
                "rsu": "120000",
                "bonus": "30000",
                "remote_policy": "remote first",
                "eng_size": "200",
                "total_size": "2000",
                "headquarters": "New York",
                "ny_address": "123 Test Ave",
                "ai_notes": "AI-driven product",
            }
        )
        writer.writerow(
            {
                "company_id": "test-2",
                "name": "Test Corp 2",
                "type": "private",
                "valuation": "",
                "total_comp": "250000",
                "base": "180000",
                "rsu": "",
                "bonus": "70000",
                "remote_policy": "hybrid",
                "eng_size": "150",
                "total_size": "500",
                "headquarters": "San Francisco",
                "ny_address": "",
                "ai_notes": "",
            }
        )

    # Process the file
    companies = process_companies_file(str(csv_file))

    # Check results
    assert len(companies) == 2

    # Check first company
    assert companies[0]["company_id"] == "test-1"
    assert companies[0]["valuation"] == 1000000.0
    assert companies[0]["total_comp"] == 350000.0
    assert companies[0]["base"] == 200000.0
    assert companies[0]["rsu"] == 120000.0
    assert companies[0]["bonus"] == 30000.0
    assert companies[0]["eng_size"] == 200.0
    assert companies[0]["total_size"] == 2000.0

    # Check second company
    assert companies[1]["company_id"] == "test-2"
    assert companies[1]["valuation"] is None
    assert companies[1]["total_comp"] == 250000.0
    assert companies[1]["base"] == 180000.0
    assert companies[1]["rsu"] is None
    assert companies[1]["bonus"] == 70000.0
    assert companies[1]["eng_size"] == 150.0
    assert companies[1]["total_size"] == 500.0
