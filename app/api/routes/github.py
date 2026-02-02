"""
GitHub API Routes
Owner: ① Slack · GitHub Integration & Flow Owner
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class PRCreateRequest(BaseModel):
    """Request to create a PR with knowledge base content."""

    title: str
    content: str  # Markdown content
    file_path: str  # Path in KB repo (e.g., "knowledge/troubleshooting/api-timeout.md")
    source_thread_url: str  # Original Slack thread URL for reference


class PRResponse(BaseModel):
    """PR creation response."""

    pr_number: int
    pr_url: str
    branch_name: str


@router.post("/pr", response_model=PRResponse)
async def create_pr(request: PRCreateRequest):
    """
    Create a PR with knowledge base document.

    1. Create new branch
    2. Add/update markdown file
    3. Create PR with metadata
    """
    # TODO: Implement using app.integrations.github
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/pr/{pr_number}/status")
async def get_pr_status(pr_number: int):
    """Get status of a PR."""
    # TODO: Implement PR status check
    raise HTTPException(status_code=501, detail="Not implemented")
