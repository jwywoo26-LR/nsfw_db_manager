"""
Asset Details Tab - View detailed information about a specific asset by ID
"""
import gradio as gr
import requests
from .config import API_URL


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
- S3 Key: {asset.get('s3_key', 'N/A')}
- S3 URL: {asset.get('s3_url', 'N/A')}
"""
            return details
        else:
            return f"❌ Failed to get asset details: {response.text}"

    except Exception as e:
        return f"❌ Error: {str(e)}"


def create_asset_details_tab():
    """
    Create and return the Asset Details tab UI
    """
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
