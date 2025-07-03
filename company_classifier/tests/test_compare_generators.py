import csv
import json
import os
import types
from io import StringIO
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
    assert get_model_info("haiku-3.5") == ("claude-3-5-haiku-20241022", "anthropic")
    assert get_model_info("gpt-4-turbo") == ("gpt-4-turbo-2024-04-09", "openai")

    # Test full names
    assert get_model_info("claude-3-5-haiku-20241022") == (
        "claude-3-5-haiku-20241022",
        "anthropic",
    )
    assert get_model_info("gpt-4-turbo-2024-04-09") == (
        "gpt-4-turbo-2024-04-09",
        "openai",
    )

    # Test dash/dot variations
    assert get_model_info("haiku-3-5") == ("claude-3-5-haiku-20241022", "anthropic")
    assert get_model_info("gpt.4.turbo") == ("gpt-4-turbo-2024-04-09", "openai")

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


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"})
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

    # Create mock response JSON once to avoid circular references
    response_json = json.dumps({"companies": [mock_response, mock_response]})

    # Patch both OpenAI and Anthropic
    with patch("company_classifier.synthetic_data.OpenAI") as MockOpenAI, patch(
        "company_classifier.synthetic_data.Anthropic"
    ) as MockAnthropic:

        # Set up OpenAI mock
        mock_openai_client = MockOpenAI.return_value
        mock_openai_chat = mock_openai_client.chat
        mock_openai_completions = mock_openai_chat.completions

        # Set up simple mock response for OpenAI
        mock_openai_message = types.SimpleNamespace(content=response_json)
        mock_openai_choice = types.SimpleNamespace(message=mock_openai_message)
        mock_openai_response = types.SimpleNamespace(choices=[mock_openai_choice])
        mock_openai_completions.create.return_value = mock_openai_response

        # Set up Anthropic mock
        mock_anthropic_client = MockAnthropic.return_value
        mock_anthropic_messages = mock_anthropic_client.messages

        # Set up simple mock response for Anthropic
        mock_content_block = types.SimpleNamespace(text=response_json)
        mock_anthropic_response = types.SimpleNamespace(content=[mock_content_block])
        mock_anthropic_messages.create.return_value = mock_anthropic_response

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


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"})
def test_batch_size_parameter_passed_to_hybrid_generator(tmp_path):
    """Test that batch_size parameter is correctly passed to Hybrid generator."""
    # Mock the LLM response
    mock_response = {
        "company_id": "synthetic-hybrid-0001",
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

    # Create mock response JSON once to avoid circular references
    response_json = json.dumps({"companies": [mock_response, mock_response]})

    # Use mock.patch to check if HybridCompanyGenerator is initialized with correct batch_size
    with patch(
        "company_classifier.compare_generators.HybridCompanyGenerator", autospec=True
    ) as mock_hybrid_gen, patch(
        "company_classifier.synthetic_data.OpenAI"
    ) as MockOpenAI, patch(
        "company_classifier.synthetic_data.Anthropic"
    ) as MockAnthropic:

        # Set up the mock to return a generator that produces mock companies
        mock_instance = mock_hybrid_gen.return_value
        mock_instance.generate_companies.return_value = [mock_response, mock_response]

        # Set up OpenAI mock
        mock_openai_client = MockOpenAI.return_value
        mock_openai_chat = mock_openai_client.chat
        mock_openai_completions = mock_openai_chat.completions

        # Set up simple mock response for OpenAI
        mock_openai_message = types.SimpleNamespace(content=response_json)
        mock_openai_choice = types.SimpleNamespace(message=mock_openai_message)
        mock_openai_response = types.SimpleNamespace(choices=[mock_openai_choice])
        mock_openai_completions.create.return_value = mock_openai_response

        # Set up Anthropic mock
        mock_anthropic_client = MockAnthropic.return_value
        mock_anthropic_messages = mock_anthropic_client.messages

        # Set up simple mock response for Anthropic
        mock_content_block = types.SimpleNamespace(text=response_json)
        mock_anthropic_response = types.SimpleNamespace(content=[mock_content_block])
        mock_anthropic_messages.create.return_value = mock_anthropic_response

        # Call generate_test_batch with a specific batch_size
        test_batch_size = 7
        output_file = generate_test_batch(
            generator_type="hybrid",
            num_companies=2,
            model="gpt-4-turbo",
            output_dir=str(tmp_path),
            batch_size=test_batch_size,
        )

        # Verify HybridCompanyGenerator was initialized with the correct batch_size
        mock_hybrid_gen.assert_called_once()
        call_kwargs = mock_hybrid_gen.call_args.kwargs
        assert "batch_size" in call_kwargs
        assert call_kwargs["batch_size"] == test_batch_size


def test_batch_size_included_in_output_filename(tmp_path):
    """Test that batch_size is included in the output filename."""
    # Mock the generate_companies method to avoid actual generation
    with patch(
        "company_classifier.compare_generators.LLMCompanyGenerator", autospec=True
    ) as mock_llm_gen, patch(
        "company_classifier.synthetic_data.OpenAI"
    ) as MockOpenAI, patch(
        "company_classifier.synthetic_data.Anthropic"
    ) as MockAnthropic:

        mock_instance = mock_llm_gen.return_value
        # Include all required fields for the company data
        mock_instance.generate_companies.return_value = [
            {
                "name": "Test Corp",
                "company_id": "test-001",
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
        ]

        # Create mock response JSON once to avoid circular references
        response_json = json.dumps({"companies": [{"dummy": "response"}]})

        # Set up OpenAI mock
        mock_openai_client = MockOpenAI.return_value
        mock_openai_chat = mock_openai_client.chat
        mock_openai_completions = mock_openai_chat.completions

        # Set up simple mock response for OpenAI
        mock_openai_message = types.SimpleNamespace(content=response_json)
        mock_openai_choice = types.SimpleNamespace(message=mock_openai_message)
        mock_openai_response = types.SimpleNamespace(choices=[mock_openai_choice])
        mock_openai_completions.create.return_value = mock_openai_response

        # Set up Anthropic mock
        mock_anthropic_client = MockAnthropic.return_value
        mock_anthropic_messages = mock_anthropic_client.messages

        # Set up simple mock response for Anthropic
        mock_content_block = types.SimpleNamespace(text=response_json)
        mock_anthropic_response = types.SimpleNamespace(content=[mock_content_block])
        mock_anthropic_messages.create.return_value = mock_anthropic_response

        # Test with different batch sizes
        batch_size_5 = generate_test_batch(
            generator_type="llm",
            num_companies=1,
            model="gpt-4-turbo",
            output_dir=str(tmp_path),
            batch_size=5,
        )

        batch_size_10 = generate_test_batch(
            generator_type="llm",
            num_companies=1,
            model="gpt-4-turbo",
            output_dir=str(tmp_path),
            batch_size=10,
        )

        # Check that batch size is in the filenames
        assert "batch5" in batch_size_5
        assert "batch10" in batch_size_10
        assert batch_size_5 != batch_size_10


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"})
def test_batch_size_validation():
    """Test that batch_size is properly validated."""
    # Import here to avoid circular imports
    from company_classifier.compare_generators import main

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

    # Create mock response JSON once to avoid circular references
    response_json = json.dumps({"companies": [mock_response, mock_response]})

    # Mock the LLMCompanyGenerator and HybridCompanyGenerator classes
    llm_gen_patch = patch(
        "company_classifier.compare_generators.LLMCompanyGenerator", autospec=True
    )
    hybrid_gen_patch = patch(
        "company_classifier.compare_generators.HybridCompanyGenerator", autospec=True
    )
    openai_patch = patch("company_classifier.synthetic_data.OpenAI")
    anthropic_patch = patch("company_classifier.synthetic_data.Anthropic")

    # Mock parser.parse_args to return args with specific batch_size
    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args, patch(
        "sys.exit"
    ) as mock_exit, llm_gen_patch as mock_llm_gen, hybrid_gen_patch as mock_hybrid_gen, openai_patch as MockOpenAI, anthropic_patch as MockAnthropic:

        # Set up mocks to return test companies
        mock_llm_instance = mock_llm_gen.return_value
        mock_llm_instance.generate_companies.return_value = [mock_response, mock_response]
        mock_hybrid_instance = mock_hybrid_gen.return_value
        mock_hybrid_instance.generate_companies.return_value = [
            mock_response,
            mock_response,
        ]

        # Set up OpenAI mock
        mock_openai_client = MockOpenAI.return_value
        mock_openai_chat = mock_openai_client.chat
        mock_openai_completions = mock_openai_chat.completions

        # Set up simple mock response for OpenAI
        mock_openai_message = types.SimpleNamespace(content=response_json)
        mock_openai_choice = types.SimpleNamespace(message=mock_openai_message)
        mock_openai_response = types.SimpleNamespace(choices=[mock_openai_choice])
        mock_openai_completions.create.return_value = mock_openai_response

        # Set up Anthropic mock
        mock_anthropic_client = MockAnthropic.return_value
        mock_anthropic_messages = mock_anthropic_client.messages

        # Set up simple mock response for Anthropic
        mock_content_block = types.SimpleNamespace(text=response_json)
        mock_anthropic_response = types.SimpleNamespace(content=[mock_content_block])
        mock_anthropic_messages.create.return_value = mock_anthropic_response

        # Valid batch size
        args = types.SimpleNamespace(
            batch_size=15,
            models=["gpt-4.1-mini"],
            generator="all",
            num_companies=1,
            output_dir="test_dir",
        )
        mock_parse_args.return_value = args

        # Reset mock_exit
        mock_exit.reset_mock()

        # Should not exit for valid batch size
        with patch(
            "company_classifier.compare_generators.generate_test_batch"
        ) as mock_generate:
            mock_generate.return_value = "test.csv"
            with patch(
                "company_classifier.compare_generators.process_companies_file"
            ) as mock_process:
                mock_process.return_value = []
                with patch(
                    "company_classifier.compare_generators.calculate_diversity_score"
                ) as mock_score:
                    mock_score.return_value = {}
                    with patch("os.path.join", return_value="test_results.json"):
                        with patch("builtins.open", create=True):
                            with patch("json.dump"):
                                main()
                                mock_exit.assert_not_called()

        # Invalid small batch size
        args = types.SimpleNamespace(
            batch_size=0,  # Too small
            models=["gpt-4.1-mini"],
            generator="all",
            num_companies=1,
            output_dir="test_dir",
        )
        mock_parse_args.return_value = args

        # Reset mock_exit
        mock_exit.reset_mock()

        # Should exit for invalid batch size
        with patch("sys.stderr", new=StringIO()):
            main()
            mock_exit.assert_called_once()

        # Invalid large batch size
        args = types.SimpleNamespace(
            batch_size=25,  # Too large
            models=["gpt-4.1-mini"],
            generator="all",
            num_companies=1,
            output_dir="test_dir",
        )
        mock_parse_args.return_value = args

        # Reset mock_exit
        mock_exit.reset_mock()

        # Should exit for invalid batch size
        with patch("sys.stderr", new=StringIO()):
            main()
            mock_exit.assert_called_once()


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant-test"})
def test_batch_size_parameter_passed_to_llm_generator(tmp_path):
    """Test that batch_size parameter is correctly passed to LLM generator."""
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

    # Create mock response JSON once to avoid circular references
    response_json = json.dumps({"companies": [mock_response, mock_response]})

    # Use mock.patch to check if LLMCompanyGenerator is initialized with correct batch_size
    with patch(
        "company_classifier.compare_generators.LLMCompanyGenerator", autospec=True
    ) as mock_llm_gen, patch(
        "company_classifier.synthetic_data.OpenAI"
    ) as MockOpenAI, patch(
        "company_classifier.synthetic_data.Anthropic"
    ) as MockAnthropic:

        # Set up the mock to return a generator that produces mock companies
        mock_instance = mock_llm_gen.return_value
        mock_instance.generate_companies.return_value = [mock_response, mock_response]

        # Set up OpenAI mock
        mock_openai_client = MockOpenAI.return_value
        mock_openai_chat = mock_openai_client.chat
        mock_openai_completions = mock_openai_chat.completions

        # Set up simple mock response for OpenAI
        mock_openai_message = types.SimpleNamespace(content=response_json)
        mock_openai_choice = types.SimpleNamespace(message=mock_openai_message)
        mock_openai_response = types.SimpleNamespace(choices=[mock_openai_choice])
        mock_openai_completions.create.return_value = mock_openai_response

        # Set up Anthropic mock
        mock_anthropic_client = MockAnthropic.return_value
        mock_anthropic_messages = mock_anthropic_client.messages

        # Set up simple mock response for Anthropic
        mock_content_block = types.SimpleNamespace(text=response_json)
        mock_anthropic_response = types.SimpleNamespace(content=[mock_content_block])
        mock_anthropic_messages.create.return_value = mock_anthropic_response

        # Call generate_test_batch with a specific batch_size
        test_batch_size = 10
        output_file = generate_test_batch(
            generator_type="llm",
            num_companies=2,
            model="gpt-4-turbo",
            output_dir=str(tmp_path),
            batch_size=test_batch_size,
        )

        # Verify LLMCompanyGenerator was initialized with the correct batch_size
        mock_llm_gen.assert_called_once()
        call_kwargs = mock_llm_gen.call_args.kwargs
        assert "batch_size" in call_kwargs
        assert call_kwargs["batch_size"] == test_batch_size
