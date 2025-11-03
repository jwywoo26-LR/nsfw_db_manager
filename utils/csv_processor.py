import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


class CSVProcessor:
    def read_csv_rows(self, csv_path: str) -> List[Dict[str, Any]]:
        """Read all rows from a CSV file and return as list of dictionaries."""
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)
        
        return rows
    
    def get_rows_by_column_value(self, csv_path: str, column: str, value: Any) -> List[Dict[str, Any]]:
        """Get rows where a specific column matches a value."""
        rows = self.read_csv_rows(csv_path)
        return [row for row in rows if row.get(column) == str(value)]
    
    def get_column_values(self, csv_path: str, column: str) -> List[str]:
        """Get all values from a specific column."""
        rows = self.read_csv_rows(csv_path)
        return [row.get(column, '') for row in rows]
    
    def count_rows(self, csv_path: str) -> int:
        """Count the number of data rows in the CSV (excluding header)."""
        return len(self.read_csv_rows(csv_path))
    
    def update_row(self, csv_path: str, row_index: int, updates: Dict[str, Any]) -> None:
        """Update specific fields in a row by index, adding new columns if needed."""
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            original_fieldnames = list(reader.fieldnames) if reader.fieldnames else []
            for i, row in enumerate(reader):
                if i == row_index:
                    row.update(updates)
                rows.append(row)
        
        # Determine all fieldnames (original + new ones from updates)
        new_fields = set()
        for row in rows:
            new_fields.update(row.keys())
        
        # Combine original fieldnames with new fields, preserving order
        all_fieldnames = original_fieldnames.copy()
        for field in new_fields:
            if field not in all_fieldnames:
                all_fieldnames.append(field)
        
        with open(csv_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def main():
    processor = CSVProcessor()
    
    # Example usage - you provide the path
    csv_path = "sheets/20250825_prompts.csv"
    
    try:
        rows = processor.read_csv_rows(csv_path)
        print(f"Total rows: {len(rows)}")
        
        for i, row in enumerate(rows):
            print(f"Row {i}: {row}")
            
    except FileNotFoundError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()