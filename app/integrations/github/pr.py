"""
GitHub PR Manager
Owner: ① Slack · GitHub Integration & Flow Owner

Responsibilities:
- PR creation with proper metadata
- PR template and labeling
- Retry with numbered branch names on PR conflicts
"""

import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from github import GithubException
from app.integrations.github.client import GitHubClient
from app.integrations.github.models import PRMetadata

logger = logging.getLogger(__name__)


@dataclass
class PRResult:
    """Result of PR creation."""

    pr_number: int
    pr_url: str
    branch_name: str


class PRManager:
    """Manages Knowledge Base PR creation."""

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    async def create_pr(
        self,
        title: str,
        content: str,
        file_path: str,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        max_retries: int = 5,
    ) -> PRResult:
        """Alias for create_kb_pr for backward compatibility."""
        return await self.create_kb_pr(
            title=title,
            content=content,
            file_path=file_path,
            summary=summary,
            source_url=source_url,
            ai_confidence=ai_confidence,
            max_retries=max_retries,
        )

    async def create_kb_pr(
        self,
        title: str,
        content: str,
        file_path: str,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        max_retries: int = 5,
    ) -> PRResult:
        """
        Create a PR with a document.

        Steps:
        1. Generate unique branch name from title
        2. Create branch from main
        3. Ensure KB folder structure exists
        4. Add/update markdown file
        5. Create PR with metadata

        If a PR already exists for the branch, retry with numbered branch name
        (e.g., kb/title-2, kb/title-3, etc.)

        Args:
            title: PR title (used for PR title and branch name generation)
            content: Markdown content to write
            file_path: Path in repo (e.g., "troubleshooting/db-issue.md")
            summary: Brief summary of the document
            source_url: Source URL (e.g., Slack thread URL)
            ai_confidence: AI confidence score
            max_retries: Maximum number of retries for branch name conflicts

        Returns:
            PRResult with PR details
        """
        # Step 1: Generate base branch name from title
        base_branch_name = self.client.generate_branch_name(title)

        for attempt in range(max_retries):
            try:
                # Add suffix for retries (2, 3, 4, ...)
                if attempt == 0:
                    branch_name = base_branch_name
                else:
                    branch_name = f"{base_branch_name}-{attempt + 1}"

                logger.info(
                    f"Attempting to create PR with branch: {branch_name} (attempt {attempt + 1}/{max_retries})"
                )

                # Step 2: Create branch
                await self.client.create_branch(branch_name)

                # Step 3: Ensure KB folder structure exists
                await self.client.ensure_kb_structure(branch_name)

                # Step 4: Create/update the file
                commit_message = f"Add document: {title}"
                commit_sha = await self.client.create_or_update_file(
                    branch_name=branch_name,
                    file_path=file_path,
                    content=content,
                    commit_message=commit_message,
                )
                logger.info(f"Added/updated file {file_path} in branch {branch_name}")

                # Step 5: Create PR
                pr_body = self._build_pr_body(
                    summary=summary,
                    source_url=source_url,
                    ai_confidence=ai_confidence,
                )

                # Create the PR
                pr = self.client.repo.create_pull(
                    title=title,
                    body=pr_body,
                    head=branch_name,
                    base=self.client.default_branch,
                )

                # Add labels to categorize the PR
                self._add_pr_labels(pr, file_path)

                logger.info(f"Created PR #{pr.number}: {pr.html_url}")

                return PRResult(
                    pr_number=pr.number,
                    pr_url=pr.html_url,
                    branch_name=branch_name,
                )

            except GithubException as e:
                # Check if error is "PR already exists" (422 Validation Failed)
                if (
                    e.status == 422
                    and "pull request already exists" in str(e.data).lower()
                ):
                    logger.warning(
                        f"PR already exists for branch {branch_name}, trying with suffix -{attempt + 2}"
                    )
                    continue
                # Check if branch already exists
                elif (
                    e.status == 422
                    and "reference already exists" in str(e.data).lower()
                ):
                    logger.warning(
                        f"Branch {branch_name} already exists, trying with suffix -{attempt + 2}"
                    )
                    continue
                else:
                    logger.error(f"Failed to create PR for '{title}': {e}")
                    raise
            except Exception as e:
                logger.error(f"Failed to create PR for '{title}': {e}")
                raise

        # All retries exhausted
        raise Exception(
            f"Failed to create PR for '{title}' after {max_retries} attempts - all branch names are taken"
        )

    def _build_pr_body(
        self,
        summary: Optional[str] = None,
        source_url: Optional[str] = None,
        ai_confidence: Optional[float] = None,
    ) -> str:
        """
        Build PR description body with metadata.

        Args:
            summary: Brief document summary
            source_url: Source URL (e.g., Slack thread)
            ai_confidence: AI confidence score

        Returns:
            Formatted PR body
        """
        body_parts = []

        # Add summary if provided
        if summary:
            body_parts.append(f"## Summary\n\n{summary}")

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
            "🤖 *This knowledge base document was automatically generated by Archie from team conversations.*\n\n"
            "Please review the content for accuracy before merging."
        )

        return "\n\n".join(body_parts)

    def _add_pr_labels(self, pr, file_path: str) -> None:
        """
        Add relevant labels to the PR based on the file path.

        Args:
            pr: GitHub PR object
            file_path: Path to the file
        """
        try:
            labels = ["archie-generated", "knowledge-base"]

            # Add category-specific label
            if file_path.startswith("troubleshooting/"):
                labels.append("troubleshooting")
            elif file_path.startswith("processes/"):
                labels.append("process")
            elif file_path.startswith("decisions/"):
                labels.append("decision")
            elif file_path.startswith("references/"):
                labels.append("reference")
            elif file_path.startswith("general/"):
                labels.append("general")

            # Apply labels (only if they exist in the repository)
            existing_labels = {label.name for label in self.client.repo.get_labels()}
            valid_labels = [label for label in labels if label in existing_labels]

            if valid_labels:
                pr.add_to_labels(*valid_labels)
                logger.info(f"Added labels to PR #{pr.number}: {valid_labels}")
            else:
                logger.info(f"No matching labels found in repository for: {labels}")

        except Exception as e:
            logger.warning(f"Failed to add labels to PR #{pr.number}: {e}")
            # Don't raise - labels are not critical

    async def get_pr_status(self, pr_number: int) -> dict:
        """
        Get the current status of a PR.

        Args:
            pr_number: PR number to check

        Returns:
            Dictionary with PR status information
        """
        try:
            pr = self.client.repo.get_pull(pr_number)

            return {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "merged": pr.merged,
                "url": pr.html_url,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "author": pr.user.login,
                "branch": pr.head.ref,
                "commits": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
            }

        except Exception as e:
            logger.error(f"Failed to get PR status for #{pr_number}: {e}")
            raise

    async def update_kb_pr(
        self,
        pr_number: int,
        content: str,
        file_path: str,
        commit_message: str,
    ) -> str:
        """
        Update an existing KB PR with new content.

        Args:
            pr_number: Existing PR number
            content: Updated markdown content
            file_path: Path to the file to update
            commit_message: Commit message for the update

        Returns:
            Commit SHA
        """
        try:
            # Get PR details
            pr = self.client.repo.get_pull(pr_number)
            branch_name = pr.head.ref

            # Update the file in the PR branch
            commit_sha = await self.client.create_or_update_file(
                branch_name=branch_name,
                file_path=file_path,
                content=content,
                commit_message=commit_message,
            )

            logger.info(f"Updated PR #{pr_number} with new content in {file_path}")
            return commit_sha

        except Exception as e:
            logger.error(f"Failed to update PR #{pr_number}: {e}")
            raise
