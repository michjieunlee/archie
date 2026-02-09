"""
Updated Slack Integration Test Suite

This script tests the Slack integration with the new clean architecture:
- StandardizedConversation-based structure
- Global indexing with idx/parent_idx fields
- Clean SlackClient without masking logic
- Simplified test structure without deprecated masking tests

Usage:
    python tests/integrations/test_slack_integration.py --mock      # Mock data (default)
    python tests/integrations/test_slack_integration.py --real      # Real Slack API
    python tests/integrations/test_slack_integration.py --quick     # Quick test
    python tests/integrations/test_slack_integration.py --list-channels  # List channels

Requirements for --real mode:
- SLACK_BOT_TOKEN in .env
- SLACK_CHANNEL_ID in .env (optional)
"""

import sys
from pathlib import Path
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

from app.integrations.slack.client import SlackClient
from app.models.thread import (
    StandardizedConversation,
    StandardizedMessage,
    Source,
    SourceType,
    ConversationCategory,
)
from app.config import get_settings


# ============================================================================
# Constants and Test Data
# ============================================================================

MOCK_HISTORY_DATA = {
    "messages": [
        {
            "ts": "1706123400.123456",
            "user": "U123USER1",
            "text": "Hey team, I need help with the new feature implementation",
            "reply_count": 2,
            "reactions": [{"name": "thumbsup", "count": 1}],
            "attachments": [],
        },
        {
            "ts": "1706123300.654321",
            "user": "U456USER2",
            "text": "Quick update: The deployment went smoothly",
            "reactions": [],
            "attachments": [],
        },
    ]
}

MOCK_THREAD_DATA = {
    "messages": [
        {
            "ts": "1706123400.123456",
            "user": "U123USER1",
            "text": "Hey team, I need help with the new feature implementation",
            "thread_ts": "1706123400.123456",
        },
        {
            "ts": "1706123450.789012",
            "user": "U456USER2",
            "text": "I can help! Let me take a look at the requirements",
            "thread_ts": "1706123400.123456",
        },
        {
            "ts": "1706123500.345678",
            "user": "U789USER3",
            "text": "Thanks both! I'll update the documentation once it's ready",
            "thread_ts": "1706123400.123456",
        },
    ]
}

EXPECTED_MESSAGE_ORDER = [
    "Hey team, I need help with the new feature implementation",
    "I can help! Let me take a look at the requirements",
    "Thanks both! I'll update the documentation once it's ready",
    "Quick update: The deployment went smoothly",
]


# ============================================================================
# Configuration and Data Classes
# ============================================================================


@dataclass
class TestConfig:
    """Test configuration settings."""

    verbose: bool = False
    limit: Optional[int] = 10
    from_datetime: Optional[datetime] = None
    to_datetime: Optional[datetime] = None

    def has_time_filter(self) -> bool:
        return self.from_datetime is not None or self.to_datetime is not None

    def has_custom_settings(self) -> bool:
        return self.verbose or self.has_time_filter() or self.limit != 10


