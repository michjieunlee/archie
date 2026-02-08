"""
Slack API Client
Owner: ① Slack · GitHub Integration & Flow Owner

Responsibilities:
- conversations.history: Fetch channel messages
- conversations.replies: Fetch thread replies
- Thread expansion: Automatically detect and expand all threaded conversations
- Pure fetching focus - NO PII masking
- Returns StandardizedConversation directly
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import get_settings
from app.models.thread import StandardizedConversation, StandardizedMessage, SourceType
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for conversation fetching with thread expansion."""

    def __init__(self):
        settings = get_settings()
        self.client = WebClient(token=settings.slack_bot_token)
        self.settings = settings

    async def fetch_conversation_history_with_raw_data(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversation history and return raw message data.
        Raw data is needed for thread detection.

        Returns:
            List of raw message dictionaries from Slack API
        """
        # Use configured channel if none provided
        if channel_id is None:
            channel_id = self.settings.slack_channel_id

        if not channel_id:
            raise ValueError("No channel_id provided and SLACK_CHANNEL_ID not configured")

        try:
            # Prepare API parameters
            api_params = {"channel": channel_id}

            # Use datetime range if provided, otherwise use limit (max 100)
            if from_datetime or to_datetime:
                if from_datetime:
                    api_params["oldest"] = str(int(from_datetime.timestamp()))
                if to_datetime:
                    api_params["latest"] = str(int(to_datetime.timestamp()))
                logger.info(f"Fetching conversation history from channel {channel_id}, "
                           f"from={from_datetime}, to={to_datetime}")
            else:
                api_params["limit"] = min(limit, 100)  # Max 100 messages
                logger.info(f"Fetching conversation history from channel {channel_id}, limit={api_params['limit']}")

            # Call Slack API
            result = await asyncio.to_thread(
                self.client.conversations_history,
                **api_params
            )

            raw_messages = result.get("messages", [])
            logger.info(f"Successfully fetched {len(raw_messages)} messages")
            return raw_messages

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            raise

    def _parse_message_to_standardized(self, msg_data: dict, idx: int, parent_idx: Optional[int] = None) -> Optional[StandardizedMessage]:
        """Parse Slack message data into StandardizedMessage object."""
        try:
            return StandardizedMessage(
                idx=idx,
                parent_idx=parent_idx,
                id=msg_data["ts"],
                author_id=msg_data.get("user", "unknown"),
                author_name=None,  # Will be set by PII masker later
                content=msg_data.get("text", ""),
                timestamp=datetime.fromtimestamp(float(msg_data["ts"])),
                message_id=msg_data["ts"],  # Add required message_id field
                is_masked=False,  # Will be set by PII masker
                metadata={
                    "reactions": msg_data.get("reactions", []),
                    "attachments": msg_data.get("attachments", []),
                    "slack_ts": msg_data["ts"]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse message: {e}")
            return None

    async def fetch_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """
        Fetch all replies in a thread.

        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp

        Returns:
            List of raw message dictionaries (including the parent message)
        """
        try:
            logger.debug(f"Fetching thread replies for {thread_ts}")

            result = await asyncio.to_thread(
                self.client.conversations_replies,
                channel=channel_id,
                ts=thread_ts
            )

            raw_messages = result.get("messages", [])
            logger.debug(f"Fetched {len(raw_messages)} messages from thread {thread_ts}")
            return raw_messages

        except SlackApiError as e:
            logger.error(f"Slack API error fetching thread {thread_ts}: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Error fetching thread replies {thread_ts}: {e}")
            raise

    async def fetch_conversations_with_threads(
        self,
        channel_id: Optional[str] = None,
        from_datetime: Optional[datetime] = None,
        to_datetime: Optional[datetime] = None,
        limit: int = 100
    ) -> StandardizedConversation:
        """
        Fetch Slack conversations with complete thread expansion and return StandardizedConversation.

        This method:
        1. Fetches main channel messages (in reverse chronological order from Slack)
        2. Detects threaded messages (reply_count > 0)
        3. Fetches all thread replies and inserts them chronologically after parent
        4. Assigns global indexing (idx) and parent references (parent_idx)

        Returns:
            StandardizedConversation with chronologically ordered messages and global indexing
        """
        try:
            logger.info("Starting conversation fetching with thread expansion...")

            # Step 1: Get raw messages for thread detection
            raw_messages = await self.fetch_conversation_history_with_raw_data(
                channel_id=channel_id,
                from_datetime=from_datetime,
                to_datetime=to_datetime,
                limit=min(limit, 100)  # Max 100 messages
            )

            if not raw_messages:
                logger.info("No messages found")
                # Return empty StandardizedConversation
                actual_channel_id = channel_id or self.settings.slack_channel_id
                return StandardizedConversation(
                    id=f"slack_conversation_{actual_channel_id}_{int(datetime.now().timestamp())}",  # Add required id field
                    source=SourceType.SLACK,
                    source_url=f"https://slack.com/archives/{actual_channel_id}",
                    channel_id=actual_channel_id,
                    channel_name=None,
                    messages=[],
                    participant_count=0,
                    created_at=datetime.now(),
                    last_activity_at=datetime.now(),
                    metadata={"threads_expanded": False, "total_messages": 0}
                )

            actual_channel_id = channel_id or self.settings.slack_channel_id
            all_standardized_messages = []
            processed_threads = set()
            current_idx = 0

            # Step 2: Process messages in chronological order and detect threads
            # Note: Slack API returns messages in reverse chronological order, so we reverse
            for msg_data in reversed(raw_messages):
                # Parse main message
                main_msg = self._parse_message_to_standardized(msg_data, current_idx)
                if main_msg:
                    all_standardized_messages.append(main_msg)
                    main_msg_idx = current_idx
                    current_idx += 1

                    # Thread detection: check if message has replies
                    reply_count = msg_data.get("reply_count", 0)
                    thread_ts = msg_data.get("ts")

                    if reply_count > 0 and thread_ts and thread_ts not in processed_threads:
                        logger.info(f"Found thread with {reply_count} replies: {thread_ts}")

                        # Step 3: Fetch thread replies
                        thread_raw_messages = await self.fetch_thread_replies(actual_channel_id, thread_ts)

                        # Add replies (skip first message as it's the parent we already have)
                        if len(thread_raw_messages) > 1:
                            thread_replies_raw = thread_raw_messages[1:]  # Skip parent message

                            for reply_data in thread_replies_raw:
                                reply_msg = self._parse_message_to_standardized(
                                    reply_data,
                                    current_idx,
                                    parent_idx=main_msg_idx
                                )
                                if reply_msg:
                                    all_standardized_messages.append(reply_msg)
                                    current_idx += 1

                            logger.info(f"Added {len(thread_replies_raw)} thread replies")

                        processed_threads.add(thread_ts)

            # Step 4: Calculate conversation metadata
            if all_standardized_messages:
                unique_authors = set(msg.author_id for msg in all_standardized_messages)
                created_at = all_standardized_messages[0].timestamp
                last_activity_at = all_standardized_messages[-1].timestamp
                participant_count = len(unique_authors)
            else:
                unique_authors = set()
                created_at = datetime.now()
                last_activity_at = datetime.now()
                participant_count = 0

            # Step 5: Create StandardizedConversation
            conversation = StandardizedConversation(
                id=f"slack_conversation_{actual_channel_id}_{int(created_at.timestamp())}",  # Add required id field
                source=SourceType.SLACK,
                source_url=f"https://slack.com/archives/{actual_channel_id}",
                channel_id=actual_channel_id,
                channel_name=None,  # Could be fetched if needed
                messages=all_standardized_messages,
                participant_count=participant_count,
                created_at=created_at,
                last_activity_at=last_activity_at,
                metadata={
                    "threads_expanded": True,
                    "total_messages": len(all_standardized_messages),
                    "main_messages": len(raw_messages),
                    "thread_replies": len(all_standardized_messages) - len(raw_messages),
                    "date_range": {
                        "from": created_at.isoformat() if all_standardized_messages else None,
                        "to": last_activity_at.isoformat() if all_standardized_messages else None
                    }
                }
            )

            logger.info(f"Fetch complete: {len(all_standardized_messages)} total messages "
                       f"({len(raw_messages)} main + {len(all_standardized_messages) - len(raw_messages)} replies), "
                       f"{participant_count} participants")

            return conversation

        except Exception as e:
            logger.error(f"Error in fetch_conversations_with_threads: {e}")
            raise