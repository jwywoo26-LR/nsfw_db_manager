#!/usr/bin/env python3
"""
Run the NSFW Image Asset Manager API server
"""

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting NSFW Image Asset Manager API...")
    print("📖 API Documentation: http://localhost:8001/docs")
    print("🔍 Alternative docs: http://localhost:8001/redoc")
    print("\n" + "="*60 + "\n")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
