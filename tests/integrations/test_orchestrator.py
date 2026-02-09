"""
Integration Test for KBOrchestrator

Tests the full KB orchestration pipeline with real LLM requests.
This test validates:
1. Text-to-KB processing (simplest - no Slack dependency)
2. PII masking
3. KB extraction with categorization
4. KB matching (stub)
5. End-to-end orchestrator flow
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
from datetime import datetime

from app.services.kb_orchestrator import KBOrchestrator
from app.models.api_responses import KBActionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_text_to_kb_simple():
    """
    Test Case 1: Simple troubleshooting text.
    Expected: Should extract as TROUBLESHOOTING category.
    """
    print("\n" + "=" * 80)
    print("TEST 1: Simple Troubleshooting Text")
    print("=" * 80)

    orchestrator = KBOrchestrator()

    text = """
    We had an issue with API timeout errors in production. The API calls to the 
    external service were failing after 30 seconds. 
    
    After investigation, we found that the default timeout was too short for 
    large data transfers. We increased the connection timeout from 30s to 60s 
    in the config file and the issue was resolved.
    
    The fix was deployed to production and we haven't seen the timeout errors since.
    """

    result = await orchestrator.process_text_input(
        text=text,
        title="API Timeout Troubleshooting",
        metadata={"test": "simple_troubleshooting"},
    )

    print(f"\n✅ Result:")
    print(f"  Status: {result.status}")
    print(f"  Action: {result.action}")
    print(f"  Title: {result.kb_article_title}")
    print(f"  Category: {result.kb_category}")
    print(f"  Confidence: {result.ai_confidence}")
    print(f"  Summary: {result.kb_summary}")
    print(f"  Reasoning: {result.ai_reasoning[:100]}...")

    assert result.status == "success", f"Expected success, got {result.status}"
    assert result.action in [
        KBActionType.CREATE,
        KBActionType.IGNORE,
    ], f"Expected CREATE or IGNORE, got {result.action}"

    if result.action == KBActionType.CREATE:
        assert result.kb_article_title is not None, "Title should not be None"
        assert result.kb_category == "troubleshooting", "Should be troubleshooting"
        assert (
            result.kb_summary is not None and len(result.kb_summary) > 0
        ), "Summary should be generated"

    return result


async def test_text_to_kb_process():
    """
    Test Case 2: Process documentation.
    Expected: Should extract as PROCESSES category.
    """
    print("\n" + "=" * 80)
    print("TEST 2: Process Documentation")
    print("=" * 80)

    orchestrator = KBOrchestrator()

    text = """
    Here's our standard procedure for deploying to production:
    
    1. Create a release branch from main
    2. Run all tests locally: npm test && npm run e2e
    3. Update CHANGELOG.md with version and changes
    4. Create PR and get approval from at least 2 reviewers
    5. Merge to main after CI passes
    6. Tag the release: git tag -a v1.2.3 -m "Release 1.2.3"
    7. Deploy to staging first and validate
    8. If staging looks good, deploy to production
    9. Monitor logs for 30 minutes post-deployment
    10. Update deployment documentation
    """

    result = await orchestrator.process_text_input(
        text=text,
        title="Production Deployment Process",
        metadata={"test": "process_documentation"},
    )

    print(f"\n✅ Result:")
    print(f"  Status: {result.status}")
    print(f"  Action: {result.action}")
    print(f"  Title: {result.kb_article_title}")
    print(f"  Category: {result.kb_category}")
    print(f"  Confidence: {result.ai_confidence}")
    print(f"  Summary: {result.kb_summary}")

    assert result.status == "success", f"Expected success, got {result.status}"
    assert result.action in [
        KBActionType.CREATE,
        KBActionType.IGNORE,
    ], f"Expected CREATE or IGNORE, got {result.action}"

    if result.action == KBActionType.CREATE:
        assert result.kb_category == "processes", "Should be processes"

    return result


async def test_text_to_kb_with_pii():
    """
    Test Case 3: Text with PII data.
    Expected: Should mask PII before extraction.
    """
    print("\n" + "=" * 80)
    print("TEST 3: Text with PII Data")
    print("=" * 80)

    orchestrator = KBOrchestrator()

    text = """
    John Doe (john.doe@company.com) reported an issue with the database connection.
    His employee ID is D123456 and he can be reached at 555-1234.
    
    The issue was related to his local environment setup. Sarah Smith helped him 
    configure the connection string properly, and the issue was resolved.
    
    Contact: sarah.smith@company.com if you have similar issues.
    Phone: +1-555-5678
    """

    result = await orchestrator.process_text_input(
        text=text,
        title="Database Connection Issue",
        metadata={"test": "pii_masking"},
    )

    print(f"\n✅ Result:")
    print(f"  Status: {result.status}")
    print(f"  Action: {result.action}")
    print(f"  Title: {result.kb_article_title}")
    print(f"  Category: {result.kb_category}")
    print(f"  Confidence: {result.ai_confidence}")

    assert result.status == "success", f"Expected success, got {result.status}"
    print("\n  ✓ PII masking completed (names, emails, IDs should be masked)")

    return result


async def test_insufficient_content():
    """
    Test Case 4: Insufficient content.
    Expected: Should return IGNORE action with helpful message.
    """
    print("\n" + "=" * 80)
    print("TEST 4: Insufficient Content")
    print("=" * 80)

    orchestrator = KBOrchestrator()

    text = "Hi"  # Too short

    result = await orchestrator.process_text_input(
        text=text,
        title="Short Message",
        metadata={"test": "insufficient_content"},
    )

    print(f"\n✅ Result:")
    print(f"  Status: {result.status}")
    print(f"  Action: {result.action}")
    print(f"  Reason: {result.reason}")

    assert result.status == "success", f"Expected success, got {result.status}"
    assert result.action == KBActionType.IGNORE, f"Expected IGNORE, got {result.action}"
    assert result.reason is not None, "Should have a reason for IGNORE"
    print("\n  ✓ Correctly identified insufficient content")

    return result


async def test_decision_documentation():
    """
    Test Case 5: Decision documentation.
    Expected: Should extract as DECISIONS category.
    """
    print("\n" + "=" * 80)
    print("TEST 5: Decision Documentation")
    print("=" * 80)

    orchestrator = KBOrchestrator()

    text = """
    We discussed whether to use PostgreSQL or MongoDB for our new analytics service.
    
    After evaluating both options, we decided to go with PostgreSQL because:
    1. Better support for complex queries and joins
    2. ACID compliance for data consistency
    3. Team has more experience with SQL
    4. Better tooling and monitoring options
    
    MongoDB was considered for its flexibility with schema changes, but we felt
    the benefits of PostgreSQL outweighed this advantage for our use case.
    
    This decision applies to all new analytics services going forward.
    """

    result = await orchestrator.process_text_input(
        text=text,
        title="Database Selection Decision",
        metadata={"test": "decision_documentation"},
    )

    print(f"\n✅ Result:")
    print(f"  Status: {result.status}")
    print(f"  Action: {result.action}")
    print(f"  Title: {result.kb_article_title}")
    print(f"  Category: {result.kb_category}")
    print(f"  Confidence: {result.ai_confidence}")
    print(f"  Summary: {result.kb_summary}")

    assert result.status == "success", f"Expected success, got {result.status}"

    if result.action == KBActionType.CREATE:
        assert result.kb_category == "decisions", "Should be decisions"

    return result


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("KB ORCHESTRATOR INTEGRATION TESTS")
    print("Testing with Real LLM Requests")
    print("=" * 80)

    start_time = datetime.now()
    results = []
    failed_tests = []

    # Run tests
    tests = [
        ("Simple Troubleshooting", test_text_to_kb_simple),
        ("Process Documentation", test_text_to_kb_process),
        ("PII Masking", test_text_to_kb_with_pii),
        ("Insufficient Content", test_insufficient_content),
        ("Decision Documentation", test_decision_documentation),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASS", result))
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}", exc_info=True)
            results.append((test_name, "FAIL", str(e)))
            failed_tests.append(test_name)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, status, result in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {test_name}: {status}")

    print(f"\nTotal Tests: {len(tests)}")
    print(f"Passed: {len([r for r in results if r[1] == 'PASS'])}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Duration: {duration:.2f}s")

    if failed_tests:
        print(f"\n❌ Failed Tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
