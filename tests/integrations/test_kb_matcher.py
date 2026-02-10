"""
Integration tests for KB Matcher

Tests the KBMatcher component with both mock and real GitHub data.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
import argparse
from typing import List, Dict, Any
from datetime import datetime

from app.ai_core.matching import KBMatcher, MatchAction, MatchResult
from app.models.knowledge import (
    KBDocument,
    KBCategory,
    TroubleshootingExtraction,
    ProcessExtraction,
    DecisionExtraction,
    ExtractionMetadata,
)
from app.integrations.github import GitHubClient

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_troubleshooting_document() -> KBDocument:
    """Create a sample troubleshooting KB document."""
    extraction = TroubleshootingExtraction(
        title="Database Connection Timeout in Production",
        tags=["database", "postgresql", "timeout", "production"],
        ai_confidence=0.85,
        ai_reasoning="Clear problem description with verified solution and root cause analysis",
        problem_description="Database connection timeout after 30 seconds when connecting to production database",
        system_info="PostgreSQL 14.5 on Ubuntu 20.04",
        version_info="PostgreSQL 14.5, pgBouncer 1.17",
        environment="Production",
        symptoms="Connection attempts timeout after exactly 30 seconds. Error: 'connection timeout'",
        root_cause="Default connection timeout too low for high-latency network between app and DB server",
        solution_steps="1. Increase connection_timeout in postgresql.conf to 60s\n2. Restart PostgreSQL\n3. Test connection",
        prevention_measures="Monitor connection latency, set appropriate timeouts based on network conditions",
        related_links="https://wiki.internal/db-timeout-issues",
    )

    metadata = ExtractionMetadata(
        source_type="slack_thread",
        source_id="C123-p1234567890",
        message_count=10,
    )

    return KBDocument(
        extraction_output=extraction,
        category=KBCategory.TROUBLESHOOTING,
        extraction_metadata=metadata,
    )


def create_sample_process_document() -> KBDocument:
    """Create a sample process KB document."""
    extraction = ProcessExtraction(
        title="Staging Deployment Process",
        tags=["deployment", "staging", "ci-cd", "process"],
        ai_confidence=0.90,
        ai_reasoning="Well-documented process with clear steps and validation",
        process_overview="Standard deployment process for staging environment",
        prerequisites="- Access to staging AWS account\n- Deployment credentials\n- Code review approval",
        process_steps="1. Create deployment branch\n2. Run tests\n3. Build Docker image\n4. Deploy to staging\n5. Run smoke tests",
        validation_steps="1. Check application logs\n2. Verify health endpoints\n3. Test critical user flows",
        common_issues="Build failures: Check Docker daemon\nDeployment timeout: Check AWS credentials",
        related_processes="Production deployment process, Rollback process",
    )

    metadata = ExtractionMetadata(
        source_type="slack_thread",
        source_id="C456-p9876543210",
        message_count=15,
    )

    return KBDocument(
        extraction_output=extraction,
        category=KBCategory.PROCESSES,
        extraction_metadata=metadata,
    )


def create_sample_decision_document() -> KBDocument:
    """Create a sample decision KB document."""
    extraction = DecisionExtraction(
        title="Microservices Architecture Adoption",
        tags=["architecture", "microservices", "scalability"],
        ai_confidence=0.88,
        ai_reasoning="Well-reasoned decision with clear alternatives and consequences",
        decision_context="Need to improve application scalability as user base grows",
        decision_made="Adopt microservices architecture for new features",
        reasoning="Microservices allow independent scaling and team autonomy",
        alternatives="1. Monolithic with horizontal scaling\n2. Serverless functions\n3. Hybrid approach",
        positive_consequences="- Independent deployment\n- Team autonomy\n- Better scalability",
        negative_consequences="- Increased complexity\n- More DevOps overhead\n- Network latency",
        implementation_notes="Start with user service and auth service as first microservices",
    )

    metadata = ExtractionMetadata(
        source_type="slack_thread",
        source_id="C789-p5555555555",
        message_count=20,
    )

    return KBDocument(
        extraction_output=extraction,
        category=KBCategory.DECISIONS,
        extraction_metadata=metadata,
    )


def create_mock_existing_docs() -> List[Dict[str, Any]]:
    """Create mock existing KB documents."""
    return [
        {
            "title": "Database Connection Pool Configuration",
            "path": "troubleshooting/database-connection-pool.md",
            "category": "troubleshooting",
            "tags": ["database", "postgresql", "connection-pool"],
            "markdown_content": """Configuration guide for PostgreSQL connection pools.

