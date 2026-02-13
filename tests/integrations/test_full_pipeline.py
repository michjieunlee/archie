"""
Full Pipeline Integration Test for KBOrchestrator

Tests the complete KB creation pipeline:
1. Text input → PII masking → KB extraction → Matching → Generation
2. Slack messages → Full pipeline (requires --slack flag)
3. Different KB categories (troubleshooting, processes, decisions)
4. UPDATE matching detection

Modes:
    --mock  : Dry-run mode (DRY_RUN=true), no PR created (default)
    --real  : Real mode (DRY_RUN=false), creates actual PRs
    --quick : Quick smoke test (troubleshooting only, dry-run)

Options:
    --test <name>  : Run specific test (troubleshooting, process, update)
    --slack        : Include Slack tests (requires SLACK_BOT_TOKEN)
    --verbose, -v  : Show detailed output

Usage Examples:
    python tests/integrations/test_full_pipeline.py --mock                         # Dry-run, all text tests
    python tests/integrations/test_full_pipeline.py --mock --test process          # Dry-run, process only
    python tests/integrations/test_full_pipeline.py --real --test process -v       # Creates PR, process only
    python tests/integrations/test_full_pipeline.py --real --slack -v              # Creates PRs with Slack
    python tests/integrations/test_full_pipeline.py --mock --slack --slack-limit 1 # Slack with 1 message

Requirements:
- OPENAI_API_KEY or gen_ai_hub proxy configured
- GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME in .env
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (for --slack tests)
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass

from app.services.kb_orchestrator import KBOrchestrator
from app.models.api_responses import KBActionType
from app.config import get_settings


def setup_logging(verbose: bool = False):
    """Configure logging based on verbose mode."""
    log_level = logging.DEBUG if verbose else logging.WARNING
    
    # Configure root logger for app modules
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s | %(name)s | %(message)s',
        force=True,
    )
    
    # Set app modules to appropriate level
    for module in ['app.services', 'app.ai_core', 'app.integrations']:
        logging.getLogger(module).setLevel(log_level)
    
    # Always suppress noisy third-party loggers
    for module in ['httpx', 'httpcore', 'urllib3', 'openai']:
        logging.getLogger(module).setLevel(logging.WARNING)


# ============================================================================
# Test Data Constants
# ============================================================================

TROUBLESHOOTING_TEXT = """
We encountered a critical production issue with the payment service yesterday.

**Problem**: Payment transactions were failing with timeout errors after the 
deployment of version 2.3.5. Users reported seeing "Payment processing failed" 
messages when trying to complete checkout.

**Investigation**: 
- John from the backend team found that the database connection pool was exhausted
- The logs showed connection timeout after 30 seconds
- CPU usage on the payment-db server was at 95%

**Root Cause**: The new version introduced a memory leak in the connection 
handling code. Connections were not being properly released after transactions.

**Solution**:
1. Rolled back to version 2.3.4
2. Fixed the connection leak in the PaymentProcessor class
3. Added connection pool monitoring alerts
4. Deployed fix as version 2.3.6

**Prevention**:
- Added integration tests for connection pool behavior
- Set up alerts for connection pool utilization > 80%
- Added code review checklist item for resource cleanup

Contact Sarah (sarah@company.com) or Mike (mike@company.com) for questions.
"""

PROCESS_TEXT = """
**New Developer Onboarding Process**

**Overview**: This document outlines the step-by-step process for onboarding 
new developers to the engineering team. Following this process ensures new 
team members are productive within their first week.

**Prerequisites**:
- GitHub account created and added to the organization
- Slack workspace invite accepted
- VPN access granted by IT team
- Hardware (laptop) received and configured
- Manager has assigned a buddy/mentor

**Step-by-Step Process**:

1. Day 1 - Environment Setup:
   - Clone the main repositories from GitHub (frontend, backend, infra)
   - Install required dependencies (Node.js 18+, Python 3.11+, Docker Desktop)
   - Run the dev-setup.sh script to configure local environment
   - Configure IDE (VSCode recommended) with team extensions pack
   - Verify you can run all services locally with `make dev`

2. Day 1-2 - Access Configuration:
   - Request access to AWS console (dev account) via IT ticket
   - Configure SSO for internal tools (Jira, Confluence, Datadog)
   - Set up 2FA for all accounts (use authenticator app, not SMS)
   - Add SSH keys to GitHub and internal servers

