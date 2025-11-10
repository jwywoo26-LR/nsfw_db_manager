"""
Configuration and constants for the NSFW Asset Manager frontend
"""
import os

# Backend API URL - Use 127.0.0.1 instead of localhost for Gradio compatibility
API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")

# Dropdown Options for Upload/Search
ANGLE_1_OPTIONS = ["", "above", "below"]
ANGLE_2_OPTIONS = ["", "front", "back", "side"]

# Action options (currently empty, can be customized)
ACTION_1_OPTIONS = []
ACTION_2_OPTIONS = []
ACTION_3_OPTIONS = []
