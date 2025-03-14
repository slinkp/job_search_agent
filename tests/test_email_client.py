import pytest
from unittest.mock import MagicMock, patch

from email_client import GmailRepliesSearcher


@patch("email_client.build", autospec=True)
def test_send_reply(mock_build):
    """Test that send_reply correctly formats and sends an email reply."""
    # Setup mock service with proper specs
    mock_service = MagicMock(spec=["users"])
    mock_users = MagicMock(spec=["messages"])
    mock_messages = MagicMock(spec=["get", "send"])
    
    # Setup the chain of mocks to match the API structure
    mock_build.return_value = mock_service
    mock_service.users.return_value = mock_users
    mock_users.messages.return_value = mock_messages
    
    # Mock the get method to return a message with headers
    mock_get = MagicMock(spec=["execute"])
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
    mock_send = MagicMock(spec=["execute"])
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


@patch("email_client.build", autospec=True)
def test_archive_message(mock_build):
    """Test that archive_message correctly removes the INBOX label."""
    # Setup mock service with proper specs
    mock_service = MagicMock(spec=["users"])
    mock_users = MagicMock(spec=["messages"])
    mock_messages = MagicMock(spec=["modify"])
    
    # Setup the chain of mocks to match the API structure
    mock_build.return_value = mock_service
    mock_service.users.return_value = mock_users
    mock_users.messages.return_value = mock_messages
    
    # Mock the modify method
    mock_modify = MagicMock(spec=["execute"])
    mock_modify.execute.return_value = {}
    mock_messages.modify.return_value = mock_modify

    # Create the searcher and set the service
    searcher = GmailRepliesSearcher()
    searcher._service = mock_service

    # Test archiving a message
    result = searcher.archive_message(message_id="test-message")

    # Verify the result
    assert result is True

    # Verify the API was called correctly
    mock_messages.modify.assert_called_once_with(
        userId="me",
        id="test-message",
        body={"removeLabelIds": ["INBOX"]}
    )
    mock_modify.execute.assert_called_once()


@patch("email_client.build", autospec=True)
def test_add_label_existing(mock_build):
    """Test adding an existing label to a message."""
    # Setup mock service with proper specs
    mock_service = MagicMock(spec=["users"])
    mock_users = MagicMock(spec=["messages", "labels"])
    mock_messages = MagicMock(spec=["modify"])
    mock_labels = MagicMock(spec=["list"])
    
    # Setup the chain of mocks to match the API structure
    mock_build.return_value = mock_service
    mock_service.users.return_value = mock_users
    mock_users.messages.return_value = mock_messages
    mock_users.labels.return_value = mock_labels
    
    # Mock the labels list method
    mock_list = MagicMock(spec=["execute"])
    mock_list.execute.return_value = {
        "labels": [
            {"id": "Label_123", "name": "Existing-Label"}
        ]
    }
    mock_labels.list.return_value = mock_list
    
    # Mock the modify method
    mock_modify = MagicMock(spec=["execute"])
    mock_modify.execute.return_value = {}
    mock_messages.modify.return_value = mock_modify

    # Create the searcher and set the service
    searcher = GmailRepliesSearcher()
    searcher._service = mock_service

    # Test adding a label
    result = searcher.add_label(
        message_id="test-message",
        label_name="Existing-Label"
    )

    # Verify the result
    assert result is True

    # Verify the API was called correctly
    mock_labels.list.assert_called_once_with(userId="me")
    mock_messages.modify.assert_called_once_with(
        userId="me",
        id="test-message",
        body={"addLabelIds": ["Label_123"]}
    )


@patch("email_client.build", autospec=True)
def test_add_label_new(mock_build):
    """Test adding a new label to a message."""
    # Setup mock service with proper specs
    mock_service = MagicMock(spec=["users"])
    mock_users = MagicMock(spec=["messages", "labels"])
    mock_messages = MagicMock(spec=["modify"])
    mock_labels = MagicMock(spec=["list", "create"])
    
    # Setup the chain of mocks to match the API structure
    mock_build.return_value = mock_service
    mock_service.users.return_value = mock_users
    mock_users.messages.return_value = mock_messages
    mock_users.labels.return_value = mock_labels
    
    # Mock the labels list method - no matching label
    mock_list = MagicMock(spec=["execute"])
    mock_list.execute.return_value = {
        "labels": [
            {"id": "Label_123", "name": "Other-Label"}
        ]
    }
    mock_labels.list.return_value = mock_list
    
    # Mock the create method
    mock_create = MagicMock(spec=["execute"])
    mock_create.execute.return_value = {"id": "New_Label_456", "name": "New-Label"}
    mock_labels.create.return_value = mock_create
    
    # Mock the modify method
    mock_modify = MagicMock(spec=["execute"])
    mock_modify.execute.return_value = {}
    mock_messages.modify.return_value = mock_modify

    # Create the searcher and set the service
    searcher = GmailRepliesSearcher()
    searcher._service = mock_service

    # Test adding a new label
    result = searcher.add_label(
        message_id="test-message",
        label_name="New-Label"
    )

    # Verify the result
    assert result is True

    # Verify the API was called correctly
    mock_labels.list.assert_called_once_with(userId="me")
    mock_labels.create.assert_called_once_with(
        userId="me",
        body={
            "name": "New-Label",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
    )
    mock_messages.modify.assert_called_once_with(
        userId="me",
        id="test-message",
        body={"addLabelIds": ["New_Label_456"]}
    )
