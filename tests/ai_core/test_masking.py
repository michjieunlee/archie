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
    StandardizedConversation,
    StandardizedMessage,
    Source,
    SourceType,
)
from app.ai_core.masking.pii_masker import PIIMasker, MaskingError


def create_sample_conversations() -> List[StandardizedConversation]:
    """Create sample conversations with PII for testing."""

    # conversation 1: Email discussion with 3 participants
    conversation1 = StandardizedConversation(
        id="conversation_001",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C123",
            channel_name="general",
        ),
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg1",
                message_id="msg1",
                author_id="user_john",
                author_name="John Doe",
                content="Hi team, please contact me at john.doe@company.com",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=1,
                id="msg2",
                message_id="msg2",
                author_id="user_jane",
                author_name="Jane Smith",
                content="Thanks John! My ID is i111111 and my number is +1-555-0123 or local 555-1234 if you need to call.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=2,
                id="msg3",
                message_id="msg3",
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

    # conversation 2: Support conversation
    conversation2 = StandardizedConversation(
        id="conversation_002",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C456",
            channel_name="support",
        ),
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg4",
                message_id="msg4",
                author_id="user_bob",
                author_name="Bob Wilson",
                content="I'm having issues with C987654. Call me at 555-9876 or email bob.wilson@email.com",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=1,
                id="msg5",
                message_id="msg5",
                author_id="user_alice",
                author_name="Alice Brown",
                content="Hi Bob, I'll help you. My ID is I123456 and contact is alice@company.com. Check channel C01ABC123DE or ask user U0ABCDEF04R",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=2,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    # conversation 3: Slack-specific IDs
    conversation3 = StandardizedConversation(
        id="conversation_003",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C1A2B3C4D5E",
            channel_name="tech-support",
        ),
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg6",
                message_id="msg6",
                author_id="U0ABCDEF04R",
                author_name="Tech User",
                content="Please check channel C1234567890 for updates. Contact U9876543210 or W1122334455 if needed.",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=1,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    # conversation 4: Multi-paragraph message with corrections (tests delimiter fix)
    conversation4 = StandardizedConversation(
        id="conversation_004",
        source=Source(
            type=SourceType.SLACK,
            channel_id="C789",
            channel_name="infrastructure",
        ),
        messages=[
            StandardizedMessage(
                idx=0,
                id="msg7",
                message_id="msg7",
                author_id="user_david",
                author_name="David Lee",
                content="Where can I find the infrastructure service contacts?",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=1,
                id="msg8",
                message_id="msg8",
                author_id="user_emma",
                author_name="Emma Wilson",
                content="You can find them at: https://wiki.example.page/infra-service-responsibles\n\nAlso check the GitHub onboarding: https://github.com/your-org/onboarding",
                timestamp=datetime.now(),
                is_masked=False,
            ),
            StandardizedMessage(
                idx=2,
                id="msg9",
                message_id="msg9",
                author_id="user_emma",
                author_name="Emma Wilson",
                content="Correction: The correct first link is:\n\nhttps://wiki.example.page/infra-service/responsibles\n\n(Note the slash between infra-service and responsibles)",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=2,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    return [conversation1, conversation2, conversation3, conversation4]


def print_divider(char="=", length=80):
    """Print a divider line."""
    print(char * length)


def print_conversation(conversation: StandardizedConversation, title: str):
    """Print conversation details."""
    print(f"\n🔹 {title}: {conversation.id} ({conversation.source.channel_name})")
    print(f"   Messages: {len(conversation.messages)}")
    for msg in conversation.messages:
        masked_flag = "✓" if msg.is_masked else "✗"
        print(f"   • [{masked_flag}] {msg.author_name}: {msg.content}")


async def test_masking():
    """Test the PII masking functionality with real SAP GenAI service."""

    print_divider()
    print("PII MASKING TEST WITH REAL SAP GenAI ORCHESTRATION SERVICE")
    print_divider()
    print()

    # Create sample conversations
    conversations = create_sample_conversations()

    print(f"📊 Created {len(conversations)} sample conversations with PII")
    print()

    # Display original conversations
    print("ORIGINAL CONVERSATIONS (Before Masking):")
    print_divider("-")
    for conversation in conversations:
        print_conversation(conversation, "Conversation")
    print()

    try:
        # Create masker (with real service)
        print("🔧 Initializing PIIMasker with real SAP GenAI service...")
        masker = PIIMasker()
        print("✅ PIIMasker initialized successfully!")
        print()

        # Get statistics before masking
        stats = await masker.get_masking_stats(conversations)
        print("📈 Masking Statistics:")
        print(f"   Total conversations: {stats['total_conversations']}")
        print(f"   Total messages: {stats['total_messages']}")
        print(f"   Total characters: {stats['total_characters']}")
        print(f"   Estimated API calls: {stats['estimated_api_calls']}")
        print(f"   Estimated time: {stats['estimated_time_seconds']}s")
        print(f"   Entities to mask: {', '.join(stats['entities_masked'])}")
        print(f"   Masking method: {stats['masking_method']}")
        print()

        # Perform masking
        print("🔐 Starting PII masking with SAP GenAI Orchestration V2...")
        print("   (Processing conversations in parallel with asyncio.gather)")
        print()

        masked_conversations = await masker.mask_conversations(conversations)

        print("✅ Masking completed successfully!")
        print()

        # Display masked conversations
        print("MASKED CONVERSATIONS (After Masking):")
        print_divider("-")
        for conversation in masked_conversations:
            print_conversation(conversation, "Conversation")
        print()

        # Verify masking results
        print("VERIFICATION:")
        print_divider("-")
        print()

        # Check 1: All messages masked
        all_masked = all(
            msg.is_masked
            for conversation in masked_conversations
            for msg in conversation.messages
        )
        status1 = "✅" if all_masked else "❌"
        print(f"{status1} All messages marked as masked: {all_masked}")

        # Check 2: All author names updated to USER_X
        author_names_updated = all(
            msg.author_name and msg.author_name.startswith("USER_")
            for conversation in masked_conversations
            for msg in conversation.messages
        )
        status2 = "✅" if author_names_updated else "❌"
        print(
            f"{status2} All author names updated to USER_X format: {author_names_updated}"
        )

        # Check 3: Conversation structure preserved
        structure_preserved = len(masked_conversations) == len(conversations) and all(
            len(masked_conversations[i].messages) == len(conversations[i].messages)
            for i in range(len(conversations))
        )
        status3 = "✅" if structure_preserved else "❌"
        print(f"{status3} Conversation structure preserved: {structure_preserved}")

        # Check 4: Content changed (masking applied)
        content_changed = any(
            conversations[i].messages[j].content
            != masked_conversations[i].messages[j].content
            for i in range(len(conversations))
            for j in range(len(conversations[i].messages))
        )
        status4 = "✅" if content_changed else "❌"
        print(f"{status4} Content was modified (masking applied): {content_changed}")

        # Check 6: Custom I_NUMBER entities are masked
        inumber_masked = True
        original_inumbers = ["i111111", "D123456", "C987654", "I123456"]
        for conversation in masked_conversations:
            for msg in conversation.messages:
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

        # Check 7: Local phone numbers (123-4567 format) are masked
        local_phone_masked = True
        local_phones = ["555-1234", "555-9876"]
        for conversation in masked_conversations:
            for msg in conversation.messages:
                for phone in local_phones:
                    if phone in msg.content:
                        local_phone_masked = False
                        break
                if not local_phone_masked:
                    break
            if not local_phone_masked:
                break

        status7 = "✅" if local_phone_masked else "❌"
        print(
            f"{status7} Local phone numbers (123-4567 format) were masked: {local_phone_masked}"
        )

        # Check 5: Same user gets same USER_X identifier
        user_consistency = True
        for conversation in masked_conversations:
            author_map_check = {}
            for msg in conversation.messages:
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

        # Check 8: Slack user IDs are masked
        slack_user_masked = True
        slack_users = ["U0ABCDEF04R", "U9876543210", "W1122334455"]
        for conversation in masked_conversations:
            for msg in conversation.messages:
                for user in slack_users:
                    if user in msg.content:
                        slack_user_masked = False
                        break
                if not slack_user_masked:
                    break
            if not slack_user_masked:
                break

        status8 = "✅" if slack_user_masked else "❌"
        print(f"{status8} Slack user IDs were masked: {slack_user_masked}")

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
                local_phone_masked,
                slack_user_masked,
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


async def test_single_conversation():
    """Quick test with a single conversation for faster debugging."""

    print("\n" + "=" * 80)
    print("QUICK TEST - Single Conversation")
    print("=" * 80 + "\n")

    # Create a simple single conversation
    conversation = StandardizedConversation(
        id="test_conversation",
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
                content="My ID is i111111, email is test@example.com, phone is +1-555-0100, and local phone is 123-4567",
                timestamp=datetime.now(),
                is_masked=False,
            ),
        ],
        participant_count=1,
        created_at=datetime.now(),
        last_activity_at=datetime.now(),
    )

    print("Original message:")
    print(
        f"  {conversation.messages[0].author_name}: {conversation.messages[0].content}"
    )
    print()

    try:
        masker = PIIMasker()
        masked = await masker.mask_conversations([conversation])

        print("Masked message:")
        print(f"  {masked[0].messages[0].author_name}: {masked[0].messages[0].content}")
        print()
        print("✅ Single conversation test passed!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys

    print("\n🚀 Starting PII Masking Test with Real SAP GenAI Service...\n")

    # Check if user wants quick test
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        asyncio.run(test_single_conversation())
    else:
        asyncio.run(test_masking())

    print(
        "\n💡 Tip: Use 'python test_masking.py --quick' for faster single-conversation test\n"
    )
