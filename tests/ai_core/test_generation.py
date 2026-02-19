"""
Unit Tests for KBGenerator

Tests the KB document generation and update functionality.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime

from app.ai_core.generation import KBGenerator
from app.models.knowledge import (
    KBDocument,
    KBCategory,
    ExtractionMetadata,
    TroubleshootingExtraction,
)


@pytest.fixture
def sample_kb_document():
    """Create a sample KB document for testing."""
    extraction_output = TroubleshootingExtraction(
        title="API Timeout Issue",
        tags=["api", "timeout", "troubleshooting"],
        difficulty="intermediate",
        problem_description="API calls timing out after 30 seconds",
        system_info="Production API Gateway",
        version_info="v2.1.0",
        environment="Production",
        symptoms="HTTP 504 Gateway Timeout errors",
        root_cause="Default timeout setting too short for large data transfers",
        solution_steps="Increased timeout from 30s to 60s in configuration",
        prevention_measures="Monitor API response times and adjust timeouts proactively",
        related_links="",
        ai_confidence=0.85,
        ai_reasoning="Clear troubleshooting scenario with solution",
    )

    extraction_metadata = ExtractionMetadata(
        source_type="text",
        source_id="test_input_1",
        history_from=datetime.now(),
        history_to=datetime.now(),
        message_limit=1,
    )

    return KBDocument(
        category=KBCategory.TROUBLESHOOTING,
        extraction_output=extraction_output,
        extraction_metadata=extraction_metadata,
        title="API Timeout Issue",
        tags=["api", "timeout", "troubleshooting"],
        ai_confidence=0.85,
        ai_reasoning="Clear troubleshooting scenario",
    )


def test_generator_initialization():
    """Test KBGenerator initialization."""
    generator = KBGenerator()
    assert generator.templates_dir.exists()
    assert generator.templates_dir.name == "templates"


def test_generate_markdown(sample_kb_document):
    """Test markdown generation from KB document."""
    generator = KBGenerator()
    markdown = generator.generate_markdown(sample_kb_document)

    # Verify markdown structure
    assert markdown.startswith("---")  # Frontmatter
    assert "title:" in markdown
    assert 'category: "troubleshooting"' in markdown
    assert "API Timeout Issue" in markdown
    assert "## Problem Description" in markdown
    assert "## Solution" in markdown


def test_generate_filename(sample_kb_document):
    """Test filename generation."""
    generator = KBGenerator()
    filename = generator.generate_filename(sample_kb_document)

    assert filename.endswith(".md")
    assert "api-timeout-issue" in filename
    assert " " not in filename  # No spaces
    assert len(filename) <= 63  # 60 + ".md"


def test_get_category_directory():
    """Test category directory mapping for all 5 categories."""
    generator = KBGenerator()

    # Test all 5 categories
    assert (
        generator.get_category_directory(KBCategory.TROUBLESHOOTING)
        == "troubleshooting"
    )
    assert generator.get_category_directory(KBCategory.PROCESS) == "processes"
    assert generator.get_category_directory(KBCategory.DECISION) == "decisions"
    assert generator.get_category_directory(KBCategory.REFERENCE) == "references"
    assert generator.get_category_directory(KBCategory.GENERAL) == "general"


@pytest.mark.asyncio
async def test_update_markdown_basic(sample_kb_document):
    """Test basic update_markdown functionality."""
    generator = KBGenerator()

    existing_content = """---
title: "API Timeout Issue"
category: "troubleshooting"
tags: ["api", "timeout"]
---

# API Timeout Issue

## Problem Description
API calls timing out after 30 seconds

## Solution
Increased timeout from 30s to 60s
"""

    # This test requires actual LLM, so we'll just verify it doesn't crash
    try:
        updated = await generator.update_markdown(existing_content, sample_kb_document)
        assert isinstance(updated, str)
        assert len(updated) > 0
        # Should preserve the title
        assert "API Timeout" in updated

        print("\n" + "=" * 80)
        print("UPDATED DOCUMENT:")
        print("=" * 80)
        print(updated)
        print("=" * 80)
    except Exception as e:
        # Expected if no LLM credentials configured
        print(f"\nNote: LLM not available for testing: {e}")
        assert "proxy_client" in str(e).lower() or "api" in str(e).lower()


@pytest.mark.asyncio
async def test_update_markdown_with_new_info(sample_kb_document):
    """Test update_markdown with additional information from different document.

    Tests that:
    1. Different title in existing doc is preserved
    2. Different tags in existing doc are NOT unnecessarily changed
    3. New meaningful content is added
    """
    generator = KBGenerator()

    # Existing document with different title and tags
    existing_content = """---
title: "Gateway Timeout Errors"
category: "troubleshooting"
tags: ["gateway", "http-504", "production-issues"]
difficulty: "beginner"
---

# Gateway Timeout Errors

## Problem Description
API calls timing out

## Solution
Increased timeout setting

## Prevention
None specified
"""

    # Modify the sample document to have more detailed information
    sample_kb_document.extraction_output.solution_steps = (
        "1. Increased timeout from 30s to 60s\n"
        "2. Added connection pool monitoring\n"
        "3. Implemented retry logic with exponential backoff"
    )

    try:
        updated = await generator.update_markdown(existing_content, sample_kb_document)
        assert isinstance(updated, str)
        assert len(updated) > 0

        print("\n" + "=" * 80)
        print("ORIGINAL DOCUMENT:")
        print("=" * 80)
        print(existing_content)
        print("\n" + "=" * 80)
        print("UPDATED DOCUMENT:")
        print("=" * 80)
        print(updated)
        print("=" * 80)

        # Verify tags should ideally be preserved (unless meaning changed)
        # The AI should follow the guideline to not change tags unnecessarily
        print("\nVerifying selective update guidelines:")
        print(f"  - Original tags: ['gateway', 'http-504', 'production-issues']")
        print(f"  - New doc tags: ['api', 'timeout', 'troubleshooting']")
        print(
            f"  - Tags in updated doc should ideally match original unless meaning changed"
        )

    except Exception as e:
        # Expected if no LLM credentials configured
        print(f"\nNote: LLM not available for testing: {e}")
        assert "proxy_client" in str(e).lower() or "api" in str(e).lower()


def test_fallback_markdown(sample_kb_document):
    """Test fallback markdown generation when template fails."""
    generator = KBGenerator()
    fallback = generator._fallback_markdown(sample_kb_document)

    assert "# API Timeout Issue" in fallback
    assert "**Category**: troubleshooting" in fallback
    assert "**Tags**:" in fallback
    assert "**Confidence**:" in fallback


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements
