"""
Quick test to verify that "Gerrit" is excluded from PERSON masking.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime

from app.models.thread import (
    StandardizedConversation,
    StandardizedMessage,
    Source,
    SourceType,
)
from app.ai_core.masking.pii_masker import PIIMasker


async def test_gerrit_exclusion():
    """Test that 'Gerrit' is not masked while other names are."""

    print("=" * 80)
    print("Testing Gerrit Exclusion from PERSON Masking")
    print("=" * 80)
    print()

    # Create a conversation with Gerrit and other person names
    conversation = StandardizedConversation(
        id="test_gerrit",
        source=Source(
            type=SourceType.TEXT,
            channel_id="test",
            channel_name="test",
        ),
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                message_id="msg1",
                author_id="user1",
                author_name="Test User",
                content="John Doe created a pull request in Gerrit. Please review it with Jane Smith.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                message_id="msg2",
                author_id="user2",
                author_name="Another User",
                content="I checked Gerrit and saw Bob Wilson's comments there.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=2,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    print("Original messages:")
    for msg in conversation.messages:
        print(f"  • {msg.content}")
    print()

    try:
        # Initialize masker
        print("Initializing PIIMasker...")
        masker = PIIMasker()
        print("✅ PIIMasker initialized")
        print()

        # Mask the conversation
        print("Masking conversation...")
        masked = await masker.mask_conversations([conversation])
        print("✅ Masking completed")
        print()

        # Display masked messages
        print("Masked messages:")
        for msg in masked[0].messages:
            print(f"  • {msg.content}")
        print()

        # Verify Gerrit is NOT masked
        gerrit_preserved = all("Gerrit" in msg.content for msg in masked[0].messages)

        # Verify other names ARE masked
        names_masked = all(
            "John Doe" not in msg.content
            and "Jane Smith" not in msg.content
            and "Bob Wilson" not in msg.content
            for msg in masked[0].messages
        )

        print("Verification:")
        print(
            f"  {'✅' if gerrit_preserved else '❌'} Gerrit is preserved (not masked): {gerrit_preserved}"
        )
        print(
            f"  {'✅' if names_masked else '❌'} Other person names are masked: {names_masked}"
        )
        print()

        if gerrit_preserved and names_masked:
            print("=" * 80)
            print("🎉 SUCCESS! Gerrit exclusion is working correctly!")
            print("=" * 80)
        else:
            print("=" * 80)
            print("⚠️  Test failed - please review results above")
            print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gerrit_exclusion())
