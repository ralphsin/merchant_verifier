#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: tests/test_data_extractor.py

"""
Tests for Data Extractor Module

This module contains tests for the data_extractor.py module, which provides
functionality for extracting merchant data from Excel files.
"""

# Standard library imports
import os
import shutil
import unittest
import tempfile
import pandas as pd
from unittest.mock import patch

# Module to test
from src.data_extractor import (
    extract_merchant_data,
    get_merchant_by_id,
    filter_merchants,
    export_merchants_to_excel,
)


class TestDataExtractor(unittest.TestCase):
    """Test cases for merchant data extraction functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create a sample DataFrame
        self.sample_data = pd.DataFrame(
            {
                "merchant_id": ["M123", "M456", "M789"],
                "merchant_name": ["Test Shop", "Sample Store", "Example Business"],
                "merchant_legal_name": [
                    "Test Shop Ltd",
                    "Sample Store Inc",
                    "Example Business LLC",
                ],
                "industry": ["Retail", "Food", "Services"],
                "sub_industry": ["Clothing", "Restaurant", "Consulting"],
                "merchant_industry": ["Retail", "Food Service", "Business Services"],
                "address_line1": ["123 Main St", "456 High St", "789 Park Ave"],
                "postcode": ["SW1A 1AA", "NW1 6XE", "E1 6AN"],
                "town": ["London", "Manchester", "Birmingham"],
                "country": ["UK", "UK", "UK"],
            }
        )

        # Create a sample Excel file
        self.sample_excel_path = os.path.join(self.test_dir, "sample_data.xlsx")

        # Create a DataFrame with enough columns to match those used in extract_merchant_data
        # Based on the error, we need at least 34 columns
        excel_data = pd.DataFrame()

        # Create column names
        column_names = [f"col_{i}" for i in range(40)]  # Create 40 columns to be safe

        # Create header rows (simulate the 2 header rows from the real Excel)
        header_row1 = pd.DataFrame(
            [["Header Row 1"] + [""] * (len(column_names) - 1)], columns=column_names
        )
        header_row2 = pd.DataFrame(
            [["Header Row 2"] + [""] * (len(column_names) - 1)], columns=column_names
        )

        # Create data rows with empty values
        data_rows = pd.DataFrame(index=range(3), columns=column_names)
        data_rows = data_rows.fillna("")

        # Fill in the columns that matter (indices match those in extract_merchant_data)
        data_rows["col_16"] = self.sample_data["merchant_id"]
        data_rows["col_18"] = self.sample_data["merchant_name"]
        data_rows["col_19"] = self.sample_data["merchant_legal_name"]
        data_rows["col_25"] = self.sample_data["industry"]
        data_rows["col_26"] = self.sample_data["sub_industry"]
        data_rows["col_29"] = self.sample_data["merchant_industry"]
        data_rows["col_30"] = self.sample_data["address_line1"]
        data_rows["col_31"] = self.sample_data["postcode"]
        data_rows["col_32"] = self.sample_data["town"]
        data_rows["col_33"] = self.sample_data["country"]

        # Combine headers and data
        excel_data = pd.concat([header_row1, header_row2, data_rows], ignore_index=True)

        # Combine headers and data
        excel_data = pd.concat([excel_data, data_rows], ignore_index=True)

        # Write to Excel
        excel_data.to_excel(self.sample_excel_path, sheet_name="Sheet1", index=False)

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_extract_merchant_data(self):
        """Test extraction of merchant data from Excel file."""
        # Test with our sample Excel file
        result_df = extract_merchant_data(self.sample_excel_path)

        # Check that we got the right data
        self.assertEqual(len(result_df), 3)
        self.assertListEqual(
            result_df["merchant_id"].tolist(), ["M123", "M456", "M789"]
        )
        self.assertListEqual(
            result_df["merchant_name"].tolist(),
            ["Test Shop", "Sample Store", "Example Business"],
        )

        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            extract_merchant_data("nonexistent_file.xlsx")

    def test_get_merchant_by_id(self):
        """Test getting a merchant by ID."""
        # Test with a valid merchant ID
        merchant = get_merchant_by_id(self.sample_data, "M123")
        self.assertIsNotNone(merchant)
        self.assertEqual(merchant["merchant_name"], "Test Shop")

        # Test with a non-existent merchant ID
        merchant = get_merchant_by_id(self.sample_data, "NONEXISTENT")
        self.assertIsNone(merchant)

        # Test with an empty DataFrame
        with patch("src.data_extractor.logger.warning") as mock_warning:
            empty_df = pd.DataFrame(columns=["merchant_id", "merchant_name"])
            merchant = get_merchant_by_id(empty_df, "M123")
            self.assertIsNone(merchant)
            mock_warning.assert_called_once()

    def test_filter_merchants(self):
        """Test filtering merchants based on criteria."""
        # Test filtering by country (exact match)
        filtered_df = filter_merchants(self.sample_data, {"country": "UK"})
        self.assertEqual(len(filtered_df), 3)  # All are in UK

        # Test filtering by industry (exact match)
        filtered_df = filter_merchants(self.sample_data, {"industry": "Retail"})
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_name"], "Test Shop")

        # Test filtering by multiple criteria
        filtered_df = filter_merchants(
            self.sample_data, {"country": "UK", "town": "London"}
        )
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_name"], "Test Shop")

        # Test filtering with non-exact match
        filtered_df = filter_merchants(
            self.sample_data, {"industry": "retail"}, exact_match=False
        )
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_name"], "Test Shop")

        # Test filtering with non-existent column
        filtered_df = filter_merchants(self.sample_data, {"nonexistent": "value"})
        self.assertEqual(
            len(filtered_df), 3
        )  # Should return all rows since filter is ignored

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
        self.assertListEqual(df_read["merchant_id"].tolist(), ["M123", "M456", "M789"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
