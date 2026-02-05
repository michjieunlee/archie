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
    messages: list[SlackMessage]
    metadata: dict = {}

    @property
    def threads_expanded(self) -> bool:
        """Check if threads were expanded."""
        return self.metadata.get("threads_expanded", False)

    @property
    def participant_count(self) -> int:
        """Count unique participants."""
        return len(set(msg.user_id for msg in self.messages))

    @property
    def message_count(self) -> int:
        """Count total messages."""
        return len(self.messages)
