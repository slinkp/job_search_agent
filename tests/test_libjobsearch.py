import argparse
import datetime
import decimal
import logging
import os
from unittest.mock import ANY, MagicMock, patch

import pytest

import libjobsearch
import models
from models import CompaniesSheetRow, Event, EventType, RecruiterMessage


@pytest.fixture
def mock_research_methods():
    """Fixture to mock all research methods."""
    with patch(
        "company_researcher.main", autospec=True
    ) as mock_company_researcher, patch(
        "libjobsearch.levels_searcher.main", autospec=True
    ) as mock_levels_main, patch(
        "libjobsearch.levels_searcher.extract_levels", autospec=True
    ) as mock_levels_extract, patch(
        "libjobsearch.linkedin_searcher.main", autospec=True
    ) as mock_linkedin_main, patch(
        "libjobsearch.run_in_process", autospec=True
    ) as mock_run_in_process, patch(
        "libjobsearch.EmailResponseGenerator", autospec=True
    ) as mock_email_responder_class:

        # Configure run_in_process to just call the function
        mock_run_in_process.side_effect = lambda func, *args, **kwargs: func(
            *args, **kwargs
        )

        # Configure email responder mock
        mock_email_responder = mock_email_responder_class.return_value
        mock_email_responder.generate_reply.return_value = "Test reply"

        yield {
            "company_researcher": mock_company_researcher,
            "levels_main": mock_levels_main,
            "levels_extract": mock_levels_extract,
            "linkedin_main": mock_linkedin_main,
            "run_in_process": mock_run_in_process,
            "email_responder_class": mock_email_responder_class,
        }


@pytest.fixture
def job_search():
    """Fixture to create a JobSearch instance with common args."""
    args = argparse.Namespace(
        model="claude-3-5-sonnet-latest",
        rag_message_limit=20,
        no_cache=True,
    )
    return libjobsearch.JobSearch(
        args,
        loglevel=logging.INFO,
        cache_settings=libjobsearch.CacheSettings(no_cache=True),
    )


@pytest.fixture
def recruiter_message():
    """Fixture to create a test recruiter message."""
    return RecruiterMessage(
        message_id="test123",
        message="Hello, we have a job opportunity at Acme Corp for you.",
        subject="Job Opportunity at Acme Corp",
        sender="recruiter@example.com",
        email_thread_link="https://mail.example.com/thread123",
        thread_id="thread123",
        date=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
    )


@pytest.fixture
def complete_company_info():
    """Fixture to create a complete company info object."""
    return CompaniesSheetRow(
        name="Acme Corp",
        type="Private",
        url="https://acme.com",
        total_comp=decimal.Decimal("450000"),  # High enough to pass fit check
        base=decimal.Decimal("320000"),
        rsu=decimal.Decimal("130000"),
        bonus=decimal.Decimal("0"),
        level_equiv="Staff",
        maybe_referrals="John Doe - Senior Engineer",
        remote_policy="Remote-first",  # Good remote policy
        ai_notes="Leading AI company focused on machine learning and artificial intelligence",  # AI keywords
    )


@pytest.fixture
def basic_company_info():
    """Fixture to create a basic company info object."""
    return CompaniesSheetRow(
        name="Acme Corp",
        type="Private",
        url="https://acme.com",
        remote_policy="Remote-first",  # Good remote policy
        ai_notes="Leading AI company focused on machine learning and artificial intelligence",  # AI keywords
    )


@pytest.fixture
def levels_data():
    """Fixture to create test levels data."""
    return {
        "levels": ["Staff Engineer", "Senior Staff Engineer"],
        "main_data": [
            {
                "level": "Staff Engineer",
                "role": "Staff Engineer",
                "experience": "10+ years",
                "total_comp": 450000,  # High enough to pass fit check
                "equity": 130000,
                "bonus": 0,
                "salary": 320000,
            }
        ],
    }


