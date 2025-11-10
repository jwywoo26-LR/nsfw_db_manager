#!/usr/bin/env python3
"""
Gradio Frontend for NSFW Image Asset Manager
Simple UI for searching, uploading, and managing image assets
"""

import gradio as gr
import requests
from pathlib import Path
from typing import List, Tuple, Optional
import os
import zipfile
import tempfile
import shutil
import pandas as pd

# Backend API URL - Use 127.0.0.1 instead of localhost for Gradio compatibility
API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")

# Dropdown Options
ANGLE_1_OPTIONS = ["above", "below"]
ANGLE_2_OPTIONS = ["front", "behind", "side"]

# TODO: Add your action options here
# Example: ACTION_1_OPTIONS = ["standing", "sitting", "lying", "walking"]
ACTION_1_OPTIONS = []  # Add your action options
ACTION_2_OPTIONS = []  # Add your action options
ACTION_3_OPTIONS = []  # Add your action options


def upload_image(
    file,
    angle_1: str,
    angle_2: str,
    action_1: str,
    action_2: str,
    action_3: str,
    prompt: str
) -> Tuple[str, str]:
    """
    Upload an image with metadata to the backend
    Returns (status_message, uploaded_image_url)
    """
    try:
        if file is None:
            return "❌ Please select an image file", None

        # Validation: angle_2, action_1, and prompt are required
        if not angle_2 or not angle_2.strip():
            return "❌ Angle 2 is required", None
        if not action_1 or not action_1.strip():
            return "❌ Action 1 is required", None
        if not prompt or not prompt.strip():
            return "❌ Prompt is required", None

        # Prepare the file and query parameters
        files = {'file': open(file, 'rb')}
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

        # Send request to backend
        response = requests.post(f"{API_URL}/api/upload", files=files, params=params)

        if response.status_code == 200:
            result = response.json()
            asset_id = result['asset']['id']

            # Download the uploaded image to display it
            try:
                import tempfile
                download_url = f"{API_URL}/api/download/{asset_id}"
                img_response = requests.get(download_url, timeout=10)

                if img_response.status_code == 200:
                    # Save to temp file
                    filename = result['asset'].get('original_filename', f'asset_{asset_id}.png')
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
                    temp_file.write(img_response.content)
                    temp_file.close()
                    return f"✅ Successfully uploaded! Asset ID: {asset_id}", temp_file.name
                else:
                    return f"✅ Uploaded (Asset ID: {asset_id}) but couldn't display image", None
            except Exception as e:
                return f"✅ Uploaded (Asset ID: {asset_id}) but display error: {e}", None
        else:
            return f"❌ Upload failed: {response.text}", None

    except Exception as e:
        return f"❌ Error: {str(e)}", None


def search_images(
    angle_1: str,
    angle_2: str,
    action_1: str,
    prompt: str,
    limit: int
) -> Tuple[List[str], str]:
    """
    Search for images based on metadata filters
    Returns (list of image paths, status message)
    """
    try:
        # Build query parameters
        params = {}
        if angle_1:
            params['angle_1'] = angle_1
        if angle_2:
            params['angle_2'] = angle_2
        if action_1:
            params['action_1'] = action_1
        if prompt:
            params['prompt'] = prompt
        params['limit'] = limit

        # Send search request
        response = requests.get(f"{API_URL}/api/search", params=params)

        if response.status_code == 200:
            result = response.json()
            total = result['total']
            assets = result['results']

            if not assets:
                return [], f"No images found matching the criteria"

            # Download images from backend and return local paths
            image_paths = []
            import tempfile

            for asset in assets:
                asset_id = asset['id']

                try:
                    # Download image from backend
                    download_url = f"{API_URL}/api/download/{asset_id}"
                    img_response = requests.get(download_url, timeout=10)

                    if img_response.status_code == 200:
                        # Save to temp file
                        filename = asset.get('original_filename', f'asset_{asset_id}.png')
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
                        temp_file.write(img_response.content)
                        temp_file.close()
                        image_paths.append(temp_file.name)
                    else:
                        print(f"Failed to download asset {asset_id}")
                except Exception as e:
                    print(f"Error downloading asset {asset_id}: {e}")

            if not image_paths:
                return [], f"Found {total} images but couldn't download them."

            status = f"✅ Found {total} images"
            return image_paths, status
        else:
            return [], f"❌ Search failed: {response.text}"

    except Exception as e:
        return [], f"❌ Error: {str(e)}"


def get_asset_details(asset_id: int) -> str:
    """
    Get detailed information about a specific asset
    """
    try:
        response = requests.get(f"{API_URL}/api/assets/{asset_id}")

        if response.status_code == 200:
            asset = response.json()
            details = f"""
**Asset ID:** {asset['id']}
**Filename:** {asset.get('original_filename', 'N/A')}
**Created:** {asset.get('created_at', 'N/A')}

**Metadata:**
- Angle 1: {asset.get('angle_1', 'N/A')}
- Angle 2: {asset.get('angle_2', 'N/A')}
- Action 1: {asset.get('action_1', 'N/A')}
- Action 2: {asset.get('action_2', 'N/A')}
- Action 3: {asset.get('action_3', 'N/A')}
- Prompt: {asset.get('prompt', 'N/A')}

**Storage:**
- Local Path: {asset.get('local_file_path', 'N/A')}
- S3 URL: {asset.get('s3_url', 'N/A')}
"""
            return details
        else:
            return f"❌ Failed to get asset details: {response.text}"

    except Exception as e:
        return f"❌ Error: {str(e)}"


def check_backend_status() -> str:
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=2)
        if response.status_code == 200:
            return "✅ Backend is running"
        else:
            return "❌ Backend returned error"
    except:
        return f"❌ Cannot connect to backend at {API_URL}"


def get_available_actions() -> List[str]:
    """Fetch available action_1 values from database"""
    try:
        response = requests.get(f"{API_URL}/api/metadata/actions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [""] + data.get("actions", [])  # Add empty option for "all"
        else:
            return [""]
    except Exception as e:
        print(f"Failed to fetch actions: {e}")
        return [""]


def process_bulk_upload(zip_file) -> Tuple[str, str]:
    """
    Process a zip file containing CSV and images for bulk upload

    Expected zip structure:
        archive.zip
        ├── data.csv
        └── resources/
            └── nsfw_data/
                └── images...

    CSV Format:
        reference_image_name,reference_image_path,angle_direction_1,angle_direction_2,action_direction_1,prompt

    Returns (status_message, detailed_log)
    """
    if zip_file is None:
        return "❌ Please select a zip file", ""

    temp_dir = None
    try:
        # Create temporary directory for extraction
        temp_dir = tempfile.mkdtemp()

        log = []
        log.append(f"📦 Extracting zip file...")

        # Extract zip file
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        log.append(f"✓ Extracted to temporary directory\n")

        # Find CSV file
        csv_files = list(Path(temp_dir).rglob("*.csv"))
        if not csv_files:
            return "❌ No CSV file found in zip archive", "\n".join(log)

        csv_path = csv_files[0]
        log.append(f"📄 Found CSV file: {csv_path.name}\n")

        # Read CSV
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        log.append(f"📊 Found {total_rows} rows in CSV")
        log.append(f"📂 CSV location: {csv_path.parent}\n")

        # List extracted structure for debugging
        log.append("📁 Extracted structure:")
        file_count = 0
        dir_structure = set()
        for item in Path(temp_dir).rglob("*"):
            rel_path = item.relative_to(temp_dir)
            if item.is_dir():
                dir_structure.add(str(rel_path))
            elif item.is_file():
                file_count += 1
                if file_count <= 10:  # Show first 10 files as examples
                    log.append(f"  FILE: {rel_path}")

        log.append(f"\n  Total files found: {file_count}")
        log.append("\n  Directories found:")
        for d in sorted(dir_structure):
            log.append(f"    DIR: {d}")

        # Check if resources/nsfw_data exists
        expected_dir = Path(temp_dir) / "resources" / "nsfw_data"
        log.append(f"\n  Expected directory exists? {expected_dir.exists()}")
        if expected_dir.exists():
            image_count = len(list(expected_dir.glob("*.png"))) + len(list(expected_dir.glob("*.jpg")))
            log.append(f"  Images in resources/nsfw_data: {image_count}")

        log.append("")
        log.append("=" * 60)

        successful = 0
        failed = 0

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
                prompt = row.get('prompt', None) if 'prompt' in row else None

                # Handle empty strings as None
                action_1 = action_1 if pd.notna(action_1) and str(action_1).strip() else None
                action_2 = action_2 if pd.notna(action_2) and str(action_2).strip() else None
                action_3 = action_3 if pd.notna(action_3) and str(action_3).strip() else None
                prompt = prompt if pd.notna(prompt) and str(prompt).strip() else None

                # Resolve image path
                # Handle different path formats
                csv_dir = csv_path.parent

                # If path starts with ../, strip it and look from extracted root
                if image_path.startswith('../'):
                    # Remove leading ../
                    clean_path = image_path.replace('../', '', 1)
                    # Look from temp_dir root instead of csv_dir
                    resolved_path = (Path(temp_dir) / clean_path).resolve()
                else:
                    # Standard relative path from CSV location
                    resolved_path = (csv_dir / image_path).resolve()

                # If file not found at exact path, search recursively in subdirectories
                if not resolved_path.exists():
                    filename = Path(image_path).name
                    # Search in resources/nsfw_data and all subdirectories
                    search_dir = Path(temp_dir) / "resources" / "nsfw_data"
                    if search_dir.exists():
                        matches = list(search_dir.rglob(filename))
                        if matches:
                            resolved_path = matches[0]  # Use first match

                log.append(f"\n[{idx+1}/{total_rows}] {reference_name}")
                log.append(f"  CSV path: {image_path}")
                log.append(f"  Resolved to: {resolved_path}")
                log.append(f"  Angles: {angle_1}, {angle_2}")
                log.append(f"  Actions: {action_1 or 'N/A'}, {action_2 or 'N/A'}, {action_3 or 'N/A'}")
                log.append(f"  Prompt: {prompt or 'N/A'}")

                # Check if image exists
                if not resolved_path.exists():
                    log.append(f"  ✗ Image not found!")
                    failed += 1
                    continue

                # Upload to backend
                with open(resolved_path, 'rb') as f:
                    files = {'file': (resolved_path.name, f, 'image/png')}
                    params = {
                        'angle_1': angle_1,
                        'angle_2': angle_2,
                    }

                    if action_1:
                        params['action_1'] = action_1
                    if action_2:
                        params['action_2'] = action_2
                    if action_3:
                        params['action_3'] = action_3
                    if prompt:
                        params['prompt'] = prompt

                    response = requests.post(
                        f"{API_URL}/api/upload",
                        files=files,
                        params=params,
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        asset_id = result['asset']['id']
                        log.append(f"  ✓ Success! Asset ID: {asset_id}")
                        successful += 1
                    else:
                        log.append(f"  ✗ Upload failed: {response.text}")
                        failed += 1

            except Exception as e:
                log.append(f"  ✗ Error: {str(e)}")
                failed += 1

        # Summary
        log.append("\n" + "=" * 60)
        log.append("UPLOAD SUMMARY")
        log.append("=" * 60)
        log.append(f"Total images: {total_rows}")
        log.append(f"Successful: {successful}")
        log.append(f"Failed: {failed}")
        log.append("=" * 60)

        summary = f"✅ Completed! {successful}/{total_rows} images uploaded successfully"
        if failed > 0:
            summary = f"⚠️ Completed with errors. {successful}/{total_rows} uploaded, {failed} failed"

        return summary, "\n".join(log)

    except Exception as e:
        return f"❌ Error processing zip file: {str(e)}", "\n".join(log) if 'log' in locals() else str(e)

    finally:
        # Clean up temporary directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


# Create Gradio Interface
with gr.Blocks(title="NSFW Image Asset Manager", theme=gr.themes.Soft()) as app:
    # Header with title and backend status side by side
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("# 🖼️ NSFW Image Asset Manager")
            gr.Markdown("Upload, search, and manage NSFW image assets with metadata tagging")
        with gr.Column(scale=1):
            status_output = gr.Textbox(label="Backend Status", interactive=False, value="Not checked yet")
            status_btn = gr.Button("🔍 Check Backend Status", size="sm")

    status_btn.click(fn=check_backend_status, outputs=status_output)

    with gr.Tabs():
        # Tab 1: Upload Images
        with gr.Tab("📤 Upload"):
            gr.Markdown("### Upload Image with Metadata")

            with gr.Row():
                with gr.Column(scale=1):
                    upload_file = gr.File(label="Image File", file_types=["image"])

                    # All metadata fields in ONE horizontal row
                    with gr.Row():
                        upload_angle_1 = gr.Dropdown(
                            choices=ANGLE_1_OPTIONS,
                            label="Angle 1 (Optional)",
                            allow_custom_value=True
                        )
                        upload_angle_2 = gr.Dropdown(
                            choices=ANGLE_2_OPTIONS,
                            label="Angle 2 (Required)",
                            allow_custom_value=True
                        )
                        # TODO: Replace with Dropdown when ACTION options are defined
                        # upload_action_1 = gr.Dropdown(choices=ACTION_1_OPTIONS, label="Action 1", allow_custom_value=True)
                        upload_action_1 = gr.Textbox(label="Action 1 (Required)", placeholder="Required")
                        upload_action_2 = gr.Textbox(label="Action 2 (Optional)", placeholder="Optional")
                        upload_action_3 = gr.Textbox(label="Action 3 (Optional)", placeholder="Optional")

                    upload_prompt = gr.Textbox(label="Prompt (Required)", placeholder="Required description or generation prompt", lines=2)

                    upload_btn = gr.Button("📤 Upload Image", variant="primary")
                    upload_output = gr.Textbox(label="Upload Status", interactive=False)

                with gr.Column(scale=1):
                    upload_preview = gr.Image(label="Preview / Uploaded Image", interactive=False)

            # Auto-update preview when file is selected
            def preview_file(file):
                if file is not None:
                    return file.name if hasattr(file, 'name') else file
                return None

            upload_file.change(fn=preview_file, inputs=upload_file, outputs=upload_preview)

            # Upload and show the uploaded image in preview
            upload_btn.click(
                fn=upload_image,
                inputs=[upload_file, upload_angle_1, upload_angle_2, upload_action_1, upload_action_2, upload_action_3, upload_prompt],
                outputs=[upload_output, upload_preview]
            )

        # Tab 2: Search Images
        with gr.Tab("🔍 Search"):
            gr.Markdown("### Search Images by Metadata")

            # All search filters in ONE horizontal row
            with gr.Row():
                search_angle_1 = gr.Dropdown(
                    choices=[""] + ANGLE_1_OPTIONS,
                    label="Angle 1 (Vertical)",
                    value=""
                )
                search_angle_2 = gr.Dropdown(
                    choices=[""] + ANGLE_2_OPTIONS,
                    label="Angle 2 (Horizontal)",
                    value=""
                )
                # Simple textbox for action_1 (dropdown was too complex)
                search_action_1 = gr.Textbox(
                    label="Action 1",
                    placeholder="Leave empty for all"
                )
                # search_action_2 = gr.Textbox(label="Action 2", placeholder="Leave empty for all")
                # search_action_3 = gr.Textbox(label="Action 3", placeholder="Leave empty for all")

            search_prompt = gr.Textbox(label="Prompt (partial match)", placeholder="Leave empty for all")

            with gr.Row():
                search_limit = gr.Slider(minimum=1, maximum=100, value=20, step=1, label="Max Results")

            search_btn = gr.Button("🔍 Search", variant="primary")
            search_status = gr.Textbox(label="Search Status", interactive=False)
            search_gallery = gr.Gallery(label="Results", columns=5, height="auto")

            search_btn.click(
                fn=search_images,
                inputs=[search_angle_1, search_angle_2, search_action_1, search_prompt, search_limit],
                outputs=[search_gallery, search_status]
            )

        # Tab 3: Bulk Upload
        with gr.Tab("📦 Bulk Upload"):
            gr.Markdown("### Bulk Upload Images from Zip File")
            gr.Markdown("""
            Upload a zip file containing:
            - **CSV file** with columns: `reference_image_name`, `reference_image_path`, `angle_direction_1`, `angle_direction_2`, `action_direction_1`, `prompt` (optional)
            - **resources/** folder with images referenced in the CSV

            Example CSV row:
            ```
            testright_02_v1,../resources/nsfw_data/test right_02.png,above,front,test,a woman in standing position
            ```
            """)

            bulk_upload_file = gr.File(label="Zip File", file_types=[".zip"])
            bulk_upload_btn = gr.Button("📦 Process Bulk Upload", variant="primary", size="lg")
            bulk_upload_status = gr.Textbox(label="Upload Status", interactive=False)
            bulk_upload_log = gr.Textbox(label="Detailed Log", interactive=False, lines=20, max_lines=30)

            bulk_upload_btn.click(
                fn=process_bulk_upload,
                inputs=bulk_upload_file,
                outputs=[bulk_upload_status, bulk_upload_log]
            )

        # Tab 4: Asset Details
        with gr.Tab("📋 Asset Details"):
            gr.Markdown("### Get Asset Information by ID")

            asset_id_input = gr.Number(label="Asset ID", precision=0)
            details_btn = gr.Button("📋 Get Details", variant="primary")
            details_output = gr.Markdown(label="Asset Details")

            details_btn.click(
                fn=get_asset_details,
                inputs=asset_id_input,
                outputs=details_output
            )

    gr.Markdown("""
    ---
    **Instructions:**
    1. Make sure the backend server is running (`python backend/run_server.py`)
    2. Use the Upload tab to add new images with metadata
    3. Use the Search tab to find images by their tags
    4. View detailed information in the Asset Details tab
    """)


if __name__ == "__main__":
    print("🚀 Starting Gradio Frontend...")
    print(f"🔗 Backend API: {API_URL}")
    print(f"📖 Opening browser...")

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
