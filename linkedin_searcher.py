import os
import os.path
import random
import time
from datetime import datetime
from typing import Dict, List

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from models import company_repository


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
            viewport=viewport,  # type: ignore[arg-type]
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
        if not os.path.exists("screenshots"):
            os.mkdir("screenshots")
        if self.debug:
            path = f"screenshots/debug_{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
            print(f"Saving screenshot to {path}")
            self.page.screenshot(path=path)

    def dump_html(self, name, content):
        path = f"screenshots/debug_{name}_{datetime.now():%Y%m%d_%H%M%S}.html"
        with open(path, "w", encoding="utf8") as dumpfile:
            dumpfile.write(content)

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

            # Click the Current company filter - try multiple selector variations
            # LinkedIn changed from a button to a label element
            company_filter_clicked = False

            # Try direct text-based label selector first (most reliable for current UI)
            try:
                print("Trying to find label containing 'Current companies'")
                element = (
                    self.page.locator("label").filter(has_text="Current companies").first
                )
                element.wait_for(state="visible", timeout=3000)
                element.click()
                company_filter_clicked = True
                print("Successfully clicked 'Current companies' label")
            except PlaywrightTimeout:
                print("Label with 'Current companies' not found, trying alternatives")

            # Try other selector variations if first attempt failed
            if not company_filter_clicked:
                selector_attempts = [
                    ("label", "Current companies"),
                    ("button", "Current company filter. Click to add a filter."),
                    ("button", "Current company filter"),
                    ("button", "Current company"),
                    ("button", "Company"),
                ]

                for role, name in selector_attempts:
                    try:
                        print(f"Trying to find company filter {role} with name: {name}")
                        element = self.page.get_by_role(role, name=name)
                        element.wait_for(state="visible", timeout=3000)
                        element.click()
                        company_filter_clicked = True
                        print(f"Successfully clicked company filter {role}: {name}")
                        break
                    except PlaywrightTimeout:
                        print(
                            f"{role.capitalize()} with name '{name}' not found, trying next variation"
                        )
                        continue

            # Final fallback: look for any label containing company-related text
            if not company_filter_clicked:
                try:
                    print("Trying fallback: looking for label containing 'ompan'")
                    element = self.page.locator("label").filter(has_text="ompan").first
                    element.wait_for(state="visible", timeout=3000)
                    element.click()
                    company_filter_clicked = True
                    print("Successfully clicked company filter using fallback selector")
                except PlaywrightTimeout:
                    print("All selector attempts failed")

            if not company_filter_clicked:
                print("Could not find company filter button with any known variation")
                self.screenshot("company_filter_button_not_found")
                self.dump_html("company_filter_button_not_found", self.page.content())
                return []

            self._wait()
            self.screenshot("after_clicking_company_filter")

            # Enter company name and wait for dropdown
            company_input = self.page.get_by_placeholder("Add a company")
            company_input.fill(company)
            company_input.press("Enter")
            self._wait()
            self.screenshot("after_entering_company")

            print("Waiting for company option to be visible...")
            company_option = None

            # LinkedIn changed from role='option' to role='checkbox' for company list items
            # Try multiple selector strategies
            selector_strategies = [
                # New UI: checkbox role with just company name
                ("div[role='checkbox']", None),
                # Fallback: old option role with additional text
                ("div[role='option']", "Company • Software Development"),
                ("div[role='option']", "Company • "),
            ]

            for selector, additional_text in selector_strategies:
                try:
                    if additional_text:
                        company_option = (
                            self.page.locator(selector)
                            .filter(has_text=company)
                            .filter(has_text=additional_text)
                            .first
                        )
                    else:
                        # Just match by company name for checkbox elements
                        company_option = (
                            self.page.locator(selector).filter(has_text=company).first
                        )
                    company_option.wait_for(state="visible", timeout=5000)
                    print(f"Found company option using selector: {selector}")
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
            # LinkedIn changed their structure - try multiple container selectors
            results_container = None

            # Try different container selectors in order of specificity
            container_selectors = [
                ('div[role="main"]', "main role container"),
                ('div[data-testid="lazy-column"]', "lazy-column container"),
                ("div.search-results-container", "search-results-container (old)"),
            ]

            for selector, description in container_selectors:
                try:
                    container = self.page.locator(selector).first
                    container.wait_for(state="visible", timeout=3000)
                    results_container = container
                    print(f"Found {description}")
                    break
                except PlaywrightTimeout:
                    continue

            if results_container is None:
                print("No specific results container found, will search entire page")
                results_container = self.page
            else:
                try:
                    self.dump_html(
                        "search_results_container",
                        results_container.evaluate("el => el.outerHTML"),
                    )
                except Exception:
                    pass

            self.screenshot("post_wait")

            # Check for no results first
            no_results = self.page.get_by_text("No results found")
            try:
                if no_results.is_visible(timeout=1000):
                    print(f"Linkedin found no connections at {company}")
                    return []
            except PlaywrightTimeout:
                # No "no results" message, which is good - means there are results
                pass

            # First try to get the HTML content of the page to analyze
            self.dump_html("full_page", self.page.content())

            # Get all result cards - LinkedIn changed from <li> to <div role="listitem">
            # Try multiple selector strategies
            results = None
            count = 0

            # Strategy 1: div with role="listitem" inside results container
            try:
                results = results_container.locator('div[role="listitem"]')
                count = results.count()
                if count > 0:
                    print(f"Found {count} result items using div[role='listitem']")
            except Exception:
                pass

            # Strategy 2: Try by data attribute
            if count == 0:
                try:
                    results = self.page.locator(
                        'div[data-view-name="people-search-result"]'
                    )
                    count = results.count()
                    if count > 0:
                        print(f"Found {count} results with data-view-name selector")
                except Exception:
                    pass

            # Strategy 3: Fall back to old li-based selectors
            if count == 0:
                try:
                    results = results_container.get_by_role("list").first.locator("li")
                    count = results.count()
                    if count > 0:
                        print(f"Found {count} result items using old <li> selector")
                except Exception:
                    pass

            # Strategy 4: Direct class-based selector
            if count == 0:
                try:
                    results = self.page.locator("li.reusable-search__result-container")
                    count = results.count()
                    if count > 0:
                        print(f"Found {count} results with direct class selector")
                except Exception:
                    pass

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
                except Exception:
                    self.dump_html(
                        f"result_{i}_exception", result.evaluate("el => el.outerHTML")
                    )
                    if self.debug:
                        # Save screenshot of this specific result for visual debugging
                        try:
                            result.screenshot(
                                path=f"screenshots/debug_result_{i}_{datetime.now():%Y%m%d_%H%M%S}.png"
                            )
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

        # Get title - LinkedIn changed their class names
        title = None
        title_selectors = [
            # New UI: Look for p tags that likely contain the title
            # The title is typically the second or third p tag after the name
            ("p.ff633f4c.e295a86c", "new p tag classes"),
            # Try finding any p that contains common title patterns
            ("p", "any p tag"),
            # Old selector as fallback
            ("div.t-black.t-normal", "old div selector"),
        ]

        for selector, description in title_selectors:
            try:
                # Get all matching elements and try to find the one with the title
                # Title usually comes after the name and before location
                title_elements = result.locator(selector).all()
                for elem in title_elements:
                    text = elem.inner_text(timeout=500).strip()
                    # Title usually contains " at " or ends with job-related words
                    # Skip if it's the connection degree indicator
                    if (
                        text
                        and " • 1st" not in text
                        and " • 2nd" not in text
                        and " • 3rd" not in text
                    ):
                        # Simple heuristic: if it contains common job indicators or "at", it's likely the title
                        if " at " in text or any(
                            word in text.lower()
                            for word in [
                                "engineer",
                                "manager",
                                "director",
                                "developer",
                                "designer",
                                "analyst",
                                "lead",
                                "specialist",
                                "coordinator",
                                "consultant",
                            ]
                        ):
                            title = text
                            break
                        # If we haven't found a title yet and this looks like it could be one (not a location)
                        # Location usually has city/state/country patterns
                        elif title is None and not any(
                            word in text
                            for word in [
                                ", ",
                                " Area",
                                "United States",
                                "Canada",
                                "United Kingdom",
                            ]
                        ):
                            title = text
                if title:
                    break
            except Exception:
                continue

        if title is None:
            title = "Unknown title"
            if self.debug:
                print(f"Could not find title for result {i}, dumping HTML for debugging")
                try:
                    self.dump_html(
                        f"unknown_title_result_{i}", result.evaluate("el => el.outerHTML")
                    )
                except Exception as e:
                    print(f"Could not dump HTML: {e}")

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


