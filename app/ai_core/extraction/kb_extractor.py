"""
Knowledge Base Candidate Extractor
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

Responsibilities:
- Prompt 1: KB Candidate Extraction
- Detect decision-making, troubleshooting, and know-how
- Evaluate KB value
"""

from dataclasses import dataclass
from enum import Enum
from app.integrations.slack.models import SlackThread


class KBType(str, Enum):
    """Type of knowledge base content."""

    TROUBLESHOOTING = "troubleshooting"  # Problem-solving process
    DECISION = "decision"  # Decision record
    HOWTO = "howto"  # How-to / Procedure
    ARCHITECTURE = "architecture"  # Architecture decision
    BEST_PRACTICE = "best_practice"  # Best practice
    NOT_KB_WORTHY = "not_kb_worthy"  # Not KB worthy


@dataclass
class ExtractionResult:
    """Result of KB candidate extraction."""

    is_kb_candidate: bool
    kb_type: KBType
    confidence_score: float  # 0.0 - 1.0
    title_suggestion: str
    summary: str
    key_points: list[str]
    reasoning: str  # AI's reasoning (explainability)


class KBExtractor:
    """
    Extracts KB candidates from Slack threads.

    Uses Prompt 1: KB Candidate Extraction
    """

    def __init__(self):
        # TODO: Initialize SAP GenAI SDK client
        pass

    async def extract(self, masked_thread: SlackThread) -> ExtractionResult:
        """
        Analyze thread and extract KB candidate information.

        Analysis criteria:
        1. Is there a problem-solution pattern?
        2. Is a decision-making process documented?
        3. Is there reusable know-how?
        4. Would this be helpful for new hires?

        Args:
            masked_thread: PII-masked Slack thread

        Returns:
            ExtractionResult with KB candidate info and reasoning
        """
        # TODO: Implement using SAP GenAI SDK with extraction prompt
        raise NotImplementedError

    def _build_extraction_prompt(self, thread: SlackThread) -> str:
        """Build the extraction prompt."""
        # TODO: Use prompts/extraction.py
        raise NotImplementedError
