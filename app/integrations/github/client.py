"""
GitHub API Client
Owner: ① Slack · GitHub Integration & Flow Owner

Responsibilities:
- Repository operations
- Branch management
- File operations (create/update)
- KB repository reading and parsing
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import yaml
from github import Github
from github.Repository import Repository
from github.GithubException import GithubException, UnknownObjectException
from app.config import get_settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client wrapper."""

    def __init__(self):
        settings = get_settings()
        self.client = Github(settings.github_token)
        self.repo: Repository = self.client.get_repo(
            f"{settings.github_repo_owner}/{settings.github_repo_name}"
        )
        self.default_branch = settings.github_default_branch
        self._cached_categories: Optional[List[str]] = (
            None  # Cache for discovered categories
        )
        logger.info(f"GitHub client initialized for {self.repo.full_name}")

    async def read_kb_repository(self) -> List[Dict[str, Any]]:
        """
        Scan KB repository and return existing documents with full content.
        This is called by the orchestrator to get existing KB docs for AI matching.

        Returns:
            List of document data: [{title, path, category, tags, content, metadata}, ...]
        """
        try:
            logger.info("Reading KB repository structure and content...")
            documents = []

            # Discover categories and cache them
            await self._discover_categories()

            # Get all markdown files in the repository
            contents = self.repo.get_contents("", ref=self.default_branch)

            # Process files and directories
            documents.extend(await self._scan_directory_for_kb(contents))

            logger.info(f"Found {len(documents)} KB documents in repository")
            return documents

        except UnknownObjectException:
            # Repository is empty or doesn't exist
            logger.info("Repository is empty or branch doesn't exist")
            return []
        except GithubException as e:
            logger.error(f"GitHub API error reading repository: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error reading KB repository: {e}")
            raise

    async def _scan_directory_for_kb(self, contents) -> List[Dict[str, Any]]:
        """
        Recursively scan directory contents for KB markdown files.

        Args:
            contents: GitHub contents list

        Returns:
            List of document metadata
        """
        documents = []

        for content in contents:
            if content.type == "dir":
                # Recursively scan subdirectories
                subcontents = self.repo.get_contents(
                    content.path, ref=self.default_branch
                )
                documents.extend(await self._scan_directory_for_kb(subcontents))
            elif content.type == "file" and content.name.endswith(".md"):
                # Parse markdown file
                doc_metadata = await self._parse_kb_document(content)
                if doc_metadata:
                    documents.append(doc_metadata)

        return documents

    async def _parse_kb_document(self, file_content) -> Optional[Dict[str, Any]]:
        """
        Parse a KB markdown file and extract full content and metadata.

        Args:
            file_content: GitHub file content object

        Returns:
            Document data with full content or None if not a valid KB document
        """
        try:
            # Get file content
            content = file_content.decoded_content.decode("utf-8")

            # Extract YAML frontmatter and content
            frontmatter, markdown_content = self._extract_frontmatter(content)

            # Extract category from path or frontmatter
            category = self._extract_category_from_path(file_content.path)
            if not category and frontmatter:
                category = frontmatter.get("category", "unknown")

            return {
                "title": (
                    frontmatter.get("title", file_content.name.replace(".md", ""))
                    if frontmatter
                    else file_content.name.replace(".md", "")
                ),
                "path": file_content.path,
                "category": category,
                "tags": frontmatter.get("tags", []) if frontmatter else [],
                "content": content,  # Full content for AI matching
                "markdown_content": markdown_content,  # Content without frontmatter
                "frontmatter": frontmatter or {},  # All frontmatter metadata
                "ai_confidence": (
                    frontmatter.get("ai_confidence") if frontmatter else None
                ),
                "created_date": (
                    frontmatter.get("created_date") if frontmatter else None
                ),
                "last_updated": (
                    frontmatter.get("last_updated") if frontmatter else None
                ),
                "file_size": len(content),  # For monitoring purposes
            }

        except Exception as e:
            logger.warning(f"Failed to parse KB document {file_content.path}: {e}")
            return None

    def _extract_frontmatter(
        self, content: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Extract YAML frontmatter from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (frontmatter_dict, markdown_content)
        """
        if not content.startswith("---"):
            return None, content

        try:
            # Find the closing ---
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None, content

            frontmatter_yaml = parts[1].strip()
            markdown_content = parts[2].strip()

            # Parse YAML
            frontmatter = yaml.safe_load(frontmatter_yaml) if frontmatter_yaml else {}

            return frontmatter, markdown_content

        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return None, content

    def _extract_category_from_path(self, file_path: str) -> Optional[str]:
        """
        Extract category from file path using discovered categories.

        Args:
            file_path: Path to the file (e.g., "troubleshooting/db-issue.md")

        Returns:
            Category name or None
        """
        if not self._cached_categories:
            return None

        for category in self._cached_categories:
            if file_path.startswith(f"{category}/"):
                return category

        return None

    async def _discover_categories(self) -> List[str]:
        """
        Discover categories by scanning repository structure.
        Cache the results for subsequent calls.

        Returns:
            List of category names found in repository
        """
        if self._cached_categories is not None:
            return self._cached_categories

        try:
            logger.info("Discovering KB categories from repository structure...")
            categories = set()

            # Get root level contents
            contents = self.repo.get_contents("", ref=self.default_branch)

            for content in contents:
                if content.type == "dir":
                    # Check if directory contains markdown files (indicating it's a category)
                    try:
                        dir_contents = self.repo.get_contents(
                            content.path, ref=self.default_branch
                        )
                        has_markdown = any(
                            item.name.endswith(".md")
                            for item in dir_contents
                            if item.type == "file"
                        )
                        if has_markdown:
                            categories.add(content.name)
                            logger.info(f"Found category: {content.name}")
                    except Exception as e:
                        logger.warning(f"Could not scan directory {content.path}: {e}")

            # Convert to sorted list for consistency
            self._cached_categories = sorted(list(categories))

            if not self._cached_categories:
                # Fallback to default categories if none found
                logger.info(
                    "No categories found in repository, using default categories"
                )
                self._cached_categories = ["troubleshooting", "processes", "decisions"]

            logger.info(f"Discovered categories: {self._cached_categories}")
            return self._cached_categories

        except UnknownObjectException:
            # Repository is empty
            logger.info("Repository is empty, using default categories")
            self._cached_categories = ["troubleshooting", "processes", "decisions"]
            return self._cached_categories
        except Exception as e:
            logger.warning(f"Error discovering categories: {e}, using defaults")
            self._cached_categories = ["troubleshooting", "processes", "decisions"]
            return self._cached_categories

    def get_categories(self) -> List[str]:
        """
        Get cached categories without async call.

        Returns:
            List of category names or empty list if not discovered yet
        """
        return self._cached_categories or []

    def refresh_categories(self) -> None:
        """Clear cached categories to force rediscovery on next access."""
        self._cached_categories = None
        logger.info("Category cache cleared")

    async def create_branch(self, branch_name: str) -> str:
        """
        Create a new branch from default branch.

        Args:
            branch_name: Name for the new branch

        Returns:
            Full branch reference
        """
        try:
            # Get the latest commit SHA from default branch
            default_branch_ref = self.repo.get_branch(self.default_branch)
            default_sha = default_branch_ref.commit.sha

            # Create new branch
            new_ref = f"refs/heads/{branch_name}"
            self.repo.create_git_ref(ref=new_ref, sha=default_sha)

            logger.info(f"Created branch: {branch_name}")
            return new_ref

        except GithubException as e:
            if "Reference already exists" in str(e):
                logger.info(
                    f"Branch {branch_name} already exists, using existing branch"
                )
                return f"refs/heads/{branch_name}"
            else:
                logger.error(f"Failed to create branch {branch_name}: {e}")
                raise

    async def create_or_update_file(
        self,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> str:
        """
        Create or update a file in the repository.

        Args:
            branch_name: Target branch
            file_path: Path in repository
            content: File content
            commit_message: Commit message

        Returns:
            Commit SHA
        """
        try:
            # Check if file exists
            file_exists = await self.file_exists(branch_name, file_path)

            if file_exists:
                # Update existing file
                existing_file = self.repo.get_contents(file_path, ref=branch_name)
                result = self.repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch_name,
                )
                logger.info(f"Updated file: {file_path} in branch {branch_name}")
            else:
                # Create new file
                result = self.repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    branch=branch_name,
                )
                logger.info(f"Created file: {file_path} in branch {branch_name}")

            return result["commit"].sha

        except GithubException as e:
            logger.error(f"Failed to create/update file {file_path}: {e}")
            raise

    async def file_exists(self, branch_name: str, file_path: str) -> bool:
        """Check if a file exists in the repository."""
        try:
            self.repo.get_contents(file_path, ref=branch_name)
            return True
        except UnknownObjectException:
            return False
        except GithubException as e:
            logger.error(f"Error checking file existence {file_path}: {e}")
            return False

    async def ensure_kb_structure(self, branch_name: str) -> None:
        """
        Ensure KB folder structure exists in the repository based on discovered categories.
        Creates folders if they don't exist.

        Args:
            branch_name: Target branch to create structure in
        """
        try:
            # Get discovered categories or use defaults
            categories = await self._discover_categories()

            for category in categories:
                placeholder_path = f"{category}/.gitkeep"

                # Check if category folder exists by checking for any file in it
                if not await self.file_exists(branch_name, placeholder_path):
                    # Create placeholder file to create the directory
                    await self.create_or_update_file(
                        branch_name=branch_name,
                        file_path=placeholder_path,
                        content="# This file ensures the directory exists in Git\n",
                        commit_message=f"Initialize {category} category folder",
                    )
                    logger.info(f"Created {category} folder structure")

        except Exception as e:
            logger.warning(f"Failed to create KB structure: {e}")
            # Don't raise - this is not critical

    def generate_branch_name(self, title: str) -> str:
        """
        Generate a branch name from document title.
        Format: kb/{sanitized-title}

        Args:
            title: Document title

        Returns:
            Sanitized branch name
        """
        # Sanitize title for branch name
        sanitized = re.sub(r"[^a-zA-Z0-9\s-]", "", title)  # Remove special chars
        sanitized = re.sub(
            r"\s+", "-", sanitized.strip()
        )  # Replace spaces with hyphens
        sanitized = sanitized.lower()[:50]  # Lowercase and limit length

        return f"kb/{sanitized}"

    async def delete_file(
        self, branch_name: str, file_path: str, commit_message: str
    ) -> str:
        """
        Delete a file from the repository.

        Args:
            branch_name: Target branch
            file_path: Path to file to delete
            commit_message: Commit message

        Returns:
            Commit SHA
        """
        try:
            # Get existing file to get its SHA
            existing_file = self.repo.get_contents(file_path, ref=branch_name)

            # Delete the file
            result = self.repo.delete_file(
                path=file_path,
                message=commit_message,
                sha=existing_file.sha,
                branch=branch_name,
            )

            logger.info(f"Deleted file: {file_path} from branch {branch_name}")
            return result["commit"].sha

        except UnknownObjectException:
            logger.warning(f"File {file_path} does not exist, cannot delete")
            raise
        except GithubException as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise
