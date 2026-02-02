"""
Knowledge Base Pipeline Orchestrator

Full pipeline orchestration:
Slack Thread -> PII Masking -> KB Extraction -> Matching -> Generation -> GitHub PR
"""

from dataclasses import dataclass
from app.integrations.slack import SlackClient, parse_permalink
from app.integrations.github import GitHubClient, PRManager
from app.ai_core.masking import PIIMasker
from app.ai_core.extraction import KBExtractor
from app.ai_core.matching import KBMatcher, MatchAction
from app.ai_core.generation import KBGenerator
from app.models.knowledge import KnowledgeDocument


@dataclass
class PipelineResult:
    """Result of the full pipeline execution."""

    success: bool
    action: str  # create, update, ignore
    document: KnowledgeDocument | None = None
    pr_url: str | None = None
    error: str | None = None


class KBPipeline:
    """
    Orchestrates the full KB creation pipeline.

    Pipeline steps:
    1. Fetch thread from Slack
    2. Mask PII data
    3. Extract KB candidate
    4. Match against existing KB
    5. Generate KB document
    6. Create GitHub PR
    """

    def __init__(self):
        self.slack_client = SlackClient()
        self.github_client = GitHubClient()
        self.pr_manager = PRManager(self.github_client)
        self.masker = PIIMasker()
        self.extractor = KBExtractor()
        self.matcher = KBMatcher()
        self.generator = KBGenerator()

    async def process_thread(self, permalink: str) -> PipelineResult:
        """
        Process a Slack thread through the full KB pipeline.

        Args:
            permalink: Slack thread permalink

        Returns:
            PipelineResult with outcome details
        """
        try:
            # Step 1: Parse permalink and fetch thread
            parsed = parse_permalink(permalink)
            thread = await self.slack_client.get_thread_messages(
                parsed.channel_id, parsed.thread_ts
            )

            # Step 2: Mask PII
            masking_result = await self.masker.mask_thread(thread)

            # Step 3: Extract KB candidate
            extraction_result = await self.extractor.extract(
                masking_result.masked_thread
            )

            if not extraction_result.is_kb_candidate:
                return PipelineResult(
                    success=True,
                    action="ignore",
                    error=f"Not KB worthy: {extraction_result.reasoning}",
                )

            # Step 4: Match against existing KB
            existing_docs = []  # TODO: Fetch from KB repo
            match_result = await self.matcher.match(extraction_result, existing_docs)

            if match_result.action == MatchAction.IGNORE:
                return PipelineResult(
                    success=True,
                    action="ignore",
                    error=f"Ignored: {match_result.reasoning}",
                )

            # Step 5: Generate KB document
            if match_result.action == MatchAction.CREATE:
                gen_result = await self.generator.generate_new(
                    masking_result.masked_thread, extraction_result
                )
            else:  # UPDATE
                existing_content = ""  # TODO: Fetch from repo
                gen_result = await self.generator.generate_update(
                    masking_result.masked_thread,
                    extraction_result,
                    match_result,
                    existing_content,
                )

            # Step 6: Create GitHub PR
            # TODO: Implement PR creation

            return PipelineResult(
                success=True,
                action=match_result.action.value,
                document=KnowledgeDocument(
                    title=gen_result.title,
                    content=gen_result.content,
                    category=gen_result.metadata.get("category", "general"),
                    tags=gen_result.metadata.get("tags", []),
                    source_thread_url=permalink,
                    source_type="slack",
                    ai_confidence_score=extraction_result.confidence_score,
                    ai_reasoning=extraction_result.reasoning,
                    file_path=gen_result.file_path,
                ),
            )

        except Exception as e:
            return PipelineResult(
                success=False,
                action="error",
                error=str(e),
            )
