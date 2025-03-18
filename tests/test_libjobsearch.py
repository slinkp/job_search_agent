import argparse
import logging
import os
import tempfile
from unittest.mock import ANY, MagicMock, patch

import pytest

import libjobsearch
import models
from models import CompaniesSheetRow, Company, Event, EventType


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

    # Call the function with a company name
    result = libjobsearch.send_reply_and_archive(
        message_id="test-message-id",
        thread_id="test-thread-id",
        reply="This is a test reply",
        company_name="Test Company"
    )

    # Verify the result
    assert result is True

    # Verify an event was created
    mock_repo.create_event.assert_called_once()

    # Get the event that was created
    event_arg = mock_repo.create_event.call_args[0][0]

    # Verify event properties
    assert isinstance(event_arg, Event)
    assert event_arg.company_name == "Test Company"
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


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Create a test repository with the temp database
    repo = models.CompanyRepository(db_path=db_path, clear_data=True)
    
    # Create a test company
    company = Company(
        name="Test Company",
        details=CompaniesSheetRow(name="Test Company"),
    )
    repo.create(company)
    
    # Override the singleton for testing
    original_repo = models._company_repository
    models._company_repository = repo
    
    yield db_path
    
    # Restore the original repository
    models._company_repository = original_repo
    
    # Clean up the temp file
    if os.path.exists(db_path):
        os.remove(db_path)


def test_research_company_creates_event(temp_db):
    """Test that research_company creates a RESEARCH_COMPLETED event."""
    # Create test args and cache settings
    class Args:
        model = "test-model"
        rag_message_limit = 5
        recruiter_message_limit = 1
        sheet = "test"
    
    args = Args()
    cache_settings = libjobsearch.CacheSettings(no_cache=True)
    
    # Create a JobSearch instance with mocked components
    with patch("libjobsearch.EmailResponseGenerator", autospec=True):
        job_search = libjobsearch.JobSearch(args, logging.INFO, cache_settings)
        
        # Mock the research methods to avoid actual API calls
        with patch.object(job_search, "initial_research_company") as mock_initial:
            with patch.object(job_search, "research_compensation") as mock_comp:
                with patch.object(job_search, "followup_research_company") as mock_followup:
                    # Configure mocks
                    company_info = CompaniesSheetRow(name="Test Company")
                    mock_initial.return_value = company_info
                    mock_comp.return_value = company_info
                    mock_followup.return_value = company_info
                    
                    # Call the method
                    result = job_search.research_company("Test message", model="test-model")
                    
                    # Verify the result
                    assert result.name == "Test Company"
                    
                    # Check that an event was created
                    repo = models.company_repository()
                    events = repo.get_events(
                        company_name="Test Company",
                        event_type=EventType.RESEARCH_COMPLETED
                    )
                    
                    # Verify we have exactly one event
                    assert len(events) == 1
                    assert events[0].company_name == "Test Company"
                    assert events[0].event_type == EventType.RESEARCH_COMPLETED
