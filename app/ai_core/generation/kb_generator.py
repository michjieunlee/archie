"""
Knowledge Base Generator Module

This module handles generation of markdown files from KBDocuments using templates.
"""

import logging
import re
import yaml
from pathlib import Path
from typing import Optional

from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain_core.prompts import ChatPromptTemplate

from app.models.knowledge import KBDocument, KBCategory
from app.utils import flatten_list, format_kb_document_content
from app.ai_core.prompts.generation import UPDATE_PROMPT
from app.config import get_settings

logger = logging.getLogger(__name__)


class KBGenerator:
    """
    Generates markdown files from knowledge documents using templates.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the KB Generator.

        Args:
            templates_dir: Directory containing template files. Defaults to app/ai_core/templates
        """
        if templates_dir is None:
            # Default to templates dir relative to this module
            module_dir = Path(__file__).parent.parent  # ai_core directory
            self.templates_dir = module_dir / "templates"
        else:
            self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")

    def generate_markdown(self, document: KBDocument) -> str:
        """
        Generate markdown file content for the knowledge document using templates.

        Args:
            document: The knowledge document to convert

        Returns:
            Markdown formatted document content
        """
        # Load the appropriate template
        template_file = self._get_template_file(document.category)
        template_content = self._load_template(template_file)

        if not template_content:
            logger.error(f"Failed to load template for category: {document.category}")
            return self._fallback_markdown(document)

        # Prepare template variables
        variables = self._prepare_template_variables(document)

        # Fill the template
        try:
            markdown = template_content.format(**variables)
            return markdown
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return self._fallback_markdown(document)

    def _get_template_file(self, category: KBCategory) -> str:
        """
        Get the template filename for a category.

        Args:
            category: The document category

        Returns:
            Template filename
        """
        template_map = {
            KBCategory.TROUBLESHOOTING: "troubleshooting.md",
            KBCategory.PROCESSES: "processes.md",
            KBCategory.DECISIONS: "decisions.md",
            KBCategory.REFERENCES: "references.md",
            KBCategory.GENERAL: "general.md",
        }
        return template_map.get(category, "general.md")

    def _load_template(self, template_file: str) -> Optional[str]:
        """
        Load template content from file.

        Args:
            template_file: Template filename

        Returns:
            Template content as string, or None if not found
        """
        template_path = self.templates_dir / template_file

        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return None

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading template {template_file}: {e}")
            return None

    def _prepare_template_variables(self, document: KBDocument) -> dict:
        """
        Prepare variables for template filling.

        Args:
            document: The knowledge document

        Returns:
            Dictionary of template variables
        """
        extraction = document.extraction_output
        metadata = document.extraction_metadata

        # Flatten any nested lists in tags (use shared utility)
        normalized_tags = flatten_list(extraction.tags)
        tags_formatted = ", ".join([f'"{tag}"' for tag in normalized_tags])

        # Use yaml.dump() to properly serialize ai_reasoning with correct escaping
        # This handles quotes, special characters, and multiline strings correctly
        ai_reasoning_yaml = yaml.dump(
            extraction.ai_reasoning, default_flow_style=True, allow_unicode=True
        ).strip()

        # Common variables
        variables = {
            "title": extraction.title,
            "tags": tags_formatted,
            "difficulty": extraction.difficulty,
            "source_type": metadata.source_type,
            # Show "N/A" for history_from if not provided (e.g., when only limit is used)
            "history_from": (
                metadata.history_from.isoformat() if metadata.history_from else "N/A"
            ),
            "history_to": (
                metadata.history_to.isoformat() if metadata.history_to else "N/A"
            ),
            "message_limit": (
                metadata.message_limit if metadata.message_limit is not None else ""
            ),
            "ai_confidence": f"{extraction.ai_confidence:.2f}",
            "ai_reasoning": ai_reasoning_yaml,
            "created_date": document.created_at.strftime("%Y-%m-%d"),
            "last_updated": document.updated_at.strftime("%Y-%m-%d"),
        }

        # Category-specific variables from extraction
        # Get extraction data but exclude keys we've already handled
        extraction_data = extraction.model_dump()
        # Remove keys that we've already processed (to avoid overwriting)
        for key in ["title", "tags", "difficulty", "ai_confidence", "ai_reasoning"]:
            extraction_data.pop(key, None)
        variables.update(extraction_data)

        return variables

    def _fallback_markdown(self, document: KBDocument) -> str:
        """
        Generate basic markdown as fallback if template fails.

        Args:
            document: The knowledge document

        Returns:
            Basic markdown content
        """
        extraction = document.extraction_output

        # Flatten tags to flat list (use shared utility)
        normalized_tags = flatten_list(extraction.tags)

        md = f"# {extraction.title}\n\n"
        md += f"**Category**: {document.category.value}\n\n"
        md += f"**Tags**: {', '.join(normalized_tags)}\n\n"
        md += f"**Difficulty**: {extraction.difficulty}\n\n"
        md += f"**Confidence**: {extraction.ai_confidence:.2f}\n\n"
        md += f"**Reasoning**: {extraction.ai_reasoning}\n\n"

        md += "## Content\n\n"
        md += str(extraction.model_dump())

        return md

    def generate_filename(self, document: KBDocument) -> str:
        """
        Generate a filename for the document.

        Args:
            document: The knowledge document

        Returns:
            Filename with .md extension
        """
        # Convert title to kebab-case filename
        filename = document.title.lower()
        filename = filename.replace(" ", "-")
        filename = "".join(c for c in filename if c.isalnum() or c == "-")
        filename = filename.strip("-")

        # Limit length
        if len(filename) > 60:
            filename = filename[:60].rstrip("-")

        return f"{filename}.md"

    def _update_frontmatter_metadata(
        self, content: str, new_document: KBDocument
    ) -> str:
        """
        Programmatically update metadata fields in the YAML frontmatter.

        Updates the following fields if they exist in the new_document:
        - last_updated: Always set to new_document.updated_at
        - history_from: If present in new_document metadata
        - history_to: If present in new_document metadata
        - message_limit: If present in new_document metadata
        - ai_confidence: From new_document extraction
        - ai_reasoning: From new_document extraction

        Args:
            content: The markdown content with YAML frontmatter
            new_document: The new KB document with updated metadata

        Returns:
            Content with updated frontmatter metadata
        """
        # Extract frontmatter and body
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            logger.warning("No frontmatter found in document, returning content as-is")
            return content

        frontmatter = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        # Update last_updated to new_document's updated_at timestamp
        update_date = new_document.updated_at.strftime("%Y-%m-%d")
        frontmatter = re.sub(
            r'last_updated:\s*"[^"]*"', f'last_updated: "{update_date}"', frontmatter
        )

        # Update metadata fields from new_document if they exist
        metadata = new_document.extraction_metadata
        extraction = new_document.extraction_output

        # Update history_from if present
        if metadata.history_from:
            history_from_str = metadata.history_from.isoformat()
            frontmatter = re.sub(
                r'history_from:\s*"[^"]*"',
                f'history_from: "{history_from_str}"',
                frontmatter,
            )

        # Update history_to if present
        if metadata.history_to:
            history_to_str = metadata.history_to.isoformat()
            frontmatter = re.sub(
                r'history_to:\s*"[^"]*"', f'history_to: "{history_to_str}"', frontmatter
            )

        # Update message_limit if present
        if metadata.message_limit is not None:
            frontmatter = re.sub(
                r"message_limit:\s*\d+",
                f"message_limit: {metadata.message_limit}",
                frontmatter,
            )

        # Update ai_confidence
        ai_confidence_str = f"{extraction.ai_confidence:.2f}"
        frontmatter = re.sub(
            r"ai_confidence:\s*[\d.]+",
            f"ai_confidence: {ai_confidence_str}",
            frontmatter,
        )

        # Update ai_reasoning - use yaml.dump() for proper YAML serialization
        # This handles quotes, special characters, and multiline strings correctly
        ai_reasoning_yaml = yaml.dump(
            extraction.ai_reasoning, default_flow_style=True, allow_unicode=True
        ).strip()
        frontmatter = re.sub(
            r'ai_reasoning:\s*["\'].*?["\'](?:\s|$)',
            f"ai_reasoning: {ai_reasoning_yaml}\n",
            frontmatter,
            flags=re.DOTALL,
        )

        # Reconstruct the document
        updated_content = f"---\n{frontmatter}\n---\n{body}"

        logger.info(f"Updated frontmatter metadata: last_updated={update_date}")
        return updated_content

    async def update_markdown(
        self, existing_content: str, new_document: KBDocument
    ) -> str:
        """
        Update existing KB document with new information using AI.

        Uses UPDATE_PROMPT to intelligently merge content following guidelines:
        - Only update lines that change meaning
        - Preserve formatting and structure
        - Make minimal changes
        - Programmatically updates metadata fields after AI processing

        Args:
            existing_content: The current markdown content of the existing document
            new_document: The newly extracted KB document with information to merge

        Returns:
            Updated markdown content with refreshed metadata

        Raises:
            Exception: If AI update fails, will be caught by caller for fallback
        """
        try:
            logger.info("Initializing AI-powered document update...")

            # Initialize LLM
            config = get_settings()
            proxy_client = get_proxy_client("gen-ai-hub")
            llm = ChatOpenAI(
                proxy_model_name=config.openai_model,
                proxy_client=proxy_client,
                temperature=0.0,  # Deterministic for updates
            )

            # Format new information using shared utility function
            new_info_formatted = format_kb_document_content(new_document)

            logger.info(
                f"Formatted new content for category: {new_document.category.value}"
            )

            # Create prompt
            prompt = ChatPromptTemplate.from_messages([("system", UPDATE_PROMPT)])

            # Build chain and invoke
            chain = prompt | llm
            response = await chain.ainvoke(
                {
                    "existing_content": existing_content,
                    "new_information": new_info_formatted,
                }
            )

            updated_content = response.content.strip()

            # Programmatically update metadata fields in frontmatter
            updated_content = self._update_frontmatter_metadata(
                updated_content, new_document
            )

            logger.info(
                f"Successfully updated KB document using AI (length: {len(updated_content)} chars)"
            )
            return updated_content

        except Exception as e:
            logger.error(f"Error in AI-powered document update: {e}", exc_info=True)
            raise  # Re-raise for caller to handle fallback

    def get_category_directory(self, category: KBCategory) -> str:
        """
        Get the directory name for a category.

        Args:
            category: The document category

        Returns:
            Directory name (already plural in enum values)
        """
        # Now that enum values are already plural, just return the value directly
        return category.value
