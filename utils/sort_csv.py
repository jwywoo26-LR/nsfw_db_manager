#!/usr/bin/env python3
"""
Quick CSV sorting utility.
Sorts CSV files by the 'reference_image' column.
"""

import pandas as pd
from pathlib import Path
import sys


def sort_csv(csv_path: str, sort_column: str = "reference_image", backup: bool = True):
    """
    Sort a CSV file by a specified column.

    Args:
        csv_path: Path to the CSV file
        sort_column: Column name to sort by (default: "reference_image")
        backup: Whether to create a backup before sorting (default: True)
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"❌ Error: File not found: {csv_path}")
        return False

    try:
        # Read CSV
        print(f"📖 Reading {csv_path.name}...")
        df = pd.read_csv(csv_path)

        # Check if sort column exists
        if sort_column not in df.columns:
            print(f"❌ Error: Column '{sort_column}' not found in CSV")
            print(f"Available columns: {', '.join(df.columns)}")
            return False

        # Create backup
        if backup:
            backup_path = csv_path.with_suffix('.csv.bak')
            df.to_csv(backup_path, index=False)
            print(f"💾 Backup created: {backup_path.name}")

        # Sort by column
        original_order = df[sort_column].tolist()[:5]
        df_sorted = df.sort_values(by=sort_column)
        sorted_order = df_sorted[sort_column].tolist()[:5]

        # Save sorted CSV
        df_sorted.to_csv(csv_path, index=False)

        print(f"✅ Sorted {csv_path.name} by '{sort_column}'")
        print(f"   Original first 5: {original_order}")
        print(f"   Sorted first 5:   {sorted_order}")
        print(f"   Total rows: {len(df_sorted)}")

        return True

    except Exception as e:
        print(f"❌ Error sorting {csv_path.name}: {e}")
        return False


def main():
    """Main entry point."""

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    csvs_dir = project_root / "resources" / "csvs"

    # Define CSVs to sort
    csv_files = [
        "sounds_effect_map_V2.csv",
        "sounds_effect_map_V3.csv"
    ]

    print("=" * 60)
    print("CSV Sorting Utility")
    print("=" * 60)
    print()

    success_count = 0

    for csv_name in csv_files:
        csv_path = csvs_dir / csv_name
        if sort_csv(csv_path):
            success_count += 1
        print()

    print("=" * 60)
    print(f"✅ Successfully sorted {success_count}/{len(csv_files)} files")
    print("=" * 60)


if __name__ == "__main__":
    main()
