#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Merchant Verifier Module

This module provides the core functionality for verifying merchant address information
by searching for merchant websites and comparing address details.

It uses browser automation to search for merchant websites and verify address information
against provided merchant data from Excel files.
"""

# Standard library imports
import os
import re
import time
from typing import Dict, Optional, Any, List, Tuple
from urllib.parse import urljoin

# Third-party imports
from playwright.sync_api import Page, sync_playwright

# Local imports
from src.config.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


class MerchantVerifier:
    """
    A class to automate merchant address verification using web search.

    This class handles the process of searching for merchant websites,
    navigating to relevant pages, and verifying address information.
    """

    def __init__(
        self, headless: bool = True, screenshots_dir: str = "verification_screenshots"
    ):
        """
        Initialize the merchant verification system.

        Args:
            headless: Whether to run browser in headless mode (invisible)
            screenshots_dir: Directory to save verification screenshots
        """
        logger.info("Initializing MerchantVerifier")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4472.124 Safari/537.36",
        )

        # Create screenshots directory if it doesn't exist
        os.makedirs(screenshots_dir, exist_ok=True)
        self.screenshots_dir = screenshots_dir

    def __del__(self):
        """Clean up resources upon object destruction."""
        logger.info("Cleaning up MerchantVerifier resources")
        try:
            if hasattr(self, "browser") and self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.debug(f"Browser already closed: {str(e)}")
            if hasattr(self, "playwright") and self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.debug(f"Playwright already stopped: {str(e)}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def clean_text(self, text: str) -> str:
        """
        Clean text for better matching.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""
        # Convert to lowercase
        text = str(text).lower()
        # Remove punctuation
        text = re.sub(r"[^\w\s]", " ", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def is_social_media(self, url: str) -> bool:
        """
        Check if a URL is from a social media site.

        Args:
            url: URL to check

        Returns:
            True if the URL is from a social media site
        """
        social_media_domains = [
            "facebook.com",
            "fb.com",
            "instagram.com",
            "twitter.com",
            "linkedin.com",
            "youtube.com",
            "tiktok.com",
            "pinterest.com",
            "snapchat.com",
            "reddit.com",
            "tumblr.com",
            "whatsapp.com",
            "telegram.org",
            "medium.com",
        ]
        return any(domain in url.lower() for domain in social_media_domains)

    def is_directory_site(self, url: str) -> bool:
        """
        Check if a URL is a directory or review site.

        Args:
            url: URL to check

        Returns:
            True if the URL is a directory or review site
        """
        directory_domains = [
            "yelp.com",
            "tripadvisor.com",
            "yellowpages.com",
            "manta.com",
            "bbb.org",
            "thomasnet.com",
            "angi.com",
            "foursquare.com",
            "mapquest.com",
            "booking.com",
            "expedia.com",
            "hotels.com",
            "glassdoor.com",
            "indeed.com",
            "amazon.com",
            "ebay.com",
        ]
        return any(domain in url.lower() for domain in directory_domains)

    def check_address_match(
        self, page_content: str, merchant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check for address match with enhanced detection.

        Args:
            page_content: HTML content of the page
            merchant_data: Merchant information dictionary

        Returns:
            Dictionary with match results
        """
        # Clean and prepare content
        page_text = self.clean_text(page_content)

        # Extract merchant address components
        address_line = self.clean_text(str(merchant_data["address_line1"]))
        town = self.clean_text(str(merchant_data["town"]))
        postcode = self.clean_text(str(merchant_data["postcode"]))
        country = self.clean_text(str(merchant_data["country"]))

        logger.debug("Looking for address components:")
        logger.debug(f"  Address: '{address_line}'")
        logger.debug(f"  Town: '{town}'")
        logger.debug(f"  Postcode: '{postcode}'")
        logger.debug(f"  Country: '{country}'")

        # Simple check for exact matches
        has_address = address_line in page_text
        has_town = town in page_text
        has_postcode = postcode in page_text
        has_country = country in page_text

        # Try alternative checks for address
        address_words = address_line.split()
        address_word_matches = sum(1 for word in address_words if word in page_text)
        address_partial_match = address_word_matches > len(address_words) / 2

        # Look for nearby address elements (within reasonable proximity)
        # Extract text chunks that might contain address information
        address_chunks = []
        if postcode in page_text:
            # Look for text around the postcode
            postcode_idx = page_text.find(postcode)
            start_idx = max(0, postcode_idx - 100)
            end_idx = min(len(page_text), postcode_idx + 100)
            address_chunks.append(page_text[start_idx:end_idx])

        if town in page_text:
            # Look for text around the town
            town_idx = page_text.find(town)
            start_idx = max(0, town_idx - 100)
            end_idx = min(len(page_text), town_idx + 100)
            address_chunks.append(page_text[start_idx:end_idx])

        # Check if address words appear in these chunks
        nearby_address_match = False
        for chunk in address_chunks:
            address_word_matches = sum(1 for word in address_words if word in chunk)
            if address_word_matches > len(address_words) / 3:
                nearby_address_match = True
                break

        # Calculate confidence based on matches
        confidence = 0
        if has_address:
            confidence += 30
            logger.debug("Found exact address match")
        elif address_partial_match:
            confidence += 15
            logger.debug(
                f"Found partial address match ({address_word_matches}/{len(address_words)} words)"
            )
        elif nearby_address_match:
            confidence += 10
            logger.debug("Found address words near postcode or town")

        if has_town:
            confidence += 20
            logger.debug("Found town match")

        if has_postcode:
            confidence += 40
            logger.debug("Found postcode match")

        if has_country:
            confidence += 10
            logger.debug("Found country match")

        # Cap at 100
        confidence = min(confidence, 100)

        logger.info(f"Address match confidence: {confidence}%")

        # Extract the matching address context
        matching_text = None
        if has_postcode:
            # Extract text around postcode
            postcode_idx = page_text.find(postcode)
            start_idx = max(0, postcode_idx - 50)
            end_idx = min(len(page_text), postcode_idx + 50)
            matching_text = page_text[start_idx:end_idx]
        elif has_town:
            # Extract text around town
            town_idx = page_text.find(town)
            start_idx = max(0, town_idx - 50)
            end_idx = min(len(page_text), town_idx + 50)
            matching_text = page_text[start_idx:end_idx]

        return {
            "has_address": has_address,
            "has_town": has_town,
            "has_postcode": has_postcode,
            "has_country": has_country,
            "address_partial_match": address_partial_match,
            "nearby_address_match": nearby_address_match,
            "confidence": confidence,
            "matching_text": matching_text,
        }

    def search_for_merchant(
        self, query: str, page: Page
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Search for a merchant using multiple search engines.

        Args:
            query: Search query string
            page: Playwright page object

        Returns:
            Tuple of (success, search results)
        """
        search_engines = [
            {
                "name": "DuckDuckGo_HTML",
                "url_template": "https://html.duckduckgo.com/html/?q={query}",
                "link_selector": "div.result__body a.result__a",
                "is_direct_query_url": True,  # Query is in the URL itself
                "consent_selectors": [],  # Usually no consent dialogs
            },
            {
                "name": "Google",
                "url_template": "https://www.google.com",
                "search_input_selector": 'textarea[name="q"]',
                "is_direct_query_url": False,
                "consent_selectors": [
                    "button#L2AGLb",
                    "//button[.//div[contains(text(), 'Accept all')]]",
                    "//button[.//div[contains(text(), 'Tout accepter')]]",
                    'button:has-text("Accept all")',
                    'button:has-text("I agree")',
                    'button:has-text("Agree")',
                    # Fallback: Reject if accept is not found or causes issues
                    "//button[.//div[contains(text(), 'Reject all')]]",
                    "//button[contains(., 'Reject all')]",
                    "//button[contains(., 'Tout refuser')]",
                ],
            },
            {
                "name": "Bing",
                "url_template": "https://www.bing.com",
                "search_input_selector": "input#sb_form_q",
                "is_direct_query_url": False,
                "consent_selectors": [
                    "button#bnp_btn_accept",
                    'button:has-text("Accept all")',
                    'button:has-text("Accept")',
                    # Fallback: Reject
                    "//button[contains(., 'Reject all')]",
                    "//button[contains(., 'Decline')]",
                ],
            },
        ]

        success = False
        search_results = []

        for engine_config in search_engines:
            name = engine_config["name"]
            try:
                logger.info(f"Trying search with {name}...")
                current_url = ""

                if engine_config["is_direct_query_url"]:
                    current_url = engine_config["url_template"].format(query=query)
                    page.goto(current_url, timeout=30000, wait_until="domcontentloaded")
                    page.screenshot(
                        path=os.path.join(
                            self.screenshots_dir, f"{name}_initial_page.png"
                        )
                    )
                else:
                    current_url = engine_config["url_template"]
                    page.goto(current_url, timeout=30000, wait_until="domcontentloaded")
                    page.screenshot(
                        path=os.path.join(
                            self.screenshots_dir, f"{name}_initial_page.png"
                        )
                    )

                    # CAPTCHA/Interstitial check for Google/Bing BEFORE consent/search
                    page_title_lower = page.title().lower()
                    page_content_lower = page.content().lower()
                    captcha_keywords = [
                        "recaptcha",
                        "unusual traffic",
                        "verify you're human",
                        "privacy error",
                    ]
                    interstitial_keywords = [
                        "before you continue",
                        "avant de continuer",
                        "consent choices",
                    ]

                    if any(kw in page_title_lower for kw in captcha_keywords) or any(
                        kw in page_content_lower for kw in captcha_keywords
                    ):
                        logger.warning(
                            f"CAPTCHA detected on {name}. Screenshot: {name}_initial_page.png. Skipping."
                        )
                        continue  # Skip to next engine

                    if name == "Google" and any(
                        kw in page_content_lower for kw in interstitial_keywords
                    ):
                        logger.warning(
                            f"Interstitial page detected on {name}. Screenshot: {name}_initial_page.png. Skipping."
                        )
                        continue

                    # Handle consent dialogs for Google/Bing
                    if engine_config["consent_selectors"]:
                        logger.debug(
                            f"Waiting for potential consent dialogs on {name}..."
                        )
                        page.wait_for_timeout(1000)  # Brief wait for dialogs to appear
                        consent_clicked = False
                        for sel_idx, consent_sel in enumerate(
                            engine_config["consent_selectors"]
                        ):
                            try:
                                consent_button_locator = page.locator(consent_sel)
                                if consent_button_locator.count() > 0:
                                    first_button = consent_button_locator.first
                                    first_button.wait_for(state="visible", timeout=3000)
                                    first_button.wait_for(state="enabled", timeout=3000)
                                    logger.debug(
                                        f"Found {name} consent button with selector: {consent_sel}"
                                    )
                                    first_button.click(timeout=5000)
                                    logger.debug(f"Clicked {name} consent button.")
                                    page.wait_for_timeout(2000)
                                    consent_clicked = True
                                    break
                            except Exception as e_consent:
                                logger.debug(
                                    f"Attempt {sel_idx + 1} to click {name} consent button ({consent_sel}) failed: {str(e_consent)}"
                                )
                        if not consent_clicked:
                            logger.debug(
                                f"Could not click any known {name} consent buttons. Proceeding cautiously."
                            )
                        page.screenshot(
                            path=os.path.join(
                                self.screenshots_dir,
                                f"{name}_after_consent_attempt.png",
                            )
                        )

                    # Perform search for Google/Bing
                    logger.debug(f"Waiting for {name} search box...")
                    search_box_locator = page.locator(
                        engine_config["search_input_selector"]
                    )
                    search_box_locator.wait_for(state="visible", timeout=10000)
                    logger.debug(f"{name} search box found. Entering search query...")
                    search_box_locator.fill(query)
                    logger.debug(f"Query entered for {name}. Submitting search...")
                    search_box_locator.press("Enter")
                    logger.debug(f"{name} search submitted. Waiting for results...")
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception as e_load:
                        logger.warning(
                            f"Problem waiting for load state after {name} search: {e_load}"
                        )
                    time.sleep(3)  # Allow JS to render

                page.screenshot(
                    path=os.path.join(self.screenshots_dir, f"{name}_results_page.png")
                )

                # Extract Links
                extracted_links = []
                if name == "DuckDuckGo_HTML":
                    extracted_links = page.locator(
                        engine_config["link_selector"]
                    ).evaluate_all(
                        """
                        links => links.map(link => ({
                            url: link.href,
                            text: link.textContent ? link.textContent.trim() : ""
                        }))
                        """
                    )
                else:  # Google, Bing
                    # A more general selector for result links
                    google_bing_link_selectors = [
                        "div#search a[href^='http']:not([href*='google.com']):not([href*='bing.com'])",
                        "li.b_algo a[href^='http']",
                        "a[href^='http'][data-ved]",
                        "a[h*='ID=SERP']",
                        "a[href^='http']",  # Fallback, very broad
                    ]
                    for sel in google_bing_link_selectors:
                        try:
                            temp_links = page.locator(sel).evaluate_all(
                                """
                                links => links.filter(link => link.href && !link.href.startsWith('javascript:') && link.offsetParent !== null)
                                            .map(link => ({
                                                url: link.href,
                                                text: link.innerText ? link.innerText.trim() : (link.textContent ? link.textContent.trim() : "")
                                            }))
                                """
                            )
                            if temp_links:
                                extracted_links.extend(temp_links)
                                # Break if we got a good number of links from a specific selector
                                if len(extracted_links) > 10:
                                    break
                        except Exception as e_link_extract:
                            logger.debug(
                                f"Error extracting links with selector '{sel}' on {name}: {e_link_extract}"
                            )
                    # Deduplicate links based on URL
                    seen_urls = set()
                    unique_links = []
                    for link_item in extracted_links:
                        if link_item["url"] not in seen_urls:
                            unique_links.append(link_item)
                            seen_urls.add(link_item["url"])
                    extracted_links = unique_links

                if not extracted_links:
                    logger.warning(f"No links extracted from {name}.")
                    continue  # Try next engine

                logger.info(
                    f"Extracted {len(extracted_links)} raw links from {name}. Filtering..."
                )

                # Filter out search engine domains and excluded sites
                excluded_domains_common = [
                    "google.",
                    "bing.com",
                    "duckduckgo.com",
                    "youtube.com",
                    "wikipedia.org",
                    "amazon.",
                    "pinterest.",
                    "microsoft.com",
                    "apple.com",
                    "support.google.com",
                    "maps.google.com",
                    "translate.google.com",
                    "books.google.com",
                    "policies.google.com",
                    "play.google.com",
                    "news.google.com",
                    "accounts.google.com",
                ]

                temp_filtered_links = []
                for link_data in extracted_links:
                    link_url = link_data.get("url")
                    if not link_url:
                        continue
                    try:
                        # Basic check to avoid malformed URLs
                        if not isinstance(link_url, str) or not link_url.startswith(
                            ("http://", "https://")
                        ):
                            continue
                        if not any(
                            ex_domain in link_url.lower()
                            for ex_domain in excluded_domains_common
                        ):
                            temp_filtered_links.append(link_data)
                    except TypeError:
                        logger.debug(f"Skipping malformed link data: {link_data}")
                        continue

                extracted_links = temp_filtered_links

                # Filter for business vs directory sites
                business_links = []
                directory_links_buffer = []

                for link_data in extracted_links:
                    link_url = link_data["url"]
                    if not self.is_social_media(
                        link_url
                    ) and not self.is_directory_site(link_url):
                        business_links.append(link_data)
                    elif not self.is_social_media(link_url) and self.is_directory_site(
                        link_url
                    ):
                        directory_links_buffer.append(link_data)

                # Prioritize business links, then add directory links if needed
                final_filtered_links = business_links
                if len(final_filtered_links) < 7:  # Aim for a decent pool
                    needed = 7 - len(final_filtered_links)
                    final_filtered_links.extend(directory_links_buffer[:needed])

                if final_filtered_links:
                    logger.info(
                        f"Found {len(final_filtered_links)} potential websites from {name} after filtering."
                    )
                    search_results = final_filtered_links[:15]  # Take top results
                    success = True
                    break  # Successfully found results, exit search engine loop
                else:
                    logger.warning(
                        f"No suitable links found on {name} after all filtering."
                    )

            except Exception as e:
                logger.error(f"Error with {name} search: {type(e).__name__} - {str(e)}")
                try:
                    page.screenshot(
                        path=os.path.join(self.screenshots_dir, f"{name}_error.png")
                    )
                except Exception:
                    pass
                continue  # Try next search engine

        return success, search_results

    def try_direct_url_guessing(
        self, merchant_data: Dict[str, Any], page: Page
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """
        Try direct URL guessing for merchant website.

        Args:
            merchant_data: Merchant information
            page: Playwright page object

        Returns:
            Tuple of (success, result dictionary or None)
        """
        logger.info("Trying direct URL guessing...")
        merchant_name_clean = (
            merchant_data["merchant_name"]
            .lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("'", "")
        )
        possible_domains = [
            f"www.{merchant_name_clean}.com",
            f"www.{merchant_name_clean}.fr",
            f"{merchant_name_clean}.com",
            f"{merchant_name_clean}.fr",
        ]
        merchant_name_dashed = (
            merchant_data["merchant_name"].lower().replace(" ", "-").replace("'", "")
        )
        possible_domains.extend(
            [
                f"www.{merchant_name_dashed}.com",
                f"www.{merchant_name_dashed}.fr",
                f"{merchant_name_dashed}.com",
                f"{merchant_name_dashed}.fr",
            ]
        )

        success = False
        result = None

        for domain_attempt in possible_domains:
            try:
                logger.info(f"Trying direct URL: https://{domain_attempt}")
                page.goto(
                    f"https://{domain_attempt}",
                    timeout=10000,
                    wait_until="domcontentloaded",
                )
                time.sleep(2)
                screenshot_path = os.path.join(
                    self.screenshots_dir,
                    f"direct_{domain_attempt.replace('/', '_')}.png",
                )
                page.screenshot(path=screenshot_path)

                if (
                    page.url != "about:blank"
                    and "404" not in page.title().lower()
                    and "not found" not in page.content().lower()
                ):
                    logger.info(f"Successfully loaded direct URL: {page.url}")
                    result = {
                        "url": page.url,
                        "text": page.title() or "Directly Accessed Page",
                    }
                    success = True
                    break
            except Exception as e_direct:
                logger.warning(
                    f"Error loading direct URL {domain_attempt}: {str(e_direct)}"
                )
                continue

        return success, result

    def find_and_verify_merchant(
        self, merchant_data: Dict[str, Any], max_websites: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Find merchant website and verify address information.

        Args:
            merchant_data: Dictionary containing merchant information
            max_websites: Maximum number of websites to check

        Returns:
            Dictionary with verification results or None if verification failed
        """
        logger.info(
            f"Starting verification for merchant: {merchant_data['merchant_name']}"
        )

        # Prepare search query including name, location, and "site" to prioritize official sites
        search_query = f"{merchant_data['merchant_name']} {merchant_data['town']} {merchant_data['country']} site"

        try:
            # Create a new page for search
            page = self.context.new_page()

            # Step 1: Search for the merchant
            search_success, search_results = self.search_for_merchant(
                search_query, page
            )

            # Step 2: If search failed, try direct URL guessing
            if not search_success or not search_results:
                direct_success, direct_result = self.try_direct_url_guessing(
                    merchant_data, page
                )
                if direct_success and direct_result:
                    search_success = True
                    search_results = [direct_result]

            # Step 3: Process search results
            verification_results = []

            if search_success and search_results:
                logger.info(f"Found {len(search_results)} potential websites to check.")
                websites_checked = 0

                for result in search_results:
                    url = result["url"]

                    # Skip social media sites
                    if self.is_social_media(url):
                        logger.debug(f"Skipping social media site: {url}")
                        continue

                    websites_checked += 1
                    logger.info(
                        f"Checking website {websites_checked}/{max_websites}: {url}"
                    )

                    if websites_checked > max_websites:
                        logger.info(
                            f"Reached maximum number of websites to check ({max_websites})"
                        )
                        break

                    try:
                        # Navigate to website
                        try:
                            page.goto(url, timeout=20000, wait_until="domcontentloaded")
                            time.sleep(3)  # Allow page to settle
                        except Exception as e_nav:
                            logger.error(f"Error navigating to {url}: {str(e_nav)}")
                            page.screenshot(
                                path=os.path.join(
                                    self.screenshots_dir,
                                    f"website_{websites_checked}_nav_error.png",
                                )
                            )
                            continue

                        screenshot_path = os.path.join(
                            self.screenshots_dir,
                            f"website_{websites_checked}_{page.title()[:20].replace(' ', '_')}.png",
                        )
                        page.screenshot(path=screenshot_path, full_page=False)

                        # Extract page content AFTER navigation and settling
                        page_content = page.content()
                        match_results = self.check_address_match(
                            page_content, merchant_data
                        )

                        current_verification_result = {
                            "url": page.url,  # Use page.url for canonical URL
                            "title": page.title(),
                            "address_found": match_results["has_address"]
                            or match_results["has_town"]
                            or match_results["has_postcode"],
                            "address_match": match_results["matching_text"],
                            "address_match_confidence": match_results["confidence"],
                            "screenshot_path": screenshot_path,
                            "verified": match_results["confidence"]
                            > 50,  # Threshold for verification
                        }
                        verification_results.append(current_verification_result)

                        # If high confidence match, capture address section and stop search
                        if match_results["confidence"] > 70:
                            logger.info("Found high confidence match, stopping search.")
                            try:
                                selectors = [
                                    f"*:text-matches('{merchant_data['postcode']}')",
                                    f"*:text-matches('{merchant_data['town']}')",
                                    "footer",
                                    ".address",
                                    ".contact",
                                    ".location",
                                    "#contact",
                                    "#address",
                                    "address",
                                ]
                                for selector in selectors:
                                    try:
                                        if page.locator(selector).count() > 0:
                                            page.locator(
                                                selector
                                            ).first.scroll_into_view_if_needed()
                                            address_screenshot_path = os.path.join(
                                                self.screenshots_dir,
                                                f"website_{websites_checked}_address_section.png",
                                            )
                                            page.screenshot(
                                                path=address_screenshot_path
                                            )
                                            current_verification_result[
                                                "address_screenshot_path"
                                            ] = address_screenshot_path
                                            break
                                    except Exception:
                                        continue
                            except Exception as e_addr_ss:
                                logger.warning(
                                    f"Error capturing address section screenshot: {str(e_addr_ss)}"
                                )
                            break  # Break from website checking loop

                        # Try to check contact page
                        try:
                            contact_page_links = page.locator(
                                "a:text-matches('contact|nous trouver|find us|location', 'i')"
                            )
                            if contact_page_links.count() > 0:
                                contact_link_element = contact_page_links.first
                                contact_url_relative = (
                                    contact_link_element.get_attribute("href")
                                )
                                if contact_url_relative:
                                    contact_url_absolute = urljoin(
                                        page.url, contact_url_relative
                                    )
                                    logger.info(
                                        f"Found potential contact page: {contact_url_absolute}"
                                    )

                                    page.goto(
                                        contact_url_absolute,
                                        timeout=15000,
                                        wait_until="domcontentloaded",
                                    )
                                    time.sleep(2)
                                    contact_screenshot_path = os.path.join(
                                        self.screenshots_dir,
                                        f"contact_page_{websites_checked}.png",
                                    )
                                    page.screenshot(path=contact_screenshot_path)

                                    contact_content = page.content()
                                    contact_match_results = self.check_address_match(
                                        contact_content, merchant_data
                                    )

                                    if (
                                        contact_match_results["confidence"]
                                        > current_verification_result[
                                            "address_match_confidence"
                                        ]
                                    ):
                                        logger.info(
                                            f"Contact page has better match: {contact_match_results['confidence']}%"
                                        )
                                        # Update the current result with contact page data
                                        verification_results[-1].update(
                                            {
                                                "url": page.url,
                                                "title": page.title(),
                                                "address_found": contact_match_results[
                                                    "has_address"
                                                ]
                                                or contact_match_results["has_town"]
                                                or contact_match_results[
                                                    "has_postcode"
                                                ],
                                                "address_match": contact_match_results[
                                                    "matching_text"
                                                ],
                                                "address_match_confidence": contact_match_results[
                                                    "confidence"
                                                ],
                                                "screenshot_path": contact_screenshot_path,
                                                "verified": contact_match_results[
                                                    "confidence"
                                                ]
                                                > 50,
                                                "is_contact_page": True,
                                            }
                                        )
                                        if contact_match_results["confidence"] > 70:
                                            logger.info(
                                                "Found high confidence match on contact page, stopping search."
                                            )
                                            break  # Break from website checking loop
                        except Exception as e_contact:
                            logger.warning(
                                f"Error checking contact page: {str(e_contact)}"
                            )
                    except Exception as e_site:
                        logger.error(f"Error processing website {url}: {str(e_site)}")
                        continue

            # Return best result if we have any
            if verification_results:
                best_result = max(
                    verification_results,
                    key=lambda x: x.get("address_match_confidence", 0),
                )
                return best_result

            return None

        except Exception as e:
            logger.error(f"Error during merchant verification: {str(e)}")
            return None
        finally:
            if "page" in locals():
                try:
                    page.close()
                except Exception:
                    pass
