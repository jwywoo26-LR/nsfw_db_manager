#!/usr/bin/env python3
"""
Miro Group Board Creator - Create and manage Miro boards for grouped image uploads
Organized by directories with sections and 5cm gaps between groups
"""

import os
import sys
import asyncio
import aiohttp
import boto3
import concurrent.futures
from pathlib import Path
from typing import Optional, Dict, Tuple
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


class MiroGroupBoard:
    """
    Create and manage Miro boards for directory-grouped image uploads
    """

    def __init__(self, miro_token: str, aws_config: dict, s3_bucket: str, s3_prefix: str = "nsfw_groups/"):
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

        # Layout configuration - 5cm gaps between directories
        self.gap_between_directories = 1890  # 5cm in pixels at 96 DPI
        self.gap_between_images = 200
        self.images_per_row = 5
        self.section_header_height = 100

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
            team_id = "3458764629693515876"

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

            import requests
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

    def get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        """
        Get actual dimensions of an image file

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            print(f"⚠️ Could not read image dimensions for {image_path}: {e}")
            # Return default dimensions
            return (400, 600)

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

            # Generate presigned URL (valid for 7 days)
            public_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )
            return public_url

        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None

    async def create_section_header(self, session: aiohttp.ClientSession, text: str, x: float, y: float, width: float) -> bool:
        """
        Create a section header shape on Miro board

        Args:
            session: aiohttp session
            text: Header text
            x: X coordinate
            y: Y coordinate
            width: Width of header

        Returns:
            True if successful
        """
        url = f"https://api.miro.com/v2/boards/{self.board_id}/shapes"
        payload = {
            "data": {
                "content": f"<p><strong>{text}</strong></p>",
                "shape": "rectangle"
            },
            "style": {
                "fillColor": "#e6f7ff",
                "color": "#1a1a1a"
            },
            "position": {
                "x": x,
                "y": y
            },
            "geometry": {
                "width": width,
                "height": self.section_header_height
            }
        }

        try:
            async with session.post(url, headers=self.headers, json=payload) as response:
                return response.status in [200, 201]
        except Exception as e:
            print(f"❌ Error creating section header: {e}")
            return False

    async def add_image_to_board(self, session: aiohttp.ClientSession, image_url: str, x: float, y: float, title: str = "") -> bool:
        """
        Add an image to the Miro board from URL

        Args:
            session: aiohttp session
            image_url: URL of the image
            x: X coordinate
            y: Y coordinate
            title: Image title

        Returns:
            True if successful
        """
        url = f"https://api.miro.com/v2/boards/{self.board_id}/images"
        payload = {
            "data": {
                "url": image_url,
                "title": title
            },
            "position": {
                "x": x,
                "y": y
            },
            "geometry": {
                "width": self.image_width
            }
        }

        try:
            async with session.post(url, headers=self.headers, json=payload) as response:
                return response.status in [200, 201]
        except Exception as e:
            return False
