"""
Standardized Thread Model

Unified thread data structure regardless of input source (Slack, Teams, File, Text, etc.)
"""

from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class SourceType(str, Enum):
    """Source platform type."""

    SLACK = "slack"
    FILE = "file"
    TEXT = "text"
    TEAMS = "teams"  # Future extension


class ThreadCategory(str, Enum):
    """Knowledge base document categories."""

    TROUBLESHOOTING = "troubleshooting"
    PROCESS = "process"
    DECISION = "decision"


class StandardizedMessage(BaseModel):
    """Platform-agnostic message format."""

    id: str
    author_id: str
    author_name: Optional[str] = None  # May be masked or None for privacy
    content: str
    timestamp: datetime
    is_masked: bool = False
    metadata: Dict[str, Any] = {}


class StandardizedThread(BaseModel):
    """Platform-agnostic thread format."""

    id: str
    source: SourceType
    source_url: Optional[str] = None  # Optional for file/text inputs
    channel_id: str
    channel_name: Optional[str] = None
    messages: List[StandardizedMessage]
    participant_count: int
    created_at: datetime
    last_activity_at: datetime
    metadata: Dict[str, Any] = {}


# Living KB Models


class ExistingKBDocument(BaseModel):
    """Represents an existing KB document from GitHub repository."""

    file_path: str  # e.g., "troubleshooting/database/connection-issues.md"
    title: str
    category: str
    tags: List[str]
    content: str  # Full markdown content
    metadata: Dict[str, Any]  # Created date, last updated, difficulty, etc.


class KBOperationType(str, Enum):
    """Types of operations that can be performed on KB documents."""

    CREATE = "create"  # Create new document
    UPDATE = "update"  # Update entire document
    APPEND = "append"  # Add section to existing document
    REPLACE = "replace"  # Replace specific section
    REMOVE = "remove"  # Remove section/document
    MERGE = "merge"  # Merge with another document


# AI Processing Models for team integration


class KBExtractionResult(BaseModel):
    """Result of KB extraction analysis (for AI Core team ②)."""

    thread_id: str
    is_kb_worthy: bool
    confidence_score: float  # 0.0 to 1.0
    reasoning: str  # AI explanation
    suggested_title: str
    category: ThreadCategory  # e.g., "troubleshooting", "process", "decision"
    tags: List[str]
    key_topics: List[str]
    estimated_value: str  # "high", "medium", "low"


class KBMatchResult(BaseModel):
    """Result of matching against existing KB documents."""

    thread_id: str
    operation: KBOperationType
    confidence_score: float
    reasoning: str
    target_document: Optional[str] = None  # File path of existing document to modify
    related_documents: List[str] = []  # File paths of related documents
    merge_candidates: List[str] = []  # Documents that could be merged


class KBOperationResult(BaseModel):
    """Complete result of KB processing with operation instructions."""

    operation: KBOperationType
    file_path: str  # Target file path in KB repo
    title: str
    content: str  # Generated/updated markdown content
    category: str
    tags: List[str]
    metadata: Dict[str, Any]

    # AI context
    ai_confidence: float
    ai_reasoning: str
    source_threads: List[str]

    # For update operations
    target_section: Optional[str] = None  # Section to update (for append/replace)
    original_content: Optional[str] = None  # Original content being modified


class ExistingKBContext(BaseModel):
    """Context about existing KB repository for AI processing."""

    documents: List[ExistingKBDocument]
    repository_stats: Dict[str, Any]  # Total docs, categories, last update, etc.
    categories: List[str]  # Available categories
    search_index: Optional[Dict[str, Any]] = None  # For semantic search
