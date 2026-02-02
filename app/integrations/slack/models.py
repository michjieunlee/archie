"""
Slack Data Models
Owner: ① Slack · GitHub Integration & Flow Owner
"""

from pydantic import BaseModel
from datetime import datetime


class SlackMessage(BaseModel):
    """Standardized Slack message."""

    ts: str  # Message timestamp (unique ID)
    user_id: str
    user_name: str | None = None
    text: str
    timestamp: datetime
    reactions: list[dict] = []
    attachments: list[dict] = []


class SlackThread(BaseModel):
    """Standardized Slack thread with all messages."""

    channel_id: str
    channel_name: str | None = None
    thread_ts: str
    permalink: str
    messages: list[SlackMessage]
    reply_count: int
    participant_count: int
