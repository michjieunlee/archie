"""
GitHub Integration Module

Provides GitHub API integration for Knowledge Base operations.
"""

from app.integrations.github.client import GitHubClient
from app.integrations.github.pr import PRManager, PRResult
from app.integrations.github.operations import GitHubKBOperations, KBOperation
from app.integrations.github.models import PRMetadata, KBCategory

__all__ = [
    "GitHubClient",
    "PRManager",
    "PRResult",
    "GitHubKBOperations",
    "KBOperation",
    "PRMetadata",
    "KBCategory",
]