#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: src/data_extractor.py

"""
Data Extractor Module

This module provides functionality for extracting merchant data from Excel files.
It handles the parsing, cleaning, and transformation of merchant information
to prepare it for the verification process.
"""

# Standard library imports
import os
from typing import Dict, Optional, Any

# Third-party imports
import pandas as pd

# Local imports
from config.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def extract_merchant_data(file_path: str) -> pd.DataFrame:
    """
    Extract merchant data from Excel file.

    Args:
        file_path: Path to the Excel file containing merchant data

    Returns:
        DataFrame containing structured merchant information

    Raises:
        FileNotFoundError: If the specified file does not exist
        ValueError: If the file format is invalid or missing required columns
    """
    logger.info(f"Extracting merchant data from: {file_path}")

    # Verify the file exists
    if not os.path.exists(file_path):
        error_msg = f"Excel file not found: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        # Load Excel file with pandas
        df = pd.read_excel(file_path, sheet_name="Sheet1")
        logger.debug(f"Loaded Excel with {df.shape[0]} rows and {df.shape[1]} columns")

        # Skip only the first row (header row)
        df = df.iloc[1:].reset_index(drop=True)

        # Extract only needed columns - map column names based on the Excel structure
        merchants = pd.DataFrame(
            {
                "merchant_id": df.iloc[:, 16],  # mer_id
                "merchant_name": df.iloc[:, 18],  # mer_dba_nm
                "merchant_legal_name": df.iloc[:, 19],  # mer_lgl_nm
                "industry": df.iloc[:, 25],  # genesis_mjr_indus_ds
                "sub_industry": df.iloc[:, 26],  # genesis_mjr_sbd_indus_ds
                "merchant_industry": df.iloc[:, 29],  # merchant_industry
                "address_line1": df.iloc[:, 30],  # phys_ad_line_1_tx
                "postcode": df.iloc[:, 31],  # postcode
                "town": df.iloc[:, 32],  # phys_ad_post_town_nm
                "country": df.iloc[:, 33],  # market
            }
        )

        # Clean data
        merchants = _clean_merchant_data(merchants)

        logger.info(f"Successfully extracted {len(merchants)} merchant records")
        return merchants

    except Exception as e:
        error_msg = f"Error extracting merchant data: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def _clean_merchant_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare merchant data.

    This function:
    - Fills missing values
    - Removes duplicate records
    - Standardizes data formats
    - Validates essential fields

    Args:
        df: DataFrame containing merchant data

    Returns:
        Cleaned DataFrame
    """
    logger.debug("Cleaning merchant data")

    # Make a copy to avoid modifying the original
    cleaned_df = df.copy()

    # Fill missing values with empty strings for text columns
    text_columns = [
        "merchant_name",
        "merchant_legal_name",
        "industry",
        "sub_industry",
        "merchant_industry",
        "address_line1",
        "town",
        "country",
    ]

    for col in text_columns:
        if col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].fillna("").astype(str)

    # Handle postcode specifically - keep as-is if NaN
    if "postcode" in cleaned_df.columns:
        cleaned_df["postcode"] = cleaned_df["postcode"].astype(str)
        cleaned_df.loc[cleaned_df["postcode"] == "nan", "postcode"] = ""

    # Standardize merchant_id format
    if "merchant_id" in cleaned_df.columns:
        cleaned_df["merchant_id"] = cleaned_df["merchant_id"].astype(str)
        cleaned_df["merchant_id"] = cleaned_df["merchant_id"].str.strip()

    # Remove duplicate merchant_id entries (keep first occurrence)
    pre_dedup_count = len(cleaned_df)
    cleaned_df = cleaned_df.drop_duplicates(subset=["merchant_id"], keep="first")
    post_dedup_count = len(cleaned_df)

    if pre_dedup_count != post_dedup_count:
        logger.warning(
            f"Removed {pre_dedup_count - post_dedup_count} duplicate merchant records"
        )

    # Validate essential fields
    missing_name = cleaned_df["merchant_name"].str.strip() == ""
    missing_address = cleaned_df["address_line1"].str.strip() == ""

    if missing_name.any():
        logger.warning(f"Found {missing_name.sum()} records with missing merchant name")

    if missing_address.any():
        logger.warning(f"Found {missing_address.sum()} records with missing address")

    return cleaned_df


def get_merchant_by_id(
    merchants_df: pd.DataFrame, merchant_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific merchant by ID.

    Args:
        merchants_df: DataFrame containing merchant data
        merchant_id: ID of the merchant to retrieve

    Returns:
        Dictionary with merchant data or None if not found
    """
    merchant_rows = merchants_df[merchants_df["merchant_id"] == str(merchant_id)]

    if len(merchant_rows) == 0:
        logger.warning(f"Merchant with ID {merchant_id} not found")
        return None

    if len(merchant_rows) > 1:
        logger.warning(
            f"Multiple entries found for merchant ID {merchant_id}, using first entry"
        )

    # Convert the first row to a dictionary
    merchant_dict = merchant_rows.iloc[0].to_dict()

    return merchant_dict


def filter_merchants(
    merchants_df: pd.DataFrame, filters: Dict[str, Any], exact_match: bool = True
) -> pd.DataFrame:
    """
    Filter merchants based on specified criteria.

    Args:
        merchants_df: DataFrame containing merchant data
        filters: Dictionary of column:value pairs to filter by
        exact_match: Whether to require exact matches (False for partial matching)

    Returns:
        Filtered DataFrame
    """
    filtered_df = merchants_df.copy()

    for column, value in filters.items():
        if column not in filtered_df.columns:
            logger.warning(f"Column '{column}' not found, skipping this filter")
            continue

        if exact_match:
            filtered_df = filtered_df[filtered_df[column] == value]
        else:
            # For string columns, use case-insensitive contains
            if filtered_df[column].dtype == "object":
                filtered_df = filtered_df[
                    filtered_df[column].str.contains(value, case=False, na=False)
                ]
            else:
                filtered_df = filtered_df[filtered_df[column] == value]

    logger.info(f"Filtered merchant data: {len(filtered_df)} records match criteria")
    return filtered_df


def export_merchants_to_excel(merchants_df: pd.DataFrame, output_path: str) -> str:
    """
    Export merchant data to Excel file.

    Args:
        merchants_df: DataFrame containing merchant data
        output_path: Path for the output Excel file

    Returns:
        Path to the created Excel file
    """
    try:
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Export to Excel
        merchants_df.to_excel(output_path, index=False)
        logger.info(
            f"Successfully exported {len(merchants_df)} merchants to {output_path}"
        )

        return output_path

    except Exception as e:
        error_msg = f"Error exporting to Excel: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
