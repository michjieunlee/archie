"""
Test KB Query functionality
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio
from app.services.kb_orchestrator import KBOrchestrator
from app.models.api_responses import KBQueryResponse, KBSearchSource


class TestKBQuery(unittest.TestCase):
    """
    Test KB Query functionality.
    This is just a mock test to validate the basic structure works.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.mock_kb_docs = [
            {
                "title": "API Timeout Resolution",
                "path": "troubleshooting/api-timeout.md",
                "category": "troubleshooting",
                "content": "To fix API timeout errors, increase the connection timeout from 30s to 60s in config.json.",
                "tags": ["api", "timeout", "configuration"]
            },
            {
                "title": "Database Connection Guide",
                "path": "references/database-connection.md",
                "category": "references",
                "content": "To connect to the database, use the following connection string: postgresql://user:pass@host:port/db",
                "tags": ["database", "connection", "postgresql"]
            }
        ]

    @patch('app.services.kb_orchestrator.KBOrchestrator.github_client')
    @patch('gen_ai_hub.proxy.langchain.openai.ChatOpenAI')
    def test_kb_query_basic_structure(self, mock_llm, mock_github_client):
        """Test the basic structure of KB query functionality."""
        # Mock GitHub client response
        mock_github_client.read_kb_repository.return_value = asyncio.Future()
        mock_github_client.read_kb_repository.return_value.set_result(self.mock_kb_docs)
        mock_github_client.repo.full_name = "test/repo"
        mock_github_client.default_branch = "main"

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = "To fix API timeout errors, increase the connection timeout from 30s to 60s in config.json.\n\nSources: [API Timeout Resolution]"
        mock_llm.ainvoke.return_value = asyncio.Future()
        mock_llm.ainvoke.return_value.set_result(mock_llm_response)

        # Create orchestrator instance with mocked dependencies
        orchestrator = KBOrchestrator()
        orchestrator.llm = mock_llm

        # Run test query
        query = "How do I fix API timeout errors?"
        result = asyncio.run(orchestrator.query_knowledge_base(query))

        # Verify basic structure of response
        self.assertIsInstance(result, KBQueryResponse)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.query, query)
        self.assertIsNotNone(result.answer)
        self.assertGreater(len(result.sources), 0)

        # Verify sources
        self.assertIsInstance(result.sources[0], KBSearchSource)


# Manual test function to demonstrate usage
def manual_test():
    """Manual test function for demonstration purposes."""
    # This would be run in actual environment with real GitHub repo
    # Not run as part of unit tests
    import asyncio
    from app.services.kb_orchestrator import KBOrchestrator

    orchestrator = KBOrchestrator()
    query = "How do I fix API timeout errors?"

    result = asyncio.run(orchestrator.query_knowledge_base(query))
    print(f"Query: {query}")
    print(f"Answer: {result.answer}")
    print(f"Sources: {len(result.sources)}")
    for source in result.sources:
        print(f"- {source.title} ({source.relevance_score:.2f})")


if __name__ == "__main__":
    # For direct script execution (manual testing)
    manual_test()

    # Run unit tests
    # unittest.main()