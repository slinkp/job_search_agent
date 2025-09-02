from datetime import datetime, timezone
from unittest.mock import Mock, patch

from models import RecruiterMessage

from ..app import get_messages


class TestMessagesEndpoint:
    """Test the messages endpoint functionality."""

    def test_messages_are_cleaned_for_display(self):
        """Test that recruiter messages are cleaned for display readability."""
        # Create a mock request
        request = Mock()

        # Create a sample recruiter message with typical Gmail formatting issues
        sample_message = RecruiterMessage(
            message_id="test123",
            company_id="company123",
            message="""Hi there,

I hope this message finds you well. I'm reaching out about an exciting opportunity at our company.

We're looking for a senior developer to join our team.

Best regards,
John Recruiter

On Mon, Jan 15, 2024 at 10:00 AM, Paul <paul@example.com> wrote:
> Thanks for reaching out. I'm interested in learning more.

-----Original Message-----
From: John Recruiter <john@company.com>
Sent: Monday, January 15, 2024 9:00 AM
To: Paul <paul@example.com>
Subject: Exciting Opportunity

This email is confidential and intended only for the recipient.

Sent from my iPhone

Unsubscribe: Click here to unsubscribe from our mailing list.

LinkedIn Footer: This message was sent to you via LinkedIn""",
            subject="Exciting Opportunity",
            sender="john@company.com",
            date=datetime.now(timezone.utc),
            thread_id="thread123",
            email_thread_link="https://mail.google.com/mail/u/0/#inbox/thread123",
        )

        # Mock the company repository to return our test message
        with patch("server.app.models.company_repository") as mock_repo:
            mock_repo.return_value.get_all_messages.return_value = [sample_message]

            # Call the endpoint
            result = get_messages(request)

            # Verify we get a message back
            assert len(result) == 1
            message_data = result[0]

            # Verify the original message is preserved
            assert "message" in message_data
            assert "Hi there," in message_data["message"]
            assert (
                "On Mon, Jan 15" in message_data["message"]
            )  # Quoted content still there

            # Verify we now have a cleaned display version
            assert "message_display" in message_data

            # Verify the cleaned version removes quoted content and footers
            cleaned = message_data["message_display"]
            assert "Hi there," in cleaned
            assert "I hope this message finds you well" in cleaned
            assert "We're looking for a senior developer" in cleaned
            assert "Best regards," in cleaned
            assert "John Recruiter" in cleaned

            # Verify quoted content is removed
            assert "On Mon, Jan 15" not in cleaned
            assert "-----Original Message-----" not in cleaned
            assert "Sent from my iPhone" not in cleaned
            assert "Unsubscribe:" not in cleaned
            assert "LinkedIn Footer:" not in cleaned

            # Verify paragraph structure is preserved
            assert "\n\n" in cleaned  # Should have paragraph breaks
            assert cleaned.count("\n\n") >= 2  # Should have multiple paragraphs
