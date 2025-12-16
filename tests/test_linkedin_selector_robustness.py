"""Test that LinkedIn searcher handles selector variations robustly."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout


def test_company_filter_button_tries_multiple_selectors():
    """Test that search_company_connections tries multiple selector variations for the company filter button."""
    from linkedin_searcher import LinkedInSearcher

    # Create a mock page that simulates LinkedIn's UI
    mock_page = Mock()
    mock_context = Mock()

    # Track which selectors were tried
    selector_attempts = []

    def get_by_role_side_effect(role, **kwargs):
        """Simulate different button names failing until one works."""
        name = kwargs.get("name", "")
        selector_attempts.append(name)

        button_mock = Mock()
        # All button attempts fail
        button_mock.wait_for.side_effect = PlaywrightTimeout("Button not found")
        return button_mock

    mock_page.get_by_role.side_effect = get_by_role_side_effect
    mock_page.goto = Mock()
    mock_page.screenshot = Mock()
    mock_page.content.return_value = "<html><body>Test</body></html>"

    # Also make the alternative selector fail
    mock_alt_button = Mock()
    mock_alt_button.wait_for.side_effect = PlaywrightTimeout("Button not found")
    mock_locator = Mock()
    mock_locator.filter.return_value.first = mock_alt_button
    mock_page.locator.return_value = mock_locator

    # Patch the context and page creation
    with patch("linkedin_searcher.sync_playwright") as mock_playwright:
        mock_pw = Mock()
        mock_playwright.return_value.start.return_value = mock_pw
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Mock environment variables
        with patch.dict(
            "os.environ",
            {"LINKEDIN_EMAIL": "test@example.com", "LINKEDIN_PASSWORD": "password"},
        ):
            searcher = LinkedInSearcher(debug=True, headless=True)
            searcher.page = mock_page

            # Try to search, should return empty list when all selectors fail
            result = searcher.search_company_connections("TestCompany")

            # Verify that multiple button name variations were tried
            assert (
                len(selector_attempts) >= 2
            ), f"Expected multiple selector attempts, got {len(selector_attempts)}"
            # Verify that different names were tried
            assert (
                len(set(selector_attempts)) >= 2
            ), "Expected different selector names to be tried"
            # Should return empty list when all selectors fail
            assert result == []


def test_company_filter_handles_timeout_gracefully():
    """Test that the searcher handles timeout errors gracefully."""
    from linkedin_searcher import LinkedInSearcher

    mock_page = Mock()
    mock_context = Mock()

    # Make all button attempts timeout
    mock_button = Mock()
    mock_button.wait_for.side_effect = PlaywrightTimeout("Timeout waiting for button")
    mock_page.get_by_role.return_value = mock_button

    # Also make the alternative selector timeout
    mock_alt_button = Mock()
    mock_alt_button.wait_for.side_effect = PlaywrightTimeout("Timeout waiting for button")
    mock_locator = Mock()
    mock_locator.filter.return_value.first = mock_alt_button
    mock_page.locator.return_value = mock_locator

    mock_page.goto = Mock()
    mock_page.screenshot = Mock()
    mock_page.content.return_value = "<html><body>Test</body></html>"

    with patch("linkedin_searcher.sync_playwright") as mock_playwright:
        mock_pw = Mock()
        mock_playwright.return_value.start.return_value = mock_pw
        mock_pw.chromium.launch_persistent_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        with patch.dict(
            "os.environ",
            {"LINKEDIN_EMAIL": "test@example.com", "LINKEDIN_PASSWORD": "password"},
        ):
            searcher = LinkedInSearcher(debug=True, headless=True)
            searcher.page = mock_page

            # Should handle timeout gracefully and return empty list
            result = searcher.search_company_connections("TestCompany")

            # The function should not crash and should return an empty list
            assert result == []
