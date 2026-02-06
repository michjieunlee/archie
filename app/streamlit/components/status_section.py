"""
Status section component for the Streamlit app.
Displays processing status in chat-style format.
"""
import streamlit as st
import time


def render_status_section(processing_result):
    """
    Update the chat interface with processing status.
    
    Args:
        processing_result: Result from the processing pipeline
    """
    if not processing_result:
        return
    
    status = processing_result.get("status", "unknown")
    
    # Find the last assistant message and update its status
    if st.session_state.messages:
        last_msg_idx = len(st.session_state.messages) - 1
        if st.session_state.messages[last_msg_idx]["role"] == "assistant":
            if status == "processing":
                current_step = processing_result.get("current_step", "Processing")
                progress = processing_result.get("progress", 0)
                st.session_state.messages[last_msg_idx]["status"] = f"⏳ {current_step}... ({progress}%)"
            
            elif status == "completed":
                st.session_state.messages[last_msg_idx]["status"] = "✅ Processing completed"
                # Processing is done
                st.session_state.processing = False
            
            elif status == "error":
                error_message = processing_result.get("error", "Unknown error occurred")
                st.session_state.messages[last_msg_idx]["status"] = f"❌ Error: {error_message}"
                st.session_state.processing = False


def update_processing_status(step: str, progress: int):
    """
    Update the processing status in the chat interface.
    
    Args:
        step: Current processing step description
        progress: Progress percentage (0-100)
    """
    if st.session_state.messages:
        last_msg_idx = len(st.session_state.messages) - 1
        if st.session_state.messages[last_msg_idx]["role"] == "assistant":
            st.session_state.messages[last_msg_idx]["status"] = f"⏳ {step}... ({progress}%)"