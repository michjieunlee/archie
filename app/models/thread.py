"""
Standardized Thread Model

Unified thread data structure regardless of input source (Slack, Teams, etc.)
"""

from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Source platform type."""

    SLACK = "slack"
    TEAMS = "teams"  # Future extension


class StandardizedMessage(BaseModel):
    """Platform-agnostic message format."""

    id: str
    author_id: str
    author_name: str | None = None  # May be masked
    content: str
    timestamp: datetime
    is_masked: bool = False
    metadata: dict = {}


class StandardizedThread(BaseModel):
    """Platform-agnostic thread format."""

    id: str
    source: SourceType
    source_url: str
    channel_id: str
    channel_name: str | None = None
    messages: list[StandardizedMessage]
    participant_count: int
    created_at: datetime
    last_activity_at: datetime
    metadata: dict = {}
