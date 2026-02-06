"""
Knowledge Base Models

This module defines the data models for knowledge articles and related metadata.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class KBCategory(str, Enum):
    """Knowledge Base article categories."""

    TROUBLESHOOTING = "troubleshooting"  # Problem-solving guides
    PROCESSES = "processes"  # Standard procedures
    DECISIONS = "decisions"  # Technical choices and rationale


class ExtractionMetadata(BaseModel):
    """
    Metadata about the extraction source and process.
    """

    source_type: str = Field(
        ..., description="Type of source (e.g., 'slack_thread', 'github_pr')"
    )
    source_id: str = Field(..., description="Unique identifier of the source")
    channel_id: Optional[str] = Field(None, description="Slack channel ID")
    channel_name: Optional[str] = Field(None, description="Slack channel name")
    participants: List[str] = Field(
        default_factory=list, description="User IDs of participants"
    )
    message_count: int = Field(0, description="Number of messages in source thread")
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When extraction occurred",
    )
    extractor_version: str = Field(
        "1.0.0", description="Version of extraction logic used"
    )


# Category-specific extraction models matching template fields


class TroubleshootingExtraction(BaseModel):
    """Extraction output for troubleshooting articles."""

    title: str = Field(..., description="Clear, descriptive title")
    tags: List[str] = Field(..., description="3-5 relevant tags")

    problem_description: str = Field(
        ..., description="Clear description of the problem"
    )
    system_info: str = Field(..., description="System/platform information")
    version_info: str = Field(..., description="Version information")
    environment: str = Field(..., description="Environment (dev/staging/prod)")
    symptoms: str = Field(..., description="Observable symptoms of the problem")
    root_cause: str = Field(..., description="Identified root cause")
    solution_steps: str = Field(..., description="Step-by-step solution")
    prevention_measures: str = Field(..., description="How to prevent this issue")
    related_links: str = Field(..., description="Related issues or documentation")

    ai_confidence: float = Field(..., description="AI confidence score (0.0 to 1.0)")
    ai_reasoning: str = Field(
        ..., description="Why this is KB-worthy and confidence explanation"
    )


class ProcessExtraction(BaseModel):
    """Extraction output for process articles."""

    title: str = Field(..., description="Clear, descriptive title")
    tags: List[str] = Field(..., description="3-5 relevant tags")

    process_overview: str = Field(..., description="Overview of the process")
    prerequisites: str = Field(..., description="Prerequisites for the process")
    process_steps: str = Field(..., description="Step-by-step process instructions")
    validation_steps: str = Field(..., description="How to validate success")
    common_issues: str = Field(..., description="Common issues and troubleshooting")
    related_processes: str = Field(..., description="Related processes")

    ai_confidence: float = Field(..., description="AI confidence score (0.0 to 1.0)")
    ai_reasoning: str = Field(
        ..., description="Why this is KB-worthy and confidence explanation"
    )


class DecisionExtraction(BaseModel):
    """Extraction output for decision articles."""

    title: str = Field(..., description="Clear, descriptive title")
    tags: List[str] = Field(..., description="3-5 relevant tags")

    decision_context: str = Field(
        ..., description="Context and background for the decision"
    )
    decision_made: str = Field(..., description="The decision that was made")
    reasoning: str = Field(..., description="Rationale behind the decision")
    alternatives: str = Field(..., description="Alternatives that were considered")
    positive_consequences: str = Field(
        ..., description="Benefits and positive outcomes"
    )
    negative_consequences: str = Field(
        ..., description="Trade-offs and potential downsides"
    )
    implementation_notes: str = Field(..., description="How to implement this decision")

    ai_confidence: float = Field(..., description="AI confidence score (0.0 to 1.0)")
    ai_reasoning: str = Field(
        ..., description="Why this is KB-worthy and confidence explanation"
    )


# Union type for extraction output

KnowledgeExtractionOutput = Union[
    TroubleshootingExtraction, ProcessExtraction, DecisionExtraction
]


class KnowledgeArticle(BaseModel):
    """
    A structured knowledge base article extracted from conversations.
    Complete model including LLM output + system-generated metadata.
    """

    # Core extraction data (from one of the category-specific models)
    extraction_output: KnowledgeExtractionOutput = Field(
        ..., description="Category-specific extraction output"
    )

    # Category (derived from extraction output)
    category: KBCategory = Field(..., description="Article category")

    # Extraction metadata (system-generated)
    extraction_metadata: ExtractionMetadata = Field(
        ..., description="Metadata about the extraction"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When article was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When article was last updated",
    )

    # KB repository info (populated when stored)
    kb_file_path: Optional[str] = Field(
        None, description="Path in KB repository where article is stored"
    )
    kb_commit_sha: Optional[str] = Field(
        None, description="Git commit SHA when stored in KB"
    )

    # Review and approval
    review_status: str = Field(
        "pending", description="Status: pending, approved, rejected"
    )
    reviewed_by: Optional[str] = Field(None, description="User who reviewed")
    reviewed_at: Optional[datetime] = Field(None, description="When reviewed")

    @property
    def title(self) -> str:
        """Get title from extraction output."""
        return self.extraction_output.title

    @property
    def tags(self) -> List[str]:
        """Get tags from extraction output."""
        return self.extraction_output.tags

    @property
    def ai_confidence(self) -> float:
        """Get AI confidence from extraction output."""
        return self.extraction_output.ai_confidence

    @property
    def ai_reasoning(self) -> str:
        """Get AI reasoning from extraction output."""
        return self.extraction_output.ai_reasoning

    def to_markdown(self) -> str:
        """
        Convert the article to markdown using template filling.
        This will be handled by kb_generator.py using actual template files.

        Returns:
            Markdown formatted article with YAML frontmatter
        """
        # This method will be replaced by template-based generation in kb_generator
        raise NotImplementedError("Use kb_generator.generate_markdown() instead")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert article to dictionary.

        Returns:
            Dictionary representation
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeArticle":
        """
        Create article from dictionary.

        Args:
            data: Dictionary with article data

        Returns:
            KnowledgeArticle instance
        """
        return cls(**data)


class KnowledgeSearchResult(BaseModel):
    """
    Result from knowledge base search.
    """

    article: KnowledgeArticle
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    matched_fields: List[str] = Field(
        default_factory=list, description="Fields that matched the search"
    )
    snippet: Optional[str] = Field(None, description="Relevant snippet from article")


class KnowledgeStats(BaseModel):
    """
    Statistics about the knowledge base.
    """

    total_articles: int = Field(0, description="Total number of articles")
    by_tag: Dict[str, int] = Field(
        default_factory=dict, description="Article count by tag"
    )
    by_channel: Dict[str, int] = Field(
        default_factory=dict, description="Article count by source channel"
    )
    recent_extractions: int = Field(0, description="Extractions in the last 7 days")
    pending_review: int = Field(0, description="Articles pending review")