3. Day 2-3 - Codebase Orientation:
   - Walk through architecture documentation in Confluence
   - Pair with buddy on a small bug fix to understand the workflow
   - Review coding standards document and PR guidelines
   - Attend architecture overview session with tech lead

4. Day 4-5 - First Contribution:
   - Pick up a "good-first-issue" ticket from the sprint backlog
   - Submit first PR for code review
   - Attend daily standup and weekly sprint planning
   - Complete security awareness training

**Validation Steps**:
- Can run all services locally without errors
- Can create a branch, commit, and open a PR
- Has access to all required systems (AWS, Jira, Slack channels)
- Has completed all required training modules

**Common Issues and Troubleshooting**:
- Docker permission issues on Mac → Run: sudo chmod 666 /var/run/docker.sock
- Node version mismatch → Use nvm to install and switch to correct version
- VPN connection drops → Contact IT, may need to update VPN client
- GitHub SSH issues → Regenerate keys and update GitHub settings

**Related Processes**:
- Offboarding Process
- Team Access Request Process
- Hardware Request Process

Contact the Engineering Lead (eng-lead@company.com) or your buddy for questions.
"""

UPDATE_TEXT = """
Follow-up on the payment service timeout issue from last week.

**New Findings**:
After further investigation, we discovered additional issues related to the 
payment service timeouts:

- The issue also affects batch processing jobs, not just real-time transactions
- Memory leak only manifests under high load (>1000 requests/second)
- Connection pool exhaustion happens faster on the replica database servers

**Additional Symptoms Observed**:
- Batch payment reconciliation jobs timing out after midnight
- Increased GC pauses (up to 5 seconds) on payment-api pods
- Replica lag increasing to 30+ seconds during peak hours

**New Solution Steps**:
1. Increased JVM heap from 2GB to 4GB as interim fix
2. Scheduled weekly connection pool restarts until permanent fix deployed
3. Added circuit breaker pattern for database connections
4. Implemented connection pool pre-warming on pod startup

**Updated Prevention Measures**:
- Set up load testing to simulate >1000 req/s before each release
- Added memory profiling to CI pipeline
- Created runbook for connection pool exhaustion incidents

