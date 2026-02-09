"""
GitHub Integration Test Suite

This script tests the GitHub integration including:
- GitHub client functionality (repository reading, PR creation)
- KB operations (create, update, delete, batch operations)
- API endpoint testing
- Mock/real API testing modes

Usage:
    python tests/integrations/test_github_integration.py --mock      # Mock data (default)
    python tests/integrations/test_github_integration.py --real      # Real GitHub API
    python tests/integrations/test_github_integration.py --quick     # Quick test
    python tests/integrations/test_github_integration.py --list-repos  # List repos

Requirements for --real mode:
- GITHUB_TOKEN in .env
- GITHUB_REPO_OWNER and GITHUB_REPO_NAME in .env
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
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi.testclient import TestClient

from app.integrations.github.client import GitHubClient
from app.integrations.github.operations import GitHubKBOperations, BatchOperation, KBOperation
from app.integrations.github.pr import PRManager
from app.main import app
from app.config import get_settings


# ============================================================================
# Constants and Test Data
# ============================================================================

MOCK_REPOSITORY_DATA = {
    "name": "test-kb-repo",
    "full_name": "test-org/test-kb-repo",
    "default_branch": "main",
    "html_url": "https://github.com/test-org/test-kb-repo"
}

MOCK_KB_DOCUMENTS = [
    {
        "title": "Database Connection Issues",
        "path": "troubleshooting/database-issues.md",
        "category": "troubleshooting",
        "tags": ["database", "connectivity"],
        "content": "# Database Connection Issues\n\nThis document covers common database connectivity problems...",
        "file_size": 1024,
        "ai_confidence": 0.9
    },
    {
        "title": "Deployment Process",
        "path": "processes/deployment.md",
        "category": "processes",
        "tags": ["deployment", "process"],
        "content": "# Deployment Process\n\nThis describes our deployment workflow...",
        "file_size": 2048,
        "ai_confidence": 0.85
    },
    {
        "title": "API Design Decisions",
        "path": "decisions/api-design.md",
        "category": "decisions",
        "tags": ["api", "architecture"],
        "content": "# API Design Decisions\n\nThis documents our API design choices...",
        "file_size": 1536,
        "ai_confidence": 0.92
    }
]

MOCK_PR_RESPONSE = {
    "number": 123,
    "html_url": "https://github.com/test-org/test-kb-repo/pull/123",
    "title": "KB: Test Document",
    "state": "open",
    "merged": False,
    "user": {"login": "archie-bot"},
    "head": {"ref": "kb/test-document"},
    "commits": 1,
    "additions": 50,
    "deletions": 0
}


# ============================================================================
# Configuration and Data Classes
# ============================================================================

@dataclass
class TestConfig:
    """Test configuration settings."""

    verbose: bool = False
    limit: Optional[int] = 10
    test_repo: Optional[str] = None
    dry_run: bool = False

    def has_custom_settings(self) -> bool:
        return self.verbose or self.limit != 10 or self.test_repo is not None or self.dry_run


@dataclass
class TestResult:
    """Test execution result."""

    name: str
    passed: bool
    message: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance timing metrics."""

    api_time: float = 0.0
    operations_time: float = 0.0
    total_time: float = 0.0


# ============================================================================
# Utility Classes
# ============================================================================

