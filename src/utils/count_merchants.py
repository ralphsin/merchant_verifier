#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/utils/count_merchants.py

"""
Excel Merchant Counter

This script counts how many merchants are in an Excel file and displays the
first few records to help verify the data structure.
"""

# Standard library imports
import sys
import os


# Third-party library imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_extractor import extract_merchant_data


def count_merchants(file_path):
    """
    Count and display information about merchants in an Excel file.

    Args:
        file_path: Path to the Excel file
    """
    print(f"Analyzing Excel file: {file_path}")

    # Verify the file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    try:
        # Extract data using the project's extraction function
        merchants_df = extract_merchant_data(file_path)

        # Print count
        count = len(merchants_df)
        print(f"\nFound {count} merchants in the Excel file.")

        # Print the first few merchants
        if count > 0:
            print("\nHere are the first 5 merchants (or all if less than 5):")
            for i, (_, merchant) in enumerate(merchants_df.head(5).iterrows()):
                print(f"\nMerchant {i + 1}:")
                print(f"  ID: {merchant['merchant_id']}")
                print(f"  Name: {merchant['merchant_name']}")
                print(
                    f"  Address: {merchant['address_line1']}, {merchant['town']}, {merchant['postcode']}, {merchant['country']}"
                )

    except Exception as e:
        print(f"Error analyzing Excel file: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_merchants.py <path_to_excel_file>")
        sys.exit(1)

    count_merchants(sys.argv[1])
