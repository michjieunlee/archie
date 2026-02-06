"""
Main Streamlit application for Archie.
Provides a two-column interface: configuration on left, chat on right.
"""
import streamlit as st
from components.config_section import render_config_section
from components.chat_section import render_chat_section
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
        /* Hide Streamlit default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Adjust column spacing */
        [data-testid="column"] {
            padding: 1rem;
        }
        
        /* Config section styling */
        .config-section {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            border: 1px solid #dee2e6;
        }
        
        /* Chat section styling */
        .stChatMessage {
            padding: 1rem;
        }
        
        /* Improve spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "github_url" not in st.session_state:
        st.session_state.github_url = ""
    if "github_token" not in st.session_state:
        st.session_state.github_token = ""
    
    # App title
    st.title("Archie - AI Knowledge Base Assistant")
    
    # Create two-column layout: 1/3 for config, 2/3 for chat
    col_config, col_chat = st.columns([1, 2])
    
    with col_config:
        # Render configuration section on the left
        render_config_section()
    
    with col_chat:
        # Render chat section on the right
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