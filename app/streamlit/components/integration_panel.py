"""
Integration panel component for GitHub, Slack, and Teams configurations.
"""
import streamlit as st
from utils.validators import validate_github_url, validate_github_token


def render_integration_buttons():
    """
    Render the three integration buttons on the left side.
    """
    with st.sidebar:
        st.markdown("### Integrations")

        # GitHub button
        # st.caption("GitHub")
        if st.button("GitHub", key="github_btn", use_container_width=True,
                    type="primary" if st.session_state.active_integration == "github" else "secondary"):
            if st.session_state.active_integration == "github":
                st.session_state.active_integration = None
            else:
                st.session_state.active_integration = "github"
            st.rerun()

        # Slack button
        # st.caption("Slack")
        if st.button("Slack", key="slack_btn", use_container_width=True,
                    type="primary" if st.session_state.active_integration == "slack" else "secondary"):
            if st.session_state.active_integration == "slack":
                st.session_state.active_integration = None
            else:
                st.session_state.active_integration = "slack"
            st.rerun()

        # Teams button
        # st.caption("Teams")
        if st.button("Teams", key="teams_btn", use_container_width=True,
                    type="primary" if st.session_state.active_integration == "teams" else "secondary"):
            if st.session_state.active_integration == "teams":
                st.session_state.active_integration = None
            else:
                st.session_state.active_integration = "teams"
            st.rerun()


def render_integration_panel():
    """
    Render the configuration panel based on the active integration.
    """
    active = st.session_state.active_integration

    if not active:
        return

    # Create a container in the sidebar for the config panel
    with st.sidebar:
        st.divider()

        if active == "github":
            render_github_config()
        elif active == "slack":
            render_slack_config()
        elif active == "teams":
            render_teams_config()


def render_github_config():
    """
    Render GitHub configuration panel.
    """
    st.markdown("### GitHub Configuration")

    is_connected = st.session_state.get("github_connected", False)

    # Repository URL input
    github_url = st.text_input(
        "Repository URL",
        value=st.session_state.get("github_url", ""),
        placeholder="https://github.com/owner/repo",
        disabled=is_connected,
        key="github_url_input"
    )

    # # Validate URL
    # url_is_valid = False
    # if github_url and not is_connected:
    #     url_is_valid, _ = validate_github_url(github_url)
    #     if url_is_valid:
    #         st.success("✓ Valid URL")
    #     else:
    #         st.error("✗ Invalid URL format")

    # Personal Access Token input
    if is_connected:
        # Show masked token
        st.text_input(
            "Personal Access Token",
            value="●" * 40,
            disabled=True,
            key="github_token_display"
        )
    else:
        github_token = st.text_input(
            "Personal Access Token",
            value=st.session_state.get("github_token", ""),
            placeholder="ghp_xxxxxxxxxxxxx",
            type="password",
            key="github_token_input"
        )

    # # Validate token
    # token_is_valid = False
    # if not is_connected and github_token:
    #     token_is_valid, _ = validate_github_token(github_token)
    #     if token_is_valid:
    #         st.success("✓ Valid token")
    #     else:
    #         st.error("✗ Invalid token format")

    # Update session state
    if not is_connected:
        st.session_state.github_url = github_url
        if 'github_token_input' in st.session_state:
            st.session_state.github_token = st.session_state.github_token_input

    # Connect/Disconnect button
    if is_connected:
        if st.button("🔌 Disconnect", key="github_disconnect", use_container_width=True, type="secondary"):
            # Clear configuration
            st.session_state.github_connected = False
            st.session_state.github_url = ""
            st.session_state.github_token = ""
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Disconnected from GitHub."
            })
            st.rerun()
    else:
        connect_enabled = github_url and github_token
        if st.button("🔗 Connect", key="github_connect", use_container_width=True,
                    type="primary", disabled=not connect_enabled):
            # Set connected state
            st.session_state.github_connected = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Successfully connected to GitHub repository: `{github_url}`"
            })
            st.rerun()


def render_slack_config():
    """
    Render Slack configuration panel.
    """
    st.markdown("### Slack Configuration")

    is_connected = st.session_state.get("slack_connected", False)

    # Channel ID input
    slack_channel_id = st.text_input(
        "Channel ID",
        value=st.session_state.get("slack_channel_id", ""),
        placeholder="C01234ABCDE",
        disabled=is_connected,
        key="slack_channel_input"
    )

    # Simple validation (non-empty)
    channel_is_valid = bool(slack_channel_id and len(slack_channel_id) > 0)

    # if slack_channel_id and not is_connected:
    #     if channel_is_valid:
    #         st.success("✓ Channel ID entered")
    #     else:
    #         st.error("✗ Please enter a channel ID")

    # Update session state
    if not is_connected:
        st.session_state.slack_channel_id = slack_channel_id

    # Connect/Disconnect button
    if is_connected:
        if st.button("🔌 Disconnect", key="slack_disconnect", use_container_width=True, type="secondary"):
            # Clear configuration
            st.session_state.slack_connected = False
            st.session_state.slack_channel_id = ""
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Disconnected from Slack."
            })
            st.rerun()
    else:
        connect_enabled = channel_is_valid
        if st.button("🔗 Connect", key="slack_connect", use_container_width=True,
                    type="primary", disabled=not connect_enabled):
            # Set connected state
            st.session_state.slack_connected = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Successfully connected to Slack channel: `{slack_channel_id}`"
            })
            st.rerun()


def render_teams_config():
    """
    Render Teams configuration panel.
    """
    st.markdown("### Microsoft Teams Configuration")

    st.info("📢 **Available Soon!**")
    st.markdown("""
    Microsoft Teams integration is coming in a future update.
    """)
