"""
Knowledge Base Main API Routes

Main entrypoint with three use case endpoints:
1. GET /api/kb/from-slack - Update KB from Slack messages
2. POST /api/kb/from-text - Update KB from free text
3. POST /api/kb/query - Query knowledge base (Q&A)
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.services.kb_orchestrator import KBOrchestrator
from app.models.api_responses import (
    KBProcessingResponse,
    KBQueryResponse,
)

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


# API Endpoints


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
    Use case 3: Query knowledge base (Q&A).

    Pipeline:
    1. Parse and understand the query
    2. Search KB repository using LLM-based semantic search
    3. Rank and retrieve relevant documents
    4. Generate natural language answer
    5. Return formatted response with sources

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
        "answer": "Based on the knowledge base, API timeout errors can be resolved by...",
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
        logger.info(f"KB query request: query='{request.query}'")

        result = await orchestrator.query_knowledge_base(query=request.query)

        return result

    except Exception as e:
        logger.error(f"Error in KB query endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query knowledge base: {str(e)}",
        )
