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

        # Print the first few rows to see the structure (showing relevant columns)
        print("\nFirst few rows (showing merchant-relevant columns):")
        for i in range(min(5, df.shape[0])):
            row_data = {}
            if df.shape[1] > 16:
                row_data["col_16_merchant_id"] = df.iloc[i, 16]
            if df.shape[1] > 18:
                row_data["col_18_merchant_name"] = df.iloc[i, 18]
            if df.shape[1] > 30:
                row_data["col_30_address"] = df.iloc[i, 30]
            if df.shape[1] > 31:
                row_data["col_31_postcode"] = df.iloc[i, 31]

            print(f"Row {i}: {row_data}")

        # Analyze header and data rows
        print("\nAnalyzing file structure:")
        if df.shape[1] > 18:
            print(
                f"Row 0 (Header): Column 16={df.iloc[0, 16]}, Column 18={df.iloc[0, 18]}"
            )
            if df.shape[0] > 1:
                print(
                    f"Row 1 (Data 1): Column 16={df.iloc[1, 16]}, Column 18={df.iloc[1, 18]}"
                )
            if df.shape[0] > 2:
                print(
                    f"Row 2 (Data 2): Column 16={df.iloc[2, 16]}, Column 18={df.iloc[2, 18]}"
                )

        # Try to extract data as the real application would
        print("\nAttempting to extract data as the application would...")

        # Skip header row (1 row) - matching the actual data_extractor.py logic
        data_rows = df.iloc[1:].reset_index(drop=True)
        print(f"After skipping 1 header row, we have {len(data_rows)} data rows")

        # Print the key column indices to verify
        print("\nKey columns used by the application:")
        print("merchant_id: Column index 16")
        print("merchant_name: Column index 18")
        print("address: Column index 30 (if available)")
        print("postcode: Column index 31 (if available)")

        # Check if required columns exist
        if df.shape[1] <= 18:
            print(
                f"\nError: Excel file doesn't have enough columns. Need at least 19 columns, got {df.shape[1]}"
            )
            return False

        # Extract sample data from required columns
        if len(data_rows) > 0:
            print("\nSample data from first merchant (first data row):")
            sample = {
                "merchant_id": data_rows.iloc[0, 16]
                if data_rows.shape[1] > 16
                else "N/A",
                "merchant_name": data_rows.iloc[0, 18]
                if data_rows.shape[1] > 18
                else "N/A",
                "address": data_rows.iloc[0, 30] if data_rows.shape[1] > 30 else "N/A",
                "postcode": data_rows.iloc[0, 31] if data_rows.shape[1] > 31 else "N/A",
            }

            for key, value in sample.items():
                print(f"{key}: {value}")

            # Check for missing essential data
            missing = [
                key
                for key, value in sample.items()
                if key in ["merchant_id", "merchant_name"]
                and (pd.isna(value) or value == "")
            ]
            if missing:
                print(f"\nWarning: Missing data for essential fields: {missing}")
                return False

            # List all merchants found in the file
            print("\nAll merchants found in the file:")
            for i in range(len(data_rows)):
                if data_rows.shape[1] > 18:
                    merchant_id = data_rows.iloc[i, 16]
                    merchant_name = data_rows.iloc[i, 18]
                    if not pd.isna(merchant_id) and not pd.isna(merchant_name):
                        print(f"  Merchant {i + 1}: {merchant_id} - {merchant_name}")

            print("\nExcel file structure appears compatible with the application.")
            return True
        else:
            print("\nWarning: No data rows found after skipping headers!")
            return False

    except Exception as e:
        print(f"Error analyzing Excel file: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_excel_format.py <path_to_excel_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    success = check_excel_format(file_path)

    if success:
        print("\nYou can now run the application with:")
        print(f"python main.py {file_path} -o verification_results.xlsx")
    else:
        print("\nPlease check the Excel file format before running the application.")
