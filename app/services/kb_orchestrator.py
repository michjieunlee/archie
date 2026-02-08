"""
Knowledge Base Orchestrator Service

Orchestrates the full KB creation pipeline for three main use cases:
1. Process Slack messages into KB
2. Process free text into KB
3. Query knowledge base (Q&A)
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.api.routes.slack import fetch_slack_conversation
from app.ai_core.masking import PIIMasker
from app.ai_core.extraction import KBExtractor
from app.ai_core.extraction.kb_extractor import (
    CategoryClassificationError,
    KBExtractionError,
)
from app.ai_core.matching import KBMatcher
from app.ai_core.generation import KBGenerator
from app.integrations.github import GitHubClient, PRManager
from app.models.thread import StandardizedConversation, StandardizedMessage, SourceType
from app.models.api_responses import (
    KBProcessingResponse,
    KBQueryResponse,
    KBActionType,
)

logger = logging.getLogger(__name__)


class KBOrchestrator:
    """
    Orchestrates the full KB creation pipeline for all use cases.
    """

    def __init__(self):
        """Initialize orchestrator with all required services."""
        self.masker = PIIMasker()
        self.extractor = KBExtractor()
        self.matcher = KBMatcher()
        self.generator = KBGenerator()
        self.github_client = GitHubClient()
        self.pr_manager = PRManager(self.github_client)

    async def process_slack_messages(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100,
    ) -> KBProcessingResponse:
        """
        Use case 1: Process Slack messages into KB.

        Args:
            channel_id: Slack channel ID (optional, uses config default)
            from_datetime: Start time for messages
            to_datetime: End time for messages
            limit: Maximum messages to fetch (max 100)

        Returns:
            KBProcessingResponse with processing results
        """
        try:
            logger.info("Starting Slack message processing pipeline")

            # Step 1: Fetch conversation from Slack
            logger.info("Fetching Slack conversation...")
            conversation = await fetch_slack_conversation(
                channel_id=channel_id,
                from_datetime=from_datetime,
                to_datetime=to_datetime,
                limit=min(limit, 100),
            )

            if not conversation or not conversation.messages:
                return KBProcessingResponse(
                    status="success",
                    action=KBActionType.IGNORE,
                    reason="No messages found in the specified range",
                    messages_fetched=0,
                )

            logger.info(f"Fetched {len(conversation.messages)} messages")

            # Step 2-6: Process the conversation (common pipeline)
            result = await self._process_standardized_conversation(
                conversation,
                messages_fetched=len(conversation.messages),
            )

            return result

        except Exception as e:
            logger.error(f"Error in Slack message processing: {str(e)}", exc_info=True)
            return KBProcessingResponse(
                status="error",
                action=KBActionType.ERROR,
                reason=str(e),
            )

    async def process_text_input(
        self,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KBProcessingResponse:
        """
        Use case 2: Process free text into KB.

        Args:
            text: Free text input to process
            title: Optional title for the conversation
            metadata: Optional metadata

        Returns:
            KBProcessingResponse with processing results
        """
        try:
            logger.info("Starting text input processing pipeline")

            # Step 1: Convert text to StandardizedConversation
            conversation = self._text_to_conversation(text, title, metadata)
            logger.info(f"Created conversation from text ({len(text)} chars)")

            # Step 2-6: Process the conversation (common pipeline)
            result = await self._process_standardized_conversation(
                conversation,
                text_length=len(text),
            )

            return result

        except Exception as e:
            logger.error(f"Error in text input processing: {str(e)}", exc_info=True)
            return KBProcessingResponse(
                status="error",
                action=KBActionType.ERROR,
                reason=str(e),
            )

    async def query_knowledge_base(
        self,
        query: str,
        max_results: int = 5,
    ) -> KBQueryResponse:
        """
        Use case 3: Query knowledge base (Q&A).

        Pipeline:
        1. Parse and understand query
        2. Search KB repository
        3. Rank and retrieve relevant articles
        4. Generate natural language answer
        5. Return formatted response

        Args:
            query: User's question
            max_results: Maximum number of results to return

        Returns:
            KBQueryResponse with search results and answer
        """
        try:
            logger.info(f"Processing KB query: {query}")

            # TODO: Implement KB search
            # For now, return placeholder response
            logger.warning("KB search not yet implemented")

            return KBQueryResponse(
                status="success",
                query=query,
                answer="Knowledge base search is not yet implemented. This feature is coming soon.",
                sources=[],
                total_sources=0,
            )

        except Exception as e:
            logger.error(f"Error in KB query: {str(e)}", exc_info=True)
            return KBQueryResponse(
                status="error",
                query=query,
                reason=str(e),
            )

    async def _process_standardized_conversation(
        self,
        conversation: StandardizedConversation,
        messages_fetched: Optional[int] = None,
        text_length: Optional[int] = None,
    ) -> KBProcessingResponse:
        """
        Common pipeline for processing StandardizedConversation into KB.

        This method is used by both process_slack_messages and process_text_input.

        Pipeline steps:
        1. Mask PII
        2. Extract KB
        3. Match against existing KB
        4. Generate KB document
        5. Create GitHub PR

        Args:
            conversation: StandardizedConversation to process
            messages_fetched: Number of messages fetched (for Slack)
            text_length: Length of text processed (for text input)

        Returns:
            KBProcessingResponse with processing results
        """
        # Step 1: Mask PII
        logger.info("Masking PII data...")
        masked_conversations = await self.masker.mask_conversations([conversation])
        masked_conversation = masked_conversations[
            0
        ]  # We only passed one, so we get one back
        logger.info("PII masking complete")

        # Step 2: Extract KB
        try:
            logger.info("Extracting knowledge...")
            kb_article = await self.extractor.extract_knowledge(masked_conversation)

            if not kb_article:
                # Insufficient content - this is not an error, just not KB-worthy
                return KBProcessingResponse(
                    status="success",
                    action=KBActionType.IGNORE,
                    reason="Conversation has insufficient content for KB extraction. Try a longer time range or more messages.",
                    messages_fetched=messages_fetched,
                    text_length=text_length,
                )

            logger.info(f"Extracted KB article: {kb_article.title}")

        except CategoryClassificationError as e:
            # LLM failed to classify the conversation - system error (500)
            logger.error(f"Category classification failed: {str(e)}")
            raise

        except KBExtractionError as e:
            # LLM failed to extract structured KB data - system error (500)
            logger.error(f"KB extraction failed: {str(e)}")
            raise

        # Step 3: Match against existing KB (TODO: implement)
        # For now, always create new
        logger.info("KB matching skipped (not yet implemented)")

        # Step 4: Generate KB document (TODO: implement full generation)
        logger.info("KB generation skipped (using extraction output)")

        # Step 5: Create GitHub PR (TODO: implement)
        logger.info("GitHub PR creation skipped (not yet implemented)")

        return KBProcessingResponse(
            status="success",
            action=KBActionType.CREATE,
            kb_article_title=kb_article.title,
            kb_category=kb_article.category.value,
            ai_confidence=kb_article.ai_confidence,
            ai_reasoning=kb_article.ai_reasoning,
            pr_url=None,  # TODO: add when PR creation is implemented
            file_path=None,  # TODO: add when generation is implemented
            messages_fetched=messages_fetched,
            text_length=text_length,
        )

    def _text_to_conversation(
        self,
        text: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StandardizedConversation:
        """
        Convert free text input to StandardizedConversation format.

        Args:
            text: Input text
            title: Optional title for the conversation
            metadata: Optional metadata

        Returns:
            StandardizedConversation object
        """
        now = datetime.now()

        # Create a single message from the text
        message = StandardizedMessage(
            idx=0,
            parent_idx=None,
            id="text_input_0",
            author_id="text_input_user",
            author_name=None,  # Will be set by masker
            content=text,
            timestamp=now,
            is_masked=False,
            metadata=metadata or {},
        )

        # Create conversation
        conversation = StandardizedConversation(
            id=f"text_input_{int(now.timestamp())}",
            source=SourceType.TEXT,
            source_url=None,
            channel_id="text_input",
            channel_name=title or "Text Input",
            messages=[message],
            participant_count=1,
            created_at=now,
            last_activity_at=now,
            metadata={
                "source": "text_input",
                "title": title,
                **(metadata or {}),
            },
        )

        return conversation
