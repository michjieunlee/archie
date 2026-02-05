"""
Slack API Client
Owner: ① Slack · GitHub Integration & Flow Owner

Responsibilities:
- conversations.history: Fetch channel messages
- conversations.replies: Fetch thread replies
- Thread expansion: Automatically detect and expand all threaded conversations
- Pure extraction focus - NO PII masking
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import get_settings
from app.integrations.slack.models import SlackThread, SlackMessage
from app.models.thread import StandardizedThread, StandardizedMessage, SourceType
from typing import List, Optional, Tuple
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for conversation extraction with thread expansion."""

    def __init__(self):
        settings = get_settings()
        self.client = WebClient(token=settings.slack_bot_token)
        self.settings = settings

    async def get_conversation_history_with_raw_data(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100
    ) -> Tuple[List[SlackMessage], List[dict]]:
        """
        Fetch conversation history and return both parsed messages and raw data.
        Raw data is needed for thread detection.

        Returns:
            Tuple of (SlackMessage list, raw message data list)
        """
        # Use configured channel if none provided
        if channel_id is None:
            channel_id = self.settings.slack_channel_id

        if not channel_id:
            raise ValueError("No channel_id provided and SLACK_CHANNEL_ID not configured")

        try:
            # Prepare API parameters
            api_params = {"channel": channel_id}

            # Use datetime range if provided, otherwise use limit
            if from_datetime or to_datetime:
                if from_datetime:
                    api_params["oldest"] = str(int(from_datetime.timestamp()))
                if to_datetime:
                    api_params["latest"] = str(int(to_datetime.timestamp()))
                logger.info(f"Fetching conversation history from channel {channel_id}, "
                           f"from={from_datetime}, to={to_datetime}")
            else:
                api_params["limit"] = limit
                logger.info(f"Fetching conversation history from channel {channel_id}, limit={limit}")

            # Call Slack API
            result = await asyncio.to_thread(
                self.client.conversations_history,
                **api_params
            )

            raw_messages = result.get("messages", [])
            parsed_messages = []

            for msg_data in raw_messages:
                message = self._parse_message(msg_data)
                if message:
                    parsed_messages.append(message)

            logger.info(f"Successfully fetched {len(parsed_messages)} messages")
            return parsed_messages, raw_messages

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            raise

    def _parse_message(self, msg_data: dict) -> Optional[SlackMessage]:
        """Parse Slack message data into SlackMessage object."""
        try:
            return SlackMessage(
                ts=msg_data["ts"],
                user_id=msg_data.get("user", "unknown"),
                user_name=None,  # Will be set by PII masker
                text=msg_data.get("text", ""),
                timestamp=datetime.fromtimestamp(float(msg_data["ts"])),
                reactions=msg_data.get("reactions", []),
                attachments=msg_data.get("attachments", [])
            )
        except Exception as e:
            logger.warning(f"Failed to parse message: {e}")
            return None

    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[SlackMessage]:
        """
        Fetch all replies in a thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp

        Returns:
            List of SlackMessage objects (including the parent message)
        """
        try:
            logger.debug(f"Fetching thread replies for {thread_ts}")

            result = await asyncio.to_thread(
                self.client.conversations_replies,
                channel=channel_id,
                ts=thread_ts
            )

            messages = []
            for msg_data in result.get("messages", []):
                message = self._parse_message(msg_data)
                if message:
                    messages.append(message)

            logger.debug(f"Fetched {len(messages)} messages from thread {thread_ts}")
            return messages

        except SlackApiError as e:
            logger.error(f"Slack API error fetching thread {thread_ts}: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Error fetching thread replies {thread_ts}: {e}")
            raise

    async def extract_conversations_with_threads(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100
    ) -> SlackThread:
        """
        Extract Slack conversations with complete thread expansion.

        This method:
        1. Fetches main channel messages (in reverse chronological order)
        2. Detects threaded messages (reply_count > 0)
        3. Fetches all thread replies (appended immediately after parent)
        4. Preserves thread context

        Returns:
            SlackThread with all messages including thread replies
        """
        try:
            logger.info("Starting conversation extraction with thread expansion...")

            # Step 1: Get main messages and raw data for thread detection
            main_messages, raw_messages = await self.get_conversation_history_with_raw_data(
                channel_id=channel_id,
                from_datetime=from_datetime,
                to_datetime=to_datetime,
                limit=limit
            )

            if not main_messages:
                logger.info("No messages found")
                # Return empty SlackThread
                actual_channel_id = channel_id or self.settings.slack_channel_id
                return SlackThread(
                    channel_id=actual_channel_id,
                    channel_name=None,
                    messages=[],
                    metadata={"threads_expanded": False}
                )

            actual_channel_id = channel_id or self.settings.slack_channel_id
            all_messages = []
            processed_threads = set()

            # Step 2: Process messages and detect threads
            for i, msg_data in enumerate(raw_messages):
                main_msg = main_messages[i]
                all_messages.append(main_msg)

                # Thread detection: check if message has replies
                reply_count = msg_data.get("reply_count", 0)
                thread_ts = msg_data.get("ts")

                if reply_count > 0 and thread_ts and thread_ts not in processed_threads:
                    logger.info(f"Found thread with {reply_count} replies: {thread_ts}")

                    # Step 3: Fetch thread replies
                    thread_messages = await self.get_thread_replies(actual_channel_id, thread_ts)

                    # Add replies (skip first message as it's the parent we already have)
                    if len(thread_messages) > 1:
                        thread_replies = thread_messages[1:]  # Skip parent message
                        all_messages.extend(thread_replies)
                        logger.info(f"Added {len(thread_replies)} thread replies")

                    processed_threads.add(thread_ts)

            logger.info(f"Extraction complete: {len(all_messages)} total messages "
                       f"({len(main_messages)} main + {len(all_messages) - len(main_messages)} replies)")

            # Create SlackThread from all messages
            slack_thread = SlackThread(
                channel_id=actual_channel_id,
                channel_name=None,  # Could be fetched if needed
                messages=all_messages,
                metadata={
                    "threads_expanded": True,
                    "total_messages": len(all_messages),
                    "main_messages": len(main_messages),
                    "thread_replies": len(all_messages) - len(main_messages)
                }
            )

            return slack_thread

        except Exception as e:
            logger.error(f"Error in extract_conversations_with_threads: {e}")
            raise

    def convert_to_standardized_thread(
        self,
        slack_thread: SlackThread
    ) -> StandardizedThread:
        """
        Convert SlackThread to StandardizedThread format.

        NOTE: This should be called AFTER PII masking so user_name is properly set.
        """
        if not slack_thread.messages:
            raise ValueError("Cannot create thread from empty SlackThread")

        # Convert SlackMessage to StandardizedMessage
        standardized_messages = []
        for slack_msg in slack_thread.messages:
            std_msg = StandardizedMessage(
                id=slack_msg.ts,
                author_id=slack_msg.user_id,
                author_name=slack_msg.user_name,  # Should be masked by now (USER_1, USER_2, etc.)
                content=slack_msg.text,
                timestamp=slack_msg.timestamp,
                is_masked=bool(slack_msg.user_name),  # True if PII masker set user_name
                metadata={
                    "reactions": slack_msg.reactions,
                    "attachments": slack_msg.attachments
                }
            )
            standardized_messages.append(std_msg)

        # Count unique participants
        unique_authors = set(msg.author_id for msg in standardized_messages)

        # Create thread ID from channel and first message timestamp
        thread_id = f"{slack_thread.channel_id}_{slack_thread.messages[0].ts}"

        # Create StandardizedThread
        thread = StandardizedThread(
            id=thread_id,
            source=SourceType.SLACK,
            source_url=f"https://slack.com/archives/{slack_thread.channel_id}",
            channel_id=slack_thread.channel_id,
            channel_name=slack_thread.channel_name,
            messages=standardized_messages,
            participant_count=len(unique_authors),
            created_at=standardized_messages[0].timestamp,
            last_activity_at=standardized_messages[-1].timestamp,
            metadata={
                "total_messages": len(standardized_messages),
                "threads_expanded": slack_thread.threads_expanded,
                "date_range": {
                    "from": standardized_messages[0].timestamp.isoformat(),
                    "to": standardized_messages[-1].timestamp.isoformat()
                }
            }
        )

        logger.info(f"Created StandardizedThread {thread_id} with {len(standardized_messages)} messages, "
                   f"{len(unique_authors)} participants")

        return thread