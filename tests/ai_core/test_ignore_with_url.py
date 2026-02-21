"""
Test script to verify that IGNORE decisions include existing_document_url
"""

import asyncio
from app.ai_core.matching.kb_matcher import KBMatcher, MatchAction
from app.models.knowledge import KBDocument, KBCategory


async def test_ignore_with_existing_url():
    """Test that IGNORE decision populates existing_document_url"""

    # Import required models
    from app.models.knowledge import TroubleshootingExtraction, ExtractionMetadata

    # Create a test KB document with proper structure
    extraction_output = TroubleshootingExtraction(
        title="Test Database Connection Issue",
        tags=["database", "connection", "troubleshooting"],
        difficulty="intermediate",
        problem_description="Cannot connect to database",
        system_info="PostgreSQL 14",
        version_info="14.2",
        environment="production",
        symptoms="Connection timeout errors",
        root_cause="Wrong password configuration",
        solution_steps="1. Check credentials\n2. Update password",
        prevention_measures="Use environment variables for credentials",
        related_links="https://example.com/docs",
        ai_confidence=0.85,
        ai_reasoning="Test document with similar content to existing doc",
    )

    extraction_metadata = ExtractionMetadata(
        source_type="test",
        source_id="test_123",
        message_count=5,
    )

    test_doc = KBDocument(
        extraction_output=extraction_output,
        category=KBCategory.TROUBLESHOOTING,
        extraction_metadata=extraction_metadata,
    )

    # Create mock existing documents (simulating documents from GitHub)
    existing_docs = [
        {
            "title": "Database Connection Troubleshooting",
            "path": "troubleshooting/database-connection.md",
            "category": "troubleshooting",
            "tags": ["database", "connection"],
            "content": "---\ntitle: Database Connection\n---\n\nHow to fix database connection issues.",
            "markdown_content": "How to fix database connection issues.",
            "frontmatter": {"title": "Database Connection"},
        }
    ]

    # Initialize matcher
    matcher = KBMatcher()

    # Run matching
    print("Running matcher...")
    result = await matcher.match(test_doc, existing_docs)

    # Check results
    print(f"\n{'='*60}")
    print(f"Match Result:")
    print(f"{'='*60}")
    print(f"Action: {result.action}")
    print(f"Confidence: {result.confidence_score:.2%}")
    print(f"Document Path: {result.document_path}")
    print(f"Existing Document URL: {result.existing_document_url}")
    print(f"Reasoning: {result.reasoning[:200]}...")
    print(f"{'='*60}\n")

    # Verify the implementation
    if result.action == MatchAction.IGNORE:
        if result.existing_document_url:
            print("✅ SUCCESS: existing_document_url is populated for IGNORE action")
            print(f"   URL: {result.existing_document_url}")
        else:
            print("⚠️  WARNING: existing_document_url is None for IGNORE action")
            print("   This could be due to missing GitHub configuration")
    elif result.action == MatchAction.UPDATE:
        print(f"ℹ️  INFO: Matcher decided to UPDATE instead of IGNORE")
        print(f"   Document Path: {result.document_path}")
    elif result.action == MatchAction.CREATE:
        print(f"ℹ️  INFO: Matcher decided to CREATE instead of IGNORE")

    return result


if __name__ == "__main__":
    print("Testing IGNORE decision with existing_document_url...\n")
    result = asyncio.run(test_ignore_with_existing_url())
    print("\nTest completed!")
