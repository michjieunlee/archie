"""
API Response Models

Pydantic models for consistent API response structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class KBActionType(str, Enum):
    """Type of action taken on KB."""

    CREATE = "create"
    UPDATE = "update"
    IGNORE = "ignore"
    ERROR = "error"


class KBProcessingResponse(BaseModel):
    """
    Response model for KB processing endpoints.
    Used by both process_slack_messages and process_text_input.
    """

    status: str = Field(..., description="Status: success or error")
    action: KBActionType = Field(
        ..., description="Action taken: create, update, ignore, or error"
    )
    reason: Optional[str] = Field(
        None, description="Reason for the action (especially for ignore/error)"
    )

    # KB article information (if created/updated)
    kb_article_title: Optional[str] = Field(None, description="Title of the KB article")
    kb_category: Optional[str] = Field(None, description="Category of the KB article")
    ai_confidence: Optional[float] = Field(
        None, description="AI confidence score (0.0-1.0)"
    )
    ai_reasoning: Optional[str] = Field(
        None, description="AI reasoning for the extraction"
    )

    # GitHub PR information (if created)
    pr_url: Optional[str] = Field(None, description="URL of the created GitHub PR")
    file_path: Optional[str] = Field(
        None, description="Path of the KB file in repository"
    )

    # Processing metadata
    messages_fetched: Optional[int] = Field(
        None, description="Number of messages processed (for Slack)"
    )
    text_length: Optional[int] = Field(
        None, description="Length of text processed (for text input)"
    )


class KBSearchSource(BaseModel):
    """Individual search result source."""

    title: str = Field(..., description="Article title")
    category: str = Field(..., description="Article category")
    excerpt: str = Field(..., description="Relevant excerpt from the article")
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")
    file_path: str = Field(..., description="Path to the file in KB repository")
    github_url: str = Field(..., description="GitHub URL to view the article")


class KBQueryResponse(BaseModel):
    """
    Response model for KB query endpoint (Q&A).
    """

    status: str = Field(..., description="Status: success or error")
    query: str = Field(..., description="The original query")
    answer: Optional[str] = Field(
        None, description="Natural language answer generated from KB"
    )
    sources: List[KBSearchSource] = Field(
        default_factory=list, description="Relevant KB articles"
    )
    total_sources: int = Field(0, description="Total number of relevant sources found")
    reason: Optional[str] = Field(None, description="Error reason if status is error")
