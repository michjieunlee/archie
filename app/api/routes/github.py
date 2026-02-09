"""
GitHub API Routes
Owner: ① Slack · GitHub Integration & Flow Owner

Provides REST API endpoints for GitHub KB operations.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.integrations.github.operations import GitHubKBOperations, BatchOperation

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy initialization to avoid import-time GitHub API calls
_github_ops = None

def get_github_ops() -> GitHubKBOperations:
    """Get GitHubKBOperations instance with lazy initialization."""
    global _github_ops
    if _github_ops is None:
        _github_ops = GitHubKBOperations()
    return _github_ops


# Request/Response Models

class KBDocumentRequest(BaseModel):
    """Request to create/update a KB document."""

    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Markdown content")
    file_path: str = Field(..., description="Path in KB repo (e.g., 'troubleshooting/api-timeout.md')")
    summary: Optional[str] = Field(None, description="Brief summary for PR description")
    source_url: Optional[str] = Field(None, description="Source URL (e.g., Slack thread)")
    ai_confidence: Optional[float] = Field(None, description="AI confidence score (0.0-1.0)")


class AppendRequest(BaseModel):
    """Request to append content to a KB document."""

    title: str = Field(..., description="Document title (for PR naming)")
    file_path: str = Field(..., description="Path to existing file in repository")
    additional_content: str = Field(..., description="Content to append")
    summary: Optional[str] = Field(None, description="Brief summary for PR description")
    source_url: Optional[str] = Field(None, description="Source URL (e.g., Slack thread)")
    ai_confidence: Optional[float] = Field(None, description="AI confidence score (0.0-1.0)")


class DeleteRequest(BaseModel):
    """Request to delete a KB document."""

    title: str = Field(..., description="Document title (for PR naming)")
    file_path: str = Field(..., description="Path to file to delete")
    reason: Optional[str] = Field(None, description="Reason for deletion")


class BatchRequest(BaseModel):
    """Request to perform multiple KB operations in one PR."""

    title: str = Field(..., description="Overall PR title")
    operations: List[BatchOperation] = Field(..., description="List of operations to perform")
    summary: Optional[str] = Field(None, description="Brief summary for PR description")
    source_url: Optional[str] = Field(None, description="Source URL (e.g., Slack thread)")
    ai_confidence: Optional[float] = Field(None, description="AI confidence score (0.0-1.0)")


class PRResponse(BaseModel):
    """PR operation response."""

    status: str = Field(..., description="Response status: success or error")
    pr_url: Optional[str] = Field(None, description="URL of the created/updated PR")
    message: str = Field(..., description="Success or error message")


class KBStatsResponse(BaseModel):
    """KB statistics response."""

    total_documents: int
    by_category: dict
    by_tags: dict
    recent_documents: int


# API Endpoints

@router.get("/kb/documents", response_model=List[dict])
async def list_kb_documents():
    """
    List all existing KB documents in the repository.

    Returns document metadata including title, path, category, tags, and content preview.
    """
    try:
        logger.info("Listing KB documents")
        documents = await get_github_ops().read_existing_kb()
        return documents

    except Exception as e:
        logger.error(f"Error listing KB documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/documents", response_model=PRResponse)
async def create_kb_document(request: KBDocumentRequest):
    """
    Create a new KB document via PR.

    Creates a branch, adds the document, and opens a PR for review.
    """
    try:
        logger.info(f"Creating KB document: {request.title}")

        pr_url = await get_github_ops().create_kb_document(
            title=request.title,
            content=request.content,
            file_path=request.file_path,
            summary=request.summary,
            source_url=request.source_url,
            ai_confidence=request.ai_confidence,
        )

        return PRResponse(
            status="success",
            pr_url=pr_url,
            message=f"Successfully created KB document PR: {request.title}"
        )

    except Exception as e:
        logger.error(f"Error creating KB document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/kb/documents", response_model=PRResponse)
async def update_kb_document(request: KBDocumentRequest):
    """
    Update an existing KB document via PR.

    Creates a branch with the updated content and opens a PR for review.
    """
    try:
        logger.info(f"Updating KB document: {request.title}")

        pr_url = await get_github_ops().update_kb_document(
            title=request.title,
            content=request.content,
            file_path=request.file_path,
            summary=request.summary,
            source_url=request.source_url,
            ai_confidence=request.ai_confidence,
        )

        return PRResponse(
            status="success",
            pr_url=pr_url,
            message=f"Successfully created update PR: {request.title}"
        )

    except Exception as e:
        logger.error(f"Error updating KB document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/documents/append", response_model=PRResponse)
async def append_to_kb_document(request: AppendRequest):
    """
    Append content to an existing KB document via PR.

    Reads the existing document, appends new content, and creates a PR.
    """
    try:
        logger.info(f"Appending to KB document: {request.title}")

        pr_url = await get_github_ops().append_to_kb_document(
            title=request.title,
            file_path=request.file_path,
            additional_content=request.additional_content,
            summary=request.summary,
            source_url=request.source_url,
            ai_confidence=request.ai_confidence,
        )

        return PRResponse(
            status="success",
            pr_url=pr_url,
            message=f"Successfully created append PR: {request.title}"
        )

    except Exception as e:
        logger.error(f"Error appending to KB document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/kb/documents", response_model=PRResponse)
async def delete_kb_document(request: DeleteRequest):
    """
    Delete a KB document via PR.

    Creates a branch with the file removed and opens a PR for review.
    """
    try:
        logger.info(f"Deleting KB document: {request.title}")

        pr_url = await get_github_ops().delete_kb_document(
            title=request.title,
            file_path=request.file_path,
            reason=request.reason,
        )

        return PRResponse(
            status="success",
            pr_url=pr_url,
            message=f"Successfully created deletion PR: {request.title}"
        )

    except Exception as e:
        logger.error(f"Error deleting KB document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/search")
async def search_kb_documents(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(10, description="Maximum results to return", ge=1, le=50)
):
    """
    Search existing KB documents.

    Performs simple text search across document titles, content, and tags.
    """
    try:
        logger.info(f"Searching KB documents: '{query}'")

        results = await get_github_ops().search_kb_documents(
            query=query,
            category=category,
            limit=limit,
        )

        return {
            "query": query,
            "results": results,
            "total": len(results),
        }

    except Exception as e:
        logger.error(f"Error searching KB documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/stats", response_model=KBStatsResponse)
async def get_kb_stats():
    """
    Get statistics about the KB repository.

    Returns document counts by category, tags, and other metrics.
    """
    try:
        logger.info("Getting KB statistics")
        stats = await get_github_ops().get_kb_stats()
        return KBStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting KB stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pr/{pr_number}/status")
async def get_pr_status(pr_number: int):
    """
    Get the current status of a PR.

    Returns detailed information about the PR including state, commits, etc.
    """
    try:
        logger.info(f"Getting PR status: #{pr_number}")
        status = await get_github_ops().get_pr_status(pr_number)
        return status

    except Exception as e:
        logger.error(f"Error getting PR status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/batch", response_model=PRResponse)
async def create_batch_pr(request: BatchRequest):
    """
    Create a single PR with multiple KB operations.

    This allows combining multiple create/update/delete operations in one PR,
    which is more efficient for related changes.
    """
    try:
        logger.info(f"Creating batch PR: {request.title} with {len(request.operations)} operations")

        pr_url = await get_github_ops().create_batch_pr(
            title=request.title,
            operations=request.operations,
            summary=request.summary,
            source_url=request.source_url,
            ai_confidence=request.ai_confidence,
        )

        return PRResponse(
            status="success",
            pr_url=pr_url,
            message=f"Successfully created batch PR: {request.title}"
        )

    except Exception as e:
        logger.error(f"Error creating batch PR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


