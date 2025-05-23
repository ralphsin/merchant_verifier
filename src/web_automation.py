#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/web_automation.py

"""
Web Automation Module

This module provides utilities for web automation tasks using Playwright.
It includes classes and functions for browser management, web searches using DuckDuckGo,
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
    A class that provides general web automation capabilities using DuckDuckGo search.

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

    def duckduckgo_search(
        self, query: str, num_results: int = 10
    ) -> Tuple[Page, List[Dict[str, str]]]:
        """
        Perform a DuckDuckGo search and extract results.

        Args:
            query: Search query string
            num_results: Maximum number of results to extract

        Returns:
            Tuple of (Page object, List of result dictionaries with url and text)

        Raises:
            Exception: If search fails after multiple attempts
        """
        logger.info(f"Performing DuckDuckGo search for: {query}")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                page = self.context.new_page()

                # Use DuckDuckGo HTML version (no JavaScript required)
                search_url = (
                    f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                )

                if not self.navigate(page, search_url):
                    retry_count += 1
                    page.close()
                    continue

                # Wait for results to load
                page.wait_for_selector("div.result", timeout=10000)

                # Add random delay to avoid detection
                time.sleep(random.uniform(1, 3))

                # Take screenshot of search results
                search_screenshot = os.path.join(
                    self.screenshots_dir,
                    f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                )
                page.screenshot(path=search_screenshot)
                logger.info(f"Search results screenshot: {search_screenshot}")

                # Extract search results using DuckDuckGo's HTML structure
                results = page.eval_on_selector_all(
                    "div.result h2.result__title a",
                    """
                        (links) => links.map(link => {
                            return {
                                url: link.href,
                                text: link.textContent.trim()
                            }
                        }).filter(result => result.url && !result.url.includes('duckduckgo.com'))
                    """,
                )

                # Limit to requested number of results
                results = results[:num_results]

                logger.info(f"Found {len(results)} search results from DuckDuckGo")
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
            f"Failed to perform DuckDuckGo search for '{query}' after {max_retries} attempts"
        )
        raise Exception(
            f"Failed to perform DuckDuckGo search after {max_retries} attempts"
        )

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

    def find_address_on_page(
        self, page: Page, merchant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Find and capture address information on a web page.

        Args:
            page: Playwright page object
            merchant_data: Dictionary containing merchant information

        Returns:
            Dictionary with address finding results
        """
        result = {
            "address_found": False,
            "address_confidence": 0,
            "address_text": None,
            "screenshot_path": None,
            "address_screenshot_path": None,
        }

        try:
            # Extract page content
            page_text = page.evaluate("() => document.body.innerText").lower()

            # Get merchant address components
            merchant_name = str(merchant_data.get("merchant_name", "")).lower()
            address_line = str(merchant_data.get("address_line1", "")).lower()
            town = str(merchant_data.get("town", "")).lower()
            postcode = str(merchant_data.get("postcode", "")).lower()
            country = str(merchant_data.get("country", "")).lower()

            logger.info(f"Looking for address components on {page.url}")
            logger.debug(f"  Merchant: {merchant_name}")
            logger.debug(f"  Address: {address_line}")
            logger.debug(f"  Town: {town}")
            logger.debug(f"  Postcode: {postcode}")
            logger.debug(f"  Country: {country}")

            # Check for matches
            confidence = 0
            found_components = []

            if merchant_name and merchant_name in page_text:
                confidence += 20
                found_components.append("merchant_name")
                logger.debug("✓ Found merchant name")

            if address_line and address_line in page_text:
                confidence += 30
                found_components.append("address")
                logger.debug("✓ Found address")

            if town and town in page_text:
                confidence += 25
                found_components.append("town")
                logger.debug("✓ Found town")

            if postcode and postcode in page_text:
                confidence += 35
                found_components.append("postcode")
                logger.debug("✓ Found postcode")

            if country and country in page_text:
                confidence += 10
                found_components.append("country")
                logger.debug("✓ Found country")

            # Partial address matching
            if address_line:
                address_words = address_line.split()
                found_words = sum(1 for word in address_words if word in page_text)
                if found_words > len(address_words) / 2:
                    confidence += 15
                    found_components.append("partial_address")
                    logger.debug(
                        f"✓ Found partial address ({found_words}/{len(address_words)} words)"
                    )

            result["address_confidence"] = min(confidence, 100)
            result["address_found"] = confidence > 30

            if result["address_found"]:
                logger.info(f"Address found with {confidence}% confidence")

                # Take full page screenshot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_filename = f"page_{merchant_data.get('merchant_id', 'unknown')}_{timestamp}.png"
                result["screenshot_path"] = self.take_screenshot(
                    page, screenshot_filename, full_page=True
                )

                # Try to find and screenshot specific address sections
                address_selectors = [
                    "footer",
                    ".address",
                    ".contact",
                    ".location",
                    "#contact",
                    "#address",
                    "address",
                    ".footer",
                    "[class*='address']",
                    "[class*='contact']",
                    "[id*='address']",
                    "[id*='contact']",
                ]

                # Also look for elements containing postcode or town
                if postcode:
                    try:
                        postcode_elements = page.locator(f"text={postcode}").all()
                        if postcode_elements:
                            logger.info("Found postcode on page, scrolling to it")
                            postcode_elements[0].scroll_into_view_if_needed()
                            time.sleep(1)
                            address_screenshot_filename = f"address_{merchant_data.get('merchant_id', 'unknown')}_{timestamp}.png"
                            result["address_screenshot_path"] = self.take_screenshot(
                                page, address_screenshot_filename, full_page=False
                            )
                    except Exception as e:
                        logger.debug(f"Could not scroll to postcode: {e}")

                # If no postcode element found, try other selectors
                if not result.get("address_screenshot_path"):
                    for selector in address_selectors:
                        try:
                            elements = page.locator(selector).all()
                            if elements:
                                logger.info(
                                    f"Found address section with selector: {selector}"
                                )
                                elements[0].scroll_into_view_if_needed()
                                time.sleep(1)
                                address_screenshot_filename = f"address_{merchant_data.get('merchant_id', 'unknown')}_{timestamp}.png"
                                result["address_screenshot_path"] = (
                                    self.take_screenshot(
                                        page,
                                        address_screenshot_filename,
                                        full_page=False,
                                    )
                                )
                                break
                        except Exception as e:
                            logger.debug(f"Could not use selector {selector}: {e}")
                            continue

                # Extract surrounding text for address context
                if postcode and postcode in page_text:
                    postcode_idx = page_text.find(postcode)
                    start_idx = max(0, postcode_idx - 100)
                    end_idx = min(len(page_text), postcode_idx + 100)
                    result["address_text"] = page_text[start_idx:end_idx].strip()
                elif town and town in page_text:
                    town_idx = page_text.find(town)
                    start_idx = max(0, town_idx - 100)
                    end_idx = min(len(page_text), town_idx + 100)
                    result["address_text"] = page_text[start_idx:end_idx].strip()

            else:
                logger.info(f"Address not found (confidence: {confidence}%)")

            return result

        except Exception as e:
            logger.error(f"Error finding address on page: {str(e)}")
            return result

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


