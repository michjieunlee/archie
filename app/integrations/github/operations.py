"""
GitHub KB Operations
High-level CRUD operations for Knowledge Base management

This module provides the main interface that the orchestrator uses
for all GitHub KB operations (Create, Read, Update, Delete, Append).
"""

import logging
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from app.integrations.github.client import GitHubClient
from app.integrations.github.pr import PRManager, PRResult

logger = logging.getLogger(__name__)


class KBOperation(str, Enum):
    """Types of KB operations."""

    CREATE = "create"
    UPDATE = "update"
    APPEND = "append"
    DELETE = "delete"


class BatchOperation(BaseModel):
    """Single operation in a batch request."""

    action: KBOperation = Field(..., description="Type of operation")
    file_path: str = Field(..., description="Path to the file in repository")
    title: Optional[str] = Field(
        None, description="Title for the operation (used in commit messages)"
    )
    content: Optional[str] = Field(None, description="File content (for create/update)")
    additional_content: Optional[str] = Field(
        None, description="Additional content (for append)"
    )
    reason: Optional[str] = Field(None, description="Reason for operation (for delete)")


class GitHubKBOperations:
    """
    High-level Knowledge Base operations using GitHub.

    This is the main interface used by the orchestrator.
    """

    def __init__(self, github_client: Optional[GitHubClient] = None):
        """
        Initialize KB operations.

        Args:
            github_client: Optional GitHub client (will create if not provided)
        """
        self.client = github_client or GitHubClient()
        self.pr_manager = PRManager(self.client)

    async def read_existing_kb(self) -> List[Dict[str, Any]]:
        """
        Read all existing KB documents from the repository.
        This is called by the orchestrator for matching against existing content.

        Returns:
            List of existing KB document metadata
        """
        return await self.client.read_kb_repository()

    async def create_kb_document(
        self,
        title: str,
        content: str,
        file_path: str,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Create a new KB document via PR.

        Args:
            title: Document title
            content: Markdown content
            file_path: Target path in repository
            summary: Brief summary for PR description
            source_url: Source URL (e.g., Slack thread)
            ai_confidence: AI confidence score

        Returns:
            PR URL
        """
        try:
            logger.info(f"Creating new KB document: {title}")

            pr_result = await self.pr_manager.create_pr(
                title=title,
                content=content,
                file_path=file_path,
                summary=summary,
                source_url=source_url,
                ai_confidence=ai_confidence,
            )

            logger.info(f"Successfully created KB document PR: {pr_result.pr_url}")
            return pr_result.pr_url

        except Exception as e:
            logger.error(f"Failed to create KB document '{title}': {e}")
            raise

    async def update_kb_document(
        self,
        title: str,
        content: str,
        file_path: str,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Update an existing KB document via PR.

        This creates a new PR to replace the existing document content.

        Args:
            title: Document title (for PR naming)
            content: New markdown content (replaces existing)
            file_path: Path to existing file in repository
            summary: Brief summary for PR description
            source_url: Source URL (e.g., Slack thread)
            ai_confidence: AI confidence score

        Returns:
            PR URL
        """
        try:
            logger.info(f"Updating KB document: {title} at {file_path}")

            # Use the same create_pr method - it handles both create and update
            pr_result = await self.pr_manager.create_pr(
                title=f"Update: {title}",
                content=content,
                file_path=file_path,
                summary=summary,
                source_url=source_url,
                ai_confidence=ai_confidence,
            )

            logger.info(f"Successfully created update PR: {pr_result.pr_url}")
            return pr_result.pr_url

        except Exception as e:
            logger.error(f"Failed to update KB document '{title}': {e}")
            raise

    async def append_to_kb_document(
        self,
        title: str,
        file_path: str,
        additional_content: str,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Append content to an existing KB document via PR.

        This reads the existing document and appends new content.

        Args:
            title: Document title (for PR naming)
            file_path: Path to existing file in repository
            additional_content: Content to append
            summary: Brief summary for PR description
            source_url: Source URL (e.g., Slack thread)
            ai_confidence: AI confidence score

        Returns:
            PR URL
        """
        try:
            logger.info(f"Appending to KB document: {title} at {file_path}")

            # Read existing content
            try:
                existing_file = self.client.repo.get_contents(
                    file_path, ref=self.client.default_branch
                )
                existing_content = existing_file.decoded_content.decode("utf-8")
            except Exception as e:
                logger.error(f"Could not read existing file {file_path}: {e}")
                raise ValueError(f"Cannot append to non-existent file: {file_path}")

            # Combine existing and new content
            combined_content = (
                existing_content.rstrip() + "\n\n" + additional_content.strip()
            )

            # Create PR with combined content
            pr_result = await self.pr_manager.create_pr(
                title=f"Append to: {title}",
                content=combined_content,
                file_path=file_path,
                summary=summary,
                source_url=source_url,
                ai_confidence=ai_confidence,
            )

            logger.info(f"Successfully created append PR: {pr_result.pr_url}")
            return pr_result.pr_url

        except Exception as e:
            logger.error(f"Failed to append to KB document '{title}': {e}")
            raise

    async def delete_kb_document(
        self,
        title: str,
        file_path: str,
        reason: Optional[str] = None,
    ) -> str:
        """
        Delete a KB document via PR.

        Args:
            title: Document title (for PR naming)
            file_path: Path to file to delete
            reason: Reason for deletion

        Returns:
            PR URL
        """
        try:
            logger.info(f"Deleting KB document: {title} at {file_path}")

            # Generate branch name for deletion
            branch_name = self.client.generate_branch_name(f"delete-{title}")

            # Create branch
            await self.client.create_branch(branch_name)

            # Delete the file
            commit_message = f"Delete KB document: {title}"
            await self.client.delete_file(
                branch_name=branch_name,
                file_path=file_path,
                commit_message=commit_message,
            )

            # Create PR for deletion
            pr_title = f"Delete KB: {title}"
            pr_body = f"## Deletion Request\n\nDeleting KB document: **{title}**\n\n"
            if reason:
                pr_body += f"**Reason**: {reason}\n\n"
            pr_body += f"**File Path**: `{file_path}`\n\n---\n\n🗑️ *This is an automated deletion request.*"

            pr = self.client.repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=self.client.default_branch,
            )

            logger.info(f"Successfully created deletion PR: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            logger.error(f"Failed to delete KB document '{title}': {e}")
            raise

    async def get_pr_status(self, pr_number: int) -> Dict[str, Any]:
        """
        Get status of a KB PR.

        Args:
            pr_number: PR number

        Returns:
            PR status information
        """
        return await self.pr_manager.get_pr_status(pr_number)

    async def search_kb_documents(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search existing KB documents.

        This is a simple text-based search through existing documents.
        For a production system, this would use more sophisticated search.

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results to return

        Returns:
            List of matching documents
        """
        try:
            logger.info(f"Searching KB documents for: '{query}'")

            # Get all existing documents
            all_docs = await self.read_existing_kb()

            # Filter by category if specified
            if category:
                all_docs = [doc for doc in all_docs if doc.get("category") == category]

            # Simple text search in title and content_preview
            query_lower = query.lower()
            matching_docs = []

            for doc in all_docs:
                relevance_score = 0.0

                # Search in title (higher weight)
                if query_lower in doc.get("title", "").lower():
                    relevance_score += 0.5

                # Search in content preview
                if query_lower in doc.get("content_preview", "").lower():
                    relevance_score += 0.3

                # Search in tags
                tags = doc.get("tags", [])
                for tag in tags:
                    if query_lower in tag.lower():
                        relevance_score += 0.2
                        break

                if relevance_score > 0:
                    doc["relevance_score"] = relevance_score
                    matching_docs.append(doc)

            # Sort by relevance and limit results
            matching_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = matching_docs[:limit]

            logger.info(f"Found {len(results)} matching documents")
            return results

        except Exception as e:
            logger.error(f"Failed to search KB documents: {e}")
            raise

    async def get_kb_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the KB repository.

        Returns:
            Dictionary with KB statistics
        """
        try:
            all_docs = await self.read_existing_kb()

            # Calculate basic stats
            stats = {
                "total_documents": len(all_docs),
                "by_category": {},
                "by_tags": {},
                "recent_documents": 0,  # Would need date parsing for this
            }

            # Count by category
            for doc in all_docs:
                category = doc.get("category", "unknown")
                stats["by_category"][category] = (
                    stats["by_category"].get(category, 0) + 1
                )

            # Count by tags
            for doc in all_docs:
                for tag in doc.get("tags", []):
                    stats["by_tags"][tag] = stats["by_tags"].get(tag, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get KB stats: {e}")
            raise

    async def create_batch_pr(
        self,
        title: str,
        operations: List[BatchOperation],
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Create a single PR with multiple KB operations.

        This allows combining multiple create/update/delete operations in one PR,
        which is more efficient for related changes.

        Args:
            title: Overall PR title
            operations: List of operations to perform
            summary: Brief summary for PR description
            source_url: Source URL (e.g., Slack thread)
            ai_confidence: AI confidence score

        Returns:
            PR URL
        """
        try:
            logger.info(f"Creating batch PR: {title} with {len(operations)} operations")

            # Generate branch name from title
            branch_name = self.client.generate_branch_name(title)

            # Create branch
            await self.client.create_branch(branch_name)

            # Ensure KB structure exists
            await self.client.ensure_kb_structure(branch_name)

            # Perform all operations
            commit_messages = []

            for i, op in enumerate(operations, 1):
                try:
                    if op.action == KBOperation.CREATE:
                        commit_message = f"Create: {op.title or op.file_path}"
                        await self.client.create_or_update_file(
                            branch_name=branch_name,
                            file_path=op.file_path,
                            content=op.content or "",
                            commit_message=commit_message,
                        )

                    elif op.action == KBOperation.UPDATE:
                        commit_message = f"Update: {op.title or op.file_path}"
                        await self.client.create_or_update_file(
                            branch_name=branch_name,
                            file_path=op.file_path,
                            content=op.content or "",
                            commit_message=commit_message,
                        )

                    elif op.action == KBOperation.APPEND:
                        # Read existing content first
                        existing_file = self.client.repo.get_contents(
                            op.file_path, ref=self.client.default_branch
                        )
                        existing_content = existing_file.decoded_content.decode("utf-8")
                        combined_content = (
                            existing_content.rstrip()
                            + "\n\n"
                            + (op.additional_content or "").strip()
                        )

                        commit_message = f"Append to: {op.title or op.file_path}"
                        await self.client.create_or_update_file(
                            branch_name=branch_name,
                            file_path=op.file_path,
                            content=combined_content,
                            commit_message=commit_message,
                        )

                    elif op.action == KBOperation.DELETE:
                        commit_message = f"Delete: {op.title or op.file_path}"
                        await self.client.delete_file(
                            branch_name=branch_name,
                            file_path=op.file_path,
                            commit_message=commit_message,
                        )

                    commit_messages.append(commit_message)
                    logger.info(
                        f"Completed operation {i}/{len(operations)}: {op.action.value} {op.file_path}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed operation {i}/{len(operations)}: {op.action.value} {op.file_path}: {e}"
                    )
                    # Continue with other operations, but log the failure
                    commit_messages.append(f"Failed: {op.action.value} {op.file_path}")

            # Create PR with batch summary
            pr_title = f"KB Batch: {title}"
            pr_body = self._build_batch_pr_body(
                summary=summary,
                operations=operations,
                commit_messages=commit_messages,
                source_url=source_url,
                ai_confidence=ai_confidence,
            )

            pr = self.client.repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=self.client.default_branch,
            )

            # Add batch-specific labels
            self._add_batch_pr_labels(pr, operations)

            logger.info(f"Successfully created batch PR: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            logger.error(f"Failed to create batch PR '{title}': {e}")
            raise

    def _build_batch_pr_body(
        self,
        summary: Optional[str],
        operations: List[BatchOperation],
        commit_messages: List[str],
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Build PR description body for batch operations.

        Args:
            summary: Brief summary
            operations: List of operations performed
            commit_messages: List of commit messages
            source_url: Source URL
            ai_confidence: AI confidence score

        Returns:
            Formatted PR body
        """
        body_parts = []

        # Add summary if provided
        if summary:
            body_parts.append(f"## Summary\n\n{summary}")

        # Add operations summary
        operations_summary = f"## Operations Performed ({len(operations)})\n\n"
        for i, (op, commit_msg) in enumerate(zip(operations, commit_messages), 1):
            operations_summary += f"{i}. **{op.action.value.upper()}** `{op.file_path}`"
            if op.title:
                operations_summary += f" - {op.title}"
            operations_summary += "\n"

        body_parts.append(operations_summary)

        # Add metadata section
        metadata_parts = []

        if source_url:
            metadata_parts.append(f"**Source**: {source_url}")

        if ai_confidence is not None:
            confidence_pct = int(ai_confidence * 100)
            metadata_parts.append(f"**AI Confidence**: {confidence_pct}%")

        metadata_parts.append(
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        if metadata_parts:
            body_parts.append("## Metadata\n\n" + "\n".join(metadata_parts))

        # Add footer
        body_parts.append(
            "---\n\n"
            "🤖 *This batch of knowledge base changes was automatically generated by Archie.*\n\n"
            "Please review all changes for accuracy before merging."
        )

        return "\n\n".join(body_parts)

    def _add_batch_pr_labels(self, pr, operations: List[BatchOperation]) -> None:
        """
        Add relevant labels to a batch PR.

        Args:
            pr: GitHub PR object
            operations: List of operations
        """
        try:
            labels = {"archie-generated", "knowledge-base", "batch-operation"}

            # Add operation-specific labels
            operation_types = {op.action.value for op in operations}
            labels.update(operation_types)

            # Add category labels based on file paths
            categories = set()
            for op in operations:
                if "/" in op.file_path:
                    category = op.file_path.split("/")[0]
                    categories.add(category)
            labels.update(categories)

            # Apply labels (only if they exist in the repository)
            existing_labels = {label.name for label in self.client.repo.get_labels()}
            valid_labels = [label for label in labels if label in existing_labels]

            if valid_labels:
                pr.add_to_labels(*valid_labels)
                logger.info(f"Added batch labels to PR #{pr.number}: {valid_labels}")
            else:
                logger.info(
                    f"No matching labels found in repository for: {list(labels)}"
                )

        except Exception as e:
            logger.warning(f"Failed to add batch labels to PR #{pr.number}: {e}")
            # Don't raise - labels are not critical
