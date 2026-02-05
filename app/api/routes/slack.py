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
from app.integrations.slack.models import SlackThread
from app.ai_core.masking.pii_masker import PIIMasker

logger = logging.getLogger(__name__)
router = APIRouter()


async def _apply_pii_masking(
    slack_thread: SlackThread,
    slack_client: SlackClient
):
    """Apply PII masking and return masked thread."""
    logger.info("Applying PII masking...")
    pii_masker = PIIMasker()

    # Create temporary StandardizedThread for PII masking
    temp_thread = slack_client.convert_to_standardized_thread(slack_thread)

    # Mask the thread
    masked_threads = await pii_masker.mask_threads([temp_thread])
    return masked_threads[0]


async def _create_final_thread_with_user_mapping(
    slack_thread: SlackThread,
    masked_thread,
    slack_client: SlackClient
):
    """Update SlackMessages with masked user names and create final StandardizedThread."""
    # Create user mapping from masked thread
    user_mapping = {}
    for msg in masked_thread.messages:
        user_mapping[msg.author_id] = msg.author_name

    # Apply mapping back to SlackMessages
    for slack_msg in slack_thread.messages:
        slack_msg.user_name = user_mapping.get(slack_msg.user_id)

    # Create final StandardizedThread with proper user names
    return slack_client.convert_to_standardized_thread(slack_thread)


@router.get("/extract")
async def extract_conversations(
    from_datetime: Optional[datetime] = Query(None, description="Start datetime for message range (ISO format)"),
    to_datetime: Optional[datetime] = Query(None, description="End datetime for message range (ISO format)"),
    limit: Optional[int] = Query(100, description="Maximum messages if no datetime range (default: 100)"),
    channel_id: Optional[str] = Query(None, description="Slack channel ID (optional, uses config if not provided)")
):
    """
    Complete Slack conversation extraction pipeline with thread expansion and PII masking.

    Pipeline:
    1. Extract Slack conversations with automatic thread expansion
    2. Apply PII masking to assign proper user names (USER_1, USER_2, etc.)
    3. Convert to StandardizedThread format with masked user names

    Examples:
    - GET /api/slack/extract  (uses defaults)
    - GET /api/slack/extract?limit=50
    - GET /api/slack/extract?from_datetime=2026-01-01T00:00:00Z&to_datetime=2026-01-05T23:59:59Z
    """
    start_time = time.time()

    try:
        logger.info(f"Starting complete extraction pipeline - from_datetime: {from_datetime}, to_datetime: {to_datetime}, limit: {limit}")

        # Step 1: Extract conversations with thread expansion
        slack_client = SlackClient()
        slack_thread = await slack_client.extract_conversations_with_threads(
            channel_id=channel_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit or 100
        )

        # Handle empty case inline
        if not slack_thread.messages:
            return {
                "success": True,
                "message": "No messages found in the specified range",
                "threads": [],
                "total_messages": 0,
                "total_participants": 0,
                "processing_time_seconds": round(time.time() - start_time, 2)
            }

        # Step 2: Apply PII masking
        masked_thread = await _apply_pii_masking(slack_thread, slack_client)

        # Step 3: Create final thread with user mapping
        final_thread = await _create_final_thread_with_user_mapping(
            slack_thread, masked_thread, slack_client
        )

        # Build response
        total_messages = len(final_thread.messages)
        total_participants = final_thread.participant_count
        processing_time = time.time() - start_time

        logger.info(f"Pipeline complete: {total_messages} messages, {total_participants} participants in {processing_time:.2f}s")

        return {
            "success": True,
            "message": f"Successfully extracted and processed conversation with thread expansion",
            "threads": [final_thread.model_dump()],
            "total_messages": total_messages,
            "total_participants": total_participants,
            "processing_time_seconds": round(processing_time, 2),
            "pipeline_stats": {
                "threads_expanded": final_thread.metadata.get("threads_expanded", False),
                "pii_masked": True,
                "extraction_params": {
                    "from_datetime": from_datetime.isoformat() if from_datetime else None,
                    "to_datetime": to_datetime.isoformat() if to_datetime else None,
                    "limit": limit,
                    "channel_id": channel_id
                }
            }
        }

    except Exception as e:
        logger.error(f"Error in extraction pipeline: {e}")
        processing_time = time.time() - start_time

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Pipeline failed: {str(e)}",
                "processing_time_seconds": round(processing_time, 2)
            }
        )
