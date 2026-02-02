"""
Prompt 3: KB Draft / Update
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

This prompt generates or updates KB documents.
"""

GENERATION_PROMPT = """
You are a technical writer creating knowledge base documentation.

## Task
{task_type}  # "Create new document" or "Update existing document"

## Source Thread
{thread_content}

## Extracted Information
Title: {title}
Type: {kb_type}
Summary: {summary}
Key Points:
{key_points}

{existing_content_section}

## Requirements
1. Write in clear, concise technical language
2. Use the provided markdown template structure
3. Include actionable information
4. Add relevant tags for searchability
5. Keep the tone professional and helpful

## Markdown Template
{template}

Generate the complete markdown document.
"""

# Template sections for different KB types
TEMPLATE_SECTIONS = {
    "troubleshooting": ["Problem", "Root Cause", "Solution", "Prevention"],
    "decision": ["Context", "Decision", "Rationale", "Consequences"],
    "howto": ["Overview", "Prerequisites", "Steps", "Verification"],
    "architecture": ["Context", "Design", "Tradeoffs", "Related"],
    "best_practice": ["Overview", "Practice", "Examples", "Anti-patterns"],
}
