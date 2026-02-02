"""
Slack API Routes
Owner: ① Slack · GitHub Integration & Flow Owner
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ThreadRequest(BaseModel):
    """Request to fetch a Slack thread by permalink."""

    permalink: str  # e.g., https://workspace.slack.com/archives/C123ABC456/p1234567890123456


class ThreadResponse(BaseModel):
    """Standardized thread data response."""

    channel_id: str
    thread_ts: str
    messages: list[dict]


@router.post("/thread", response_model=ThreadResponse)
async def fetch_thread(request: ThreadRequest):
    """
    Fetch thread messages from Slack permalink.

    1. Parse permalink to extract channel_id and thread_ts
    2. Call Slack API (conversations.replies)
    3. Return standardized thread data
    """
    # TODO: Implement using app.integrations.slack
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/events")
async def handle_slack_events(payload: dict):
    """
    Handle Slack Events API (thread detection, mentions, etc.)
    """
    # TODO: Implement Slack event handling
    raise HTTPException(status_code=501, detail="Not implemented")
