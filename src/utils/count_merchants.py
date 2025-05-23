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
import pandas as pd
import logging

# Third-party library imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.data_extractor import extract_merchant_data
from src.config.logging_config import setup_logging


def debug_excel_file(file_path):
    """
    Analyze the raw Excel file structure before extraction to identify potential issues.

    Args:
        file_path: Path to the Excel file
    """
    print("\n==== DEBUGGING EXCEL FILE STRUCTURE ====")
    try:
        # Read the raw Excel file
        df = pd.read_excel(file_path)

        # Print basic stats
        print(f"Total rows in Excel: {len(df)}")
        print(f"Total columns in Excel: {df.shape[1]}")

        # Print all rows with the actual column indices used by the application
        print("\nAll rows (showing merchant-relevant columns):")
        for i in range(len(df)):
            print(f"Row {i}:")
            # Show the actual columns that the application uses
            if df.shape[1] > 16:
                print(f"  Column 16 (merchant_id): {df.iloc[i, 16]}")
            if df.shape[1] > 18:
                print(f"  Column 18 (merchant_name): {df.iloc[i, 18]}")
            if df.shape[1] > 30:
                print(f"  Column 30 (address): {df.iloc[i, 30]}")
            if df.shape[1] > 31:
                print(f"  Column 31 (postcode): {df.iloc[i, 31]}")

        print("==== END OF EXCEL STRUCTURE DEBUG ====\n")
    except Exception as e:
        print(f"Error during debug: {e}")


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

    # First debug the raw Excel structure
    debug_excel_file(file_path)

    try:
        # Set up debug logging for this session
        setup_logging(log_level=logging.DEBUG, console=True, log_dir=None)

        print("=== CALLING EXTRACT_MERCHANT_DATA ===")
        # Extract data using the project's extraction function
        merchants_df = extract_merchant_data(file_path)
        print("=== FINISHED EXTRACT_MERCHANT_DATA ===")

        # Print count
        count = len(merchants_df)
        print(f"\nFound {count} merchants in the Excel file.")

        # Debugging: Print all merchant IDs to see what was extracted
        print("\nExtracted merchant IDs:")
        print(merchants_df["merchant_id"].tolist())

        print("\nExtracted merchant names:")
        print(merchants_df["merchant_name"].tolist())

        # Print the first few merchants
        if count > 0:
            print("\nHere are all the merchants:")
            for i, (_, merchant) in enumerate(merchants_df.iterrows()):
                print(f"\nMerchant {i + 1}:")
                print(f"  ID: {merchant['merchant_id']}")
                print(f"  Name: {merchant['merchant_name']}")
                print(f"  Legal Name: {merchant['merchant_legal_name']}")
                print(f"  Industry: {merchant['industry']}")
                print(f"  Country: {merchant['country']}")
                print(
                    f"  Address: {merchant['address_line1']}, {merchant['town']}, {merchant['postcode']}"
                )
        else:
            print(
                "\nNo merchants were extracted. Check the debug logs above to see what went wrong."
            )

    except Exception as e:
        print(f"Error analyzing Excel file: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_merchants.py <path_to_excel_file>")
        sys.exit(1)

    count_merchants(sys.argv[1])
