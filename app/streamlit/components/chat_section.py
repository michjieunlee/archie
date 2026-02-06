"""
Chat section component for the Streamlit app.
Provides an independent chat interface that works with or without GitHub config.
"""
import streamlit as st
from config.settings import MAX_FILE_SIZE_MB, MAX_FILES_COUNT


def render_chat_section():
    """
    Render the chat interface section.
    """
    # Chat container with fixed height
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display attached files if any
                if "files" in message and message["files"]:
                    st.markdown("**📎 Attached Files:**")
                    for file_info in message["files"]:
                        file_size_mb = file_info['size'] / (1024 * 1024)
                        st.caption(f"📄 {file_info['name']} ({file_size_mb:.2f}MB)")
        
        # Show welcome message if no messages
        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.markdown("""
                👋 **Welcome to Archie!**
                
                I'm your AI Knowledge Base Assistant. Here's what I can help you with:
                
                - 💬 **Chat freely:** Ask me anything, request summaries, or seek clarifications
                - 📊 **Analyze repositories:** Process GitHub repos to extract knowledge base articles
                - 🔍 **Provide insights:** Get explanations about code patterns and best practices
                - 📎 **Upload files:** Attach up to 3 files to your messages for analysis
                
                Feel free to start chatting, or configure GitHub settings on the left to process repositories!
                """)
    
    st.divider()
    
    # File upload section
    st.markdown(f"**📎 Attach Files (optional, up to {MAX_FILES_COUNT} files, max {MAX_FILE_SIZE_MB}MB each):**")
    
    # Initialize file uploader key for clearing after message send
    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    uploaded_files = st.file_uploader(
        "Drag and drop files here or click to browse",
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        help=f"Upload up to {MAX_FILES_COUNT} files (max {MAX_FILE_SIZE_MB}MB each) to include in your message",
        label_visibility="collapsed"
    )
    
    # Validate file count and size
    if uploaded_files:
        valid_files = []
        for file in uploaded_files[:MAX_FILES_COUNT]:
            file_size_mb = file.size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                st.error(f"❌ File '{file.name}' exceeds {MAX_FILE_SIZE_MB}MB limit ({file_size_mb:.2f}MB). Skipping this file.")
            else:
                valid_files.append(file)
        
        if len(uploaded_files) > MAX_FILES_COUNT:
            st.warning(f"⚠️ Maximum {MAX_FILES_COUNT} files allowed. Only the first {MAX_FILES_COUNT} files will be used.")
        
        uploaded_files = valid_files
    
    # Display currently attached files
    if uploaded_files:
        st.markdown(f"**Selected files ({len(uploaded_files)}/{MAX_FILES_COUNT}):**")
        cols = st.columns(len(uploaded_files))
        for idx, file in enumerate(uploaded_files):
            with cols[idx]:
                file_size_mb = file.size / (1024 * 1024)
                st.caption(f"📄 {file.name}")
                st.caption(f"Size: {file_size_mb:.2f}MB")
    
    # Chat input at the bottom
    user_input = st.chat_input(
        "Type your message here...",
        disabled=st.session_state.get("processing", False)
    )
    
    if user_input:
        # Prepare file information if files are uploaded
        file_info_list = []
        if uploaded_files:
            for file in uploaded_files:
                file_info_list.append({
                    "name": file.name,
                    "size": file.size,
                    "type": file.type,
                    "content": file.getvalue()  # Store file content
                })
        
        # Add user message with files
        user_message = {
            "role": "user",
            "content": user_input
        }
        if file_info_list:
            user_message["files"] = file_info_list
        
        st.session_state.messages.append(user_message)
        
        # Generate response based on input and files
        response = generate_chat_response(user_input, file_info_list)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        
        # Clear the file uploader by incrementing a counter
        if "file_uploader_key" not in st.session_state:
            st.session_state.file_uploader_key = 0
        st.session_state.file_uploader_key += 1
        
        st.rerun()


