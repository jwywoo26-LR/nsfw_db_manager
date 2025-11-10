"""
NSFW Image Asset Manager - Gradio Frontend
Main application file that imports modular tabs
"""
import gradio as gr
import requests
from src.config import API_URL
from src.upload_tab import create_upload_tab
from src.search_tab import create_search_tab
from src.bulk_upload_tab import create_bulk_upload_tab
from src.asset_details_tab import create_asset_details_tab


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


# Create Gradio app
with gr.Blocks(title="NSFW Asset Manager", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🖼️ NSFW Image Asset Manager")
    gr.Markdown("Manage and search your NSFW image assets with metadata tagging")

    # Backend status indicator
    with gr.Row():
        status_text = gr.Textbox(
            value=check_backend_status(),
            label="Backend Status",
            interactive=False,
            scale=4
        )
        refresh_btn = gr.Button("🔄 Refresh Status", scale=1)
        refresh_btn.click(fn=check_backend_status, outputs=status_text)

    # Create all tabs
    with gr.Tabs():
        create_upload_tab()
        create_search_tab()
        create_bulk_upload_tab()
        create_asset_details_tab()

    gr.Markdown("""
    ---
    **Instructions:**
    1. Make sure the backend server is running (`python backend/run_server.py`)
    2. Use the Upload tab to add new images with metadata
    3. Use the Search tab to find images by their tags (click images to view details)
    4. Use the Bulk Upload tab to process zip files with CSV data
    5. View detailed information in the Asset Details tab
    """)


if __name__ == "__main__":
    import sys
    import os

    # Print startup information
    print("=" * 60)
    print("🚀 Starting NSFW Image Asset Manager Frontend")
    print("=" * 60)
    print(f"🔗 Backend API: {API_URL}")
    print(f"📖 Opening browser...")

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
