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
    # Use a plain container with a key so CSS can target it via
    # .st-key-chat_history, then set height + overflow-y
    chat_container = st.container(border=False, key="chat_history")
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "files" in message and message["files"]:
                    st.markdown("**Attached Files:**")
                    for fi in message["files"]:
                        st.caption(
                            f"📄 {fi['name']} ({fi['size']/(1024*1024):.2f} MB)"
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
        /* Suppress the outer page scroll */
        [data-testid="stMain"] {{
            overflow-y: hidden !important;
        }}
        /* Force the main vertical block to fill its parent (100vh container) */
        [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{
            height: 100% !important;
        }}
        /* Chat scroll area: the keyed container is the scroll region.
           min-height:0 overrides flex default (min-height:auto) so the
           container can be smaller than its content and trigger scroll.
           max-height caps it so flex-grow cannot stretch it beyond bounds. */
        .st-key-chat_history {{
            height: calc(100vh - {_INPUT_BAR_HEIGHT + 140}px) !important;
            max-height: calc(100vh - {_INPUT_BAR_HEIGHT + 140}px) !important;
            min-height: 0 !important;
            overflow-y: auto !important;
        }}
        /* Prevent flex children from shrinking — let them overflow to trigger scroll */
        .st-key-chat_history > * {{
            flex-shrink: 0 !important;
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


def _build_system_prompt() -> str:
    """Build the system prompt with current connection states."""
    github_connected = st.session_state.get("github_connected", False)
    slack_connected = st.session_state.get("slack_connected", False)
    github_url = st.session_state.get("github_url", "")
    slack_channel = st.session_state.get(
        "slack_channel_name", st.session_state.get("slack_channel_id", "")
    )

    connection_lines = ""
    if github_connected:
        connection_lines += f"- GitHub: Connected to `{github_url}`\n"
    else:
        connection_lines += "- GitHub: NOT connected\n"
    if slack_connected:
        connection_lines += f"- Slack: Connected to #{slack_channel}\n"
    else:
        connection_lines += "- Slack: NOT connected\n"

    system_prompt = f"""
    You are Archie, an AI Knowledge Base Assistant.

    Your capabilities:
    - Help users manage and query their knowledge base
    - Analyze GitHub repositories for knowledge extraction
    - Retrieve and summarize Slack conversations
    - Answer general questions about the knowledge base workflow

    Current integration status:
    {connection_lines}
    Rules:
    - If the user asks about Slack functionality and Slack is NOT connected, tell them to connect Slack from the Integrations panel on the left sidebar first.
    - If the user asks about GitHub functionality and GitHub is NOT connected, tell them to connect GitHub from the Integrations panel on the left sidebar first.
    - Be concise, helpful, and professional.
    - When you don't know something, say so clearly.
    - Format responses in Markdown for readability.
    """

    return system_prompt


def _build_history_messages() -> list:
    """Convert recent session_state messages to LangChain message objects."""
    from langchain_core.messages import HumanMessage, AIMessage

    history = []
    recent = st.session_state.get("messages", [])[-10:]
    for msg in recent:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
    return history


def _get_llm():
    """
    Get or create the ChatOpenAI LLM instance, cached in session_state.
    Reuses the same instance across chat turns to avoid repeated initialization.
    """
    if "llm" not in st.session_state:
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
        from gen_ai_hub.proxy.langchain.openai import ChatOpenAI

        proxy_client = get_proxy_client("gen-ai-hub")
        st.session_state.llm = ChatOpenAI(
            proxy_model_name="gpt-4o",
            proxy_client=proxy_client,
            temperature=0.3,
            max_tokens=1024,
        )
    return st.session_state.llm


def generate_chat_response(user_input: str, files: list = None) -> str:
    """
    Generate a chat response using SAP GenAI SDK (ChatOpenAI with proxy_client).
    Falls back to a simple error message if the SDK is unavailable.
    """
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
    except ImportError:
        return (
            "AI service is not available (gen_ai_hub SDK not installed). "
            "Please contact your administrator."
        )

    # Build user message text (include file info if present)
    user_message_text = user_input
    if files:
        file_list = ", ".join(f["name"] for f in files)
        user_message_text = (
            f"[User attached {len(files)} file(s): {file_list}]\n\n{user_input}"
        )

    try:
        llm = _get_llm()
        system_prompt = _build_system_prompt()
        history = _build_history_messages()

        messages = (
            [SystemMessage(content=system_prompt)]
            + history
            + [HumanMessage(content=user_message_text)]
        )

        response = llm.invoke(messages)
        return response.content

    except Exception as e:
        return f"I encountered an error generating a response: {str(e)}"
