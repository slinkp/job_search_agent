import pytest
from unittest.mock import MagicMock, patch

import libjobsearch
import email_client


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
