"""
Chat section component for the Streamlit app.
Provides a centered chat interface with sticky input bar and file upload dialog.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Union

import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel, Field
from config.settings import MAX_TOTAL_FILES_SIZE_MB, MAX_FILES_COUNT
from prompts import (
    build_system_prompt,
    build_api_response_format_prompt,
    INTENT_CLASSIFICATION_PROMPT,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

# Height of the sticky input bar (px) – used to calculate chat container height
_INPUT_BAR_HEIGHT = 200

# Maximum number of messages to keep in history for LLM context
_MAX_HISTORY_MESSAGES = 20

# Model to use
_LLM_MODEL = "gpt-4o-mini"


# ── Pydantic models for structured output ──────────────────────────────


class KBFromSlackParameters(BaseModel):
    """Parameters for kb_from_slack action"""
    from_datetime: Optional[str] = Field(None, description="ISO 8601 datetime string or null")
    to_datetime: Optional[str] = Field(None, description="ISO 8601 datetime string or null")
    limit: Optional[int] = Field(None, description="Integer between 1-100 or null", ge=1, le=100)
    
    class Config:
        extra = "forbid"  # OpenAI requires additionalProperties: false


class KBFromTextParameters(BaseModel):
    """Parameters for kb_from_text action"""
    title: Optional[str] = Field(None, description="Title for the KB article or null")
    metadata: Optional[str] = Field(None, description="JSON string of metadata dict or null")
    
    class Config:
        extra = "forbid"  # OpenAI requires additionalProperties: false


class IntentClassification(BaseModel):
    """Intent classification result with action and parameters"""
    action: str = Field(
        description="One of: kb_from_slack, kb_from_text, kb_query, chat_only",
        pattern="^(kb_from_slack|kb_from_text|kb_query|chat_only)$"
    )
    parameters: Union[KBFromSlackParameters, KBFromTextParameters, str] = Field(
        description="Structured params for kb_from_slack/kb_from_text, empty string for others"
    )


# ── file-upload dialog (requires Streamlit >= 1.37) ────────────────────
@st.dialog("Attach Text Files")
def file_upload_dialog():
    """Pop-up dialog for attaching text files."""
    st.markdown(
        f"Upload up to **{MAX_FILES_COUNT}** text files (max **{MAX_TOTAL_FILES_SIZE_MB} MB** total)."
    )

    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    uploaded = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["txt", "md", "csv", "log", "json", "xml", "yaml", "yml", "py", "js", "html", "css"],
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        label_visibility="collapsed",
    )

    # Validate with total size limit
    valid_files = []
    total_size_mb = 0.0
    
    if uploaded:
        for f in uploaded[:MAX_FILES_COUNT]:
            size_mb = f.size / (1024 * 1024)
            
            # Check if adding this file would exceed total limit
            if total_size_mb + size_mb > MAX_TOTAL_FILES_SIZE_MB:
                st.error(f"Cannot add '{f.name}' - exceeds {MAX_TOTAL_FILES_SIZE_MB} MB total limit.")
                break
            
            valid_files.append(f)
            total_size_mb += size_mb
        
        if len(uploaded) > MAX_FILES_COUNT:
            st.warning(f"Only the first {MAX_FILES_COUNT} files will be used.")

    # Show selected files with total size
    if valid_files:
        st.markdown(f"**Selected: {len(valid_files)} file(s) ({total_size_mb:.2f} MB / {MAX_TOTAL_FILES_SIZE_MB} MB)**")
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
            
            // Check if dark mode is active
            var isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            // Apply colors based on theme
            if (isDarkMode) {
                block.style.background = '#1E1E1E';
                block.style.borderTop  = '1px solid #4A4A4A';
                block.style.boxShadow  = '0 -2px 8px rgba(0,0,0,0.3)';
            } else {
                block.style.background = '#ffffff';
                block.style.borderTop  = '1px solid #e0e0e0';
                block.style.boxShadow  = '0 -2px 8px rgba(0,0,0,0.06)';
            }
            
            block.style.padding    = '0.75rem 2rem';
            block.style.boxSizing  = 'border-box';
            block.style.zIndex     = '100';
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

    # Initialize generating_response flag if not exists
    if "generating_response" not in st.session_state:
        st.session_state.generating_response = False

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
                elif message["role"] == "assistant":
                    st.markdown(content, unsafe_allow_html=True)
                if "files" in message and message["files"]:
                    st.markdown("**Attached Files:**")
                    for fi in message["files"]:
                        st.caption(f"📄 {fi['name']} ({fi['size']/(1024*1024):.2f} MB)")

        # Show loading indicator if generating response
        if st.session_state.generating_response:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
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
            overflow-x: hidden !important;
        }}
        /* Prevent flex children from shrinking — let them overflow to trigger scroll */
        .st-key-chat_history > * {{
            flex-shrink: 0 !important;
        }}
        /* Prevent horizontal overflow in chat messages */
        .st-key-chat_history [data-testid="stChatMessage"] {{
            max-width: 100% !important;
            overflow-x: hidden !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
        }}
        /* Handle content within chat messages */
        .st-key-chat_history [data-testid="stChatMessage"] * {{
            max-width: 100% !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
        }}
        /* Handle code blocks - allow internal horizontal scroll */
        .st-key-chat_history [data-testid="stChatMessage"] pre {{
            overflow-x: auto !important;
            white-space: pre !important;
            word-wrap: normal !important;
            overflow-wrap: normal !important;
        }}
        /* Handle inline code */
        .st-key-chat_history [data-testid="stChatMessage"] code {{
            word-break: break-all !important;
        }}
        /* Handle long URLs and text */
        .st-key-chat_history [data-testid="stChatMessage"] p,
        .st-key-chat_history [data-testid="stChatMessage"] div {{
            word-break: break-word !important;
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
    # User clicks send - show message immediately and set loading state
    if send_clicked and user_input and not st.session_state.generating_response:
        file_info_list = list(st.session_state.pending_files)

        # Store original message for display (masked_content will be added later)
        user_message = {"role": "user", "content": user_input, "masked_content": None}
        if file_info_list:
            user_message["files"] = file_info_list
            user_message["masked_files"] = []

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
    "kb_from_slack": ["slack", "github"],
    "kb_from_text":  ["github"],
    "kb_query":      ["github"],
}


def _build_history_messages() -> list:
    """
    Convert session_state messages to OpenAI message format.
    
    Includes:
    - Last _MAX_HISTORY_MESSAGES user message & files & assistant messages (most recent exchanges)
    """
    history = []
    all_messages = st.session_state.get("messages", [])
    
    # Add last N user message & files & assistant messages (recent conversation)
    recent_messages = all_messages[-_MAX_HISTORY_MESSAGES:]
    for msg in recent_messages:
        if msg["role"] == "user":
            # Use masked content for user messages (without file content - already added above)
            content = msg.get("masked_content")
            masked_files_text = msg.get("masked_files_text")
            if content:  # Only add if masked content exists
                history.append({"role": "user", "content": content})
            if masked_files_text:
                history.append({"role": "user", "content": f"[Uploaded file(s)]\n{masked_files_text}"})
        elif msg["role"] == "assistant":
            # Assistant messages are already safe
            history.append({"role": "assistant", "content": msg["content"]})
    
    return history


def _get_llm_client():
    """
    Get or create the ChatOpenAI client instance (LangChain wrapper), cached in session_state.
    
    Uses gen_ai_hub LangChain SDK to support structured output.
    """
    # Always recreate to ensure we have the LangChain wrapper (not native OpenAI)
    # This ensures .with_structured_output() is available
    if "llm_client" not in st.session_state or not hasattr(st.session_state.llm_client, 'with_structured_output'):
        from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

        proxy_client = get_proxy_client("gen-ai-hub")
        st.session_state.llm_client = ChatOpenAI(
            proxy_model_name=_LLM_MODEL,
            proxy_client=proxy_client,
            temperature=0.3,
        )
    return st.session_state.llm_client


# ── Intent classification ─────────────────────────────────────────────


def _classify_intent(user_input: str, files: list | None = None, history: list | None = None) -> dict[str, Any]:
    """
    Ask the LLM to classify the user's message into an action using structured output.

    Args:
        user_input: The current user message
        files: Optional list of uploaded files
        history: Optional conversation history for context

    Returns:
        {"action": str, "parameters": dict or str}
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    client = _get_llm_client()

    # Build messages with history for context
    messages = [SystemMessage(content=INTENT_CLASSIFICATION_PROMPT)]
    
    # Add recent conversation history if available
    if history:
        for msg in history[-_MAX_HISTORY_MESSAGES:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                # Use SystemMessage for assistant responses in history to maintain context
                messages.append(SystemMessage(content=msg["content"]))
    
    # Add current user message
    messages.append(HumanMessage(content=user_input))

    # Use structured output to force JSON schema compliance
    structured_llm = client.with_structured_output(IntentClassification)
    
    try:
        response = structured_llm.invoke(messages)
        
        # Extract action and parameters
        action = response.action
        parameters = response.parameters
        
        # Convert Pydantic models to dicts for kb_from_slack and kb_from_text
        if isinstance(parameters, (KBFromSlackParameters, KBFromTextParameters)):
            parameters = parameters.model_dump()
        
        result = {"action": action, "parameters": parameters}
        logger.info(f"_classify_intent result: action={action}, parameters={parameters}")
        return result
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for token limit errors
        if any(keyword in error_str for keyword in ["token", "context_length_exceeded", "maximum context", "too long"]):
            logger.error(f"_classify_intent token limit error: {str(e)}", exc_info=True)
            # Return a special error action to be handled by caller
            return {"action": "error", "parameters": "", "error_type": "token_limit"}
        
        logger.error(f"_classify_intent error: {str(e)}", exc_info=True)
        # Fallback to chat_only on any other error
        logger.info(f"_classify_intent failed, defaulting to chat_only")
        return {"action": "chat_only", "parameters": ""}


def _check_prerequisites(action: str) -> str | None:
    """
    Return a user-facing message if a required integration is missing,
    or None if everything is connected.
    """
    required = _ACTION_REQUIREMENTS.get(action, [])
    status = _get_connection_status()
    logger.info(f"_check_prerequisites called for action={action}, required={required}, status={status}")
    
    missing = []

    if "slack" in required and not status["slack_connected"]:
        missing.append("**Slack** — connect a channel from the Integrations panel in the left sidebar")
    if "github" in required and not status["github_connected"]:
        missing.append("**GitHub** — connect a repository from the Integrations panel in the left sidebar")

    if missing:
        logger.info(f"_check_prerequisites: missing integrations={missing}")
        lines = "\n".join(f"- {m}" for m in missing)
        return f"To do that I need the following integration(s) configured first:\n\n{lines}\n\nPlease connect them and try again."
    
    logger.info("_check_prerequisites: all prerequisites met")
    return None


# ── API dispatch ──────────────────────────────────────────────────────


def _execute_action(action: str, parameters, user_input: str, files_text: str | None) -> dict | None:
    """
    Call the appropriate backend API and return the raw result dict,
    or None if the action is chat_only.
    
    Args:
        action: The action type (kb_from_slack, kb_from_text, kb_query, chat_only)
        parameters: Dict for kb_from_slack/kb_from_text with structured params; string for kb_query/chat_only (may be empty)
        user_input: Masked user input
        files_text: Masked concatenated file contents with markers (or None if no files)
    """
    from services.api_client import kb_from_slack, kb_from_text, kb_query

    logger.info(f"_execute_action called with action={action}, parameters={parameters}, user_input length={len(user_input)}, files_text length={len(files_text) if files_text else 0}")

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
        
        logger.info(f"_execute_action: calling kb_from_slack with from_datetime={from_datetime}, to_datetime={to_datetime}, limit={limit}")
        result = kb_from_slack(
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit if limit is not None else 20  # API default
        )
        logger.info(f"_execute_action: kb_from_slack returned result with keys: {list(result.keys()) if result else None}")
        return result

    elif action == "kb_from_text":
        if isinstance(parameters, dict):
            title = parameters.get("title")
            metadata_str = parameters.get("metadata")
            # Parse metadata from JSON string if present
            if metadata_str:
                try:
                    metadata = json.loads(metadata_str)
                except (json.JSONDecodeError, TypeError):
                    metadata = None
            else:
                metadata = None
        else:
            title = None
            metadata = None
        
        # Combine masked user input with masked file contents
        if files_text:
            text = f"{user_input}\n\n{files_text}" if user_input else files_text
        else:
            text = user_input
        
        logger.info(f"_execute_action: calling kb_from_text with title={title}, metadata={metadata}, text length={len(text)}")
        result = kb_from_text(text=text, title=title, metadata=metadata)
        logger.info(f"_execute_action: kb_from_text returned result with keys: {list(result.keys()) if result else None}")
        return result

    elif action == "kb_query":
        # Use entire user input as query (parameters not used for kb_query)
        logger.info(f"_execute_action: calling kb_query with query={user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        result = kb_query(query=user_input)
        logger.info(f"_execute_action: kb_query returned result with keys: {list(result.keys()) if result else None}")
        return result

    logger.info(f"_execute_action: action={action} does not require API call, returning None")
    return None


def _format_api_response(user_input: str, action: str, api_result: dict, history: list | None = None) -> str:
    """
    Use the LLM to turn a raw API response into a human-friendly message.
    
    Args:
        user_input: The current user message
        action: The action that was performed
        api_result: The raw API result dict
        history: Optional conversation history for context
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    import json

    client = _get_llm_client()

    api_result_json = json.dumps(api_result, indent=2, default=str)
    format_prompt = build_api_response_format_prompt(user_input, action, api_result_json)

    messages = [SystemMessage(content=format_prompt)]
    
    # Add recent conversation history if available for context
    if history:
        for msg in history[-_MAX_HISTORY_MESSAGES:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(SystemMessage(content=msg["content"]))
    
    # Add the formatting instruction
    messages.append(HumanMessage(content="Transform the API response into a user-friendly message."))

    try:
        response = client.invoke(messages)
        formatted_response = response.content
        
        # Remove markdown code block wrapping if present (e.g., ```...```)
        # The LLM might wrap the response in code blocks based on the prompt examples
        formatted_response = formatted_response.strip()
        if formatted_response.startswith("```") and formatted_response.endswith("```"):
            # Remove the opening ``` and optional language identifier
            lines = formatted_response.split("\n")
            if len(lines) > 2:
                # Remove first line (```language) and last line (```)
                formatted_response = "\n".join(lines[1:-1]).strip()
        
        logger.info(f"_format_api_response: generated response preview={formatted_response[:200]}{'...' if len(formatted_response) > 200 else ''}")
        return formatted_response
        
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for token limit errors
        if any(keyword in error_str for keyword in ["token", "context_length_exceeded", "maximum context", "too long"]):
            logger.error(f"Token limit exceeded in _format_api_response: {str(e)}")
            # Return a simplified message with the raw API result status
            status = api_result.get("status", "unknown")
            if status == "success":
                return (
                    f"✅ **Operation Completed**\n\n"
                    f"The {action.replace('_', ' ')} operation completed successfully, but the response was too large to format.\n\n"
                    f"**Raw status**: {status}"
                )
            else:
                return (
                    f"⚠️ **Operation Status**\n\n"
                    f"The {action.replace('_', ' ')} operation status: {status}\n\n"
                    f"Response details were too large to format. Check logs for more information."
                )
        
        # For other errors, log and return a generic error message
        logger.error(f"Error formatting API response: {str(e)}", exc_info=True)
        return (
            f"⚠️ **Formatting Error**\n\n"
            f"The operation completed, but there was an error formatting the response.\n\n"
            f"**Technical details**: {str(e)}"
        )


# ── Main entry point ──────────────────────────────────────────────────


def generate_chat_response(user_input: str, files: list = None) -> str:
    """
    Generate a chat response.

    Flow:
    1. Mask PII in user input & files to protect personal information
    2. LLM classifies the user's intent into one of four actions.
    3. If the action needs Slack / GitHub and those aren't connected,
       return a message asking the user to connect them.
    4. If prerequisites are met, call the backend API.
    5. Feed the API result back to the LLM for a human-friendly summary.
    6. For chat_only, fall through to a regular LLM conversation.
    """
    try:
        # STEP 1A — Concatenate files with markers BEFORE masking
        logger.info("generate_chat_response: Step 1 - concatenating files and masking PII")
        from services.api_client import mask_message
        
        combined_files_text = ""
        if files:
            file_sections = []
            for file_info in files:
                try:
                    file_content = file_info["content"].decode("utf-8", errors="replace")
                    file_sections.append(
                        f"--- FILE: {file_info['name']} ({file_info['size']} bytes) ---\n"
                        f"{file_content}\n"
                        f"--- END FILE: {file_info['name']} ---"
                    )
                except Exception as e:
                    logger.error(f"Error decoding file '{file_info['name']}': {e}")
                    file_sections.append(f"[Error reading file: {file_info['name']}]")
            
            combined_files_text = "\n\n".join(file_sections)
        
        # STEP 1B — Mask user input (ONE API CALL)
        mask_result = mask_message(user_input)
        masked_input = mask_result.get("masked_text", user_input)
        is_masked_input = mask_result.get("is_masked", False)
        
        # STEP 1C — Mask combined files (ONE API CALL)
        masked_files_text = ""
        is_masked_files = True
        if combined_files_text:
            files_mask_result = mask_message(combined_files_text)
            masked_files_text = files_mask_result.get("masked_text", combined_files_text)
            is_masked_files = files_mask_result.get("is_masked", False)
        
        # Check if masking succeeded
        if not is_masked_input or (combined_files_text and not is_masked_files):
            error_detail = mask_result.get("error", "Unknown masking error") if not is_masked_input else files_mask_result.get("error", "Unknown masking error")
            logger.error(f"PII masking failed: {error_detail}")
            return (
                "⚠️ **Unable to Process Message**\n\n"
                "PII masking service is currently unavailable. Your message could not be processed "
                "to protect personal information from being sent to the AI system.\n\n"
                f"**Technical details**: {error_detail}\n\n"
                "Please try again in a moment, or contact support if the issue persists."
            )
        
        logger.info("User input and files masked successfully")
        logger.info(f"[ORIGINAL INPUT]\n{user_input}\n\n[MASKED INPUT]\n{masked_input}")
        if combined_files_text:
            logger.info(f"[COMBINED FILES LENGTH] {len(combined_files_text)} chars → [MASKED] {len(masked_files_text)} chars")
        
        # Store masked version in the last user message for history context
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages[-1]["masked_content"] = masked_input
            if masked_files_text:
                st.session_state.messages[-1]["masked_files_text"] = masked_files_text
        
        # Use masked content for all subsequent operations
        processed_input = masked_input
        processed_files_text = masked_files_text
        
        # STEP 2 — classify intent with conversation history for context
        logger.info("generate_chat_response: STEP 2 - classifying intent")
        history = _build_history_messages()
        intent = _classify_intent(processed_input, files, history)  # Pass original files for file list
        action = intent["action"]
        parameters = intent["parameters"]
        
        # Check if we hit a token limit error during classification
        if action == "error" and intent.get("error_type") == "token_limit":
            logger.warning("Token limit exceeded during intent classification")
            return (
                "⚠️ **Context Too Large**\n\n"
                "The conversation history and uploaded files are too large to process. "
                "This can happen when many large files have been uploaded.\n\n"
                "**Suggestions:**\n"
                "- Try starting a new conversation by refreshing this page\n"
                "- Upload smaller or fewer files\n"
                "- Summarize your question more concisely"
            )

        # STEP 3 — check prerequisites
        if action != "chat_only":
            logger.info(f"generate_chat_response: STEP 3 - checking prerequisites for action={action}")
            prereq_msg = _check_prerequisites(action)
            if prereq_msg:
                logger.info(f"generate_chat_response: prerequisites not met, returning error message={prereq_msg}")
                return prereq_msg

        # STEP 4 — execute API action (if any)
        logger.info(f"generate_chat_response: STEP 4 - executing action={action}")
        api_result = _execute_action(action, parameters, processed_input, processed_files_text)

        if api_result is not None:
            # STEP 5 — LLM summarises the API result (use masked input and history for context)
            logger.info(f"generate_chat_response: STEP 5 - formatting API response for action={action}, response={json.dumps(api_result, indent=2, default=str)}")
            return _format_api_response(processed_input, action, api_result, history)

        # STEP 6 — chat_only: regular conversation (use masked input and files)
        logger.info("generate_chat_response: STEP 6 - entering chat_only conversation mode")
        from langchain_core.messages import SystemMessage, HumanMessage
        
        client = _get_llm_client()
        system_prompt = _build_system_prompt()
        logger.info(f"generate_chat_response: using {len(history)} messages from history")

        # Combine masked input with masked file text for chat
        user_text = processed_input
        if processed_files_text:
            user_text = f"{processed_input}\n\n{processed_files_text}"

        messages = [SystemMessage(content=system_prompt)]

        # Add history
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(SystemMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=user_text))

        try:
            response = client.invoke(messages)
            return response.content
        except Exception as llm_error:
            error_str = str(llm_error).lower()
            
            # Check for token limit errors
            if any(keyword in error_str for keyword in ["token", "context_length_exceeded", "maximum context", "too long"]):
                logger.error(f"Token limit exceeded in chat_only mode: {str(llm_error)}")
                return (
                    "⚠️ **Context Too Large**\n\n"
                    "The conversation history and uploaded files are too large to process. "
                    "This can happen when many large files have been uploaded.\n\n"
                    "**Suggestions:**\n"
                    "- Try starting a new conversation\n"
                    "- Upload smaller or fewer files\n"
                    "- Summarize your question more concisely"
                )
            # Re-raise other errors to be caught by outer exception handler
            raise

    except Exception as e:
        error_str = str(e).lower()
        
        # Check for token limit errors
        if any(keyword in error_str for keyword in ["token", "context_length_exceeded", "maximum context", "too long"]):
            logger.error(f"Token limit exceeded: {str(e)}")
            return (
                "⚠️ **Context Too Large**\n\n"
                "The conversation history and uploaded files are too large to process. "
                "This can happen when many large files have been uploaded.\n\n"
                "**Suggestions:**\n"
                "- Try starting a new conversation\n"
                "- Upload smaller or fewer files\n"
                "- Summarize your question more concisely"
            )
        logger.error(f"generate_chat_response: ERROR - {str(e)}", exc_info=True)
        return f"Encountered an error generating a response: {str(e)}"