def generate_chat_response(user_input: str, files: list = None) -> str:
    """
    Generate a chat response based on user input and optional files.
    This is a simple mock implementation that will be enhanced later.
    
    Args:
        user_input: The user's message
        files: List of uploaded file information dictionaries
        
    Returns:
        str: The assistant's response
    """
    user_input_lower = user_input.lower()
    
    # Handle file uploads
    if files:
        file_response = f"I've received {len(files)} file(s):\n\n"
        for file_info in files:
            file_size_mb = file_info['size'] / (1024 * 1024)
            file_response += f"- **{file_info['name']}** ({file_size_mb:.2f}MB, type: {file_info['type']})\n"
        
        file_response += "\n📝 **Note:** File analysis capabilities will be fully implemented in the next phase. "
        file_response += "For now, I've acknowledged your files and can discuss them based on their names and types.\n\n"
        
        # Add context-aware response based on file types
        file_types = [f['type'] for f in files]
        if any('text' in ft for ft in file_types):
            file_response += "I see you've uploaded text files. Once file analysis is fully integrated, I'll be able to extract information and generate insights from them."
        elif any('image' in ft for ft in file_types):
            file_response += "I see you've uploaded images. Visual content analysis will be available in future updates."
        elif any('pdf' in ft or 'document' in ft for ft in file_types):
            file_response += "I see you've uploaded document files. Document parsing and knowledge extraction will be available soon."
        
        return file_response + f"\n\nRegarding your message: \"{user_input}\"\n\n" + generate_text_response(user_input_lower)
    
    return generate_text_response(user_input_lower)


def generate_text_response(user_input_lower: str) -> str:
    """
    Generate a text-based response for user input.
    
    Args:
        user_input_lower: Lowercase version of user input
        
    Returns:
        str: The assistant's response
    """
    # Check for common queries
    if "help" in user_input_lower:
        return """
        **Here's how I can help:**
        
        1. **General Chat:** Ask me questions about anything
        2. **Repository Analysis:** Configure GitHub settings and I'll analyze repositories to extract knowledge
        3. **File Upload:** Attach up to 3 files to your messages for analysis
        
        What would you like to do?
        """
    
    elif any(word in user_input_lower for word in ["hello", "hi", "hey"]):
        return "Hello! 👋 How can I assist you today? Feel free to ask me anything, upload files, or configure GitHub settings to connect knowledgebase."
    
    elif "github" in user_input_lower or "repository" in user_input_lower or "repo" in user_input_lower:
        if st.session_state.github_url:
            return f"I see you have configured: `{st.session_state.github_url}`. Click the 'Start Processing' button on the left to analyze this repository, or ask me more about it!"
        else:
            return "To analyze GitHub repositories, please configure the GitHub URL and token in the configuration section on the left, then click 'Connect'."
    
    elif "file" in user_input_lower or "upload" in user_input_lower or "attach" in user_input_lower:
        return f"""
        **File Upload Feature:**
        
        You can attach up to {MAX_FILES_COUNT} files to your messages! Here's how:
        
        1. **Drag & Drop:** Drag files directly into the file upload area above the chat input
        2. **Click to Browse:** Click on the file upload area to select files from your computer
        3. **Add Your Message:** Type your message in the chat input
        4. **Send:** Hit Enter to send your message with the attached files
        
        **Limits:**
        - Maximum {MAX_FILES_COUNT} files per message
        - Maximum {MAX_FILE_SIZE_MB}MB per file
        
        Supported file types include text files, documents, images, and more. File analysis capabilities are being enhanced and will be fully available soon!
        """
    
    else:
        # Generic response
        return f"I understand you said: \"{user_input_lower}\"\n\nI'm a knowledge base assistant focused on analyzing GitHub repositories and providing insights. While I can chat about various topics, my main strength is in processing code repositories and extracting valuable knowledge. You can also upload files (up to 3) for analysis. Would you like to analyze a repository, upload files, or ask me something specific?"
