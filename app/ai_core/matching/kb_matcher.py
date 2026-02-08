"""
Knowledge Base Matcher
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Prompt 2: KB Matching (create / update / ignore)
- Compare with existing KB documents
- Determine New vs Update
"""

import logging
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.knowledge import KnowledgeArticle

logger = logging.getLogger(__name__)


class MatchAction(str, Enum):
    """Action to take for KB candidate."""

    CREATE = "create"  # Create new document
    UPDATE = "update"  # Update existing document
    IGNORE = "ignore"  # Do not add to KB


class MatchResult(BaseModel):
    """Result of KB matching."""

    action: MatchAction = Field(..., description="Action to take")
    confidence_score: float = Field(..., description="Confidence score (0.0-1.0)")
    reasoning: str = Field(..., description="AI's reasoning for the decision")

    # For UPDATE action
    matched_document_path: Optional[str] = Field(
        None, description="Path of matched document"
    )
    matched_document_title: Optional[str] = Field(
        None, description="Title of matched document"
    )
    similarity_score: Optional[float] = Field(
        None, description="Similarity score with matched document"
    )

    # For CREATE action
    suggested_path: Optional[str] = Field(None, description="Suggested file path")
    suggested_category: Optional[str] = Field(None, description="Suggested category")


class KBMatcher:
    """
    Matches KB candidates against existing knowledge base.

    This is a stub implementation that always returns CREATE action.
    Full implementation with LLM-based matching is TODO.
    """

    def __init__(self, kb_index_path: Optional[str] = None):
        """
        Args:
            kb_index_path: Path to KB index/embeddings for similarity search
        """
        self.kb_index_path = kb_index_path
        logger.info("KBMatcher initialized (stub implementation)")

    async def match(
        self,
        kb_article: KnowledgeArticle,
        existing_kb_docs: Optional[List[dict]] = None,
    ) -> MatchResult:
        """
        Determine if candidate should create new doc or update existing.

        STUB IMPLEMENTATION: Always returns CREATE action.

        TODO: Implement full matching logic:
        1. Topic similarity with existing documents
        2. Whether new information is valuable enough to add to existing docs
        3. Whether it's valuable as an independent new document

        Args:
            kb_article: Extracted KB article
            existing_kb_docs: List of existing KB documents metadata (optional)

        Returns:
            MatchResult with action and reasoning
        """
        logger.info(
            f"Matching KB article: {kb_article.title} (stub - always returns CREATE)"
        )

        # Stub implementation - always create new document
        suggested_path = f"{kb_article.category.value}/{kb_article.title.lower().replace(' ', '-')}.md"

        return MatchResult(
            action=MatchAction.CREATE,
            confidence_score=1.0,
            reasoning="Stub implementation: Always creates new document. Full matching logic not yet implemented.",
            suggested_path=suggested_path,
            suggested_category=kb_article.category.value,
        )

    async def get_similar_documents(
        self, kb_article: KnowledgeArticle, top_k: int = 5
    ) -> List[dict]:
        """
        Find similar existing KB documents.

        STUB IMPLEMENTATION: Returns empty list.

        TODO: Implement similarity search using embeddings or LLM.

        Args:
            kb_article: KB article to find similar documents for
            top_k: Number of similar documents to return

        Returns:
            List of similar documents (empty in stub implementation)
        """
        logger.info(f"Getting similar documents for: {kb_article.title} (stub)")
        return []
