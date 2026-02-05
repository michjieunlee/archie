"""
Refactored Slack Integration Test Suite

This script tests the complete Slack pipeline with a clean, maintainable structure:
- Thread expansion and context preservation
- PII masking integration
- Real Slack API integration (optional)

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
from app.integrations.slack.models import SlackMessage, SlackThread
from app.models.thread import StandardizedThread, StandardizedMessage, SourceType
from app.ai_core.masking.pii_masker import PIIMasker
from app.config import get_settings



# ============================================================================
# Constants and Test Data
# ============================================================================

MOCK_HISTORY_DATA = {
    "messages": [
        {
            "ts": "1706123400.123456",
            "user": "U123USER1",
            "text": "Hey team, I need help with user ID I123456. Contact me at john.doe@company.com or +1-555-0123",
            "reply_count": 2,
            "reactions": [{"name": "thumbsup", "count": 1}],
            "attachments": []
        },
        {
            "ts": "1706123300.654321",
            "user": "U456USER2",
            "text": "Quick update: My phone is 555-9876, email alice@company.com",
            "reactions": [],
            "attachments": []
        }
    ]
}

MOCK_THREAD_DATA = {
    "messages": [
        {
            "ts": "1706123400.123456",
            "user": "U123USER1",
            "text": "Hey team, I need help with user ID I123456. Contact me at john.doe@company.com or +1-555-0123",
            "thread_ts": "1706123400.123456"
        },
        {
            "ts": "1706123450.789012",
            "user": "U456USER2",
            "text": "I can help! My ID is D987654. Email me at alice@company.com",
            "thread_ts": "1706123400.123456"
        },
        {
            "ts": "1706123500.345678",
            "user": "U789USER3",
            "text": "Thanks both! Call me at 123-4567 if needed",
            "thread_ts": "1706123400.123456"
        }
    ]
}

EXPECTED_MESSAGE_ORDER = [
    "Hey team, I need help with user ID I123456. Contact me at john.doe@company.com or +1-555-0123",
    "I can help! My ID is D987654. Email me at alice@company.com",
    "Thanks both! Call me at 123-4567 if needed",
    "Quick update: My phone is 555-9876, email alice@company.com"
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
    masking_time: float = 0.0
    conversion_time: float = 0.0

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
                    hours_ago = int((datetime.now() - config.from_datetime).total_seconds() / 3600)
                    config_parts.append(f"last {hours_ago}h")
                else:
                    config_parts.append(f"last {days_ago}d")

        if config.verbose:
            config_parts.append("verbose mode")

        if config_parts:
            print(f"📅 Configuration: {', '.join(config_parts)}")
            print()

    @staticmethod
    def print_verbose_extraction(slack_thread: SlackThread, user_mapping: Dict[str, str]):
        """Print detailed extraction results."""
        print("📊 RAW EXTRACTION RESULTS:")

        for i, msg in enumerate(slack_thread.messages, 1):
            user_display = user_mapping.get(msg.user_id, f"USER_{len(user_mapping) + 1}")
            timestamp_str = msg.timestamp.strftime('%H:%M:%S')
            preview = msg.text[:60] + "..." if len(msg.text) > 60 else msg.text

            print(f"   {i:2d}. [{user_display}] {timestamp_str}: {preview}")

            if msg.reactions:
                reactions_str = ", ".join([f"{r['name']}({r['count']})" for r in msg.reactions])
                print(f"       👍 {reactions_str}")

        print(f"\n🔒 USER MAPPING:")
        for real_id, display_id in user_mapping.items():
            print(f"   {real_id} → {display_id}")

    @staticmethod
    def print_pii_processing_details(original_messages: List[SlackMessage],
                                   masked_thread: StandardizedThread):
        """Print detailed PII processing information."""
        import re

        # Count PII patterns in original messages
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'[\+]?[1-9]?[\-\s]?\(?[0-9]{3}\)?[\-\s]?[0-9]{3}[\-\s]?[0-9]{4}'
        id_pattern = r'\b[A-Z]\d{6,}\b'

        total_emails = sum(len(re.findall(email_pattern, msg.text)) for msg in original_messages)
        total_phones = sum(len(re.findall(phone_pattern, msg.text)) for msg in original_messages)
        total_ids = sum(len(re.findall(id_pattern, msg.text)) for msg in original_messages)

        if total_emails + total_phones + total_ids > 0:
            print(f"🔒 PII MASKING APPLIED:")
            transformations = []
            if total_emails > 0:
                transformations.append(f"{total_emails} email{'s' if total_emails != 1 else ''}")
            if total_phones > 0:
                transformations.append(f"{total_phones} phone{'s' if total_phones != 1 else ''}")
            if total_ids > 0:
                transformations.append(f"{total_ids} ID{'s' if total_ids != 1 else ''}")

            print(f"   → Detected: {', '.join(transformations)}")
            print(f"   → Transformations: {total_emails + total_phones + total_ids} total replacements")

    @staticmethod
    def print_processed_messages(masked_thread: StandardizedThread, user_mapping: Dict[str, str]):
        """Print processed message content after PII masking."""
        print(f"\n📝 PROCESSED MESSAGE CONTENT:")

        for i, msg in enumerate(masked_thread.messages, 1):
            user_display = user_mapping.get(msg.author_id, f"USER_{i}")
            timestamp_str = msg.timestamp.strftime('%H:%M:%S')
            preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content

            print(f"   {i:2d}. [{user_display}] {timestamp_str}: {preview}")

        # Validate no PII leaked through
        TestOutputFormatter._validate_pii_removal(masked_thread)

    @staticmethod
    def _validate_pii_removal(masked_thread: StandardizedThread):
        """Validate that PII was properly removed from processed messages."""
        import re

        # Patterns that should NOT appear in masked content
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'[\+]?[1-9]?[\-\s]?\(?[0-9]{3}\)?[\-\s]?[0-9]{3}[\-\s]?[0-9]{4}'

        leaked_pii = []
        for msg in masked_thread.messages:
            emails = re.findall(email_pattern, msg.content)
            phones = re.findall(phone_pattern, msg.content)
            leaked_pii.extend(emails + phones)

        if leaked_pii:
            print(f"⚠️  PII Validation: {len(leaked_pii)} potential leaks detected")
            for pii in leaked_pii[:3]:  # Show first 3
                print(f"      → {pii}")
        else:
            print(f"✅ PII Validation: No sensitive data detected in final output")

    @staticmethod
    def print_performance_breakdown(metrics: PerformanceMetrics):
        """Print concise performance metrics."""
        print(f"\n⏱️  Performance: API {metrics.extraction_time:.2f}s | Masking {metrics.masking_time:.2f}s | Total {metrics.total_time:.2f}s")

    @staticmethod
    def print_results_summary(results: List[TestResult]):
        """Print clean test results summary."""
        print(f"\n📊 Results: {sum(1 for r in results if r.passed)}/{len(results)} tests passed", end="")

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

    def start_masking(self):
        self.masking_start = time.time()

    def end_masking(self):
        self.metrics.masking_time = time.time() - self.masking_start

    def finalize(self):
        self.metrics.total_time = time.time() - self.start_time
        self.metrics.conversion_time = (
            self.metrics.total_time -
            self.metrics.extraction_time -
            self.metrics.masking_time
        )
        return self.metrics


class SlackTestClient:
    """Enhanced SlackClient wrapper for testing."""

    def __init__(self):
        self.client = SlackClient()

    async def extract_with_config(self, config: TestConfig) -> SlackThread:
        """Extract messages based on test configuration."""
        return await self.client.extract_conversations_with_threads(
            from_datetime=config.from_datetime,
            to_datetime=config.to_datetime,
            limit=config.limit if config.limit else 1000
        )

    def convert_to_standardized(self, slack_thread: SlackThread) -> StandardizedThread:
        """Convert SlackThread to StandardizedThread."""
        return self.client.convert_to_standardized_thread(slack_thread)

    def create_user_mapping(self, slack_thread: SlackThread) -> Dict[str, str]:
        """Create user mapping for display purposes."""
        user_mapping = {}
        user_counter = 1

        for msg in slack_thread.messages:
            if msg.user_id not in user_mapping:
                user_mapping[msg.user_id] = f"USER_{user_counter}"
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

    def _create_slack_thread_from_messages(self, messages: List[SlackMessage]) -> SlackThread:
        """Create SlackThread from message list."""
        return SlackThread(
            channel_id="C1234567890",
            channel_name="test-channel",
            messages=messages,
            metadata={"threads_expanded": True}
        )


# ============================================================================
# Specific Test Classes
# ============================================================================

class MockSlackTest(BaseSlackTest):
    """Tests using mock data."""

    async def test_thread_expansion(self, config: TestConfig = None) -> TestResult:
        """Test thread expansion with mock data."""
        if config is None:
            config = TestConfig()

        try:
            client = SlackTestClient()
            mock_history, mock_thread = MockDataFactory.create_mock_responses()

            # Setup mocks
            original_get_history = client.client.get_conversation_history_with_raw_data
            original_get_replies = client.client.get_thread_replies

            async def mock_get_history(*args, **kwargs):
                messages = []
                for msg_data in mock_history["messages"]:
                    message = client.client._parse_message(msg_data)
                    if message:
                        messages.append(message)
                return messages, mock_history["messages"]

            async def mock_get_replies(channel_id, thread_ts):
                messages = []
                for msg_data in mock_thread["messages"]:
                    message = client.client._parse_message(msg_data)
                    if message:
                        messages.append(message)
                return messages

            # Apply mocks
            client.client.get_conversation_history_with_raw_data = mock_get_history
            client.client.get_thread_replies = mock_get_replies

            try:
                # Test thread expansion
                slack_thread = await client.client.extract_conversations_with_threads(
                    channel_id="C1234567890",
                    limit=50
                )

                # Verbose output for mock data
                if config.verbose:
                    user_mapping = client.create_user_mapping(slack_thread)
                    self.formatter.print_verbose_extraction(slack_thread, user_mapping)

                # Verify results
                expected_order = MockDataFactory.get_expected_message_order()
                actual_order = [msg.text for msg in slack_thread.messages]

                # Check results
                order_correct = actual_order == expected_order
                thread_preserved = (
                    len(slack_thread.messages) >= 3 and
                    slack_thread.threads_expanded and
                    slack_thread.participant_count == 3
                )

                success = order_correct and thread_preserved

                return TestResult("Thread Expansion", success,
                                "Message order mismatch" if not order_correct else
                                "Thread context not preserved" if not thread_preserved else None)

            finally:
                # Restore original methods
                client.client.get_conversation_history_with_raw_data = original_get_history
                client.client.get_thread_replies = original_get_replies

        except Exception as e:
            return TestResult("Thread Expansion", False, f"Exception: {e}")

    async def test_complete_pipeline(self, config: TestConfig = None) -> TestResult:
        """Test complete pipeline with mock data."""
        if config is None:
            config = TestConfig()

        try:
            # Create test client and data without re-running thread expansion
            client = SlackTestClient()
            mock_history, mock_thread = MockDataFactory.create_mock_responses()

            # Create mock messages (simplified for pipeline test)
            messages = []
            for msg_data in (mock_history["messages"] + mock_thread["messages"][1:]):
                message = client.client._parse_message(msg_data)
                if message:
                    messages.append(message)

            slack_thread = self._create_slack_thread_from_messages(messages)

            # Apply PII masking
            pii_masker = PIIMasker()
            temp_thread = client.convert_to_standardized(slack_thread)
            masked_threads = await pii_masker.mask_threads([temp_thread])
            masked_thread = masked_threads[0]

            # Update SlackMessages with masked user names
            user_mapping = {msg.author_id: msg.author_name for msg in masked_thread.messages}
            for slack_msg in slack_thread.messages:
                slack_msg.user_name = user_mapping.get(slack_msg.user_id)

            # Create final thread
            final_thread = client.convert_to_standardized(slack_thread)

            # Verbose output for mock data pipeline
            if config.verbose:
                user_mapping_display = client.create_user_mapping(slack_thread)
                self.formatter.print_pii_processing_details(slack_thread.messages, masked_thread)
                self.formatter.print_processed_messages(masked_thread, user_mapping_display)

            # Verify results
            all_masked = all(msg.is_masked for msg in final_thread.messages)
            user_names_masked = all(
                msg.author_name and msg.author_name.startswith("USER_")
                for msg in final_thread.messages
            )
            thread_count_preserved = len(final_thread.messages) == len(messages)

            success = all([all_masked, user_names_masked, thread_count_preserved])

            return TestResult("Complete Pipeline", success,
                            "Failed validation checks" if not success else None)

        except Exception as e:
            return TestResult("Complete Pipeline", False, f"Pipeline failed: {e}")


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
            slack_thread = await client.extract_with_config(config)
            self.tracker.end_extraction()

            if not slack_thread.messages:
                return TestResult("Real Slack API", True, "No messages found (empty channel)")

            # Test complete pipeline
            self.tracker.start_masking()

            pii_masker = PIIMasker()
            temp_thread = client.convert_to_standardized(slack_thread)
            masked_threads = await pii_masker.mask_threads([temp_thread])
            masked_thread = masked_threads[0]

            self.tracker.end_masking()
            metrics = self.tracker.finalize()

            # Verbose mode output
            if config.verbose:
                user_mapping = client.create_user_mapping(slack_thread)
                self.formatter.print_verbose_extraction(slack_thread, user_mapping)
                self.formatter.print_pii_processing_details(slack_thread.messages, masked_thread)
                self.formatter.print_processed_messages(masked_thread, user_mapping)
                self.formatter.print_performance_breakdown(metrics)
            else:
                self.formatter.print_performance_breakdown(metrics)

            success_details = f"Extracted {len(slack_thread.messages)} messages, {masked_thread.participant_count} participants"
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

    async def _run_mock_tests(self, test_mode: str, config: TestConfig = None) -> List[TestResult]:
        """Run mock data tests."""
        self.formatter.print_header("Mock Data Tests")

        if config is None:
            config = TestConfig()

        mock_test = MockSlackTest()
        results = []

        # Thread expansion test
        thread_result = await mock_test.test_thread_expansion(config)
        self.formatter.print_test_status("Thread Expansion", thread_result.passed,
                                       "Extracted 4 messages, threads expanded correctly" if thread_result.passed else thread_result.message)
        results.append(thread_result)

        if test_mode != "quick":
            # Complete pipeline test
            pipeline_result = await mock_test.test_complete_pipeline(config)
            self.formatter.print_test_status("Complete Pipeline", pipeline_result.passed,
                                           "PII masking applied, USER_X format validated" if pipeline_result.passed else pipeline_result.message)
            results.append(pipeline_result)

        return results

    async def _run_real_tests(self, config: TestConfig) -> List[TestResult]:
        """Run real API tests."""
        self.formatter.print_header("Real Slack API Tests")

        real_test = RealSlackTest()
        result = await real_test.test_real_integration(config)
        self.formatter.print_test_status("Real Slack API", result.passed, result.message)
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
            description="Test Slack Integration",
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
            """
        )

        # Test mode arguments
        parser.add_argument("--mock", action="store_true", help="Test with mock data (default)")
        parser.add_argument("--real", action="store_true", help="Test with real Slack API")
        parser.add_argument("--quick", action="store_true", help="Quick test with mock data")
        parser.add_argument("--list-channels", action="store_true", help="List Slack channels")

        # Configuration arguments (for --real mode)
        parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed test output with message content")
        parser.add_argument("--limit", type=int, help="Maximum number of messages to extract (default: 10)")
        parser.add_argument("--no-limit", action="store_true", help="Extract all messages in time range")
        parser.add_argument("--hours", type=int, help="Extract messages from last N hours")
        parser.add_argument("--days", type=int, help="Extract messages from last N days")
        parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')")
        parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')")

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
            config.to_datetime = ConfigParser._parse_datetime(args.to_date, "to", end_of_day=True)

        return config

    @staticmethod
    def _parse_datetime(date_str: str, field_name: str, end_of_day: bool = False) -> datetime:
        """Parse datetime string."""
        try:
            if len(date_str) > 10:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                base_date = datetime.strptime(date_str, '%Y-%m-%d')
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
    print(f"   python {sys.argv[0]} --mock                           # Mock data testing")
    print(f"   python {sys.argv[0]} --real --verbose                 # Real API with details")
    print(f"   python {sys.argv[0]} --real --limit 25                # Real API, 25 messages")
    print(f"   python {sys.argv[0]} --real --days 7 --verbose        # Last 7 days, detailed")
    print(f"   python {sys.argv[0]} --real --hours 24                # Last 24 hours")
    print(f"   python {sys.argv[0]} --real --from 2026-02-01         # From specific date")
    print(f"   python {sys.argv[0]} --quick                          # Quick mock test")
    print(f"   python {sys.argv[0]} --list-channels                  # List channels\n")


if __name__ == "__main__":
    asyncio.run(main())