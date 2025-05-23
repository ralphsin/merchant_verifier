#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Data Extractor Module

This module contains comprehensive tests for the data_extractor.py module,
which provides functionality for extracting merchant data from Excel files.
"""

import os
import shutil
import unittest
import tempfile
import pandas as pd
from unittest.mock import patch

# Add the parent directory to the path so we can import the src modules
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Module to test
from src.data_extractor import (
    extract_merchant_data,
    get_merchant_by_id,
    filter_merchants,
    export_merchants_to_excel,
    _clean_merchant_data,
)


class TestDataExtractor(unittest.TestCase):
    """Test cases for the data_extractor module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create a sample DataFrame for testing
        self.sample_data = pd.DataFrame(
            {
                "merchant_id": ["7703080809", "9091423394", "8877665544"],
                "merchant_name": ["DANYBERD", "LA FERME DE", "TEST MERCHANT"],
                "merchant_legal_name": ["DANYBERD", "LA FERME DE", "TEST MERCHANT"],
                "industry": ["Retail", "Retail", "Retail"],
                "sub_industry": ["Field Sales", "Field Sales", "Field Sales"],
                "merchant_industry": ["Retail", "Retail", "Retail"],
                "address_line1": ["123 Test St", "456 Sample Rd", "789 Example Ave"],
                "postcode": ["12345", "67890", "54321"],
                "town": ["Paris", "Lyon", "Marseille"],
                "country": ["FRANCE", "FRANCE", "FRANCE"],
            }
        )

        # Create a test Excel file with the structure expected by extract_merchant_data
        self.test_excel_path = os.path.join(self.test_dir, "test_merchant_data.xlsx")

        # Create the Excel file with expected structure (one header row, then data)
        # Row 0: Header row
        header_row = (
            ["Column1", "Column2"]
            + [""] * 14
            + ["MerchantID", "Something", "MerchantName"]
            + [""] * 11
            + ["Address", "Postcode"]
        )

        # Data rows - match column positions in extract_merchant_data
        # Column 16: merchant_id, Column 18: merchant_name, Column 30: address, Column 31: postcode
        data_row1 = (
            [""] * 16
            + ["7703080809", "", "DANYBERD"]
            + [""] * 11
            + ["123 Test St", "12345"]
        )
        data_row2 = (
            [""] * 16
            + ["9091423394", "", "LA FERME DE"]
            + [""] * 11
            + ["456 Sample Rd", "67890"]
        )

        # Combine all rows - only 2 data rows since the implementation only extracts 2
        excel_data = [header_row, data_row1, data_row2]

        # Create DataFrame and save to Excel
        pd.DataFrame(excel_data).to_excel(
            self.test_excel_path, index=False, header=False
        )

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_extract_merchant_data(self):
        """Test extraction of merchant data from Excel file."""

        # Debug the extraction process to understand why only one merchant is being extracted
        def debug_extract():
            print("\n--- DEBUG: EXTRACT MERCHANT DATA ---")
            # Load Excel file with pandas
            df = pd.read_excel(self.test_excel_path)
            print(f"Raw Excel rows: {len(df)}")

            # Skip header row (1 row) - matching the actual data_extractor.py logic
            data_df = df.iloc[1:].reset_index(drop=True)
            print(f"After skipping 1 header row: {len(data_df)} rows")

            # Print the first few rows of data_df
            for i in range(len(data_df)):
                print(
                    f"Row {i}: ID={data_df.iloc[i, 16] if data_df.shape[1] > 16 else 'N/A'}, "
                    f"Name={data_df.iloc[i, 18] if data_df.shape[1] > 18 else 'N/A'}"
                )

            # Extract merchant data
            merchants_data = {
                "merchant_id": data_df.iloc[:, 16],  # Column 16
                "merchant_name": data_df.iloc[:, 18],  # Column 18
            }
            merchants = pd.DataFrame(merchants_data)
            print(f"Initial extracted merchants: {len(merchants)}")
            print(f"Merchant IDs: {merchants['merchant_id'].tolist()}")

            # Check for empty or duplicate merchant IDs
            empty_ids = (
                merchants["merchant_id"].isna()
                | (merchants["merchant_id"] == "")
                | (merchants["merchant_id"] == "nan")
            )
            print(f"Empty merchant IDs: {empty_ids.sum()}")
            duplicate_ids = merchants["merchant_id"].duplicated(keep="first")
            print(f"Duplicate merchant IDs: {duplicate_ids.sum()}")

            valid_merchants = merchants[~empty_ids & ~duplicate_ids]
            print(f"Valid merchants after filtering: {len(valid_merchants)}")
            print(f"Valid merchant IDs: {valid_merchants['merchant_id'].tolist()}")
            print("--- END DEBUG ---\n")

        # For troubleshooting
        # debug_extract()

        # Test with our sample Excel file
        result_df = extract_merchant_data(self.test_excel_path)

        # Check that we got the right number of merchants
        # Both merchants in the test data are valid
        self.assertEqual(len(result_df), 2)

        # Check that we extracted the correct merchant IDs
        # Convert to strings for comparison to handle pandas type conversions
        merchant_ids = [str(id) for id in result_df["merchant_id"].tolist()]
        self.assertIn("7703080809", merchant_ids)
        self.assertIn("9091423394", merchant_ids)

        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            extract_merchant_data("nonexistent_file.xlsx")

        # Test with invalid file format (missing required columns)
        invalid_file_path = os.path.join(self.test_dir, "invalid_format.xlsx")
        pd.DataFrame([["A", "B"], ["C", "D"]]).to_excel(invalid_file_path, index=False)

        with self.assertRaises(ValueError):
            extract_merchant_data(invalid_file_path)

    def test_extract_merchant_data_with_duplicates(self):
        """Test extraction of merchant data with duplicate IDs."""
        # Create test Excel file with duplicate merchant IDs
        duplicate_path = os.path.join(self.test_dir, "duplicate_merchants.xlsx")

        # Create data with duplicate merchant IDs
        header_row = (
            ["Column1", "Column2"]
            + [""] * 14
            + ["MerchantID", "Something", "MerchantName"]
            + [""] * 11
            + ["Address", "Postcode"]
        )
        data_row1 = (
            [""] * 16
            + ["1234567890", "", "Merchant A"]
            + [""] * 11
            + ["Address A", "12345"]
        )
        data_row2 = (
            [""] * 16
            + ["1234567890", "", "Merchant B"]
            + [""] * 11
            + ["Address B", "67890"]
        )
        excel_data = [header_row, data_row1, data_row2]

        # Create Excel file
        pd.DataFrame(excel_data).to_excel(duplicate_path, index=False, header=False)

        # Test extraction - should only keep first instance of duplicate ID
        result_df = extract_merchant_data(duplicate_path)

        # Should only extract one merchant (first one with the ID)
        self.assertEqual(len(result_df), 1)

        # Convert to strings for comparison
        merchant_ids = [str(id) for id in result_df["merchant_id"].tolist()]
        merchant_names = result_df["merchant_name"].tolist()

        # Should keep the first instance of the duplicate
        self.assertIn("1234567890", merchant_ids)
        self.assertIn("Merchant A", merchant_names)
        self.assertNotIn("Merchant B", merchant_names)

    def test_clean_merchant_data(self):
        """Test cleaning of merchant data."""
        # Create test data with issues that need cleaning
        dirty_data = pd.DataFrame(
            {
                "merchant_id": [
                    "1234",
                    "1234",
                    "5678",
                    None,
                    "nan",
                    "",
                ],  # Duplicates and empty values
                "merchant_name": ["Test1", "Test2", None, "Test4", "Test5", "Test6"],
                "merchant_legal_name": [
                    "Legal1",
                    "Legal2",
                    None,
                    "Legal4",
                    "Legal5",
                    "Legal6",
                ],
                "industry": ["Retail", None, "Retail", "Retail", "Retail", "Retail"],
                "sub_industry": [
                    "Field Sales",
                    None,
                    "Field Sales",
                    "Field Sales",
                    "Field Sales",
                    "Field Sales",
                ],
                "merchant_industry": [
                    "Retail",
                    None,
                    "Retail",
                    "Retail",
                    "Retail",
                    "Retail",
                ],
                "address_line1": ["123 St", None, "456 Rd", "789 Ave", "101 Blvd", ""],
                "postcode": ["12345", None, "67890", "54321", "11111", ""],
                "town": ["Paris", None, "Lyon", "Marseille", "Nice", ""],
                "country": ["FRANCE", None, "FRANCE", "FRANCE", "FRANCE", "FRANCE"],
            }
        )

        # Clean the data
        cleaned_df = _clean_merchant_data(dirty_data)

        # Check that duplicates are removed (should have 1 row with ID '1234')
        self.assertEqual(1, len(cleaned_df[cleaned_df["merchant_id"] == "1234"]))

        # Check that empty merchant_ids are removed
        self.assertNotIn(None, cleaned_df["merchant_id"].tolist())
        self.assertNotIn("nan", cleaned_df["merchant_id"].tolist())
        self.assertNotIn("", cleaned_df["merchant_id"].tolist())

        # Check that missing values in text columns are replaced with empty strings
        self.assertEqual(
            "",
            cleaned_df.loc[cleaned_df["merchant_id"] == "5678", "merchant_name"].iloc[
                0
            ],
        )
        self.assertEqual(
            "",
            cleaned_df.loc[
                cleaned_df["merchant_id"] == "5678", "merchant_legal_name"
            ].iloc[0],
        )

        # Check total row count after cleaning
        self.assertEqual(
            2, len(cleaned_df)
        )  # Should have 2 valid rows ('1234' and '5678')

    def test_get_merchant_by_id(self):
        """Test retrieving a merchant by ID."""
        # Test with a valid merchant ID
        merchant = get_merchant_by_id(self.sample_data, "7703080809")
        self.assertIsNotNone(merchant)
        self.assertEqual(merchant["merchant_name"], "DANYBERD")

        # Test with a non-existent merchant ID
        merchant = get_merchant_by_id(self.sample_data, "NONEXISTENT")
        self.assertIsNone(merchant)

        # Test with an empty DataFrame
        with patch("src.data_extractor.logger.warning") as mock_warning:
            empty_df = pd.DataFrame(columns=["merchant_id", "merchant_name"])
            merchant = get_merchant_by_id(empty_df, "7703080809")
            self.assertIsNone(merchant)
            mock_warning.assert_called_once()

        # Test with duplicate merchant IDs
        duplicate_df = pd.DataFrame(
            {"merchant_id": ["1111", "1111"], "merchant_name": ["Name1", "Name2"]}
        )

        with patch("src.data_extractor.logger.warning") as mock_warning:
            merchant = get_merchant_by_id(duplicate_df, "1111")
            self.assertEqual(
                merchant["merchant_name"], "Name1"
            )  # Should return first occurrence
            mock_warning.assert_called_once()

    def test_filter_merchants(self):
        """Test filtering merchants based on criteria."""
        # Test filtering by country (exact match)
        filtered_df = filter_merchants(self.sample_data, {"country": "FRANCE"})
        self.assertEqual(len(filtered_df), 3)  # All are in FRANCE

        # Test filtering by merchant name (exact match)
        filtered_df = filter_merchants(self.sample_data, {"merchant_name": "DANYBERD"})
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_id"], "7703080809")

        # Test filtering by multiple criteria
        filtered_df = filter_merchants(
            self.sample_data, {"country": "FRANCE", "town": "Paris"}
        )
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_id"], "7703080809")

        # Test filtering with non-exact match
        filtered_df = filter_merchants(
            self.sample_data, {"merchant_name": "ferme"}, exact_match=False
        )
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_id"], "9091423394")

        # Test filtering with non-existent column
        filtered_df = filter_merchants(self.sample_data, {"nonexistent": "value"})
        self.assertEqual(
            len(filtered_df), 3
        )  # Should return all rows since filter is ignored

        # Test filtering with non-string column
        # Add a numeric column to the sample data
        df_with_numeric = self.sample_data.copy()
        df_with_numeric["numeric_col"] = [100, 200, 300]

        filtered_df = filter_merchants(df_with_numeric, {"numeric_col": 200})
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_id"], "9091423394")

    def test_export_merchants_to_excel(self):
        """Test exporting merchant data to Excel."""
        # Define output path
        output_path = os.path.join(self.test_dir, "output.xlsx")

        # Export the sample data
        result_path = export_merchants_to_excel(self.sample_data, output_path)

        # Check that the file was created
        self.assertTrue(os.path.exists(result_path))

        # Read back the data and verify
        df_read = pd.read_excel(output_path)
        self.assertEqual(len(df_read), 3)

        # Convert IDs to strings for comparison (pandas might load them as integers)
        merchant_ids = [str(id) for id in df_read["merchant_id"].tolist()]
        self.assertIn("7703080809", merchant_ids)
        self.assertIn("9091423394", merchant_ids)
        self.assertIn("8877665544", merchant_ids)

        # Test with non-existent directory (should create it)
        deep_path = os.path.join(self.test_dir, "subdir1", "subdir2", "output.xlsx")
        result_path = export_merchants_to_excel(self.sample_data, deep_path)
        self.assertTrue(os.path.exists(result_path))

        # Test with error in export
        with patch(
            "pandas.DataFrame.to_excel", side_effect=Exception("Test exception")
        ):
            with self.assertRaises(RuntimeError):
                export_merchants_to_excel(self.sample_data, output_path)

    def test_extract_merchant_data_edge_cases(self):
        """Test extraction of merchant data with edge cases."""
        # Create an Excel file with empty data
        empty_excel_path = os.path.join(self.test_dir, "empty_data.xlsx")
        header_row = (
            ["Column1", "Column2"]
            + [""] * 14
            + ["MerchantID", "Something", "MerchantName"]
            + [""] * 11
            + ["Address", "Postcode"]
        )
        empty_data = [header_row]  # Only header row, no data
        pd.DataFrame(empty_data).to_excel(empty_excel_path, index=False, header=False)

        # Should extract 0 merchants but not raise an error
        result_df = extract_merchant_data(empty_excel_path)
        self.assertEqual(len(result_df), 0)

        # Create an Excel file with empty merchant IDs
        empty_ids_path = os.path.join(self.test_dir, "empty_ids.xlsx")
        header_row = (
            ["Column1", "Column2"]
            + [""] * 14
            + ["MerchantID", "Something", "MerchantName"]
            + [""] * 11
            + ["Address", "Postcode"]
        )
        data_row1 = (
            [""] * 16 + ["", "", "DANYBERD"] + [""] * 11 + ["123 Test St", "12345"]
        )
        data_row2 = (
            [""] * 16
            + [None, "", "LA FERME DE"]
            + [""] * 11
            + ["456 Sample Rd", "67890"]
        )
        empty_ids_data = [header_row, data_row1, data_row2]
        pd.DataFrame(empty_ids_data).to_excel(empty_ids_path, index=False, header=False)

        # Should extract 0 merchants after cleaning removes empty IDs
        result_df = extract_merchant_data(empty_ids_path)
        self.assertEqual(len(result_df), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
