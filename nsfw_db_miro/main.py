import os
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))

from utils.grok_api_client import GrokAPIClient


class NSFWDatabaseManager:
    def __init__(self, csv_name: str, parse_mode: str = "tags", images_dir: Optional[str] = None):
        """
        Initialize the NSFW Database Manager.

        Args:
            csv_name: Name of the CSV file (e.g., "nsfw_tags.csv")
            parse_mode: "tags" or "description" - determines CSV column structure
            images_dir: Path to images directory (defaults to "resources/nsfw_data")
        """
        self.csv_path = Path(__file__).parent.parent / "resources" / "csvs" / csv_name

        # Set images directory
        if images_dir:
            self.images_dir = Path(images_dir)
        else:
            self.images_dir = Path(__file__).parent.parent / "resources" / "nsfw_data"

        self.grok_client = GrokAPIClient()
        self.parse_mode = parse_mode

        # Define CSV columns based on parse mode
        if parse_mode == "description":
            self.columns = [
                "reference_image",
                "description"
            ]
        else:
            self.columns = [
                "reference_image_name",
                "reference_image_path",
                "angle_direction_1",
                "angle_direction_2",
                "action_direction_1"
            ]

        # Initialize or load CSV
        self._initialize_csv()

    def _initialize_csv(self):
        """Initialize CSV file if it doesn't exist, or load existing one."""
        if not self.csv_path.exists():
            # Create new CSV with headers
            df = pd.DataFrame(columns=self.columns)
            df.to_csv(self.csv_path, index=False)
            print(f"Created new CSV at: {self.csv_path}")
        else:
            print(f"Loading existing CSV from: {self.csv_path}")

    def _parse_grok_response(self, response: Dict) -> Dict[str, Optional[str]]:
        """
        Parse Grok API response and extract tag information.

        Args:
            response: Raw response from Grok API

        Returns:
            Dictionary with extracted tags
        """
        try:
            # Extract content from response
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]

                print(f"[DEBUG] Raw Grok response content:")
                print(f"{content[:500]}...")  # Show first 500 chars

                # Parse JSON from content
                # Sometimes the response might have markdown code blocks, so clean it
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                print(f"[DEBUG] Cleaned content:")
                print(f"{content[:500]}...")

                tags = json.loads(content)

                print(f"[DEBUG] Parsed tags: {tags}")

                return {
                    "angle_direction_1": tags.get("angle_direction_1"),
                    "angle_direction_2": tags.get("angle_direction_2"),
                    "action_direction_1": tags.get("action_direction_1")
                }
            else:
                print("❌ No valid response from Grok API")
                print(f"[DEBUG] Response structure: {response}")
                return self._empty_tags()

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON from Grok response: {e}")
            print(f"[DEBUG] Content that failed to parse: {content}")
            return self._empty_tags()
        except Exception as e:
            print(f"❌ Error parsing Grok response: {e}")
            print(f"[DEBUG] Full response: {response}")
            return self._empty_tags()

    def _parse_grok_response_description(self, response: Dict) -> Optional[str]:
        """
        Parse description from Grok API response (expects JSON format).

        Args:
            response: Raw response from Grok API

        Returns:
            Extracted description text or None if not found
        """
        try:
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]

                # Parse JSON from content (same cleaning as _parse_grok_response)
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                # Parse JSON and extract description field
                data = json.loads(content)
                description = data.get("description", "")

                return description.strip() if description else None
            else:
                print("No valid response from Grok API")
                return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for description: {e}")
            print(f"Content: {content}")
            return None
        except Exception as e:
            print(f"Error parsing description from Grok response: {e}")
            return None

    def _empty_tags(self) -> Dict[str, None]:
        """Return empty tags dictionary."""
        return {
            "angle_direction_1": None,
            "angle_direction_2": None,
            "action_direction_1": None
        }

    def process_image(self, image_path: str, prompt: str = "Analyze this image.", parse_mode: str = "tags", num_requests: int = 1) -> bool:
        """
        Process a single image: send to Grok API and update CSV.

        Args:
            image_path: Path to the image file
            prompt: Custom prompt for Grok (optional)
            parse_mode: "tags" for JSON tags or "description" for raw text (default: "tags")
            num_requests: Number of requests to send per image (for tags mode, default: 1)

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\nProcessing: {image_path}")

            # Get image filename for reference
            image_name = Path(image_path).name
            image_name_base = Path(image_path).stem  # Name without extension

            # Check if image already exists in CSV
            df = pd.read_csv(self.csv_path)

            # For tags mode with multiple requests, check for _v1, _v2, etc.
            if parse_mode == "tags" and num_requests > 1:
                if "reference_image_path" in df.columns:
                    if image_path in df["reference_image_path"].values:
                        print(f"Image {image_name} already processed. Skipping...")
                        return True
            else:
                if "reference_image" in df.columns:
                    if image_name in df["reference_image"].values:
                        print(f"Image {image_name} already processed. Skipping...")
                        return True

            # Parse response based on mode
            if parse_mode == "description":
                # Send single request for description
                print("Sending to Grok API...")
                response = self.grok_client.evaluate_image(
                    image_path=image_path,
                    prompt=prompt,
                    use_system_prompt=True
                )

                description = self._parse_grok_response_description(response)
                new_row = {
                    "reference_image": image_name,
                    "description": description
                }
                print(f"✓ Parsed description: {description[:100]}..." if description and len(description) > 100 else f"✓ Parsed description: {description}")

                # Append to CSV
                df = pd.read_csv(self.csv_path)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(self.csv_path, index=False)
                print(f"✓ Added to CSV")

            else:
                # Tags mode - send multiple requests if specified
                new_rows = []

                for request_num in range(1, num_requests + 1):
                    print(f"Sending request {request_num}/{num_requests} to Grok API...")
                    response = self.grok_client.evaluate_image(
                        image_path=image_path,
                        prompt=prompt,
                        use_system_prompt=True
                    )

                    tags = self._parse_grok_response(response)

                    # Create reference_image_name with version suffix
                    if num_requests > 1:
                        reference_name = f"{image_name_base}_v{request_num}"
                    else:
                        reference_name = image_name_base

                    new_row = {
                        "reference_image_name": reference_name,
                        "reference_image_path": image_path,
                        **tags
                    }
                    new_rows.append(new_row)
                    print(f"✓ Request {request_num} - Parsed tags: {tags}")

                # Append all rows to CSV
                df = pd.read_csv(self.csv_path)
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                df.to_csv(self.csv_path, index=False)
                print(f"✓ Added {len(new_rows)} row(s) to CSV")

            return True

        except Exception as e:
            print(f"✗ Error processing {image_path}: {e}")
            return False

    def process_all_images(self, prompt: str = "Analyze this image.", limit: Optional[int] = None, parse_mode: str = "tags", num_requests: int = 1):
        """
        Process all images in the nsfw_data directory.

        Args:
            prompt: Custom prompt for Grok (optional)
            limit: Maximum number of images to process (optional)
            parse_mode: "tags" for JSON tags or "description" for raw text (default: "tags")
            num_requests: Number of requests to send per image (for tags mode, default: 1)
        """
        # Get all image files
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
        image_files = []

        for ext in image_extensions:
            image_files.extend(self.images_dir.glob(f"*{ext}"))

        print(f"\nFound {len(image_files)} images in {self.images_dir}")
        print(f"Parse mode: {parse_mode}")
        if parse_mode == "tags" and num_requests > 1:
            print(f"Requests per image: {num_requests}")

        if limit:
            image_files = image_files[:limit]
            print(f"Processing first {limit} images...")

        # Process each image
        success_count = 0
        for idx, image_path in enumerate(image_files, 1):
            print(f"\n[{idx}/{len(image_files)}]")
            if self.process_image(str(image_path), prompt, parse_mode, num_requests):
                success_count += 1

        print(f"\n{'='*50}")
        print(f"Processing complete: {success_count}/{len(image_files)} successful")
        print(f"CSV saved at: {self.csv_path}")

    def get_stats(self):
        """Display statistics about the CSV database."""
        if not self.csv_path.exists():
            print("CSV file doesn't exist yet.")
            return

        df = pd.read_csv(self.csv_path)

        print(f"\n{'='*50}")
        print(f"Database Statistics")
        print(f"{'='*50}")
        print(f"Total images processed: {len(df)}")
        print(f"\nAngle Direction 1 distribution:")
        print(df["angle_direction_1"].value_counts())
        print(f"\nAngle Direction 2 distribution:")
        print(df["angle_direction_2"].value_counts())
        print(f"\nTop Action Direction 1:")
        print(df["action_direction_1"].value_counts().head(10))


def main():
    """Main entry point for the NSFW Database Manager."""

    # ===== CONFIGURATION VARIABLES =====
    # Modify these variables to configure the behavior

    CSV_NAME = "nsfw_data_v3.csv"  # Name of the CSV file to create/update
    IMAGES_DIR = "../resources/nsfw_data"  # Path to images directory (None = use default "resources/nsfw_data")
    LIMIT = None  # Limit number of images to process (None = process all)
    PROMPT = "Analyze this image,."  # Custom prompt for Grok API
    SHOW_STATS = False  # Set to True to show statistics instead of processing
    SINGLE_IMAGE = None  # Path to a single image to process (None = process all)

    # Response parsing mode: "tags" or "description"
    PARSE_MODE = "tags"  # "tags" = parse JSON tags, "description" = parse raw description text

    # Number of requests per image (only for tags mode)
    NUM_REQUESTS = 2  # Send 2 requests per image to get variations (e.g., image_v1, image_v2)

    # ===================================

    # Initialize manager with parse mode and custom images directory
    manager = NSFWDatabaseManager(csv_name=CSV_NAME, parse_mode=PARSE_MODE, images_dir=IMAGES_DIR)

    # Show stats if requested
    if SHOW_STATS:
        manager.get_stats()
        return

    # Process single image if specified
    if SINGLE_IMAGE:
        manager.process_image(SINGLE_IMAGE, PROMPT, parse_mode=PARSE_MODE, num_requests=NUM_REQUESTS)
        return

    # Process all images
    manager.process_all_images(prompt=PROMPT, limit=LIMIT, parse_mode=PARSE_MODE, num_requests=NUM_REQUESTS)


if __name__ == "__main__":
    main()
