"""
Text cleaning utilities for recruiter messages.

This module handles cleaning and formatting recruiter messages for better display readability.
"""

import re
from typing import List


def clean_recruiter_message(text: str) -> str:
    """
    Clean a recruiter message for display by removing quoted content, footers, and normalizing formatting.

    Args:
        text: The raw message text to clean

    Returns:
        Cleaned text suitable for display
    """
    if not text:
        return ""

    # Normalize line endings and whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into lines for processing
    lines = text.split("\n")

    # Remove quoted content and footers
    cleaned_lines = []
    in_quoted_section = False
    in_footer_section = False

    for i, line in enumerate(lines):
        line = line.strip()

        # Skip empty lines (we'll normalize spacing later)
        if not line:
            continue

        # Check if we're entering a quoted section
        if _is_quoted_section_start(line, lines, i):
            in_quoted_section = True
            continue

        # Also enter quoted section if we're already in one and this line looks like a continuation
        # (email headers like From:, Sent:, To:, Subject:)
        if (
            in_quoted_section
            and line
            and re.match(r"^(from|sent|to|subject):", line.lower())
        ):
            continue

        # Check if we're entering a footer section
        if _is_footer_section_start(line):
            in_footer_section = True
            continue

        # Check if we're exiting quoted sections (look for end markers)
        if in_quoted_section and _is_quoted_section_end(line):
            in_quoted_section = False
            continue

        # Also exit quoted section if we see a line that looks like legitimate content
        # (not starting with >, not empty, and not a quoted section starter)
        if (
            in_quoted_section
            and line
            and not line.startswith(">")
            and not _is_quoted_section_start(line, lines, i)
        ):
            in_quoted_section = False
            # Don't continue here - let this line be processed normally

        # Skip lines if we're in quoted or footer sections
        if in_quoted_section or in_footer_section:
            continue

        # Add the line if it's not in a quoted or footer section
        cleaned_lines.append(line)

    # Reconstruct text with normalized paragraph spacing
    cleaned_text = "\n\n".join(cleaned_lines)

    # Normalize excessive whitespace
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    # Trim leading/trailing whitespace
    cleaned_text = cleaned_text.strip()

    return cleaned_text


def _is_quoted_section_start(line: str, all_lines: List[str], current_index: int) -> bool:
    """Check if this line starts a quoted section."""
    line_lower = line.lower()

    # Common quoted section starters
    quoted_patterns = [
        r"^on .* wrote:$",
        r"^-----original message-----$",
        r"^from:.*sent:.*to:.*subject:",
        r"^>.*$",  # Lines starting with >
        r"^.*\s+wrote:$",
        r"^.*\s+said:$",
        r"^-----.*-----",  # Lines with dashes (like "-----Original Message-----")
    ]

    for pattern in quoted_patterns:
        if re.match(pattern, line_lower):
            return True

    # Check for email header patterns
    if re.match(r"^from:\s+", line_lower) and current_index < len(all_lines) - 1:
        # Look ahead to see if this is followed by email headers
        next_line = all_lines[current_index + 1].strip().lower()
        if re.match(r"^sent:\s+", next_line):
            return True

    return False


def _is_quoted_section_end(line: str) -> bool:
    """Check if this line marks the end of a quoted section."""
    line_lower = line.lower()

    # Common quoted section end markers
    end_patterns = [
        r"^sent from my",
        r"^unsubscribe",
        r"^linkedin footer:",
        r"^this email is confidential",
        r"^privacy policy",
        r"^terms of service",
        r"^click here to",
        r"^sent from iphone",
        r"^sent from gmail",
        r"^get outlook",
        r"^get gmail",
    ]

    for pattern in end_patterns:
        if re.search(pattern, line_lower):
            return True

    return False


def _is_footer_section_start(line: str) -> bool:
    """Check if this line starts a footer section."""
    line_lower = line.lower()

    # Common footer section starters - only the obvious ones that come after the main content
    footer_patterns = [
        r"^sent from my",
        r"^unsubscribe",
        r"^linkedin footer:",
        r"^this email is confidential",
        r"^privacy policy",
        r"^terms of service",
        r"^click here to",
        r"^get outlook",
        r"^get gmail",
        # Don't treat common email closings as footers - they're part of the message
        # r'^best regards',
        # r'^sincerely',
        # r'^thanks',
        # r'^regards',
    ]

    for pattern in footer_patterns:
        if re.search(pattern, line_lower):
            return True

    return False
