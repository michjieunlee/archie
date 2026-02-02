"""
Slack API Client
Owner: ① Slack · GitHub Integration & Flow Owner

Responsibilities:
- conversations.history: Fetch channel messages
- conversations.replies: Fetch thread replies
- Standardize input data (JSON)
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import get_settings
from app.integrations.slack.models import SlackThread, SlackMessage


class SlackClient:
    """Slack API client wrapper."""

    def __init__(self):
        settings = get_settings()
        self.client = WebClient(token=settings.slack_bot_token)

    async def get_thread_messages(
        self, channel_id: str, thread_ts: str
    ) -> SlackThread:
        """
        Fetch all messages in a thread.

        Args:
            channel_id: Slack channel ID (e.g., C123ABC456)
            thread_ts: Thread timestamp (e.g., 1234567890.123456)

        Returns:
            SlackThread with all messages
        """
        # TODO: Implement conversations.replies API call
        # https://api.slack.com/methods/conversations.replies
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> dict:
        """Get channel information."""
        # TODO: Implement conversations.info API call
        raise NotImplementedError

    async def get_user_info(self, user_id: str) -> dict:
        """Get user information (for display name resolution)."""
        # TODO: Implement users.info API call
        raise NotImplementedError
