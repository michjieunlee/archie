"""
Slack API Routes
Owner: ① Slack · GitHub Integration & Flow Owner
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import logging
import time

from app.integrations.slack.client import SlackClient

logger = logging.getLogger(__name__)
router = APIRouter()


async def fetch_slack_conversation(
    channel_id: Optional[str] = None,
    from_datetime: Optional[datetime] = None,
    to_datetime: Optional[datetime] = None,
    limit: int = 100
) -> 'StandardizedConversation':
    """
    Fetch Slack conversations with reply expansion.
    
    Args:
        channel_id: Slack channel ID (uses configured default if not provided)
        from_datetime: Start time for message fetching
        to_datetime: End time for message fetching
        limit: Maximum number of messages to fetch (max 100)
        
    Returns:
        StandardizedConversation with all messages and replies (unmasked)
    """
    try:
        client = SlackClient()
        
        # Fetch Slack conversations with replies (no PII masking)
        conversation = await client.fetch_conversations_with_threads(
            channel_id=channel_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=min(limit, 100)  # Max 100 messages
        )
        
        logger.info(f"Successfully fetched Slack conversation with {len(conversation.messages)} messages, "
                   f"{conversation.participant_count} participants")
        
        return conversation
        
    except Exception as e:
        logger.error(f"Error fetching Slack conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Slack conversation: {str(e)}")


@router.get("/fetch")
async def fetch_conversations(
    from_datetime: Optional[datetime] = Query(None, description="Start datetime for message range (ISO format)"),
    to_datetime: Optional[datetime] = Query(None, description="End datetime for message range (ISO format)"),
    limit: Optional[int] = Query(100, description="Maximum messages if no datetime range (default: 100)"),
    channel_id: Optional[str] = Query(None, description="Slack channel ID (optional, uses config if not provided)")
):
    """
    Fetch Slack conversations with reply expansion.

    Returns raw StandardizedConversation data (no PII masking applied).
    For PII masking, use a separate processing step.

    Examples:
    - GET /api/slack/fetch  (uses defaults)
    - GET /api/slack/fetch?limit=50
    - GET /api/slack/fetch?from_datetime=2026-01-01T00:00:00Z&to_datetime=2026-01-05T23:59:59Z
    """
    start_time = time.time()

    try:
        logger.info(f"Starting conversation fetch - from_datetime: {from_datetime}, to_datetime: {to_datetime}, limit: {limit}")

        # Fetch conversations (no PII masking)
        conversation = await fetch_slack_conversation(
            channel_id=channel_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit or 100
        )

        # Handle empty case
        if not conversation.messages:
            return {
                "success": True,
                "message": "No messages found in the specified range",
                "conversation": None,
                "total_messages": 0,
                "total_participants": 0,
                "processing_time_seconds": round(time.time() - start_time, 2)
            }

        # Build response
        total_messages = len(conversation.messages)
        total_participants = conversation.participant_count
        processing_time = time.time() - start_time

        logger.info(f"Fetch complete: {total_messages} messages, {total_participants} participants in {processing_time:.2f}s")

        return {
            "success": True,
            "message": f"Successfully fetched conversation with reply expansion",
            "conversation": conversation.model_dump(),
            "total_messages": total_messages,
            "total_participants": total_participants,
            "processing_time_seconds": round(processing_time, 2),
            "fetch_stats": {
                "replies_expanded": conversation.metadata.get("replies_expanded", False),
                "pii_masked": False,  # No PII masking applied
                "fetch_params": {
                    "from_datetime": from_datetime.isoformat() if from_datetime else None,
                    "to_datetime": to_datetime.isoformat() if to_datetime else None,
                    "limit": limit,
                    "channel_id": channel_id
                }
            }
        }

    except Exception as e:
        logger.error(f"Error in fetch: {e}")
        processing_time = time.time() - start_time

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Fetch failed: {str(e)}",
                "processing_time_seconds": round(processing_time, 2)
            }
        )