@pytest.fixture
def linkedin_data():
    """Fixture to create test LinkedIn data."""
    return [
        {
            "name": "John Doe",
            "title": "Senior Engineer",
            "profile_url": "https://linkedin.com/in/john-doe",
        }
    ]


@patch("libjobsearch.email_client.GmailRepliesSearcher", autospec=True)
def test_send_reply_and_archive(mock_gmail_searcher_class):
    """Test that send_reply_and_archive correctly sends an email and archives it."""
    mock_searcher = mock_gmail_searcher_class.return_value
    # Configure the mock to return success
    mock_searcher.send_reply.return_value = True

    # Test sending a reply
    result = libjobsearch.send_reply_and_archive(
        message_id="test-message-id",
        thread_id="test-thread-id",
        reply="This is a test reply",
    )

    # Verify the result
    assert result is True

    # Verify the methods were called correctly
    mock_searcher.send_reply.assert_called_once_with(
        "test-thread-id", "test-message-id", "This is a test reply"
    )
    mock_searcher.label_and_archive_message.assert_called_once_with("test-message-id")


@patch("libjobsearch.email_client.GmailRepliesSearcher", autospec=True)
@patch("models.company_repository", autospec=True)
def test_send_reply_and_archive_creates_event(mock_repo_func, mock_gmail_searcher_class):
    """Test that send_reply_and_archive creates a REPLY_SENT event."""
    # Setup mocks
    mock_searcher = mock_gmail_searcher_class.return_value
    mock_searcher.send_reply.return_value = True

    mock_repo = MagicMock()
    mock_repo_func.return_value = mock_repo

    result = libjobsearch.send_reply_and_archive(
        message_id="test-message-id",
        thread_id="test-thread-id",
        reply="This is a test reply",
        company_id="test-company",
    )

    # Verify the result
    assert result is True

    # Verify an event was created
    mock_repo.create_event.assert_called_once()

    # Get the event that was created
    event_arg = mock_repo.create_event.call_args[0][0]

    # Verify event properties
    assert isinstance(event_arg, Event)
    assert event_arg.company_id == "test-company"
    assert event_arg.event_type == EventType.REPLY_SENT
    assert event_arg.timestamp is not None


@patch("libjobsearch.MainTabCompaniesClient", autospec=True)
def test_upsert_company_in_spreadsheet_update_existing(mock_client_class):
    """Test updating an existing company in spreadsheet."""
    # Setup
    mock_client = mock_client_class.return_value

    # Mock existing rows with one matching company
    existing_company = CompaniesSheetRow(name="Test Company")
    mock_client.read_rows_from_google.return_value = [existing_company]

    # Create test company info and args
    company_info = CompaniesSheetRow(
        name="Test Company", type="Startup", valuation="100M"
    )
    args = argparse.Namespace(sheet="test")

    # Call the function
    libjobsearch.upsert_company_in_spreadsheet(company_info, args)

    # Verify client was created with correct config
    mock_client_class.assert_called_once_with(doc_id=ANY, sheet_id=ANY, range_name=ANY)

    # Verify existing rows were fetched
    mock_client.read_rows_from_google.assert_called_once()

    # Verify row was updated not appended
    mock_client.update_row_partial.assert_called_once_with(
        0, company_info, skip_empty_update_values=True
    )
    mock_client.append_rows.assert_not_called()


@patch("libjobsearch.MainTabCompaniesClient", autospec=True)
def test_upsert_company_in_spreadsheet_add_new(mock_client_class):
    """Test adding a new company to spreadsheet."""
    # Setup
    mock_client = mock_client_class.return_value

    # Mock empty existing rows
    mock_client.read_rows_from_google.return_value = []

    # Create test company info and args
    company_info = CompaniesSheetRow(name="New Company", type="Public", valuation="10B")
    args = argparse.Namespace(sheet="prod")

    # Call the function
    libjobsearch.upsert_company_in_spreadsheet(company_info, args)

    # Verify client was created with correct config
    mock_client_class.assert_called_once_with(doc_id=ANY, sheet_id=ANY, range_name=ANY)

    # Verify existing rows were fetched
    mock_client.read_rows_from_google.assert_called_once()

    # Verify row was appended not updated
    mock_client.append_rows.assert_called_once_with([company_info.as_list_of_str()])
    mock_client.update_row_partial.assert_not_called()