class TestOutputFormatter:
    """Handles all test output formatting."""

    @staticmethod
    def print_divider(char: str = "=", length: int = 60):
        """Print a divider line."""
        print(char * length)

    @staticmethod
    def print_header(title: str, emoji: str = "🔧"):
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
        if config.test_repo:
            config_parts.append(f"repo {config.test_repo}")
        if config.verbose:
            config_parts.append("verbose mode")

        if config_parts:
            print(f"🔧 Configuration: {', '.join(config_parts)}")
            print()

    @staticmethod
    def print_verbose_kb_results(documents: List[Dict[str, Any]]):
        """Print detailed KB document results."""
        print("📄 KB DOCUMENT RESULTS:")

        for i, doc in enumerate(documents, 1):
            title = doc.get("title", "Untitled")
            category = doc.get("category", "unknown")
            path = doc.get("path", "unknown")
            size = doc.get("file_size", 0)
            confidence = doc.get("ai_confidence", 0)

            print(f"   {i:2d}. [{category}] {title}")
            print(f"       └─ Path: {path} | Size: {size}b | Confidence: {confidence:.0%}")

    @staticmethod
    def print_api_endpoint_results(endpoint: str, status_code: int, response_data: dict):
        """Print API endpoint test results."""
        print(f"🌐 API ENDPOINT: {endpoint}")
        print(f"   → Status: {status_code}")
        if response_data:
            if "status" in response_data:
                print(f"   → Response: {response_data['status']}")
            if "pr_url" in response_data:
                print(f"   → PR URL: {response_data['pr_url']}")

    @staticmethod
    def print_performance_breakdown(metrics: PerformanceMetrics):
        """Print concise performance metrics."""
        print(f"\n⏱️  Performance: API {metrics.api_time:.2f}s | Operations {metrics.operations_time:.2f}s | Total {metrics.total_time:.2f}s")

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

    def start_api_timing(self):
        self.api_start = time.time()

    def end_api_timing(self):
        self.metrics.api_time = time.time() - self.api_start

    def start_operations_timing(self):
        self.operations_start = time.time()

    def end_operations_timing(self):
        self.metrics.operations_time = time.time() - self.operations_start

    def finalize(self):
        self.metrics.total_time = time.time() - self.start_time
        return self.metrics


class GitHubTestClient:
    """Enhanced GitHub client wrapper for testing."""

    def __init__(self):
        self.client = None
        self.operations = None

    def init_for_real_testing(self):
        """Initialize for real GitHub API testing."""
        self.client = GitHubClient()
        self.operations = GitHubKBOperations()

    async def fetch_kb_documents(self, config: TestConfig) -> List[Dict[str, Any]]:
        """Fetch KB documents based on test configuration."""
        if self.operations:
            docs = await self.operations.read_existing_kb()
            if config.limit:
                return docs[:config.limit]
            return docs
        return []


class MockDataFactory:
    """Factory for creating mock test data."""

    @staticmethod
    def create_mock_kb_documents() -> List[Dict[str, Any]]:
        """Create mock KB documents."""
        return MOCK_KB_DOCUMENTS.copy()

    @staticmethod
    def create_mock_pr_response() -> Dict[str, Any]:
        """Create mock PR response."""
        return MOCK_PR_RESPONSE.copy()

    @staticmethod
    def create_mock_api_responses() -> Dict[str, Any]:
        """Create comprehensive mock API responses."""
        return {
            "repository": MOCK_REPOSITORY_DATA,
            "documents": MOCK_KB_DOCUMENTS,
            "pr_create": MOCK_PR_RESPONSE,
            "pr_status": MOCK_PR_RESPONSE
        }


# ============================================================================
# Test Base Classes
# ============================================================================

class BaseGitHubTest:
    """Base class for GitHub integration tests."""

    def __init__(self):
        self.formatter = TestOutputFormatter()
        self.tracker = PerformanceTracker()

    def _validate_credentials(self) -> bool:
        """Validate required credentials."""
        settings = get_settings()
        if not settings.github_token:
            print("❌ GITHUB_TOKEN not found in .env")
            print("   Set up GitHub integration first (see docs)")
            return False
        if not settings.github_repo_owner or not settings.github_repo_name:
            print("❌ GITHUB_REPO_OWNER and GITHUB_REPO_NAME required in .env")
            return False
        return True


# ============================================================================
# Specific Test Classes
# ============================================================================

