#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Address Matcher Module

This module provides utilities for matching and comparing addresses between
different sources, particularly between structured merchant data and
unstructured text found on websites.

It includes functions for address normalization, comparison, and confidence scoring
using fuzzy matching algorithms.
"""

# Standard library imports
import re
from typing import Dict, List, Optional, Any, Tuple

# Third-party imports
from fuzzywuzzy import fuzz

# Local imports
from src.config.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def normalize_address(address: str) -> str:
    """
    Normalize an address string for better comparison.

    This function:
    - Converts to lowercase
    - Removes punctuation
    - Standardizes whitespace
    - Removes common words like "street", "road", etc.

    Args:
        address: The address string to normalize

    Returns:
        Normalized address string
    """
    if not address:
        return ""

    # Convert to lowercase
    address = address.lower()

    # Replace common abbreviations
    replacements = {
        "st.": "street",
        "st ": "street ",
        "rd.": "road",
        "rd ": "road ",
        "ave.": "avenue",
        "ave ": "avenue ",
        "dr.": "drive",
        "dr ": "drive ",
        "ln.": "lane",
        "ln ": "lane ",
        "blvd.": "boulevard",
        "blvd ": "boulevard ",
    }

    for old, new in replacements.items():
        address = address.replace(old, new)

    # Remove punctuation except for postal code patterns
    address = re.sub(r"[^\w\s]", " ", address)

    # Standardize whitespace
    address = re.sub(r"\s+", " ", address).strip()

    return address


def extract_address_components(address: str) -> Dict[str, str]:
    """
    Extract components from an address string.

    Attempts to identify and extract postal code, city/town, street name,
    and building number from an address string.

    Args:
        address: The address string to parse

    Returns:
        Dictionary with extracted address components
    """
    components = {
        "postal_code": None,
        "city": None,
        "street": None,
        "building_number": None,
    }

    if not address:
        return components

    # Extract postal/zip code - this pattern matches common formats
    # UK: AA9A 9AA, A9A 9AA, A9 9AA, A99 9AA, AA9 9AA, AA99 9AA
    # US: 99999, 99999-9999
    # Can be extended for other countries
    postal_patterns = [
        r"\b[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}\b",  # UK
        r"\b[0-9]{5}(?:-[0-9]{4})?\b",  # US
    ]

    for pattern in postal_patterns:
        postal_match = re.search(pattern, address, re.IGNORECASE)
        if postal_match:
            components["postal_code"] = postal_match.group(0)
            break

    # Extract building number (typically at the beginning of an address)
    building_match = re.search(r"^\s*(\d+[-\w]*)\s", address)
    if building_match:
        components["building_number"] = building_match.group(1)

    # Simple street extraction (this is a basic approach)
    # More sophisticated parsing would require a dedicated address parsing library
    street_pattern = r"\d+\s+([A-Za-z\s]+?)(?:\s+(?:road|street|avenue|lane|drive|place|way|boulevard|rd|st|ave|ln|dr|pl|blvd))?"
    street_match = re.search(street_pattern, address, re.IGNORECASE)
    if street_match:
        components["street"] = street_match.group(1).strip()

    return components


def compare_addresses(
    reference_address: Dict[str, Any],
    candidate_address: str,
    require_postal_match: bool = True,
) -> Tuple[int, Optional[str]]:
    """
    Compare a structured reference address to a candidate address string.

    Args:
        reference_address: Dictionary containing structured address data
        candidate_address: String address to compare against
        require_postal_match: Whether to require postal code to match for a high confidence

    Returns:
        Tuple of (confidence score, matched text)
    """
    if not candidate_address:
        return 0, None

    # Normalize the candidate address
    normalized_candidate = normalize_address(candidate_address)

    # Create a normalized reference address string
    ref_parts = [
        reference_address.get("address_line1", ""),
        reference_address.get("town", ""),
        reference_address.get("postcode", ""),
        reference_address.get("country", ""),
    ]
    reference_string = normalize_address(" ".join([p for p in ref_parts if p]))

    # Initial score based on overall similarity
    overall_score = fuzz.token_sort_ratio(reference_string, normalized_candidate)

    # Check for postal code match
    postcode = reference_address.get("postcode", "").strip()
    has_postal_match = postcode and postcode.lower() in normalized_candidate.lower()

    # Check for town/city match
    town = reference_address.get("town", "").strip().lower()
    has_town_match = town and town in normalized_candidate.lower()

    # Check for street match
    street = reference_address.get("address_line1", "").strip().lower()
    has_street_match = (
        street and fuzz.partial_ratio(street, normalized_candidate.lower()) > 70
    )

    # Calculate final confidence score
    confidence = overall_score

    # Adjust confidence based on component matches
    if has_postal_match:
        confidence += 20
    if has_town_match:
        confidence += 15
    if has_street_match:
        confidence += 10

    # Cap at 100
    confidence = min(confidence, 100)

    # If postal match is required but missing, cap confidence
    if require_postal_match and not has_postal_match:
        confidence = min(confidence, 60)

    logger.debug(
        f"Address comparison - Overall: {overall_score}, Postal: {has_postal_match}, "
        f"Town: {has_town_match}, Street: {has_street_match}, Final: {confidence}"
    )

    return confidence, candidate_address


def extract_addresses_from_text(text: str) -> List[str]:
    """
    Extract potential address strings from a larger text.

    Uses pattern matching to identify text fragments that appear to be addresses.

    Args:
        text: The text to search for addresses

    Returns:
        List of potential address strings
    """
    # Clean the text (remove HTML tags)
    clean_text = re.sub(r"<[^>]+>", " ", text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # List to store potential addresses
    potential_addresses = []

    # UK postcode pattern
    uk_postcode = r"[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}"

    # US zip code pattern
    us_zipcode = r"[0-9]{5}(?:-[0-9]{4})?"

    # Combined pattern
    postal_pattern = f"({uk_postcode}|{us_zipcode})"

    # Find all postal code matches
    postal_matches = re.finditer(postal_pattern, clean_text, re.IGNORECASE)

    for match in postal_matches:
        # Get the position of the postal code
        pos = match.start()

        # Extract text before and after (context window)
        start = max(0, pos - 100)
        end = min(len(clean_text), pos + 100)

        # Extract the context and add to potential addresses
        context = clean_text[start:end]
        potential_addresses.append(context)

    # Additional patterns for addresses without postal codes
    address_patterns = [
        r"\d+\s+[A-Za-z\s]+(?:Road|Street|Avenue|Lane|Drive|Plaza|Square|Court)\b",
        r"\b(?:Road|Street|Avenue|Lane|Drive|Plaza|Square|Court)\b\s+\d+",
    ]

    for pattern in address_patterns:
        matches = re.finditer(pattern, clean_text, re.IGNORECASE)
        for match in matches:
            pos = match.start()
            start = max(0, pos - 50)
            end = min(len(clean_text), pos + 100)
            context = clean_text[start:end]

            # Only add if it's not too similar to existing entries
            if not any(fuzz.ratio(context, addr) > 80 for addr in potential_addresses):
                potential_addresses.append(context)

    return potential_addresses


def find_best_address_match(
    reference_address: Dict[str, Any], text: str, min_confidence: int = 50
) -> Tuple[int, Optional[str]]:
    """
    Find the best address match in a text.

    Args:
        reference_address: Dictionary containing structured address data
        text: Text to search for address matches
        min_confidence: Minimum confidence score to consider a match valid

    Returns:
        Tuple of (confidence score, matched text)
    """
    # Extract potential addresses from the text
    potential_addresses = extract_addresses_from_text(text)

    if not potential_addresses:
        return 0, None

    # Compare each potential address with the reference
    best_score = 0
    best_match = None

    for address in potential_addresses:
        score, match = compare_addresses(reference_address, address)

        if score > best_score:
            best_score = score
            best_match = match

    # Return None if confidence is below minimum
    if best_score < min_confidence:
        return best_score, None

    return best_score, best_match
