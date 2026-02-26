"""
Knowledge Base Main API Routes

Main entrypoint with three use case endpoints:
1. GET /api/kb/from-slack - Update KB from Slack messages
2. POST /api/kb/from-text - Update KB from free text
3. POST /api/kb/query - Query knowledge base (Q&A)
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.services.kb_orchestrator import KBOrchestrator
from app.models.api_responses import (
    KBProcessingResponse,
    KBQueryResponse,
)
from app.models.thread import (
    StandardizedMessage,
    StandardizedConversation,
    Source,
    SourceType,
)
from app.ai_core.masking.pii_masker import PIIMasker

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize orchestrator (singleton pattern)
orchestrator = KBOrchestrator()


# Request models for POST endpoints


class TextKBRequest(BaseModel):
    """Request model for text-to-KB endpoint."""

    text: str = Field(..., description="Free text input to process into KB")
    title: Optional[str] = Field(
        None, description="Optional title for the conversation"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class KBQueryRequest(BaseModel):
    """Request model for KB query endpoint."""

    query: str = Field(..., description="User's question about the knowledge base")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Recent conversation history. Format: [{'role': 'user'|'assistant', 'content': str}]"
    )


class MaskMessageRequest(BaseModel):
    """Request model for message masking endpoint."""

    text: str = Field(..., description="Text to mask PII from")


# API Endpoints


@router.post("/mask-message")
async def mask_message(request: MaskMessageRequest):
    """
    Mask PII in a text message.

    This endpoint is used to mask user messages before
    sending them to LLM for processing. This ensures PII is never exposed
    in prompts for intent classification, chat conversations, or API calls.

    Pipeline:
    1. Convert text to StandardizedMessage format
    2. Use PIIMasker to mask PII entities
    3. Return masked text

    Example request body:
    ```json
    {
        "text": "My email is john.doe@example.com and my ID is D123456"
    }
    ```

    Example response:
    ```json
    {
        "masked_text": "My email is MASKED_EMAIL and my ID is MASKED_I_NUMBER",
        "is_masked": true
    }
    ```
    """
    try:
        logger.info(f"Mask message request: text_length={len(request.text)}")

        # Create a temporary StandardizedMessage for masking
        temp_message = StandardizedMessage(
            idx=0,
            id="mask_temp",
            author_id="user",
            author_name="User",
            content=request.text,
            timestamp=datetime.now(),
            is_masked=False,
        )

        # Create a temporary conversation with single message
        temp_conversation = StandardizedConversation(
            id="mask_temp",
            source=Source(
                type=SourceType.TEXT,
                channel_id="ui",
                channel_name="Streamlit UI",
            ),
            messages=[temp_message],
            participant_count=1,
            created_at=datetime.now(),
            last_activity_at=datetime.now(),
        )

        # Initialize masker and mask the conversation
        try:
            masker = PIIMasker()
            masked_conversations = await masker.mask_conversations([temp_conversation])
        except Exception as masker_error:
            logger.error(f"Failed to initialize or use PIIMasker: {str(masker_error)}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"PII masking service unavailable: {str(masker_error)}",
            )

        # Extract masked text from result
        masked_text = masked_conversations[0].messages[0].content

        logger.info(f"Message masked successfully: original_length={len(request.text)}, masked_length={len(masked_text)}")

        return {
            "masked_text": masked_text,
            "is_masked": True,
        }

    except Exception as e:
        logger.error(f"Error in mask message endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mask message: {str(e)}",
        )


@router.get("/from-slack", response_model=KBProcessingResponse)
async def kb_from_slack(
    channel_id: Optional[str] = Query(
        None, description="Slack channel ID (optional, uses config default)"
    ),
    from_datetime: Optional[datetime] = Query(
        None, description="Start datetime for message range (ISO format)"
    ),
    to_datetime: Optional[datetime] = Query(
        None, description="End datetime for message range (ISO format)"
    ),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum messages to fetch (max 100)"
    ),
):
    """
    Use case 1: Update KB from Slack messages.

    Pipeline:
    1. Fetch Slack messages in time range (with thread expansion)
    2. Mask PII data
    3. Extract KB using AI
    4. Match against existing KB
    5. Generate KB document
    6. Create GitHub PR

    Examples:
    - GET /api/kb/from-slack?limit=50
    - GET /api/kb/from-slack?from_datetime=2026-01-01T00:00:00Z&to_datetime=2026-01-05T23:59:59Z
    - GET /api/kb/from-slack?channel_id=C123ABC456&limit=100
    """
    try:
        logger.info(
            f"KB from Slack request: channel_id={channel_id}, "
            f"from={from_datetime}, to={to_datetime}, limit={limit}"
        )

        result = await orchestrator.process_slack_messages(
            channel_id=channel_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            limit=limit,
        )

        return result

    except Exception as e:
        logger.error(f"Error in KB from Slack endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Slack messages: {str(e)}",
        )


@router.post("/from-text", response_model=KBProcessingResponse)
async def kb_from_text(request: TextKBRequest):
    """
    Use case 2: Update KB from free text.

    Pipeline:
    1. Convert text to standardized conversation format
    2. Mask PII data
    3. Extract KB using AI
    4. Match against existing KB
    5. Generate KB document
    6. Create GitHub PR

    Example request body:
    ```json
    {
        "text": "We had an issue with API timeout errors. The solution was to increase the connection timeout from 30s to 60s in the config file.",
        "title": "API Timeout Fix",
        "metadata": {
            "source": "manual",
            "author": "user123"
        }
    }
    ```
    """
    try:
        logger.info(f"KB from text request: text_length={len(request.text)}")

        result = await orchestrator.process_text_input(
            text=request.text,
            title=request.title,
            metadata=request.metadata,
        )

        return result

    except Exception as e:
        logger.error(f"Error in KB from text endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process text input: {str(e)}",
        )


@router.post("/query", response_model=KBQueryResponse)
async def kb_query(request: KBQueryRequest):
    """
    Use case 3: Question and Answer (QnA) from the knowledge base.

    Pipeline:
    1. Parse and understand the user's question
    2. Search KB repository using LLM-based relevance assessment
    3. Generate natural language answer with inline citations
    4. Return formatted response with sources section

    Example request body:
    ```json
    {
        "query": "How do I fix API timeout errors?",
    }
    ```

    Example response:
    ```json
    {
        "status": "success",
        "query": "How do I fix API timeout errors?",
        "answer": "Based on the knowledge base, API timeout errors can be resolved by increasing the connection timeout from 30s to 60s in the config file. According to the API Timeout Resolution document, this change should be made in the `config.json` file under the `api.timeout` setting.\n\nSources: [API Timeout Resolution]",
        "sources": [
            {
                "title": "API Timeout Resolution",
                "category": "troubleshooting",
                "excerpt": "To fix API timeout errors, increase the connection timeout...",
                "relevance_score": 0.95,
                "file_path": "troubleshooting/api-timeout.md",
                "github_url": "https://github.com/.../troubleshooting/api-timeout.md"
            }
        ],
        "total_sources": 1
    }
    ```
    """
    try:
        logger.info(
            f"KB query request: query='{request.query}', "
            f"history={len(request.conversation_history) if request.conversation_history else 0} messages"
        )

        result = await orchestrator.query_knowledge_base(
            query=request.query,
            conversation_history=request.conversation_history
        )

        return result

    except Exception as e:
        logger.error(f"Error in KB query endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query knowledge base: {str(e)}",
        )
