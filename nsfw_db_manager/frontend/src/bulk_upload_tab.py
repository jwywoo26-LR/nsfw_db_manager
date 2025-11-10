"""
Bulk Upload Tab - Process zip files containing CSV and images
"""
import gradio as gr
import requests
import tempfile
import zipfile
import shutil
import pandas as pd
from typing import Tuple
from pathlib import Path
from .config import API_URL


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

        # Final summary
        log.append("\n" + "=" * 60)
        log.append(f"\n📊 Summary:")
        log.append(f"  Total images: {total_rows}")
        log.append(f"  Successful: {successful}")
        log.append(f"  Failed: {failed}")
        log.append(f"  Success rate: {(successful/total_rows*100):.1f}%")

        status = f"✅ Bulk upload completed! {successful}/{total_rows} successful"
        return status, "\n".join(log)

    except Exception as e:
        error_msg = f"❌ Error processing bulk upload: {str(e)}"
        return error_msg, error_msg

    finally:
        # Clean up temporary directory
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


def create_bulk_upload_tab():
    """
    Create and return the Bulk Upload tab UI
    """
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
