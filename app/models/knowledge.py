"""
Knowledge Document Model

Standard data structure for KB documents
"""

from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """KB document lifecycle status."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class KnowledgeDocument(BaseModel):
    """Knowledge Base document."""

    id: str | None = None
    title: str
    content: str  # Markdown content
    category: str
    tags: list[str] = []
    status: DocumentStatus = DocumentStatus.DRAFT

    # Source tracking
    source_thread_url: str
    source_type: str  # slack, teams

    # AI metadata
    ai_confidence_score: float
    ai_reasoning: str

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # GitHub tracking
    pr_number: int | None = None
    pr_url: str | None = None
    file_path: str | None = None