class MockGitHubTest(BaseGitHubTest):
    """Tests using mock data."""

    async def test_client_functionality(self, config: TestConfig = None) -> TestResult:
        """Test GitHub client basic functionality with mock data."""
        if config is None:
            config = TestConfig()

        try:
            with patch('app.integrations.github.client.Github') as mock_github, \
                 patch('app.integrations.github.client.get_settings') as mock_get_settings:

                # Mock settings
                mock_settings = Mock()
                mock_settings.github_token = "test_token"
                mock_settings.github_repo_owner = "test_owner"
                mock_settings.github_repo_name = "test_repo"
                mock_settings.github_default_branch = "main"
                mock_get_settings.return_value = mock_settings

                # Mock GitHub client
                mock_github_instance = Mock()
                mock_repo = Mock()
                mock_repo.full_name = "test_owner/test_repo"
                mock_github_instance.get_repo.return_value = mock_repo
                mock_github.return_value = mock_github_instance

                # Initialize and test client
                client = GitHubClient()

                # Test basic functionality
                has_repo = client.repo == mock_repo
                has_branch = client.default_branch == "main"

                # Test branch name generation
                branch = client.generate_branch_name("Test Document")
                valid_branch = branch == "kb/test-document"

                success = all([has_repo, has_branch, valid_branch])

                details = []
                if not has_repo:
                    details.append("repo initialization failed")
                if not has_branch:
                    details.append("branch configuration failed")
                if not valid_branch:
                    details.append("branch name generation failed")

                return TestResult(
                    "Client Functionality",
                    success,
                    "; ".join(details) if details else "✅ Repo access, branch config, name generation"
                )

        except Exception as e:
            return TestResult("Client Functionality", False, f"Exception: {e}")

    async def test_kb_operations(self, config: TestConfig = None) -> TestResult:
        """Test KB operations with mock data."""
        if config is None:
            config = TestConfig()

        try:
            with patch('app.integrations.github.operations.GitHubClient') as mock_client_class, \
                 patch('app.integrations.github.operations.PRManager') as mock_pr_manager_class:

                # Mock client
                mock_client = AsyncMock()
                mock_client.read_kb_repository.return_value = MockDataFactory.create_mock_kb_documents()
                mock_client_class.return_value = mock_client

                # Mock PR manager
                mock_pr_manager = AsyncMock()
                mock_pr_result = Mock()
                mock_pr_result.pr_url = "https://github.com/test/repo/pull/123"
                mock_pr_manager.create_kb_pr.return_value = mock_pr_result
                mock_pr_manager_class.return_value = mock_pr_manager

                ops = GitHubKBOperations()

                # Test read operations
                self.tracker.start_operations_timing()
                docs = await ops.read_existing_kb()
                self.tracker.end_operations_timing()

                # Test create operation
                pr_url = await ops.create_kb_document(
                    title="Test Document",
                    content="# Test Content",
                    file_path="test/document.md",
                    summary="Test summary"
                )

                # Verbose output
                if config.verbose:
                    self.formatter.print_verbose_kb_results(docs)

                # Verify results
                has_documents = len(docs) > 0
                valid_pr_url = pr_url.startswith("https://github.com/")
                correct_doc_count = len(docs) == 3

                success = all([has_documents, valid_pr_url, correct_doc_count])

                details = []
                if not has_documents:
                    details.append("no documents returned")
                if not valid_pr_url:
                    details.append("invalid PR URL")
                if not correct_doc_count:
                    details.append(f"expected 3 docs, got {len(docs)}")

                return TestResult(
                    "KB Operations",
                    success,
                    "; ".join(details) if details else f"✅ {len(docs)} documents, PR creation"
                )

        except Exception as e:
            return TestResult("KB Operations", False, f"Exception: {e}")

    async def test_api_endpoints(self, config: TestConfig = None) -> TestResult:
        """Test API endpoints with mock data."""
        if config is None:
            config = TestConfig()

        try:
            client = TestClient(app)

            # Mock the GitHub operations
            with patch('app.api.routes.github.get_github_ops') as mock_get_ops:
                mock_ops = AsyncMock()
                mock_ops.read_existing_kb.return_value = MockDataFactory.create_mock_kb_documents()
                mock_ops.create_kb_document.return_value = "https://github.com/test/repo/pull/123"
                mock_ops.get_pr_status.return_value = MockDataFactory.create_mock_pr_response()
                mock_get_ops.return_value = mock_ops

                # Test endpoints
                endpoints_tested = []

                # Test GET /api/github/kb/documents
                response = client.get("/api/github/kb/documents")
                list_success = response.status_code == 200 and len(response.json()) > 0
                endpoints_tested.append(("GET /kb/documents", list_success))

                if config.verbose:
                    self.formatter.print_api_endpoint_results("GET /api/github/kb/documents", response.status_code, response.json())

                # Test POST /api/github/kb/documents
                create_data = {
                    "title": "Test Document",
                    "content": "# Test Content",
                    "file_path": "test/document.md"
                }
                response = client.post("/api/github/kb/documents", json=create_data)
                create_success = response.status_code == 200 and "pr_url" in response.json()
                endpoints_tested.append(("POST /kb/documents", create_success))

                if config.verbose:
                    self.formatter.print_api_endpoint_results("POST /api/github/kb/documents", response.status_code, response.json())

                # Test GET /api/github/pr/{id}/status
                response = client.get("/api/github/pr/123/status")
                status_success = response.status_code == 200 and "number" in response.json()
                endpoints_tested.append(("GET /pr/status", status_success))

                if config.verbose:
                    self.formatter.print_api_endpoint_results("GET /api/github/pr/123/status", response.status_code, response.json())

                # Check results
                all_passed = all(success for _, success in endpoints_tested)
                passed_count = sum(1 for _, success in endpoints_tested if success)

                return TestResult(
                    "API Endpoints",
                    all_passed,
                    f"✅ {passed_count}/{len(endpoints_tested)} endpoints working" if all_passed
                    else f"❌ {passed_count}/{len(endpoints_tested)} endpoints working"
                )

        except Exception as e:
            return TestResult("API Endpoints", False, f"Exception: {e}")

    async def test_batch_operations(self, config: TestConfig = None) -> TestResult:
        """Test batch operations with mock data."""
        if config is None:
            config = TestConfig()

        try:
            with patch('app.integrations.github.operations.GitHubClient') as mock_client_class:
                # Mock client
                mock_client = Mock()
                mock_client.generate_branch_name = Mock(return_value="kb/batch-test")
                mock_client.create_branch = AsyncMock(return_value=None)
                mock_client.ensure_kb_structure = AsyncMock(return_value=None)
                mock_client.create_or_update_file = AsyncMock(return_value="commit_sha")
                mock_client.delete_file = AsyncMock(return_value="commit_sha")

                # Mock PR creation
                mock_pr = Mock()
                mock_pr.number = 123
                mock_pr.html_url = "https://github.com/test/repo/pull/123"
                mock_repo = Mock()
                mock_repo.create_pull.return_value = mock_pr
                mock_repo.get_labels.return_value = []
                mock_client.repo = mock_repo

                mock_client_class.return_value = mock_client

                # Create operations
                operations = [
                    BatchOperation(
                        action=KBOperation.CREATE,
                        file_path="test/new.md",
                        title="New Document",
                        content="Content"
                    ),
                    BatchOperation(
                        action=KBOperation.UPDATE,
                        file_path="test/existing.md",
                        title="Updated Document",
                        content="Updated content"
                    ),
                    BatchOperation(
                        action=KBOperation.DELETE,
                        file_path="test/old.md",
                        title="Old Document"
                    )
                ]

                ops = GitHubKBOperations()
                pr_url = await ops.create_batch_pr(
                    title="Test Batch",
                    operations=operations,
                    summary="Batch test operations"
                )

                # Verify results
                valid_pr_url = pr_url == "https://github.com/test/repo/pull/123"
                operations_called = mock_client.create_or_update_file.call_count == 2
                deletes_called = mock_client.delete_file.call_count == 1

                success = all([valid_pr_url, operations_called, deletes_called])

                details = []
                if not valid_pr_url:
                    details.append("invalid PR URL")
                if not operations_called:
                    details.append("create/update operations not called")
                if not deletes_called:
                    details.append("delete operations not called")

                return TestResult(
                    "Batch Operations",
                    success,
                    "; ".join(details) if details else "✅ 3 operations, PR creation"
                )

        except Exception as e:
            return TestResult("Batch Operations", False, f"Exception: {e}")


