from src.address_matcher import (
    normalize_address,
    extract_address_components,
    compare_addresses,
    extract_addresses_from_text,
    find_best_address_match,
)


def main():
    # Example 1: Normalize an address
    address = "123 Main St., London, UK, SW1A 1AA"
    normalized = normalize_address(address)
    print("\n1. Address Normalization:")
    print(f"Original: {address}")
    print(f"Normalized: {normalized}")

    # Example 2: Extract address components
    components = extract_address_components(address)
    print("\n2. Address Components:")
    for key, value in components.items():
        print(f"{key}: {value}")

    # Example 3: Compare addresses
    reference_address = {
        "address_line1": "123 Main Street",
        "town": "London",
        "postcode": "SW1A 1AA",
        "country": "UK",
    }
    candidate_address = "123 Main St, London, SW1A 1AA"
    score, match = compare_addresses(reference_address, candidate_address)
    print("\n3. Address Comparison:")
    print(f"Reference: {reference_address}")
    print(f"Candidate: {candidate_address}")
    print(f"Confidence Score: {score}")
    print(f"Matched Text: {match}")

    # Example 4: Extract addresses from text
    text = """
    Our office is located at 456 Park Avenue, New York, NY 10022.
    We also have a branch at 789 Oxford Street, London, W1D 2BS.
    Contact us at 123 Main St, Boston, MA 02108.
    """
    addresses = extract_addresses_from_text(text)
    print("\n4. Addresses Extracted from Text:")
    for addr in addresses:
        print(f"- {addr}")

    # Example 5: Find best address match
    best_score, best_match = find_best_address_match(
        reference_address, text, min_confidence=50
    )
    print("\n5. Best Address Match:")
    print(f"Best Score: {best_score}")
    print(f"Best Match: {best_match}")


if __name__ == "__main__":
    main()
