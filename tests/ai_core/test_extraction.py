"""
Tests for Knowledge Base Extraction

Tests the 3-step extraction process: classify → extract → article creation
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from datetime import datetime, timezone

from app.ai_core.extraction.kb_extractor import KBExtractor
from app.ai_core.generation.kb_generator import KBGenerator
from app.models.thread import StandardizedThread, StandardizedMessage, SourceType
from app.models.knowledge import KBCategory


@pytest.fixture
def sample_troubleshooting_thread():
    """Create a sample troubleshooting thread."""
    now = datetime.now(timezone.utc)
    return StandardizedThread(
        id="1234567890.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="engineering",
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U001",
                author_name="Alice",
                content="Hey team, I'm getting a 'Connection timeout' error when trying to connect to the database. Has anyone seen this before?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U002",
                author_name="Bob",
                content="Yeah, I've seen that. Are you behind a VPN? The database requires VPN access.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U001",
                author_name="Alice",
                content="Oh! I wasn't connected to the VPN. Let me try again.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U001",
                author_name="Alice",
                content="That fixed it! Thanks Bob. Maybe we should document this somewhere?",
                timestamp=now,
            ),
        ],
    )


@pytest.fixture
def sample_process_thread():
    """Create a sample process/workflow thread."""
    now = datetime.now(timezone.utc)
    return StandardizedThread(
        id="1234567891.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="devops",
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U003",
                author_name="Charlie",
                content="What's the process for deploying to production?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U004",
                author_name="Diana",
                content="Here's our standard process:\n1. Create a PR with your changes\n2. Get at least 2 code reviews\n3. Run all tests in CI\n4. Merge to main\n5. Tag the release\n6. Deploy to staging first\n7. Run smoke tests\n8. Deploy to production\n9. Monitor logs for 30 minutes",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U003",
                author_name="Charlie",
                content="Got it, thanks! Do we have automated rollback?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U004",
                author_name="Diana",
                content="Yes, use `./scripts/rollback.sh <tag>` if needed. It automatically reverts to the previous stable version.",
                timestamp=now,
            ),
        ],
    )


@pytest.fixture
def sample_decision_thread():
    """Create a sample technical decision thread."""
    now = datetime.now(timezone.utc)
    return StandardizedThread(
        id="1234567892.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="architecture",
        participant_count=3,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U005",
                author_name="Eve",
                content="We need to decide on our caching strategy. Should we use Redis or Memcached?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U006",
                author_name="Frank",
                content="I'd recommend Redis. Here's why:\n- Better data persistence options\n- Supports more data structures (lists, sets, sorted sets)\n- Built-in pub/sub\n- Active development community\n- Slightly slower than Memcached but the features are worth it",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U007",
                author_name="Grace",
                content="Agreed. We also use Redis for rate limiting and session storage, so it makes sense to consolidate.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U005",
                author_name="Eve",
                content="Makes sense. Let's go with Redis. I'll update the architecture docs.",
                timestamp=now,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_extract_troubleshooting_knowledge(sample_troubleshooting_thread):
    """Test extraction of troubleshooting knowledge with real LLM."""
    extractor = KBExtractor()
    generator = KBGenerator()

    article = await extractor.extract_knowledge(sample_troubleshooting_thread)

    # Assert article was created
    assert article is not None
    print(f"\n✅ Extracted Title: {article.title}")

    # Assert category is correct
    assert article.category == KBCategory.TROUBLESHOOTING
    print(f"Category: {article.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(article.extraction_output, "problem_description")
    assert hasattr(article.extraction_output, "root_cause")
    assert hasattr(article.extraction_output, "solution_steps")
    print(f"Problem: {article.extraction_output.problem_description[:100]}...")

    # Assert AI confidence and reasoning
    assert 0.0 <= article.ai_confidence <= 1.0
    assert article.ai_reasoning
    print(f"AI Confidence: {article.ai_confidence:.2f}")
    print(f"AI Reasoning: {article.ai_reasoning}")

    # Assert metadata
    assert article.extraction_metadata.source_type == "slack"
    assert article.extraction_metadata.source_id == sample_troubleshooting_thread.id
    assert article.extraction_metadata.channel_name == "engineering"
    assert article.extraction_metadata.message_count == 4

    # Assert tags
    assert len(article.tags) > 0
    print(f"Tags: {article.tags}")

    # Test markdown generation
    markdown = generator.generate_markdown(article)
    assert "# " in markdown
    assert "## Problem Description" in markdown
    assert "## Root Cause" in markdown
    print(f"\n--- Generated Markdown (first 500 chars) ---\n{markdown[:500]}...\n")


@pytest.mark.asyncio
async def test_extract_process_knowledge(sample_process_thread):
    """Test extraction of process knowledge with real LLM."""
    extractor = KBExtractor()

    article = await extractor.extract_knowledge(sample_process_thread)

    # Assert article was created
    assert article is not None
    print(f"\n✅ Extracted Title: {article.title}")

    # Assert category is correct
    assert article.category == KBCategory.PROCESSES
    print(f"Category: {article.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(article.extraction_output, "process_overview")
    assert hasattr(article.extraction_output, "process_steps")
    print(f"Overview: {article.extraction_output.process_overview[:100]}...")

    # Assert AI confidence
    assert 0.0 <= article.ai_confidence <= 1.0
    print(f"AI Confidence: {article.ai_confidence:.2f}")


@pytest.mark.asyncio
async def test_extract_decision_knowledge(sample_decision_thread):
    """Test extraction of decision knowledge with real LLM."""
    extractor = KBExtractor()

    article = await extractor.extract_knowledge(sample_decision_thread)

    # Assert article was created
    assert article is not None
    print(f"\n✅ Extracted Title: {article.title}")

    # Assert category is correct
    assert article.category == KBCategory.DECISIONS
    print(f"Category: {article.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(article.extraction_output, "decision_context")
    assert hasattr(article.extraction_output, "decision_made")
    assert hasattr(article.extraction_output, "reasoning")
    print(f"Decision: {article.extraction_output.decision_made[:100]}...")

    # Assert AI confidence
    assert 0.0 <= article.ai_confidence <= 1.0
    print(f"AI Confidence: {article.ai_confidence:.2f}")


if __name__ == "__main__":
    """Run tests manually with real LLM."""
    print("=" * 80)
    print("KB EXTRACTION TESTS - Real LLM Integration")
    print("=" * 80)

    now = datetime.now(timezone.utc)
    extractor = KBExtractor()
    generator = KBGenerator()

    # Test 1: Troubleshooting Thread
    print("\n" + "=" * 80)
    print("TEST 1: TROUBLESHOOTING EXTRACTION")
    print("=" * 80)

    troubleshooting = StandardizedThread(
        id="1234567890.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="engineering",
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U001",
                author_name="Alice",
                content="Hey team, I'm getting a 'Connection timeout' error when trying to connect to the database. Has anyone seen this before?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U002",
                author_name="Bob",
                content="Yeah, I've seen that. Are you behind a VPN? The database requires VPN access.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U001",
                author_name="Alice",
                content="Oh! I wasn't connected to the VPN. Let me try again.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U001",
                author_name="Alice",
                content="That fixed it! Thanks Bob. Maybe we should document this somewhere?",
                timestamp=now,
            ),
        ],
    )

    article1 = asyncio.run(extractor.extract_knowledge(troubleshooting))

    if article1:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {article1.title}")
        print(f"Category: {article1.category.value}")
        print(f"AI Confidence: {article1.ai_confidence:.2f}")
        print(f"Tags: {', '.join(article1.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Test 2: Process Thread
    print("\n" + "=" * 80)
    print("TEST 2: PROCESS EXTRACTION")
    print("=" * 80)

    process = StandardizedThread(
        id="1234567891.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="devops",
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U003",
                author_name="Charlie",
                content="What's the process for deploying to production?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U004",
                author_name="Diana",
                content="Here's our standard process:\n1. Create a PR with your changes\n2. Get at least 2 code reviews\n3. Run all tests in CI\n4. Merge to main\n5. Tag the release\n6. Deploy to staging first\n7. Run smoke tests\n8. Deploy to production\n9. Monitor logs for 30 minutes",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U003",
                author_name="Charlie",
                content="Got it, thanks! Do we have automated rollback?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U004",
                author_name="Diana",
                content="Yes, use `./scripts/rollback.sh <tag>` if needed. It automatically reverts to the previous stable version.",
                timestamp=now,
            ),
        ],
    )

    article2 = asyncio.run(extractor.extract_knowledge(process))

    if article2:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {article2.title}")
        print(f"Category: {article2.category.value}")
        print(f"AI Confidence: {article2.ai_confidence:.2f}")
        print(f"Tags: {', '.join(article2.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Test 3: Decision Thread
    print("\n" + "=" * 80)
    print("TEST 3: DECISION EXTRACTION")
    print("=" * 80)

    decision = StandardizedThread(
        id="1234567892.123456",
        source=SourceType.SLACK,
        channel_id="C01234567",
        channel_name="architecture",
        participant_count=3,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="U005",
                author_name="Eve",
                content="We need to decide on our caching strategy. Should we use Redis or Memcached?",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="U006",
                author_name="Frank",
                content="I'd recommend Redis. Here's why:\n- Better data persistence options\n- Supports more data structures (lists, sets, sorted sets)\n- Built-in pub/sub\n- Active development community\n- Slightly slower than Memcached but the features are worth it",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="U007",
                author_name="Grace",
                content="Agreed. We also use Redis for rate limiting and session storage, so it makes sense to consolidate.",
                timestamp=now,
            ),
            StandardizedMessage(
                id="msg4",
                author_id="U005",
                author_name="Eve",
                content="Makes sense. Let's go with Redis. I'll update the architecture docs.",
                timestamp=now,
            ),
        ],
    )

    article3 = asyncio.run(extractor.extract_knowledge(decision))

    if article3:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {article3.title}")
        print(f"Category: {article3.category.value}")
        print(f"AI Confidence: {article3.ai_confidence:.2f}")
        print(f"Tags: {', '.join(article3.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = sum([1 for a in [article1, article2, article3] if a is not None])
    print(f"\nSuccessfully extracted: {successful}/3 articles")

    if successful == 3:
        print("\n🎉 All extractions completed successfully!")
        print("\nExtracted Articles:")
        for i, article in enumerate([article1, article2, article3], 1):
            print(f"  {i}. {article.title}")
            print(f"     Category: {article.category.value}")
            print(f"     Confidence: {article.ai_confidence:.2f}")
            print(f"     Tags: {', '.join(article.tags[:3])}...")

        # Print full markdown outputs
        print("\n" + "=" * 80)
        print("FULL MARKDOWN OUTPUTS")
        print("=" * 80)

        for i, article in enumerate([article1, article2, article3], 1):
            print(f"\n{'=' * 80}")
            print(f"ARTICLE {i}: {article.title}")
            print(f"{'=' * 80}\n")
            markdown = generator.generate_markdown(article)
            print(markdown)
            print(f"\n{'=' * 80}\n")
    else:
        print(f"\n⚠️  {3 - successful} extraction(s) failed")
