"""
Knowledge Base Extraction Module

This module handles the extraction of knowledge from Slack threads into structured KB documents.
It uses a 3-step process:
1. Classify the conversation category (troubleshooting, process, or decision)
2. Extract structured data using category-specific models
3. Create KBDocument with extraction output and metadata
"""

import logging
from typing import Optional, Dict, Any, List
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.thread import StandardizedConversation, SourceType
from app.models.knowledge import (
    KBDocument,
    KBCategory,
    KnowledgeExtractionOutput,
    TroubleshootingExtraction,
    ProcessExtraction,
    DecisionExtraction,
    ReferenceExtraction,
    GeneralExtraction,
    ExtractionMetadata,
)
from app.ai_core.prompts.extraction import (
    CATEGORY_CLASSIFICATION_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
config = get_settings()


# Custom Exceptions


class CategoryClassificationError(Exception):
    """
    Raised when category classification fails.
    This is a system error (500) - the LLM failed to classify the conversation.
    """

    pass


class KBExtractionError(Exception):
    """
    Raised when KB extraction fails.
    This is a system error (500) - the LLM failed to extract structured data.
    """

    pass


class KBExtractor:
    """
    Extracts knowledge from Slack conversations using a 3-step process.
    """

    def __init__(self):
        """
        Initialize the KB Extractor using SAP gen_ai_hub SDK.
        """
        # Initialize proxy client for gen_ai_hub
        self.proxy_client = get_proxy_client("gen-ai-hub")

        # Initialize ChatOpenAI with gen_ai_hub proxy
        self.llm = ChatOpenAI(
            proxy_model_name=config.openai_model,
            proxy_client=self.proxy_client,
            temperature=config.temperature,
        )

        self.model = config.openai_model
        self.temperature = config.temperature

    async def extract_knowledge(
        self,
        conversation: StandardizedConversation,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[KBDocument]:
        """
        Extract knowledge from a standardized conversation using 3-step process.

        Args:
            conversation: The standardized conversation to extract knowledge from
            context: Optional additional context (e.g., related code, documentation)

        Returns:
            KBDocument if extraction successful,
            None if conversation has no sufficient content

        Raises:
            CategoryClassificationError: If LLM fails to classify the conversation
            KBExtractionError: If LLM fails to extract structured KB data
        """
        logger.info(f"Starting KB extraction for conversation {conversation.id}")

        # Validate conversation has sufficient content
        if not self._is_conversation_extractable(conversation):
            logger.info(
                f"Conversation {conversation.id} not suitable for extraction: "
                f"insufficient content or too few messages"
            )
            return None

        # Step 1: Classify category (raises CategoryClassificationError on failure)
        category = await self._classify_category(conversation)
        logger.info(f"Classified conversation {conversation.id} as: {category}")

        # Step 2: Extract with category-specific model (raises KBExtractionError on failure)
        extraction_output = await self._extract_with_model(
            conversation, category, context
        )
        logger.info(f"Successfully extracted: {extraction_output.title}")

        # Step 3: Build complete KBDocument with metadata
        metadata = ExtractionMetadata(
            source_type=conversation.source.type.value,
            source_id=conversation.id,
            channel_id=conversation.source.channel_id,
            channel_name=conversation.source.channel_name or "unknown",
            history_from=conversation.source.history_from,
            history_to=conversation.source.history_to,
            message_limit=conversation.source.message_limit,
            participants=[msg.author_id for msg in conversation.messages],
            message_count=len(conversation.messages),
        )

        kb_document = KBDocument(
            extraction_output=extraction_output,
            category=category,
            extraction_metadata=metadata,
        )

        logger.info(
            f"Successfully created KB document: {kb_document.title} "
            f"(confidence: {kb_document.ai_confidence:.2f})"
        )
        return kb_document

    async def _classify_category(
        self, conversation: StandardizedConversation
    ) -> KBCategory:
        """
        Step 1: Classify the conversation into a category.

        Args:
            conversation: The conversation to classify

        Returns:
            KBCategory if successful

        Raises:
            CategoryClassificationError: If classification fails
        """
        try:
            conversation_content = self._format_conversation_for_extraction(
                conversation
            )

            prompt = CATEGORY_CLASSIFICATION_PROMPT.format(
                conversation_content=conversation_content
            )

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)

            category_str = response.content.strip().lower()

            # Map to enum (handle both singular and plural for backward compatibility)
            category_map = {
                "troubleshooting": KBCategory.TROUBLESHOOTING,
                "process": KBCategory.PROCESSES,  # Backward compatibility
                "processes": KBCategory.PROCESSES,
                "decision": KBCategory.DECISIONS,  # Backward compatibility
                "decisions": KBCategory.DECISIONS,
                "reference": KBCategory.REFERENCES,  # Backward compatibility
                "references": KBCategory.REFERENCES,
                "general": KBCategory.GENERAL,
            }

            category = category_map.get(category_str)
            if not category:
                raise CategoryClassificationError(
                    f"LLM returned invalid category: '{category_str}'. "
                    f"Expected one of: troubleshooting, process, decision, reference, general"
                )

            return category

        except CategoryClassificationError:
            # Re-raise custom exception
            raise
        except Exception as e:
            logger.error(f"Error classifying category: {str(e)}", exc_info=True)
            raise CategoryClassificationError(
                f"Failed to classify conversation category: {str(e)}"
            ) from e

    async def _extract_with_model(
        self,
        conversation: StandardizedConversation,
        category: KBCategory,
        context: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeExtractionOutput:
        """
        Step 2: Extract knowledge using the appropriate category-specific model.

        Args:
            conversation: The conversation to extract from
            category: The classified category
            context: Optional additional context

        Returns:
            Category-specific extraction output if successful

        Raises:
            KBExtractionError: If extraction fails
        """
        try:
            conversation_content = self._format_conversation_for_extraction(
                conversation
            )
            context_str = self._format_context(context) if context else ""

            user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                category=category.value,
                conversation_content=conversation_content,
                additional_context=context_str,
            )

            messages = [
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            # Use appropriate model based on category
            if category == KBCategory.TROUBLESHOOTING:
                structured_llm = self.llm.with_structured_output(
                    TroubleshootingExtraction
                )
            elif category == KBCategory.PROCESSES:
                structured_llm = self.llm.with_structured_output(ProcessExtraction)
            elif category == KBCategory.DECISIONS:
                structured_llm = self.llm.with_structured_output(DecisionExtraction)
            elif category == KBCategory.REFERENCES:
                structured_llm = self.llm.with_structured_output(ReferenceExtraction)
            elif category == KBCategory.GENERAL:
                structured_llm = self.llm.with_structured_output(GeneralExtraction)
            else:
                raise KBExtractionError(f"Unknown category: {category}")

            extraction_output = await structured_llm.ainvoke(messages)

            if not extraction_output:
                raise KBExtractionError(
                    f"LLM returned empty extraction output for category {category.value}"
                )

            return extraction_output

        except KBExtractionError:
            # Re-raise custom exception
            raise
        except Exception as e:
            logger.error(f"Error extracting with model: {str(e)}", exc_info=True)
            raise KBExtractionError(
                f"Failed to extract KB from conversation: {str(e)}"
            ) from e

    def _is_conversation_extractable(
        self, conversation: StandardizedConversation
    ) -> bool:
        """
        Check if conversation has sufficient content for extraction.

        Args:
            conversation: The conversation to validate

        Returns:
            True if conversation is suitable for extraction
        """
        # Must have messages
        if not conversation.messages or len(conversation.messages) == 0:
            logger.debug(f"Conversation {conversation.id} has no messages")
            return False

        # Calculate total content length
        total_content = sum(len(msg.content) for msg in conversation.messages)

        # Must have meaningful discussion (at least 100 chars)
        if total_content < 100:
            logger.debug(
                f"Conversation {conversation.id} has insufficient content ({total_content} chars)"
            )
            return False

        # Check if this is a text input conversation (single message is OK)
        is_text_input = conversation.source.type == SourceType.TEXT

        # Must have at least 2 messages for a discussion (unless it's text input)
        if not is_text_input and len(conversation.messages) < 2:
            logger.debug(f"Conversation {conversation.id} has less than 2 messages")
            return False

        return True

    def _format_conversation_for_extraction(
        self, conversation: StandardizedConversation
    ) -> str:
        """
        Format conversation messages for the extraction prompt.

        Args:
            conversation: The standardized conversation

        Returns:
            Formatted conversation content with idx and thread structure
        """
        channel_name = conversation.source.channel_name or "unknown-channel"
        formatted = f"### Conversation from #{channel_name}\n\n"

        for i, msg in enumerate(conversation.messages, 1):
            # Format timestamp (full datetime)
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Use author_name (already masked as USER_1, USER_2, etc.)
            user = msg.author_name or "Unknown User"

            # Format with sequential number, user, timestamp, idx, and content
            # i:3d since max 100 conversations could fetched
            formatted += (
                f"{i:3d}. [{user}] {timestamp} (idx:{msg.idx}): {msg.content}\n"
            )

            # Show thread structure if this is a reply
            if msg.parent_idx is not None:
                formatted += f"     └─ Reply to message index {msg.parent_idx}\n"

        return formatted

    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Format additional context for the extraction prompt.

        Args:
            context: Additional context dictionary

        Returns:
            Formatted context string
        """
        context_str = ""
        if "documentation" in context:
            context_str += "\n\n### Related Documentation:\n"
            context_str += context["documentation"]

        if "previous_kb" in context:
            context_str += "\n\n### Related KB Documents:\n"
            for kb in context["previous_kb"]:
                context_str += f"- {kb.get('title')}: {kb.get('summary')}\n"

        return context_str

    async def batch_extract(
        self,
        conversations: List[StandardizedConversation],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[KBDocument]:
        """
        Extract knowledge from multiple conversations.

        Args:
            conversations: List of conversations to process
            context: Optional shared context

        Returns:
            List of extracted knowledge documents
        """
        documents = []

        for conversation in conversations:
            document = await self.extract_knowledge(conversation, context)
            if document:
                documents.append(document)

        logger.info(
            f"Batch extraction complete: {len(documents)}/{len(conversations)} successful"
        )
        return documents
