#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Automation Module

This module provides utilities for web automation tasks using Playwright.
It includes classes and functions for browser management, web searches,
screenshot capture, and handling common web page interactions.
"""

# Standard library imports
import os
import time
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Third-party imports
from playwright.sync_api import sync_playwright, Page
import requests

# Local imports
from src.config.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


class WebAutomator:
    """
    A class that provides general web automation capabilities.

    This class manages browser instances and provides methods for
    common web automation tasks like navigation, searching, and
    capturing screenshots.
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        screenshots_dir: str = "screenshots",
        timeout: int = 30000,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the web automation system.

        Args:
            headless: Whether to run browser in headless mode (invisible)
            browser_type: Type of browser to use ("chromium", "firefox", or "webkit")
            screenshots_dir: Directory to save screenshots
            timeout: Default timeout for operations in milliseconds
            user_agent: Custom user agent string (None to use default)
        """
        logger.info(
            f"Initializing WebAutomator with {browser_type} browser (headless={headless})"
        )

        self.playwright = sync_playwright().start()
        self.browser_type = browser_type.lower()
        self.timeout = timeout

        # Select browser based on browser_type
        if self.browser_type == "firefox":
            self.browser = self.playwright.firefox.launch(headless=headless)
        elif self.browser_type == "webkit":
            self.browser = self.playwright.webkit.launch(headless=headless)
        else:  # Default to chromium
            self.browser = self.playwright.chromium.launch(headless=headless)

        # Set up default user agent if none provided
        if user_agent is None:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"

        # Create browser context with viewport and user agent
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800}, user_agent=user_agent
        )

        # Set default timeout
        self.context.set_default_timeout(timeout)

        # Create screenshots directory if it doesn't exist
        if screenshots_dir:
            os.makedirs(screenshots_dir, exist_ok=True)
            self.screenshots_dir = screenshots_dir

    def __del__(self):
        """Clean up resources upon object destruction."""
        logger.info("Cleaning up WebAutomator resources")
        try:
            if hasattr(self, "browser") and self.browser:
                self.browser.close()
            if hasattr(self, "playwright") and self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def new_page(self) -> Page:
        """
        Create a new browser page.

        Returns:
            New Playwright page object
        """
        return self.context.new_page()

    def navigate(
        self, page: Page, url: str, wait_until: str = "domcontentloaded"
    ) -> bool:
        """
        Navigate to a URL with error handling.

        Args:
            page: Playwright page object
            url: URL to navigate to
            wait_until: Navigation wait condition ("domcontentloaded", "load", "networkidle")

        Returns:
            True if navigation was successful, False otherwise
        """
        try:
            logger.info(f"Navigating to: {url}")
            response = page.goto(url, wait_until=wait_until, timeout=self.timeout)

            # Check if page loaded successfully
            if not response:
                logger.warning(f"No response received when navigating to {url}")
                return False

            if response.status >= 400:
                logger.warning(
                    f"Received status code {response.status} when navigating to {url}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Navigation error for {url}: {str(e)}")
            return False

    def take_screenshot(
        self, page: Page, filename: Optional[str] = None, full_page: bool = False
    ) -> Optional[str]:
        """
        Take a screenshot of the current page.

        Args:
            page: Playwright page object
            filename: Optional filename for the screenshot (generated if None)
            full_page: Whether to capture the full page or just the viewport

        Returns:
            Path to the saved screenshot or None if failed
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_url = re.sub(r"[^\w\-_]", "_", page.url)[:50]  # Limit length
                filename = f"{timestamp}_{clean_url}.png"

            # Ensure filename has .png extension
            if not filename.lower().endswith(".png"):
                filename += ".png"

            # Create full path
            screenshot_path = os.path.join(self.screenshots_dir, filename)

            # Take screenshot
            page.screenshot(path=screenshot_path, full_page=full_page)
            logger.info(f"Screenshot saved: {screenshot_path}")

            return screenshot_path

        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None

    def handle_common_popups(self, page: Page) -> bool:
        """
        Handle common popups and consent banners.

        Args:
            page: Playwright page object

        Returns:
            True if any popup was handled, False otherwise
        """
        # Common selectors for cookie consent popups
        popup_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Accept")',
            'button:has-text("OK")',
            'button:has-text("Close")',
            'button:has-text("Got it")',
            'button:has-text("I understand")',
            'button:has-text("I agree")',
            ".cookie-banner button",
            ".consent-banner button",
            ".gdpr-banner button",
            ".privacy-banner button",
            '[id*="cookie"] button',
            '[class*="cookie"] button',
            '[id*="gdpr"] button',
            '[class*="gdpr"] button',
            'a:has-text("Accept All")',
            'a:has-text("Accept Cookies")',
        ]

        handled = False
        # Try each selector
        for selector in popup_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.click(selector, timeout=2000)  # Short timeout
                    time.sleep(0.5)  # Brief pause
                    logger.debug(f"Clicked popup selector: {selector}")
                    handled = True
            except Exception:
                continue

        return handled

    def google_search(
        self, query: str, num_results: int = 10
    ) -> Tuple[Page, List[Dict[str, str]]]:
        """
        Perform a Google search and extract results.

        Args:
            query: Search query string
            num_results: Maximum number of results to extract

        Returns:
            Tuple of (Page object, List of result dictionaries with url and text)

        Raises:
            Exception: If search fails after multiple attempts
        """
        logger.info(f"Performing Google search for: {query}")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                page = self.context.new_page()

                # Navigate to Google
                if not self.navigate(page, "https://www.google.com"):
                    retry_count += 1
                    page.close()
                    continue

                # Handle cookie dialog if it appears
                try:
                    if page.locator('text="Accept all"').count() > 0:
                        page.click('text="Accept all"')
                except Exception as e:
                    logger.warning(f"Cookie dialog handling failed: {str(e)}")

                # Enter search query
                page.fill('input[name="q"]', query)
                page.press('input[name="q"]', "Enter")

                # Wait for results to load
                page.wait_for_selector("div#search", timeout=10000)

                # Add random delay to avoid detection
                time.sleep(random.uniform(1, 3))

                # Extract search results
                results = page.eval_on_selector_all(
                    "div#search a[href^='http']:not([href*='google'])",
                    """
                        (links) => links.map(link => {
                            return {
                                url: link.href,
                                text: link.textContent
                            }
                        })
                    """,
                )

                # Limit to requested number of results
                results = results[:num_results]

                logger.info(f"Found {len(results)} search results")
                return page, results

            except Exception as e:
                retry_count += 1
                logger.warning(f"Search attempt {retry_count} failed: {str(e)}")
                time.sleep(2**retry_count)  # Exponential backoff

                # Close page if it exists
                if "page" in locals() and page:
                    try:
                        page.close()
                    except Exception:
                        pass

        logger.error(
            f"Failed to perform Google search for '{query}' after {max_retries} attempts"
        )
        raise Exception(f"Failed to perform Google search after {max_retries} attempts")

    def extract_page_content(self, page: Page) -> Dict[str, Any]:
        """
        Extract structured content from a page.

        Args:
            page: Playwright page object

        Returns:
            Dictionary containing extracted page content
        """
        # Wait for content to load
        page.wait_for_load_state("domcontentloaded")

        # Extract basic page information
        page_info = {
            "url": page.url,
            "title": page.title(),
            "html": page.content(),
            "text": page.evaluate("() => document.body.innerText"),
            "links": [],
            "has_contact_page": False,
            "has_about_page": False,
            "metadata": {},
        }

        # Extract metadata
        metadata = page.evaluate("""
            () => {
                const metadata = {};
                const metaTags = document.querySelectorAll('meta');
                metaTags.forEach(tag => {
                    const name = tag.getAttribute('name') || tag.getAttribute('property');
                    const content = tag.getAttribute('content');
                    if (name && content) {
                        metadata[name] = content;
                    }
                });
                return metadata;
            }
        """)
        page_info["metadata"] = metadata

        # Extract links
        links = page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => {
                    return {
                        text: a.innerText.trim(),
                        href: a.href
                    };
                }).filter(link => link.href.startsWith('http'));
            }
        """)
        page_info["links"] = links

        # Check for contact/about pages
        for link in links:
            link_text = link.get("text", "").lower()
            link_href = link.get("href", "").lower()

            if "contact" in link_text or "contact" in link_href:
                page_info["has_contact_page"] = True
                page_info["contact_link"] = link.get("href")

            if "about" in link_text or "about" in link_href:
                page_info["has_about_page"] = True
                page_info["about_link"] = link.get("href")

        logger.debug(
            f"Extracted content from {page.url}: {len(page_info['text'])} chars of text"
        )
        return page_info

    def wait_for_page_idle(self, page: Page, timeout: int = 5000) -> None:
        """
        Wait for a page to become idle (no network activity).

        Args:
            page: Playwright page object
            timeout: Maximum time to wait in milliseconds
        """
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.debug(f"Wait for idle timed out: {str(e)}")
            # Not treating this as an error, just a timeout


def check_url_accessibility(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Check if a URL is accessible without using a browser.

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        Dictionary with accessibility information
    """
    result = {
        "url": url,
        "accessible": False,
        "status_code": None,
        "error": None,
        "response_time": None,
        "content_type": None,
    }

    try:
        start_time = time.time()
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        end_time = time.time()

        result["response_time"] = round((end_time - start_time) * 1000)  # ms
        result["status_code"] = response.status_code
        result["accessible"] = 200 <= response.status_code < 400
        result["content_type"] = response.headers.get("Content-Type")

    except requests.RequestException as e:
        result["error"] = str(e)

    return result


def batch_check_urls(urls: List[str], max_concurrent: int = 5) -> List[Dict[str, Any]]:
    """
    Check accessibility of multiple URLs in parallel.

    Args:
        urls: List of URLs to check
        max_concurrent: Maximum number of concurrent requests

    Returns:
        List of result dictionaries for each URL
    """
    import concurrent.futures

    results = []
    unique_urls = list(set(urls))  # Remove duplicates

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_url = {
            executor.submit(check_url_accessibility, url): url for url in unique_urls
        }

        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"url": url, "accessible": False, "error": str(e)})

    return results
