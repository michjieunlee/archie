
from fastapi import APIRouter
from pydantic import BaseModel
from github import Github
from github.GithubException import GithubException, BadCredentialsException
from typing import Optional
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.services.credential_store import (
    set_credential,
    clear_credentials,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── GitHub ──────────────────────────────────────────────

class GitHubConnectRequest(BaseModel):
    """Credentials sent from the UI to store on the backend."""

    repo_url: str  # https://github.com/owner/repo
    token: str  # Personal access token (ghp_… or github_pat_…)


class GitHubConnectResponse(BaseModel):
    success: bool
    message: str
    repo_full_name: Optional[str] = None


@router.post("/github/connect", response_model=GitHubConnectResponse)
async def connect_github(request: GitHubConnectRequest):
    """
    Store GitHub credentials and validate the connection.

    The token is kept in the in-memory credential store so that
    downstream services (GitHubClient, PR creation) can use it.
    """
    try:
        # Validate token against GitHub API
        try:
            gh_client = Github(request.token)
            # Test token by getting authenticated user
            user = gh_client.get_user()
            user.login  # Force API call
            logger.info(f"Token validated for GitHub user: {user.login}")
        except BadCredentialsException:
            return GitHubConnectResponse(
                success=False,
                message="Invalid GitHub token. Please check your personal access token and try again.",
            )
        except GithubException as gh_err:
            logger.error(f"GitHub API error during token validation: {gh_err}")
            return GitHubConnectResponse(
                success=False,
                message=f"GitHub API error: {gh_err.data.get('message', str(gh_err))}",
            )

        # Parse owner/repo from URL
        parts = request.repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return GitHubConnectResponse(
                success=False, message="Invalid repository URL format"
            )
        owner, repo = parts[-2], parts[-1]

        # Verify repository access
        try:
            repo_obj = gh_client.get_repo(f"{owner}/{repo}")
            repo_obj.name  # Force API call to verify access
            logger.info(f"Verified access to repository: {owner}/{repo}")
        except GithubException as gh_err:
            if gh_err.status == 404:
                return GitHubConnectResponse(
                    success=False,
                    message=f"Repository '{owner}/{repo}' not found or token doesn't have access to it.",
                )
            logger.error(f"GitHub API error during repository verification: {gh_err}")
            return GitHubConnectResponse(
                success=False,
                message=f"Cannot access repository: {gh_err.data.get('message', str(gh_err))}",
            )

        # Store credentials
        set_credential("github_token", request.token)
        set_credential("github_repo_owner", owner)
        set_credential("github_repo_name", repo)

        logger.info(f"GitHub credentials stored for {owner}/{repo}")

        return GitHubConnectResponse(
            success=True,
            message=f"Successfully connected to {owner}/{repo}",
            repo_full_name=f"{owner}/{repo}",
        )

    except Exception as e:
        logger.error(f"GitHub connect error: {e}")
        return GitHubConnectResponse(success=False, message=str(e))


@router.post("/github/disconnect", response_model=GitHubConnectResponse)
async def disconnect_github():
    """
    Remove stored GitHub credentials from the backend.
    """
    clear_credentials("github_")
    logger.info("GitHub credentials cleared")
    return GitHubConnectResponse(
        success=True, message="Disconnected from GitHub repository"
    )


# ── Slack ──────────────────────────────────────────────

class SlackConnectRequest(BaseModel):
    """Credentials sent from the UI to store on the backend."""

    channel_id: str
    bot_token: Optional[str] = None  # Optional override for the .env token


class SlackConnectResponse(BaseModel):
    success: bool
    message: str
    channel_name: Optional[str] = None


@router.post("/slack/connect", response_model=SlackConnectResponse)
async def connect_slack(request: SlackConnectRequest):
    """
    Store Slack credentials and verify the channel is reachable.

    Stores the channel_id (and optional bot_token override) in the
    in-memory credential store, then attempts a small fetch to validate.
    """
    try:
        channel_id = request.channel_id.strip()
        if not channel_id:
            return SlackConnectResponse(
                success=False, message="Channel ID is required"
            )
        
        # Validate channel exists and bot has access
        try:
            settings = get_settings()
            bot_token = settings.slack_bot_token
            
            if not bot_token:
                return SlackConnectResponse(
                    success=False,
                    message="Slack bot token is not configured. Please provide a token or set SLACK_BOT_TOKEN in your environment.",
                )
            
            slack_client = WebClient(token=bot_token)
            # Validate channel exists and bot has access
            channel_info = slack_client.conversations_info(channel=channel_id)
            channel_name = channel_info["channel"]["name"]
            logger.info(f"Validated access to Slack channel: #{channel_name} ({channel_id})")
            
        except SlackApiError as slack_err:
            error_code = slack_err.response.get("error", "unknown_error")
            if error_code == "channel_not_found":
                return SlackConnectResponse(
                    success=False,
                    message=f"Channel '{channel_id}' not found. Please check the channel ID and ensure the bot is added to the channel.",
                )
            elif error_code == "invalid_auth":
                return SlackConnectResponse(
                    success=False,
                    message="Invalid Slack bot token. Please check your token and try again.",
                )
            elif error_code == "not_in_channel":
                return SlackConnectResponse(
                    success=False,
                    message=f"Bot is not a member of channel '{channel_id}'. Please add the bot to the channel first.",
                )
            else:
                logger.error(f"Slack API error during channel validation: {slack_err}")
                return SlackConnectResponse(
                    success=False,
                    message=f"Slack API error: {error_code}",
                )

        # Store credentials
        set_credential("slack_channel_id", channel_id)
        # if request.bot_token:
        #     set_credential("slack_bot_token", request.bot_token)

        logger.info(f"Slack credentials stored for channel {channel_id}")
        return SlackConnectResponse(
            success=True,
            message=f"Successfully connected to #{channel_name}",
            channel_name=channel_name,
        )

    except Exception as e:
        # Clear credentials on failure so we don't keep bad state
        clear_credentials("slack_")
        logger.error(f"Slack connect error: {e}")
        return SlackConnectResponse(
            success=False, message=f"Slack connection failed: {e}"
        )


@router.post("/slack/disconnect", response_model=SlackConnectResponse)
async def disconnect_slack():
    """
    Remove stored Slack credentials from the backend.
    """
    clear_credentials("slack_")
    logger.info("Slack credentials cleared")
    return SlackConnectResponse(
        success=True, message="Disconnected from Slack channel"
    )

