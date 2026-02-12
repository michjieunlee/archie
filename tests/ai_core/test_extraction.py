"""
Tests for Knowledge Base Extraction

Tests the 3-step extraction process: classify → extract → document creation
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
from app.models.thread import (
    StandardizedConversation,
    StandardizedMessage,
    Source,
    SourceType,
)
from app.models.knowledge import KBCategory


@pytest.fixture
def sample_troubleshooting_conversation():
    """Create a sample troubleshooting conversation."""
    now = datetime.now(timezone.utc)
    return StandardizedConversation(
        id="1234567890.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="engineering",
        ),
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U001",
                author_name="Alice",
                content="Hey team, I'm getting a 'Connection timeout' error when trying to connect to the database. Has anyone seen this before?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U002",
                author_name="Bob",
                content="Yeah, I've seen that. Are you behind a VPN? The database requires VPN access.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U001",
                author_name="Alice",
                content="Oh! I wasn't connected to the VPN. Let me try again.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U001",
                author_name="Alice",
                content="That fixed it! Thanks Bob. Maybe we should document this somewhere?",
                timestamp=now,
            ),
        ],
    )


@pytest.fixture
def sample_threaded_conversation():
    """Create a sample conversation with thread structure (parent_idx)."""
    now = datetime.now(timezone.utc)
    return StandardizedConversation(
        id="1234567893.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="support",
        ),
        participant_count=3,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U008",
                author_name="USER_1",
                content="How do I reset my password?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                parent_idx=0,
                id="msg2",
                author_id="U009",
                author_name="USER_2",
                content="Go to Settings > Security > Reset Password",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                parent_idx=0,
                id="msg3",
                author_id="U010",
                author_name="USER_3",
                content="You can also use the password reset link sent to your email",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U008",
                author_name="USER_1",
                content="Thanks! That worked.",
                timestamp=now,
            ),
        ],
    )


@pytest.fixture
def sample_process_thread():
    """Create a sample process/workflow thread."""
    now = datetime.now(timezone.utc)
    return StandardizedConversation(
        id="1234567891.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="devops",
        ),
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U003",
                author_name="Charlie",
                content="What's the process for deploying to production?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U004",
                author_name="Diana",
                content="Here's our standard process:\n1. Create a PR with your changes\n2. Get at least 2 code reviews\n3. Run all tests in CI\n4. Merge to main\n5. Tag the release\n6. Deploy to staging first\n7. Run smoke tests\n8. Deploy to production\n9. Monitor logs for 30 minutes",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U003",
                author_name="Charlie",
                content="Got it, thanks! Do we have automated rollback?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
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
    return StandardizedConversation(
        id="1234567892.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="architecture",
        ),
        participant_count=3,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U005",
                author_name="Eve",
                content="We need to decide on our caching strategy. Should we use Redis or Memcached?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U006",
                author_name="Frank",
                content="I'd recommend Redis. Here's why:\n- Better data persistence options\n- Supports more data structures (lists, sets, sorted sets)\n- Built-in pub/sub\n- Active development community\n- Slightly slower than Memcached but the features are worth it",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U007",
                author_name="Grace",
                content="Agreed. We also use Redis for rate limiting and session storage, so it makes sense to consolidate.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U005",
                author_name="Eve",
                content="Makes sense. Let's go with Redis. I'll update the architecture docs.",
                timestamp=now,
            ),
        ],
    )


def test_format_conversation_structure(sample_threaded_conversation):
    """Test that _format_conversation_for_extraction produces correct structure."""
    extractor = KBExtractor()

    # Format the conversation
    formatted = extractor._format_conversation_for_extraction(
        sample_threaded_conversation
    )

    print("\n" + "=" * 80)
    print("FORMATTED CONVERSATION OUTPUT")
    print("=" * 80)
    print(formatted)
    print("=" * 80)

    # Verify structure
    assert "### Conversation from #support" in formatted

    # Check sequential numbering (1., 2., 3., 4.)
    assert "1. [USER_1]" in formatted
    assert "2. [USER_2]" in formatted
    assert "3. [USER_3]" in formatted
    assert "4. [USER_1]" in formatted

    # Check idx labeling
    assert "(idx:0)" in formatted
    assert "(idx:1)" in formatted
    assert "(idx:2)" in formatted
    assert "(idx:3)" in formatted

    # Check thread structure for replies
    assert "└─ Reply to message index 0" in formatted

    # Count occurrences of reply marker (should be 2: idx 1 and 2 both reply to idx 0)
    reply_count = formatted.count("└─ Reply to message index")
    assert reply_count == 2, f"Expected 2 replies, found {reply_count}"

    # Verify content is included
    assert "How do I reset my password?" in formatted
    assert "Go to Settings > Security > Reset Password" in formatted
    assert "You can also use the password reset link" in formatted
    assert "Thanks! That worked." in formatted

    # Verify timestamp format (YYYY-MM-DD HH:MM:SS)
    import re

    timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    timestamps = re.findall(timestamp_pattern, formatted)
    assert len(timestamps) == 4, f"Expected 4 timestamps, found {len(timestamps)}"

    print("\n✅ All format checks passed!")
    print(f"   - Sequential numbering: ✓")
    print(f"   - idx labeling: ✓")
    print(f"   - Thread structure: ✓ ({reply_count} replies)")
    print(f"   - Timestamp format: ✓ ({len(timestamps)} timestamps)")
    print(f"   - Content preservation: ✓")


@pytest.mark.asyncio
async def test_extract_troubleshooting_knowledge(sample_troubleshooting_thread):
    """Test extraction of troubleshooting knowledge with real LLM."""
    extractor = KBExtractor()
    generator = KBGenerator()

    document = await extractor.extract_knowledge(sample_troubleshooting_thread)

    # Assert document was created
    assert document is not None
    print(f"\n✅ Extracted Title: {document.title}")

    # Assert category is correct
    assert document.category == KBCategory.TROUBLESHOOTING
    print(f"Category: {document.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(document.extraction_output, "problem_description")
    assert hasattr(document.extraction_output, "root_cause")
    assert hasattr(document.extraction_output, "solution_steps")
    print(f"Problem: {document.extraction_output.problem_description[:100]}...")

    # Assert AI confidence and reasoning
    assert 0.0 <= document.ai_confidence <= 1.0
    assert document.ai_reasoning
    print(f"AI Confidence: {document.ai_confidence:.2f}")
    print(f"AI Reasoning: {document.ai_reasoning}")

    # Assert metadata
    assert document.extraction_metadata.source_type == "slack"
    assert document.extraction_metadata.source_id == sample_troubleshooting_thread.id
    assert document.extraction_metadata.channel_id == "C01234567"
    assert document.extraction_metadata.channel_name == "engineering"
    assert document.extraction_metadata.message_count == 4

    # Assert tags
    assert len(document.tags) > 0
    print(f"Tags: {document.tags}")

    # Test markdown generation
    markdown = generator.generate_markdown(document)
    assert "# " in markdown
    assert "## Problem Description" in markdown
    assert "## Root Cause" in markdown
    print(f"\n--- Generated Markdown (first 500 chars) ---\n{markdown[:500]}...\n")


@pytest.mark.asyncio
async def test_extract_process_knowledge(sample_process_thread):
    """Test extraction of process knowledge with real LLM."""
    extractor = KBExtractor()

    document = await extractor.extract_knowledge(sample_process_thread)

    # Assert document was created
    assert document is not None
    print(f"\n✅ Extracted Title: {document.title}")

    # Assert category is correct
    assert document.category == KBCategory.PROCESSES
    print(f"Category: {document.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(document.extraction_output, "process_overview")
    assert hasattr(document.extraction_output, "process_steps")
    print(f"Overview: {document.extraction_output.process_overview[:100]}...")

    # Assert AI confidence
    assert 0.0 <= document.ai_confidence <= 1.0
    print(f"AI Confidence: {document.ai_confidence:.2f}")


@pytest.mark.asyncio
async def test_extract_decision_knowledge(sample_decision_thread):
    """Test extraction of decision knowledge with real LLM."""
    extractor = KBExtractor()

    document = await extractor.extract_knowledge(sample_decision_thread)

    # Assert document was created
    assert document is not None
    print(f"\n✅ Extracted Title: {document.title}")

    # Assert category is correct
    assert document.category == KBCategory.DECISIONS
    print(f"Category: {document.category.value}")

    # Assert extraction output has category-specific fields
    assert hasattr(document.extraction_output, "decision_context")
    assert hasattr(document.extraction_output, "decision_made")
    assert hasattr(document.extraction_output, "reasoning")
    print(f"Decision: {document.extraction_output.decision_made[:100]}...")

    # Assert AI confidence
    assert 0.0 <= document.ai_confidence <= 1.0
    print(f"AI Confidence: {document.ai_confidence:.2f}")


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

    troubleshooting = StandardizedConversation(
        id="1234567890.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="engineering",
        ),
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U001",
                author_name="Alice",
                content="Hey team, I'm getting a 'Connection timeout' error when trying to connect to the database. Has anyone seen this before?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U002",
                author_name="Bob",
                content="Yeah, I've seen that. Are you behind a VPN? The database requires VPN access.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U001",
                author_name="Alice",
                content="Oh! I wasn't connected to the VPN. Let me try again.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U001",
                author_name="Alice",
                content="That fixed it! Thanks Bob. Maybe we should document this somewhere?",
                timestamp=now,
            ),
        ],
    )

    document1 = asyncio.run(extractor.extract_knowledge(troubleshooting))

    if document1:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {document1.title}")
        print(f"Category: {document1.category.value}")
        print(f"AI Confidence: {document1.ai_confidence:.2f}")
        print(f"Tags: {', '.join(document1.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Test 2: Process Thread
    print("\n" + "=" * 80)
    print("TEST 2: PROCESS EXTRACTION")
    print("=" * 80)

    process = StandardizedConversation(
        id="1234567891.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="devops",
        ),
        participant_count=2,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U003",
                author_name="Charlie",
                content="What's the process for deploying to production?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U004",
                author_name="Diana",
                content="Here's our standard process:\n1. Create a PR with your changes\n2. Get at least 2 code reviews\n3. Run all tests in CI\n4. Merge to main\n5. Tag the release\n6. Deploy to staging first\n7. Run smoke tests\n8. Deploy to production\n9. Monitor logs for 30 minutes",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U003",
                author_name="Charlie",
                content="Got it, thanks! Do we have automated rollback?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U004",
                author_name="Diana",
                content="Yes, use `./scripts/rollback.sh <tag>` if needed. It automatically reverts to the previous stable version.",
                timestamp=now,
            ),
        ],
    )

    document2 = asyncio.run(extractor.extract_knowledge(process))

    if document2:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {document2.title}")
        print(f"Category: {document2.category.value}")
        print(f"AI Confidence: {document2.ai_confidence:.2f}")
        print(f"Tags: {', '.join(document2.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Test 3: Decision Thread
    print("\n" + "=" * 80)
    print("TEST 3: DECISION EXTRACTION")
    print("=" * 80)

    decision = StandardizedConversation(
        id="1234567892.123456",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C01234567",
            channel_name="architecture",
        ),
        participant_count=3,
        created_at=now,
        last_activity_at=now,
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                author_id="U005",
                author_name="Eve",
                content="We need to decide on our caching strategy. Should we use Redis or Memcached?",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                author_id="U006",
                author_name="Frank",
                content="I'd recommend Redis. Here's why:\n- Better data persistence options\n- Supports more data structures (lists, sets, sorted sets)\n- Built-in pub/sub\n- Active development community\n- Slightly slower than Memcached but the features are worth it",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                author_id="U007",
                author_name="Grace",
                content="Agreed. We also use Redis for rate limiting and session storage, so it makes sense to consolidate.",
                timestamp=now,
            ),
            StandardizedMessage(
                idx=3,
                id="msg4",
                author_id="U005",
                author_name="Eve",
                content="Makes sense. Let's go with Redis. I'll update the architecture docs.",
                timestamp=now,
            ),
        ],
    )

    document3 = asyncio.run(extractor.extract_knowledge(decision))

    if document3:
        print("✅ EXTRACTION SUCCESSFUL!")
        print(f"Title: {document3.title}")
        print(f"Category: {document3.category.value}")
        print(f"AI Confidence: {document3.ai_confidence:.2f}")
        print(f"Tags: {', '.join(document3.tags)}")
    else:
        print("❌ EXTRACTION FAILED")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = sum([1 for a in [document1, document2, document3] if a is not None])
    print(f"\nSuccessfully extracted: {successful}/3 documents")

    if successful == 3:
        print("\n🎉 All extractions completed successfully!")
        print("\nExtracted Documents:")
        for i, document in enumerate([document1, document2, document3], 1):
            print(f"  {i}. {document.title}")
            print(f"     Category: {document.category.value}")
            print(f"     Confidence: {document.ai_confidence:.2f}")
            print(f"     Tags: {', '.join(document.tags[:3])}...")

        # Print full markdown outputs
        print("\n" + "=" * 80)
        print("FULL MARKDOWN OUTPUTS")
        print("=" * 80)

        for i, document in enumerate([document1, document2, document3], 1):
            print(f"\n{'=' * 80}")
            print(f"Document {i}: {document.title}")
            print(f"{'=' * 80}\n")
            markdown = generator.generate_markdown(document)
            print(markdown)
            print(f"\n{'=' * 80}\n")
    else:
        print(f"\n⚠️  {3 - successful} extraction(s) failed")
