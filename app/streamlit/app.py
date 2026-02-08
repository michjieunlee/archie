"""
Main Streamlit application for Archie.
Provides a centered chat interface with integration buttons on the left.
"""
import streamlit as st
from components.chat_section import render_chat_section
from components.integration_panel import render_integration_panel, render_integration_buttons
from services.mock_api import process_github_repository
from config.settings import PAGE_CONFIG


def main():
    """
    Main application entry point.
    """
    # Configure the page
    st.set_page_config(**PAGE_CONFIG)

    # Apply custom CSS
    st.markdown("""
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
            padding-bottom: 12rem;
            max-width: 100%;
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
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
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

    # App header - centered
    st.markdown("""
        <div class="app-header">
            <h1 class="app-title">Archie</h1>
            <p class="app-subtitle">AI Knowledge Base Assistant</p>
        </div>
    """, unsafe_allow_html=True)

    # Render integration buttons first, then config panel below
    render_integration_buttons()

    # Render integration panel below buttons if active
    if st.session_state.active_integration:
        render_integration_panel()

    # Render chat section in center (includes sticky input bar via components.html JS)
    render_chat_section()

    # Handle repository processing if triggered
    if st.session_state.processing and st.session_state.github_url:
        process_repository()


def process_repository():
    """
    Process the GitHub repository in the background.
    """
    github_url = st.session_state.github_url
    github_token = st.session_state.github_token
    
    # Call the processing service
    result = process_github_repository(github_url, github_token)
    
    # Add result to chat
    if result.get("status") == "completed":
        kb_articles = result.get("kb_articles", [])
        prs_analyzed = result.get("prs_analyzed", 0)
        execution_time = result.get("execution_time", 0)
        
        result_message = f"""✅ **Processing Complete!**

**Summary:**
- Analyzed **{prs_analyzed}** pull requests
- Generated **{len(kb_articles)}** knowledge base articles
- Execution time: **{execution_time:.2f}s**

**Generated Articles:**
"""
        for i, article in enumerate(kb_articles, 1):
            result_message += f"\n{i}. {article.get('title', 'Untitled')} ({article.get('category', 'General')})"
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": result_message
        })
    
    elif result.get("status") == "error":
        error_message = result.get("error", "Unknown error")
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ **Error:** {error_message}"
        })
    
    # Reset processing state
    st.session_state.processing = False
    st.rerun()


if __name__ == "__main__":
    main()