This document covers how to properly configure connection pools
to avoid connection exhaustion and timeout issues.

## Connection Pool Settings

Configure the following parameters:
- max_connections: Maximum number of connections
- pool_size: Number of connections to maintain
- timeout: Connection timeout in seconds

## Common Issues

Connection timeout errors can occur when the pool is exhausted.
Monitor pool usage and adjust settings accordingly.""",
            "frontmatter": {
                "title": "Database Connection Pool Configuration",
                "category": "troubleshooting",
                "tags": ["database", "postgresql", "connection-pool"],
            },
        },
        {
            "title": "API Rate Limiting Issues",
            "path": "troubleshooting/api-rate-limiting.md",
            "category": "troubleshooting",
            "tags": ["api", "rate-limit", "429"],
            "markdown_content": """How to handle API rate limiting errors from external services.

This guide covers strategies for dealing with 429 errors
and implementing proper retry logic with exponential backoff.

## Symptoms

Requests to external API fail with 429 status code.
Error message indicates rate limit exceeded.

## Solutions

1. Implement exponential backoff
2. Add request queuing
3. Cache responses when possible
4. Monitor rate limit headers""",
            "frontmatter": {
                "title": "API Rate Limiting Issues",
                "category": "troubleshooting",
                "tags": ["api", "rate-limit", "429"],
            },
        },
        {
            "title": "Production Deployment Process",
            "path": "processes/production-deployment.md",
            "category": "processes",
            "tags": ["deployment", "production", "ci-cd"],
            "markdown_content": """Standard operating procedure for production deployments.

This process ensures safe and reliable deployments to production
with proper validation and rollback capabilities.

## Prerequisites

- Code review approval
- All tests passing
- Security scan completed

## Deployment Steps

1. Create production branch
2. Run full test suite
3. Build production artifacts
4. Deploy with blue-green strategy
5. Monitor metrics for 30 minutes
6. Switch traffic to new version

## Validation

