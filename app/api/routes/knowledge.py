"""
Knowledge Base API Routes
Orchestrates the full pipeline: Slack -> AI Processing -> GitHub PR
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from enum import Enum

router = APIRouter()


class KBAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    IGNORE = "ignore"


class ProcessRequest(BaseModel):
    """Request to process a Slack thread into KB."""

    thread_permalink: str


class ProcessResponse(BaseModel):
    """Processing result."""

    action: KBAction
    reason: str
    pr_url: str | None = None
    kb_document_path: str | None = None


@router.post("/process", response_model=ProcessResponse)
async def process_thread(request: ProcessRequest):
    """
    Full pipeline: Slack thread -> Knowledge Base PR

    Pipeline steps:
    1. Fetch thread from Slack (integrations.slack)
    2. Mask PII (ai_core.masking)
    3. Extract KB candidate (ai_core.extraction)
    4. Match against existing KB (ai_core.matching)
    5. Generate/Update KB document (ai_core.generation)
    6. Create GitHub PR (integrations.github)
    """
    # TODO: Implement using app.services.pipeline
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/candidates")
async def list_kb_candidates():
    """List pending KB candidates for review."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")
