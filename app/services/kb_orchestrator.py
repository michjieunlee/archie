"""
Knowledge Base Orchestrator Service

Orchestrates the full KB creation pipeline for three main use cases:
1. Process Slack messages into KB
2. Process free text into KB
3. Query knowledge base (Q&A)
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from textwrap import dedent

from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain_core.messages import HumanMessage, SystemMessage
from app.ai_core.prompts.query import QNA_SYSTEM_PROMPT, create_qna_prompt

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
from app.models.thread import (
    StandardizedConversation,
    StandardizedMessage,
    Source,
    SourceType,
)
from app.models.api_responses import (
    KBProcessingResponse,
    KBQueryResponse,
    KBActionType,
    KBSearchSource,
)
from app.ai_core.matching.kb_matcher import MatchAction
from app.config import get_settings

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

        # Initialize LLM for KB summary generation
        config = get_settings()
        self.proxy_client = get_proxy_client("gen-ai-hub")
        self.llm = ChatOpenAI(
            proxy_model_name=config.openai_model,
            proxy_client=self.proxy_client,
            temperature=0.0,
        )

        # Lazy initialization of GitHub client (only when needed)
        # This prevents initialization errors when GitHub credentials are not configured
        self._github_client = None
        self._pr_manager = None

    @property
    def github_client(self):
        """Lazy initialization of GitHub client."""
        if self._github_client is None:
            self._github_client = GitHubClient()
        return self._github_client

    @property
    def pr_manager(self):
        """Lazy initialization of PR manager."""
        if self._pr_manager is None:
            self._pr_manager = PRManager(self.github_client)
        return self._pr_manager

    async def process_slack_messages(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100,
    ) -> KBProcessingResponse:
        """
        Use case 1: Process Slack messages into KB.

        Default values:
        - to_datetime: current datetime if not provided
        - from_datetime: None if not provided (kept empty)
        - limit: 100 if not provided (max)

        Args:
            channel_id: Slack channel ID (optional, uses config default)
            from_datetime: Start time for messages (optional, kept as None if not provided)
            to_datetime: End time for messages (optional, defaults to current datetime)
            limit: Maximum messages to fetch (max 100, default 100)

        Returns:
            KBProcessingResponse with processing results
        """
        try:
            logger.info("Starting Slack message processing pipeline")

            # Step 1: Fetch conversation from Slack
            # Default values applied inline:
            # - to_datetime: current datetime if not provided
            # - from_datetime: kept as None if not provided
            # - limit: capped at 100
            logger.info("Fetching Slack conversation...")
            conversation = await fetch_slack_conversation(
                channel_id=channel_id,
                from_datetime=from_datetime,
                to_datetime=to_datetime or datetime.now(),
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

    async def query_knowledge_base(self, query: str) -> KBQueryResponse:
        """
        Use case 3: Query knowledge base (Q&A).

        Pipeline:
        1. Parse and understand query
        2. Search KB repository
        3. Rank and retrieve relevant documents
        4. Generate natural language answer
        5. Return formatted response

        Args:
            query: User's question about the knowledge base

        Returns:
            KBQueryResponse with search results and answer
        """
        try:
            logger.info(f"Processing KB query: {query}")

            # 1. Fetch KB documents from GitHub
            try:
                all_kb_docs = await self.github_client.read_kb_repository()
                if not all_kb_docs:
                    return KBQueryResponse(
                        status="success",
                        query=query,
                        answer="The knowledge base is empty or could not be accessed.",
                        sources=[],
                        total_sources=0
                    )
                logger.info(f"Fetched {len(all_kb_docs)} KB documents")
            except Exception as e:
                logger.error(f"Failed to fetch KB documents: {e}")
                return KBQueryResponse(
                    status="error",
                    query=query,
                    reason=f"Failed to access knowledge base: {str(e)}"
                )

            # 2. Compute document relevance scores
            scored_docs = self._compute_document_relevance(query, all_kb_docs)

            # Pass more documents to LLM - let AI decide what's relevant
            MAX_DOCS = 30  # Increased to give LLM more context
            MIN_RELEVANCE = 0.1  # Lower threshold - let LLM filter

            # Filter documents by relevance score and limit
            relevant_docs = [doc for doc, score in scored_docs if score >= MIN_RELEVANCE][:MAX_DOCS]

            # If we still have no documents after filtering, just take top documents
            if not relevant_docs and all_kb_docs:
                relevant_docs = [doc for doc, score in scored_docs[:MAX_DOCS]]

            logger.info(f"Passing {len(relevant_docs)} documents to LLM from {len(all_kb_docs)} total")
            logger.info(f"Query: '{query}'")

            # Log top documents for debugging
            for i, (doc, score) in enumerate(scored_docs[:10], 1):
                title = doc.get('title', 'Untitled')
                path = doc.get('path', 'unknown')
                logger.info(f"Doc {i}: '{title}' [{path}] (score: {score:.2f})")

            # 3. Create prompt and generate answer
            # Create a dict of doc paths to scores for prompt enhancement
            doc_scores = {doc.get('path', ''): score for doc, score in scored_docs}

            # Very simple document preprocessing that doesn't do special processing
            # This just adds the full document text to the prompt, nothing more
            # Let the LLM handle the extraction rather than trying to pre-process
            for doc in relevant_docs:
                # We're intentionally not doing any special preprocessing
                # because that tends to make assumptions about information types
                pass

            # Create enhanced prompt with relevance scores
            prompt = create_qna_prompt(query, relevant_docs, doc_scores)
            messages = [
                SystemMessage(content=QNA_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]

            # 4. Generate answer with LLM
            response = await self.llm.ainvoke(messages)
            answer = response.content.strip()

            # 5. Extract cited sources from answer
            # Parse the answer to find which sources were actually cited
            cited_sources = []

            # Try to extract Sources section from the answer
            sources_pattern = r'Sources:\s*\[(.*?)\]'
            sources_match = re.search(sources_pattern, answer, re.IGNORECASE | re.DOTALL)

            if sources_match:
                # Extract sources list
                sources_text = sources_match.group(1)
                source_titles = [s.strip() for s in re.split(r'],\s*\[', sources_text)]
                source_titles = [s.replace(']', '').replace('[', '') for s in source_titles]
                cited_sources = source_titles

            # If no sources section found, check for inline citations
            if not cited_sources:
                inline_pattern = r'According to [""]?([^"",]*?)[""]?,'
                inline_matches = re.findall(inline_pattern, answer)
                cited_sources = inline_matches

            # If still no sources found, include all relevant docs
            if not cited_sources:
                cited_sources = [doc.get("title", "") for doc in relevant_docs]

            # Format sources for response, filtering to only include cited sources
            sources = []
            # Get scores dictionary for quick lookup
            doc_scores = {doc.get('path', ''): score for doc, score in scored_docs}

            for doc in relevant_docs:
                doc_title = doc.get("title", "")

                # Skip this document if it wasn't cited and we have citations
                if cited_sources and doc_title not in cited_sources:
                    # Try to check with some flexibility (exact match might be too strict)
                    if not any(doc_title in source or source in doc_title for source in cited_sources):
                        continue

                # Create GitHub URL for the document
                github_url = f"https://github.com/{self.github_client.repo.full_name}/blob/{self.github_client.default_branch}/{doc['path']}"

                # Get relevance score for this doc (default to 0.5 if not found)
                relevance_score = doc_scores.get(doc.get('path', ''), 0.5)

                # Extract a more meaningful excerpt by finding key sentences or specific information
                content = doc["content"]
                excerpt = content[:150] + "..." if len(content) > 150 else content

                # Determine if we're looking for specific information types
                is_url_query = any(term in query.lower() for term in ["url", "link", "website", "site", "github"])
                is_email_query = "email" in query.lower()
                is_value_query = any(term in query.lower() for term in ["value", "number", "id", "identifier"])

                # Extract specific information if the query is looking for it
                if is_url_query:
                    # Look for URLs in the content
                    urls = re.findall(r'https?://\S+', content)
                    if urls:
                        # Use the sentence containing the URL as excerpt
                        sentences = re.split(r'(?<=[.!?])\s+', content)
                        for sentence in sentences:
                            if any(url in sentence for url in urls):
                                excerpt = sentence
                                break

                # If not found by specific pattern, try query terms
                if len(excerpt) > 150:  # Only if we haven't found a specific excerpt yet
                    query_terms = query.lower().split()
                    if len(query_terms) >= 2:  # Only for multi-word queries
                        sentences = re.split(r'(?<=[.!?])\s+', content)
                        # Look for sentences with multiple query terms
                        for sentence in sentences:
                            sentence_lower = sentence.lower()
                            if sum(1 for term in query_terms if term in sentence_lower) >= 2:
                                excerpt = sentence
                                break

                source = KBSearchSource(
                    title=doc["title"],
                    category=doc["category"],
                    excerpt=excerpt,
                    relevance_score=relevance_score,
                    file_path=doc["path"],
                    github_url=github_url
                )
                sources.append(source)

            # 6. Return formatted response
            return KBQueryResponse(
                status="success",
                query=query,
                answer=answer,
                sources=sources,
                total_sources=len(sources)
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
            kb_document = await self.extractor.extract_knowledge(masked_conversation)

            if not kb_document:
                # Insufficient content - this is not an error, just not KB-worthy
                return KBProcessingResponse(
                    status="success",
                    action=KBActionType.IGNORE,
                    reason="Conversation has insufficient content for KB extraction. Try a longer time range or more messages.",
                    messages_fetched=messages_fetched,
                    text_length=text_length,
                )

            logger.info(f"Extracted KB document: {kb_document.title}")

        except CategoryClassificationError as e:
            # LLM failed to classify the conversation - system error (500)
            logger.error(f"Category classification failed: {str(e)}")
            raise

        except KBExtractionError as e:
            # LLM failed to extract structured KB data - system error (500)
            logger.error(f"KB extraction failed: {str(e)}")
            raise

        # Step 3: Match against existing KB
        logger.info("Matching against existing KB...")
        # Fetch existing KB documents from GitHub repository
        try:
            all_kb_docs = await self.github_client.read_kb_repository()
            # Filter by category for more focused matching
            existing_kb_docs = [
                doc
                for doc in all_kb_docs
                if doc.get("category") == kb_document.category.value
            ]
            logger.info(
                f"Fetched {len(all_kb_docs)} total KB documents from GitHub, "
                f"{len(existing_kb_docs)} in category '{kb_document.category.value}'"
            )
        except Exception as e:
            logger.warning(
                f"Failed to fetch existing KB documents from GitHub: {e}. Proceeding with empty list."
            )
            existing_kb_docs = []

        match_result = await self.matcher.match(kb_document, existing_kb_docs)
        logger.info(
            f"Match result: {match_result.action.value} (confidence: {match_result.confidence_score})"
        )

        # Step 4: Generate or update KB document
        if match_result.action == MatchAction.UPDATE:
            logger.info(
                f"UPDATE action: Attempting to update existing KB document at {match_result.document_path}"
            )

            # Fetch existing document content
            existing_doc = next(
                (
                    doc
                    for doc in existing_kb_docs
                    if doc.get("path") == match_result.document_path
                ),
                None,
            )

            if existing_doc and existing_doc.get("content"):
                try:
                    logger.info(
                        "Fetched existing document, using AI to merge updates..."
                    )
                    markdown_content = await self.generator.update_markdown(
                        existing_content=existing_doc["content"],
                        new_document=kb_document,
                    )
                    logger.info("Successfully updated document using AI merge")
                except Exception as e:
                    logger.warning(
                        f"AI update failed: {e}. Falling back to generate_markdown()"
                    )
                    markdown_content = self.generator.generate_markdown(kb_document)
            else:
                logger.warning(
                    f"Could not find existing document content for path: {match_result.document_path}. "
                    f"Falling back to generate_markdown()"
                )
                markdown_content = self.generator.generate_markdown(kb_document)
        else:
            logger.info(f"CREATE action: Generating new KB document")
            markdown_content = self.generator.generate_markdown(kb_document)

        kb_summary = self._generate_document_summary(markdown_content)

        # Step 5: Create GitHub PR
        config = get_settings()
        pr_url = None

        # Check if action requires PR creation (CREATE or UPDATE)
        if match_result.action == MatchAction.IGNORE:
            logger.info("Match result is IGNORE, skipping PR creation")
            response = KBProcessingResponse(
                status="success",
                action=KBActionType.IGNORE,
                reason=match_result.reasoning,
                kb_document_title=kb_document.title,
                kb_category=kb_document.category.value,
                kb_summary=kb_summary,
                ai_confidence=kb_document.ai_confidence,
                ai_reasoning=kb_document.ai_reasoning,
                pr_url=None,
                existing_document_url=match_result.existing_document_url,
                existing_document_title=match_result.document_title,
                messages_fetched=messages_fetched,
                text_length=text_length,
            )
            logger.debug("Returning response: %s", response)

            return response

        # Compute file path for both dry-run and actual PR creation
        file_path = match_result.document_path
        if not file_path:
            # Fallback: generate path from category and title
            sanitized_title = (
                kb_document.title.lower().replace(" ", "-").replace("/", "-")
            )
            file_path = f"{kb_document.category.value}/{sanitized_title}.md"
            logger.info(f"Generated file path: {file_path}")

        # Check dry_run mode
        if config.dry_run:
            logger.info("Dry-run mode enabled, skipping PR creation")
            self._print_extraction_summary(
                kb_document=kb_document,
                match_result=match_result,
                markdown_content=markdown_content,
                kb_summary=kb_summary,
            )
            return KBProcessingResponse(
                status="success",
                action=KBActionType(match_result.action.value),
                reason="Dry-run mode: PR creation skipped",
                kb_document_title=kb_document.title,
                kb_category=kb_document.category.value,
                kb_summary=kb_summary,
                ai_confidence=kb_document.ai_confidence,
                ai_reasoning=kb_document.ai_reasoning,
                pr_url=None,
                kb_markdown_content=markdown_content,
                kb_file_path=file_path,
                messages_fetched=messages_fetched,
                text_length=text_length,
            )

        # Create PR for CREATE or UPDATE actions
        logger.info(f"Creating GitHub PR for action: {match_result.action.value}")

        # Construct source URL from conversation metadata
        source_url = self._construct_source_url(conversation)

        # Build PR title with KB prefix and action indicator
        action_prefix = (
            "[UPDATE]" if match_result.action == MatchAction.UPDATE else "[NEW]"
        )
        pr_title = f"KB {action_prefix}: {kb_document.title}"

        # Create the PR
        pr_result = await self.pr_manager.create_pr(
            title=pr_title,
            content=markdown_content,
            file_path=file_path,
            summary=kb_summary,
            source_url=source_url,
            ai_confidence=kb_document.ai_confidence,
        )

        pr_url = pr_result.pr_url
        logger.info(f"Created PR: {pr_url}")

        return KBProcessingResponse(
            status="success",
            action=KBActionType(match_result.action.value),
            kb_document_title=kb_document.title,
            kb_category=kb_document.category.value,
            kb_summary=kb_summary,
            ai_confidence=kb_document.ai_confidence,
            ai_reasoning=kb_document.ai_reasoning,
            pr_url=pr_url,
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
            source=Source(
                type=SourceType.TEXT,
                channel_id="text_input",
                channel_name=title or "Text Input",
            ),
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

    def _generate_document_summary(self, markdown_content: str) -> str:
        """
        Generate a concise summary of the KB document using LLM.

        Args:
            markdown_content: The markdown content of the document

        Returns:
            A brief summary (2-3 sentences) of the document
        """
        try:
            prompt_template = dedent(
                """
                Generate a brief, user-friendly summary (2-3 sentences) of this knowledge base document.
                The summary should give readers a quick overview of what the document covers and its main purpose.

                ---

                {markdown_content}
                ---

                Provide only the summary text, without any preamble or additional formatting.
                """
            ).strip()

            prompt = prompt_template.format(markdown_content=markdown_content)
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)

            # Check if response has content
            if not response or not response.content:
                logger.error("LLM returned empty response for summary generation")
                return ""

            summary = response.content.strip()

            # Check if summary is actually empty after stripping
            if not summary:
                logger.error("LLM returned empty response for summary generation")
                return ""

            logger.info(
                f"Generated summary ({len(summary)} chars): {summary[:100]}..."
                if len(summary) > 100
                else f"Generated summary ({len(summary)} chars): {summary}"
            )

            return summary

        except Exception as e:
            logger.error(f"Error generating document summary: {str(e)}", exc_info=True)
            # Fallback to a simple summary
            return f"Unable to generate summary at this time. Error: {str(e)}"

    def _construct_source_url(
        self, conversation: StandardizedConversation
    ) -> Optional[str]:
        """
        Construct source URL from conversation metadata.

        For Slack conversations, constructs a Slack thread URL.
        For text input, returns None.

        Args:
            conversation: The conversation to get source URL for

        Returns:
            Source URL string or None if not applicable
        """
        # Check source type
        if conversation.source.type == SourceType.TEXT:
            return None

        if conversation.source.type == SourceType.SLACK:
            channel_id = conversation.source.channel_id
            if not channel_id:
                return None

            # Try to get the first message timestamp for thread URL
            thread_ts = None
            if conversation.messages:
                first_message = conversation.messages[0]
                # Get timestamp - either from message id or metadata
                if hasattr(first_message, "id") and first_message.id:
                    # Slack message IDs often contain the timestamp
                    thread_ts = first_message.id
                elif first_message.metadata and "ts" in first_message.metadata:
                    thread_ts = first_message.metadata["ts"]

            # Construct Slack URL
            # Format: https://slack.com/app_redirect?channel=CHANNEL_ID&message_ts=TIMESTAMP
            if thread_ts:
                return f"https://slack.com/app_redirect?channel={channel_id}&message_ts={thread_ts}"
            else:
                # Just link to the channel if no specific message
                return f"https://slack.com/app_redirect?channel={channel_id}"

        return None

    def _print_extraction_summary(
        self,
        kb_document,
        match_result,
        markdown_content: str,
        kb_summary: str,
    ) -> None:
        """
        Print a summary of the extraction results for dry-run mode.

        Args:
            kb_document: The extracted KB document
            match_result: The match result from the matcher
            markdown_content: The generated markdown content
            kb_summary: The generated summary
        """
        separator = "=" * 80

        print(f"\n{separator}")
        print("🔍 DRY-RUN MODE - KB EXTRACTION SUMMARY")
        print(separator)

        print(f"\n📋 DOCUMENT INFO:")
        print(f"   Title:      {kb_document.title}")
        print(f"   Category:   {kb_document.category.value}")
        print(f"   Tags:       {', '.join(kb_document.tags)}")
        print(f"   Confidence: {kb_document.ai_confidence:.1%}")

        print(f"\n🎯 MATCH RESULT:")
        print(f"   Action:     {match_result.action.value.upper()}")
        print(f"   Confidence: {match_result.confidence_score:.1%}")
        print(f"   File Path:  {match_result.document_path or 'Not specified'}")
        print(
            f"   Reasoning:  {match_result.reasoning[:200]}..."
            if len(match_result.reasoning) > 200
            else f"   Reasoning:  {match_result.reasoning}"
        )

        print(f"\n📝 SUMMARY:")
        print(f"   {kb_summary}")

        print(f"\n📄 GENERATED MARKDOWN PREVIEW:")
        print("-" * 40)
        preview = markdown_content[:500]
        if len(markdown_content) > 500:
            preview += "\n... [truncated]"
        print(preview)
        print(markdown_content)
        print("-" * 40)

        print(f"\n{separator}")
        print("💡 To create a PR, set DRY_RUN=false in your environment")
        print(separator)
        print()

    def _compute_document_relevance(self, query: str, documents: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        """
        Compute basic relevance scores for documents. Keep it simple - let LLM do detailed filtering.

        Args:
            query: User's question
            documents: List of KB documents

        Returns:
            List of (document, score) tuples sorted by relevance
        """
        query_lower = query.lower()

        # Extract keywords (remove common stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'in', 'to',
                      'for', 'of', 'with', 'how', 'what', 'when', 'where', 'why', 'do',
                      'can', 'could', 'would', 'should', 'will', 'shall', 'may', 'might',
                      'must', 'need', 'have', 'has', 'had', 'been', 'was', 'were', 'am',
                      'that', 'this', 'these', 'those', 'which', 'who', 'whom', 'whose'}
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        query_keywords = query_words - stop_words

        scored_docs = []

        for doc in documents:
            score = 0.0
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            category = doc.get("category", "").lower()
            tags = [tag.lower() for tag in doc.get("tags", [])]

            # Title matches
            title_words = set(re.findall(r'\b\w+\b', title))
            title_match_count = len(query_keywords.intersection(title_words))
            score += title_match_count * 0.5

            # Exact query in title (very high signal)
            if query_lower in title:
                score += 1.5

            # Full query phrase in content (high signal)
            if query_lower in content:
                score += 1.0

            # Multi-word phrases from query (e.g., "github onboarding")
            words = [w for w in query_lower.split() if w not in stop_words]
            if len(words) >= 2:
                # Check all 2-word combinations
                for i in range(len(words) - 1):
                    phrase = f"{words[i]} {words[i+1]}"
                    if phrase in content:
                        score += 0.5
                    if phrase in title:
                        score += 0.8

            # Individual keyword matches in content
            for keyword in query_keywords:
                if keyword in content:
                    score += 0.15

            # Category match
            if category in query_keywords:
                score += 0.3

            # Tag matches
            for tag in tags:
                if tag in query_keywords:
                    score += 0.25

            scored_docs.append((doc, score))

        # Sort by score descending
        return sorted(scored_docs, key=lambda x: x[1], reverse=True)
