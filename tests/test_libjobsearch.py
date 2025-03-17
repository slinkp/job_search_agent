import pytest
import os
import tempfile
import logging
from unittest.mock import MagicMock, patch, ANY

import libjobsearch
import email_client
import models
from models import Event, EventType, Company, CompaniesSheetRow


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
