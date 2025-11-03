#!/usr/bin/env python3
"""
Miro Group Uploader - Upload images organized by directories
Creates a new board and uploads images grouped by directory with 5cm gaps
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from miro_group_board import MiroGroupBoard

load_dotenv()


class MiroGroupUploader:
    """
    Upload images from directories to Miro boards with grouping and gaps
    """

    def __init__(self,
                 miro_token: str,
                 aws_config: dict,
                 s3_bucket: str,
                 max_concurrent_uploads: int = 10):
        """
        Initialize Miro Group Uploader

        Args:
            miro_token: Miro API token
            aws_config: AWS configuration dict
            s3_bucket: S3 bucket name
            max_concurrent_uploads: Max concurrent S3 uploads
        """
        self.miro_token = miro_token
        self.aws_config = aws_config
        self.s3_bucket = s3_bucket
        self.max_concurrent_uploads = max_concurrent_uploads

        self.board_client = None
        self.stats = {
            'total_directories': 0,
            'total_images': 0,
            'uploaded_images': 0,
            'failed_images': 0
        }

    def organize_directory_images(self, base_directory: str) -> List[Dict]:
        """
        Organize images from subdirectories

        Args:
            base_directory: Path to base directory containing subdirectories

        Returns:
            List of directory data with image files
        """
        base_path = Path(base_directory)

        if not base_path.exists():
            raise ValueError(f"Directory not found: {base_directory}")

        # Get all subdirectories
        subdirs = [d for d in base_path.iterdir() if d.is_dir()]

        if not subdirs:
            raise ValueError(f"No subdirectories found in {base_directory}")

        # Organize by directory
        directory_data = []
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

        for subdir in sorted(subdirs):
            image_files = [
                f for f in subdir.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            if image_files:
                directory_data.append({
                    'directory_name': subdir.name,
                    'directory_path': str(subdir),
                    'image_files': sorted(image_files)
                })
                self.stats['total_images'] += len(image_files)

        self.stats['total_directories'] = len(directory_data)
        return directory_data

    async def create_board_from_directories(self,
                                           base_directory: str,
                                           board_name: str = None) -> bool:
        """
        Create a new Miro board and upload images organized by directories

        Args:
            base_directory: Path to base directory containing subdirectories
            board_name: Name for the Miro board (auto-generated if None)

        Returns:
            True if successful
        """
        try:
            # Organize directory images
            print(f"📂 Scanning directory: {base_directory}")
            directory_data = self.organize_directory_images(base_directory)

            print(f"✅ Found {self.stats['total_directories']} directories with {self.stats['total_images']} total images\n")

            # Create Miro board
            if board_name is None:
                board_name = f"NSFW Groups - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            self.board_client = MiroGroupBoard(
                miro_token=self.miro_token,
                aws_config=self.aws_config,
                s3_bucket=self.s3_bucket
            )

            print(f"🎨 Creating Miro board: {board_name}")
            if not self.board_client.create_miro_board(board_name, f"Grouped images from {base_directory}"):
                return False

            board_id = self.board_client.board_id

            # Upload images
            success = await self._upload_grouped_layout(directory_data, board_id)

            # Display stats
            self._display_stats()

            return success

        except Exception as e:
            print(f"❌ Error creating board from directories: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _upload_grouped_layout(self, directory_data: List[Dict], board_id: str) -> bool:
        """
        Upload images organized by directory with section headers and 5cm gaps

        Args:
            directory_data: List of directory data with images
            board_id: Miro board ID

        Returns:
            True if successful
        """
        try:
            print(f"\n📐 Uploading with grouped layout (5cm gaps between directories)")

            # Layout settings
            start_x = 0
            start_y = 0
            current_y = start_y

            async with aiohttp.ClientSession() as session:
                for dir_idx, dir_data in enumerate(directory_data):
                    directory_name = dir_data['directory_name']
                    image_files = dir_data['image_files']

                    print(f"\n📁 [{dir_idx + 1}/{len(directory_data)}] Processing: {directory_name}")
                    print(f"   Found {len(image_files)} images")

                    # Get actual image dimensions from first image to determine layout
                    if image_files:
                        first_image = image_files[0]
                        img_width, img_height = self.board_client.get_image_dimensions(str(first_image))
                        print(f"   📏 Image dimensions: {img_width}x{img_height}")
                    else:
                        img_width, img_height = 400, 600

                    # Calculate header width based on actual image size and 5 images per row
                    header_width = (
                        img_width * self.board_client.images_per_row +
                        self.board_client.gap_between_images * (self.board_client.images_per_row - 1)
                    )

                    # Create section header
                    await self.board_client.create_section_header(
                        session,
                        directory_name,
                        start_x,
                        current_y,
                        header_width
                    )

                    # Move Y position below header
                    current_y += self.board_client.section_header_height + 150

                    # Upload images to S3 first
                    print(f"   📤 Uploading to S3...")
                    upload_tasks = []
                    semaphore = asyncio.Semaphore(self.max_concurrent_uploads)

                    for img_file in image_files:
                        s3_key = f"{self.board_client.s3_prefix}{directory_name}/{img_file.name}"
                        task = self.board_client.upload_image_to_s3_async(str(img_file), s3_key)
                        upload_tasks.append((task, img_file.name, str(img_file)))

                    async def limited_upload(task, filename, filepath):
                        async with semaphore:
                            result = await task
                            if result:
                                self.stats['uploaded_images'] += 1
                            else:
                                self.stats['failed_images'] += 1
                            return (result, filename, filepath)

                    upload_results = await asyncio.gather(
                        *[limited_upload(task, filename, filepath) for task, filename, filepath in upload_tasks],
                        return_exceptions=True
                    )

                    # Add images to Miro board in 5-column grid
                    print(f"   🎨 Adding to Miro board (5 images per row)...")
                    miro_tasks = []
                    max_y = current_y

                    for idx, result in enumerate(upload_results):
                        if isinstance(result, tuple) and result[0]:
                            s3_url, filename, _ = result

                            # Calculate grid position - 5 images horizontally, then new row
                            row = idx // self.board_client.images_per_row
                            col = idx % self.board_client.images_per_row

                            x = start_x + col * (img_width + self.board_client.gap_between_images)
                            y = current_y + row * (img_height + self.board_client.gap_between_images)

                            task = self.board_client.add_image_to_board(session, s3_url, x, y, filename)
                            miro_tasks.append(task)
                            max_y = max(max_y, y + img_height)

                    miro_results = await asyncio.gather(*miro_tasks, return_exceptions=True)
                    success_count = sum(1 for r in miro_results if r is True)

                    print(f"   ✅ Added {success_count}/{len(miro_tasks)} images to board")

                    # Move to next section with 5cm gap
                    current_y = max_y + self.board_client.gap_between_directories

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

            return True

        except Exception as e:
            print(f"❌ Error uploading grouped layout: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _display_stats(self):
        """Display upload statistics"""
        print(f"\n{'='*60}")
        print(f"📊 Upload Statistics:")
        print(f"   Directories processed: {self.stats['total_directories']}")
        print(f"   Total images: {self.stats['total_images']}")
        print(f"   Successfully uploaded: {self.stats['uploaded_images']}")
        print(f"   Failed: {self.stats['failed_images']}")
        print(f"{'='*60}")


async def main():
    """
    Main function to upload grouped images to Miro board
    """
    # Configuration
    BASE_DIRECTORY = "../resources/nsfw_data_by_action"  # Directory containing subdirectories with images

    # Load from environment
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
    if not os.path.exists(BASE_DIRECTORY):
        print(f"❌ Directory not found: {BASE_DIRECTORY}")
        print(f"💡 Edit BASE_DIRECTORY in this script to point to your directory")
        sys.exit(1)

    print(f"🚀 Starting grouped upload...")
    print(f"📂 Base Directory: {BASE_DIRECTORY}")
    print(f"☁️  S3 Bucket: {S3_BUCKET}")
    print(f"{'='*60}\n")

    # Initialize uploader
    uploader = MiroGroupUploader(
        miro_token=MIRO_TOKEN,
        aws_config=AWS_CONFIG,
        s3_bucket=S3_BUCKET,
        max_concurrent_uploads=10
    )

    # Upload directories
    success = await uploader.create_board_from_directories(BASE_DIRECTORY)

    # Summary
    if success:
        print(f"\n🎉 Upload completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Upload failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
