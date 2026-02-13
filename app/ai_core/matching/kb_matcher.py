"""
Knowledge Base Matcher
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Prompt 2: KB Matching (create / update / ignore)
- Compare with existing KB documents
- Determine New vs Update
- Focus on value addition over topic similarity
"""

import logging
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from langchain_core.prompts import ChatPromptTemplate

from app.models.knowledge import KBDocument
from app.ai_core.prompts.matching import MATCHING_SYSTEM_PROMPT
from app.config import get_settings
from app.utils import flatten_list

logger = logging.getLogger(__name__)


class MatchAction(str, Enum):
    """Action to take for KB candidate."""

    CREATE = "create"  # Create new document
    UPDATE = "update"  # Update existing document
    IGNORE = "ignore"  # Do not add to KB


class MatchResult(BaseModel):
    """Result of KB matching - structured output from LLM."""

    action: MatchAction = Field(
        ..., description="Action to take: create, update, or ignore"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation of the decision and how new content relates to existing documents",
    )
    value_addition_assessment: str = Field(
        ...,
        description="What value the new content adds (for UPDATE/CREATE) or why it lacks value (for IGNORE)",
    )

    # Unified fields for both UPDATE and CREATE
    document_path: Optional[str] = Field(
        None,
        description="Path of document - for UPDATE: matched document path, for CREATE: suggested path",
    )
    document_title: Optional[str] = Field(
        None,
        description="Title of document - for UPDATE: matched document title, for CREATE: suggested title",
    )
    category: Optional[str] = Field(
        None,
        description="Category of document: troubleshooting, processes, or decisions",
    )


