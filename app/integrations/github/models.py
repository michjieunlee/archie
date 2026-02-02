"""
GitHub Data Models
Owner: ① Slack · GitHub Integration & Flow Owner
"""

from pydantic import BaseModel
from enum import Enum


class KBCategory(str, Enum):
    """Knowledge base document categories."""

    TROUBLESHOOTING = "troubleshooting"
    DECISION = "decision"
    HOWTO = "howto"
    ARCHITECTURE = "architecture"
    ONBOARDING = "onboarding"


class PRMetadata(BaseModel):
    """PR metadata for knowledge base documents."""

    source_thread_url: str  # Original Slack thread
    category: KBCategory
    tags: list[str] = []
    auto_generated: bool = True
    ai_confidence_score: float | None = None  # 0.0 - 1.0
