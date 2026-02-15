"""
PII Masking Module
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Leverage SAP GenAI SDK Orchestration V2 + Data Masking
- Mask personal information (names, emails, phone numbers, addresses)
- Process standardized conversations with parallel batch processing
"""

import logging
import asyncio
from typing import List, Dict, Any
from copy import deepcopy

from gen_ai_hub.orchestration_v2.service import OrchestrationService
from gen_ai_hub.orchestration_v2.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration_v2.models.template import (
    Template,
    PromptTemplatingModuleConfig,
)
from gen_ai_hub.orchestration_v2.models.llm_model_details import LLMModelDetails
from gen_ai_hub.orchestration_v2.models.config import ModuleConfig, OrchestrationConfig
from gen_ai_hub.orchestration_v2.models.data_masking import (
    MaskingModuleConfig,
    MaskingProviderConfig,
    MaskingMethod,
    DPIStandardEntity,
    DPICustomEntity,
    DPIMethodConstant,
    ProfileEntity,
)

from app.models.thread import StandardizedConversation, StandardizedMessage
from app.config import get_settings

logger = logging.getLogger(__name__)


class MaskingError(Exception):
    """Raised when PII masking fails - stops entire pipeline."""

    pass


class PIIMasker:
    """
    PII (Personally Identifiable Information) Masker.

    Uses SAP GenAI SDK Orchestration V2 with Data Masking for compliance.
    Processes StandardizedConversation objects with parallel batch processing.
    """

    def __init__(self):
        """Initialize PIIMasker with SAP GenAI Orchestration service."""
        self.settings = get_settings()

        # Initialize Orchestration Service
        try:
            self.orchestration_service = OrchestrationService()
            logger.info("PIIMasker initialized with Orchestration V2")
        except Exception as e:
            logger.error(f"Failed to initialize Orchestration service: {e}")
            raise MaskingError(f"Orchestration service initialization failed: {e}")

    def _create_masking_config(self) -> MaskingModuleConfig:
        """
        Create Data Masking configuration.

        Configured entities:
        - PERSON: Names of individuals
        - EMAIL: Email addresses
        - PHONE: Phone numbers
        - ADDRESS: Physical addresses
        - I_NUMBER: Custom entity for personal IDs (I/D/C followed by digits, e.g., i123456, D123456, C987654)
        - SLACK_USER: Slack user IDs (e.g., U1234567890, U0ACPTBU04R, W1234567890)
        """
        return MaskingModuleConfig(
            masking_providers=[
                MaskingProviderConfig(
                    method=MaskingMethod.ANONYMIZATION,
                    entities=[
                        # Standard entities
                        DPIStandardEntity(type=ProfileEntity.PERSON),
                        DPIStandardEntity(type=ProfileEntity.EMAIL),
                        DPIStandardEntity(type=ProfileEntity.PHONE),
                        DPIStandardEntity(type=ProfileEntity.ADDRESS),
                        # Custom entity for personal IDs starting with I/D/C
                        DPICustomEntity(
                            regex=r"\b[IDCidc]\d{6,6}\b",
                            replacement_strategy=DPIMethodConstant(
                                method="constant", value="MASKED_I_NUMBER"
                            ),
                        ),
                        # Custom entity for local phone numbers (e.g., 123-4567)
                        DPICustomEntity(
                            regex=r"\b\d{3}-\d{4}\b",
                            replacement_strategy=DPIMethodConstant(
                                method="constant", value="MASKED_LOCAL_PHONE"
                            ),
                        ),
                        # Custom entity for Slack user IDs (e.g., U0ACPTBU04R, U1234567890, W1234567890)
                        # Pattern: U or W followed by 8-11 alphanumeric characters
                        DPICustomEntity(
                            regex=r"\b[UW][A-Z0-9]{8,11}\b",
                            replacement_strategy=DPIMethodConstant(
                                method="constant", value="MASKED_SLACK_USER"
                            ),
                        ),
                    ],
                )
            ],
        )

    def _create_orchestration_config(self, text: str) -> OrchestrationConfig:
        """Create orchestration configuration with DPI masking."""

        # Create template for the masking request
        template = Template(
            template=[
                SystemMessage(
                    content="You are a text processor. Return the input text exactly as provided, preserving all line breaks and formatting."
                ),
                UserMessage(content="{{?input}}"),
            ]
        )

        # Create LLM model details
        llm = LLMModelDetails(
            name="gpt-4o-mini",
            params={"temperature": 0.0},
        )

        # Create prompt templating config
        prompt_template = PromptTemplatingModuleConfig(prompt=template, model=llm)

        # Create module config with prompt templating and masking
        module_config = ModuleConfig(
            prompt_templating=prompt_template,
            masking=self._create_masking_config(),
        )

        # Create orchestration config
        config = OrchestrationConfig(modules=module_config)

        return config

    async def mask_conversations(
        self, conversations: List[StandardizedConversation]
    ) -> List[StandardizedConversation]:
        """
        Mask PII in a batch of standardized conversations using parallel processing.

        This method:
        1. Processes each message individually to avoid delimiter issues
        2. Updates author_name to masked identifiers (USER_1, USER_2, etc.)
        3. Uses asyncio.gather() for parallel processing of all messages
        4. Uses SAP GenAI Orchestration V2 for masking content
        5. Fails entire pipeline on any error (strict mode)

        Masked entities:
        - Personal names (e.g., "John Doe" -> "MASKED_PERSON")
        - Email addresses (e.g., "john@example.com" -> "MASKED_EMAIL")
        - Phone numbers (e.g., "+1-555-0100" -> "MASKED_PHONE_NUMBER")
        - Addresses (e.g., "123 Main St" -> "MASKED_ADDRESS")
        - Personal IDs (e.g., "D123456" -> "MASKED_I_NUMBER")
        - Slack user IDs (e.g., "U0ABCDEF04R" -> "MASKED_SLACK_USER")
        Args:
            conversations: List of StandardizedConversation objects to mask

        Returns:
            List[StandardizedConversation] with masked content and author_name updated

        Raises:
            MaskingError: If masking fails for any conversation
        """
        if not conversations:
            logger.info("No conversations to mask")
            return []

        logger.info(f"Starting PII masking for {len(conversations)} conversations")

        try:
            # Create deep copy to avoid modifying original
            masked_conversations = deepcopy(conversations)

            # Create tasks for parallel processing of all messages across all conversations
            tasks = []
            for conversation in masked_conversations:
                for message in conversation.messages:
                    tasks.append(self._mask_single_message(message))

            # Process all messages in parallel using asyncio.gather
            logger.info(f"Processing {len(tasks)} messages in parallel...")
            await asyncio.gather(*tasks)

            # Update masked flags and author names
            for conversation in masked_conversations:
                # Build author mapping for this conversation
                author_map = {}
                next_user_num = 1

                for message in conversation.messages:
                    # Create masked author name if not already mapped
                    if message.author_id not in author_map:
                        author_map[message.author_id] = f"USER_{next_user_num}"
                        next_user_num += 1

                    # Update author_name with masked identifier
                    message.author_name = author_map[message.author_id]
                    message.is_masked = True

            total_messages = sum(len(c.messages) for c in masked_conversations)
            logger.info(
                f"Successfully masked {len(conversations)} conversations ({total_messages} messages)"
            )
            return masked_conversations

        except Exception as e:
            error_msg = f"PII masking failed: {str(e)}"
            logger.error(error_msg)
            raise MaskingError(error_msg) from e

    async def _mask_single_message(self, message: StandardizedMessage) -> None:
        """
        Mask a single message using Orchestration V2.

        Args:
            message: StandardizedMessage to mask (modified in place)

        Raises:
            MaskingError: If masking fails for the message
        """
        try:
            # Create orchestration config
            config = self._create_orchestration_config(message.content)

            # Call orchestration service
            result = await asyncio.to_thread(
                self.orchestration_service.run,
                config=config,
                placeholder_values={"input": message.content},
            )

            # Extract and update masked content
            if result and hasattr(result, "final_result"):
                message.content = self._extract_masked_content(result).strip()
            else:
                raise MaskingError(
                    f"Invalid response from orchestration service for message {message.id}"
                )

        except Exception as e:
            error_msg = f"Message masking failed for {message.id}: {str(e)}"
            logger.error(error_msg)
            raise MaskingError(error_msg) from e

    def _extract_masked_content(self, result: Any) -> str:
        """
        Extract masked content from orchestration result.

        Args:
            result: Orchestration service result

        Returns:
            Masked content string

        Raises:
            MaskingError: If content cannot be extracted
        """
        try:
            # Extract from final_result
            if hasattr(result, "final_result") and result.final_result:
                if (
                    hasattr(result.final_result, "choices")
                    and result.final_result.choices
                ):
                    choice = result.final_result.choices[0]
                    if hasattr(choice, "message") and hasattr(
                        choice.message, "content"
                    ):
                        return choice.message.content

            raise MaskingError("Could not extract content from orchestration result")

        except Exception as e:
            raise MaskingError(f"Failed to extract masked content: {e}") from e

    async def get_masking_stats(
        self, conversations: List[StandardizedConversation]
    ) -> Dict[str, Any]:
        """
        Get statistics about masking requirements (without actually masking).

        Useful for pre-flight checks and reporting.

        Args:
            conversations: Conversations to analyze

        Returns:
            Dictionary with statistics
        """
        total_messages = sum(
            len(conversation.messages) for conversation in conversations
        )
        total_chars = sum(
            len(msg.content)
            for conversation in conversations
            for msg in conversation.messages
        )

        # With parallel processing, time ≈ max of all threads (not sum)
        estimated_time = self.settings.orchestration_timeout

        return {
            "total_conversations": len(conversations),
            "total_messages": total_messages,
            "total_characters": total_chars,
            "estimated_api_calls": total_messages,  # One call per message
            "estimated_time_seconds": estimated_time,  # Parallel processing
            "entities_masked": [
                "PERSON",
                "EMAIL",
                "PHONE",
                "ADDRESS",
                "I_NUMBER",
                "SLACK_USER",
            ],
            "masking_method": "anonymization",
        }
