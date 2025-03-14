import pytest
from unittest.mock import MagicMock, patch

import libjobsearch
from libjobsearch import RecruiterMessage


@patch("libjobsearch.email_client.GmailRepliesSearcher", autospec=True)
def test_send_reply(mock_gmail_searcher_class):
    """Test that send_reply correctly sends an email and archives it."""
    # Setup mock
    mock_searcher = MagicMock()
    mock_gmail_searcher_class.return_value = mock_searcher
    
    # Configure the mock to return success
    mock_searcher.send_reply.return_value = True
    
    # Test sending a reply
    result = libjobsearch.send_reply(
        message_id="test-message-id",
        thread_id="test-thread-id",
        reply="This is a test reply"
    )
    
    # Verify the result
    assert result is True
    
    # Verify the methods were called correctly
    mock_searcher.authenticate.assert_called_once()
    mock_searcher.send_reply.assert_called_once_with(
        "test-thread-id", "test-message-id", "This is a test reply"
    )
    mock_searcher.add_label.assert_called_once_with(
        "test-message-id", "Replied-Automated"
    )
    mock_searcher.archive_message.assert_called_once_with("test-message-id")


@patch("libjobsearch.email_client.GmailRepliesSearcher", autospec=True)
def test_archive_message(mock_gmail_searcher_class):
    """Test that archive_message correctly archives and labels a message."""
    # Setup mock
    mock_searcher = MagicMock()
    mock_gmail_searcher_class.return_value = mock_searcher
    
    # Configure the mock to return a message
    mock_searcher.search_messages.return_value = [{"id": "test-message-id"}]
    
    # Create a test message
    test_message = RecruiterMessage(
        message="Test message content",
        email_thread_link="https://mail.google.com/mail/u/0/#label/jobs+2024%2Frecruiter+pings/test-thread-id"
    )
    
    # Test archiving a message
    libjobsearch.archive_message(test_message, company_name="Test Company")
    
    # Verify the methods were called correctly
    mock_searcher.authenticate.assert_called_once()
    mock_searcher.search_messages.assert_called_once_with(
        "threadId:test-thread-id", max_results=1
    )
    mock_searcher.add_label.assert_any_call("test-message-id", "Replied-Automated")
    mock_searcher.add_label.assert_any_call("test-message-id", "Company/Test Company")
    mock_searcher.archive_message.assert_called_once_with("test-message-id")
