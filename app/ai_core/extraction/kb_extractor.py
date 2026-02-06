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

from app.models.thread import StandardizedThread
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
    Extracts knowledge from Slack threads using a 3-step process.
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
        thread: StandardizedThread,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[KnowledgeArticle]:
        """
        Extract knowledge from a standardized thread using 3-step process.

        Args:
            thread: The standardized thread to extract knowledge from
            context: Optional additional context (e.g., related code, documentation)

        Returns:
            KnowledgeArticle if extraction successful, None otherwise
        """
        try:
            logger.info(f"Starting KB extraction for thread {thread.id}")

            # Validate thread has sufficient content
            if not self._is_thread_extractable(thread):
                logger.warning(f"Thread {thread.id} not suitable for extraction")
                return None

            # Step 1: Classify category
            category = await self._classify_category(thread)
            if not category:
                logger.warning(f"Could not classify category for thread {thread.id}")
                return None

            logger.info(f"Classified thread {thread.id} as: {category}")

            # Step 2: Extract with category-specific model
            extraction_output = await self._extract_with_model(
                thread, category, context
            )
            if not extraction_output:
                logger.warning(f"Extraction failed for thread {thread.id}")
                return None

            logger.info(f"Successfully extracted: {extraction_output.title}")

            # Step 3: Build complete KnowledgeArticle with metadata
            metadata = ExtractionMetadata(
                source_type=thread.source.value,
                source_id=thread.id,
                channel_id=thread.channel_id,
                channel_name=thread.channel_name or "unknown",
                participants=[msg.author_id for msg in thread.messages],
                message_count=len(thread.messages),
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
        self, thread: StandardizedThread
    ) -> Optional[KBCategory]:
        """
        Step 1: Classify the thread into a category.

        Args:
            thread: The thread to classify

        Returns:
            KBCategory if successful, None otherwise
        """
        try:
            thread_content = self._format_thread_for_extraction(thread)

            prompt = CATEGORY_CLASSIFICATION_PROMPT.format(
                thread_content=thread_content
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
        thread: StandardizedThread,
        category: KBCategory,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[KnowledgeExtractionOutput]:
        """
        Step 2: Extract knowledge using the appropriate category-specific model.

        Args:
            thread: The thread to extract from
            category: The classified category
            context: Optional additional context

        Returns:
            Category-specific extraction output if successful
        """
        try:
            thread_content = self._format_thread_for_extraction(thread)
            context_str = self._format_context(context) if context else ""

            user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                category=category.value,
                thread_content=thread_content,
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

    def _is_thread_extractable(self, thread: StandardizedThread) -> bool:
        """
        Check if thread has sufficient content for extraction.

        Args:
            thread: The thread to validate

        Returns:
            True if thread is suitable for extraction
        """
        # Must have messages
        if not thread.messages or len(thread.messages) == 0:
            logger.debug(f"Thread {thread.id} has no messages")
            return False

        # Calculate total content length
        total_content = sum(len(msg.content) for msg in thread.messages)

        # Must have meaningful discussion (at least 100 chars)
        if total_content < 100:
            logger.debug(
                f"Thread {thread.id} has insufficient content ({total_content} chars)"
            )
            return False

        # Must have at least 2 messages for a discussion
        if len(thread.messages) < 2:
            logger.debug(f"Thread {thread.id} has less than 2 messages")
            return False

        return True

    def _format_thread_for_extraction(self, thread: StandardizedThread) -> str:
        """
        Format thread messages for the extraction prompt.

        Args:
            thread: The standardized thread

        Returns:
            Formatted thread content
        """
        channel_name = thread.channel_name or "unknown-channel"
        formatted = f"### Thread from #{channel_name}\n\n"

        for msg in thread.messages:
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
        threads: List[StandardizedThread],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeArticle]:
        """
        Extract knowledge from multiple threads.

        Args:
            threads: List of threads to process
            context: Optional shared context

        Returns:
            List of extracted knowledge articles
        """
        articles = []

        for thread in threads:
            article = await self.extract_knowledge(thread, context)
            if article:
                articles.append(article)

        logger.info(
            f"Batch extraction complete: {len(articles)}/{len(threads)} successful"
        )
        return articles
