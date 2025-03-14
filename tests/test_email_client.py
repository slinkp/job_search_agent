import pytest
from unittest.mock import MagicMock, patch

from email_client import GmailRepliesSearcher


@patch("email_client.build")
def test_send_reply(mock_build):
    """Test that send_reply correctly formats and sends an email reply."""
    # Setup mock service
    mock_service = MagicMock()
    mock_messages = MagicMock()
    mock_users = MagicMock()

    # Setup the chain of mocks to match the API structure
    mock_build.return_value = mock_service
    mock_service.users.return_value = mock_users
    mock_users.messages.return_value = mock_messages

    # Mock the get method to return a message with headers
    mock_get = MagicMock()
    mock_get.execute.return_value = {
        "payload": {
            "headers": [
                {"name": "From", "value": "test@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Message-ID", "value": "<test-message-id@example.com>"},
            ]
        }
    }
    mock_messages.get.return_value = mock_get

    # Mock the send method
    mock_send = MagicMock()
    mock_send.execute.return_value = {"id": "new-message-id"}
    mock_messages.send.return_value = mock_send

    # Create the searcher and set the service
    searcher = GmailRepliesSearcher()
    searcher._service = mock_service

    # Test sending a reply
    result = searcher.send_reply(
        thread_id="test-thread",
        message_id="test-message",
        reply_text="This is a test reply",
    )

    # Verify the result
    assert result is True

    # Verify the API was called correctly
    mock_messages.get.assert_called_once_with(userId="me", id="test-message")
    mock_messages.send.assert_called_once()

    # Check that the send call included the right data
    send_args = mock_messages.send.call_args[1]
    assert send_args["userId"] == "me"
    assert "raw" in send_args["body"]
    assert send_args["body"]["threadId"] == "test-thread"