def main(company: str, debug: bool = False, headless: bool = True) -> list[Dict]:
    searcher = LinkedInSearcher(debug=debug, headless=headless)
    try:
        searcher.login()

        repo = company_repository()
        company_row = repo.get_by_normalized_name(company)

        # Fallback if unknown
        if company_row is None:
            print(f"LinkedIn: company {company} not found in repo; using raw name.")
            connections = searcher.search_company_connections(company)
            print(f"Found {len(connections)} connections at {company}")
            return connections

        # Candidates: canonical, then aliases by priority manual > auto > seed
        candidates = [company_row.name]

        aliases = repo.list_aliases(company_row.company_id)
        active_aliases = [a for a in aliases if a["is_active"]]
        source_priority = {"manual": 0, "auto": 1, "seed": 2}
        sorted_aliases = sorted(
            active_aliases, key=lambda a: source_priority.get(a["source"], 3)
        )

        for alias in sorted_aliases:
            if alias["alias"] != company_row.name:
                candidates.append(alias["alias"])

        # Try candidates in order
        for candidate_name in candidates:
            connections = searcher.search_company_connections(candidate_name)
            if connections:
                if candidate_name != company_row.name:
                    for alias in active_aliases:
                        if alias["alias"] == candidate_name:
                            repo.set_alias_as_canonical(
                                company_row.company_id, alias["id"]
                            )
                            break
                print(f"Found {len(connections)} connections at {candidate_name}")
                return connections

        print(
            f"LinkedIn: no working names for company_id={company_row.company_id} (tried: {candidates})"
        )
        return []
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
