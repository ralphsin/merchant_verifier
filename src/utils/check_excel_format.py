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
        print("\nFirst few rows (first 6 columns):")
        for i in range(min(5, df.shape[0])):
            col_data = []
            for j in range(min(6, df.shape[1])):
                col_data.append(f"{df.iloc[i, j]}")
            print(f"Row {i}: {' | '.join(col_data)}")

        # Analyze header and data rows
        print("\nAnalyzing file structure:")
        print(f"Row 0 (Header Row 1): {df.iloc[0, 0:6].tolist()}")
        print(f"Row 1 (Header Row 2): {df.iloc[1, 0:6].tolist()}")

        if df.shape[0] > 2:
            print(f"Row 2 (First Data Row): {df.iloc[2, 0:6].tolist()}")
        if df.shape[0] > 3:
            print(f"Row 3 (Second Data Row): {df.iloc[3, 0:6].tolist()}")

        # Try to extract data as the real application would
        print("\nAttempting to extract data as the application would...")

        # Skip both header rows (2 rows)
        data_rows = df.iloc[1:].reset_index(drop=True)
        print(f"After skipping 2 header rows, we have {len(data_rows)} data rows")

        # Print the key column indices to verify
        print("\nKey columns used by the application:")
        print("merchant_id: Column index 0 (Column A)")
        print("merchant_name: Column index 1 (Column B)")
        print("country: Column index 2 (Column C)")

        # Extract sample data from required columns
        if len(data_rows) > 0:
            print("\nSample data from first merchant (first data row):")
            sample = {
                "merchant_id": data_rows.iloc[0, 0]
                if data_rows.shape[1] > 0
                else "N/A",
                "merchant_name": data_rows.iloc[0, 1]
                if data_rows.shape[1] > 1
                else "N/A",
                "country": data_rows.iloc[0, 2] if data_rows.shape[1] > 2 else "N/A",
            }

            for key, value in sample.items():
                print(f"{key}: {value}")

            # Check for missing essential data
            missing = [
                key for key, value in sample.items() if pd.isna(value) or value == ""
            ]
            if missing:
                print(f"\nWarning: Missing data for essential fields: {missing}")
                return False

            # List all merchants found in the file
            print("\nAll merchants found in the file:")
            for i in range(len(data_rows)):
                merchant_id = data_rows.iloc[i, 0]
                merchant_name = data_rows.iloc[i, 1]
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
