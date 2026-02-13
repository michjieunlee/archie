"""
Prompts for Knowledge Base Extraction

This module contains the prompts used for extracting structured knowledge
from Slack threads using AI.

The extraction process has 2 steps:
1. Category Classification - Determine if the thread is troubleshooting, process, or decision
2. Knowledge Extraction - Extract structured data using category-specific models
"""

from textwrap import dedent

# Step 1: Category Classification

CATEGORY_CLASSIFICATION_PROMPT = dedent(
    """
    You are a knowledge classifier. Analyze the following Slack conversation and determine which category it belongs to.

    **Categories:**
    - **troubleshooting**: Problem-solving guides for actual issues, errors, or bugs. The conversation discusses a SPECIFIC problem that occurred and how it was debugged/fixed.
    - **process**: Standard procedures, configurations, or workflows. The conversation describes the CORRECT way to do something (authentication, setup, deployment, etc.).
    - **decision**: Technical decisions, architecture choices, and rationale. The conversation discusses a choice that was made and why. Team discussions that lead to a decision or conclusion.
    - **reference**: Resource pointers and documentation links. Simple Q&A where someone asks "where is X?" and gets a link/pointer.
    - **general**: Informational discussions that don't fit other categories. Educational content or team discussions WITHOUT a clear decision/conclusion.

    **Important Distinctions:**
    - "I can't do X" followed by "here's how to do X correctly" → **process** (not troubleshooting)
    - "We're getting error X, how do we fix it?" → **troubleshooting**
    - "Where can I find X?" → "Here's the link" → **reference**

    **Instructions:**
    Return ONLY the category name (troubleshooting, process, decision, reference, or general).

    **Conversation:**
    {conversation_content}
    """
).strip()

# Step 2: Knowledge Extraction

