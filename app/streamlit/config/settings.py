"""
Configuration settings for the Streamlit application.
"""

# Page configuration for Streamlit
PAGE_CONFIG = {
    "page_title": "Archie - AI Knowledge Base Assistant",
    "page_icon": "🤖",
    "layout": "wide",
    "initial_sidebar_state": "collapsed"
}

# API Configuration (for Phase 2)
API_BASE_URL = "http://localhost:8000"  # Backend API URL
API_TIMEOUT = 30  # seconds

# Mock data settings
MOCK_MODE = True  # Set to False when backend API is ready

# UI Settings
MAX_CHAT_HISTORY = 50  # Maximum number of messages to keep in chat history
PROCESSING_ANIMATION_SPEED = 0.5  # seconds between status updates

# File Upload Settings
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
MAX_FILES_COUNT = 3  # Maximum number of files per upload
