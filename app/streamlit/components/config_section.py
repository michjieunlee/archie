"""
Configuration section component for the Streamlit app.
Displays GitHub token and repository configuration on the left side.
"""
import streamlit as st
from utils.validators import validate_github_url, validate_github_token


def render_config_section():
    """
    Render the configuration section with GitHub settings.
    """
    # Help expander
    with st.expander("ℹ️  Help & Information"):
        st.markdown("""
        **How to use Archie:**
        
        1. **Chat Freely:** You can ask questions and chat with Archie anytime.
        
        2. **Process Repositories:** To analyze GitHub repositories:
           - Enter a GitHub repository URL (format: `https://github.com/owner/repo`)
           - Provide your GitHub personal access token
           - Click "Start Processing" or mention the repository in chat
        
        3. **GitHub Token:** 
           - Generate a token at [github.com/settings/tokens](https://github.com/settings/tokens)
           - Required format: `ghp_...` or `github_pat_...`
           - Needs `repo` scope for private repositories
                    
        4. **Slack Token:**
        """)
    
    st.divider()
    
    # GitHub configuration
    st.markdown("#### ⚙️ GitHub Configuration")
    
    # Custom CSS for input validation styling with icons inside textbox
    st.markdown("""
        <style>
        /* Valid input styling - green border */
        .input-valid input {
            border-color: #28a745 !important;
            padding-right: 2.5rem !important;
        }
        
        /* Invalid input styling - red border */
        .input-invalid input {
            border-color: #dc3545 !important;
            padding-right: 2.5rem !important;
        }
        
        /* Remove colored outline on focus - use default blue */
        .stTextInput input:focus {
            border-color: #80bdff !important;
            box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25) !important;
            outline: none !important;
        }
        
        /* Validation icon inside textbox */
        .validation-icon-inline {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.2rem;
            font-weight: bold;
            pointer-events: none;
            z-index: 1000;
        }
        .validation-icon-inline.valid {
            color: #28a745;
        }
        .validation-icon-inline.invalid {
            color: #dc3545;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # GitHub Repository URL with inline validation icon
    # Make read-only if connected
    is_github_connected = st.session_state.get("github_connected", False)
    
    github_url = st.text_input(
        "Repository URL",
        value=st.session_state.get("github_url", ""),
        placeholder="https://github.com/owner/repo",
        help="Enter the full GitHub repository URL" if not is_github_connected else "GitHub repository URL (connected)",
        disabled=st.session_state.get("processing", False) or is_github_connected,
        key="url_input"
    )
    
    # Validate URL and show icon inside textbox (only when not connected)
    url_is_valid = False
    if github_url and not st.session_state.get("github_connected", False):
        url_is_valid, url_message = validate_github_url(github_url)
        icon_class = "valid" if url_is_valid else "invalid"
        icon_symbol = "✓" if url_is_valid else "✗"
        
        st.markdown(f"""
            <style>
            div[data-testid="stTextInput"]:has(input[aria-label="Repository URL"]) input {{
                {'border-color: #28a745 !important; padding-right: 2.5rem !important;' if url_is_valid else 'border-color: #dc3545 !important; padding-right: 2.5rem !important;'}
            }}
            </style>
            <div style="position: relative; margin-top: -3.5rem; height: 0; pointer-events: none;">
                <div class="validation-icon-inline {icon_class}" style="position: absolute; right: 15px; top: 1.85rem;">
                    {icon_symbol}
                </div>
            </div>
        """, unsafe_allow_html=True)
    elif github_url and st.session_state.get("github_connected", False):
        # URL is valid if we're connected
        url_is_valid = True
    
    # GitHub Token with inline validation icon
    # Show masked value if connected, otherwise show actual input
    
    if is_github_connected:
        # Display masked token value with black circles (read-only display)
        token_display = "●" * 40 if st.session_state.get("github_token", "") else ""
        st.text_input(
            "Personal Access Token",
            value=token_display,
            placeholder="ghp_xxxxxxxxxxxxx",
            help="Your GitHub personal access token (connected and masked)",
            disabled=True,
            key="token_display"
        )
        
        # Add CSS to make the masked token display in black color
        st.markdown("""
            <style>
            div[data-testid="stTextInput"]:has(input[aria-label="Personal Access Token"]) input[disabled] {
                color: #000000 !important;
                -webkit-text-security: disc !important;
                font-weight: bold !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        github_token = st.session_state.get("github_token", "")
    else:
        # Editable token input when not connected
        github_token = st.text_input(
            "Personal Access Token",
            value=st.session_state.get("github_token", ""),
            placeholder="ghp_xxxxxxxxxxxxx",
            help="Your GitHub personal access token",
            disabled=st.session_state.get("processing", False),
            key="token_input"
        )
    
    # Validate token and show icon inside textbox (only when not connected)
    token_is_valid = False
    if github_token and not is_github_connected:
        token_is_valid, token_message = validate_github_token(github_token)
        icon_class = "valid" if token_is_valid else "invalid"
        icon_symbol = "✓" if token_is_valid else "✗"
        
        st.markdown(f"""
            <style>
            div[data-testid="stTextInput"]:has(input[aria-label="Personal Access Token"]) input {{
                {'border-color: #28a745 !important; padding-right: 2.5rem !important;' if token_is_valid else 'border-color: #dc3545 !important; padding-right: 2.5rem !important;'}
            }}
            </style>
            <div style="position: relative; margin-top: -3.5rem; height: 0; pointer-events: none;">
                <div class="validation-icon-inline {icon_class}" style="position: absolute; right: 15px; top: 1.85rem;">
                    {icon_symbol}
                </div>
            </div>
        """, unsafe_allow_html=True)
    elif github_token and is_github_connected:
        # Token is valid if we're connected
        token_is_valid = True
    
    # Update session state only if not connected
    if not is_github_connected:
        st.session_state.github_url = github_url
        st.session_state.github_token = github_token
    
    # Connect/Disconnect buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if is_github_connected:
            # Show "Disconnect" button when connected
            if st.button(
                "🔌 Disconnect GitHub",
                type="secondary",
                use_container_width=True
            ):
                # Store the URL for the message before clearing
                disconnected_url = st.session_state.get('github_url', '')
                
                # Clear the configuration
                st.session_state.github_connected = False
                st.session_state.github_url = ""
                st.session_state.github_token = ""
                
                # Clear widget keys to reset text inputs
                if "url_input" in st.session_state:
                    del st.session_state.url_input
                if "token_input" in st.session_state:
                    del st.session_state.token_input
                if "token_display" in st.session_state:
                    del st.session_state.token_display
                
                # Add disconnect message to chat
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Disconnected from GitHub repository: `{disconnected_url}`"
                })
                st.success("✓ GitHub disconnected and configuration cleared")
                st.rerun()
        else:
            # Show "Connect GitHub" button when not connected
            connect_disabled = (
                not github_url or 
                not github_token or
                not url_is_valid or
                not token_is_valid
            )
            
            if st.button(
                "🔗 Connect GitHub",
                disabled=connect_disabled,
                type="primary",
                use_container_width=True
            ):
                # Set connected state and show success message
                st.session_state.github_connected = True
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Successfully connected to GitHub repository: `{github_url}`"
                })
                st.success("✓ GitHub connected successfully!")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Config", use_container_width=True):
            st.session_state.github_url = ""
            st.session_state.github_token = ""
            st.session_state.github_connected = False
            # Also clear the widget keys to reset the text inputs
            if "url_input" in st.session_state:
                del st.session_state.url_input
            if "token_input" in st.session_state:
                del st.session_state.token_input
            if "token_display" in st.session_state:
                del st.session_state.token_display
            st.rerun()
    
    # Connection status
    if is_github_connected:
        st.success(f"✓ Connected to: `{st.session_state.get('github_url', '')}`")
    
    st.divider()