class KBMatcher:
    """
    Matches KB candidates against existing knowledge base.

    Uses LLM with structured output (Pydantic models) to determine whether new content
    should create a new document, update an existing one, or be ignored.

    Key principle: Prioritize value addition over topic similarity.
    """

    def __init__(self, kb_index_path: Optional[str] = None):
        """
        Args:
            kb_index_path: Path to KB index/embeddings for similarity search (unused in current implementation)
        """
        self.kb_index_path = kb_index_path

        # Initialize LLM with structured output
        config = get_settings()
        from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

        self.proxy_client = get_proxy_client("gen-ai-hub")
        self.llm = ChatOpenAI(
            proxy_model_name=config.openai_model,
            proxy_client=self.proxy_client,
            temperature=0.0,  # Deterministic for matching decisions
        )

        logger.info("KBMatcher initialized with structured output (Pydantic)")

    async def match(
        self,
        kb_document: KBDocument,
        existing_kb_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> MatchResult:
        """
        Determine if candidate should create new doc or update existing.

        Uses LLM with structured output (Pydantic) to assess value addition and make decisions.

        Decision logic:
        1. Find potentially relevant existing documents (broader search)
        2. Use LLM with structured output to assess value addition
        3. If high value addition found (score > 0.6), return UPDATE
        4. If no substantial value addition but content is valuable, return CREATE
        5. If content is low quality or duplicate, return IGNORE

        Args:
            kb_document: Extracted KB document
            existing_kb_docs: List of existing KB documents from GitHub with structure:
                {
                    "title": "Document Title",
                    "path": "category/filename.md",
                    "category": "troubleshooting|processes|decisions",
                    "tags": ["tag1", "tag2"],
                    "content": "Full markdown content with frontmatter",
                    "markdown_content": "Content without frontmatter",
                    "frontmatter": {...}
                }

        Returns:
            MatchResult with action and reasoning (structured output)
        """
        logger.info(f"Matching KB document: {kb_document.title}")

        # Check AI confidence - if too low, consider ignoring
        if kb_document.ai_confidence < 0.6:
            logger.info(
                f"Low AI confidence ({kb_document.ai_confidence}), may recommend IGNORE"
            )

        # If no existing docs, always CREATE
        if not existing_kb_docs or len(existing_kb_docs) == 0:
            logger.info("No existing KB docs found, returning CREATE")
            return self._create_result(kb_document)

        # Find potentially relevant existing documents
        relevant_documents = self._find_relevant_documents(
            kb_document, existing_kb_docs
        )
        logger.info(
            f"Found {len(relevant_documents)} potentially relevant existing documents"
        )

        if not relevant_documents:
            logger.info("No relevant existing documents found, returning CREATE")
            return self._create_result(kb_document)

        # Use LLM with structured output to make comprehensive matching decision
        try:
            match_result = await self._llm_match_decision_structured(
                kb_document, relevant_documents
            )

            logger.info(
                f"Match decision: {match_result.action} (confidence: {match_result.confidence_score})"
            )

            return match_result

        except Exception as e:
            logger.error(f"Error in LLM match decision: {e}", exc_info=True)
            # Fallback to CREATE with low confidence
            return self._create_result(kb_document, fallback_reason=str(e))

    def _find_relevant_documents(
        self,
        kb_document: KBDocument,
        existing_kb_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Find potentially relevant existing documents using heuristic filtering.

        Uses category and tag overlap to identify candidates. This is a preliminary
        filter before LLM-based value addition assessment.

        Args:
            kb_document: New KB document
            existing_kb_docs: All existing KB documents

        Returns:
            List of potentially relevant documents
        """
        relevant = []
        kb_tags = set(flatten_list(kb_document.tags))
        kb_category = kb_document.category.value

        for doc in existing_kb_docs:
            doc_tags = set(flatten_list(doc.get("tags", [])))
            doc_category = doc.get("category", "")

            # Same category gets higher priority
            if doc_category == kb_category:
                relevant.append(doc)
                continue

            # Tag overlap (at least 1 common tag)
            if kb_tags & doc_tags:
                relevant.append(doc)
                continue

            # Include documents from related categories
            # (value can be added across categories)
            relevant.append(doc)

        # Prioritize: same category > tag overlap > all others
        def relevance_score(doc):
            score = 0
            if doc.get("category") == kb_category:
                score += 10
            doc_tags = set(flatten_list(doc.get("tags", [])))
            overlap = len(doc_tags & kb_tags)
            score += overlap * 2
            return score

        relevant.sort(key=relevance_score, reverse=True)
        return relevant  # Return all relevant documents

    async def _llm_match_decision_structured(
        self,
        kb_document: KBDocument,
        relevant_documents: List[Dict[str, Any]],
    ) -> MatchResult:
        """
        Use LLM with structured output to make comprehensive matching decision.

        Args:
            kb_document: New KB document
            relevant_documents: Pre-filtered relevant documents

        Returns:
            MatchResult (Pydantic model from structured output)
        """
        # Format new content based on category template structure
        new_content_formatted = self._format_new_content_by_category(kb_document)

        # Format existing docs
        existing_docs_text = self._format_existing_docs(relevant_documents)

        # Build prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", MATCHING_SYSTEM_PROMPT),
                (
                    "human",
                    """## New Content to Match

Title: {candidate_title}
Category: {candidate_category}
Tags: {candidate_tags}
AI Confidence: {candidate_confidence}

{new_content_formatted}

## Existing Knowledge Base Documents

{existing_docs}

## Task

Determine if this new content should CREATE a new document, UPDATE an existing one, or be IGNORED.
Provide your response as structured output matching the MatchResult model.""",
                ),
            ]
        )

        # Create chain with structured output
        chain = prompt | self.llm.with_structured_output(MatchResult)

        # Invoke with data
        result = await chain.ainvoke(
            {
                "candidate_title": kb_document.title,
                "candidate_category": kb_document.category.value,
                "candidate_tags": ", ".join(kb_document.tags),
                "candidate_confidence": kb_document.ai_confidence,
                "new_content_formatted": new_content_formatted,
                "existing_docs": existing_docs_text,
            }
        )

        logger.info(f"Structured output received: {result.action}")
        return result

    def _format_new_content_by_category(self, kb_document: KBDocument) -> str:
        """
        Format new content based on category template structure.

        Uses the same structure as the templates to present content consistently.
        """
        extraction = kb_document.extraction_output
        category = kb_document.category.value

        if category == "troubleshooting":
            return f"""### Problem Description
{extraction.problem_description}

### Environment
- **System**: {extraction.system_info}
- **Version**: {extraction.version_info}
- **Environment**: {extraction.environment}

### Symptoms
{extraction.symptoms}

### Root Cause
{extraction.root_cause}

### Solution
{extraction.solution_steps}

### Prevention
{extraction.prevention_measures}

### Related Issues
{extraction.related_links or 'None'}"""

        elif category == "process":
            return f"""### Overview
{extraction.process_overview}

### Prerequisites
{extraction.prerequisites}

### Step-by-Step Process
{extraction.process_steps}

### Validation
{extraction.validation_steps}

### Troubleshooting
{extraction.common_issues}

### Related Processes
{extraction.related_processes}"""

        elif category == "decision":
            return f"""### Context
{extraction.decision_context}

### Decision
{extraction.decision_made}

### Rationale
{extraction.reasoning}

### Alternatives Considered
{extraction.alternatives}

### Consequences
#### Positive
{extraction.positive_consequences}

#### Negative
{extraction.negative_consequences}

### Implementation Notes
{extraction.implementation_notes}"""

        elif category == "reference":
            return f"""### Question Context
{extraction.question_context}

### Resource Type
{extraction.resource_type}

### Primary Resource
{extraction.primary_resource}

### Additional Resources
{extraction.additional_resources}

### Resource Description
{extraction.resource_description}

### Usage Context
{extraction.usage_context}

### Access Requirements
{extraction.access_requirements}

### Related Topics
{extraction.related_topics}"""

        elif category == "general":
            return f"""### Summary
{extraction.summary}

### Key Topics
{extraction.key_topics}

### Key Points
{extraction.key_points}

### Mentioned Resources
{extraction.mentioned_resources}

### Participants Context
{extraction.participants_context}"""

        else:
            return "Content format not available for this category"

    def _format_existing_docs(self, existing_docs: List[Dict[str, Any]]) -> str:
        """Format existing KB documents for LLM prompt."""
        if not existing_docs:
            return "No existing KB documents found."

        formatted = []
        for i, doc in enumerate(existing_docs, 1):  # Process all documents
            # Extract full content from markdown_content
            markdown_content = doc.get("markdown_content", "")
            summary_lines = []
            for line in markdown_content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    summary_lines.append(line)
            summary = (
                " ".join(summary_lines) if summary_lines else "No summary available"
            )

            # Use 'path' field from GitHub client
            path = doc.get("path") or doc.get("file_path", "unknown")

            # Safely flatten tags (use shared utility)
            doc_tags = flatten_list(doc.get("tags", []))
            tags_str = ", ".join(sorted(doc_tags)) if doc_tags else "None"

            formatted.append(
                f"""### {i}. {doc.get('title', 'Untitled')}
- **Path**: {path}
- **Category**: {doc.get('category', 'unknown')}
- **Tags**: {tags_str}
- **Summary**: {summary}
"""
            )

        return "\n".join(formatted)

    def _create_result(
        self, kb_document: KBDocument, fallback_reason: Optional[str] = None
    ) -> MatchResult:
        """Create a CREATE action result."""
        suggested_path = (
            f"{kb_document.category.value}/"
            f"{kb_document.title.lower().replace(' ', '-').replace('/', '-')}.md"
        )

        reasoning = (
            "No relevant existing documents found. This content deserves its own document."
            if not fallback_reason
            else f"Fallback to CREATE due to error: {fallback_reason}"
        )

        return MatchResult(
            action=MatchAction.CREATE,
            confidence_score=kb_document.ai_confidence if not fallback_reason else 0.5,
            reasoning=reasoning,
            value_addition_assessment=(
                "New independent content that warrants its own document."
                if not fallback_reason
                else "Unable to assess value addition due to processing error."
            ),
            document_path=suggested_path,
            document_title=kb_document.title,
            category=kb_document.category.value,
        )
