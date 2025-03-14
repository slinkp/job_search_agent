import base64
import pytest
from unittest.mock import MagicMock, patch

from email_client import GmailRepliesSearcher, ARCHIVED_LABEL


class TestGmailRepliesSearcher:
    @pytest.fixture
    def gmail_searcher(self):
        with patch("email_client.build") as mock_build:
            searcher = GmailRepliesSearcher()
            searcher._service = MagicMock()
            yield searcher

    def test_send_reply(self, gmail_searcher):
        # Setup
        thread_id = "thread123"
        message_id = "msg456"
        reply_text = "Thank you for your message"

        # Mock the original message response
        original_message = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Job Opportunity"},
                    {"name": "From", "value": "recruiter@example.com"},
                    {"name": "Message-ID", "value": "<msg123@example.com>"},
                ]
            }
        }

        gmail_searcher.service.users().messages().get.return_value.execute.return_value = (
            original_message
        )
        gmail_searcher.service.users().messages().send.return_value.execute.return_value = {
            "id": "sent123"
        }

        # Call the method
        result = gmail_searcher.send_reply(thread_id, message_id, reply_text)

        # Assertions
        assert result is True

        # Verify the message was constructed correctly
        send_call = gmail_searcher.service.users().messages().send.call_args
        assert send_call is not None

        # Check that the threadId was included
        body_arg = send_call[1]["body"]
        assert body_arg["threadId"] == thread_id

        # We can't easily check the raw message content since it's encoded,
        # but we can verify the method was called

    def test_send_reply_error(self, gmail_searcher):
        # Setup
        gmail_searcher.service.users().messages().get.return_value.execute.side_effect = Exception(
            "API Error"
        )

        # Call the method
        result = gmail_searcher.send_reply("thread123", "msg456", "Reply text")

        # Assertions
        assert result is False

    def test_label_and_archive_message(self, gmail_searcher):
        # Setup
        message_id = "msg456"

        # Mock the add_label method
        with patch.object(
            gmail_searcher, "add_label", return_value=True
        ) as mock_add_label:
            # Call the method
            result = gmail_searcher.label_and_archive_message(message_id)

            # Assertions
            assert result is True

            # Verify the message was modified to remove INBOX label
            modify_call = gmail_searcher.service.users().messages().modify.call_args
            assert modify_call is not None
            assert modify_call[1]["id"] == message_id
            assert modify_call[1]["body"]["removeLabelIds"] == ["INBOX"]

            # Verify add_label was called with the archived label
            mock_add_label.assert_called_once_with(message_id, ARCHIVED_LABEL)

    def test_label_and_archive_message_error(self, gmail_searcher):
        # Setup
        message_id = "msg456"
        gmail_searcher.service.users().messages().modify.return_value.execute.side_effect = Exception(
            "API Error"
        )

        # Call the method
        result = gmail_searcher.label_and_archive_message(message_id)

        # Assertions
        assert result is False

    def test_add_label(self, gmail_searcher):
        # Setup
        message_id = "msg456"
        label_name = "test-label"
        label_id = "label123"

        # Mock the _get_or_create_label_id method
        with patch.object(
            gmail_searcher, "_get_or_create_label_id", return_value=label_id
        ) as mock_get_label:
            # Call the method
            result = gmail_searcher.add_label(message_id, label_name)

            # Assertions
            assert result is True

            # Verify the label was added to the message
            modify_call = gmail_searcher.service.users().messages().modify.call_args
            assert modify_call is not None
            assert modify_call[1]["id"] == message_id
            assert modify_call[1]["body"]["addLabelIds"] == [label_id]

            # Verify _get_or_create_label_id was called with the label name
            mock_get_label.assert_called_once_with(label_name)

    def test_add_label_error(self, gmail_searcher):
        # Setup
        message_id = "msg456"
        label_name = "test-label"

        # Mock the _get_or_create_label_id method
        with patch.object(gmail_searcher, "_get_or_create_label_id", return_value="label123"):
            # Make the modify call raise an exception
            gmail_searcher.service.users().messages().modify.return_value.execute.side_effect = Exception(
                "API Error"
            )

            # Call the method
            result = gmail_searcher.add_label(message_id, label_name)

            # Assertions
            assert result is False

    def test_get_or_create_label_id_existing(self, gmail_searcher):
        # Setup
        label_name = "test-label"
        label_id = "label123"

        # Mock the labels.list response
        gmail_searcher.service.users().labels().list.return_value.execute.return_value = {
            "labels": [
                {"name": "other-label", "id": "other456"},
                {"name": label_name, "id": label_id},
            ]
        }

        # Call the method
        result = gmail_searcher._get_or_create_label_id(label_name)

        # Assertions
        assert result == label_id

        # Verify labels.create was not called
        gmail_searcher.service.users().labels().create.assert_not_called()

    def test_get_or_create_label_id_new(self, gmail_searcher):
        # Setup
        label_name = "new-label"
        label_id = "new123"

        # Mock the labels.list response (label doesn't exist)
        gmail_searcher.service.users().labels().list.return_value.execute.return_value = {
            "labels": [{"name": "other-label", "id": "other456"}]
        }

        # Mock the labels.create response
        gmail_searcher.service.users().labels().create.return_value.execute.return_value = {
            "id": label_id
        }

        # Call the method
        result = gmail_searcher._get_or_create_label_id(label_name)

        # Assertions
        assert result == label_id

        # Verify labels.create was called with the correct parameters
        create_call = gmail_searcher.service.users().labels().create.call_args
        assert create_call is not None
        assert create_call[1]["body"]["name"] == label_name
