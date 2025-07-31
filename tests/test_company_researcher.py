"""
Test the company_researcher module.
"""

import json
from unittest import mock

import pytest

from company_researcher import TavilyRAGResearchAgent, is_placeholder


class TestTavilyRAGResearchAgent:

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_extract_json_from_response_raw_json(self):
        """Test extracting JSON from raw JSON response."""
        # Use a mock LLM to avoid needing API keys
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)
        test_json = '{"key": "value", "number": 123}'

        result = agent.extract_json_from_response(test_json)
        assert result == {"key": "value", "number": 123}

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_extract_json_from_response_markdown_json(self):
        """Test extracting JSON from markdown code blocks."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)
        test_input = """```json
{
  "remote_work_policy": "hybrid",
  "hiring_status": true,
  "hiring_status_ai": true,
  "jobs_homepage_url": "https://job-boards.greenhouse.io/gusto"
}
```"""

        expected = {
            "remote_work_policy": "hybrid",
            "hiring_status": True,
            "hiring_status_ai": True,
            "jobs_homepage_url": "https://job-boards.greenhouse.io/gusto",
        }

        result = agent.extract_json_from_response(test_input)
        assert result == expected

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_extract_json_from_response_generic_markdown(self):
        """Test extracting JSON from generic markdown code blocks."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)
        test_input = """```
{
  "company_name": "Test Company",
  "status": "public"
}
```"""

        expected = {"company_name": "Test Company", "status": "public"}

        result = agent.extract_json_from_response(test_input)
        assert result == expected

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_extract_json_from_response_whitespace_handling(self):
        """Test that whitespace around input is handled correctly."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)
        test_input = '  \n{"test": "value"}  \n  '

        result = agent.extract_json_from_response(test_input)
        assert result == {"test": "value"}

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_extract_json_from_response_invalid_json(self):
        """Test that invalid JSON raises appropriate error."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)
        test_input = '{"invalid": json}'

        with pytest.raises(json.JSONDecodeError):
            agent.extract_json_from_response(test_input)


class TestIsPlaceholder:

    def test_is_placeholder_company_from_variations(self):
        """Test detection of 'Company from' placeholder patterns."""
        assert is_placeholder("Company from email")
        assert is_placeholder("company from somewhere")
        assert is_placeholder("Company from LinkedIn")
        assert is_placeholder("Company from recruiter message")

    def test_is_placeholder_unknown_variations(self):
        """Test detection of '<UNKNOWN' placeholder patterns."""
        assert is_placeholder("<UNKNOWN>")
        assert is_placeholder("<unknown company>")
        assert is_placeholder("<UNKNOWN - no info>")
        assert is_placeholder("<unknown>")

    def test_is_placeholder_case_insensitive(self):
        """Test placeholder detection is case insensitive."""
        assert is_placeholder("COMPANY FROM EMAIL")
        assert is_placeholder("<UNKNOWN>")
        assert is_placeholder("Unknown")
        assert is_placeholder("PLACEHOLDER")

    def test_is_placeholder_whitespace_handling(self):
        """Test placeholder detection handles leading/trailing whitespace."""
        assert is_placeholder("  Company from email  ")
        assert is_placeholder("\t<unknown>\n")
        assert is_placeholder("  unknown  ")
        assert is_placeholder("")

    def test_is_placeholder_none_and_empty(self):
        """Test placeholder detection handles None and empty values."""
        assert is_placeholder(None)
        assert is_placeholder("")
        assert is_placeholder("   ")

    def test_is_placeholder_non_placeholder_names(self):
        """Test that legitimate company names are not flagged as placeholders."""
        assert not is_placeholder("Google")
        assert not is_placeholder("Microsoft Corporation")
        assert not is_placeholder("Acme Inc")
        assert not is_placeholder("Tech Startup 2024")
        assert not is_placeholder("Some Company LLC")

    def test_is_placeholder_exact_matches(self):
        """Test exact placeholder matches."""
        assert is_placeholder("unknown")
        assert is_placeholder("placeholder")
        assert not is_placeholder("unknown company")  # Not exact match
        assert not is_placeholder("placeholder inc")  # Not exact match


class TestUpdateCompanyInfoFromDict:

    def test_update_company_name_from_blank(self):
        """Test that company name is updated when current name is blank."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="", company_identifier="test")
        content = {"company_name": "Google Inc"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Google Inc"

    def test_update_company_name_from_placeholder(self):
        """Test that company name is updated when current name is a placeholder."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "Microsoft"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Microsoft"

    def test_dont_update_company_name_with_placeholder(self):
        """Test that company name is not updated when new name is a placeholder."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Google", company_identifier="test")
        content = {"company_name": "Company from LinkedIn"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Google"

    def test_update_basic_fields(self):
        """Test that basic fields are updated correctly."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Test", company_identifier="test")
        content = {
            "nyc_office_address": "123 NYC St, New York, NY 10001",
            "headquarters_city": "San Francisco, CA, USA",
            "total_engineers": 500,
            "total_employees": 2000,
        }

        agent.update_company_info_from_dict(company, content)
        assert company.ny_address == "123 nyc st, new york, ny 10001"
        assert company.headquarters == "san francisco, ca, usa"
        assert company.eng_size == 500
        assert company.total_size == 2000

    def test_ignore_empty_values(self):
        """Test that empty or null values are ignored."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(
            name="Test", ny_address="existing", company_identifier="test"
        )
        content = {"nyc_office_address": ""}

        agent.update_company_info_from_dict(company, content)
        assert company.ny_address == "existing"
