"""
Chat section component for the Streamlit app.
Provides a centered chat interface with sticky input bar and file upload dialog.
"""

import json
import logging
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

# Configure logger for this module
logger = logging.getLogger(__name__)

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
        var lastSidebarState = null;
        
        function pin() {
            var doc = window.parent.document;

            var ta = doc.querySelector('textarea[aria-label="Message"]');
            if (!ta) return;

            var block = ta.closest('[data-testid="stVerticalBlock"]');
            if (!block) return;
            var outer = block.parentElement &&
                          block.parentElement.closest('[data-testid="stVerticalBlock"]');
            if (outer) block = outer;

            // Check if sidebar is collapsed
            var sidebar = doc.querySelector('[data-testid="stSidebar"]');
            var sidebarCollapsed = !sidebar || 
                                   sidebar.getAttribute('aria-expanded') === 'false' ||
                                   getComputedStyle(sidebar).width === '0px';
            
            // Track sidebar state changes
            if (lastSidebarState !== sidebarCollapsed) {
                lastSidebarState = sidebarCollapsed;
            }

            // Use fixed positioning that spans full viewport width
            // Let Streamlit's native layout handle the offset
            block.style.position   = 'fixed';
            block.style.bottom     = '0';
            block.style.left       = '0';
            block.style.right      = '0';
            block.style.width      = '100%';
            block.style.background = '#ffffff';
            block.style.borderTop  = '1px solid #e0e0e0';
            block.style.padding    = '0.75rem 2rem';
            block.style.boxSizing  = 'border-box';
            block.style.zIndex     = '100';
            block.style.boxShadow  = '0 -2px 8px rgba(0,0,0,0.06)';
            block.dataset.pinned   = '1';
            
            // Apply margin to account for sidebar when it's open
            if (!sidebarCollapsed && sidebar) {
                var sidebarWidth = sidebar.offsetWidth;
                block.style.marginLeft = sidebarWidth + 'px';
                block.style.width = 'calc(100% - ' + sidebarWidth + 'px)';
            } else {
                block.style.marginLeft = '0';
                block.style.width = '100%';
            }
        }

        // Initial pin
        setTimeout(pin, 300);
        
        // Re-pin on any DOM changes (catches sidebar toggle)
        var observer = new MutationObserver(function() { 
            setTimeout(pin, 150); 
        });
        observer.observe(window.parent.document.body, {
            childList: true, 
            subtree: true, 
            attributes: true,
            attributeFilter: ['aria-expanded', 'style']
        });
        
        // Also listen for window resize (catches manual sidebar drag)
        window.parent.addEventListener('resize', function() {
            setTimeout(pin, 100);
        });
    })();
    </script>
    """
    components.html(js, height=0, scrolling=False)


def _inject_autoscroll_js():
    """Use components.html to run JS that auto-scrolls chat to bottom on new messages."""
    js = """
    <script>
    (function() {
        // Unique namespace for auto-scroll to avoid conflicts
        window.chatAutoScroll = window.chatAutoScroll || {};
        
        var scrollTimeout = null;
        var lastMessageCount = 0;
        var lastScrollHeight = 0;
        
        function scrollToBottom() {
            var doc = window.parent.document;
            
            // Find the chat history container
            var chatContainer = doc.querySelector('.st-key-chat_history');
            if (!chatContainer) return;
            
            // Count current messages
            var messages = chatContainer.querySelectorAll('[data-testid="stChatMessage"]');
            var currentMessageCount = messages.length;
            
            // Get current scroll height (increases as content is added)
            var currentScrollHeight = chatContainer.scrollHeight;
            
            // Scroll if there are new messages OR if content height has increased
            // (content height increases for multi-line responses being rendered)
            if (currentMessageCount > lastMessageCount || currentScrollHeight > lastScrollHeight) {
                lastMessageCount = currentMessageCount;
                lastScrollHeight = currentScrollHeight;
                
                // Smooth scroll to bottom
                chatContainer.scrollTo({
                    top: chatContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }
        
        function debouncedScroll() {
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            scrollTimeout = setTimeout(scrollToBottom, 100);
        }
        
        // Initial scroll after a delay to let content load
        setTimeout(scrollToBottom, 500);
        
        // Watch for new messages being added
        var autoScrollObserver = new MutationObserver(function(mutations) {
            debouncedScroll();
        });
        
        // Start observing the document body for changes
        var doc = window.parent.document;
        autoScrollObserver.observe(doc.body, {
            childList: true,
            subtree: true
        });
        
        // Store observer globally so it can be accessed if needed
        window.chatAutoScroll.observer = autoScrollObserver;
        window.chatAutoScroll.scrollToBottom = scrollToBottom;
    })();
    </script>
    """
    components.html(js, height=0, scrolling=False)


def _inject_keyboard_shortcuts_js():
    """Use components.html to run JS that handles Command+Enter for sending messages."""
    js = """
    <script>
    (function() {
        function setupKeyboardShortcuts() {
            var doc = window.parent.document;
            var textarea = doc.querySelector('textarea[aria-label="Message"]');
            
            if (!textarea) {
                setTimeout(setupKeyboardShortcuts, 300);
                return;
            }
            
            // Remove existing listener if any (to avoid duplicates on re-render)
            if (textarea._keydownHandler) {
                textarea.removeEventListener('keydown', textarea._keydownHandler);
            }
            
            // Add keyboard event listener
            textarea._keydownHandler = function(e) {
                // Check for Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux)
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    
                    // Find the SEND button
                    var sendBtn = null;
                    var buttons = doc.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.includes('SEND')) {
                            sendBtn = buttons[i];
                            break;
                        }
                    }
                    
                    // Click the button if found and not disabled
                    if (sendBtn && !sendBtn.disabled) {
                        sendBtn.click();
                    }
                }
            };
            
            textarea.addEventListener('keydown', textarea._keydownHandler);
        }
        
        // Initial setup
        setupKeyboardShortcuts();
        
        // Re-setup on DOM changes (handles Streamlit re-renders)
        var observer = new MutationObserver(setupKeyboardShortcuts);
        observer.observe(window.parent.document.body, {
            childList: true,
            subtree: true
        });
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
    
    # Inject JS to auto-scroll chat to bottom on new messages
    _inject_autoscroll_js()
    
    # Inject JS to handle Command+Enter keyboard shortcut
    _inject_keyboard_shortcuts_js()

    # Open the dialog when + is clicked
    if attach_clicked:
        file_upload_dialog()

    # ── handle send ────────────────────────────────────────────────────
    # Initialize generating_response flag if not exists
    if "generating_response" not in st.session_state:
        st.session_state.generating_response = False
    
    # Phase 1: User clicks send - show message immediately and set loading state
    if send_clicked and user_input and not st.session_state.generating_response:
        file_info_list = list(st.session_state.pending_files)

        user_message = {"role": "user", "content": user_input}
        if file_info_list:
            user_message["files"] = file_info_list

        st.session_state.messages.append(user_message)
        
        # Store the input and files for processing in next phase
        st.session_state.pending_user_input = user_input
        st.session_state.pending_user_files = file_info_list
        
        # Set flag to trigger response generation on next render
        st.session_state.generating_response = True

        # Clear pending files and reset input field
        st.session_state.pending_files = []
        st.session_state.chat_input_key += 1
        st.session_state.scroll_to_bottom = True
        st.rerun()
    
    # Phase 2: Generate response after user message is displayed
    if st.session_state.generating_response:
        # Show loading indicator in chat
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking"):
                    # Generate the response
                    user_input_to_process = st.session_state.pending_user_input
                    files_to_process = st.session_state.pending_user_files
                    
                    response = generate_chat_response(user_input_to_process, files_to_process)
                    
                    # Add assistant response to messages
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Clear the generating flag and pending data
                    st.session_state.generating_response = False
                    st.session_state.pending_user_input = None
                    st.session_state.pending_user_files = None
                    
                    # Rerun to show the actual response
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
        connection_lines += "- GitHub: not connected\n"
    if status["slack_connected"]:
        connection_lines += f"- Slack: Connected to #{status['slack_channel_name']}\n"
    else:
        connection_lines += "- Slack: not connected\n"

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


def _classify_intent(user_input: str, files: list | None = None, history: list | None = None) -> dict[str, Any]:
    """
    Ask the LLM to classify the user's message into an action.

    Args:
        user_input: The current user message
        files: Optional list of uploaded files
        history: Optional conversation history for context

    Returns:
        {"action": str, "parameters": dict or str}
    """
    import json

    client = _get_llm_client()

    user_text = user_input
    if files:
        file_list = ", ".join(f["name"] for f in files)
        user_text = f"[User attached {len(files)} file(s): {file_list}]\n\n{user_input}"

    # Build messages with history for context
    messages = [{"role": "system", "content": INTENT_CLASSIFICATION_PROMPT}]
    
    # Add recent conversation history if available (limit to last 5 exchanges for context)
    if history:
        messages.extend(history[-10:])  # Last 10 messages = ~5 exchanges
    
    # Add current user message
    messages.append({"role": "user", "content": user_text})

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
        result = {"action": action, "parameters": parameters}
        logger.debug(f"_classify_intent result: action={action}, parameters={parameters}")
        return result
            
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug(f"_classify_intent failed to parse LLM response: {e}, defaulting to chat_only")
        return {"action": "chat_only", "parameters": ""}


def _check_prerequisites(action: str) -> str | None:
    """
    Return a user-facing message if a required integration is missing,
    or None if everything is connected.
    """
    required = _ACTION_REQUIREMENTS.get(action, [])
    status = _get_connection_status()
    logger.debug(f"_check_prerequisites called for action={action}, required={required}, status={status}")
    
    missing = []

    if "slack" in required and not status["slack_connected"]:
        missing.append("**Slack** — connect a channel from the Integrations panel in the left sidebar")
    if "github" in required and not status["github_connected"]:
        missing.append("**GitHub** — connect a repository from the Integrations panel in the left sidebar")

    if missing:
        logger.debug(f"_check_prerequisites: missing integrations={missing}")
        lines = "\n".join(f"- {m}" for m in missing)
        return f"To do that I need the following integration(s) configured first:\n\n{lines}\n\nPlease connect them and try again."
    
    logger.debug("_check_prerequisites: all prerequisites met")
    return None


# ── API dispatch ──────────────────────────────────────────────────────


def _execute_action(action: str, parameters, user_input: str, files: list | None) -> dict | None:
    """
    Call the appropriate backend API and return the raw result dict,
    or None if the action is chat_only.
    
    Args:
        action: The action type (kb_from_slack, kb_from_text, kb_query, chat_only)
        parameters: Dict for kb_from_slack/kb_from_text with structured params; string for kb_query/chat_only (may be empty)
        user_input: Original user input
        files: Optional list of uploaded files
    """
    from services.api_client import kb_from_slack, kb_from_text, kb_query

    logger.debug(f"_execute_action called with action={action}, parameters={parameters}, user_input length={len(user_input)}, files={len(files) if files else 0}")

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
        
        logger.debug(f"_execute_action: calling kb_from_slack with from_datetime={from_datetime}, to_datetime={to_datetime}, limit={limit}")
        result = kb_from_slack(
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit if limit is not None else 50  # API default
        )
        logger.debug(f"_execute_action: kb_from_slack returned result with keys: {list(result.keys()) if result else None}")
        return result

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
        
        logger.debug(f"_execute_action: calling kb_from_text with title={title}, metadata={metadata}, text length={len(text)}")
        result = kb_from_text(text=text, title=title, metadata=metadata)
        logger.debug(f"_execute_action: kb_from_text returned result with keys: {list(result.keys()) if result else None}")
        return result

    elif action == "kb_query":
        # Use entire user input as query (parameters not used for kb_query)
        logger.debug(f"_execute_action: calling kb_query with query={user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        result = kb_query(query=user_input)
        logger.debug(f"_execute_action: kb_query returned result with keys: {list(result.keys()) if result else None}")
        return result

    logger.debug(f"_execute_action: action={action} does not require API call, returning None")
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
    formatted_response = response.choices[0].message.content
    logger.debug(f"_format_api_response: generated response preview={formatted_response[:200]}{'...' if len(formatted_response) > 200 else ''}")
    return formatted_response


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
        # Step 1 — classify intent with conversation history for context
        logger.debug("generate_chat_response: Step 1 - classifying intent")
        history = _build_history_messages()
        intent = _classify_intent(user_input, files, history)
        action = intent["action"]
        parameters = intent["parameters"]

        # Step 2 — check prerequisites
        if action != "chat_only":
            logger.debug(f"generate_chat_response: Step 2 - checking prerequisites for action={action}")
            prereq_msg = _check_prerequisites(action)
            if prereq_msg:
                logger.debug(f"generate_chat_response: prerequisites not met, returning error message={prereq_msg}")
                return prereq_msg

        # Step 3 — execute API action (if any)
        logger.debug(f"generate_chat_response: Step 3 - executing action={action}")
        api_result = _execute_action(action, parameters, user_input, files)

        if api_result is not None:
            # Step 4 — LLM summarises the API result
            logger.debug(f"generate_chat_response: Step 4 - formatting API response for action={action}, response={json.dumps(api_result, indent=2, default=str)}")
            return _format_api_response(user_input, action, api_result)

        # Step 5 — chat_only: regular conversation
        logger.debug("generate_chat_response: Step 5 - entering chat_only conversation mode")
        client = _get_llm_client()
        system_prompt = _build_system_prompt()
        history = _build_history_messages()
        logger.debug(f"generate_chat_response: using {len(history)} messages from history")

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
        logger.error(f"generate_chat_response: ERROR - {str(e)}", exc_info=True)
        return f"Encountered an error generating a response: {str(e)}"
