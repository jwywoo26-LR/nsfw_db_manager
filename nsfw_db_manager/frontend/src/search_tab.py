"""
Search Tab - Search images by metadata with enhanced detail view on click
"""
import gradio as gr
import requests
import tempfile
from typing import Tuple, List, Optional
from pathlib import Path
from .config import API_URL, ANGLE_1_OPTIONS, ANGLE_2_OPTIONS


# Global cache to store asset metadata for clicked images
_search_results_cache = {}


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
    global _search_results_cache
    _search_results_cache.clear()  # Clear previous results

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

                        # Cache the asset metadata with the temp file path as key
                        _search_results_cache[temp_file.name] = asset

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


def on_image_select(evt: gr.SelectData) -> Tuple[Optional[str], str]:
    """
    Handler for when an image is clicked in the gallery
    Shows detailed metadata for the selected image

    Args:
        evt: Gradio SelectData event containing index of selected image

    Returns:
        Tuple of (image_path, metadata_markdown)
    """
    global _search_results_cache

    try:
        # Get the image path from the event
        # evt.value contains the image path or dict with image info
        # evt.index is the index in the gallery

        # Try different ways to extract the path
        image_path = None
        if isinstance(evt.value, str):
            image_path = evt.value
        elif isinstance(evt.value, dict):
            # Try different dict structures
            image_path = evt.value.get('image', {}).get('path') if isinstance(evt.value.get('image'), dict) else evt.value.get('image')
            if not image_path:
                image_path = evt.value.get('path')

        if not image_path:
            # Debug info
            return None, f"❌ Could not retrieve image path. Event value type: {type(evt.value)}, Value: {str(evt.value)[:100]}"

        # Look up the asset metadata from cache
        if image_path not in _search_results_cache:
            # Show available keys for debugging
            cache_keys = list(_search_results_cache.keys())[:3]
            return image_path, f"⚠️ Metadata not found in cache.\nLooking for: {image_path}\nCache has {len(_search_results_cache)} entries.\nSample keys: {cache_keys}"

        asset = _search_results_cache[image_path]

        # Format the metadata as beautiful markdown with emojis and better styling
        angle_1 = asset.get('angle_1') or '—'
        angle_2 = asset.get('angle_2') or '—'
        action_1 = asset.get('action_1') or '—'
        action_2 = asset.get('action_2') or '—'
        action_3 = asset.get('action_3') or '—'
        prompt = asset.get('prompt') or 'No prompt provided'

        metadata_md = f"""
# 🖼️ Asset #{asset.get('id', 'N/A')}

---

### 📄 File Information
- **Filename:** `{asset.get('original_filename', 'N/A')}`
- **Created:** {asset.get('created_at', 'N/A')}

---

### 📐 Angles & Actions

<table style="width:100%; border-collapse: collapse;">
<tr style="background-color: #f0f0f0;">
    <td style="padding: 8px; font-weight: bold; width: 30%;">🔼 Angle 1 (Vertical)</td>
    <td style="padding: 8px;">{angle_1}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold; background-color: #f0f0f0;">↔️ Angle 2 (Horizontal)</td>
    <td style="padding: 8px;">{angle_2}</td>
</tr>
<tr style="background-color: #f0f0f0;">
    <td style="padding: 8px; font-weight: bold;">🎬 Action 1</td>
    <td style="padding: 8px; font-weight: bold; color: #0066cc;">{action_1}</td>
</tr>
<tr>
    <td style="padding: 8px; font-weight: bold; background-color: #f0f0f0;">🎬 Action 2</td>
    <td style="padding: 8px;">{action_2}</td>
</tr>
<tr style="background-color: #f0f0f0;">
    <td style="padding: 8px; font-weight: bold;">🎬 Action 3</td>
    <td style="padding: 8px;">{action_3}</td>
</tr>
</table>

---

### 💬 Prompt

<div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #0066cc; font-family: monospace;">
{prompt}
</div>

---

### 💾 Storage
- **Local:** `{asset.get('local_file_path', 'N/A')}`
- **S3 Key:** `{asset.get('s3_key', 'N/A') if asset.get('s3_key') else '—'}`
"""

        return image_path, metadata_md

    except Exception as e:
        return None, f"❌ Error retrieving details: {str(e)}"


def create_search_tab():
    """
    Create and return the Search tab UI with enhanced detail view
    """
    with gr.Tab("🔍 Search"):
        gr.Markdown("""
        # 🔍 Search Images
        Find images by filtering with angles, actions, and prompts. Click any result to view full details!
        """)

        # Search filters section at the top
        with gr.Group():
            gr.Markdown("### 🎯 Search Filters")

            # All search filters in ONE horizontal row
            with gr.Row():
                search_angle_1 = gr.Dropdown(
                    choices=[""] + ANGLE_1_OPTIONS,
                    label="🔼 Angle 1 (Vertical)",
                    value="",
                    info="Optional: above, below"
                )
                search_angle_2 = gr.Dropdown(
                    choices=[""] + ANGLE_2_OPTIONS,
                    label="↔️ Angle 2 (Horizontal)",
                    value="",
                    info="Optional: front, back, side"
                )
                # Simple textbox for action_1
                search_action_1 = gr.Textbox(
                    label="🎬 Action 1",
                    placeholder="Leave empty for all",
                    info="Partial match supported"
                )

            search_prompt = gr.Textbox(
                label="💬 Prompt",
                placeholder="Leave empty to search all prompts",
                info="Partial match - searches within prompts"
            )

            with gr.Row():
                search_limit = gr.Slider(
                    minimum=1,
                    maximum=100,
                    value=20,
                    step=1,
                    label="📊 Max Results",
                    info="Number of images to return"
                )
                search_btn = gr.Button("🔍 Search", variant="primary", size="lg", scale=0)

        search_status = gr.Textbox(label="Status", interactive=False, show_label=False)

        gr.Markdown("---")

        # Results and Details side-by-side
        with gr.Row():
            # Left column: Search Results Gallery (fixed narrow width)
            with gr.Column(scale=20, min_width=250):
                with gr.Group():
                    gr.Markdown("### 🖼️ Results")
                    search_gallery = gr.Gallery(
                        label="Click any image to view details",
                        columns=1,
                        rows=8,
                        height=800,
                        object_fit="scale-down",
                        show_label=False,
                        preview=False
                    )

            # Right column: Selected Image Details (takes remaining space)
            with gr.Column(scale=80):
                with gr.Group():
                    gr.Markdown("### 📋 Selected Image Details")
                    detail_image = gr.Image(
                        label="🖼️ Preview",
                        interactive=False,
                        show_download_button=True,
                        height=350
                    )
                    detail_metadata = gr.Markdown(
                        value="""
<div style="text-align: center; padding: 40px; color: #666;">
    <p style="font-size: 16px;">👈 Click an image on the left to view its details</p>
    <p style="font-size: 12px; margin-top: 10px;">ID • Angles • Actions • Prompt • Storage Info</p>
</div>
                        """
                    )

        # Search button handler
        search_btn.click(
            fn=search_images,
            inputs=[search_angle_1, search_angle_2, search_action_1, search_prompt, search_limit],
            outputs=[search_gallery, search_status]
        )

        # Gallery click handler - shows details when image is selected
        search_gallery.select(
            fn=on_image_select,
            outputs=[detail_image, detail_metadata]
        )
