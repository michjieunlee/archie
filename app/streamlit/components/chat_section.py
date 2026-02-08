"""
Chat section component for the Streamlit app.
Provides a centered chat interface with sticky input bar and file upload dialog.
"""
import streamlit as st
import streamlit.components.v1 as components
from config.settings import MAX_FILE_SIZE_MB, MAX_FILES_COUNT

# Height of the sticky input bar (px) – used to calculate chat container height
_INPUT_BAR_HEIGHT = 200


# ── file-upload dialog (requires Streamlit >= 1.37) ────────────────────
@st.dialog("Attach Text Files")
def file_upload_dialog():
    """Pop-up dialog for attaching text files."""
    st.markdown(f"Upload up to **{MAX_FILES_COUNT}** text files (max **{MAX_FILE_SIZE_MB} MB** each).")

    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    uploaded = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["txt", "md", "json", "csv", "log", "html"],
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        label_visibility="collapsed",
    )

    # Validate
    valid_files = []
    if uploaded:
        for f in uploaded[:MAX_FILES_COUNT]:
            size_mb = f.size / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                st.error(f"'{f.name}' exceeds {MAX_FILE_SIZE_MB} MB – skipped.")
            else:
                valid_files.append(f)
        if len(uploaded) > MAX_FILES_COUNT:
            st.warning(f"Only the first {MAX_FILES_COUNT} files will be used.")

    # Show selected files
    if valid_files:
        st.markdown(f"**Selected ({len(valid_files)}/{MAX_FILES_COUNT}):**")
        for f in valid_files:
            st.caption(f"📄 {f.name}  ({f.size / (1024*1024):.2f} MB)")

    # Confirm button
    if st.button("Attach", type="primary", disabled=len(valid_files) == 0):
        st.session_state.pending_files = [
            {"name": f.name, "size": f.size, "type": f.type, "content": f.getvalue()}
            for f in valid_files
        ]
        st.session_state.file_uploader_key += 1
        st.rerun()


# ── helper: inject real JS via a zero-height iframe ────────────────────
def _inject_sticky_js():
    """Use components.html to run JS that pins the input bar to the bottom."""
    js = """
    <script>
    (function() {
        function pin() {
            var doc = window.parent.document;

            var ta = doc.querySelector('textarea[aria-label="Message"]');
            if (!ta) return;

            var block = ta.closest('[data-testid="stVerticalBlock"]');
            if (!block) return;
            var outer = block.parentElement &&
                          block.parentElement.closest('[data-testid="stVerticalBlock"]');
            if (outer) block = outer;

            // Match the main content area's exact bounds
            var mainEl = doc.querySelector('[data-testid="stMain"]');
            var left = 0;
            var width = '100%';
            if (mainEl) {
                var rect = mainEl.getBoundingClientRect();
                left = rect.left;
                width = rect.width + 'px';
            }

            block.style.position   = 'fixed';
            block.style.bottom     = '0';
            block.style.left       = left + 'px';
            block.style.width      = width;
            block.style.right      = 'auto';
            block.style.background = '#ffffff';
            block.style.borderTop  = '1px solid #e0e0e0';
            block.style.padding    = '0.75rem 2rem';
            block.style.boxSizing  = 'border-box';
            block.style.zIndex     = '100';
            block.style.boxShadow  = '0 -2px 8px rgba(0,0,0,0.06)';
            block.dataset.pinned   = '1';
        }

        setTimeout(pin, 300);
        new MutationObserver(function() { setTimeout(pin, 150); })
            .observe(window.parent.document.body, {childList: true, subtree: true});
    })();
    </script>
    """
    components.html(js, height=0, scrolling=False)


