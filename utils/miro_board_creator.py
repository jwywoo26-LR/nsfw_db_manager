import requests
import boto3
import os
import time
import asyncio
import aiohttp
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class MiroBoardCreator:
    def __init__(self, miro_token: str, aws_config: dict, s3_bucket: str, s3_prefix: str = "miro_boards/"):
        """
        Initialize Miro board creator with S3 upload capability
        
        Args:
            miro_token: Miro API token
            aws_config: AWS configuration dict with region, access key, secret key
            s3_bucket: S3 bucket name for uploading images
            s3_prefix: S3 prefix for organizing uploaded images
        """
        self.miro_token = miro_token
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.board_id = None
        
        self.headers = {
            "Authorization": f"Bearer {miro_token}",
            "Content-Type": "application/json",
        }
        
        # Initialize S3 client
        self.s3 = boto3.client("s3", **aws_config)
        
        # Layout configuration
        self.THUMB_WIDTH = 120
        self.THUMB_HEIGHT = 120
        self.THUMB_GAP = 15
        self.IMG_STEP = self.THUMB_WIDTH + self.THUMB_GAP
        self.TEXT_HEIGHT = 80  # Increased for Korean text
        self.MODEL_LABEL_HEIGHT = 30
        self.ROW_GAP = 60  # Increased spacing between rows
    
    async def upload_image_to_s3_async(self, local_image_path: str, s3_key: str) -> Optional[str]:
        """
        Upload local image to S3 asynchronously and return public URL

        Args:
            local_image_path: Path to local image file
            s3_key: S3 key for the uploaded image

        Returns:
            Public S3 URL or None if upload failed
        """
        try:
            if not os.path.exists(local_image_path):
                print(f"❌ Local image not found: {local_image_path}")
                return None

            # Run S3 upload in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await loop.run_in_executor(
                    executor,
                    lambda: self.s3.upload_file(
                        local_image_path,
                        self.s3_bucket,
                        s3_key,
                        ExtraArgs={'ContentType': 'image/png'}
                    )
                )

            # Generate presigned URL (valid for 24 hours)
            public_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )
            print(f"✅ Uploaded to S3: {public_url}")
            return public_url

        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None

    def upload_image_to_s3(self, local_image_path: str, s3_key: str) -> Optional[str]:
        """
        Upload local image to S3 and return public URL
        
        Args:
            local_image_path: Path to local image file
            s3_key: S3 key for the uploaded image
            
        Returns:
            Public S3 URL or None if upload failed
        """
        try:
            if not os.path.exists(local_image_path):
                print(f"❌ Local image not found: {local_image_path}")
                return None
                
            # Upload to S3 without ACL
            self.s3.upload_file(
                local_image_path, 
                self.s3_bucket, 
                s3_key,
                ExtraArgs={'ContentType': 'image/png'}
            )
            
            # Generate presigned URL (valid for 24 hours)
            public_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )
            print(f"✅ Uploaded to S3: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None
    
    def create_miro_board(self, board_name: str, description: str = "") -> bool:
        """
        Create a new Miro board
        
        Args:
            board_name: Name of the board
            description: Board description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            team_id = "3458764629693515876"  # Using the same team ID from the original code
            
            board_payload = {
                "name": board_name,
                "description": description,
                "teamId": team_id,
                "policy": {
                    "sharingPolicy": {
                        "access": "private",
                        "teamAccess": "edit"  
                    }
                }
            }
            
            response = requests.post(
                "https://api.miro.com/v2/boards",
                headers=self.headers,
                json=board_payload
            )
            
            if response.status_code == 201:
                board_data = response.json()
                self.board_id = board_data["id"]
                board_url = f"https://miro.com/app/board/{self.board_id}/"
                print(f"✅ Miro board created: {board_name}")
                print(f"🔗 Board URL: {board_url}")
                return True
            else:
                print(f"❌ Miro board creation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Miro board creation exception: {e}")
            return False
    
    async def _miro_post_async(self, session: aiohttp.ClientSession, endpoint: str, data: dict) -> bool:
        """Make an async POST request to Miro API"""
        url = f"https://api.miro.com/v2/boards/{self.board_id}/{endpoint}"
        try:
            async with session.post(url, headers=self.headers, json=data) as response:
                success = response.status == 201
                if not success:
                    text = await response.text()
                    print(f"❌ Miro API error ({endpoint}): {response.status} - {text}")
                return success
        except Exception as e:
            print(f"❌ Miro API exception ({endpoint}): {e}")
            return False

    def _miro_post(self, endpoint: str, data: dict) -> bool:
        """Make a POST request to Miro API"""
        url = f"https://api.miro.com/v2/boards/{self.board_id}/{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data)
            success = response.status_code == 201
            if not success:
                print(f"❌ Miro API error ({endpoint}): {response.status_code} - {response.text}")
            return success
        except Exception as e:
            print(f"❌ Miro API exception ({endpoint}): {e}")
            return False
    
    def miro_shape(self, x: float, y: float, w: float, h: float, text: str, fill: Optional[str] = None) -> bool:
        """Create a text shape on Miro board"""
        content = str(text).replace('\n', '\\n')
        
        data = {
            "data": {"shape": "rectangle", "content": content},
            "position": {"x": x, "y": y},
            "geometry": {"width": w, "height": h},
        }
        
        if fill:
            data["style"] = {
                "fillColor": fill, 
                "borderColor": "#000000", 
                "borderWidth": 1,
                "textAlign": "center", 
                "textAlignVertical": "middle", 
                "fontSize": 12,
                "fontFamily": "Arial"
            }
        
        return self._miro_post("shapes", data)
    
    async def miro_shape_async(self, session: aiohttp.ClientSession, x: float, y: float, w: float, h: float, text: str, fill: Optional[str] = None) -> bool:
        """Create a text shape on Miro board asynchronously"""
        content = str(text).replace('\n', '\\n')

        data = {
            "data": {"shape": "rectangle", "content": content},
            "position": {"x": x, "y": y},
            "geometry": {"width": w, "height": h},
        }

        if fill:
            data["style"] = {
                "fillColor": fill,
                "borderColor": "#000000",
                "borderWidth": 1,
                "textAlign": "center",
                "textAlignVertical": "middle",
                "fontSize": 12,
                "fontFamily": "Arial"
            }

        return await self._miro_post_async(session, "shapes", data)

    async def miro_image_async(self, session: aiohttp.ClientSession, x: float, y: float, url: str, w: float = 120) -> bool:
        """Add an image to Miro board asynchronously"""
        data = {
            "data": {"url": url},
            "position": {"x": x, "y": y},
            "geometry": {"width": w}
        }
        return await self._miro_post_async(session, "images", data)

    def miro_image(self, x: float, y: float, url: str, w: float = 120) -> bool:
        """Add an image to Miro board"""
        data = {
            "data": {"url": url},
            "position": {"x": x, "y": y},
            "geometry": {"width": w}
        }
        return self._miro_post("images", data)
    
    async def create_tag_visualization_board_async(self, tag_data: List[Dict], board_title: str) -> bool:
        """
        Create a Miro board showing generated images organized by tags and models (async version)

        Args:
            tag_data: List of dictionaries containing:
                - eng_tag: English tag name
                - kor_tag: Korean tag name
                - models: Dict with model names as keys and list of image paths as values
            board_title: Title for the board

        Returns:
            True if successful, False otherwise
        """
        if not self.create_miro_board(board_title):
            return False

        print(f"📋 Creating tag visualization board with {len(tag_data)} tags (async mode)")

        # Starting positions
        start_x = 100
        start_y = 100
        current_y = start_y

        # Create header
        header_text = f"Generated Images by Tag and Model\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.miro_shape(start_x, current_y - 50, 800, 80, header_text, "#e6f3ff")

        # Create aiohttp session for async requests
        async with aiohttp.ClientSession() as session:
            # Process each tag with async upload and Miro operations
            for tag_index, tag_info in enumerate(tag_data, 1):
                eng_tag = tag_info.get('eng_tag', '')
                kor_tag = tag_info.get('kor_tag', '')
                models = tag_info.get('models', {})

                # Calculate total images for this tag
                total_images_in_tag = sum(len(images) for images in models.values())
                estimated_time = (total_images_in_tag * 1) + 2  # Faster with async

                print(f"\n📝 Processing tag {tag_index}/{len(tag_data)}: {eng_tag} ({kor_tag})")
                print(f"⏱️  Estimated time for this row: ~{estimated_time} seconds ({total_images_in_tag} images) [ASYNC]")

                row_start_time = time.time()

                # Tag header with both English and Korean
                tag_header = f"{eng_tag} ({kor_tag})"
                tag_y = current_y
                self.miro_shape(start_x, tag_y, 200, 80, tag_header, "#fff2cc")

                # Calculate positions for this row (accounting for 5x4 grid)
                model_label_y = current_y + 90
                images_y = current_y + 130
                current_x = start_x + 250
                max_row_height = 600  # Increased height for 4 rows of images (4 * 130 + extra spacing)

                # Async upload all images for this row to S3
                upload_tasks = []
                model_positions = {}  # {model_name: (start_x, start_y)}

                for model_index, (model_name, image_paths) in enumerate(models.items()):
                    if not image_paths:
                        continue

                    print(f"  📤 Uploading {len(image_paths)} images for model: {model_name} [ASYNC]")

                    # Calculate model grid position (4 models per row: hyun, sua, exwife, lene)
                    model_start_x = current_x + (model_index * 700)  # 700px spacing between models
                    model_start_y = images_y
                    model_positions[model_name] = (model_start_x, model_start_y)

                    for i, image_path in enumerate(image_paths):
                        if os.path.exists(image_path):
                            # Create S3 key
                            filename = f"{eng_tag}_{model_name}_{i+1:02d}.png"
                            s3_key = f"{self.s3_prefix}{filename}"

                            # Calculate 5x4 grid position within this model's space
                            grid_col = i % 5  # 5 columns (0-4)
                            grid_row = i // 5  # 4 rows (0-3)

                            image_x = model_start_x + (grid_col * 130)  # 130px spacing between images
                            image_y = model_start_y + (grid_row * 130)  # 130px spacing between rows

                            # Create async upload task
                            upload_task = self.upload_image_to_s3_async(image_path, s3_key)
                            upload_tasks.append((upload_task, model_name, i, image_x, image_y, filename))

                # Execute all uploads concurrently
                if upload_tasks:
                    print(f"  🚀 Executing {len(upload_tasks)} concurrent uploads...")

                    upload_results = await asyncio.gather(
                        *[task[0] for task in upload_tasks],
                        return_exceptions=True
                    )

                    # Collect successful uploads and their positions
                    miro_image_tasks = []
                    model_labels_added = set()

                    for (_, model_name, i, image_x, image_y, filename), result in zip(upload_tasks, upload_results):
                        if isinstance(result, str) and result:  # Successful upload
                            s3_url = result
                            print(f"    ✅ Uploaded: {filename}")

                            # Add model label if not added yet (position above the 5x4 grid)
                            if model_name not in model_labels_added:
                                model_start_x, model_start_y = model_positions[model_name]
                                # Position label above the grid center
                                label_x = model_start_x + (5 * 130) // 2 - 60  # Center of 5 columns
                                label_y = model_start_y - 50  # Above the grid
                                self.miro_shape(label_x, label_y, 120, 30, model_name, "#f0f0f0")
                                model_labels_added.add(model_name)

                            # Create async Miro image task
                            miro_task = self.miro_image_async(session, image_x, image_y, s3_url, 120)
                            miro_image_tasks.append(miro_task)
                        else:
                            print(f"    ❌ Failed to upload: {filename}")

                    # Execute all Miro image additions concurrently (with rate limiting)
                    if miro_image_tasks:
                        print(f"  🎨 Adding {len(miro_image_tasks)} images to Miro board [ASYNC with rate limiting]...")

                        # Process in smaller batches to avoid overwhelming Miro API
                        batch_size = 20  # Process 20 images at a time
                        all_results = []

                        for i in range(0, len(miro_image_tasks), batch_size):
                            batch = miro_image_tasks[i:i + batch_size]
                            print(f"    📤 Processing Miro batch {i//batch_size + 1}/{(len(miro_image_tasks) + batch_size - 1)//batch_size} ({len(batch)} images)")

                            batch_results = await asyncio.gather(*batch, return_exceptions=True)
                            all_results.extend(batch_results)

                            # Add delay between batches to be nice to Miro API
                            if i + batch_size < len(miro_image_tasks):
                                print(f"    ⏱️ Waiting 0.5 seconds before next Miro batch...")
                                await asyncio.sleep(0.5)

                        successful_miro = sum(1 for result in all_results if result is True)
                        print(f"  ✅ Added {successful_miro}/{len(miro_image_tasks)} images to Miro board")

                    # Calculate and display actual time taken
                    row_end_time = time.time()
                    actual_time = row_end_time - row_start_time
                    print(f"  🚀 Row {tag_index} completed in {actual_time:.1f} seconds (estimated: {estimated_time}s) [ASYNC SPEEDUP!]")
                else:
                    print(f"  ❌ No images to upload for tag: {eng_tag}")

                # Move to next row
                current_y += max_row_height + self.ROW_GAP

                # Shorter delay between tag rows for faster processing
                print(f"  ⏳ Waiting 1 second before processing next tag...")
                await asyncio.sleep(1)

        print(f"🚀 Async tag visualization board created successfully!")
        return True

    def create_tag_visualization_board(self, tag_data: List[Dict], board_title: str) -> bool:
        """
        Create a Miro board showing generated images organized by tags and models
        
        Args:
            tag_data: List of dictionaries containing:
                - eng_tag: English tag name
                - kor_tag: Korean tag name  
                - models: Dict with model names as keys and list of image paths as values
            board_title: Title for the board
            
        Returns:
            True if successful, False otherwise
        """
        if not self.create_miro_board(board_title):
            return False
            
        print(f"📋 Creating tag visualization board with {len(tag_data)} tags")
        
        # Starting positions
        start_x = 100
        start_y = 100
        current_y = start_y
        
        # Create header
        header_text = f"Generated Images by Tag and Model\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.miro_shape(start_x, current_y - 50, 800, 80, header_text, "#e6f3ff")
        
        # Process each tag with time estimation
        for tag_index, tag_info in enumerate(tag_data, 1):
            eng_tag = tag_info.get('eng_tag', '')
            kor_tag = tag_info.get('kor_tag', '')
            models = tag_info.get('models', {})
            
            # Calculate total images for this tag
            total_images_in_tag = sum(len(images) for images in models.values())
            estimated_time = (total_images_in_tag * 2) + 5  # ~2 seconds per image upload + 5 seconds overhead
            
            print(f"\n📝 Processing tag {tag_index}/{len(tag_data)}: {eng_tag} ({kor_tag})")
            print(f"⏱️  Estimated time for this row: ~{estimated_time} seconds ({total_images_in_tag} images)")
            
            row_start_time = time.time()
            
            # Tag header with both English and Korean (positioned at top of row)
            tag_header = f"{eng_tag} ({kor_tag})"
            tag_y = current_y
            self.miro_shape(start_x, tag_y, 200, 80, tag_header, "#fff2cc")
            
            # Calculate positions for this row with proven spacing
            model_label_y = current_y + 90  # Model labels 90px below tag header (no overlap)
            images_y = current_y + 130      # Images 40px below model labels
            
            # Current position for model/images in this row - start after tag header 
            current_x = start_x + 250  # Start after tag header
            max_row_height = 200  # Total height for this row (tag + models + images + spacing)
            
            # First, upload all images for this row to S3
            row_uploaded_images = {}  # {model_name: [(s3_url, position_x), ...]}
            
            for model_name, image_paths in models.items():
                if not image_paths:  # Skip if no images for this model
                    continue
                    
                print(f"  📤 Uploading {len(image_paths)} images for model: {model_name}")
                
                uploaded_model_images = []
                model_x = current_x
                
                for i, image_path in enumerate(image_paths):
                    if os.path.exists(image_path):
                        # Create S3 key
                        filename = f"{eng_tag}_{model_name}_{i+1:02d}.png"
                        s3_key = f"{self.s3_prefix}{filename}"
                        
                        # Upload to S3
                        s3_url = self.upload_image_to_s3(image_path, s3_key)
                        if s3_url:
                            # Calculate image position: horizontal spread for variations
                            image_x = model_x + (i * 125)  # 125px spacing between image variations
                            uploaded_model_images.append((s3_url, image_x))
                            print(f"    ✅ Uploaded: {filename}")
                        else:
                            print(f"    ❌ Failed to upload: {image_path}")
                    else:
                        print(f"    ❌ Image not found: {image_path}")
                
                # Move to next model position (after all variations of current model)
                if uploaded_model_images:
                    # Space for all variations + gap between models
                    model_x += (len(image_paths) * 125) + 30
                
                if uploaded_model_images:
                    row_uploaded_images[model_name] = uploaded_model_images
                
                current_x = model_x + 30  # Gap between models
            
            # Now add all uploaded images for this row to Miro board
            if row_uploaded_images:
                print(f"  🎨 Adding row to Miro board...")
                
                # Add model labels and images with proper vertical positioning
                for model_name, model_images in row_uploaded_images.items():
                    if model_images:
                        # Model name label positioned above first image of the model
                        first_image_x = model_images[0][1]
                        self.miro_shape(first_image_x, model_label_y, 120, 30, model_name, "#f0f0f0")
                        
                        # Add all images for this model at calculated image position
                        for s3_url, image_x in model_images:
                            self.miro_image(image_x, images_y, s3_url, 120)
                
                # Calculate and display actual time taken
                row_end_time = time.time()
                actual_time = row_end_time - row_start_time
                print(f"  ✅ Row {tag_index} completed in {actual_time:.1f} seconds (estimated: {estimated_time}s)")
            else:
                print(f"  ❌ No images uploaded for tag: {eng_tag}")
            
            # Move to next row with proper spacing
            current_y += max_row_height + self.ROW_GAP
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        print(f"✅ Tag visualization board created successfully!")
        return True
    
    def organize_generated_images(self, csv_data: List[Dict], generated_images_dir: str) -> List[Dict]:
        """
        Organize generated images by tag and model for board creation

        Args:
            csv_data: List of CSV row data with eng_tag, kor_tag
            generated_images_dir: Directory containing generated images

        Returns:
            List of organized tag data for board creation
        """
        models = ["hyun", "sua", "exwife", "lene"]  # From your image generator
        organized_data = []

        for row_index, row in enumerate(csv_data):
            # Handle BOM character in column names
            eng_tag = row.get('eng_tag', '') or row.get('\ufeffeng_tag', '')
            eng_tag = eng_tag.strip()
            kor_tag = row.get('kor_tag', '').strip()

            if not eng_tag:
                continue

            tag_models = {}

            # Find images for each model (now supporting up to 20 variations per model)
            for model in models:
                model_images = []
                for variation in range(1, 21):  # 20 variations per model (1-20)
                    # Use new filename format with row index: row_tag_variation_short_model.png
                    short_tag = eng_tag[:6] if len(eng_tag) > 6 else eng_tag
                    filename = f"r{row_index:02d}_{short_tag}_{variation:02d}_{model[:3]}.png"
                    image_path = os.path.join(generated_images_dir, filename)

                    if os.path.exists(image_path):
                        model_images.append(image_path)

                if model_images:
                    tag_models[model] = model_images

            if tag_models:  # Only add if we found images
                organized_data.append({
                    'eng_tag': eng_tag,
                    'kor_tag': kor_tag,
                    'models': tag_models
                })

        return organized_data


def main():
    """Example usage"""
    
    # Configuration
    MIRO_TOKEN = os.getenv("MIRO_TOKEN", "your_miro_token_here")
    AWS_CONFIG = {
        'region_name': 'ap-northeast-2',
        'aws_access_key_id': os.getenv("AWS_ACCESS_KEY_ID"),
        'aws_secret_access_key': os.getenv("AWS_SECRET_ACCESS_KEY")
    }
    S3_BUCKET = os.getenv("S3_BUCKET", "your-s3-bucket")
    
    # Initialize client
    miro_client = MiroBoardCreator(MIRO_TOKEN, AWS_CONFIG, S3_BUCKET)
    
    # Example data structure
    example_tag_data = [
        {
            'eng_tag': 'male focus',
            'kor_tag': '남성에 초점',
            'models': {
                'hyun': ['path/to/male_focus_01_hyun.png', 'path/to/male_focus_02_hyun.png'],
                'sua': ['path/to/male_focus_01_sua.png', 'path/to/male_focus_02_sua.png'],
            }
        }
    ]
    
    # Create board
    board_title = f"Generated Images - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    success = miro_client.create_tag_visualization_board(example_tag_data, board_title)
    
    if success:
        print("🎉 Miro board created successfully!")
    else:
        print("❌ Failed to create Miro board")


if __name__ == "__main__":
    main()