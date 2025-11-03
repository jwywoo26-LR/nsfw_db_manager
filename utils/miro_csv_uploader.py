#!/usr/bin/env python3
"""
Miro CSV Uploader - Batch upload images from CSV files to Miro boards
Supports fast async uploads with safety features (rate limiting, error handling, resume capability)
"""

import os
import asyncio
import aiohttp
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from miro_board_creator import MiroBoardCreator
from csv_processor import CSVProcessor

load_dotenv()


class MiroCSVUploader:
    """
    Upload images from CSV files to Miro boards with batch processing support
    """

    def __init__(self,
                 miro_token: str,
                 aws_config: dict,
                 s3_bucket: str,
                 batch_size: int = 20,
                 max_concurrent_uploads: int = 10,
                 delay_between_batches: float = 0.5):
        """
        Initialize Miro CSV Uploader

        Args:
            miro_token: Miro API token
            aws_config: AWS configuration dict
            s3_bucket: S3 bucket name
            batch_size: Number of images to process in each batch (default: 20)
            max_concurrent_uploads: Max concurrent S3 uploads (default: 10)
            delay_between_batches: Delay in seconds between batches (default: 0.5)
        """
        self.miro_token = miro_token
        self.aws_config = aws_config
        self.s3_bucket = s3_bucket
        self.batch_size = batch_size
        self.max_concurrent_uploads = max_concurrent_uploads
        self.delay_between_batches = delay_between_batches

        self.csv_processor = CSVProcessor()
        self.miro_client = None

        # Progress tracking
        self.progress_file = ".miro_upload_progress.json"
        self.stats = {
            'total_images': 0,
            'uploaded_images': 0,
            'failed_images': 0,
            'start_time': None,
            'end_time': None
        }

    def _load_progress(self) -> Dict:
        """Load progress from file for resume capability"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Could not load progress file: {e}")
        return {}

    def _save_progress(self, progress: Dict):
        """Save progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")

    def _clear_progress(self):
        """Clear progress file after successful completion"""
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception as e:
                print(f"⚠️ Could not remove progress file: {e}")

    def organize_csv_images(self, csv_data: List[Dict], image_directory: str) -> List[Dict]:
        """
        Organize images from CSV data - supports both old and new CSV formats

        Args:
            csv_data: List of CSV rows with columns:
                Old format:
                  - reference_image: Image filename
                  - angle_direction_1, angle_direction_2: Angle tags
                  - action_direction_1: Action tag
                New format (with versions):
                  - reference_image_name: Name with version (e.g., image_v1, image_v2)
                  - reference_image_path: Actual image path
                  - angle_direction_1, angle_direction_2: Angle tags
                  - action_direction_1: Action tag
            image_directory: Directory containing the images

        Returns:
            List of organized image data grouped by actual image path
        """
        # Check if using new format (with reference_image_name and reference_image_path)
        has_new_format = csv_data and 'reference_image_name' in csv_data[0]

        if has_new_format:
            # Group rows by reference_image_path
            image_groups = {}

            for row_index, row in enumerate(csv_data):
                image_path = row.get('reference_image_path', '').strip()
                if not image_path:
                    continue

                if not os.path.exists(image_path):
                    print(f"⚠️ Image not found: {image_path}")
                    continue

                # Collect angle tags
                angles = []
                for i in [1, 2]:
                    angle = row.get(f'angle_direction_{i}', '').strip()
                    if angle and angle != '-':
                        angles.append(angle)

                # Get single action tag
                action = row.get('action_direction_1', '').strip()
                actions = [action] if action and action != '-' else []

                version_name = row.get('reference_image_name', '').strip()

                # Group by image path
                if image_path not in image_groups:
                    image_groups[image_path] = []

                image_groups[image_path].append({
                    'version_name': version_name,
                    'angles': angles,
                    'actions': actions
                })

            # Convert groups to organized data
            organized_data = []
            for image_path, versions in image_groups.items():
                organized_data.append({
                    'image_path': image_path,
                    'reference_image': os.path.basename(image_path),
                    'versions': versions,
                    'display_label': f"{os.path.basename(image_path)[:30]}..."
                })

        else:
            # Old format - single row per image
            organized_data = []

            for row_index, row in enumerate(csv_data):
                # Get reference image
                reference_image = row.get('reference_image', '').strip()
                if not reference_image:
                    continue

                # Build full image path
                image_path = os.path.join(image_directory, reference_image)
                if not os.path.exists(image_path):
                    print(f"⚠️ Image not found: {reference_image}")
                    continue

                # Collect angle tags
                angles = []
                for i in [1, 2]:
                    angle = row.get(f'angle_direction_{i}', '').strip()
                    if angle:
                        angles.append(angle)

                # Get single action tag
                action = row.get('action_direction_1', '').strip()
                actions = [action] if action else []

                # Create single version for old format
                organized_data.append({
                    'image_path': image_path,
                    'reference_image': reference_image,
                    'versions': [{
                        'version_name': reference_image,
                        'angles': angles,
                        'actions': actions
                    }],
                    'display_label': f"{reference_image[:30]}..."
                })

        return organized_data

    async def create_board_from_csv(self,
                                   csv_path: str,
                                   image_directory: str,
                                   board_title: Optional[str] = None,
                                   layout: str = "grid") -> bool:
        """
        Create a Miro board from a single CSV file

        Args:
            csv_path: Path to CSV file
            image_directory: Directory containing images
            board_title: Custom board title (auto-generated if None)
            layout: Layout type - "grid" (default), "by_angle", or "by_action"

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n{'='*60}")
            print(f"📄 Processing CSV: {os.path.basename(csv_path)}")
            print(f"{'='*60}")

            # Read CSV data
            csv_data = self.csv_processor.read_csv_rows(csv_path)
            print(f"📊 Read {len(csv_data)} rows from CSV")

            if not csv_data:
                print("⚠️ No data in CSV file")
                return False

            # Organize images
            organized_data = self.organize_csv_images(csv_data, image_directory)

            if not organized_data:
                print("❌ No valid images found")
                return False

            self.stats['total_images'] = len(organized_data)
            print(f"🖼️ Found {len(organized_data)} valid images")

            # Generate board title
            if not board_title:
                csv_name = os.path.basename(csv_path).replace('.csv', '')
                timestamp = datetime.now().strftime('%m%d-%H%M')
                board_title = f"{csv_name[:20]}-{len(organized_data)}img-{timestamp}"

            # Initialize Miro client
            self.miro_client = MiroBoardCreator(
                self.miro_token,
                self.aws_config,
                self.s3_bucket
            )

            # Create board
            print(f"🎨 Creating Miro board: '{board_title}'")
            if not self.miro_client.create_miro_board(board_title):
                print("❌ Failed to create Miro board")
                return False

            board_id = self.miro_client.board_id
            print(f"✅ Board created: {board_id}")
            print(f"🔗 Board URL: https://miro.com/app/board/{board_id}/")

            # Estimate time
            estimated_time = (len(organized_data) * 1.5) + 5
            estimated_minutes = estimated_time / 60
            print(f"⏱️ Estimated time: ~{estimated_time:.0f} seconds ({estimated_minutes:.1f} minutes)")

            self.stats['start_time'] = time.time()

            # Upload based on layout type
            if layout == "grid":
                success = await self._upload_grid_layout(organized_data, board_id)
            elif layout == "by_angle":
                success = await self._upload_by_angle_layout(organized_data, board_id)
            elif layout == "by_action":
                success = await self._upload_by_action_layout(organized_data, board_id)
            else:
                print(f"⚠️ Unknown layout: {layout}, using grid")
                success = await self._upload_grid_layout(organized_data, board_id)

            self.stats['end_time'] = time.time()

            # Display stats
            self._display_stats()

            return success

        except Exception as e:
            print(f"❌ Error creating board from CSV: {e}")
            return False

    async def _upload_grid_layout(self, organized_data: List[Dict], board_id: str) -> bool:
        """Upload images in row layout: [Angles Box] [Actions Box] [Image]"""
        try:
            print(f"\n📐 Using ROW layout: [Angles] [Actions] [Image]")

            # Layout settings
            start_x = 100
            start_y = 100
            angle_box_width = 200
            action_box_width = 200
            box_height = 120
            img_width = 200
            gap = 20
            row_gap = 300  # Gap between rows

            # Create header
            header_text = f"Image List\\nTotal: {len(organized_data)} images\\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.miro_client.miro_shape(start_x, start_y - 100, 800, 60, header_text, "#e6f3ff")

            # Upload images in batches
            async with aiohttp.ClientSession() as session:
                # Upload all images to S3 first
                print(f"\n📤 Step 1/2: Uploading {len(organized_data)} images to S3...")
                upload_tasks = []

                for idx, img_data in enumerate(organized_data):
                    s3_key = f"miro_boards/{board_id}/{os.path.basename(img_data['image_path'])}"
                    task = self.miro_client.upload_image_to_s3_async(img_data['image_path'], s3_key)
                    upload_tasks.append((task, img_data, idx))

                # Process uploads with concurrency limit
                semaphore = asyncio.Semaphore(self.max_concurrent_uploads)

                async def limited_upload(task, img_data, idx):
                    async with semaphore:
                        result = await task
                        if result:
                            self.stats['uploaded_images'] += 1
                            print(f"  ✅ [{self.stats['uploaded_images']}/{len(organized_data)}] Uploaded: {img_data['display_label']}")
                        else:
                            self.stats['failed_images'] += 1
                            print(f"  ❌ Failed: {img_data['display_label']}")
                        return (result, img_data, idx)

                upload_results = await asyncio.gather(
                    *[limited_upload(task, img_data, idx) for task, img_data, idx in upload_tasks],
                    return_exceptions=True
                )

                # Add images to Miro board
                print(f"\n🎨 Step 2/2: Adding images and tables to Miro board...")

                # Collect all shape and image tasks first
                all_shape_tasks = []
                all_image_tasks = []

                for result in upload_results:
                    if isinstance(result, tuple) and result[0]:
                        s3_url, img_data, idx = result

                        # Calculate row position
                        row_y = start_y + (idx * row_gap)

                        # Table structure with versions
                        table_x = start_x
                        cell_width = 100
                        cell_height = 40

                        versions = img_data.get('versions', [])

                        # Header row - collect all header cells (Version, angle_1, angle_2, action_1)
                        header_y = row_y
                        all_shape_tasks.append((table_x, header_y, cell_width, cell_height, "Version", "#cccccc"))
                        all_shape_tasks.append((table_x + cell_width, header_y, cell_width, cell_height, "angle_1", "#cccccc"))
                        all_shape_tasks.append((table_x + cell_width*2, header_y, cell_width, cell_height, "angle_2", "#cccccc"))
                        all_shape_tasks.append((table_x + cell_width*3, header_y, cell_width, cell_height, "action_1", "#cccccc"))

                        # Data rows - one row per version
                        for v_idx, version in enumerate(versions):
                            data_y = row_y + cell_height + (v_idx * cell_height)

                            angles = version.get('angles', [])
                            actions = version.get('actions', [])
                            version_name = version.get('version_name', '')

                            # Extract version number (e.g., "v1" from "image_v1")
                            version_label = version_name.split('_')[-1] if '_v' in version_name else version_name

                            angle_1 = angles[0] if len(angles) > 0 else '-'
                            angle_2 = angles[1] if len(angles) > 1 else '-'
                            action_1 = actions[0] if len(actions) > 0 else '-'

                            all_shape_tasks.append((table_x, data_y, cell_width, cell_height, version_label, "#f0f0f0"))
                            all_shape_tasks.append((table_x + cell_width, data_y, cell_width, cell_height, angle_1, "#e6f3ff"))
                            all_shape_tasks.append((table_x + cell_width*2, data_y, cell_width, cell_height, angle_2, "#e6f3ff"))
                            all_shape_tasks.append((table_x + cell_width*3, data_y, cell_width, cell_height, action_1, "#ffe6f0"))

                        # Add image to the right of the table (4 columns now instead of 6)
                        image_x = table_x + (cell_width * 4) + 60  # 60px gap between table and image
                        image_y = row_y + (cell_height * (1 + len(versions)) / 2)  # Center image with table rows
                        all_image_tasks.append((image_x, image_y, s3_url, img_width))

                # Process all shapes in batches (much faster than individual calls)
                print(f"  📋 Creating {len(all_shape_tasks)} table cells...")
                for i in range(0, len(all_shape_tasks), self.batch_size):
                    batch = all_shape_tasks[i:i + self.batch_size]
                    print(f"    📤 Processing shape batch {i//self.batch_size + 1}/{(len(all_shape_tasks) + self.batch_size - 1)//self.batch_size} ({len(batch)} cells)")

                    shape_coroutines = [
                        self.miro_client.miro_shape_async(session, x, y, w, h, text, fill)
                        for x, y, w, h, text, fill in batch
                    ]
                    await asyncio.gather(*shape_coroutines, return_exceptions=True)

                    if i + self.batch_size < len(all_shape_tasks):
                        await asyncio.sleep(self.delay_between_batches)

                # Process all images in batches
                print(f"  🖼️ Adding {len(all_image_tasks)} images...")
                for i in range(0, len(all_image_tasks), self.batch_size):
                    batch = all_image_tasks[i:i + self.batch_size]
                    print(f"    📤 Processing image batch {i//self.batch_size + 1}/{(len(all_image_tasks) + self.batch_size - 1)//self.batch_size} ({len(batch)} images)")

                    image_coroutines = [
                        self.miro_client.miro_image_async(session, x, y, url, w)
                        for x, y, url, w in batch
                    ]
                    await asyncio.gather(*image_coroutines, return_exceptions=True)

                    if i + self.batch_size < len(all_image_tasks):
                        await asyncio.sleep(self.delay_between_batches)

            print(f"\n✅ Grid layout completed!")
            return True

        except Exception as e:
            print(f"❌ Error in grid layout: {e}")
            return False

    async def _upload_by_angle_layout(self, organized_data: List[Dict], board_id: str) -> bool:
        """Upload images organized by angle"""
        try:
            print(f"\n📐 Using BY_ANGLE layout")

            # Group by angle
            angle_groups = {}
            for img_data in organized_data:
                angle_key = img_data['angle_label']
                if angle_key not in angle_groups:
                    angle_groups[angle_key] = []
                angle_groups[angle_key].append(img_data)

            print(f"📊 Found {len(angle_groups)} angle groups")

            # Layout settings
            start_x = 100
            start_y = 100
            img_width = 150
            img_gap = 20
            row_height = 250
            cols_per_row = 6
            current_y = start_y

            # Create header
            header_text = f"Images by Angle\nTotal: {len(organized_data)} images in {len(angle_groups)} groups\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.miro_client.miro_shape(start_x, current_y - 80, 800, 60, header_text, "#e6f3ff")

            async with aiohttp.ClientSession() as session:
                # Process each angle group
                for angle_idx, (angle_label, images) in enumerate(sorted(angle_groups.items()), 1):
                    print(f"\n📝 Processing angle group {angle_idx}/{len(angle_groups)}: {angle_label} ({len(images)} images)")

                    # Add angle header
                    self.miro_client.miro_shape(start_x, current_y, 200, 60, f"Angle: {angle_label}", "#fff2cc")

                    # Upload images for this angle
                    upload_tasks = []
                    for img_data in images:
                        s3_key = f"miro_boards/{board_id}/{os.path.basename(img_data['image_path'])}"
                        task = self.miro_client.upload_image_to_s3_async(img_data['image_path'], s3_key)
                        upload_tasks.append((task, img_data))

                    # Execute uploads with rate limiting
                    semaphore = asyncio.Semaphore(self.max_concurrent_uploads)

                    async def limited_upload(task, img_data):
                        async with semaphore:
                            result = await task
                            if result:
                                self.stats['uploaded_images'] += 1
                            else:
                                self.stats['failed_images'] += 1
                            return (result, img_data)

                    upload_results = await asyncio.gather(
                        *[limited_upload(task, img_data) for task, img_data in upload_tasks],
                        return_exceptions=True
                    )

                    # Add to Miro board
                    miro_tasks = []
                    for idx, result in enumerate(upload_results):
                        if isinstance(result, tuple) and result[0]:
                            s3_url, img_data = result

                            col = idx % cols_per_row
                            row = idx // cols_per_row

                            x = start_x + 250 + (col * (img_width + img_gap))
                            y = current_y + (row * row_height)

                            # Add action label
                            label_y = y + 90
                            self.miro_client.miro_shape(x, label_y, img_width, 30,
                                                       img_data['action_label'], "#f0f0f0")

                            miro_task = self.miro_client.miro_image_async(session, x, y, s3_url, img_width)
                            miro_tasks.append(miro_task)

                    # Process Miro batch
                    if miro_tasks:
                        for i in range(0, len(miro_tasks), self.batch_size):
                            batch = miro_tasks[i:i + self.batch_size]
                            await asyncio.gather(*batch, return_exceptions=True)
                            if i + self.batch_size < len(miro_tasks):
                                await asyncio.sleep(self.delay_between_batches)

                    # Calculate next Y position based on rows used
                    rows_used = (len(images) + cols_per_row - 1) // cols_per_row
                    current_y += (rows_used * row_height) + 100

                    print(f"  ✅ Completed angle group: {angle_label}")

            print(f"\n✅ By-angle layout completed!")
            return True

        except Exception as e:
            print(f"❌ Error in by-angle layout: {e}")
            return False

    async def _upload_by_action_layout(self, organized_data: List[Dict], board_id: str) -> bool:
        """Upload images organized by action"""
        try:
            print(f"\n📐 Using BY_ACTION layout")

            # Group by action
            action_groups = {}
            for img_data in organized_data:
                action_key = img_data['action_label']
                if action_key not in action_groups:
                    action_groups[action_key] = []
                action_groups[action_key].append(img_data)

            print(f"📊 Found {len(action_groups)} action groups")

            # Use same layout logic as by_angle but with actions
            start_x = 100
            start_y = 100
            img_width = 150
            img_gap = 20
            row_height = 250
            cols_per_row = 6
            current_y = start_y

            # Create header
            header_text = f"Images by Action\nTotal: {len(organized_data)} images in {len(action_groups)} groups\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.miro_client.miro_shape(start_x, current_y - 80, 800, 60, header_text, "#e6f3ff")

            async with aiohttp.ClientSession() as session:
                for action_idx, (action_label, images) in enumerate(sorted(action_groups.items()), 1):
                    print(f"\n📝 Processing action group {action_idx}/{len(action_groups)}: {action_label} ({len(images)} images)")

                    # Add action header
                    self.miro_client.miro_shape(start_x, current_y, 200, 60, f"Action: {action_label}", "#ffe6f0")

                    # Upload images
                    upload_tasks = []
                    for img_data in images:
                        s3_key = f"miro_boards/{board_id}/{os.path.basename(img_data['image_path'])}"
                        task = self.miro_client.upload_image_to_s3_async(img_data['image_path'], s3_key)
                        upload_tasks.append((task, img_data))

                    semaphore = asyncio.Semaphore(self.max_concurrent_uploads)

                    async def limited_upload(task, img_data):
                        async with semaphore:
                            result = await task
                            if result:
                                self.stats['uploaded_images'] += 1
                            else:
                                self.stats['failed_images'] += 1
                            return (result, img_data)

                    upload_results = await asyncio.gather(
                        *[limited_upload(task, img_data) for task, img_data in upload_tasks],
                        return_exceptions=True
                    )

                    # Add to Miro
                    miro_tasks = []
                    for idx, result in enumerate(upload_results):
                        if isinstance(result, tuple) and result[0]:
                            s3_url, img_data = result

                            col = idx % cols_per_row
                            row = idx // cols_per_row

                            x = start_x + 250 + (col * (img_width + img_gap))
                            y = current_y + (row * row_height)

                            # Add angle label
                            label_y = y + 90
                            self.miro_client.miro_shape(x, label_y, img_width, 30,
                                                       img_data['angle_label'], "#f0f0f0")

                            miro_task = self.miro_client.miro_image_async(session, x, y, s3_url, img_width)
                            miro_tasks.append(miro_task)

                    if miro_tasks:
                        for i in range(0, len(miro_tasks), self.batch_size):
                            batch = miro_tasks[i:i + self.batch_size]
                            await asyncio.gather(*batch, return_exceptions=True)
                            if i + self.batch_size < len(miro_tasks):
                                await asyncio.sleep(self.delay_between_batches)

                    rows_used = (len(images) + cols_per_row - 1) // cols_per_row
                    current_y += (rows_used * row_height) + 100

                    print(f"  ✅ Completed action group: {action_label}")

            print(f"\n✅ By-action layout completed!")
            return True

        except Exception as e:
            print(f"❌ Error in by-action layout: {e}")
            return False

    async def batch_process_csvs(self,
                                 csv_directory: str,
                                 image_directory: str,
                                 layout: str = "grid",
                                 csv_pattern: str = "*.csv") -> Dict[str, bool]:
        """
        Process multiple CSV files in a directory

        Args:
            csv_directory: Directory containing CSV files
            image_directory: Directory containing images
            layout: Layout type for all boards
            csv_pattern: Pattern to match CSV files (default: "*.csv")

        Returns:
            Dictionary with CSV filename as key and success status as value
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 BATCH PROCESSING MODE")
            print(f"{'='*60}")
            print(f"📁 CSV Directory: {csv_directory}")
            print(f"🖼️ Image Directory: {image_directory}")
            print(f"📐 Layout: {layout}")
            print(f"{'='*60}")

            import glob
            csv_files = glob.glob(os.path.join(csv_directory, csv_pattern))

            if not csv_files:
                print(f"❌ No CSV files found matching pattern: {csv_pattern}")
                return {}

            print(f"📄 Found {len(csv_files)} CSV files to process")

            results = {}
            successful = 0
            failed = 0

            for csv_idx, csv_path in enumerate(sorted(csv_files), 1):
                csv_name = os.path.basename(csv_path)
                print(f"\n{'='*60}")
                print(f"📄 Processing CSV {csv_idx}/{len(csv_files)}: {csv_name}")
                print(f"{'='*60}")

                success = await self.create_board_from_csv(csv_path, image_directory, layout=layout)
                results[csv_name] = success

                if success:
                    successful += 1
                    print(f"✅ Successfully processed: {csv_name}")
                else:
                    failed += 1
                    print(f"❌ Failed to process: {csv_name}")

                # Delay between CSVs
                if csv_idx < len(csv_files):
                    print(f"\n⏳ Waiting 2 seconds before next CSV...")
                    await asyncio.sleep(2)

            # Final summary
            print(f"\n{'='*60}")
            print(f"🏁 BATCH PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"📊 Total CSVs processed: {len(csv_files)}")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"📈 Success rate: {(successful/len(csv_files)*100):.1f}%")
            print(f"{'='*60}")

            return results

        except Exception as e:
            print(f"❌ Error in batch processing: {e}")
            return {}

    def _display_stats(self):
        """Display upload statistics"""
        print(f"\n{'='*60}")
        print(f"📊 UPLOAD STATISTICS")
        print(f"{'='*60}")
        print(f"Total images: {self.stats['total_images']}")
        print(f"✅ Uploaded: {self.stats['uploaded_images']}")
        print(f"❌ Failed: {self.stats['failed_images']}")

        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            print(f"⏱️ Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

            if self.stats['uploaded_images'] > 0:
                avg_time = duration / self.stats['uploaded_images']
                print(f"📈 Average time per image: {avg_time:.2f} seconds")

        success_rate = (self.stats['uploaded_images'] / self.stats['total_images'] * 100) if self.stats['total_images'] > 0 else 0
        print(f"📊 Success rate: {success_rate:.1f}%")
        print(f"{'='*60}")


async def main():
    """Example usage"""

    # Load configuration from environment
    MIRO_TOKEN = os.getenv("MIRO_TOKEN")
    AWS_CONFIG = {
        'region_name': os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
        'aws_access_key_id': os.getenv("AWS_ACCESS_KEY_ID"),
        'aws_secret_access_key': os.getenv("AWS_SECRET_ACCESS_KEY")
    }
    S3_BUCKET = os.getenv("S3_BUCKET", "genvas-saas-stage")

    # Validate configuration
    if not MIRO_TOKEN or not AWS_CONFIG.get('aws_access_key_id') or not AWS_CONFIG.get('aws_secret_access_key'):
        print("❌ Missing required environment variables!")
        print("📝 Please set these in your .env file:")
        print("   MIRO_TOKEN=your_miro_token")
        print("   AWS_ACCESS_KEY_ID=your_aws_key")
        print("   AWS_SECRET_ACCESS_KEY=your_aws_secret")
        print("   S3_BUCKET=your_s3_bucket")
        print("   AWS_DEFAULT_REGION=ap-northeast-2")
        return

    # Initialize uploader with safety settings
    uploader = MiroCSVUploader(
        miro_token=MIRO_TOKEN,
        aws_config=AWS_CONFIG,
        s3_bucket=S3_BUCKET,
        batch_size=20,  # Process 20 images at a time
        max_concurrent_uploads=10,  # Max 10 concurrent S3 uploads
        delay_between_batches=0.5  # 0.5 second delay between batches
    )

    # Example 1: Single CSV with grid layout
    csv_path = "resources/csvs/nsfw_tags.csv"
    image_directory = "resources/nsfw_data"

    print("🎨 Example 1: Single CSV Upload (Grid Layout)")
    await uploader.create_board_from_csv(
        csv_path=csv_path,
        image_directory=image_directory,
        layout="grid"
    )

    # Example 2: Single CSV with by-angle layout
    # print("\n🎨 Example 2: Single CSV Upload (By-Angle Layout)")
    # await uploader.create_board_from_csv(
    #     csv_path=csv_path,
    #     image_directory=image_directory,
    #     layout="by_angle"
    # )

    # Example 3: Batch process all CSVs in a directory
    # csv_directory = "resources/csvs"
    # print("\n🎨 Example 3: Batch Process Multiple CSVs")
    # results = await uploader.batch_process_csvs(
    #     csv_directory=csv_directory,
    #     image_directory=image_directory,
    #     layout="grid"
    # )


if __name__ == "__main__":
    asyncio.run(main())
