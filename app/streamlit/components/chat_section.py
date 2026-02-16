"""
Chat section component for the Streamlit app.
Provides a centered chat interface with sticky input bar and file upload dialog.
"""

import re
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from config.settings import MAX_FILE_SIZE_MB, MAX_FILES_COUNT
from prompts import (
    build_system_prompt,
    build_api_response_format_prompt,
    INTENT_CLASSIFICATION_PROMPT,
)

# Height of the sticky input bar (px) – used to calculate chat container height
_INPUT_BAR_HEIGHT = 200


# ── file-upload dialog (requires Streamlit >= 1.37) ────────────────────
@st.dialog("Attach Text Files")
def file_upload_dialog():
    """Pop-up dialog for attaching text files."""
    st.markdown(
        f"Upload up to **{MAX_FILES_COUNT}** text files (max **{MAX_FILE_SIZE_MB} MB** each)."
    )

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
                content = message["content"]
                if message["role"] == "user":
                    # Preserve single newlines as hard line breaks in Markdown.
                    content = re.sub(r"(?<!\n)\n(?!\n)", "  \n", content)
                st.markdown(content)
                if "files" in message and message["files"]:
                    st.markdown("**Attached Files:**")
                    for fi in message["files"]:
                        st.caption(f"📄 {fi['name']} ({fi['size']/(1024*1024):.2f} MB)")

        # Welcome message
        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.markdown(
                    """
                👋 **Welcome to Archie!**

                I'm your AI Knowledge Base Assistant. Here's what I can help you with:

                - 💬 **Chat:** Ask me anything, request summaries, or seek clarifications
                - 📊 **Connect KnowledgeBase repository:** Connect GitHub to extract knowledge base documents
                - 📊 **Connect Slack channel:** Connect Slack to extract messages
                - 📎 **Upload files:** Attach text files

                Connect your GitHub repository and Slack channel on the left, then get started!
                """
                )

    # CSS: make the chat container fill available vertical space
    st.markdown(
        f"""
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
    """,
        unsafe_allow_html=True,
    )

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
                "SEND",
                key="send_btn",
                use_container_width=True,
                type="primary",
                # help="Send message",
            )
            attach_clicked = st.button(
                "ATTACH FILES",
                key="attach_btn",
                use_container_width=True,
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
        st.session_state.scroll_to_bottom = True
        st.rerun()


def _get_connection_status() -> dict:
    """Return current integration connection status."""
    return {
        "github_connected": st.session_state.get("github_connected", False),
        "slack_connected": st.session_state.get("slack_connected", False),
        "github_url": st.session_state.get("github_url", ""),
        "slack_channel_id": st.session_state.get("slack_channel_id", ""),
        "slack_channel_name": st.session_state.get(
            "slack_channel_name", st.session_state.get("slack_channel_id", "")
        ),
    }


def _build_system_prompt() -> str:
    """Build the system prompt with current connection states."""
    status = _get_connection_status()

    connection_lines = ""
    if status["github_connected"]:
        connection_lines += f"- GitHub: Connected to `{status['github_url']}`\n"
    else:
        connection_lines += "- GitHub: NOT connected\n"
    if status["slack_connected"]:
        connection_lines += f"- Slack: Connected to #{status['slack_channel_name']}\n"
    else:
        connection_lines += "- Slack: NOT connected\n"

    return build_system_prompt(connection_lines)

# Map each action to the integrations it requires.
_ACTION_REQUIREMENTS = {
    "kb_from_slack": ["slack", "github"], # TODO: check if slack -> github PR is mandatory
    "kb_from_text":  ["github"],
    "kb_query":      ["github"],
}


def _build_history_messages() -> list:
    """Convert recent session_state messages to OpenAI message format."""
    history = []
    recent = st.session_state.get("messages", [])[-10:]
    for msg in recent:
        if msg["role"] in ("user", "assistant"):
            history.append({"role": msg["role"], "content": msg["content"]})
    return history


def _get_llm_client():
    """
    Get or create the OpenAI client instance, cached in session_state.

    Uses gen_ai_hub native SDK (not LangChain wrapper).
    """
    if "llm_client" not in st.session_state:
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
        from gen_ai_hub.proxy.native.openai import OpenAI

        proxy_client = get_proxy_client("gen-ai-hub")
        st.session_state.llm_client = OpenAI(proxy_client=proxy_client)
    return st.session_state.llm_client


# ── Intent classification ─────────────────────────────────────────────


def _classify_intent(user_input: str, files: list | None = None) -> dict[str, Any]:
    """
    Ask the LLM to classify the user's message into an action.

    Returns:
        {"action": str, "parameters": dict or str}
    """
    import json

    client = _get_llm_client()

    user_text = user_input
    if files:
        file_list = ", ".join(f["name"] for f in files)
        user_text = f"[User attached {len(files)} file(s): {file_list}]\n\n{user_input}"

    messages = [
        {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
        {"role": "user", "content": user_text},
    ]

    response = client.chat.completions.create(
        model_name='gpt-4o-mini',
        messages=messages,
        temperature=0.3,
        max_tokens=512
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model wraps the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(raw)
        action = parsed.get("action", "chat_only")
        
        if action not in ("kb_from_slack", "kb_from_text", "kb_query", "chat_only"):
            action = "chat_only"
        
        if action in ("kb_from_slack", "kb_from_text"):
            default_params = {}
        else:
            default_params = ""
        
        parameters = parsed.get("parameters", default_params)
        return {"action": action, "parameters": parameters}
            
    except (json.JSONDecodeError, AttributeError):
        return {"action": "chat_only", "parameters": ""}


def _check_prerequisites(action: str) -> str | None:
    """
    Return a user-facing message if a required integration is missing,
    or None if everything is connected.
    """
    required = _ACTION_REQUIREMENTS.get(action, [])
    status = _get_connection_status()
    missing = []

    if "slack" in required and not status["slack_connected"]:
        missing.append("**Slack** — connect a channel from the Integrations panel in the left sidebar")
    if "github" in required and not status["github_connected"]:
        missing.append("**GitHub** — connect a repository from the Integrations panel in the left sidebar")

    if missing:
        lines = "\n".join(f"- {m}" for m in missing)
        return f"To do that I need the following integration(s) configured first:\n\n{lines}\n\nPlease connect them and try again."
    return None


# ── API dispatch ──────────────────────────────────────────────────────


def _execute_action(action: str, parameters, user_input: str, files: list | None) -> dict | None:
    """
    Call the appropriate backend API and return the raw result dict,
    or None if the action is chat_only.
    
    Args:
        action: The action type (kb_from_slack, kb_from_text, kb_query, chat_only)
        parameters: Either dict (for kb_from_slack) or str (for other actions) # TODO
        user_input: Original user input
        files: Optional list of uploaded files
    """
    from services.api_client import kb_from_slack, kb_from_text, kb_query

    if action == "kb_from_slack":
        # Extract structured parameters from dict
        if isinstance(parameters, dict):
            from_datetime = parameters.get("from_datetime")
            to_datetime = parameters.get("to_datetime")
            limit = parameters.get("limit")
        else:
            from_datetime = None
            to_datetime = None
            limit = None
        
        return kb_from_slack(
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit if limit is not None else 50  # API default
        )

    elif action == "kb_from_text":
        if isinstance(parameters, dict):
            title = parameters.get("title")
            metadata = parameters.get("metadata")
        else:
            title = None
            metadata = None
        
        # Build text from user input + files
        text = user_input
        if files:
            file_texts = []
            for f in files:
                try:
                    file_texts.append(f["content"].decode("utf-8", errors="replace"))
                except Exception:
                    file_texts.append(str(f["content"]))
            text = "\n\n".join([text] + file_texts) if text else "\n\n".join(file_texts)
        
        return kb_from_text(text=text, title=title, metadata=metadata)

    elif action == "kb_query":
        return kb_query(query=parameters or user_input)

    return None


def _format_api_response(user_input: str, action: str, api_result: dict) -> str:
    """
    Use the LLM to turn a raw API response into a human-friendly message.
    """
    import json

    client = _get_llm_client()
    
    api_result_json = json.dumps(api_result, indent=2, default=str)
    format_prompt = build_api_response_format_prompt(user_input, action, api_result_json)

    messages = [
        {"role": "system", "content": format_prompt},
        {"role": "user", "content": "Transform the API response into a user-friendly message."},
    ]

    response = client.chat.completions.create(
        model_name='gpt-4o-mini',
        messages=messages,
        temperature=0.3,
        max_tokens=1024
    )
    return response.choices[0].message.content


# ── Main entry point ──────────────────────────────────────────────────


def generate_chat_response(user_input: str, files: list = None) -> str:
    """
    Generate a chat response.

    Flow:
    1. LLM classifies the user's intent into one of four actions.
    2. If the action needs Slack / GitHub and those aren't connected,
       return a message asking the user to connect them.
    3. If prerequisites are met, call the backend API.
    4. Feed the API result back to the LLM for a human-friendly summary.
    5. For chat_only, fall through to a regular LLM conversation.
    """
    try:
        # Step 1 — classify intent
        intent = _classify_intent(user_input, files)
        action = intent["action"]
        parameters = intent["parameters"]

        # Step 2 — check prerequisites
        if action != "chat_only":
            prereq_msg = _check_prerequisites(action)
            if prereq_msg:
                return prereq_msg

        # Step 3 — execute API action (if any)
        api_result = _execute_action(action, parameters, user_input, files)

        if api_result is not None:
            # Step 4 — LLM summarises the API result
            return _format_api_response(user_input, action, api_result)

        # Step 5 — chat_only: regular conversation
        client = _get_llm_client()
        system_prompt = _build_system_prompt()
        history = _build_history_messages()

        user_text = user_input
        if files:
            file_list = ", ".join(f["name"] for f in files)
            user_text = f"[User attached {len(files)} file(s): {file_list}]\n\n{user_input}"

        messages = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": user_text}]
        )
        
        response = client.chat.completions.create(
            model_name='gpt-4o-mini',
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Encountered an error generating a response: {str(e)}"
