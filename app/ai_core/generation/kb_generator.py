"""
Knowledge Base Generator Module

This module handles generation of markdown files from KnowledgeArticles using templates.
"""

import logging
from pathlib import Path
from typing import Optional

from app.models.knowledge import KnowledgeArticle, KBCategory

logger = logging.getLogger(__name__)


class KBGenerator:
    """
    Generates markdown files from knowledge articles using templates.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the KB Generator.

        Args:
            templates_dir: Directory containing template files. Defaults to .archie/templates
        """
        if templates_dir is None:
            # Default to .archie/templates relative to project root
            self.templates_dir = (
                Path(__file__).parent.parent.parent.parent / ".archie" / "templates"
            )
        else:
            self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")

    def generate_markdown(self, article: KnowledgeArticle) -> str:
        """
        Generate markdown file content for the knowledge article using templates.

        Args:
            article: The knowledge article to convert

        Returns:
            Markdown formatted article content
        """
        # Load the appropriate template
        template_file = self._get_template_file(article.category)
        template_content = self._load_template(template_file)

        if not template_content:
            logger.error(f"Failed to load template for category: {article.category}")
            return self._fallback_markdown(article)

        # Prepare template variables
        variables = self._prepare_template_variables(article)

        # Fill the template
        try:
            markdown = template_content.format(**variables)
            return markdown
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return self._fallback_markdown(article)

    def _get_template_file(self, category: KBCategory) -> str:
        """
        Get the template filename for a category.

        Args:
            category: The article category

        Returns:
            Template filename
        """
        template_map = {
            KBCategory.TROUBLESHOOTING: "troubleshooting.md",
            KBCategory.PROCESSES: "process.md",
            KBCategory.DECISIONS: "decision.md",
        }
        return template_map.get(category, "troubleshooting.md")

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

    def _prepare_template_variables(self, article: KnowledgeArticle) -> dict:
        """
        Prepare variables for template filling.

        Args:
            article: The knowledge article

        Returns:
            Dictionary of template variables
        """
        extraction = article.extraction_output
        metadata = article.extraction_metadata

        # Common variables
        variables = {
            "title": extraction.title,
            "tags": ", ".join([f'"{tag}"' for tag in extraction.tags]),
            "source_type": metadata.source_type,
            "source_threads": f'"{metadata.source_id}"' if metadata.source_id else "",
            "ai_confidence": f"{extraction.ai_confidence:.2f}",
            "ai_reasoning": extraction.ai_reasoning,
            "created_date": article.created_at.strftime("%Y-%m-%d"),
            "last_updated": article.updated_at.strftime("%Y-%m-%d"),
        }

        # Category-specific variables
        variables.update(extraction.model_dump())

        return variables

    def _fallback_markdown(self, article: KnowledgeArticle) -> str:
        """
        Generate basic markdown as fallback if template fails.

        Args:
            article: The knowledge article

        Returns:
            Basic markdown content
        """
        extraction = article.extraction_output

        md = f"# {extraction.title}\n\n"
        md += f"**Category**: {article.category.value}\n\n"
        md += f"**Tags**: {', '.join(extraction.tags)}\n\n"
        md += f"**Confidence**: {extraction.ai_confidence:.2f}\n\n"
        md += f"**Reasoning**: {extraction.ai_reasoning}\n\n"

        md += "## Content\n\n"
        md += str(extraction.model_dump())

        return md

    def generate_filename(self, article: KnowledgeArticle) -> str:
        """
        Generate a filename for the article.

        Args:
            article: The knowledge article

        Returns:
            Filename with .md extension
        """
        # Convert title to kebab-case filename
        filename = article.title.lower()
        filename = filename.replace(" ", "-")
        filename = "".join(c for c in filename if c.isalnum() or c == "-")
        filename = filename.strip("-")

        # Limit length
        if len(filename) > 60:
            filename = filename[:60].rstrip("-")

        return f"{filename}.md"

    def get_category_directory(self, category: KBCategory) -> str:
        """
        Get the directory name for a category.

        Args:
            category: The article category

        Returns:
            Directory name
        """
        return category.value
