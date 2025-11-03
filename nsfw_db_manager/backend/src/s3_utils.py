"""
S3 utility functions for uploading and managing image assets
"""

import os
import boto3
from pathlib import Path
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class S3Manager:
    """
    Manager for S3 operations
    """

    def __init__(self):
        """Initialize S3 client with AWS credentials from environment"""
        self.s3_client = boto3.client(
            's3',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.bucket_name = os.getenv('S3_BUCKET', 'genvas-saas-stage')
        self.s3_prefix = os.getenv('S3_PREFIX', 'nsfw_assets/')

    def upload_image(self, file_path: str, custom_key: Optional[str] = None) -> Optional[str]:
        """
        Upload an image file to S3 and return the public URL

        Args:
            file_path: Path to the local image file
            custom_key: Custom S3 key (optional, auto-generated if not provided)

        Returns:
            S3 URL of the uploaded image or None if failed
        """
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return None

            # Generate S3 key
            if custom_key:
                s3_key = f"{self.s3_prefix}{custom_key}"
            else:
                filename = Path(file_path).name
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                s3_key = f"{self.s3_prefix}{timestamp}_{filename}"

            # Determine content type
            content_type = self._get_content_type(file_path)

            # Upload to S3
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            # Generate presigned URL (valid for 7 days)
            s3_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )

            print(f"✅ Uploaded to S3: {s3_key}")
            return s3_url

        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None

    def upload_file_bytes(self, file_bytes: bytes, filename: str, custom_key: Optional[str] = None) -> Optional[str]:
        """
        Upload file bytes to S3 and return the public URL

        Args:
            file_bytes: File content as bytes
            filename: Original filename
            custom_key: Custom S3 key (optional, auto-generated if not provided)

        Returns:
            S3 URL of the uploaded image or None if failed
        """
        try:
            # Generate S3 key
            if custom_key:
                s3_key = f"{self.s3_prefix}{custom_key}"
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                s3_key = f"{self.s3_prefix}{timestamp}_{filename}"

            # Determine content type
            content_type = self._get_content_type_from_filename(filename)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type
            )

            # Generate presigned URL (valid for 7 days)
            s3_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )

            print(f"✅ Uploaded to S3: {s3_key}")
            return s3_url

        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
            return None

    def delete_file(self, s3_url: str) -> bool:
        """
        Delete a file from S3 using its URL

        Args:
            s3_url: S3 URL of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract S3 key from URL
            s3_key = self._extract_s3_key_from_url(s3_url)
            if not s3_key:
                print(f"❌ Invalid S3 URL: {s3_url}")
                return False

            # Delete from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            print(f"✅ Deleted from S3: {s3_key}")
            return True

        except Exception as e:
            print(f"❌ S3 deletion failed: {e}")
            return False

    def _get_content_type(self, file_path: str) -> str:
        """Get content type based on file extension"""
        extension = Path(file_path).suffix.lower()
        return self._get_content_type_from_extension(extension)

    def _get_content_type_from_filename(self, filename: str) -> str:
        """Get content type based on filename"""
        extension = Path(filename).suffix.lower()
        return self._get_content_type_from_extension(extension)

    def _get_content_type_from_extension(self, extension: str) -> str:
        """Map file extension to content type"""
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        return content_types.get(extension, 'application/octet-stream')

    def _extract_s3_key_from_url(self, s3_url: str) -> Optional[str]:
        """Extract S3 key from presigned URL"""
        try:
            # Parse URL to extract key
            # Presigned URLs have format: https://bucket.s3.region.amazonaws.com/key?params
            if self.bucket_name in s3_url:
                parts = s3_url.split(self.bucket_name)
                if len(parts) > 1:
                    key_part = parts[1].split('?')[0]
                    return key_part.lstrip('/')
            return None
        except Exception as e:
            print(f"❌ Error extracting S3 key: {e}")
            return None