# ── main render function ───────────────────────────────────────────────
def render_chat_section():
    """
    Render chat history in a scrollable container and a sticky input bar.
    """
    if "pending_files" not in st.session_state:
        st.session_state.pending_files = []

    # ── scrollable chat history ────────────────────────────────────────
    # height is viewport-relative via CSS override below; the Python value
    # is just an initial fallback.
    chat_container = st.container(height=500, border=False)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "files" in message and message["files"]:
                    st.markdown("**📎 Attached Files:**")
                    for fi in message["files"]:
                        st.caption(
                            f"{fi['name']} ({fi['size']/(1024*1024):.2f} MB)"
                        )

        # Welcome message
        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.markdown("""
                👋 **Welcome to Archie!**

                I'm your AI Knowledge Base Assistant. Here's what I can help you with:

                - 💬 **Chat:** Ask me anything, request summaries, or seek clarifications
                - 📊 **Connect KnowledgeBase repository:** Connect GitHub to extract knowledge base articles
                - 📊 **Connect Slack channel:** Connect Slack to extract messages
                - 📎 **Upload files:** Attach text files

                Connect your GitHub repository and Slack channel on the left, then get started!
                """)

    # CSS: make the chat container fill available vertical space
    st.markdown(f"""
        <style>
        /* Override the fixed-height container so it stretches dynamically */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            height: calc(100vh - {_INPUT_BAR_HEIGHT + 140}px) !important;
            max-height: none !important;
            min-height: 200px !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ── input bar (will be pinned to bottom by JS) ─────────────────────
    input_bar = st.container()
    with input_bar:
        # Show pending file badges above input
        if st.session_state.pending_files:
            badge_html = " ".join(
                f'<span class="file-badge">📄 {f["name"]}</span>'
                for f in st.session_state.pending_files
            )
            st.markdown(badge_html, unsafe_allow_html=True)

        if "chat_input_key" not in st.session_state:
            st.session_state.chat_input_key = 0

        col_input, col_btns = st.columns([6, 1])

        with col_input:
            user_input = st.text_area(
                "Message",
                height=150,
                placeholder="Type your message here...",
                key=f"chat_input_area_{st.session_state.chat_input_key}",
                label_visibility="collapsed",
            )

        with col_btns:
            send_clicked = st.button(
                "SEND", key="send_btn", use_container_width=True, type="primary", 
                # help="Send message",
            )
            attach_clicked = st.button(
                "ATTACH FILES", key="attach_btn", use_container_width=True,
                # help="Attach text files",
            )

    # Inject JS to pin the input bar
    _inject_sticky_js()

    # Open the dialog when + is clicked
    if attach_clicked:
        file_upload_dialog()

    # ── handle send ────────────────────────────────────────────────────
    if send_clicked and user_input:
        file_info_list = list(st.session_state.pending_files)

        user_message = {"role": "user", "content": user_input}
        if file_info_list:
            user_message["files"] = file_info_list

        st.session_state.messages.append(user_message)

        response = generate_chat_response(user_input, file_info_list)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Clear pending files and reset input field
        st.session_state.pending_files = []
        st.session_state.chat_input_key += 1
        st.rerun()


def generate_chat_response(user_input: str, files: list = None) -> str:
    """
    Generate a mock chat response based on user input and optional files.
    Will be replaced with actual AI responses in Phase 2.
    """
    response = ""

    if files:
        response += f"I've received {len(files)} file(s):\n\n"
        for f in files:
            response += f"- **{f['name']}** ({f['size'] / (1024 * 1024):.2f}MB)\n"
        response += "\n📝 **Note:** File analysis will be fully implemented in the next phase.\n\n"
        response += f"Regarding your message: \"{user_input}\"\n\n"

    query = user_input.lower()

    if "help" in query:
        response += ("**Here's how I can help:**\n\n"
                     "1. **General Chat:** Ask me questions about anything\n"
                     "2. **Repository Analysis:** Configure GitHub settings and I'll analyze repositories\n"
                     f"3. **File Upload:** Attach up to {MAX_FILES_COUNT} files for analysis\n\n"
                     "What would you like to do?")
    elif any(w in query for w in ["hello", "hi", "hey"]):
        response += "Hello! How can I assist you today? Feel free to ask me anything, upload files, or configure GitHub settings to connect your knowledgebase."
    elif any(w in query for w in ["github", "repository", "repo"]):
        if st.session_state.github_url:
            response += f"I see you have configured: `{st.session_state.github_url}`. Click 'Start Processing' on the left to analyze this repository."
        else:
            response += "To analyze GitHub repositories, configure the GitHub URL and token in the sidebar, then click 'Connect'."
    elif any(w in query for w in ["file", "upload", "attach"]):
        response += (f"You can attach up to **{MAX_FILES_COUNT}** files (max **{MAX_FILE_SIZE_MB}MB** each) "
                     "using the **ATTACH FILES** button below the chat input.")
    else:
        response += (f"I understand you said: \"{user_input}\"\n\n"
                     "I'm a knowledge base assistant focused on analyzing GitHub repositories. "
                     "Would you like to analyze a repository, upload files, or ask me something specific?")

    return response
