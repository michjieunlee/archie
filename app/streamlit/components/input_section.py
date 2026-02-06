"""
Input section component for the Streamlit app.
Provides a chat-style interface for user input.
"""
import streamlit as st
from utils.validators import validate_github_url, validate_github_token


def render_input_section():
    """
    Render the chat-style input section.
    """
    st.title("Archie - AI Knowledge Base Assistant")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "status" in message:
                st.caption(message["status"])
    
    # Chat input with inline token field
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.chat_input(
            "Enter GitHub repository URL (e.g., https://github.com/owner/repo)",
            disabled=st.session_state.processing
        )
    
    with col2:
        # Token input in a compact format
        st.markdown("<div style='margin-top: 8px;'>", unsafe_allow_html=True)
        github_token = st.text_input(
            "Token",
            type="password",
            key="github_token",
            label_visibility="collapsed",
            placeholder="🔑 Token",
            disabled=st.session_state.processing,
            help="Enter your GitHub personal access token"
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Process user input
    if user_input and not st.session_state.processing:
        # Validate GitHub URL
        is_valid_url, url_message = validate_github_url(user_input)
        
        if not is_valid_url:
            # Add error message to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ **Invalid Input**\n\n{url_message}\n\nPlease provide a full GitHub repository URL in the format: `https://github.com/owner/repo`"
            })
            st.rerun()
            return
        
        # Validate token
        is_valid_token, token_message = validate_github_token(github_token)
        
        if not is_valid_token:
            # Add error message to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ **Invalid Token**\n\n{token_message}\n\nPlease provide a valid GitHub personal access token in the format: `ghp_...` or `github_pat_...`"
            })
            st.rerun()
            return
        
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user",
            "content": f"Process repository: `{user_input}`"
        })
        
        # Store validated inputs in session state
        st.session_state.github_url = user_input
        st.session_state.validated_token = github_token
        st.session_state.processing = True
        
        # Add assistant acknowledgment
        st.session_state.messages.append({
            "role": "assistant",
            "content": "✅ **Starting Processing**\n\nI'll analyze this repository and extract knowledge base information.",
            "status": "⏳ Initializing..."
        })
        
        st.rerun()


def get_validated_inputs():
    """
    Get validated inputs from session state.
    
    Returns:
        tuple: (github_url, github_token) or (None, None) if not available
    """
    if st.session_state.processing and "github_url" in st.session_state:
        return (
            st.session_state.github_url,
            st.session_state.validated_token
        )
    return None, None