import os
import random
import time
from datetime import datetime
from typing import Dict, List

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


class LinkedInSearcher:

    def __init__(self, debug: bool = False, headless: bool = True):
        # Fetch credentials from environment
        self.email: str = os.environ.get("LINKEDIN_EMAIL", "")
        self.password: str = os.environ.get("LINKEDIN_PASSWORD", "")
        self.headless = headless
        self.debug: bool = debug
        if not all([self.email, self.password]):
            raise ValueError("LinkedIn credentials not found in environment")

        playwright = sync_playwright().start()

        # Define path for persistent context
        user_data_dir = os.path.abspath("./playwright-linkedin-chrome")

        if headless:
            viewport = {"width": 1200, "height": 1400}
        else:
            viewport = {"width": 1000, "height": 1000}

        self.context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            channel="chrome",  # Use regular Chrome instead of Chromium
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--enable-sandbox",
            ],
            ignore_default_args=["--enable-automation", "--no-sandbox"],
            # Use new headless mode instead of the deprecated old headless mode
            chromium_sandbox=True,
            viewport=viewport,
        )
        print(f"Browser context launched in {'headless' if headless else 'headed'} mode")
        self.page = self.context.new_page()

        # Add webdriver detection bypass
        self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        self.delay = 1  # seconds between actions

    def screenshot(self, name: str):
        if self.debug:
            path = f"debug_{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
            print(f"Saving screenshot to {path}")
            self.page.screenshot(path=path)

    def _wait(self, delay: float | int = 0):
        """Add random delay between actions"""
        time.sleep(delay or (self.delay + random.random()))

    def login(self) -> None:
        """Login to LinkedIn with 2FA handling"""
        try:
            # First check if we're already logged in
            self.page.goto("https://www.linkedin.com/feed/")
            self._wait()
            try:
                # If we can access the feed within 3 seconds, we're already logged in
                self.page.wait_for_url("https://www.linkedin.com/feed/", timeout=3000)
                print("Already logged in!")
                return
            except PlaywrightTimeout:
                if self.headless:
                    raise ValueError(
                        "Not logged in and running in headless mode. "
                        "Please run with --no-headless first to log in manually."
                    )

            # Not logged in, proceed with login process
            self.page.goto("https://www.linkedin.com/login")
            self._wait()
            # Fill login form
            self.page.get_by_label("Email or Phone").fill(self.email)
            self._wait()
            self.page.get_by_label("Password").fill(self.password)
            self._wait()
            # Click sign in
            self.page.locator(
                "button[type='submit'][data-litms-control-urn='login-submit']"
            ).click()

            print("\nWaiting for 2FA verification or successful login...")

            # Try to detect 2FA page
            try:
                # Look for common 2FA elements using role-based selectors
                self.page.wait_for_selector("input[name='pin']", timeout=6000)
                print("2FA required - Please enter code from your authenticator app...")

                # Wait for successful login after 2FA
                # Give plenty of time to enter the code
                self.page.wait_for_url("https://www.linkedin.com/feed/", timeout=30000)
                print("Login successful!")

            except PlaywrightTimeout:
                # If no 2FA prompt is found, check if we're already logged in
                try:
                    self.page.wait_for_url("https://www.linkedin.com/feed/", timeout=3000)
                    print("Login successful (no 2FA required)!")
                except PlaywrightTimeout:
                    self.screenshot("login_state_with_timeout")
                    raise

        except Exception:
            self.screenshot("login_failure")
            raise

    def search_company_connections(self, company: str) -> List[Dict]:
        """
        Search for 1st-degree connections at specified company.
        Returns list of found connections with their details.
        """
        try:
            # Navigate to network-filtered search (starting with just network filter)
            search_url = (
                "https://www.linkedin.com/search/results/people/"
                "?network=[%22F%22]"  # F = 1st degree connections
                "&origin=FACETED_SEARCH"
            )
            self.page.goto(search_url)
            self._wait()

            # Click the Current company filter button
            self.page.get_by_role("button", name="Current company filter").click()
            self._wait()
            self.screenshot("after_clicking_company_filter")

            # Enter company name and wait for dropdown
            company_input = self.page.get_by_placeholder("Add a company")
            company_input.fill(company)
            company_input.press("Enter")
            self._wait()
            self.screenshot("after_entering_company")

            print("Waiting for company option to be visible...")
            for text in ["Company • Software Development", "Company • "]:
                company_option = (
                    self.page.locator("div[role='option']")
                    .filter(has_text=company)
                    .filter(has_text=text)
                    .first
                )
                try:
                    company_option.wait_for(state="visible", timeout=5000)
                    break
                except PlaywrightTimeout:
                    company_option = None
                    continue

            if company_option is None:
                print(f"Company option not found for {company}")
                self.screenshot("company_option_not_found")
                return []
            else:
                company_option.click()

            self._wait()
            self.screenshot("after_clicking_company_option")

            print("Waiting for Show results button to be visible...")
            show_results = self.page.get_by_role("button", name="Show results").first
            try:
                show_results.wait_for(state="visible", timeout=5000)
                # Click Show results directly (it should use the currently highlighted option)
                print("Clicking Show results button...")
                show_results.click()
                self._wait()
            except PlaywrightTimeout:
                print("Show results button not found")
                self.screenshot("show_results_button_not_found")
                return []

            self.screenshot("after_clicking_show_results")

            print("Waiting for search results...")
            try:
                results_container = self.page.locator("div.search-results-container")
                results_container.wait_for(state="visible", timeout=8000)
                with open(
                    f"debug_search_results_container_{datetime.now():%Y%m%d_%H%M%S}.html",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(results_container.evaluate("el => el.outerHTML"))
            except PlaywrightTimeout:
                self.screenshot("search_results_timeout")
                # Also capture page content for debugging
                with open(
                    f"debug_page_content_{datetime.now():%Y%m%d_%H%M%S}.html", "w"
                ) as f:
                    f.write(self.page.content())
                print("Results container missing")
                return []

            self.screenshot("post_wait")

            # Check for no results first
            no_results = self.page.get_by_text("No results found")
            if no_results.is_visible():
                print(f"Linkedin found no connections at {company}")
                return []

            # First try to get the HTML content of the page to analyze
            page_html = self.page.content()
            with open(
                f"debug_full_page_{datetime.now():%Y%m%d_%H%M%S}.html",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(page_html)

            # Get all result cards within search results container
            results = results_container.get_by_role("list").first.locator("li")
            count = results.count()
            print(f"Found {count} result items")

            # If we can't get results through the normal way, try a more direct approach
            if count == 0:
                # Try to get search results directly by class
                results = self.page.locator("li.reusable-search__result-container")
                count = results.count()
                print(f"Found {count} results with direct selector")

            connections = []

            for i in range(count):
                result = results.nth(i)
                try:
                    connection = self._find_connection(i, result)
                    if connection:
                        connections.append(connection)
                        print(
                            f"Found connection: {connection['name']} - {connection['title']}"
                        )
                except Exception as e:
                    dumpfile = f"debug_result_{i}_{datetime.now():%Y%m%d_%H%M%S}.html"
                    print(f"Error parsing result {i}: {e}, writing to {dumpfile}")
                    with open(dumpfile, "w", encoding="utf-8") as f:
                        f.write(result.evaluate("el => el.outerHTML"))

                    if self.debug:
                        # Save screenshot of this specific result for visual debugging
                        try:
                            result.screenshot(
                                path=f"debug_result_{i}_{datetime.now():%Y%m%d_%H%M%S}.png"
                            )
                            # Also dump the inner HTML structure for detailed analysis
                            with open(
                                f"debug_result_{i}_structure_{datetime.now():%Y%m%d_%H%M%S}.txt",
                                "w",
                                encoding="utf-8",
                            ) as f:
                                # Get element structure with classes - fixed to handle className that might not be a string
                                structure = result.evaluate(
                                    """el => {
                                    function getElementInfo(element, depth = 0) {
                                        let info = '  '.repeat(depth) + element.tagName.toLowerCase();
                                        if (element.id) info += '#' + element.id;
                                        if (element.className && typeof element.className === 'string') {
                                            info += '.' + element.className.replace(/\\s+/g, '.');
                                        } else if (element.classList && element.classList.length) {
                                            info += '.' + Array.from(element.classList).join('.');
                                        }
                                        if (element.innerText && element.innerText.trim()) 
                                            info += ' -> "' + element.innerText.trim().substring(0, 50) + '"';
                                        return info;
                                    }

                                    function getElementTree(element, depth = 0) {
                                        let result = getElementInfo(element, depth) + '\\n';
                                        for (const child of element.children) {
                                            result += getElementTree(child, depth + 1);
                                        }
                                        return result;
                                    }

                                    return getElementTree(el);
                                }"""
                                )
                                f.write(structure)
                        except Exception as screenshot_err:
                            print(f"Error capturing debug info: {screenshot_err}")

            return connections

        except Exception:
            self.screenshot("search_error.png")
            raise

    def _find_connection(self, i, result):
        # Skip upsell cards (they have specific classes or content)
        if (
            result.locator("div.search-result__upsell-divider").is_visible(timeout=1000)
            or result.locator("text=Sales Navigator").is_visible(timeout=1000)
            or result.locator("text=Try Premium").is_visible(timeout=1000)
        ):
            print(f"Skipping upsell card at index {i}")
            return {}

        # Check if this is a profile result by looking for a link
        try:
            result.get_by_role("link").first.is_visible(timeout=2000)
        except Exception:
            print(f"Skipping non-profile result at index {i}")
            return {}

        # Use multiple approaches to get the human-readable name
        try:
            # First try to get the name from the specific span that contains the actual name
            name_element = result.locator(
                "span.entity-result__title-text a span[aria-hidden='true']"
            ).first
            name = name_element.inner_text(timeout=1000).strip()
        except Exception:
            try:
                # Try to get the name from the link text directly
                name = (
                    result.get_by_role("link")
                    .first.inner_text(timeout=1000)
                    .strip()
                    .split("\n")[0]
                )
            except Exception:
                try:
                    # Another fallback method
                    name_element = result.locator(
                        "span.entity-result__title-text a"
                    ).first
                    name = name_element.inner_text(timeout=1000).strip().split("\n")[0]
                    print("Getting name from first approach failed, second worked")
                except Exception:
                    name = ""

        # Get title with shorter timeout
        try:
            title = result.locator("div.t-black.t-normal").first.inner_text(timeout=1000)
        except Exception:
            title = "Unknown title"

        # Get profile URL
        profile_url = result.get_by_role("link").first.get_attribute("href")

        # Extract username from URL for fallback or to combine with name
        username = ""
        url_parts = profile_url.split("/in/")
        if len(url_parts) > 1:
            username = url_parts[1].split("?")[0]

        # If we couldn't get a proper name, use the username
        if not name or "Status is" in name or len(name) < 2:
            print("No good Name found, falling back to username from URL")
            name = username

        # Try one more approach - look for the name in a different location
        if not name or name == username:
            try:
                # Try to find the name in the aria-label of the profile image
                img = result.locator("img.presence-entity__image").first
                if img.is_visible(timeout=1000):
                    aria_label = img.get_attribute("alt", timeout=1000).strip()
                    if aria_label and "Status is" not in aria_label:
                        print(
                            f"Fell back to using aria_label {aria_label} instead of username {username}"
                        )
                        name = aria_label
            except Exception:
                pass

        connection = {
            "name": name,
            "title": title,
            "profile_url": profile_url,
        }
        return connection

    def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main(company: str, debug: bool = False, headless: bool = True):
    searcher = LinkedInSearcher(debug=debug, headless=headless)
    try:
        searcher.login()

        print(f"\nSearching connections at {company}...")
        connections = searcher.search_company_connections(company)

        print(f"Found {len(connections)} connections at {company}")
        return connections
    finally:
        searcher.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "company", type=str, help="Company name to search for", default="Shopify"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode screenshots"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (not headless)",
    )
    args = parser.parse_args()
    headless = not args.no_headless
    results = main(args.company, debug=args.debug, headless=headless)
    for result in results:
        print(result)
