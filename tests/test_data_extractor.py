import os
import tempfile
import pandas as pd
import pytest
from src.data_extractor import (
    extract_merchant_data,
    _clean_merchant_data,
    get_merchant_by_id,
    filter_merchants,
    export_merchants_to_excel,
)


# Test fixtures
@pytest.fixture
def sample_excel_file():
    """Create a temporary Excel file with sample merchant data."""
    # Create sample data
    data = {
        "col_16": ["MERCH001", "MERCH002", "MERCH003"],  # merchant_id
        "col_18": ["Store 1", "Store 2", "Store 3"],  # merchant_name
        "col_30": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],  # address
        "col_31": ["12345", "67890", "11111"],  # postcode
    }

    # Create DataFrame with proper structure (adding empty columns to match expected format)
    df = pd.DataFrame(data)
    # Add empty columns to match the expected structure
    for i in range(32):
        if f"col_{i}" not in df.columns:
            df[f"col_{i}"] = ""

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df.to_excel(tmp.name, index=False)
        return tmp.name


@pytest.fixture
def sample_merchants_df():
    """Create a sample DataFrame with merchant data."""
    return pd.DataFrame(
        {
            "merchant_id": ["MERCH001", "MERCH002", "MERCH003"],
            "merchant_name": ["Store 1", "Store 2", "Store 3"],
            "merchant_legal_name": ["Store 1", "Store 2", "Store 3"],
            "industry": ["Retail", "Retail", "Retail"],
            "sub_industry": ["Field Sales", "Field Sales", "Field Sales"],
            "merchant_industry": ["Retail", "Retail", "Retail"],
            "address_line1": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],
            "postcode": ["12345", "67890", "11111"],
            "town": ["", "", ""],
            "country": ["FRANCE", "FRANCE", "FRANCE"],
        }
    )


# Test cases
def test_extract_merchant_data(sample_excel_file):
    """Test extracting merchant data from Excel file."""
    df = extract_merchant_data(sample_excel_file)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "merchant_id" in df.columns
    assert "merchant_name" in df.columns
    assert df.iloc[0]["merchant_id"] == "MERCH001"
    assert df.iloc[0]["merchant_name"] == "Store 1"


def test_extract_merchant_data_file_not_found():
    """Test handling of non-existent file."""
    with pytest.raises(FileNotFoundError):
        extract_merchant_data("nonexistent_file.xlsx")


def test_clean_merchant_data(sample_merchants_df):
    """Test cleaning merchant data."""
    # Add some problematic data
    df = sample_merchants_df.copy()
    df.loc[3] = [
        "",
        "Empty Store",
        "Empty Store",
        "Retail",
        "Field Sales",
        "Retail",
        "",
        "",
        "",
        "FRANCE",
    ]  # Empty merchant_id
    df.loc[4] = [
        "MERCH001",
        "Duplicate Store",
        "Duplicate Store",
        "Retail",
        "Field Sales",
        "Retail",
        "",
        "",
        "",
        "FRANCE",
    ]  # Duplicate merchant_id

    cleaned_df = _clean_merchant_data(df)

    assert len(cleaned_df) == 3  # Should remove empty and duplicate IDs
    assert "MERCH001" in cleaned_df["merchant_id"].values
    assert "" not in cleaned_df["merchant_id"].values


def test_get_merchant_by_id(sample_merchants_df):
    """Test retrieving merchant by ID."""
    # Test existing merchant
    merchant = get_merchant_by_id(sample_merchants_df, "MERCH001")
    assert merchant is not None
    assert merchant["merchant_name"] == "Store 1"

    # Test non-existing merchant
    merchant = get_merchant_by_id(sample_merchants_df, "NONEXISTENT")
    assert merchant is None


def test_filter_merchants(sample_merchants_df):
    """Test filtering merchants."""
    # Test exact match
    filtered_df = filter_merchants(
        sample_merchants_df, {"merchant_name": "Store 1"}, exact_match=True
    )
    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]["merchant_id"] == "MERCH001"

    # Test partial match
    filtered_df = filter_merchants(
        sample_merchants_df, {"merchant_name": "Store"}, exact_match=False
    )
    assert len(filtered_df) == 3


def test_export_merchants_to_excel(sample_merchants_df):
    """Test exporting merchants to Excel."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        output_path = export_merchants_to_excel(sample_merchants_df, tmp.name)

        assert os.path.exists(output_path)
        # Verify the exported file can be read back
        exported_df = pd.read_excel(output_path)
        assert len(exported_df) == len(sample_merchants_df)
        assert all(col in exported_df.columns for col in sample_merchants_df.columns)

        # Clean up
        os.unlink(output_path)