- Check error rates
- Monitor response times
- Verify critical user flows
- Check database performance""",
            "frontmatter": {
                "title": "Production Deployment Process",
                "category": "processes",
                "tags": ["deployment", "production", "ci-cd"],
            },
        },
    ]


async def test_create_new_document():
    """Test CREATE action when no similar documents exist."""
    logger.info("\n=== Test 1: CREATE New Document ===")

    matcher = KBMatcher()
    kb_document = create_sample_decision_document()
    existing_docs = create_mock_existing_docs()

    # None of the existing docs are about architecture decisions
    result = await matcher.match(kb_document, existing_docs)

    logger.info(f"Action: {result.action.value}")
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"Document Path: {result.document_path}")
    logger.info(f"Document Title: {result.document_title}")
    logger.info(f"Category: {result.category}")
    logger.info(f"Reasoning: {result.reasoning[:200]}...")
    logger.info(f"Value Assessment: {result.value_addition_assessment[:200]}...")

    assert result.action == MatchAction.CREATE, f"Expected CREATE, got {result.action}"
    assert result.document_path is not None, "document_path should be set for CREATE"
    assert result.category is not None, "category should be set for CREATE"

    logger.info("✅ Test 1 PASSED")
    return result


async def test_update_existing_document():
    """Test UPDATE action when similar document exists."""
    logger.info("\n=== Test 2: UPDATE Existing Document ===")

    matcher = KBMatcher()
    kb_document = create_sample_troubleshooting_document()
    existing_docs = create_mock_existing_docs()

    # The database connection pool document is related
    result = await matcher.match(kb_document, existing_docs)

    logger.info(f"Action: {result.action.value}")
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"Document Path: {result.document_path}")
    logger.info(f"Document Title: {result.document_title}")
    logger.info(f"Category: {result.category}")
    logger.info(f"Reasoning: {result.reasoning[:200]}...")
    logger.info(f"Value Assessment: {result.value_addition_assessment[:200]}...")

    # Note: This might be CREATE or UPDATE depending on LLM assessment
    assert result.action in [
        MatchAction.CREATE,
        MatchAction.UPDATE,
    ], f"Expected CREATE or UPDATE, got {result.action}"
    assert result.document_path is not None, "document_path should be set"
    assert result.category is not None, "category should be set"

    logger.info(f"✅ Test 2 PASSED - Action: {result.action.value}")
    return result


async def test_ignore_low_quality():
    """Test IGNORE action for low quality content."""
    logger.info("\n=== Test 3: IGNORE Low Quality Content ===")

    matcher = KBMatcher()

    # Create document with low confidence
    extraction = TroubleshootingExtraction(
        title="Vague Issue",
        tags=["generic"],
        ai_confidence=0.45,
        ai_reasoning="Content lacks specific details and actionable information",
        problem_description="Something broke",
        system_info="Computer",
        version_info="Unknown",
        environment="Somewhere",
        symptoms="Not working",
        root_cause="Unknown",
        solution_steps="Restarted it",
        prevention_measures="Don't do that",
        related_links="",
    )

    metadata = ExtractionMetadata(
        source_type="slack_thread",
        source_id="C999-p1111111111",
        message_count=3,
    )

    kb_document = KBDocument(
        extraction_output=extraction,
        category=KBCategory.TROUBLESHOOTING,
        extraction_metadata=metadata,
    )

    existing_docs = create_mock_existing_docs()
    result = await matcher.match(kb_document, existing_docs)

    logger.info(f"Action: {result.action.value}")
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"Reasoning: {result.reasoning[:200]}...")

    # Low confidence content should likely be IGNORE
    logger.info(f"✅ Test 3 COMPLETED - Action: {result.action.value}")
    return result


async def test_with_real_github():
    """Test with real GitHub repository data."""
    logger.info("\n=== Test 4: Real GitHub Integration ===")

    try:
        github_client = GitHubClient()
        logger.info(f"Connected to GitHub: {github_client.repo.full_name}")

        # Step 1: Create and push a test document to GitHub
        logger.info("\n--- Step 1: Pushing test document to GitHub ---")

        test_document_content = """---
title: Test Redis Cache Timeout
category: troubleshooting
tags:
    - redis
    - cache
    - timeout
ai_confidence: 0.92
created_date: 2026-02-10
---

# Test Redis Cache Timeout

## Problem Description
Redis cache operations timing out after 5 seconds in production environment.

## Environment
- Redis 7.0
- Ubuntu 22.04
- Production

## Symptoms
Cache SET and GET operations fail with timeout errors after exactly 5 seconds.

## Root Cause
Default Redis timeout setting too conservative for network latency.

## Solution
1. Increase redis timeout to 10s in redis.conf
2. Restart Redis server
3. Monitor performance

