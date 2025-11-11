"""
Test the company_researcher module.
"""

import json
from unittest import mock

import pytest

from models import CompaniesSheetRow
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

    def test_ignore_notion_host_name(self):
        """Test that company name is not updated when research returns 'Notion'."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "Notion"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Company from email"  # Should not be changed to "Notion"

    def test_ignore_linkedin_host_name(self):
        """Test that company name is not updated when research returns 'LinkedIn'."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Tech Startup", company_identifier="test")
        content = {"company_name": "LinkedIn"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Tech Startup"  # Should not be changed

    def test_ignore_notion_host_name_case_insensitive(self):
        """Test that company name is not updated when research returns 'notion' (lowercase)."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Real Company", company_identifier="test")
        content = {"company_name": "notion"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Real Company"  # Should not be changed

    def test_ignore_notion_variations(self):
        """Test that company name is not updated when research returns Notion variations."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Real Company", company_identifier="test")

        # Test various Notion-like variations
        notion_variations = [
            "notion.so",
            "notion.site",
            "notion.com",
            "notion.io",
            "notion.app",
            "NOTION",
            "Notion",
            "NOTION.SO",
            "Notion.so",
        ]

        for variation in notion_variations:
            content = {"company_name": variation}
            agent.update_company_info_from_dict(company, content)
            assert company.name == "Real Company", f"Should not change to '{variation}'"

    def test_ignore_linkedin_variations(self):
        """Test that company name is not updated when research returns LinkedIn variations."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Real Company", company_identifier="test")

        # Test various LinkedIn-like variations
        linkedin_variations = [
            "linkedin.com",
            "linkedin.co",
            "linkedin.io",
            "LINKEDIN",
            "LinkedIn",
            "LINKEDIN.COM",
            "LinkedIn.com",
        ]

        for variation in linkedin_variations:
            content = {"company_name": variation}
            agent.update_company_info_from_dict(company, content)
            assert company.name == "Real Company", f"Should not change to '{variation}'"

    def test_preserve_existing_name_when_research_returns_notion(self):
        """Test that existing valid company name is preserved when research returns 'notion'."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Google Inc", company_identifier="test")
        content = {"company_name": "notion"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Google Inc"  # Should preserve existing valid name

    def test_keep_placeholder_when_research_returns_notion(self):
        """Test that placeholder name remains when research returns 'notion'."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "notion"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Company from email"  # Should keep placeholder

    def test_accept_legitimate_names_containing_notion(self):
        """Test that legitimate company names containing 'notion' are accepted."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()

        # These should be accepted as they're legitimate company names
        legitimate_names = [
            "Notion Labs Inc",
            "Notion Labs",
            "Notion Corporation",
            "Notion Technologies",
            "My Notion Company",
            "Notion Solutions",
            "NotionWorks",
        ]

        for name in legitimate_names:
            # Create fresh company for each test
            company = CompaniesSheetRow(
                name="Company from email", company_identifier="test"
            )
            content = {"company_name": name}
            agent.update_company_info_from_dict(company, content)
            assert company.name == name, f"Should accept legitimate name '{name}'"

    def test_accept_legitimate_names_containing_linkedin(self):
        """Test that legitimate company names containing 'linkedin' are accepted."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()

        # These should be accepted as they're legitimate company names
        legitimate_names = [
            "LinkedIn Corporation",
            "LinkedIn Inc",
            "LinkedIn Technologies",
            "My LinkedIn Company",
            "LinkedIn Solutions",
            "LinkedInWorks",
        ]

        for name in legitimate_names:
            # Create fresh company for each test
            company = CompaniesSheetRow(
                name="Company from email", company_identifier="test"
            )
            content = {"company_name": name}
            agent.update_company_info_from_dict(company, content)
            assert company.name == name, f"Should accept legitimate name '{name}'"

    def test_notion_guardrails_with_other_fields(self):
        """Test that Notion guardrails work correctly when other fields are also updated."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Real Company", company_identifier="test")
        content = {
            "company_name": "notion",
            "headquarters_city": "San Francisco, CA",
            "total_employees": 1000,
        }

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Real Company"  # Should not change
        assert company.headquarters == "san francisco, ca"  # Other fields should update
        assert company.total_size == 1000  # Other fields should update

    def test_linkedin_host_name_case_insensitive(self):
        """Test that company name is not updated when research returns 'linkedin' (lowercase)."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Another Company", company_identifier="test")
        content = {"company_name": "linkedin"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Another Company"  # Should not be changed

    def test_allow_legitimate_company_with_notion_in_name(self):
        """Test that legitimate company names containing 'notion' are still allowed."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "Notion Labs Inc"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Notion Labs Inc"  # Should be allowed

    def test_allow_legitimate_company_with_linkedin_in_name(self):
        """Test that legitimate company names containing 'linkedin' are still allowed."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "LinkedIn Corporation"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "LinkedIn Corporation"  # Should be allowed

    def test_prefer_existing_canonical_name_unless_placeholder(self):
        """Test that existing canonical names are preferred unless they are placeholders."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()

        # Test 1: Existing canonical name should not be replaced
        company = CompaniesSheetRow(name="Google Inc", company_identifier="test")
        content = {"company_name": "Google"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Google Inc"  # Should keep existing canonical name

        # Test 2: Placeholder should be replaced with better name
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "Microsoft Corporation"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Microsoft Corporation"  # Should replace placeholder

        # Test 3: Placeholder should not be replaced with another placeholder
        company = CompaniesSheetRow(name="Company from email", company_identifier="test")
        content = {"company_name": "unknown"}

        agent.update_company_info_from_dict(company, content)
        assert company.name == "Company from email"  # Should keep existing placeholder

    def test_main_happy_path(self):
        """Test main method with recruiter message successfully."""
        from company_researcher import TavilyRAGResearchAgent

        mock_llm = mock.Mock()
        mock_tavily = mock.Mock()

        # Mock LLM responses for extract_initial_company_info
        initial_response_data = json.dumps(
            {
                "company_name": "Acme Corp",
                "company_url": "https://acme.com",
                "role": "Senior Software Engineer",
                "recruiter_name": "John Doe",
                "recruiter_contact": "john@recruiter.com",
            }
        )

        # Mock LLM responses for research prompts
        research_responses = [
            initial_response_data,
            json.dumps(
                {
                    "company_name": "Acme Corp",
                    "headquarters_city": "san francisco, ca, usa",
                    "nyc_office_address": "123 main st, san francisco, ca 94105",
                    "total_employees": 1000,
                    "total_engineers": 200,
                }
            ),
            json.dumps(
                {
                    "remote_work_policy": "hybrid",
                    "hiring_status": True,
                    "hiring_status_ai": True,
                    "jobs_homepage_url": "https://acme.com/careers",
                }
            ),
            json.dumps(
                {
                    "public_status": "private",
                    "valuation": "500m",
                    "funding_series": "series c",
                }
            ),
            json.dumps(
                {"interview_style_systems": True, "interview_style_leetcode": True}
            ),
            json.dumps(
                {
                    "uses_ai": True,
                    "ai_notes": "Uses AI for product recommendations and fraud detection",
                }
            ),
            json.dumps({}),
        ]

        mock_invoke_responses = [
            mock.Mock(spec=["content"], content=text) for text in research_responses
        ]

        mock_llm.invoke.side_effect = mock_invoke_responses

        agent = TavilyRAGResearchAgent(llm=mock_llm)
        agent.tavily_client = mock_tavily
        mock_tavily.get_search_context.return_value = "mock search context"

        # Mock _plaintext_from_url to avoid real web requests
        with mock.patch.object(
            agent,
            "_plaintext_from_url",
            return_value="mock website content",
            autospec=True,
        ):
            message = """
        Hi! I'm John Doe from Recruiters Inc.
        Acme Corp is looking for a Senior Software Engineer.
        Check their careers page at https://acme.com/careers
        Contact me at john@recruiter.com
        """

            with mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
                result = agent.main(message=message)

        assert result.name == "Acme Corp"
        assert result.url == "https://acme.com/careers"
        assert result.headquarters == "san francisco, ca, usa"
        assert result.eng_size == 200
        assert result.total_size == 1000
        assert result.remote_policy == "hybrid"
        assert result.current_state == "25. consider applying"
        assert result.updated is not None

    def test_alternate_names_are_discovered_but_not_replace_canonical(self):
        """Test that alternate names are discovered but don't replace existing canonical names."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Acme Corp")
        content = {"company_name": "Acme Corporation"}

        agent.update_company_info_from_dict(company, content)

        # Should keep existing canonical name, not replace with alternate
        assert company.name == "Acme Corp"  # Should keep existing canonical name

    def test_alternate_names_are_tracked_during_research(self):
        """Test that alternate names are tracked during research process."""
        from models import CompaniesSheetRow

        agent = TavilyRAGResearchAgent()
        company = CompaniesSheetRow(name="Acme Corp")
        content = {"company_name": "Acme Corporation"}

        agent.update_company_info_from_dict(company, content)

        # Should discover alternate name
        discovered_names = agent.get_discovered_alternate_names()
        assert "Acme Corporation" in discovered_names

    @pytest.mark.parametrize("has_url", [True, False])
    def test_research_updates_company_name(self, has_url):
        """Test that research updates the company name when URL is available, or early returns when not."""
        from company_researcher import TavilyRAGResearchAgent

        mock_llm = mock.Mock()
        mock_tavily = mock.Mock()

        # Mock LLM responses
        initial_response_data = json.dumps(
            {
                "company_name": "Company from bobby bobbers",
                "company_url": "https://example.com" if has_url else "",
            }
        )

        research_response = json.dumps(
            {
                "company_name": "New Name",
                "headquarters_city": "New York",
            }
        )

        # Need more mock responses for the research loop
        mock_llm.invoke.side_effect = [
            mock.Mock(spec=["content"], content=initial_response_data),
            mock.Mock(spec=["content"], content=research_response),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
        ]

        with mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
            agent = TavilyRAGResearchAgent(llm=mock_llm)
            agent.tavily_client = mock_tavily
            mock_tavily.get_search_context.return_value = "mock search context"

            with mock.patch.object(
                agent,
                "_plaintext_from_url",
                return_value="mock website content",
                autospec=True,
            ):
                result = agent.main(message="Test message")

        if has_url:
            # Verify the company name was updated when URL is available
            assert result.name == "New Name"
        else:
            # Verify early return with placeholder name when no URL
            assert result.name == "Company from bobby bobbers"

    def test_extract_initial_company_info_basic(self):
        """Test basic extraction of company info from recruiter message."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)

        # Mock LLM response
        expected_response = {
            "company_name": "TechCorp Inc",
            "company_url": "https://techcorp.com",
            "role": "Senior Backend Engineer",
            "recruiter_name": "Jane Smith",
            "recruiter_contact": "jane@recruiter.com",
        }
        mock_llm.invoke.return_value.content = json.dumps(expected_response)

        message = """
        Hi! I'm Jane Smith from Recruiters Inc.
        TechCorp Inc is looking for a Senior Backend Engineer.
        Check out their careers page: https://techcorp.com/careers
        Contact me at jane@recruiter.com
        """

        with mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"}):
            result = agent.extract_initial_company_info(message)

        assert result == expected_response
        mock_llm.invoke.assert_called_once()

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_initial_extraction_uses_non_linkedin_url_content_first(self):
        """When a recruiter message includes a non-LinkedIn URL, fetch that page and use its plaintext for initial extraction before any web search."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)

        # First LLM call (initial extraction) returns minimal JSON
        mock_llm.invoke.side_effect = [
            mock.Mock(
                spec=["content"],
                content=json.dumps(
                    {
                        "company_name": "Example Co",
                        "company_url": "https://example.com",
                    }
                ),
            ),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
        ]

        fetched_plaintext = "THIS IS WEBSITE PLAINTEXT CONTENT"

        # Avoid real Tavily calls
        mock_tavily = mock.Mock()
        mock_tavily.get_search_context.return_value = "mock context"
        agent.tavily_client = mock_tavily

        # Patch _plaintext_from_url so we don't make a network call
        with mock.patch.object(
            agent, "_plaintext_from_url", return_value=fetched_plaintext, autospec=True
        ) as mock_plain:
            message = "Hi — check details here: https://example.com/careers and also my LinkedIn https://www.linkedin.com/in/recruiter"
            result = agent.main(message=message)

        # Ensure we fetched a non-LinkedIn URL (called twice: once for initial, once for redo)
        assert mock_plain.call_count == 2
        # Check that both calls were to non-LinkedIn URLs
        for call_args, _ in mock_plain.call_args_list:
            # When autospec=True on a bound method, first arg is the instance (self)
            fetched_url = call_args[1] if len(call_args) > 1 else call_args[0]
            assert fetched_url.startswith("http")
            assert "linkedin.com" not in fetched_url
            assert "example.com" in fetched_url

        # Ensure at least one prompt included both fetched plaintext and original message context
        prompts = [call_args[0][0] for call_args in mock_llm.invoke.call_args_list]
        assert any(fetched_plaintext in p for p in prompts)
        assert any("Begin email message" in p for p in prompts)

        # Basic sanity on the result (case-insensitive name check)
        assert result.name.lower() == "example co"
        assert result.url == "https://example.com"

    @mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
    def test_ignore_linkedin_only_links_for_initial_fetch(self):
        """If a recruiter message only contains LinkedIn links, do not attempt a URL fetch; use the raw message for initial extraction."""
        mock_llm = mock.Mock()
        agent = TavilyRAGResearchAgent(llm=mock_llm)

        mock_llm.invoke.side_effect = [
            mock.Mock(
                spec=["content"],
                content=json.dumps(
                    {
                        "company_name": "LinkedIn Outreach",
                        "company_url": None,
                    }
                ),
            ),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
            mock.Mock(spec=["content"], content=json.dumps({})),
        ]

        # Avoid real Tavily calls
        mock_tavily = mock.Mock()
        mock_tavily.get_search_context.return_value = "mock context"
        agent.tavily_client = mock_tavily

        with mock.patch.object(
            agent, "_plaintext_from_url", return_value="SHOULD NOT BE USED", autospec=True
        ) as mock_plain:
            message = "Connect with me on LinkedIn: https://linkedin.com/in/foo or https://www.linkedin.com/jobs/view/12345"
            agent.main(message=message)

        # Should not fetch any plaintext since only LinkedIn links are present
        mock_plain.assert_not_called()


@mock.patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key-for-testing"})
def test_update_company_info_from_dict_without_company_name_key_does_not_raise():
    # Issue 79
    agent = TavilyRAGResearchAgent(llm=mock.Mock())

    company = CompaniesSheetRow(name="Existing Co", company_identifier="test")
    content = {
        # Intentionally omit "company_name"
        "headquarters_city": "San Francisco, CA, USA",
    }

    # Should not raise
    agent.update_company_info_from_dict(company, content)

    # Name should remain unchanged; other fields should update (normalized to lowercase)
    assert company.name.lower() == "existing co"
    assert company.headquarters.lower() == "san francisco, ca, usa"

    content = {
        "company_name": None,  # Explicit None should not cause exceptions
        "headquarters_city": "New York, NY, USA",
    }

    # Should not raise
    agent.update_company_info_from_dict(company, content)

    # Name should remain unchanged; other fields should update (normalized to lowercase)
    assert company.name.lower() == "existing co"
    assert company.headquarters.lower() == "new york, ny, usa"
