"""
Zip Uploader for NSFW Image Asset Manager
Unzips a file containing CSV and images, then uploads to the backend server
"""

import zipfile
import pandas as pd
import requests
from pathlib import Path
import os
import tempfile
import shutil
from typing import Optional


def upload_image_with_metadata(
    image_path: str,
    angle_1: str,
    angle_2: str,
    action_1: Optional[str] = None,
    action_2: Optional[str] = None,
    action_3: Optional[str] = None,
    backend_url: str = "http://127.0.0.1:8001"
) -> dict:
    """
    Upload an image with metadata to the backend server

    Args:
        image_path: Path to the image file
        angle_1: First angle direction (e.g., "above", "below")
        angle_2: Second angle direction (e.g., "front", "behind", "side")
        action_1: First action direction (optional)
        action_2: Second action direction (optional)
        action_3: Third action direction (optional)
        backend_url: URL of the backend server

    Returns:
        Response dictionary from the server
    """
    # Check if image exists
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Prepare the file
    with open(image_path, 'rb') as f:
        files = {'file': (Path(image_path).name, f, 'image/png')}

        # Prepare the metadata
        data = {
            'angle_1': angle_1,
            'angle_2': angle_2,
        }

        # Add optional action fields if provided
        if action_1:
            data['action_1'] = action_1
        if action_2:
            data['action_2'] = action_2
        if action_3:
            data['action_3'] = action_3

        # Upload to backend
        response = requests.post(
            f"{backend_url}/api/upload",
            files=files,
            data=data,
            timeout=30
        )

        response.raise_for_status()
        return response.json()


def process_zip_upload(
    zip_path: str,
    backend_url: str = "http://127.0.0.1:8001",
    csv_filename: Optional[str] = None
) -> dict:
    """
    Process a zip file containing CSV and images, upload all to backend

    Expected zip structure:
        archive.zip
        ├── data.csv (or specified csv_filename)
        └── resources/
            └── nsfw_data/
                └── images...

    CSV Format:
        reference_image_name,reference_image_path,angle_direction_1,angle_direction_2,action_direction_1
        testright_02_v1,../resources/nsfw_data/test right_02.png,above,front,test

    Args:
        zip_path: Path to the zip file
        backend_url: URL of the backend server
        csv_filename: Name of CSV file in zip (will auto-detect if None)

    Returns:
        Dictionary with success/failure counts and details
    """
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp()

    try:
        print(f"Extracting zip file: {zip_path}")

        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        print(f"Extracted to: {temp_dir}\n")

        # Find CSV file
        csv_path = None
        if csv_filename:
            csv_path = Path(temp_dir) / csv_filename
        else:
            # Auto-detect CSV file
            csv_files = list(Path(temp_dir).rglob("*.csv"))
            if not csv_files:
                raise FileNotFoundError("No CSV file found in zip archive")
            csv_path = csv_files[0]
            print(f"Found CSV file: {csv_path.name}")

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} rows in CSV\n")

        results = {
            'total': len(df),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        # Process each row
        for idx, row in df.iterrows():
            try:
                # Extract metadata
                reference_name = row.get('reference_image_name', '')
                image_path = row.get('reference_image_path', '')
                angle_1 = row.get('angle_direction_1', '')
                angle_2 = row.get('angle_direction_2', '')
                action_1 = row.get('action_direction_1', None)
                action_2 = row.get('action_direction_2', None) if 'action_direction_2' in row else None
                action_3 = row.get('action_direction_3', None) if 'action_direction_3' in row else None

                # Handle empty strings as None
                action_1 = action_1 if pd.notna(action_1) and str(action_1).strip() else None
                action_2 = action_2 if pd.notna(action_2) and str(action_2).strip() else None
                action_3 = action_3 if pd.notna(action_3) and str(action_3).strip() else None

                # Resolve image path (handle relative paths from CSV location)
                csv_dir = csv_path.parent
                resolved_path = (csv_dir / image_path).resolve()

                print(f"Processing [{idx+1}/{len(df)}]: {reference_name}")
                print(f"  Image: {resolved_path.name}")
                print(f"  Angles: {angle_1}, {angle_2}")
                print(f"  Actions: {action_1 or 'N/A'}, {action_2 or 'N/A'}, {action_3 or 'N/A'}")

                # Upload
                response = upload_image_with_metadata(
                    image_path=str(resolved_path),
                    angle_1=angle_1,
                    angle_2=angle_2,
                    action_1=action_1,
                    action_2=action_2,
                    action_3=action_3,
                    backend_url=backend_url
                )

                results['successful'] += 1
                asset_id = response.get('asset', {}).get('id')
                print(f"  ✓ Success! Asset ID: {asset_id}\n")

            except Exception as e:
                results['failed'] += 1
                error_msg = f"Row {idx+1} ({reference_name}): {str(e)}"
                results['errors'].append(error_msg)
                print(f"  ✗ Failed: {str(e)}\n")

        return results

    finally:
        # Clean up temporary directory
        print(f"Cleaning up temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Main function to run the zip uploader"""
    import sys

    # Configuration
    ZIP_PATH = "path/to/your/archive.zip"  # TODO: Update this path
    BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
    CSV_FILENAME = None  # Will auto-detect if None

    # Allow zip path as command line argument
    if len(sys.argv) > 1:
        ZIP_PATH = sys.argv[1]

    if len(sys.argv) > 2:
        CSV_FILENAME = sys.argv[2]

    if not Path(ZIP_PATH).exists():
        print(f"Error: Zip file not found: {ZIP_PATH}")
        print(f"Usage: python zip_uploader.py <path_to_zip> [csv_filename]")
        sys.exit(1)

    print(f"Starting zip upload process...")
    print(f"Zip File: {ZIP_PATH}")
    print(f"Backend: {BACKEND_URL}\n")
    print("=" * 60)

    # Process the zip
    results = process_zip_upload(ZIP_PATH, BACKEND_URL, CSV_FILENAME)

    # Print summary
    print("=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total images: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")

    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")

    print("=" * 60)


if __name__ == "__main__":
    main()