TEST_DB_PATH = "data/_test_libjobsearch.db"


@pytest.fixture(scope="function", autouse=True)
def temp_repo():
    """Ensure we have a clean test database for each test."""
    # Remove the test database if it exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Make sure the directory exists
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)

    # Create a new repository with the test database
    repo = models.CompanyRepository(db_path=TEST_DB_PATH, clear_data=True)

    # Create a test company
    company = models.Company(
        company_id="test-company",
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)

    # Override the singleton for testing
    original_repo = models._company_repository
    models._company_repository = repo

    yield repo

    # Restore the original repository
    models._company_repository = original_repo

    # Clean up after the test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_research_company_creates_event():
    """Test that research_company creates a RESEARCH_COMPLETED event."""
    # Create test args and cache settings
    args = argparse.Namespace(
        model="test-model",
        rag_message_limit=5,
        recruiter_message_limit=1,
        sheet="test",
    )
    cache_settings = libjobsearch.CacheSettings(no_cache=True)

    # Create a JobSearch instance with mocked components
    with patch("libjobsearch.EmailResponseGenerator", autospec=True):
        job_search = libjobsearch.JobSearch(args, logging.INFO, cache_settings)

        # Mock the research methods to avoid actual API calls
        with patch.object(
            job_search, "initial_research_company", autospec=True
        ) as mock_initial:
            with patch.object(
                job_search, "research_compensation", autospec=True
            ) as mock_comp:
                with patch.object(
                    job_search, "research_levels", autospec=True
                ) as mock_levels:
                    with patch.object(
                        job_search, "followup_research_company", autospec=True
                    ) as mock_followup:
                        # Configure mocks
                        company_info = CompaniesSheetRow(name="Test Company")
                        mock_initial.return_value = company_info
                        mock_comp.return_value = company_info
                        mock_followup.return_value = company_info

                        # Call the method
                        result = job_search.research_company(
                            "Test message", model="test-model"
                        )

                        # Verify the result
                        assert result.name == "Test Company"

                        # Check that an event was created
                        repo = models.company_repository()
                        events = repo.get_events(
                            company_id="test-company",
                            event_type=EventType.RESEARCH_COMPLETED,
                        )

                        # Verify we have exactly one event
                        assert len(events) == 1
                        assert events[0].company_id == "test-company"
                        assert events[0].event_type == EventType.RESEARCH_COMPLETED


def test_research_company_with_recruiter_message(
    mock_research_methods,
    job_search,
    recruiter_message,
    complete_company_info,
    levels_data,
    linkedin_data,
):
    """Test creating a company from a recruiter message."""
    # Configure mocks
    mock_research_methods["company_researcher"].return_value = complete_company_info
    mock_research_methods["levels_extract"].return_value = levels_data["levels"]
    mock_research_methods["levels_main"].return_value = levels_data["main_data"]
    mock_research_methods["linkedin_main"].return_value = linkedin_data

    # Research the company
    company = job_search.research_company(
        recruiter_message, model="claude-3-5-sonnet-latest"
    )

    # Verify the company was created with the recruiter message
    assert company.name == "Acme Corp"
    assert company.recruiter_message is not None
    assert company.recruiter_message.message_id == "test123"
    assert company.message_id == "test123"
    assert (
        company.recruiter_message.message
        == "Hello, we have a job opportunity at Acme Corp for you."
    )

    # Verify all research methods were called
    mock_research_methods["company_researcher"].assert_called_once()
    mock_research_methods["levels_main"].assert_called_once()
    mock_research_methods["levels_extract"].assert_called_once()
    mock_research_methods["linkedin_main"].assert_called_once()


