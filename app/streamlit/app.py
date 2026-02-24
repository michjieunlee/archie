"""
Main Streamlit application for Archie.
Provides a centered chat interface with integration buttons on the left.
"""

import base64
import logging
import os

import streamlit as st
from components.chat_section import render_chat_section
from components.integration_panel import render_integration_panel, render_integration_buttons
from config.settings import PAGE_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """
    Main application entry point.
    """
    # Configure the page
    st.set_page_config(**PAGE_CONFIG)

    # Apply custom CSS
    st.markdown(
        """
        <style>
        /* Hide Streamlit default elements but keep sidebar toggle */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stDecoration"] {display: none;}
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
        /* Hide toolbar content but keep layout so >> button stays visible */
        [data-testid="stToolbar"] {
            visibility: hidden;
        }
        [data-testid="stExpandSidebarButton"] {
            visibility: visible !important;
        }

        /* Main container adjustments */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0;
            max-width: 100%;
            overflow: hidden;
            height: 100vh;
            box-sizing: border-box;
        }

        /* Header styling */
        .app-header {
            text-align: center;
            margin-bottom: 1rem;
        }

        .app-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            color: #1f1f1f;
        }

        .app-subtitle {
            font-size: 1.2rem;
            color: #666;
            font-weight: 400;
        }

        /* Chat message styling */
        .stChatMessage {
            padding: 1rem;
        }

        /* Ensure main content area takes full width when sidebar is collapsed */
        [data-testid="stMain"] {
            transition: margin-left 0.3s ease;
        }

        /* ===== Sidebar: remove ALL top space ===== */
        [data-testid="stSidebar"] {
            padding-top: 0 !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0 !important;
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 0 !important;
            gap: 0.5rem !important;
        }

        /* Remove the extra decorative top bar in sidebar */
        [data-testid="stSidebar"] [data-testid="stDecoration"] {
            display: none !important;
        }

        /* Kill any top margin/padding on the first sidebar child */
        [data-testid="stSidebar"] .stMarkdown:first-child {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem !important;
        }

        /* File badge shown above input when files are attached */
        .file-badge {
            display: inline-block;
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 16px;
            padding: 0.2rem 0.8rem;
            margin-right: 0.5rem;
            font-size: 0.85rem;
        }

        /* Dark mode text input styling - only when dark mode is active */
        @media (prefers-color-scheme: dark) {
            textarea[aria-label="Message"] {
                background-color: #0E1117 !important;
                color: #FFFFFF !important;
                border: 1px solid #4A4A4A !important;
            }

            textarea[aria-label="Message"]::placeholder {
                color: #888888 !important;
            }

            /* Attach files button styling */
            button[key="attach_btn"] p,
            button:has(p:contains("ATTACH FILES")) p {
                color: #2D2D2D !important;
            }

            button[key="attach_btn"],
            button:has(p:contains("ATTACH FILES")) {
                background-color: #FDB750 !important;
                border: 1px solid #FDB750 !important;
            }

            button[key="attach_btn"]:hover,
            button:has(p:contains("ATTACH FILES")):hover {
                background-color: #E59E35 !important;
                border: 1px solid #E59E35 !important;
            }

            button[key="attach_btn"]:active,
            button:has(p:contains("ATTACH FILES")):active {
                background-color: #CC8A2B !important;
            }

            .file-badge {
                background: #1e3a5f !important;
                border: 1px solid #2e5a8f !important;
                color: #a0c4e8 !important;
            }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "active_integration" not in st.session_state:
        st.session_state.active_integration = None
    if "github_url" not in st.session_state:
        st.session_state.github_url = ""
    if "github_token" not in st.session_state:
        st.session_state.github_token = ""
    if "github_connected" not in st.session_state:
        st.session_state.github_connected = False
    if "slack_channel_id" not in st.session_state:
        st.session_state.slack_channel_id = ""
    if "slack_connected" not in st.session_state:
        st.session_state.slack_connected = False

    # App header - centered with logo
    # Load logo image and convert to base64
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "img", "logo1.png")
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    
    st.markdown(
        f"""
        <style>
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 0.25rem;
        }}
        .app-logo {{
            width: 60px;
            height: 60px;
            border-radius: 12px;
            object-fit: cover;
        }}
        </style>
        <div class="app-header">
            <div class="header-container">
                <img src="data:image/png;base64,{logo_base64}" class="app-logo" alt="Archie Logo">
                <h1 class="app-title">Archie</h1>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Render integration buttons first, then config panel below
    render_integration_buttons()

    # Render integration panel below buttons if active
    if st.session_state.active_integration:
        render_integration_panel()

    # Render chat section in center (includes sticky input bar via components.html JS)
    render_chat_section()


if __name__ == "__main__":
    main()