## Prevention
Set appropriate timeouts based on network conditions and monitor latency.
"""

        test_document_path = "troubleshooting/test-redis-cache-timeout.md"

        try:
            # Create test branch
            test_branch = "test-kb-matcher-integration"
            await github_client.create_branch(test_branch)

            # Write test document to branch
            await github_client.create_or_update_file(
                branch_name=test_branch,
                file_path=test_document_path,
                content=test_document_content,
                commit_message="Test: Add test document for KB matcher integration test",
            )
            logger.info(f"✅ Test document pushed to branch {test_branch}")
            logger.info(f"   File path: {test_document_path}")
            logger.info(f"   Note: Document is in test branch, not main branch")
        except Exception as e:
            logger.warning(f"Could not push test document: {e}")
            logger.info("Proceeding with existing documents only")

        # Step 2: Fetch all KB documents and verify our test document is there
        logger.info("\n--- Step 2: Fetching KB documents from GitHub ---")
        all_docs = await github_client.read_kb_repository()
        logger.info(f"Fetched {len(all_docs)} real KB documents from GitHub")

        if len(all_docs) == 0:
            logger.warning("No KB documents found in repository - skipping test")
            return None

        # Check if our test document was retrieved
        test_document_found = any(
            doc.get("path") == test_document_path for doc in all_docs
        )
        if test_document_found:
            logger.info(f"✅ Test document found in repository: {test_document_path}")
        else:
            logger.warning(
                f"Test document not found in repository (may not have been pushed)"
            )

        # Show sample of what we found
        logger.info("\nSample of existing documents:")
        for i, doc in enumerate(all_docs[:5], 1):
            logger.info(
                f"  {i}. {doc.get('title')} ({doc.get('category')}) - {doc.get('path')}"
            )

        # Step 3: Test matching with real data
        logger.info("\n--- Step 3: Testing KB matching ---")
        matcher = KBMatcher()
        kb_document = create_sample_troubleshooting_document()

        # Filter to same category for focused test
        troubleshooting_docs = [
            doc for doc in all_docs if doc.get("category") == "troubleshooting"
        ]
        logger.info(
            f"Testing against {len(troubleshooting_docs)} troubleshooting documents"
        )

        result = await matcher.match(kb_document, troubleshooting_docs)

        assert result.action.value == MatchAction.CREATE

        logger.info(f"\n✅ Match Results:")
        logger.info(f"  Action: {result.action.value}")
        logger.info(f"  Confidence: {result.confidence_score}")
        logger.info(f"  Document Path: {result.document_path}")
        logger.info(f"  Document Title: {result.document_title}")
        logger.info(f"  Category: {result.category}")
        logger.info(f"  Reasoning: {result.reasoning[:300]}...")
        logger.info(f"  Value Assessment: {result.value_addition_assessment[:300]}...")

        logger.info("\n✅ Test 4 PASSED - Real GitHub Integration")
        return result

    except Exception as e:
        logger.error(f"Error testing with real GitHub: {e}", exc_info=True)
        logger.warning(
            "Ensure GitHub credentials are configured in .env file for real API testing"
        )
        raise


async def test_empty_repository():
    """Test matching when repository is empty."""
    logger.info("\n=== Test 5: Empty Repository ===")

    matcher = KBMatcher()
    kb_document = create_sample_troubleshooting_document()
    existing_docs = []  # Empty repository

    result = await matcher.match(kb_document, existing_docs)

    logger.info(f"Action: {result.action.value}")
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"Document Path: {result.document_path}")

    assert (
        result.action == MatchAction.CREATE
    ), f"Expected CREATE for empty repo, got {result.action}"
    assert result.document_path is not None, "document_path should be set"

    logger.info("✅ Test 5 PASSED")
    return result


async def test_all_categories():
    """Test matching for all category types."""
    logger.info("\n=== Test 6: All Categories ===")

    matcher = KBMatcher()
    existing_docs = create_mock_existing_docs()

    # Test troubleshooting
    logger.info("\n--- Testing Troubleshooting ---")
    ts_document = create_sample_troubleshooting_document()
    ts_result = await matcher.match(ts_document, existing_docs)
    logger.info(f"Troubleshooting: {ts_result.action.value}")

    # Test processes
    logger.info("\n--- Testing Processes ---")
    proc_document = create_sample_process_document()
    proc_result = await matcher.match(proc_document, existing_docs)
    logger.info(f"Processes: {proc_result.action.value}")

    # Test decisions
    logger.info("\n--- Testing Decisions ---")
    dec_document = create_sample_decision_document()
    dec_result = await matcher.match(dec_document, existing_docs)
    logger.info(f"Decisions: {dec_result.action.value}")

    logger.info("✅ Test 6 PASSED - All Categories")
    return [ts_result, proc_result, dec_result]


async def test_value_addition_assessment():
    """Test value addition assessment for different scenarios."""
    logger.info("\n=== Test 7: Value Addition Assessment ===")

    matcher = KBMatcher()
    existing_docs = create_mock_existing_docs()

    # Create document that adds new information to existing topic
    extraction = TroubleshootingExtraction(
        title="Connection Pool Exhaustion During Peak Traffic",
        tags=["database", "postgresql", "connection-pool", "scaling"],
        ai_confidence=0.87,
        ai_reasoning="Specific scenario with different root cause and solution",
        problem_description="PostgreSQL connection pool exhaustion during peak traffic",
        system_info="PostgreSQL 14.5 with pgBouncer",
        version_info="PostgreSQL 14.5, pgBouncer 1.17",
        environment="Production",
        symptoms="Connection requests queued, new connections fail with 'too many connections'",
        root_cause="Connection pool size too small for peak load, connections not released properly",
        solution_steps="1. Increase max_connections in postgresql.conf\n2. Increase pool_size in pgBouncer\n3. Fix connection leak in application code\n4. Implement connection monitoring",
        prevention_measures="Monitor active connections, implement auto-scaling for connection pool",
        related_links="",
    )

    metadata = ExtractionMetadata(
        source_type="slack_thread",
        source_id="C123-p9999999999",
        message_count=12,
    )

    kb_document = KBDocument(
        extraction_output=extraction,
        category=KBCategory.TROUBLESHOOTING,
        extraction_metadata=metadata,
    )

    result = await matcher.match(kb_document, existing_docs)

    logger.info(f"Action: {result.action.value}")
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"Value Assessment:")
    logger.info(f"  {result.value_addition_assessment}")

    # This should likely UPDATE the connection pool document
    logger.info(f"✅ Test 7 COMPLETED - Action: {result.action.value}")
    return result


async def run_all_tests(use_real_github: bool = False):
    """Run all integration tests."""
    logger.info("=" * 70)
    logger.info("KB MATCHER INTEGRATION TESTS")
    logger.info("=" * 70)

    results = []

    try:
        # Test 1: CREATE new document
        result1 = await test_create_new_document()
        results.append(("Create New Document", result1))

        # Test 2: UPDATE existing document
        result2 = await test_update_existing_document()
        results.append(("Update Existing", result2))

        # Test 3: IGNORE low quality
        result3 = await test_ignore_low_quality()
        results.append(("Ignore Low Quality", result3))

        # Test 4: Real GitHub (if enabled)
        if use_real_github:
            result4 = await test_with_real_github()
            if result4:
                results.append(("Real GitHub", result4))
        else:
            logger.info("\n=== Test 4: Real GitHub Integration ===")
            logger.info("Skipped (use --real flag to enable)")

        # Test 5: Empty repository
        result5 = await test_empty_repository()
        results.append(("Empty Repository", result5))

        # Test 6: All categories
        result6 = await test_all_categories()
        results.append(("All Categories", result6))

        # Test 7: Value addition
        result7 = await test_value_addition_assessment()
        results.append(("Value Addition", result7))

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)

        action_counts = {"CREATE": 0, "UPDATE": 0, "IGNORE": 0}

        for test_name, result in results:
            if isinstance(result, list):
                # Multiple results (test 6)
                actions = [r.action.value for r in result]
                logger.info(f"{test_name}: {actions}")
                for action in actions:
                    action_counts[action.upper()] += 1
            else:
                logger.info(f"{test_name}: {result.action.value}")
                action_counts[result.action.value.upper()] += 1

        logger.info(f"\nAction Distribution:")
        logger.info(f"  CREATE: {action_counts['CREATE']}")
        logger.info(f"  UPDATE: {action_counts['UPDATE']}")
        logger.info(f"  IGNORE: {action_counts['IGNORE']}")

        logger.info("\n✅ ALL TESTS COMPLETED SUCCESSFULLY")

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        raise


async def quick_test():
    """Quick test with just basic functionality."""
    logger.info("Running quick test...")

    matcher = KBMatcher()
    kb_document = create_sample_troubleshooting_document()
    existing_docs = create_mock_existing_docs()

    result = await matcher.match(kb_document, existing_docs)

    logger.info(
        f"Result: {result.action.value} (confidence: {result.confidence_score})"
    )
    logger.info("✅ Quick test PASSED")


def main():
    """Main entry point for tests."""
    parser = argparse.ArgumentParser(description="KB Matcher Integration Tests")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Test with real GitHub API (requires credentials)",
    )
    parser.add_argument("--quick", action="store_true", help="Run only quick test")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.quick:
        asyncio.run(quick_test())
    else:
        asyncio.run(run_all_tests(use_real_github=args.real))


if __name__ == "__main__":
    main()
