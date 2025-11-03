"""
Direct CSV to Database Uploader
Uploads images directly from the project directory without requiring zip files
"""

import pandas as pd
import requests
from pathlib import Path
import os
from typing import Optional


def upload_image_with_metadata(
    image_path: str,
    angle_1: str,
    angle_2: str,
    action_1: Optional[str] = None,
    action_2: Optional[str] = None,
    action_3: Optional[str] = None,
    prompt: Optional[str] = None,
    backend_url: str = "http://127.0.0.1:8001"
) -> dict:
    """
    Upload an image with metadata to the backend server

    Args:
        image_path: Path to the image file
        angle_1: First angle direction
        angle_2: Second angle direction
        action_1: First action direction (optional)
        action_2: Second action direction (optional)
        action_3: Third action direction (optional)
        prompt: Description or generation prompt (optional)
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

        # Prepare query parameters
        params = {}
        if angle_1:
            params['angle_1'] = angle_1
        if angle_2:
            params['angle_2'] = angle_2
        if action_1:
            params['action_1'] = action_1
        if action_2:
            params['action_2'] = action_2
        if action_3:
            params['action_3'] = action_3
        if prompt:
            params['prompt'] = prompt

        # Upload to backend
        response = requests.post(
            f"{backend_url}/api/upload",
            files=files,
            params=params,
            timeout=30
        )

        response.raise_for_status()
        return response.json()


def process_csv_direct_upload(
    csv_path: str,
    images_base_dir: str,
    backend_url: str = "http://127.0.0.1:8001"
) -> dict:
    """
    Process CSV and upload images directly from the local filesystem

    Args:
        csv_path: Path to the CSV file
        images_base_dir: Base directory where images are located
        backend_url: URL of the backend server

    Returns:
        Dictionary with success/failure counts and details
    """
    csv_path = Path(csv_path)
    images_base_dir = Path(images_base_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if not images_base_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_base_dir}")

    print(f"Reading CSV file: {csv_path}")
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
            image_path_from_csv = row.get('reference_image_path', '')
            angle_1 = row.get('angle_direction_1', '')
            angle_2 = row.get('angle_direction_2', '')
            action_1 = row.get('action_direction_1', None)
            action_2 = row.get('action_direction_2', None) if 'action_direction_2' in row else None
            action_3 = row.get('action_direction_3', None) if 'action_direction_3' in row else None
            prompt = row.get('prompt', None) if 'prompt' in row else None

            # Handle empty strings as None
            action_1 = action_1 if pd.notna(action_1) and str(action_1).strip() else None
            action_2 = action_2 if pd.notna(action_2) and str(action_2).strip() else None
            action_3 = action_3 if pd.notna(action_3) and str(action_3).strip() else None
            prompt = prompt if pd.notna(prompt) and str(prompt).strip() else None

            # Extract filename from CSV path
            # CSV has paths like: ../resources/nsfw_data/image.png
            # We need to extract just the filename
            filename = Path(image_path_from_csv).name

            # Construct actual path
            actual_image_path = images_base_dir / filename

            print(f"[{idx+1}/{len(df)}] {reference_name}")
            print(f"  File: {filename}")
            print(f"  Path: {actual_image_path}")
            print(f"  Angles: {angle_1}, {angle_2}")
            print(f"  Actions: {action_1 or 'N/A'}, {action_2 or 'N/A'}, {action_3 or 'N/A'}")

            if not actual_image_path.exists():
                raise FileNotFoundError(f"Image not found: {actual_image_path}")

            # Upload
            response = upload_image_with_metadata(
                image_path=str(actual_image_path),
                angle_1=angle_1,
                angle_2=angle_2,
                action_1=action_1,
                action_2=action_2,
                action_3=action_3,
                prompt=prompt,
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


def main():
    """Main function to run the CSV uploader"""
    import sys

    # Default configuration
    CSV_PATH = "resources/csvs/nsfw_data_v3.csv"
    IMAGES_DIR = "resources/nsfw_data"
    BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")

    # Allow command line arguments
    if len(sys.argv) > 1:
        CSV_PATH = sys.argv[1]
    if len(sys.argv) > 2:
        IMAGES_DIR = sys.argv[2]
    if len(sys.argv) > 3:
        BACKEND_URL = sys.argv[3]

    print("=" * 60)
    print("CSV to Database Upload Process")
    print("=" * 60)
    print(f"CSV File: {CSV_PATH}")
    print(f"Images Directory: {IMAGES_DIR}")
    print(f"Backend URL: {BACKEND_URL}")
    print("=" * 60)
    print()

    # Check if backend is running
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        print(f"✓ Backend is running: {response.json()}\n")
    except Exception as e:
        print(f"✗ Error: Cannot connect to backend at {BACKEND_URL}")
        print(f"  Make sure the backend server is running:")
        print(f"  cd nsfw_db_manager/backend && python run_server.py")
        print(f"  Error: {e}\n")
        sys.exit(1)

    # Process the CSV
    results = process_csv_direct_upload(CSV_PATH, IMAGES_DIR, BACKEND_URL)

    # Print summary
    print("=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total images: {results['total']}")
    print(f"✓ Successful: {results['successful']}")
    print(f"✗ Failed: {results['failed']}")
    print(f"Success rate: {results['successful']/results['total']*100:.1f}%")

    if results['errors']:
        print(f"\nFirst 10 errors:")
        for error in results['errors'][:10]:
            print(f"  - {error}")

        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")

    print("=" * 60)

    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    exit(main())
