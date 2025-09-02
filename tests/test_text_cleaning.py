from server.text_cleaning import clean_recruiter_message


class TestTextCleaning:
    """Test the text cleaning utility for recruiter messages."""

    def test_removes_quoted_content(self):
        """Test that quoted content is removed."""
        message = """Hi there,

I hope this message finds you well.

On Mon, Jan 15, 2024 at 10:00 AM, Paul <paul@example.com> wrote:
> Thanks for reaching out. I'm interested in learning more.

Best regards,
John"""

        cleaned = clean_recruiter_message(message)

        assert "Hi there," in cleaned
        assert "I hope this message finds you well" in cleaned
        assert "Best regards," in cleaned
        assert "John" in cleaned

        # Quoted content should be removed
        assert "On Mon, Jan 15" not in cleaned
        assert "Thanks for reaching out" not in cleaned
        assert "paul@example.com" not in cleaned

    def test_removes_email_headers(self):
        """Test that email headers are removed."""
        message = """Hi there,

I hope this message finds you well.

-----Original Message-----
From: John Recruiter <john@company.com>
Sent: Monday, January 15, 2024 9:00 AM
To: Paul <paul@example.com>
Subject: Exciting Opportunity

Best regards,
John"""

        cleaned = clean_recruiter_message(message)

        assert "Hi there," in cleaned
        assert "I hope this message finds you well" in cleaned
        assert "Best regards," in cleaned
        assert "John" in cleaned

        # Email headers should be removed
        assert "-----Original Message-----" not in cleaned
        assert "From: John Recruiter" not in cleaned
        assert "Sent: Monday" not in cleaned
        assert "To: Paul" not in cleaned
        assert "Subject: Exciting Opportunity" not in cleaned

    def test_removes_footers(self):
        """Test that footer content is removed."""
        message = """Hi there,

I hope this message finds you well.

Best regards,
John

Sent from my iPhone

Unsubscribe: Click here to unsubscribe from our mailing list.

LinkedIn Footer: This message was sent to you via LinkedIn"""

        cleaned = clean_recruiter_message(message)

        assert "Hi there," in cleaned
        assert "I hope this message finds you well" in cleaned
        assert "Best regards," in cleaned
        assert "John" in cleaned

        # Footer content should be removed
        assert "Sent from my iPhone" not in cleaned
        assert "Unsubscribe:" not in cleaned
        assert "LinkedIn Footer:" not in cleaned

    def test_preserves_paragraph_structure(self):
        """Test that paragraph structure is preserved."""
        message = """Hi there,

I hope this message finds you well.

We're looking for a senior developer to join our team.

Best regards,
John"""

        cleaned = clean_recruiter_message(message)

        # Should have paragraph breaks
        assert "\n\n" in cleaned
        assert cleaned.count("\n\n") >= 2

        # Content should be preserved in order
        lines = cleaned.split("\n\n")
        assert "Hi there," in lines[0]
        assert "I hope this message finds you well" in lines[1]
        assert "We're looking for a senior developer" in lines[2]
        assert "Best regards," in lines[3]
        assert "John" in lines[4]

    def test_normalizes_excessive_whitespace(self):
        """Test that excessive whitespace is normalized."""
        message = """Hi there,



I hope this message finds you well.



We're looking for a senior developer to join our team."""

        cleaned = clean_recruiter_message(message)

        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in cleaned

        # Should have reasonable paragraph spacing
        assert cleaned.count("\n\n") >= 1

    def test_handles_empty_message(self):
        """Test that empty messages are handled gracefully."""
        assert clean_recruiter_message("") == ""
        assert clean_recruiter_message(None) == ""

    def test_handles_message_with_only_quoted_content(self):
        """Test that messages with only quoted content return empty string."""
        message = """On Mon, Jan 15, 2024 at 10:00 AM, Paul <paul@example.com> wrote:
> Thanks for reaching out. I'm interested in learning more.

-----Original Message-----
From: John Recruiter <john@company.com>
Sent: Monday, January 15, 2024 9:00 AM
To: Paul <paul@example.com>
Subject: Exciting Opportunity

Sent from my iPhone"""

        cleaned = clean_recruiter_message(message)

        # Should return empty string since all content was quoted/footer
        assert cleaned == ""

    def test_preserves_important_content_after_quotes(self):
        """Test that important content after quoted sections is preserved."""
        message = """Hi there,

I hope this message finds you well.

On Mon, Jan 15, 2024 at 10:00 AM, Paul <paul@example.com> wrote:
> Thanks for reaching out. I'm interested in learning more.

-----Original Message-----
From: John Recruiter <john@company.com>
Sent: Monday, January 15, 2024 9:00 AM
To: Paul <paul@example.com>
Subject: Exciting Opportunity

But wait, there's more important information here!

Best regards,
John"""

        cleaned = clean_recruiter_message(message)

        assert "Hi there," in cleaned
        assert "I hope this message finds you well" in cleaned
        assert "But wait, there's more important information here!" in cleaned
        assert "Best regards," in cleaned
        assert "John" in cleaned

        # Quoted content should still be removed
        assert "On Mon, Jan 15" not in cleaned
        assert "-----Original Message-----" not in cleaned
