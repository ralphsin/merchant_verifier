#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/utils/check_excel_row_structure.py

"""
Excel Row Structure Checker

This script analyzes the structure of the first few rows in an Excel file
to help determine where the merchant data actually starts.
"""

# Standard library imports
import sys
import os

# Third-party library imports
import pandas as pd


def check_excel_rows(file_path, num_rows=10):
    """
    Analyze the first few rows of an Excel file.

    Args:
        file_path: Path to the Excel file
        num_rows: Number of rows to analyze
    """
    print(f"Analyzing rows in Excel file: {file_path}")

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    try:
        # Load Excel file
        df = pd.read_excel(file_path, sheet_name="Sheet1")
        print(f"File has {df.shape[0]} rows and {df.shape[1]} columns total")

        # Show the structure of the first few rows
        max_rows = min(num_rows, df.shape[0])
        print(f"\nShowing first {max_rows} rows structure:")

        for i in range(max_rows):
            # Get a sample of values from this row
            # Check columns 16, 18, 30, 31 (merchant_id, name, address, postcode)
            sample_cols = (
                [16, 18, 30, 31] if i < df.shape[0] and 31 < df.shape[1] else []
            )

            if sample_cols:
                sample_values = {
                    f"col_{j}": str(df.iloc[i, j]) if j < df.shape[1] else "N/A"
                    for j in sample_cols
                }

                print(f"\nRow {i + 1} (index {i}):")
                print(f"  merchant_id (col_16): {sample_values.get('col_16', 'N/A')}")
                print(f"  merchant_name (col_18): {sample_values.get('col_18', 'N/A')}")
                print(f"  address (col_30): {sample_values.get('col_30', 'N/A')}")
                print(f"  postcode (col_31): {sample_values.get('col_31', 'N/A')}")

                # Determine if this looks like a header or data row
                is_header = all(
                    isinstance(val, str)
                    and val.strip()
                    and not val.strip().isdigit()
                    and len(val.strip()) < 30
                    for val in sample_values.values()
                )

                is_empty = all(
                    not str(val).strip() or str(val).strip().lower() == "nan"
                    for val in sample_values.values()
                )

                if is_empty:
                    print("  ⚠️ This row appears to be EMPTY")
                elif is_header:
                    print("  ⚠️ This row might be a HEADER row")
                else:
                    print("  ✓ This row appears to contain MERCHANT DATA")

        print("\nBased on this analysis:")
        print(
            "If you have 3 header rows, data extraction should start at row 4 (index 3)"
        )
        print(
            "If you have 2 header rows, data extraction should start at row 3 (index 2)"
        )

    except Exception as e:
        print(f"Error analyzing Excel file: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_row_structure.py <path_to_excel_file>")
        sys.exit(1)

    check_excel_rows(sys.argv[1])
