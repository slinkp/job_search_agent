import base64
import os
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError

from email_client import ARCHIVED_LABEL, GmailRepliesSearcher
from models import RecruiterMessage


class TestGmailRepliesSearcher:
    @pytest.fixture
    def gmail_searcher(self):
        with patch("email_client.build", autospec=True):
            searcher = GmailRepliesSearcher()
            searcher._service = MagicMock()
            yield searcher

    @pytest.fixture
    def mock_message(self):
        """Fixture for a basic Gmail message structure."""
        return {
            "id": "msg123",
            "threadId": "thread123",
            "internalDate": "1617235200000",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Job Opportunity"},
                    {"name": "From", "value": "recruiter@example.com"},
                    {"name": "Message-ID", "value": "<msg123@example.com>"},
                ],
                "body": {"data": base64.b64encode(b"Message content").decode()},
            },
        }

    @pytest.fixture
    def mock_credentials(self):
        """Fixture for Gmail API credentials."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token"}'
        return mock_creds

    def test_send_reply(self, gmail_searcher, mock_message):
        # Setup
        thread_id = "thread123"
        message_id = "msg456"
        reply_text = "Thank you for your message"

        gmail_searcher.service.users().messages().get.return_value.execute.return_value = (
            mock_message
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

    def test_send_reply_error(self, gmail_searcher):
        # Setup
        gmail_searcher.service.users().messages().get.return_value.execute.side_effect = (
            Exception("API Error")
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
            gmail_searcher, "add_label", return_value=True, autospec=True
        ) as mock_add_label:
            # Call the method
            result = gmail_searcher.label_and_archive_message(message_id)

            # Assertions
            assert result is True

            # Verify the message was modified to remove INBOX label
            modify_call = gmail_searcher.service.users().messages().modify.call_args
            assert modify_call is not None
            assert modify_call[1]["id"] == message_id
            assert modify_call[1]["body"]["removeLabelIds"][0] == "INBOX"

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
            gmail_searcher,
            "_get_or_create_label_id",
            return_value=label_id,
            autospec=True,
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
        with patch.object(
            gmail_searcher,
            "_get_or_create_label_id",
            return_value="label123",
            autospec=True,
        ):
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
            "id": label_id,
            "name": label_name,
        }

        # Call the method
        result = gmail_searcher._get_or_create_label_id(label_name)

        # Assertions
        assert result == label_id

        # Verify labels.create was called with the correct parameters
        create_call = gmail_searcher.service.users().labels().create.call_args
        assert create_call is not None
        assert create_call[1]["body"]["name"] == label_name

    def test_get_new_recruiter_messages(self, gmail_searcher, mock_message):
        """Test getting new recruiter messages."""
        # Mock the search_and_get_details method
        with patch.object(
            gmail_searcher,
            "search_and_get_details",
            return_value=[mock_message],
            autospec=True,
        ) as mock_search:
            # Mock the _get_email_thread_link method
            with patch.object(
                gmail_searcher,
                "_get_email_thread_link",
                return_value="https://mail.google.com/mail/u/0/#label/jobs+2024%2Frecruiter+pings/thread123",
                autospec=True,
            ):
                # Call the method
                result = gmail_searcher.get_new_recruiter_messages(max_results=1)

                # Assertions
                assert len(result) == 1
                assert isinstance(result[0], RecruiterMessage)
                assert result[0].message_id == "msg123"
                assert result[0].thread_id == "thread123"
                assert result[0].subject == "Job Opportunity"
                assert result[0].sender == "recruiter@example.com"

                def normalize_whitespace(text):
                    return " ".join(text.split())

                assert normalize_whitespace(result[0].message) == normalize_whitespace(
                    "Job Opportunity\n\nMessage content"
                )
                assert (
                    result[0].email_thread_link
                    == "https://mail.google.com/mail/u/0/#label/jobs+2024%2Frecruiter+pings/thread123"
                )

                # Verify search_and_get_details was called with the correct parameters
                mock_search.assert_called_once()

    def test_authenticate_with_expired_token(self, gmail_searcher, mock_credentials):
        """Test authentication with expired token."""
        # Mock expired credentials
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "token123"

        # Mock token file
        with patch("os.path.exists", return_value=True, autospec=True), patch(
            "email_client.Credentials.from_authorized_user_file",
            return_value=mock_creds,
            autospec=True,
        ), patch("email_client.Request", autospec=True), patch(
            "email_client.InstalledAppFlow", autospec=True
        ) as mock_flow, patch(
            "builtins.open", autospec=True
        ) as mock_open, patch(
            "email_client.build"
        ) as mock_build, patch(
            "email_client.CREDENTIALS_FILE", os.path.abspath("secrets/credentials.json")
        ), patch(
            "email_client.TOKEN_FILE", "secrets/token.json"
        ):
            # Make refresh fail with RefreshError
            mock_creds.refresh.side_effect = RefreshError("Token expired")

            # Mock the flow and its returned credentials
            mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = (
                mock_credentials
            )

            # Mock the build function
            mock_build.return_value = MagicMock()

            # Call authenticate
            gmail_searcher.authenticate()

            # Verify refresh was attempted
            mock_creds.refresh.assert_called_once()

            # Verify flow was created and run
            mock_flow.from_client_secrets_file.assert_called_once_with(
                os.path.abspath("secrets/credentials.json"), gmail_searcher.SCOPES
            )
            mock_flow.from_client_secrets_file.return_value.run_local_server.assert_called_once_with(
                port=0
            )

            # Verify the credentials were set correctly
            assert gmail_searcher.creds == mock_credentials

            # Verify credentials were written to file
            mock_open.assert_called_once_with("secrets/token.json", "w")
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
                '{"token": "new_token"}'
            )

            # Verify build was called with correct parameters
            mock_build.assert_called_once_with(
                "gmail", "v1", credentials=mock_credentials
            )

    def test_authenticate_without_token(self, gmail_searcher, mock_credentials):
        """Test authentication without existing token."""
        with patch("os.path.exists", return_value=False, autospec=True), patch(
            "email_client.InstalledAppFlow", autospec=True
        ) as mock_flow, patch(
            "email_client.CREDENTIALS_FILE", os.path.abspath("secrets/credentials.json")
        ), patch(
            "email_client.TOKEN_FILE", "secrets/token.json"
        ), patch(
            "builtins.open", autospec=True
        ) as mock_open:
            # Mock the flow and its returned credentials
            mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = (
                mock_credentials
            )

            # Call authenticate
            gmail_searcher.authenticate()

            # Verify flow was created and run
            mock_flow.from_client_secrets_file.assert_called_once_with(
                os.path.abspath("secrets/credentials.json"), gmail_searcher.SCOPES
            )
            mock_flow.from_client_secrets_file.return_value.run_local_server.assert_called_once_with(
                port=0
            )

            # Verify credentials were written to file
            mock_open.assert_called_once_with("secrets/token.json", "w")
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
                '{"token": "new_token"}'
            )

    def test_extract_message_content_with_parts(self, gmail_searcher):
        """Test extracting message content from message parts."""
        message = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": base64.b64encode(b"Message content").decode()},
                    }
                ]
            }
        }

        content = gmail_searcher.extract_message_content(message)
        assert content == "Message content"

    def test_extract_message_content_no_content(self, gmail_searcher):
        """Test extracting message content when no content is found."""
        message = {"payload": {"parts": []}}

        content = gmail_searcher.extract_message_content(message)
        assert content == ""

    def test_clean_reply_short_text(self, gmail_searcher):
        """Test cleaning short reply text."""
        text = "Replied on LinkedIn"
        cleaned = gmail_searcher.clean_reply(text)
        assert cleaned == ""

    def test_clean_reply_long_text(self, gmail_searcher):
        """Test cleaning long reply text."""
        text = "Thank you for your message. I am interested in the position."
        cleaned = gmail_searcher.clean_reply(text)
        assert cleaned == text

    def test_clean_quoted_text_with_garbage(self, gmail_searcher):
        """Test cleaning quoted text with garbage lines."""
        text = "> Normal line\n> Get the new LinkedIn\n> Another line"
        cleaned = gmail_searcher.clean_quoted_text(text)
        assert cleaned == "Normal line"

    def test_clean_quoted_text_with_email(self, gmail_searcher):
        """Test cleaning quoted text with email addresses."""
        text = "> Normal line\n> <user@example.com> wrote:\n> Another line"
        cleaned = gmail_searcher.clean_quoted_text(text)

        def normalize_whitespace(text):
            return " ".join(text.split())

        assert normalize_whitespace(cleaned) == normalize_whitespace("Normal line")

    def test_split_message_with_quoted_text(self, gmail_searcher):
        """Test splitting message with quoted text."""
        content = "My reply. Lorem ipsum dolor sit amet.\n\n"
        content += "On Mon, Jan 1, 2024 at 12:00 PM <user@example.com> wrote:\n\n"
        content += "Blah blah blah"
        reply, quoted = gmail_searcher.split_message(content)
        assert reply == "My reply. Lorem ipsum dolor sit amet."
        assert quoted == "Blah blah blah"

    def test_split_message_without_quoted_text(self, gmail_searcher):
        """Test splitting message without quoted text."""
        content = "Just a simple message. Lorem ipsum dolor sit amet."
        reply, quoted = gmail_searcher.split_message(content)
        assert reply == "Just a simple message. Lorem ipsum dolor sit amet."
        assert quoted == ""

    def test_get_subject_with_garbage(self, gmail_searcher):
        """Test getting subject with garbage subject."""
        message = {
            "payload": {
                "headers": [{"name": "Subject", "value": "You have an invitation"}]
            }
        }
        subject = gmail_searcher.get_subject(message)
        assert subject == "(No Subject)"

    def test_get_subject_no_subject(self, gmail_searcher):
        """Test getting subject when no subject header exists."""
        message = {"payload": {"headers": []}}
        subject = gmail_searcher.get_subject(message)
        assert subject == "(No Subject)"

    def test_send_reply_without_headers(self, gmail_searcher):
        """Test sending reply when original message has no headers."""
        thread_id = "thread123"
        message_id = "msg456"
        reply_text = "Thank you for your message"

        # Mock the original message response with no headers
        original_message = {"payload": {"headers": []}}

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

    def test_label_and_archive_message_error_removing_label(self, gmail_searcher):
        """Test error handling when removing label fails."""
        message_id = "msg456"
        gmail_searcher.service.users().messages().modify.return_value.execute.side_effect = Exception(
            "API Error"
        )

        result = gmail_searcher.label_and_archive_message(message_id)
        assert result is False

    def test_add_label_error_creating_label(self, gmail_searcher):
        """Test error handling when creating label fails."""
        message_id = "msg456"
        label_name = "test-label"

        # Make the modify call raise an exception
        gmail_searcher.service.users().messages().modify.return_value.execute.side_effect = Exception(
            "Label creation failed"
        )

        # Call the method
        result = gmail_searcher.add_label(message_id, label_name)

        # Assertions
        assert result is False

    def test_get_or_create_label_id_with_similar_name(self, gmail_searcher):
        """Test getting label ID with similar name."""
        label_name = "jobs-2024/recruiter-pings"
        label_id = "label123"

        # Mock the labels.list response with similar name
        gmail_searcher.service.users().labels().list.return_value.execute.return_value = {
            "labels": [
                {"name": "jobs 2024/recruiter pings", "id": label_id},
            ]
        }

        result = gmail_searcher._get_or_create_label_id(label_name)
        assert result == label_id
