#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: main.py

"""
Main Merchant Verification Script

This script processes all merchants from an Excel file and verifies their
address information by searching online using DuckDuckGo and checking
relevant websites.
"""

import sys
import os
import json
import argparse
from datetime import datetime
import pandas as pd

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config.logging_config import setup_logging
from src.web_automation import process_merchant_verification


def save_results_to_excel(results: dict, output_path: str) -> str:
    """
    Save verification results to an Excel file.

    Args:
        results: Dictionary containing verification results
        output_path: Path for the output Excel file

    Returns:
        Path to the created Excel file
    """
    # Prepare data for Excel export
    excel_data = []

    for result in results["results"]:
        base_row = {
            "merchant_id": result["merchant_id"],
            "merchant_name": result["merchant_name"],
            "search_successful": result["search_successful"],
            "websites_checked": result["websites_checked"],
            "verification_successful": result["best_match"]["address_found"]
            if result["best_match"]
            else False,
            "best_confidence": result["best_match"]["confidence"]
            if result["best_match"]
            else 0,
            "best_match_url": result["best_match"]["url"]
            if result["best_match"]
            else "",
            "best_match_title": result["best_match"]["title"]
            if result["best_match"]
            else "",
            "address_text_found": result["best_match"]["address_text"]
            if result["best_match"]
            else "",
            "screenshot_path": result["best_match"]["screenshot_path"]
            if result["best_match"]
            else "",
            "address_screenshot_path": result["best_match"]["address_screenshot_path"]
            if result["best_match"]
            else "",
        }
        excel_data.append(base_row)

    # Create DataFrame and save to Excel
    df = pd.DataFrame(excel_data)

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save to Excel with multiple sheets
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Main results sheet
        df.to_excel(writer, sheet_name="Verification Results", index=False)

        # Summary sheet
        summary_data = {
            "Metric": [
                "Total Merchants",
                "Processed Merchants",
                "Successful Verifications",
                "Success Rate (%)",
                "Average Websites Checked",
                "Verification Date",
            ],
            "Value": [
                results["total_merchants"],
                results["processed_merchants"],
                results["successful_verifications"],
                f"{results['successful_verifications'] / results['processed_merchants'] * 100:.1f}"
                if results["processed_merchants"] > 0
                else "0",
                f"{df['websites_checked'].mean():.1f}" if len(df) > 0 else "0",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    return output_path


def main():
    """Main function to run the merchant verification process."""
    parser = argparse.ArgumentParser(
        description="Verify merchant addresses from Excel file"
    )
    parser.add_argument(
        "excel_file", help="Path to Excel file containing merchant data"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="verification_results",
        help="Directory to save results and screenshots",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(
        log_level=args.log_level,
        log_dir=os.path.join(args.output_dir, "logs"),
        console=True,
    )

    # Check if Excel file exists
    if not os.path.exists(args.excel_file):
        print(f"Error: Excel file '{args.excel_file}' not found.")
        sys.exit(1)

    try:
        print("Starting merchant verification process...")
        print(f"Excel file: {args.excel_file}")
        print(f"Output directory: {args.output_dir}")
        print(f"Headless mode: {args.headless}")
        print("-" * 60)

        # Process merchant verification
        results = process_merchant_verification(args.excel_file, args.output_dir)

        # Save results to Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_output_path = os.path.join(
            args.output_dir, f"verification_results_{timestamp}.xlsx"
        )
        save_results_to_excel(results, excel_output_path)

        # Save results to JSON for additional analysis
        json_output_path = os.path.join(
            args.output_dir, f"verification_results_{timestamp}.json"
        )
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Print summary
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Total merchants processed: {results['processed_merchants']}")
        print(f"Successful verifications: {results['successful_verifications']}")
        print(
            f"Success rate: {results['successful_verifications'] / results['processed_merchants'] * 100:.1f}%"
        )
        print("\nResults saved to:")
        print(f"  Excel: {excel_output_path}")
        print(f"  JSON:  {json_output_path}")
        print(f"  Screenshots: {os.path.join(args.output_dir, 'screenshots')}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during verification process: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