This is a continuation of the original payment service timeout incident.
Contact the payments team for more details.
"""


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TestConfig:
    """Test configuration settings."""
    verbose: bool = False
    dry_run: bool = True
    include_slack: bool = False  # Whether to include Slack tests
    slack_limit: int = 10
    slack_hours: int = 24
    test_filter: Optional[str] = None  # Filter to run specific test

    def has_custom_settings(self) -> bool:
        return self.verbose or not self.dry_run or self.test_filter is not None or self.include_slack


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
    total_time: float = 0.0


# ============================================================================
# Utility Classes
# ============================================================================

class TestOutputFormatter:
    """Handles all test output formatting."""

    @staticmethod
    def print_divider(char: str = "=", length: int = 60):
        print(char * length)

    @staticmethod
    def print_header(title: str, emoji: str = "🧪"):
        print(f"\n{emoji} {title}")

    @staticmethod
    def print_test_status(test_name: str, passed: bool, details: str = None):
        status = "✅ PASS" if passed else "❌ FAIL"
        dots = "." * (45 - len(test_name))
        print(f"  {test_name} {dots} {status}")
        if details:
            print(f"      → {details}")

    @staticmethod
    def print_config(config: TestConfig):
        if not config.has_custom_settings():
            return
        settings = get_settings()
        print(f"🔧 Configuration: dry_run={settings.dry_run}")
        print()

    @staticmethod
    def print_verbose_result(result):
        """Print detailed result information."""
        print(f"\n   📊 Status: {result.status}")
        print(f"   🎯 Action: {result.action.value.upper()}")
        
        if result.reason:
            print(f"   💬 Reason: {result.reason}")
        
        if result.kb_document_title:
            print(f"   📋 Title: {result.kb_document_title}")
            print(f"   📁 Category: {result.kb_category}")
            if result.ai_confidence:
                print(f"   🎯 Confidence: {result.ai_confidence:.1%}")
        
        if result.ai_reasoning:
            print(f"   🤖 AI Reasoning: {result.ai_reasoning[:200]}..." if len(result.ai_reasoning) > 200 else f"   🤖 AI Reasoning: {result.ai_reasoning}")
        
        if result.kb_summary:
            print(f"   📝 Summary: {result.kb_summary}")
        
        if result.pr_url:
            print(f"   🔗 PR URL: {result.pr_url}")
        
        if result.kb_file_path:
            print(f"   📄 File: {result.kb_file_path}")
        
        if result.kb_markdown_content:
            print(f"\n   📝 Markdown Preview (first 500 chars):")
            print("   " + "-" * 50)
            preview = result.kb_markdown_content[:500].replace('\n', '\n   ')
            print(f"   {preview}")
            if len(result.kb_markdown_content) > 500:
                print(f"   ... [truncated, total {len(result.kb_markdown_content)} chars]")
            print("   " + "-" * 50)

    @staticmethod
    def print_results_summary(results: List[TestResult]):
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        print(f"\n📊 Results: {passed}/{total} tests passed", end="")
        
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

    def finalize(self):
        self.metrics.total_time = time.time() - self.start_time
        return self.metrics


# ============================================================================
# Test Classes
# ============================================================================

class BasePipelineTest:
    """Base class for pipeline tests."""

    def __init__(self):
        self.formatter = TestOutputFormatter()
        self.tracker = PerformanceTracker()

    def _validate_env(self) -> bool:
        """Validate required environment variables."""
        settings = get_settings()
        if not settings.github_token:
            print("❌ GITHUB_TOKEN not found in .env")
            return False
        return True


class MockPipelineTest(BasePipelineTest):
    """Tests that can run with mocked/minimal real API calls."""

    async def test_troubleshooting_kb(self, config: TestConfig) -> TestResult:
        """Test troubleshooting category extraction."""
        try:
            orchestrator = KBOrchestrator()
            
            self.tracker.start_extraction()
            result = await orchestrator.process_text_input(
                text=TROUBLESHOOTING_TEXT,
                title="Payment Service Timeout Issue",
                metadata={"test": "troubleshooting"},
            )
            self.tracker.end_extraction()
            
            if config.verbose:
                self.formatter.print_verbose_result(result)
            
            # Validate
            if result.status == "error":
                return TestResult("Troubleshooting KB", False, result.reason)
            
            if result.action == KBActionType.IGNORE:
                return TestResult("Troubleshooting KB", True, "Content ignored (valid outcome)")
            
            if result.action in [KBActionType.CREATE, KBActionType.UPDATE]:
                if result.kb_category != "troubleshooting":
                    return TestResult("Troubleshooting KB", False, 
                                     f"Expected troubleshooting, got {result.kb_category}")
                return TestResult("Troubleshooting KB", True, 
                                 f"Category: {result.kb_category}, Action: {result.action.value}")
            
            return TestResult("Troubleshooting KB", True, "Completed")
            
        except Exception as e:
            return TestResult("Troubleshooting KB", False, f"Exception: {e}")

    async def test_process_kb(self, config: TestConfig) -> TestResult:
        """Test processes category extraction."""
        try:
            orchestrator = KBOrchestrator()
            
            self.tracker.start_extraction()
            result = await orchestrator.process_text_input(
                text=PROCESS_TEXT,
                title="New Developer Onboarding Process",
                metadata={"test": "process"},
            )
            self.tracker.end_extraction()
            
            if config.verbose:
                self.formatter.print_verbose_result(result)
            
            # Validate
            if result.status == "error":
                return TestResult("Process KB", False, result.reason)
            
            if result.action == KBActionType.IGNORE:
                return TestResult("Process KB", True, "Content ignored (valid outcome)")
            
            if result.action in [KBActionType.CREATE, KBActionType.UPDATE]:
                if result.kb_category != "processes":
                    return TestResult("Process KB", False, 
                                     f"Expected processes, got {result.kb_category}")
                return TestResult("Process KB", True, 
                                 f"Category: {result.kb_category}, Action: {result.action.value}")
            
            return TestResult("Process KB", True, "Completed")
            
        except Exception as e:
            return TestResult("Process KB", False, f"Exception: {e}")

    async def test_update_matching(self, config: TestConfig) -> TestResult:
        """Test UPDATE matching detection."""
        try:
            orchestrator = KBOrchestrator()
            
            result = await orchestrator.process_text_input(
                text=UPDATE_TEXT,
                title="Payment Service Timeout - Additional Findings",
                metadata={"test": "update_matching"},
            )
            
            if config.verbose:
                self.formatter.print_verbose_result(result)
            
            # Validate
            if result.status == "error":
                return TestResult("Update Matching", False, result.reason)
            
            # Both CREATE and UPDATE are valid outcomes depending on existing KB
            if result.action == KBActionType.UPDATE:
                return TestResult("Update Matching", True, 
                                 f"UPDATE detected (matched existing KB)")
            elif result.action == KBActionType.CREATE:
                return TestResult("Update Matching", True, 
                                 f"CREATE returned (no existing KB found)")
            elif result.action == KBActionType.IGNORE:
                return TestResult("Update Matching", True, "Content ignored")
            
            return TestResult("Update Matching", True, f"Action: {result.action.value}")
            
        except Exception as e:
            return TestResult("Update Matching", False, f"Exception: {e}")


class RealPipelineTest(BasePipelineTest):
    """Tests that require real Slack API."""

    async def test_slack_pipeline(self, config: TestConfig) -> TestResult:
        """Test full pipeline with real Slack messages."""
        settings = get_settings()
        
        if not settings.slack_bot_token:
            return TestResult("Slack Pipeline", True, "⚠️ Skipped (no SLACK_BOT_TOKEN)")
        
        try:
            orchestrator = KBOrchestrator()
            
            to_datetime = datetime.now()
            from_datetime = to_datetime - timedelta(hours=config.slack_hours)
            
            result = await orchestrator.process_slack_messages(
                from_datetime=from_datetime,
                to_datetime=to_datetime,
                limit=config.slack_limit,
            )
            
            if config.verbose:
                self.formatter.print_verbose_result(result)
            
            # Validate
            if result.status == "error":
                return TestResult("Slack Pipeline", False, result.reason)
            
            if result.action == KBActionType.IGNORE:
                return TestResult("Slack Pipeline", True, 
                                 f"No KB-worthy content ({result.messages_fetched} msgs)")
            
            if result.action in [KBActionType.CREATE, KBActionType.UPDATE]:
                return TestResult("Slack Pipeline", True, 
                                 f"{result.action.value.upper()}: {result.kb_document_title}")
            
            return TestResult("Slack Pipeline", True, "Completed")
            
        except Exception as e:
            return TestResult("Slack Pipeline", False, f"Exception: {e}")


# ============================================================================
# Test Runner
# ============================================================================

class PipelineTestRunner:
    """Main test runner."""

    def __init__(self):
        self.formatter = TestOutputFormatter()

    async def run_tests(self, test_mode: str, config: TestConfig) -> List[TestResult]:
        """Run tests based on mode."""
        settings = get_settings()
        
        mode_desc = "dry-run" if config.dry_run else "REAL (creates PRs)"
        print(f"🚀 Full Pipeline Tests ({mode_desc})")
        print(f"🔧 DRY_RUN: {settings.dry_run}")
        if config.include_slack:
            print(f"📱 Slack tests: ENABLED")
        self.formatter.print_config(config)

        results = []

        # If --slack is provided WITHOUT --test, skip text tests and run only Slack
        # If --test is provided, run only that specific test
        if config.include_slack and config.test_filter is None:
            # --slack only: skip text tests, run only Slack test
            results.extend(await self._run_slack_tests(config))
        else:
            # Run text input tests (troubleshooting, process, update)
            results.extend(await self._run_text_tests(test_mode, config))
            
            # Also run Slack if --slack AND --test are both provided
            if config.include_slack:
                results.extend(await self._run_slack_tests(config))

        self.formatter.print_results_summary(results)
        return results

    async def _run_text_tests(self, test_mode: str, config: TestConfig) -> List[TestResult]:
        """Run text input tests (troubleshooting, process, update)."""
        self.formatter.print_header("Text Input Pipeline Tests")

        text_test = MockPipelineTest()
        results = []
        
        # Check for test filter
        test_filter = config.test_filter

        # Troubleshooting test
        if test_filter is None or test_filter == "troubleshooting":
            result = await text_test.test_troubleshooting_kb(config)
            self.formatter.print_test_status("Troubleshooting KB", result.passed, result.message)
            results.append(result)

        if test_mode != "quick" or test_filter:
            # Process test
            if test_filter is None or test_filter == "process":
                result = await text_test.test_process_kb(config)
                self.formatter.print_test_status("Process KB", result.passed, result.message)
                results.append(result)

            # Update matching test
            if test_filter is None or test_filter == "update":
                result = await text_test.test_update_matching(config)
                self.formatter.print_test_status("Update Matching", result.passed, result.message)
                results.append(result)

        return results

    async def _run_slack_tests(self, config: TestConfig) -> List[TestResult]:
        """Run Slack pipeline tests."""
        self.formatter.print_header("Slack Pipeline Tests")

        slack_test = RealPipelineTest()
        results = []

        # Slack pipeline test
        result = await slack_test.test_slack_pipeline(config)
        self.formatter.print_test_status("Slack Pipeline", result.passed, result.message)
        results.append(result)

        return results


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
            description="Test Full KB Pipeline",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --mock                           # Dry-run (no PR created), text tests only
  %(prog)s --mock --test process            # Dry-run, process test only
  %(prog)s --real --test process            # Real run (creates PR), process test only
  %(prog)s --mock --slack                   # Dry-run with Slack tests
  %(prog)s --real --slack                   # Real run with Slack tests
  %(prog)s --quick                          # Quick smoke test (dry-run)
            """
        )

        # Run mode arguments (controls DRY_RUN)
        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument("--mock", action="store_true", 
                               help="Dry-run mode: DRY_RUN=true, no PR created (default)")
        mode_group.add_argument("--real", action="store_true", 
                               help="Real mode: DRY_RUN=false, creates actual PRs")
        mode_group.add_argument("--quick", action="store_true", 
                               help="Quick smoke test (dry-run, troubleshooting only)")

        # Additional test options
        parser.add_argument("--slack", action="store_true", 
                           help="Include Slack tests (requires SLACK_BOT_TOKEN)")
        parser.add_argument("--verbose", "-v", action="store_true", 
                           help="Show detailed output")
        parser.add_argument("--test", type=str, choices=["troubleshooting", "process", "update"],
                           help="Run specific test only (troubleshooting, process, update)")
        parser.add_argument("--slack-limit", type=int, default=10, 
                           help="Slack message limit (default: 10)")
        parser.add_argument("--slack-hours", type=int, default=24, 
                           help="Slack history hours (default: 24)")

        args = parser.parse_args()

        # Determine test mode and set DRY_RUN environment variable
        # IMPORTANT: Set env var BEFORE importing get_settings to avoid cache issues
        if args.real:
            test_mode = "real"
            os.environ["DRY_RUN"] = "false"
        elif args.quick:
            test_mode = "quick"
            os.environ["DRY_RUN"] = "true"
        else:
            test_mode = "mock"
            os.environ["DRY_RUN"] = "true"
        
        # Clear the settings cache to pick up the new DRY_RUN value
        from app.config import get_settings
        get_settings.cache_clear()

        # Create config
        config = TestConfig(
            verbose=args.verbose,
            dry_run=(test_mode != "real"),
            include_slack=args.slack,
            slack_limit=args.slack_limit,
            slack_hours=args.slack_hours,
            test_filter=args.test,
        )

        return test_mode, config


# ============================================================================
# Main Function
# ============================================================================

async def main():
    """Main test execution function."""
    test_mode, config = ConfigParser.parse_args()
    
    # Setup logging based on verbose mode
    setup_logging(config.verbose)

    print(f"\n🚀 Running full pipeline tests in '{test_mode}' mode...\n")

    runner = PipelineTestRunner()
    results = await runner.run_tests(test_mode, config)

    # Print usage examples
    print(f"\n💡 Test mode examples:")
    print(f"   python {sys.argv[0]} --mock                         # Dry-run, all text tests")
    print(f"   python {sys.argv[0]} --mock --test process          # Dry-run, process only")
    print(f"   python {sys.argv[0]} --real --test process -v       # Creates PR, process only")
    print(f"   python {sys.argv[0]} --mock --slack                 # Dry-run with Slack tests")
    print(f"   python {sys.argv[0]} --mock --slack --slack-limit 1 # Slack with 1 message")
    print(f"   python {sys.argv[0]} --real --slack -v              # Creates PRs with Slack")
    print(f"   python {sys.argv[0]} --quick                        # Quick smoke test\n")

    # Return exit code
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)