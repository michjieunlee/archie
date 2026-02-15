"""
Unit Tests for Utility Functions

Tests shared helper functions.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime

from app.utils.helpers import flatten_list, format_kb_document_content
from app.models.knowledge import (
    KBDocument,
    KBCategory,
    ExtractionMetadata,
    TroubleshootingExtraction,
    ProcessExtraction,
    DecisionExtraction,
)


def test_flatten_list_empty():
    """Test flatten_list with empty input."""
    assert flatten_list(None) == []
    assert flatten_list([]) == []


def test_flatten_list_single_string():
    """Test flatten_list with single string."""
    assert flatten_list("test") == ["test"]


def test_flatten_list_flat_list():
    """Test flatten_list with already flat list."""
    assert flatten_list(["a", "b", "c"]) == ["a", "b", "c"]


def test_flatten_list_nested():
    """Test flatten_list with nested list."""
    assert flatten_list([["a", "b"], ["c"]]) == ["a", "b", "c"]
    # Deeply nested lists get flattened to one level
    result = flatten_list([[["nested"]]])
    assert len(result) == 1
    assert (
        "nested" in result[0]
    )  # The string is in there, possibly as str representation


def test_format_kb_document_content_troubleshooting():
    """Test format_kb_document_content for troubleshooting category."""
    extraction = TroubleshootingExtraction(
        title="Test Issue",
        tags=["test"],
        difficulty="easy",
        problem_description="Test problem",
        system_info="Test system",
        version_info="v1.0",
        environment="Test",
        symptoms="Test symptoms",
        root_cause="Test cause",
        solution_steps="Test solution",
        prevention_measures="Test prevention",
        related_links="",
        ai_confidence=0.9,
        ai_reasoning="Test reasoning",
    )

    metadata = ExtractionMetadata(
        source_type="text",
        source_id="test_troubleshooting",
        history_from=datetime.now(),
        history_to=datetime.now(),
        message_limit=1,
    )

    document = KBDocument(
        category=KBCategory.TROUBLESHOOTING,
        extraction_output=extraction,
        extraction_metadata=metadata,
        title="Test Issue",
        tags=["test"],
        ai_confidence=0.9,
        ai_reasoning="Test reasoning",
    )

    formatted = format_kb_document_content(document)

    assert "### Problem Description" in formatted
    assert "Test problem" in formatted
    assert "### Environment" in formatted
    assert "Test system" in formatted
    assert "### Solution" in formatted
    assert "Test solution" in formatted


def test_format_kb_document_content_process():
    """Test format_kb_document_content for process category."""
    extraction = ProcessExtraction(
        title="Test Process",
        tags=["process"],
        difficulty="intermediate",
        process_overview="Test overview",
        prerequisites="Test prerequisites",
        process_steps="Test steps",
        validation_steps="Test validation",
        common_issues="Test issues",
        related_processes="",
        ai_confidence=0.85,
        ai_reasoning="Test reasoning",
    )

    metadata = ExtractionMetadata(
        source_type="text",
        source_id="test_process",
        history_from=datetime.now(),
        history_to=datetime.now(),
        message_limit=1,
    )

    document = KBDocument(
        category=KBCategory.PROCESS,
        extraction_output=extraction,
        extraction_metadata=metadata,
        title="Test Process",
        tags=["process"],
        ai_confidence=0.85,
        ai_reasoning="Test reasoning",
    )

    formatted = format_kb_document_content(document)

    assert "### Overview" in formatted
    assert "Test overview" in formatted
    assert "### Prerequisites" in formatted
    assert "### Step-by-Step Process" in formatted
    assert "Test steps" in formatted


def test_format_kb_document_content_decision():
    """Test format_kb_document_content for decision category."""
    extraction = DecisionExtraction(
        title="Test Decision",
        tags=["decision"],
        difficulty="advanced",
        decision_context="Test context",
        decision_made="Test decision",
        reasoning="Test reasoning",
        alternatives="Test alternatives",
        positive_consequences="Test positive",
        negative_consequences="Test negative",
        implementation_notes="",
        ai_confidence=0.8,
        ai_reasoning="Test AI reasoning",
    )

    metadata = ExtractionMetadata(
        source_type="text",
        source_id="test_decision",
        history_from=datetime.now(),
        history_to=datetime.now(),
        message_limit=1,
    )

    document = KBDocument(
        category=KBCategory.DECISION,
        extraction_output=extraction,
        extraction_metadata=metadata,
        title="Test Decision",
        tags=["decision"],
        ai_confidence=0.8,
        ai_reasoning="Test AI reasoning",
    )

    formatted = format_kb_document_content(document)

    assert "### Context" in formatted
    assert "Test context" in formatted
    assert "### Decision" in formatted
    assert "Test decision" in formatted
    assert "### Consequences" in formatted
    assert "#### Positive" in formatted
    assert "#### Negative" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