class RealGitHubTest(BaseGitHubTest):
    """Tests using real GitHub API."""

    def __init__(self):
        super().__init__()
        self.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_artifacts = []  # Track created PRs/branches for cleanup

    async def test_real_integration(self, config: TestConfig) -> TestResult:
        """Test with real GitHub API - read-only test."""
        # Validate credentials
        if not self._validate_credentials():
            return TestResult("Real GitHub API Read", False, "Missing credentials")

        try:
            client = GitHubTestClient()
            client.init_for_real_testing()

            self.tracker.start_api_timing()
            documents = await client.fetch_kb_documents(config)
            self.tracker.end_api_timing()

            if not documents:
                return TestResult(
                    "Real GitHub API Read", True, "No KB documents found (empty repository)"
                )

            metrics = self.tracker.finalize()

            # Verbose mode output
            if config.verbose:
                self.formatter.print_verbose_kb_results(documents)
                self.formatter.print_performance_breakdown(metrics)
            else:
                self.formatter.print_performance_breakdown(metrics)

            success_details = f"Fetched {len(documents)} KB documents"
            return TestResult("Real GitHub API Read", True, success_details)

        except Exception as e:
            return TestResult("Real GitHub API Read", False, f"Integration failed: {e}")

    async def test_real_create_operation(self, config: TestConfig) -> TestResult:
        """Test creating a real KB document via PR."""
        if not self._validate_credentials():
            return TestResult("Real Create Operation", False, "Missing credentials")

        try:
            operations = GitHubKBOperations()

            # Create test document
            test_title = f"[TEST] Integration Test Document"
            test_file_path = f"test/integration-test-{self.test_timestamp}.md"
            test_content = f"""# Integration Test Document

This is a test document created by the GitHub integration test suite.

**Created**: {datetime.now().isoformat()}
**Test Run**: {self.test_timestamp}

## Purpose

This document validates that Archie can successfully:
- Create KB documents
- Generate proper branch names
- Create pull requests
- Handle markdown content

## Cleanup

This test document can be safely deleted after testing.

---

*This is an automated test document. Safe to delete.*
"""

            # Create the document (this should create a PR)
            pr_url = await operations.create_kb_document(
                title=test_title,
                content=test_content,
                file_path=test_file_path,
                summary=f"Integration test document created at {datetime.now().isoformat()}",
                ai_confidence=0.95
            )

            # Track for potential cleanup
            self.test_artifacts.append({
                'type': 'pr',
                'url': pr_url,
                'file_path': test_file_path
            })

            # Validate PR was created
            if pr_url and pr_url.startswith("https://github.com/"):
                success_message = f"✅ Created PR: {pr_url}"
                if config.verbose:
                    print(f"🔗 Test PR Created: {pr_url}")
                    print(f"📄 Test File: {test_file_path}")
                return TestResult("Real Create Operation", True, success_message)
            else:
                return TestResult("Real Create Operation", False, "Invalid PR URL returned")

        except Exception as e:
            return TestResult("Real Create Operation", False, f"Create operation failed: {e}")

    async def test_real_update_operation(self, config: TestConfig) -> TestResult:
        """Test updating an existing KB document via PR."""
        if not self._validate_credentials():
            return TestResult("Real Update Operation", False, "Missing credentials")

        try:
            operations = GitHubKBOperations()

            # First, check if we have any existing documents to update
            existing_docs = await operations.read_existing_kb()
            if not existing_docs:
                return TestResult("Real Update Operation", True, "⚠️  No existing documents to update (skipped)")

            # Use the first document for testing
            target_doc = existing_docs[0]
            original_path = target_doc.get('path', 'unknown.md')

            # Create updated content
            updated_content = f"""# {target_doc.get('title', 'Updated Document')}

**Original Path**: {original_path}
**Last Updated**: {datetime.now().isoformat()}
**Test Update**: {self.test_timestamp}

---

## UPDATE TEST NOTICE
This document was temporarily modified by the integration test suite to validate update functionality.

The original content has been preserved below:

---

{target_doc.get('content', 'Original content not available')}

---

*This update was created by an automated test. You may want to revert this change.*
"""

            # Update the document
            pr_url = await operations.update_kb_document(
                title=f"[TEST] Update {target_doc.get('title', 'Document')}",
                content=updated_content,
                file_path=original_path,
                summary=f"Test update of existing document at {datetime.now().isoformat()}",
                ai_confidence=0.90
            )

            # Track for potential cleanup
            self.test_artifacts.append({
                'type': 'pr',
                'url': pr_url,
                'file_path': original_path,
                'operation': 'update'
            })

            if pr_url and pr_url.startswith("https://github.com/"):
                success_message = f"✅ Created update PR: {pr_url}"
                if config.verbose:
                    print(f"🔗 Update PR Created: {pr_url}")
                    print(f"📄 Updated File: {original_path}")
                return TestResult("Real Update Operation", True, success_message)
            else:
                return TestResult("Real Update Operation", False, "Invalid PR URL returned")

        except Exception as e:
            return TestResult("Real Update Operation", False, f"Update operation failed: {e}")

    async def test_real_batch_operation(self, config: TestConfig) -> TestResult:
        """Test batch operations with real GitHub API."""
        if not self._validate_credentials():
            return TestResult("Real Batch Operation", False, "Missing credentials")

        try:
            operations = GitHubKBOperations()

            # Create multiple test operations in one PR
            batch_operations = [
                BatchOperation(
                    action=KBOperation.CREATE,
                    file_path=f"test/batch-test-doc1-{self.test_timestamp}.md",
                    title="Batch Test Document 1",
                    content=f"""# Batch Test Document 1

This is the first document in a batch operation test.

**Created**: {datetime.now().isoformat()}
**Test Batch**: {self.test_timestamp}

This document validates batch CREATE operations.
"""
                ),
                BatchOperation(
                    action=KBOperation.CREATE,
                    file_path=f"test/batch-test-doc2-{self.test_timestamp}.md",
                    title="Batch Test Document 2",
                    content=f"""# Batch Test Document 2

This is the second document in a batch operation test.

**Created**: {datetime.now().isoformat()}
**Test Batch**: {self.test_timestamp}

This document validates batch CREATE operations alongside other documents.
"""
                )
            ]

            # Execute batch operation
            pr_url = await operations.create_batch_pr(
                title=f"[TEST] Batch Integration Test",
                operations=batch_operations,
                summary=f"Batch integration test with {len(batch_operations)} operations at {datetime.now().isoformat()}",
                ai_confidence=0.88
            )

            # Track for cleanup
            self.test_artifacts.append({
                'type': 'pr',
                'url': pr_url,
                'operation': 'batch',
                'file_paths': [op.file_path for op in batch_operations]
            })

            if pr_url and pr_url.startswith("https://github.com/"):
                success_message = f"✅ Created batch PR with {len(batch_operations)} operations: {pr_url}"
                if config.verbose:
                    print(f"🔗 Batch PR Created: {pr_url}")
                    print(f"📄 Files: {', '.join([op.file_path for op in batch_operations])}")
                return TestResult("Real Batch Operation", True, success_message)
            else:
                return TestResult("Real Batch Operation", False, "Invalid batch PR URL returned")

        except Exception as e:
            return TestResult("Real Batch Operation", False, f"Batch operation failed: {e}")

    def print_cleanup_instructions(self):
        """Print instructions for cleaning up test artifacts."""
        if not self.test_artifacts:
            return

        print(f"\n🧹 Test Cleanup Instructions:")
        print(f"   The following test artifacts were created and may need cleanup:")

        for i, artifact in enumerate(self.test_artifacts, 1):
            print(f"\n   {i}. {artifact['type'].upper()}: {artifact['url']}")
            if artifact.get('file_paths'):
                print(f"      Files: {', '.join(artifact['file_paths'])}")
            elif artifact.get('file_path'):
                print(f"      File: {artifact['file_path']}")

        print(f"\n   💡 These test PRs are clearly marked with '[TEST]' prefix.")
        print(f"   💡 You can safely close/merge them or leave them for reference.")
        print(f"   💡 Test files are in the 'test/' directory and can be deleted.\n")


