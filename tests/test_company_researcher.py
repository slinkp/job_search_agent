"""
Test the company_researcher module.
"""

import json
from unittest import mock

import pytest

from company_researcher import TavilyRAGResearchAgent


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