def process_merchant_verification(
    excel_file_path: str, output_dir: str = "verification_results"
) -> Dict[str, Any]:
    """
    Process all merchants from Excel file and verify their addresses online.

    Args:
        excel_file_path: Path to the Excel file containing merchant data
        output_dir: Directory to save verification results and screenshots

    Returns:
        Dictionary containing verification results for all merchants
    """
    from src.data_extractor import extract_merchant_data

    logger.info(f"Starting merchant verification process for: {excel_file_path}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    screenshots_dir = os.path.join(output_dir, "screenshots")

    # Initialize web automator
    automator = WebAutomator(headless=False, screenshots_dir=screenshots_dir)

    try:
        # Extract merchant data from Excel
        merchants_df = extract_merchant_data(excel_file_path)
        logger.info(f"Found {len(merchants_df)} merchants to verify")

        verification_results = {
            "total_merchants": len(merchants_df),
            "processed_merchants": 0,
            "successful_verifications": 0,
            "results": [],
        }

        # Process each merchant
        for index, merchant in merchants_df.iterrows():
            merchant_id = merchant["merchant_id"]
            merchant_name = merchant["merchant_name"]

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing Merchant {index + 1}/{len(merchants_df)}")
            logger.info(f"ID: {merchant_id}")
            logger.info(f"Name: {merchant_name}")
            logger.info(f"Address: {merchant['address_line1']}")
            logger.info(f"Town: {merchant['town']}")
            logger.info(f"Postcode: {merchant['postcode']}")
            logger.info(f"{'=' * 60}")

            merchant_result = {
                "merchant_id": merchant_id,
                "merchant_name": merchant_name,
                "search_successful": False,
                "websites_checked": 0,
                "best_match": None,
                "all_results": [],
            }

            try:
                # Create search query
                search_query = (
                    f'"{merchant_name}" {merchant["town"]} {merchant["country"]}'
                )

                # Perform DuckDuckGo search
                search_page, search_results = automator.duckduckgo_search(
                    search_query, num_results=10
                )

                if search_results:
                    merchant_result["search_successful"] = True
                    logger.info(f"Found {len(search_results)} search results")

                    # Filter out unwanted sites
                    filtered_results = []
                    unwanted_domains = [
                        "facebook.com",
                        "linkedin.com",
                        "twitter.com",
                        "instagram.com",
                        "youtube.com",
                        "yelp.com",
                        "tripadvisor.com",
                        "booking.com",
                        "amazon.com",
                        "ebay.com",
                    ]

                    for result in search_results:
                        url = result["url"].lower()
                        if not any(domain in url for domain in unwanted_domains):
                            filtered_results.append(result)

                    logger.info(
                        f"After filtering: {len(filtered_results)} relevant results"
                    )

                    # Check each website
                    max_sites_to_check = 5
                    best_confidence = 0
                    best_result = None

                    for i, result in enumerate(filtered_results[:max_sites_to_check]):
                        website_url = result["url"]
                        logger.info(
                            f"Checking website {i + 1}/{min(len(filtered_results), max_sites_to_check)}: {website_url}"
                        )

                        try:
                            # Navigate to website
                            website_page = automator.new_page()
                            if automator.navigate(website_page, website_url):
                                # Handle popups
                                automator.handle_common_popups(website_page)
                                time.sleep(2)  # Allow page to settle

                                # Find address on page
                                address_result = automator.find_address_on_page(
                                    website_page, merchant.to_dict()
                                )

                                website_result = {
                                    "url": website_url,
                                    "title": website_page.title(),
                                    "address_found": address_result["address_found"],
                                    "confidence": address_result["address_confidence"],
                                    "address_text": address_result["address_text"],
                                    "screenshot_path": address_result[
                                        "screenshot_path"
                                    ],
                                    "address_screenshot_path": address_result[
                                        "address_screenshot_path"
                                    ],
                                }

                                merchant_result["all_results"].append(website_result)
                                merchant_result["websites_checked"] += 1

                                # Update best match if this is better
                                if (
                                    address_result["address_confidence"]
                                    > best_confidence
                                ):
                                    best_confidence = address_result[
                                        "address_confidence"
                                    ]
                                    best_result = website_result

                                logger.info(
                                    f"Website processed - Confidence: {address_result['address_confidence']}%"
                                )

                                # If we found a very good match, stop searching
                                if address_result["address_confidence"] > 80:
                                    logger.info(
                                        "High confidence match found, stopping search"
                                    )
                                    break

                            else:
                                logger.warning(f"Could not navigate to {website_url}")

                        except Exception as e:
                            logger.error(
                                f"Error processing website {website_url}: {str(e)}"
                            )
                        finally:
                            try:
                                website_page.close()
                            except Exception as e:
                                logger.error(f"Error closing website page: {str(e)}")

                    merchant_result["best_match"] = best_result
                    if best_result and best_result["address_found"]:
                        verification_results["successful_verifications"] += 1

                else:
                    logger.warning("No search results found")

                # Close search page
                search_page.close()

            except Exception as e:
                logger.error(f"Error processing merchant {merchant_id}: {str(e)}")

            verification_results["results"].append(merchant_result)
            verification_results["processed_merchants"] += 1

            # Add delay between merchants to be respectful
            time.sleep(random.uniform(2, 5))

        logger.info(f"\n{'=' * 60}")
        logger.info("VERIFICATION COMPLETE")
        logger.info(f"Total merchants: {verification_results['total_merchants']}")
        logger.info(f"Processed: {verification_results['processed_merchants']}")
        logger.info(
            f"Successful verifications: {verification_results['successful_verifications']}"
        )
        logger.info(
            f"Success rate: {verification_results['successful_verifications'] / verification_results['processed_merchants'] * 100:.1f}%"
        )
        logger.info(f"{'=' * 60}")

        return verification_results

    except Exception as e:
        logger.error(f"Error in merchant verification process: {str(e)}")
        raise
    finally:
        # Cleanup
        try:
            del automator
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


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