# ============================================================================
# Test Runner
# ============================================================================

class GitHubTestRunner:
    """Main test runner."""

    def __init__(self):
        self.formatter = TestOutputFormatter()

    async def run_tests(self, test_mode: str, config: TestConfig) -> List[TestResult]:
        """Run tests based on mode."""
        print(f"🚀 GitHub Integration Tests ({test_mode} mode)")
        self.formatter.print_config(config)

        results = []

        if test_mode == "list-repos":
            await self._list_github_repos()
            return []

        if test_mode in ["mock", "quick"]:
            results.extend(await self._run_mock_tests(test_mode, config))

        if test_mode == "real":
            results.extend(await self._run_real_tests(config))
        elif test_mode == "real-read-only":
            results.extend(await self._run_real_read_only_tests(config))

        self.formatter.print_results_summary(results)
        return results

    async def _run_mock_tests(self, test_mode: str, config: TestConfig = None) -> List[TestResult]:
        """Run mock data tests."""
        self.formatter.print_header("Mock Data Tests")

        if config is None:
            config = TestConfig()

        mock_test = MockGitHubTest()
        results = []

        # Client functionality test
        client_result = await mock_test.test_client_functionality(config)
        self.formatter.print_test_status("Client Functionality", client_result.passed, client_result.message)
        results.append(client_result)

        # KB operations test
        kb_result = await mock_test.test_kb_operations(config)
        self.formatter.print_test_status("KB Operations", kb_result.passed, kb_result.message)
        results.append(kb_result)

        if test_mode != "quick":
            # API endpoints test
            api_result = await mock_test.test_api_endpoints(config)
            self.formatter.print_test_status("API Endpoints", api_result.passed, api_result.message)
            results.append(api_result)

            # Batch operations test
            batch_result = await mock_test.test_batch_operations(config)
            self.formatter.print_test_status("Batch Operations", batch_result.passed, batch_result.message)
            results.append(batch_result)

        return results

    async def _run_real_tests(self, config: TestConfig) -> List[TestResult]:
        """Run real API tests."""
        self.formatter.print_header("Real GitHub API Tests")

        real_test = RealGitHubTest()
        results = []

        # Read-only test (existing functionality)
        read_result = await real_test.test_real_integration(config)
        self.formatter.print_test_status("Real GitHub API Read", read_result.passed, read_result.message)
        results.append(read_result)

        # Create operation test (creates actual PR)
        create_result = await real_test.test_real_create_operation(config)
        self.formatter.print_test_status("Real Create Operation", create_result.passed, create_result.message)
        results.append(create_result)

        # Update operation test (creates actual PR)
        update_result = await real_test.test_real_update_operation(config)
        self.formatter.print_test_status("Real Update Operation", update_result.passed, update_result.message)
        results.append(update_result)

        # Batch operation test (creates actual PR)
        batch_result = await real_test.test_real_batch_operation(config)
        self.formatter.print_test_status("Real Batch Operation", batch_result.passed, batch_result.message)
        results.append(batch_result)

        # Print cleanup instructions if any artifacts were created
        real_test.print_cleanup_instructions()

        return results

    async def _run_real_read_only_tests(self, config: TestConfig) -> List[TestResult]:
        """Run real API read-only tests."""
        self.formatter.print_header("Real GitHub API Tests (Read-Only)")

        real_test = RealGitHubTest()
        results = []

        # Only run the read-only test
        read_result = await real_test.test_real_integration(config)
        self.formatter.print_test_status("Real GitHub API Read", read_result.passed, read_result.message)
        results.append(read_result)

        return results

    async def _list_github_repos(self):
        """List available GitHub repositories."""
        print("\n🔧 Listing GitHub repository configuration...")

        settings = get_settings()
        if not settings.github_token:
            print("❌ GITHUB_TOKEN not found in .env")
            return

        try:
            if settings.github_repo_owner and settings.github_repo_name:
                repo_name = f"{settings.github_repo_owner}/{settings.github_repo_name}"
                print(f"✅ Configured repository: {repo_name}")
            else:
                print("⚠️  No GITHUB_REPO_OWNER and GITHUB_REPO_NAME configured in .env")
                print("   Add GITHUB_REPO_OWNER=your-username to your .env file")
                print("   Add GITHUB_REPO_NAME=your-repo-name to your .env file")
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
            description="Test GitHub Integration",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --mock                           # Mock data testing
  %(prog)s --real --verbose                 # Real API with detailed output
  %(prog)s --real --limit 25                # Real API, max 25 documents
  %(prog)s --quick                          # Quick mock test
  %(prog)s --list-repos                     # List repo config
            """
        )

        # Test mode arguments
        parser.add_argument("--mock", action="store_true", help="Test with mock data (default)")
        parser.add_argument("--real", action="store_true", help="Test with real GitHub API (creates PRs)")
        parser.add_argument("--real-read-only", action="store_true", help="Real GitHub API read-only test")
        parser.add_argument("--quick", action="store_true", help="Quick test with mock data")
        parser.add_argument("--list-repos", action="store_true", help="List GitHub repo configuration")

        # Configuration arguments
        parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed test output")
        parser.add_argument("--limit", type=int, help="Maximum number of documents to fetch (default: 10)")
        parser.add_argument("--test-repo", help="Test repository (owner/repo format)")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without actually creating PRs")

        args = parser.parse_args()

        # Determine test mode
        if args.real:
            test_mode = "real"
        elif args.real_read_only:
            test_mode = "real-read-only"
        elif args.quick:
            test_mode = "quick"
        elif args.list_repos:
            test_mode = "list-repos"
        else:
            test_mode = "mock"  # default

        # Parse test configuration
        config = ConfigParser._create_test_config(args, test_mode)

        return test_mode, config

    @staticmethod
    def _create_test_config(args, test_mode: str) -> TestConfig:
        """Create test configuration from arguments."""
        config = TestConfig(verbose=args.verbose)

        if args.limit:
            config.limit = args.limit
        if args.test_repo:
            config.test_repo = args.test_repo

        # Add dry_run flag to config
        config.dry_run = getattr(args, 'dry_run', False)

        return config


# ============================================================================
# Main Function
# ============================================================================

async def main():
    """Main test execution function."""
    test_mode, config = ConfigParser.parse_args()

    print(f"\n🚀 Running GitHub integration tests in '{test_mode}' mode...\n")

    runner = GitHubTestRunner()
    results = await runner.run_tests(test_mode, config)

    # Print usage examples
    print(f"\n💡 Test mode examples:")
    print(f"   python {sys.argv[0]} --mock                           # Mock data testing (safe)")
    print(f"   python {sys.argv[0]} --real-read-only --verbose       # Real API, read-only (safe)")
    print(f"   python {sys.argv[0]} --real --verbose                 # Real API, creates PRs ⚠️")
    print(f"   python {sys.argv[0]} --real --limit 5                 # Real API, limit docs")
    print(f"   python {sys.argv[0]} --quick                          # Quick mock test")
    print(f"   python {sys.argv[0]} --list-repos                     # List repo config")
    print(f"   python {sys.argv[0]} --dry-run                        # Show what would be done\n")


if __name__ == "__main__":
    asyncio.run(main())