"""
Configuration settings for the Streamlit application.
"""

# Page configuration for Streamlit
PAGE_CONFIG = {
    "page_title": "Archie - AI Knowledge Base Assistant",
    "page_icon": "🤖",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# API Configuration
API_BASE_URL = "http://localhost:8001"  # Backend API URL
API_TIMEOUT = 180  # seconds (3 minutes)

# File Upload Settings
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
MAX_FILES_COUNT = 3  # Maximum number of files per upload
