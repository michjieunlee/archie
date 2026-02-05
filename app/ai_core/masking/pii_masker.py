"""
PII Masking Module
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Leverage SAP GenAI SDK Orchestration V2 + Data Masking
- Mask personal information (names, emails, phone numbers, addresses)
- Process standardized threads with parallel batch processing
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

from app.models.thread import StandardizedThread, StandardizedMessage
from app.config import get_settings

logger = logging.getLogger(__name__)


class MaskingError(Exception):
    """Raised when PII masking fails - stops entire pipeline."""

    pass


class PIIMasker:
    """
    PII (Personally Identifiable Information) Masker.

    Uses SAP GenAI SDK Orchestration V2 with Data Masking for compliance.
    Processes StandardizedThread objects with parallel batch processing.
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

        Excluded: ORG, LOCATION (to preserve technical context)
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
                                method="constant", value="I_NUMBER"
                            ),
                        ),
                    ],
                )
            ],
        )

    def _create_orchestration_config(self, combined_text: str) -> OrchestrationConfig:
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
            params={"max_tokens": 1000, "temperature": 0.0},
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

    async def mask_threads(
        self, threads: List[StandardizedThread]
    ) -> List[StandardizedThread]:
        """
        Mask PII in a batch of standardized threads using parallel processing.

        This method:
        1. Processes each thread's messages together as a batch
        2. Updates author_name to masked identifiers (USER_1, USER_2, etc.)
        3. Uses asyncio.gather() for parallel processing of multiple threads
        4. Uses SAP GenAI Orchestration V2 for masking content
        5. Fails entire pipeline on any error (strict mode)

        Masked entities:
        - Personal names (e.g., "John Doe" -> "USER_1")
        - Email addresses (e.g., "john@example.com" -> "EMAIL_1")
        - Phone numbers (e.g., "+1-555-0100" -> "PHONE_1")
        - Addresses (e.g., "123 Main St" -> "ADDRESS_1")
        - Personal IDs (e.g., "i538638" -> "PERSONAL_ID_1", "D123456" -> "PERSONAL_ID_2")

        Args:
            threads: List of StandardizedThread objects to mask

        Returns:
            List[StandardizedThread] with masked content and author_name updated

        Raises:
            MaskingError: If masking fails for any thread
        """
        if not threads:
            logger.info("No threads to mask")
            return []

        logger.info(f"Starting PII masking for {len(threads)} threads")

        try:
            # Create deep copy to avoid modifying original
            masked_threads = deepcopy(threads)

            # Create tasks for parallel processing of all threads
            tasks = []
            for thread_idx, thread in enumerate(masked_threads):
                logger.info(
                    f"Queuing thread {thread_idx + 1}/{len(masked_threads)}: {thread.id} ({len(thread.messages)} messages)"
                )
                tasks.append(self._mask_thread_messages(thread))

            # Process all threads in parallel using asyncio.gather
            # Note: Each await inside _mask_thread_messages() yields control to event loop
            # allowing all threads to process concurrently
            logger.info(f"Processing {len(tasks)} threads in parallel...")
            await asyncio.gather(*tasks)

            # Update masked flags and author names
            for thread in masked_threads:
                # Build author mapping for this thread
                author_map = {}
                next_user_num = 1

                for message in thread.messages:
                    # Create masked author name if not already mapped
                    if message.author_id not in author_map:
                        author_map[message.author_id] = f"USER_{next_user_num}"
                        next_user_num += 1

                    # Update author_name with masked identifier
                    message.author_name = author_map[message.author_id]
                    message.is_masked = True

            total_messages = sum(len(t.messages) for t in masked_threads)
            logger.info(
                f"Successfully masked {len(threads)} threads ({total_messages} messages)"
            )
            return masked_threads

        except Exception as e:
            error_msg = f"PII masking failed: {str(e)}"
            logger.error(error_msg)
            raise MaskingError(error_msg) from e

    async def _mask_thread_messages(self, thread: StandardizedThread) -> None:
        """
        Mask all messages in a thread using a single Orchestration V2 call.

        Args:
            thread: StandardizedThread whose messages need masking

        Raises:
            MaskingError: If masking fails for the thread
        """
        try:
            # Combine all messages into a natural conversation flow
            # This allows the LLM to better understand context for consistent masking
            combined_text = "\n\n".join([msg.content for msg in thread.messages])

            # Create orchestration config
            config = self._create_orchestration_config(combined_text)

            # Call orchestration service with placeholder values
            # Note: This await yields control to event loop, allowing other threads
            # in asyncio.gather() to start their API calls concurrently
            result = await asyncio.to_thread(
                self.orchestration_service.run,
                config=config,
                placeholder_values={"input": combined_text},
            )

            # Extract masked content from result
            if result and hasattr(result, "final_result"):
                masked_combined = self._extract_masked_content(result)

                # Split the masked content back into individual messages
                self._distribute_masked_content(thread, masked_combined)

                logger.debug(
                    f"Masked thread {thread.id}: {len(thread.messages)} messages"
                )
            else:
                raise MaskingError(
                    f"Invalid response from orchestration service for thread {thread.id}"
                )

        except Exception as e:
            error_msg = f"Thread masking failed for {thread.id}: {str(e)}"
            logger.error(error_msg)
            raise MaskingError(error_msg) from e

    def _distribute_masked_content(
        self, thread: StandardizedThread, masked_combined: str
    ) -> None:
        """
        Distribute masked content back to individual messages.

        The masked text is split by double newlines (same separator used when combining).

        Args:
            thread: Thread whose messages need updating
            masked_combined: Combined masked text

        Raises:
            MaskingError: If content cannot be distributed properly
        """
        try:
            # Split by double newlines (same separator used in combining)
            masked_parts = masked_combined.split("\n\n")

            # Verify we got the expected number of parts
            if len(masked_parts) != len(thread.messages):
                logger.warning(
                    f"Message count mismatch: expected {len(thread.messages)}, got {len(masked_parts)}. "
                    f"Attempting to distribute content anyway."
                )

            # Distribute masked content to messages
            for i, message in enumerate(thread.messages):
                if i < len(masked_parts):
                    message.content = masked_parts[i].strip()
                else:
                    # If we have fewer parts than messages, this is an error
                    logger.error(f"Missing masked content for message {i+1}")
                    raise MaskingError(
                        f"Could not find masked content for message {i+1}/{len(thread.messages)}"
                    )

        except Exception as e:
            raise MaskingError(f"Failed to distribute masked content: {e}") from e

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
        self, threads: List[StandardizedThread]
    ) -> Dict[str, Any]:
        """
        Get statistics about masking requirements (without actually masking).

        Useful for pre-flight checks and reporting.

        Args:
            threads: Threads to analyze

        Returns:
            Dictionary with statistics
        """
        total_messages = sum(len(thread.messages) for thread in threads)
        total_chars = sum(
            len(msg.content) for thread in threads for msg in thread.messages
        )

        # With parallel processing, time ≈ max of all threads (not sum)
        estimated_time = self.settings.orchestration_timeout

        return {
            "total_threads": len(threads),
            "total_messages": total_messages,
            "total_characters": total_chars,
            "estimated_api_calls": len(threads),  # One call per thread
            "estimated_time_seconds": estimated_time,  # Parallel processing
            "entities_masked": ["PERSON", "EMAIL", "PHONE", "ADDRESS", "PERSONAL_ID"],
            "masking_method": "anonymization",
        }