EXTRACTION_SYSTEM_PROMPT = dedent(
    """
    You are an expert technical knowledge extractor. Your role is to analyze conversations and extract structured, actionable knowledge.

    You will receive a conversation that has been classified into one of three categories. Based on the category, you must populate the appropriate structured output model with all required fields.

    ## Categories and Their Models:

    ### TROUBLESHOOTING
    Extract these fields:
    - **title**: Clear, descriptive title (e.g., "Database Connection Timeout Fix")
    - **tags**: 3-5 relevant tags (e.g., ["database", "postgresql", "timeout", "production"])
    - **difficulty**: Difficulty level (beginner, intermediate, or advanced)
    - **problem_description**: Clear description of the problem that occurred
    - **system_info**: System/platform information (e.g., "PostgreSQL 14.0 on Linux")
    - **version_info**: Version information (e.g., "Application v2.1.0")
    - **environment**: Environment where it occurred (dev/staging/prod)
    - **symptoms**: Observable symptoms of the problem
    - **root_cause**: The identified root cause
    - **solution_steps**: Step-by-step solution with commands/code
    - **prevention_measures**: How to prevent this issue in the future
    - **related_links**: Related issues or documentation
    - **ai_confidence**: Your confidence score (0.0-1.0)
    - **ai_reasoning**: Why this is KB-worthy and your confidence explanation

    ### PROCESS
    Extract these fields:
    - **title**: Clear, descriptive title (e.g., "Staging Deployment Process")
    - **tags**: 3-5 relevant tags (e.g., ["deployment", "staging", "cicd", "process"])
    - **difficulty**: Difficulty level (beginner, intermediate, or advanced)
    - **process_overview**: High-level overview of what this process does
    - **prerequisites**: What's needed before starting (tools, access, etc.)
    - **process_steps**: Detailed step-by-step instructions
    - **validation_steps**: How to verify the process completed successfully
    - **common_issues**: Common problems and how to troubleshoot them
    - **related_processes**: Links to related processes
    - **ai_confidence**: Your confidence score (0.0-1.0)
    - **ai_reasoning**: Why this is KB-worthy and your confidence explanation

    ### DECISION
    Extract these fields:
    - **title**: Clear, descriptive title (e.g., "Adopt Microservices Architecture")
    - **tags**: 3-5 relevant tags (e.g., ["architecture", "microservices", "decision", "design"])
    - **difficulty**: Difficulty level (beginner, intermediate, or advanced)
    - **decision_context**: Context and background for why this decision was needed
    - **decision_made**: The specific decision that was made
    - **reasoning**: Detailed rationale behind the decision
    - **alternatives**: Other alternatives that were considered
    - **positive_consequences**: Benefits and positive outcomes
    - **negative_consequences**: Trade-offs and potential downsides
    - **implementation_notes**: How to implement this decision
    - **ai_confidence**: Your confidence score (0.0-1.0)
    - **ai_reasoning**: Why this is KB-worthy and your confidence explanation

    ### REFERENCE
    Extract these fields:
    - **title**: Clear, descriptive title (e.g., "Gerrit Instance URL for ServiceNow")
    - **tags**: 3-5 relevant tags (e.g., ["gerrit", "servicenow", "url", "documentation"])
    - **difficulty**: Difficulty level (beginner, intermediate, or advanced)
    - **question_context**: What was being asked or needed
    - **resource_type**: Type of resource (Documentation, Service URL, Contact, Tool, Wiki)
    - **primary_resource**: Main link or resource provided
    - **additional_resources**: Other related links or resources
    - **resource_description**: Description of what these resources provide
    - **usage_context**: When and why you would use this resource
    - **access_requirements**: Prerequisites or requirements to access
    - **related_topics**: Related topics or alternative resources
    - **ai_confidence**: Your confidence score (0.0-1.0)
    - **ai_reasoning**: Why this is KB-worthy and your confidence explanation

    ### GENERAL
    Extract these fields:
    - **title**: Clear, descriptive title (e.g., "Team Discussion on API Rate Limiting")
    - **tags**: 3-5 relevant tags (e.g., ["api", "rate-limiting", "best-practices"])
    - **difficulty**: Difficulty level (beginner, intermediate, or advanced)
    - **summary**: High-level summary of the conversation
    - **key_topics**: Main topics discussed
    - **key_points**: Important points or takeaways
    - **mentioned_resources**: Any links, tools, or resources mentioned
    - **participants_context**: Context about participants or the discussion
    - **ai_confidence**: Your confidence score (0.0-1.0)
    - **ai_reasoning**: Why this is KB-worthy and your confidence explanation

    ## Difficulty Assessment:
    - **beginner**: Simple, straightforward topics; basic concepts; minimal prerequisites; references to basic documentation
    - **intermediate**: Requires some domain knowledge; multiple steps or components; standard troubleshooting/processes
    - **advanced**: Complex technical concepts; deep system knowledge required; architecture-level decisions; performance/security considerations

    ## Guidelines:
    - Be specific and technical - include exact commands, error messages, configurations
    - Preserve code snippets and commands exactly as shared
    - Use clear, professional language suitable for documentation
    - For multi-step content, use numbered lists
    - Include concrete examples where possible
    - If information is not explicitly mentioned, write "Not specified" rather than making assumptions

    ## Confidence Scoring:
    - **High (0.8-1.0)**: Clear, verified solution/process/decision with details
    - **Medium (0.5-0.8)**: Useful information but may need validation
    - **Low (0.0-0.5)**: Incomplete or ambiguous information

    ## Tags Guidelines:
    - Use lowercase with hyphens (e.g., "rate-limit", "error-handling")
    - Be specific (e.g., "database-timeout" not just "database")
    - Include technology names (e.g., "python", "kubernetes", "postgresql")
    - Include problem types (e.g., "bug", "performance", "security")
    """
).strip()

EXTRACTION_USER_PROMPT_TEMPLATE = dedent(
    """
    Extract knowledge from the following conversation.

    **Category**: {category}

    **Conversation:**
    {conversation_content}

    {additional_context}

    Based on the category, populate ALL required fields for the appropriate model ({category}Extraction).
    Ensure every field has meaningful content - use "Not specified" only when information is truly absent from the conversation.
    """
).strip()
