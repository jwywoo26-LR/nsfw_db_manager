"""
Upload Tab - Single image upload with metadata
"""
import gradio as gr
import requests
import tempfile
from typing import Tuple
from pathlib import Path
from .config import API_URL, ANGLE_1_OPTIONS, ANGLE_2_OPTIONS


def upload_image(
    file,
    angle_1: str,
    angle_2: str,
    action_1: str,
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
        if prompt:
            params['prompt'] = prompt

        # Send request to backend
        response = requests.post(f"{API_URL}/api/upload", files=files, params=params)

        if response.status_code == 200:
            result = response.json()
            asset_id = result['asset']['id']

            # Download the uploaded image to display it
            try:
                download_url = f"{API_URL}/api/download/{asset_id}"
                img_response = requests.get(download_url, timeout=10)

                if img_response.status_code == 200:
                    # Save to temp file
                    filename = result['asset'].get('original_filename', f'asset_{asset_id}.png')
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
                    temp_file.write(img_response.content)
                    temp_file.close()

                    return f"✅ Upload successful! Asset ID: {asset_id}", temp_file.name
            except Exception as e:
                return f"✅ Upload successful! Asset ID: {asset_id} (Preview failed: {e})", None

            return f"✅ Upload successful! Asset ID: {asset_id}", None
        else:
            return f"❌ Upload failed: {response.text}", None

    except Exception as e:
        return f"❌ Error: {str(e)}", None


def create_upload_tab():
    """
    Create and return the Upload tab UI
    """
    with gr.Tab("📤 Upload"):
        gr.Markdown("""
        # 📤 Upload Image
        Upload a single image with metadata tags. All fields marked as **Required** must be filled.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 📁 Select Image")
                    upload_file = gr.File(
                        label="Image File",
                        file_types=["image"],
                        file_count="single"
                    )

                with gr.Group():
                    gr.Markdown("### 📐 Metadata")

                    # All metadata fields in ONE horizontal row
                    with gr.Row():
                        upload_angle_1 = gr.Dropdown(
                            choices=ANGLE_1_OPTIONS,
                            label="🔼 Angle 1 (Optional)",
                            value="",
                            allow_custom_value=True,
                            info="above, below, or empty"
                        )
                        upload_angle_2 = gr.Dropdown(
                            choices=ANGLE_2_OPTIONS,
                            label="↔️ Angle 2 (Required)",
                            value="",
                            allow_custom_value=True,
                            info="front, back, or side"
                        )
                        # Action 1 is required
                        upload_action_1 = gr.Textbox(
                            label="🎬 Action 1 (Required)",
                            placeholder="Enter action description",
                            value="",
                            info="Main action in the image"
                        )

                    upload_prompt = gr.Textbox(
                        label="💬 Prompt (Required)",
                        placeholder="Enter a detailed description or prompt",
                        value="",
                        lines=3,
                        info="Describe the image content"
                    )

                upload_btn = gr.Button("📤 Upload Image", variant="primary", size="lg")
                upload_output = gr.Textbox(label="Status", interactive=False, show_label=False)

            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 🖼️ Preview")
                    upload_preview = gr.Image(
                        label="Image Preview",
                        interactive=False,
                        show_label=False,
                        show_download_button=True
                    )

        # Auto-update preview when file is selected
        def preview_file(file):
            if file:
                return file.name if hasattr(file, 'name') else file
            return None

        upload_file.change(fn=preview_file, inputs=upload_file, outputs=upload_preview)

        # Upload and show the uploaded image in preview
        upload_btn.click(
            fn=upload_image,
            inputs=[upload_file, upload_angle_1, upload_angle_2, upload_action_1, upload_prompt],
            outputs=[upload_output, upload_preview]
        )
