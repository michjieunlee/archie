"""
Knowledge Base Extraction Module

This module handles the extraction of knowledge from Slack threads into structured KB articles.
It uses a 3-step process:
1. Classify the conversation category (troubleshooting, process, or decision)
2. Extract structured data using category-specific models
3. Create KnowledgeArticle with extraction output and metadata
"""

import logging
from typing import Optional, Dict, Any, List
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.thread import StandardizedConversation
from app.models.knowledge import (
    KnowledgeArticle,
    KBCategory,
    KnowledgeExtractionOutput,
    TroubleshootingExtraction,
    ProcessExtraction,
    DecisionExtraction,
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
            max_tokens=config.max_tokens,
        )

        self.model = config.openai_model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    async def extract_knowledge(
        self,
        conversation: StandardizedConversation,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[KnowledgeArticle]:
        """
        Extract knowledge from a standardized conversation using 3-step process.

        Args:
            conversation: The standardized conversation to extract knowledge from
            context: Optional additional context (e.g., related code, documentation)

        Returns:
            KnowledgeArticle if extraction successful, None otherwise
        """
        try:
            logger.info(f"Starting KB extraction for conversation {conversation.id}")

            # Validate conversation has sufficient content
            if not self._is_conversation_extractable(conversation):
                logger.warning(f"Conversation {conversation.id} not suitable for extraction")
                return None

            # Step 1: Classify category
            category = await self._classify_category(conversation)
            if not category:
                logger.warning(f"Could not classify category for conversation {conversation.id}")
                return None

            logger.info(f"Classified conversation {conversation.id} as: {category}")

            # Step 2: Extract with category-specific model
            extraction_output = await self._extract_with_model(
                conversation, category, context
            )
            if not extraction_output:
                logger.warning(f"Extraction failed for conversation {conversation.id}")
                return None

            logger.info(f"Successfully extracted: {extraction_output.title}")

            # Step 3: Build complete KnowledgeArticle with metadata
            metadata = ExtractionMetadata(
                source_type=conversation.source.value,
                source_id=conversation.id,
                channel_id=conversation.channel_id,
                channel_name=conversation.channel_name or "unknown",
                participants=[msg.author_id for msg in conversation.messages],
                message_count=len(conversation.messages),
            )

            knowledge_article = KnowledgeArticle(
                extraction_output=extraction_output,
                category=category,
                extraction_metadata=metadata,
            )

            logger.info(
                f"Successfully created KB article: {knowledge_article.title} "
                f"(confidence: {knowledge_article.ai_confidence:.2f})"
            )
            return knowledge_article

        except Exception as e:
            logger.error(f"Error during KB extraction: {str(e)}", exc_info=True)
            return None

    async def _classify_category(
        self, conversation: StandardizedConversation
    ) -> Optional[KBCategory]:
        """
        Step 1: Classify the conversation into a category.

        Args:
            conversation: The conversation to classify

        Returns:
            KBCategory if successful, None otherwise
        """
        try:
            conversation_content = self._format_conversation_for_extraction(conversation)

            prompt = CATEGORY_CLASSIFICATION_PROMPT.format(
                thread_content=conversation_content
            )

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)

            category_str = response.content.strip().lower()

            # Map to enum
            category_map = {
                "troubleshooting": KBCategory.TROUBLESHOOTING,
                "processes": KBCategory.PROCESSES,
                "process": KBCategory.PROCESSES,  # Handle singular
                "decisions": KBCategory.DECISIONS,
                "decision": KBCategory.DECISIONS,  # Handle singular
            }

            return category_map.get(category_str)

        except Exception as e:
            logger.error(f"Error classifying category: {str(e)}", exc_info=True)
            return None

    async def _extract_with_model(
        self,
        conversation: StandardizedConversation,
        category: KBCategory,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[KnowledgeExtractionOutput]:
        """
        Step 2: Extract knowledge using the appropriate category-specific model.

        Args:
            conversation: The conversation to extract from
            category: The classified category
            context: Optional additional context

        Returns:
            Category-specific extraction output if successful
        """
        try:
            conversation_content = self._format_conversation_for_extraction(conversation)
            context_str = self._format_context(context) if context else ""

            user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                category=category.value,
                thread_content=conversation_content,
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
            else:
                logger.error(f"Unknown category: {category}")
                return None

            extraction_output = await structured_llm.ainvoke(messages)

            return extraction_output

        except Exception as e:
            logger.error(f"Error extracting with model: {str(e)}", exc_info=True)
            return None

    def _is_conversation_extractable(self, conversation: StandardizedConversation) -> bool:
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

        # Must have at least 2 messages for a discussion
        if len(conversation.messages) < 2:
            logger.debug(f"Conversation {conversation.id} has less than 2 messages")
            return False

        return True

    def _format_conversation_for_extraction(self, conversation: StandardizedConversation) -> str:
        """
        Format conversation messages for the extraction prompt.

        Args:
            conversation: The standardized conversation

        Returns:
            Formatted conversation content
        """
        channel_name = conversation.channel_name or "unknown-channel"
        formatted = f"### Conversation from #{channel_name}\n\n"

        for msg in conversation.messages:
            # Format timestamp
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Format user
            user = msg.author_name or msg.author_id or "Unknown User"

            # Format message
            formatted += f"**{user}** ({timestamp}):\n{msg.content}\n\n"

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
            context_str += "\n\n### Related KB Articles:\n"
            for kb in context["previous_kb"]:
                context_str += f"- {kb.get('title')}: {kb.get('summary')}\n"

        return context_str

    async def batch_extract(
        self,
        conversations: List[StandardizedConversation],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeArticle]:
        """
        Extract knowledge from multiple conversations.

        Args:
            conversations: List of conversations to process
            context: Optional shared context

        Returns:
            List of extracted knowledge articles
        """
        articles = []

        for conversation in conversations:
            article = await self.extract_knowledge(conversation, context)
            if article:
                articles.append(article)

        logger.info(
            f"Batch extraction complete: {len(articles)}/{len(conversations)} successful"
        )
        return articles