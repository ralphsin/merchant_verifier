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

# Add the parent directory to the path so we can import the src modules
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

        # Create a sample DataFrame with our test merchants
        self.sample_data = pd.DataFrame(
            {
                "merchant_id": ["7703080809", "9091423394"],
                "merchant_name": ["DANYBERD", "LA FERME DE"],
                "merchant_legal_name": ["DANYBERD", "LA FERME DE"],
                "industry": ["Retail", "Retail"],
                "sub_industry": ["Field Sales", "Field Sales"],
                "merchant_industry": ["Retail", "Retail"],
                "address_line1": ["", ""],
                "postcode": ["", ""],
                "town": ["", ""],
                "country": ["FRANCE", "FRANCE"],
            }
        )

        # Create a sample Excel file with the structure matching the screenshot
        self.sample_excel_path = os.path.join(self.test_dir, "sample_data.xlsx")

        # Create the Excel data that matches the actual format
        # Row 1: Header row 1
        header_row1 = [
            "SE for Review",
            "SE for Review",
            "SE for Review",
            "",
            "Employee Details",
        ]
        # Extend header to have enough columns
        header_row1.extend([""] * 10)

        # Row 2: Header row 2 with column headings
        header_row2 = [
            "SE for Review #",
            "SE for Review Name",
            "SE for Review linked to this Market",
            "Primary Market(s) Supported",
            "Primary Channel(s) Supported",
            "Employee name",
            "Band",
            "Status",
            "Role Start-Date",
            "Role End-Date",
        ]
        # Extend header to have enough columns
        header_row2.extend([""] * 5)

        # Data rows
        data_row1 = [
            "7703080809",
            "DANYBERD",
            "FRANCE",
            "France",
            "Field Sales",
            "Karuna",
            "30",
            "Current",
            "04-Jul-08",
            "",
            "Mohan",
        ]
        # Extend data row to have enough columns
        data_row1.extend([""] * 4)

        data_row2 = [
            "9091423394",
            "LA FERME DE",
            "FRANCE",
            "France",
            "Field Sales",
            "Rakesh",
            "30",
            "Current",
            "01-Jan-07",
            "",
            "Sohan",
        ]
        # Extend data row to have enough columns
        data_row2.extend([""] * 4)

        # Combine all rows
        excel_data = [header_row1, header_row2, data_row1, data_row2]

        # Create DataFrame and save to Excel
        pd.DataFrame(excel_data).to_excel(
            self.sample_excel_path, index=False, header=False
        )

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_extract_merchant_data(self):
        """Test extraction of merchant data from Excel file."""
        # Test with our sample Excel file
        result_df = extract_merchant_data(self.sample_excel_path)

        # Check that we got the right data
        self.assertEqual(len(result_df), 2)
        self.assertIn("7703080809", result_df["merchant_id"].tolist())
        self.assertIn("9091423394", result_df["merchant_id"].tolist())
        self.assertIn("DANYBERD", result_df["merchant_name"].tolist())
        self.assertIn("LA FERME DE", result_df["merchant_name"].tolist())

        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            extract_merchant_data("nonexistent_file.xlsx")

    def test_get_merchant_by_id(self):
        """Test getting a merchant by ID."""
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

    def test_filter_merchants(self):
        """Test filtering merchants based on criteria."""
        # Test filtering by country (exact match)
        filtered_df = filter_merchants(self.sample_data, {"country": "FRANCE"})
        self.assertEqual(len(filtered_df), 2)  # All are in FRANCE

        # Test filtering by merchant name (exact match)
        filtered_df = filter_merchants(self.sample_data, {"merchant_name": "DANYBERD"})
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df.iloc[0]["merchant_id"], "7703080809")

        # Test filtering by multiple criteria
        filtered_df = filter_merchants(
            self.sample_data, {"country": "FRANCE", "merchant_name": "DANYBERD"}
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
            len(filtered_df), 2
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
        self.assertEqual(len(df_read), 2)
        self.assertIn("7703080809", df_read["merchant_id"].tolist())
        self.assertIn("9091423394", df_read["merchant_id"].tolist())

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
