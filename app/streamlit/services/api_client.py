"""
API client for Archie backend connections.
Currently uses mock validation; swap to real HTTP calls when backend is ready.
"""
from utils.validators import (
    validate_github_url,
    validate_github_token,
    extract_owner_repo_from_url,
)


def connect_github(url: str, token: str) -> dict[str, ]:
    """
    Verify GitHub connection by validating URL and token format.

    TODO: Replace with real HTTP call to POST /api/github/connect

    Returns:
        dict with keys: success (bool), message (str), repo_full_name (str|None)
    """
    url_valid, url_msg = validate_github_url(url)
    if not url_valid:
        return {"success": False, "message": url_msg, "repo_full_name": None}

    token_valid, token_msg = validate_github_token(token)
    if not token_valid:
        return {"success": False, "message": token_msg, "repo_full_name": None}

    # TODO: send API to backend and return True only when it succeeds
    owner, repo = extract_owner_repo_from_url(url)
    return {
        "success": True,
        "message": f"Successfully connected to {owner}/{repo}",
        "repo_full_name": f"{owner}/{repo}",
    }


def connect_slack(channel_id: str) -> dict:
    """
    Verify Slack connection by validating channel ID format.

    TODO: Replace with real HTTP call to POST /api/slack/connect

    Returns:
        dict with keys: success (bool), message (str), channel_name (str|None)
    """
    channel_id = channel_id.strip()

    if not channel_id:
        return {
            "success": False,
            "message": "Channel ID is required.",
            "channel_name": None,
        }

    if not channel_id[0].isalpha() or len(channel_id) < 5:
        return {
            "success": False,
            "message": "Invalid Channel ID format. Expected format: C01234ABCDE",
            "channel_name": None,
        }

    # TODO: send API to backend and return True only when it succeeds
    return {
        "success": True,
        "message": f"Connected to channel {channel_id}",
        "channel_name": channel_id,
    }


def disconnect_github(url: str) -> dict:
    """
    Disconnect from a GitHub repository.

    TODO: Replace with real HTTP call to POST /api/github/disconnect

    Returns:
        dict with keys: success (bool), message (str)
    """
    # TODO: send API to backend to clean up server-side state
    return {
        "success": True,
        "message": f"Disconnected from GitHub repository",
    }


def disconnect_slack(channel_id: str) -> dict:
    """
    Disconnect from a Slack channel.

    TODO: Replace with real HTTP call to POST /api/slack/disconnect

    Returns:
        dict with keys: success (bool), message (str)
    """
    # TODO: send API to backend to clean up server-side state
    return {
        "success": True,
        "message": f"Disconnected from Slack channel",
    }