def test_research_company_with_string_message(
    mock_research_methods,
    job_search,
    basic_company_info,
    levels_data,
    linkedin_data,
):
    """Test creating a company from a string message."""
    # Configure mocks
    mock_research_methods["company_researcher"].return_value = basic_company_info
    mock_research_methods["levels_extract"].return_value = levels_data["levels"]
    mock_research_methods["levels_main"].return_value = levels_data["main_data"]
    mock_research_methods["linkedin_main"].return_value = linkedin_data

    # Research the company from a string message
    company = job_search.research_company(
        "We have a job opportunity at Acme Corp for you.",
        model="claude-3-5-sonnet-latest",
    )

    # Verify the company was created without a recruiter message
    assert company.name == "Acme Corp"
    assert company.recruiter_message is None
    assert company.message_id is None

    # Verify all research methods were called
    mock_research_methods["company_researcher"].assert_called_once()
    mock_research_methods["levels_main"].assert_called_once()
    mock_research_methods["levels_extract"].assert_called_once()
    mock_research_methods["linkedin_main"].assert_called_once()


def test_research_company_with_unknown_company(
    mock_research_methods,
    job_search,
    basic_company_info,
):
    """Test creating a company when the name can't be extracted."""
    # Configure mocks
    mock_research_methods["company_researcher"].return_value = CompaniesSheetRow(
        name=None,
        type="Private",
        url="https://acme.com",
    )
    mock_research_methods["levels_main"].return_value = []
    mock_research_methods["levels_extract"].return_value = []
    mock_research_methods["linkedin_main"].return_value = []

    # Research with a message that doesn't contain a company name
    company = job_search.research_company(
        "We have a job opportunity for you.", model="claude-3-5-sonnet-latest"
    )

    # Verify an unknown company was created
    assert company.name.startswith("<UNKNOWN")
    assert company.recruiter_message is None
    assert company.message_id is None

    # Verify basic research methods were called
    mock_research_methods["company_researcher"].assert_called_once()
    mock_research_methods["levels_main"].assert_called_once()
    mock_research_methods["levels_extract"].assert_called_once()

    # LinkedIn research should NOT be called for unknown companies that don't pass fit check
    # (no compensation data, no remote policy, no AI focus = 0 points, below 70% threshold)
    mock_research_methods["linkedin_main"].assert_not_called()


def test_research_company_with_advanced_research(
    mock_research_methods,
    job_search,
    recruiter_message,
    complete_company_info,
    levels_data,
    linkedin_data,
):
    """Test creating a company with advanced research enabled."""
    # Configure mocks
    mock_research_methods["company_researcher"].return_value = complete_company_info
    mock_research_methods["levels_extract"].return_value = levels_data["levels"]
    mock_research_methods["levels_main"].return_value = levels_data["main_data"]
    mock_research_methods["linkedin_main"].return_value = linkedin_data

    # Research the company with advanced research
    company = job_search.research_company(
        recruiter_message, model="claude-3-5-sonnet-latest", do_advanced=True
    )

    # Verify the company was created with the recruiter message
    assert company.name == "Acme Corp"
    assert company.recruiter_message is not None
    assert company.recruiter_message.message_id == "test123"
    assert company.message_id == "test123"
    assert (
        company.recruiter_message.message
        == "Hello, we have a job opportunity at Acme Corp for you."
    )

    # Verify research errors are initialized
    assert isinstance(company.status.research_errors, list)

    # Verify all research methods were called
    mock_research_methods["company_researcher"].assert_called_once()
    mock_research_methods["levels_main"].assert_called_once()
    mock_research_methods["levels_extract"].assert_called_once()
    mock_research_methods["linkedin_main"].assert_called_once()
