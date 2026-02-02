"""
Knowledge Base Matcher
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Prompt 2: KB Matching (create / update / ignore)
- Compare with existing KB documents
- Determine New vs Update
"""

from dataclasses import dataclass
from enum import Enum
from app.ai_core.extraction.kb_extractor import ExtractionResult


class MatchAction(str, Enum):
    """Action to take for KB candidate."""

    CREATE = "create"  # Create new document
    UPDATE = "update"  # Update existing document
    IGNORE = "ignore"  # Do not add to KB


@dataclass
class MatchResult:
    """Result of KB matching."""

    action: MatchAction
    confidence_score: float  # 0.0 - 1.0
    reasoning: str  # AI's reasoning

    # For UPDATE action
    matched_document_path: str | None = None
    matched_document_title: str | None = None
    similarity_score: float | None = None

    # For CREATE action
    suggested_path: str | None = None
    suggested_category: str | None = None


class KBMatcher:
    """
    Matches KB candidates against existing knowledge base.

    Uses Prompt 2: KB Matching
    """

    def __init__(self, kb_index_path: str | None = None):
        """
        Args:
            kb_index_path: Path to KB index/embeddings for similarity search
        """
        # TODO: Initialize KB index (vector DB or simple search)
        self.kb_index_path = kb_index_path

    async def match(
        self, extraction_result: ExtractionResult, existing_kb_docs: list[dict]
    ) -> MatchResult:
        """
        Determine if candidate should create new doc or update existing.

        Decision criteria:
        1. Topic similarity with existing documents
        2. Whether new information is valuable enough to add to existing docs
        3. Whether it's valuable as an independent new document

        Args:
            extraction_result: KB candidate info
            existing_kb_docs: List of existing KB documents metadata

        Returns:
            MatchResult with action and reasoning
        """
        # TODO: Implement using SAP GenAI SDK with matching prompt
        raise NotImplementedError

    async def get_similar_documents(
        self, extraction_result: ExtractionResult, top_k: int = 5
    ) -> list[dict]:
        """Find similar existing KB documents."""
        # TODO: Implement similarity search
        raise NotImplementedError
