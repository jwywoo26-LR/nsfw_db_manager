#!/usr/bin/env python3
"""
Simple Batch Uploader for Miro - Upload all CSVs in a directory to Miro boards
Usage: python run_miro_upload.py
"""

import asyncio
import os
import sys
from miro_csv_uploader import MiroCSVUploader
from dotenv import load_dotenv

# Configuration
CSV_FILE = "../resources/csvs/nsfw_data_v3.csv"  # Path to your CSV file
IMAGE_DIRECTORY = "../resources/nsfw_data"  # Path to images directory
LAYOUT = "grid"  # Options: "grid", "by_angle", "by_action"


async def main():
    """Upload single CSV file to Miro"""

    # Load environment variables
    load_dotenv()

    MIRO_TOKEN = os.getenv("MIRO_TOKEN")
    AWS_CONFIG = {
        'region_name': os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
        'aws_access_key_id': os.getenv("AWS_ACCESS_KEY_ID"),
        'aws_secret_access_key': os.getenv("AWS_SECRET_ACCESS_KEY")
    }
    S3_BUCKET = os.getenv("S3_BUCKET", "genvas-saas-stage")

    # Validate environment
    if not MIRO_TOKEN or not AWS_CONFIG.get('aws_access_key_id') or not AWS_CONFIG.get('aws_secret_access_key'):
        print("❌ Missing required environment variables!")
        print("📝 Set these in your .env file:")
        print("   MIRO_TOKEN=your_miro_token")
        print("   AWS_ACCESS_KEY_ID=your_aws_key")
        print("   AWS_SECRET_ACCESS_KEY=your_aws_secret")
        print("   S3_BUCKET=your_s3_bucket")
        sys.exit(1)

    # Validate paths
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV file not found: {CSV_FILE}")
        print(f"💡 Edit CSV_FILE in this script to point to your CSV")
        sys.exit(1)

    if not os.path.exists(IMAGE_DIRECTORY):
        print(f"❌ Image directory not found: {IMAGE_DIRECTORY}")
        print(f"💡 Edit IMAGE_DIRECTORY in this script to point to your images")
        sys.exit(1)

    print(f"🚀 Starting upload...")
    print(f"📄 CSV File: {CSV_FILE}")
    print(f"🖼️ Image Directory: {IMAGE_DIRECTORY}")
    print(f"📐 Layout: {LAYOUT}")
    print(f"{'='*60}\n")

    # Initialize uploader
    uploader = MiroCSVUploader(
        miro_token=MIRO_TOKEN,
        aws_config=AWS_CONFIG,
        s3_bucket=S3_BUCKET,
        batch_size=20,
        max_concurrent_uploads=10,
        delay_between_batches=0.5
    )

    # Upload single CSV
    success = await uploader.create_board_from_csv(
        csv_path=CSV_FILE,
        image_directory=IMAGE_DIRECTORY,
        layout=LAYOUT
    )

    # Summary
    if success:
        print(f"\n🎉 Upload completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Upload failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