@dataclass
class TestResult:
    """Test execution result."""

    name: str
    passed: bool
    message: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance timing metrics."""

    extraction_time: float = 0.0
    conversion_time: float = 0.0
    total_time: float = 0.0


# ============================================================================
# Utility Classes
# ============================================================================


class TestOutputFormatter:
    """Handles all test output formatting."""

    @staticmethod
    def print_divider(char: str = "=", length: int = 60):
        """Print a shorter divider line."""
        print(char * length)

    @staticmethod
    def print_header(title: str, emoji: str = "📋"):
        """Print clean section header."""
        print(f"\n{emoji} {title}")

    @staticmethod
    def print_test_status(test_name: str, passed: bool, details: str = None):
        """Print aligned test status."""
        status = "✅ PASS" if passed else "❌ FAIL"
        dots = "." * (45 - len(test_name))
        print(f"  {test_name} {dots} {status}")
        if details:
            print(f"      → {details}")

    @staticmethod
    def print_config(config: TestConfig):
        """Print test configuration concisely."""
        if not config.has_custom_settings():
            return

        config_parts = []
        if config.limit:
            config_parts.append(f"limit {config.limit}")
        elif config.limit is None:
            config_parts.append("no limit")

        if config.has_time_filter():
            if config.from_datetime and config.to_datetime:
                config_parts.append("date range")
            elif config.from_datetime:
                days_ago = (datetime.now() - config.from_datetime).days
                if days_ago == 0:
                    hours_ago = int(
                        (datetime.now() - config.from_datetime).total_seconds() / 3600
                    )
                    config_parts.append(f"last {hours_ago}h")
                else:
                    config_parts.append(f"last {days_ago}d")

        if config.verbose:
            config_parts.append("verbose mode")

        if config_parts:
            print(f"📅 Configuration: {', '.join(config_parts)}")
            print()

    @staticmethod
    def print_verbose_extraction(
        conversation: StandardizedConversation, user_mapping: Dict[str, str]
    ):
        """Print detailed extraction results."""
        print("📊 CONVERSATION EXTRACTION RESULTS:")

        for i, msg in enumerate(conversation.messages, 1):
            user_display = user_mapping.get(
                msg.author_id, f"USER_{len(user_mapping) + 1}"
            )
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content

            print(
                f"   {i:2d}. [{user_display}] {timestamp_str} (idx:{msg.idx}): {preview}"
            )

            if msg.parent_idx is not None:
                print(f"       └─ Reply to message index {msg.parent_idx}")

        print(f"\n🔒 USER MAPPING:")
        for real_id, display_id in user_mapping.items():
            print(f"   {real_id} → {display_id}")

    @staticmethod
    def print_conversation_details(conversation: StandardizedConversation):
        """Print conversation structure details."""
        print(f"📝 CONVERSATION DETAILS:")
        print(f"   → ID: {conversation.id}")
        print(f"   → Source: {conversation.source.type.value}")
        print(
            f"   → Category: {getattr(conversation.category, 'value', 'None') if hasattr(conversation, 'category') and conversation.category else 'None'}"
        )
        print(f"   → Messages: {len(conversation.messages)}")
        print(f"   → Participants: {conversation.participant_count}")

        # Check global indexing
        indices = [msg.idx for msg in conversation.messages]
        print(f"   → Message indices: {indices}")

        # Check thread structure
        thread_messages = [
            msg for msg in conversation.messages if msg.parent_idx is not None
        ]
        if thread_messages:
            print(f"   → Thread replies: {len(thread_messages)}")

    @staticmethod
    def print_performance_breakdown(metrics: PerformanceMetrics):
        """Print concise performance metrics."""
        print(
            f"\n⏱️  Performance: API {metrics.extraction_time:.2f}s | Conversion {metrics.conversion_time:.2f}s | Total {metrics.total_time:.2f}s"
        )

    @staticmethod
    def print_results_summary(results: List[TestResult]):
        """Print clean test results summary."""
        print(
            f"\n📊 Results: {sum(1 for r in results if r.passed)}/{len(results)} tests passed",
            end="",
        )

        if all(r.passed for r in results):
            print(" ✅")
            print(f"\n🎉 All tests completed successfully!")
        else:
            print(" ❌")
            print(f"\n⚠️  Some tests failed:")
            for result in results:
                if not result.passed:
                    print(f"   • {result.name}: {result.message}")


class PerformanceTracker:
    """Tracks and manages performance timing."""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = PerformanceMetrics()

    def start_extraction(self):
        self.extraction_start = time.time()

    def end_extraction(self):
        self.metrics.extraction_time = time.time() - self.extraction_start

    def start_conversion(self):
        self.conversion_start = time.time()

    def end_conversion(self):
        self.metrics.conversion_time = time.time() - self.conversion_start

    def finalize(self):
        self.metrics.total_time = time.time() - self.start_time
        return self.metrics


class SlackTestClient:
    """Enhanced SlackClient wrapper for testing."""

    def __init__(self):
        self.client = SlackClient()

    async def fetch_with_config(self, config: TestConfig) -> StandardizedConversation:
        """Fetch conversations based on test configuration."""
        return await self.client.fetch_conversations_with_threads(
            from_datetime=config.from_datetime,
            to_datetime=config.to_datetime,
            limit=config.limit if config.limit else 1000,
        )

    def create_user_mapping(
        self, conversation: StandardizedConversation
    ) -> Dict[str, str]:
        """Create user mapping for display purposes."""
        user_mapping = {}
        user_counter = 1

        for msg in conversation.messages:
            if msg.author_id not in user_mapping:
                user_mapping[msg.author_id] = f"USER_{user_counter}"
                user_counter += 1

        return user_mapping


class MockDataFactory:
    """Factory for creating mock test data."""

    @staticmethod
    def create_mock_responses() -> Tuple[dict, dict]:
        """Create mock Slack API responses."""
        return MOCK_HISTORY_DATA, MOCK_THREAD_DATA

    @staticmethod
    def get_expected_message_order() -> List[str]:
        """Get expected message order after thread expansion."""
        return EXPECTED_MESSAGE_ORDER.copy()


# ============================================================================
# Test Base Classes
# ============================================================================


class BaseSlackTest:
    """Base class for Slack integration tests."""

    def __init__(self):
        self.formatter = TestOutputFormatter()
        self.tracker = PerformanceTracker()

    def _validate_credentials(self) -> bool:
        """Validate required credentials."""
        settings = get_settings()
        if not settings.slack_bot_token:
            print("❌ SLACK_BOT_TOKEN not found in .env")
            print("   Set up Slack integration first (see docs)")
            return False
        return True


# ============================================================================
# Specific Test Classes
# ============================================================================


class MockSlackTest(BaseSlackTest):
    """Tests using mock data."""

    async def test_conversation_structure(
        self, config: TestConfig = None
    ) -> TestResult:
        """Test StandardizedConversation structure with mock data."""
        if config is None:
            config = TestConfig()

        try:
            client = SlackTestClient()
            mock_history, mock_thread = MockDataFactory.create_mock_responses()

            # Setup mocks
            original_fetch = client.client.fetch_conversations_with_threads

            async def mock_fetch(*args, **kwargs):
                # Create mock StandardizedConversation
                messages = []
                idx = 0

                # Add thread messages first (maintaining thread structure)
                for msg_data in mock_thread["messages"]:
                    message = StandardizedMessage(
                        id=msg_data["ts"],  # Add required id field
                        idx=idx,
                        parent_idx=(
                            0 if idx > 0 else None
                        ),  # First message is root, others are replies
                        content=msg_data["text"],
                        author_id=msg_data["user"],
                        author_name=f"USER_{idx + 1}",
                        timestamp=datetime.fromtimestamp(float(msg_data["ts"])),
                        message_id=msg_data["ts"],
                    )
                    messages.append(message)
                    idx += 1

                # Add standalone messages
                for msg_data in mock_history["messages"][
                    1:
                ]:  # Skip first one (it's the thread root)
                    message = StandardizedMessage(
                        id=msg_data["ts"],  # Add required id field
                        idx=idx,
                        parent_idx=None,
                        content=msg_data["text"],
                        author_id=msg_data["user"],
                        author_name=f"USER_{idx + 1}",
                        timestamp=datetime.fromtimestamp(float(msg_data["ts"])),
                        message_id=msg_data["ts"],
                    )
                    messages.append(message)
                    idx += 1

                return StandardizedConversation(
                    id="mock_conversation_123",
                    source=Source(
                        type=SourceType.SLACK,
                        channel_id="C1234567890",
                        channel_name="test-channel",
                    ),
                    messages=messages,
                    participant_count=3,
                    category=ConversationCategory.TROUBLESHOOTING,
                    created_at=datetime.now(),
                    last_activity_at=datetime.now(),
                )

            # Apply mock
            client.client.fetch_conversations_with_threads = mock_fetch

            try:
                # Test conversation fetching
                conversation = await client.fetch_with_config(config)

                # Verbose output for mock data
                if config.verbose:
                    user_mapping = client.create_user_mapping(conversation)
                    self.formatter.print_verbose_extraction(conversation, user_mapping)
                    self.formatter.print_conversation_details(conversation)

                # Verify results
                has_id = conversation.id is not None
                has_global_indexing = all(
                    msg.idx is not None for msg in conversation.messages
                )
                has_thread_structure = any(
                    msg.parent_idx is not None for msg in conversation.messages
                )
                correct_source = conversation.source.type == SourceType.SLACK
                correct_message_count = len(conversation.messages) >= 3

                success = all(
                    [
                        has_id,
                        has_global_indexing,
                        has_thread_structure,
                        correct_source,
                        correct_message_count,
                    ]
                )

                details = []
                if not has_id:
                    details.append("missing conversation ID")
                if not has_global_indexing:
                    details.append("missing global indexing")
                if not has_thread_structure:
                    details.append("no thread structure detected")
                if not correct_source:
                    details.append("incorrect source type")
                if not correct_message_count:
                    details.append("insufficient messages")

                return TestResult(
                    "Conversation Structure",
                    success,
                    (
                        "; ".join(details)
                        if details
                        else f"✅ ID, indexing, threads, {len(conversation.messages)} messages"
                    ),
                )

            finally:
                # Restore original method
                client.client.fetch_conversations_with_threads = original_fetch

        except Exception as e:
            return TestResult("Conversation Structure", False, f"Exception: {e}")

    async def test_clean_architecture(self, config: TestConfig = None) -> TestResult:
        """Test clean architecture compliance (no masking, clean separation)."""
        if config is None:
            config = TestConfig()

        try:
            # Verify SlackClient doesn't have masking methods
            client = SlackTestClient()

            has_no_masking = not hasattr(client.client, "mask_messages")
            has_fetch_method = hasattr(
                client.client, "fetch_conversations_with_threads"
            )

            # Verify StandardizedConversation has required fields
            from app.models.thread import StandardizedConversation, StandardizedMessage

            conversation_fields = StandardizedConversation.model_fields.keys()
            message_fields = StandardizedMessage.model_fields.keys()

            has_conversation_id = "id" in conversation_fields
            has_message_indexing = (
                "idx" in message_fields and "parent_idx" in message_fields
            )

            success = all(
                [
                    has_no_masking,
                    has_fetch_method,
                    has_conversation_id,
                    has_message_indexing,
                ]
            )

            details = []
            if not has_no_masking:
                details.append("SlackClient still has masking methods")
            if not has_fetch_method:
                details.append("missing fetch_conversations_with_threads method")
            if not has_conversation_id:
                details.append("StandardizedConversation missing id field")
            if not has_message_indexing:
                details.append("StandardizedMessage missing idx/parent_idx fields")

            return TestResult(
                "Clean Architecture",
                success,
                (
                    "; ".join(details)
                    if details
                    else "✅ Clean SlackClient, proper field structure"
                ),
            )

        except Exception as e:
            return TestResult("Clean Architecture", False, f"Exception: {e}")


class RealSlackTest(BaseSlackTest):
    """Tests using real Slack API."""

    async def test_real_integration(self, config: TestConfig) -> TestResult:
        """Test with real Slack API."""
        # Validate credentials
        if not self._validate_credentials():
            return TestResult("Real Slack API", False, "Missing credentials")

        try:
            client = SlackTestClient()

            self.tracker.start_extraction()
            conversation = await client.fetch_with_config(config)
            self.tracker.end_extraction()

            if not conversation.messages:
                return TestResult(
                    "Real Slack API", True, "No messages found (empty channel)"
                )

            self.tracker.start_conversion()
            # No additional conversion needed - SlackClient now returns StandardizedConversation directly
            self.tracker.end_conversion()

            metrics = self.tracker.finalize()

            # Verbose mode output
            if config.verbose:
                user_mapping = client.create_user_mapping(conversation)
                self.formatter.print_verbose_extraction(conversation, user_mapping)
                self.formatter.print_conversation_details(conversation)
                self.formatter.print_performance_breakdown(metrics)
            else:
                self.formatter.print_performance_breakdown(metrics)

            success_details = f"Fetched {len(conversation.messages)} messages, {conversation.participant_count} participants"
            return TestResult("Real Slack API", True, success_details)

        except Exception as e:
            return TestResult("Real Slack API", False, f"Integration failed: {e}")


# ============================================================================
# Test Runner
# ============================================================================


class SlackTestRunner:
    """Main test runner."""

    def __init__(self):
        self.formatter = TestOutputFormatter()

    async def run_tests(self, test_mode: str, config: TestConfig) -> List[TestResult]:
        """Run tests based on mode."""
        print(f"🚀 Slack Integration Tests ({test_mode} mode)")
        self.formatter.print_config(config)

        results = []

        if test_mode == "list-channels":
            await self._list_slack_channels()
            return []

        if test_mode in ["mock", "quick"]:
            results.extend(await self._run_mock_tests(test_mode, config))

        if test_mode == "real":
            results.extend(await self._run_real_tests(config))

        self.formatter.print_results_summary(results)
        return results

    async def _run_mock_tests(
        self, test_mode: str, config: TestConfig = None
    ) -> List[TestResult]:
        """Run mock data tests."""
        self.formatter.print_header("Mock Data Tests")

        if config is None:
            config = TestConfig()

        mock_test = MockSlackTest()
        results = []

        # Conversation structure test
        structure_result = await mock_test.test_conversation_structure(config)
        self.formatter.print_test_status(
            "Conversation Structure", structure_result.passed, structure_result.message
        )
        results.append(structure_result)

        if test_mode != "quick":
            # Clean architecture test
            architecture_result = await mock_test.test_clean_architecture(config)
            self.formatter.print_test_status(
                "Clean Architecture",
                architecture_result.passed,
                architecture_result.message,
            )
            results.append(architecture_result)

        return results

    async def _run_real_tests(self, config: TestConfig) -> List[TestResult]:
        """Run real API tests."""
        self.formatter.print_header("Real Slack API Tests")

        real_test = RealSlackTest()
        result = await real_test.test_real_integration(config)
        self.formatter.print_test_status(
            "Real Slack API", result.passed, result.message
        )
        return [result]

    async def _list_slack_channels(self):
        """List available Slack channels."""
        print("\n📋 Listing Slack channels...")

        settings = get_settings()
        if not settings.slack_bot_token:
            print("❌ SLACK_BOT_TOKEN not found in .env")
            return

        try:
            client = SlackClient()
            channel_id = client.settings.slack_channel_id
            if channel_id:
                print(f"✅ Configured channel: {channel_id}")
            else:
                print("⚠️  No SLACK_CHANNEL_ID configured in .env")
                print("   Add SLACK_CHANNEL_ID=C1234567890 to your .env file")
        except Exception as e:
            print(f"❌ Error: {e}")


# ============================================================================
# Configuration Parser
# ============================================================================


class ConfigParser:
    """Parse command line arguments into test configuration."""

    @staticmethod
    def parse_args() -> Tuple[str, TestConfig]:
        """Parse command line arguments."""
        import argparse

        parser = argparse.ArgumentParser(
            description="Test Slack Integration with Clean Architecture",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --mock                           # Mock data testing
  %(prog)s --real --verbose                 # Real API with detailed output
  %(prog)s --real --limit 25                # Real API, max 25 messages
  %(prog)s --real --days 7                  # Real API, last 7 days
  %(prog)s --real --hours 24 --verbose      # Real API, last 24 hours, detailed
  %(prog)s --real --from 2026-02-01         # Real API, from specific date
  %(prog)s --real --from 2026-02-01 --to 2026-02-05  # Date range
  %(prog)s --quick                          # Quick mock test
  %(prog)s --list-channels                  # List channels
            """,
        )

        # Test mode arguments
        parser.add_argument(
            "--mock", action="store_true", help="Test with mock data (default)"
        )
        parser.add_argument(
            "--real", action="store_true", help="Test with real Slack API"
        )
        parser.add_argument(
            "--quick", action="store_true", help="Quick test with mock data"
        )
        parser.add_argument(
            "--list-channels", action="store_true", help="List Slack channels"
        )

        # Configuration arguments (for --real mode)
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Show detailed test output with message content",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of messages to extract (default: 10)",
        )
        parser.add_argument(
            "--no-limit", action="store_true", help="Extract all messages in time range"
        )
        parser.add_argument(
            "--hours", type=int, help="Extract messages from last N hours"
        )
        parser.add_argument(
            "--days", type=int, help="Extract messages from last N days"
        )
        parser.add_argument(
            "--from",
            dest="from_date",
            help="Start date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')",
        )
        parser.add_argument(
            "--to",
            dest="to_date",
            help="End date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')",
        )

        args = parser.parse_args()

        # Determine test mode
        if args.real:
            test_mode = "real"
        elif args.quick:
            test_mode = "quick"
        elif args.list_channels:
            test_mode = "list-channels"
        else:
            test_mode = "mock"  # default

        # Parse test configuration
        config = ConfigParser._create_test_config(args, test_mode)

        return test_mode, config

    @staticmethod
    def _create_test_config(args, test_mode: str) -> TestConfig:
        """Create test configuration from arguments."""
        config = TestConfig(verbose=args.verbose)

        if test_mode != "real":
            return config

        # Handle message limits
        if args.no_limit:
            config.limit = None
        elif args.limit:
            config.limit = args.limit
        # else: keep default limit = 10

        # Handle time ranges
        now = datetime.now()

        if args.hours:
            config.from_datetime = now - timedelta(hours=args.hours)
        elif args.days:
            config.from_datetime = now - timedelta(days=args.days)
        elif args.from_date:
            config.from_datetime = ConfigParser._parse_datetime(args.from_date, "from")

        if args.to_date:
            config.to_datetime = ConfigParser._parse_datetime(
                args.to_date, "to", end_of_day=True
            )

        return config

    @staticmethod
    def _parse_datetime(
        date_str: str, field_name: str, end_of_day: bool = False
    ) -> datetime:
        """Parse datetime string."""
        try:
            if len(date_str) > 10:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                base_date = datetime.strptime(date_str, "%Y-%m-%d")
                if end_of_day:
                    return base_date.replace(hour=23, minute=59, second=59)
                return base_date
        except ValueError:
            print(f"❌ Invalid --{field_name} date format: {date_str}")
            print("   Use: YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS'")
            sys.exit(1)


# ============================================================================
# Main Function
# ============================================================================


async def main():
    """Main test execution function."""
    test_mode, config = ConfigParser.parse_args()

    print(f"\n🚀 Running Slack integration tests in '{test_mode}' mode...\n")

    runner = SlackTestRunner()
    results = await runner.run_tests(test_mode, config)

    # Print usage examples
    print(f"\n💡 Test mode examples:")
    print(
        f"   python {sys.argv[0]} --mock                           # Mock data testing"
    )
    print(
        f"   python {sys.argv[0]} --real --verbose                 # Real API with details"
    )
    print(
        f"   python {sys.argv[0]} --real --limit 25                # Real API, 25 messages"
    )
    print(
        f"   python {sys.argv[0]} --real --days 7 --verbose        # Last 7 days, detailed"
    )
    print(f"   python {sys.argv[0]} --real --hours 24                # Last 24 hours")
    print(
        f"   python {sys.argv[0]} --real --from 2026-02-01         # From specific date"
    )
    print(f"   python {sys.argv[0]} --quick                          # Quick mock test")
    print(f"   python {sys.argv[0]} --list-channels                  # List channels\n")


if __name__ == "__main__":
    asyncio.run(main())
