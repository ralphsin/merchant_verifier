#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/utils/check_excel_format.py

"""
Excel Format Checker

This script checks if the structure of the provided Excel file
matches what is expected by the merchant verification application.
"""

# Standard library imports
import os
import sys

# Third-party Library imports
import pandas as pd


def check_excel_format(file_path):
    """
    Check if the Excel file has the expected structure.

    Args:
        file_path: Path to the Excel file
    """
    print(f"Checking Excel file: {file_path}")

    # Verify the file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    try:
        # Load Excel file with pandas
        print("Loading Excel file...")
        df = pd.read_excel(file_path)
        print(f"Loaded Excel with {df.shape[0]} rows and {df.shape[1]} columns")

        # Print the first few rows to see the structure
        print("\nFirst 5 rows:")
        print(df.head(5))

        # Print column names/indices
        print("\nColumn names:")
        for i, col in enumerate(df.columns):
            print(f"Column {i}: {col}")

        # Check if it has enough columns
        if df.shape[1] < 34:  # We need columns up to index 33
            print(
                f"Warning: File has only {df.shape[1]} columns, but we need at least 34"
            )
            return False

        # Try to extract data as the real application would
        print("\nAttempting to extract data as the application would...")

        # Skip header rows (we know there are 2 header rows)
        data_rows = df.iloc[2:].reset_index(drop=True)

        # Extract sample data from required columns
        try:
            sample = {
                "merchant_id": data_rows.iloc[0, 16] if len(data_rows) > 0 else None,
                "merchant_name": data_rows.iloc[0, 18] if len(data_rows) > 0 else None,
                "address_line1": data_rows.iloc[0, 30] if len(data_rows) > 0 else None,
                "postcode": data_rows.iloc[0, 31] if len(data_rows) > 0 else None,
                "town": data_rows.iloc[0, 32] if len(data_rows) > 0 else None,
                "country": data_rows.iloc[0, 33] if len(data_rows) > 0 else None,
            }

            print("\nSample extracted data:")
            for key, value in sample.items():
                print(f"{key}: {value}")

            # Check for missing essential data
            missing = [
                key for key, value in sample.items() if pd.isna(value) or value == ""
            ]
            if missing:
                print(f"\nWarning: Missing data for essential fields: {missing}")
                return False

            print("\nExcel file structure appears compatible with the application.")
            return True

        except Exception as e:
            print(f"\nError extracting data: {str(e)}")
            return False

    except Exception as e:
        print(f"Error loading Excel file: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python excel_check.py <path_to_excel_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    success = check_excel_format(file_path)

    if success:
        print("\nYou can now run the application with:")
        print(f"python main.py {file_path} -o verification_results.xlsx")
    else:
        print("\nPlease check the Excel file format before running the application.")
