"""
Test script for PII Masking with real SAP GenAI Orchestration Service.

This script tests the actual PII masking functionality using real SAP GenAI credentials.
Make sure you have configured the following in your .env file:
- SAP_GENAI_API_URL
- SAP_GENAI_API_KEY
- SAP_GENAI_DEPLOYMENT_ID

Usage:
    python test_masking.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime
from typing import List

from app.models.thread import (
    StandardizedThread,
    StandardizedMessage,
    SourceType,
)
from app.ai_core.masking.pii_masker import PIIMasker, MaskingError


def create_sample_threads() -> List[StandardizedThread]:
    """Create sample threads with PII for testing."""

    # Thread 1: Email discussion with 3 participants
    thread1 = StandardizedThread(
        id="thread_001",
        source=SourceType.SLACK,
        source_url="https://example.slack.com/archives/C123/p123456",
        channel_id="C123",
        channel_name="general",
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="user_john",
                author_name="John Doe",
                content="Hi team, please contact me at john.doe@company.com",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                id="msg2",
                author_id="user_jane",
                author_name="Jane Smith",
                content="Thanks John! My ID is i111111 and my number is +1-555-0123 if you need to call.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                id="msg3",
                author_id="user_john",
                author_name="John Doe",
                content="Got it Jane. My colleague D123456 will help. I'll send the docs to john.doe@company.com later.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=2,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    # Thread 2: Support conversation
    thread2 = StandardizedThread(
        id="thread_002",
        source=SourceType.SLACK,
        source_url="https://example.slack.com/archives/C456/p789012",
        channel_id="C456",
        channel_name="support",
        messages=[
            StandardizedMessage(
                id="msg4",
                author_id="user_bob",
                author_name="Bob Wilson",
                content="I'm having issues with C987654. Call me at 555-9876 or email bob.wilson@email.com",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                id="msg5",
                author_id="user_alice",
                author_name="Alice Brown",
                content="Hi Bob, I'll help you. My ID is I123456 and contact is alice@company.com",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=2,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    return [thread1, thread2]


def print_divider(char="=", length=80):
    """Print a divider line."""
    print(char * length)


def print_thread(thread: StandardizedThread, title: str):
    """Print thread details."""
    print(f"\n🔹 {title}: {thread.id} ({thread.channel_name})")
    print(f"   Messages: {len(thread.messages)}")
    for msg in thread.messages:
        masked_flag = "✓" if msg.is_masked else "✗"
        print(f"   • [{masked_flag}] {msg.author_name}: {msg.content}")


async def test_masking():
    """Test the PII masking functionality with real SAP GenAI service."""

    print_divider()
    print("PII MASKING TEST WITH REAL SAP GenAI ORCHESTRATION SERVICE")
    print_divider()
    print()

    # Create sample threads
    threads = create_sample_threads()

    print(f"📊 Created {len(threads)} sample threads with PII")
    print()

    # Display original threads
    print("ORIGINAL THREADS (Before Masking):")
    print_divider("-")
    for thread in threads:
        print_thread(thread, "Thread")
    print()

    try:
        # Create masker (with real service)
        print("🔧 Initializing PIIMasker with real SAP GenAI service...")
        masker = PIIMasker()
        print("✅ PIIMasker initialized successfully!")
        print()

        # Get statistics before masking
        stats = await masker.get_masking_stats(threads)
        print("📈 Masking Statistics:")
        print(f"   Total threads: {stats['total_threads']}")
        print(f"   Total messages: {stats['total_messages']}")
        print(f"   Total characters: {stats['total_characters']}")
        print(f"   Estimated API calls: {stats['estimated_api_calls']}")
        print(f"   Estimated time: {stats['estimated_time_seconds']}s")
        print(f"   Entities to mask: {', '.join(stats['entities_masked'])}")
        print(f"   Masking method: {stats['masking_method']}")
        print()

        # Perform masking
        print("🔐 Starting PII masking with SAP GenAI Orchestration V2...")
        print("   (Processing threads in parallel with asyncio.gather)")
        print()

        masked_threads = await masker.mask_threads(threads)

        print("✅ Masking completed successfully!")
        print()

        # Display masked threads
        print("MASKED THREADS (After Masking):")
        print_divider("-")
        for thread in masked_threads:
            print_thread(thread, "Thread")
        print()

        # Verify masking results
        print("VERIFICATION:")
        print_divider("-")
        print()

        # Check 1: All messages masked
        all_masked = all(
            msg.is_masked for thread in masked_threads for msg in thread.messages
        )
        status1 = "✅" if all_masked else "❌"
        print(f"{status1} All messages marked as masked: {all_masked}")

        # Check 2: All author names updated to USER_X
        author_names_updated = all(
            msg.author_name and msg.author_name.startswith("USER_")
            for thread in masked_threads
            for msg in thread.messages
        )
        status2 = "✅" if author_names_updated else "❌"
        print(
            f"{status2} All author names updated to USER_X format: {author_names_updated}"
        )

        # Check 3: Thread structure preserved
        structure_preserved = len(masked_threads) == len(threads) and all(
            len(masked_threads[i].messages) == len(threads[i].messages)
            for i in range(len(threads))
        )
        status3 = "✅" if structure_preserved else "❌"
        print(f"{status3} Thread structure preserved: {structure_preserved}")

        # Check 4: Content changed (masking applied)
        content_changed = any(
            threads[i].messages[j].content != masked_threads[i].messages[j].content
            for i in range(len(threads))
            for j in range(len(threads[i].messages))
        )
        status4 = "✅" if content_changed else "❌"
        print(f"{status4} Content was modified (masking applied): {content_changed}")

        # Check 6: Custom I_NUMBER entities are masked
        inumber_masked = True
        original_inumbers = ["i111111", "D123456", "C987654", "I123456"]
        for thread in masked_threads:
            for msg in thread.messages:
                for inumber in original_inumbers:
                    if inumber in msg.content or inumber.lower() in msg.content:
                        inumber_masked = False
                        break
                if not inumber_masked:
                    break
            if not inumber_masked:
                break

        status6 = "✅" if inumber_masked else "❌"
        print(
            f"{status6} Custom I_NUMBER entities (I/D/C IDs) were masked: {inumber_masked}"
        )

        # Check 5: Same user gets same USER_X identifier
        user_consistency = True
        for thread in masked_threads:
            author_map_check = {}
            for msg in thread.messages:
                if msg.author_id in author_map_check:
                    if author_map_check[msg.author_id] != msg.author_name:
                        user_consistency = False
                        break
                else:
                    author_map_check[msg.author_id] = msg.author_name
            if not user_consistency:
                break

        status5 = "✅" if user_consistency else "❌"
        print(
            f"{status5} Same author_id gets same USER_X across messages: {user_consistency}"
        )

        print()

        # Summary
        all_checks_passed = all(
            [
                all_masked,
                author_names_updated,
                structure_preserved,
                content_changed,
                user_consistency,
                inumber_masked,
            ]
        )

        if all_checks_passed:
            print_divider()
            print("🎉 ALL TESTS PASSED! PII MASKING WORKING CORRECTLY! ✅")
            print_divider()
        else:
            print_divider()
            print("⚠️  SOME TESTS FAILED - PLEASE REVIEW RESULTS ABOVE")
            print_divider()

    except MaskingError as e:
        print()
        print_divider()
        print(f"❌ MASKING ERROR: {e}")
        print_divider()
        print()
        print("Troubleshooting tips:")
        print("1. Check your .env file has correct SAP GenAI credentials:")
        print("   - SAP_GENAI_API_URL")
        print("   - SAP_GENAI_API_KEY")
        print("   - SAP_GENAI_DEPLOYMENT_ID")
        print("2. Verify your deployment supports Orchestration V2")
        print("3. Check network connectivity to SAP GenAI service")
        print()

    except Exception as e:
        print()
        print_divider()
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        print_divider()
        print()
        import traceback

        traceback.print_exc()


async def test_single_thread():
    """Quick test with a single thread for faster debugging."""

    print("\n" + "=" * 80)
    print("QUICK TEST - Single Thread")
    print("=" * 80 + "\n")

    # Create a simple single thread
    thread = StandardizedThread(
        id="test_thread",
        source=SourceType.TEXT,
        channel_id="test",
        channel_name="test",
        messages=[
            StandardizedMessage(
                id="msg1",
                author_id="user1",
                author_name="Test User",
                content="My ID is i111111, email is test@example.com and phone is 555-1234",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=1,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    print("Original message:")
    print(f"  {thread.messages[0].author_name}: {thread.messages[0].content}")
    print()

    try:
        masker = PIIMasker()
        masked = await masker.mask_threads([thread])

        print("Masked message:")
        print(f"  {masked[0].messages[0].author_name}: {masked[0].messages[0].content}")
        print()
        print("✅ Single thread test passed!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys

    print("\n🚀 Starting PII Masking Test with Real SAP GenAI Service...\n")

    # Check if user wants quick test
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(test_single_thread())
    else:
        asyncio.run(test_masking())

    print(
        "\n💡 Tip: Use 'python test_masking.py --quick' for faster single-thread test\n"
    )
