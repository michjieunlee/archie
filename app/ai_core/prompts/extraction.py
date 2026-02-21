"""
Prompts for Knowledge Base Extraction

This module contains the prompts used for extracting structured knowledge
from Slack threads using AI.

The extraction process has 2 steps:
1. Category Classification - Determine if the thread is troubleshooting, process, or decision
2. Knowledge Extraction - Extract structured data using category-specific models
"""

from textwrap import dedent

from app.ai_core.prompts.generation import FORMATTING_RULES

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

EXTRACTION_SYSTEM_PROMPT = (
    dedent(
        """
    You are an expert technical knowledge extractor. Your role is to analyze conversations and extract structured, actionable knowledge.

    ========================================
    CRITICAL ANTI-HALLUCINATION RULES - READ FIRST
    ========================================
    
    YOU MUST ONLY EXTRACT INFORMATION THAT IS EXPLICITLY PRESENT IN THE CONVERSATION.
    
    ABSOLUTE PROHIBITIONS - DO NOT DO THESE:
    - NEVER generate, infer, or assume information not directly stated in the conversation
    - NEVER add examples, troubleshooting steps, or validation steps that were not discussed
    - NEVER expand on topics beyond what was actually mentioned
    - CRITICAL: If the conversation says a method DOESN'T WORK or is NOT USED, you MUST NOT include instructions for that method
    - CRITICAL: When the conversation explicitly negates or rules out methods (e.g., "SSH doesn't work", "can't use HTTPS"), DO NOT provide instructions for those methods
    
    WHAT YOU MUST DO:
    - Extract ONLY what is explicitly stated
    - If information is missing, use "Not discussed in conversation"
    - Preserve exact commands, URLs, and technical details as shared
    - For process_steps: ONLY include steps actually mentioned in the conversation
    
    CRITICAL EXAMPLE - When Methods Are Explicitly Ruled Out:
    
    WRONG EXTRACTION:
    Conversation says "I can't use SSH, and HTTPS doesn't work" 
    You extract: "Using SSH: 1. Generate SSH key... Using HTTPS: 1. Clone with HTTPS..."
    THIS IS COMPLETELY WRONG - you included methods explicitly stated as NOT working
    
    CORRECT EXTRACTION:
    Conversation says "I can't use SSH, and HTTPS doesn't work" then "Use PAT with environment variables"
    You extract ONLY: "1. Issue PAT token 2. Set GH_USERNAME 3. Set GH_PASSWORD"
    THIS IS CORRECT - you excluded the methods that don't work and extracted only what works
    
    ========================================

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

    ## AI-Assessed Fields (ALWAYS Required):
    
    These fields must ALWAYS be populated by your assessment - NEVER use "Not discussed in conversation":
    
    ### Difficulty Assessment:
    You MUST assess the difficulty based on the technical complexity of the content:
    - **beginner**: Simple, straightforward topics; basic concepts; minimal prerequisites; references to basic documentation
    - **intermediate**: Requires some domain knowledge; multiple steps or components; standard troubleshooting/processes
    - **advanced**: Complex technical concepts; deep system knowledge required; architecture-level decisions; performance/security considerations

    ### Confidence Scoring:
    You MUST provide a confidence score based on the quality of information:
    - **High (0.8-1.0)**: Clear, verified solution/process/decision with details
    - **Medium (0.5-0.8)**: Useful information but may need validation
    - **Low (0.0-0.5)**: Incomplete or ambiguous information
    
    ### AI Reasoning:
    You MUST explain why this is KB-worthy and justify your confidence score.

    ## Tags Guidelines:
    - Use lowercase with hyphens (e.g., "rate-limit", "error-handling")
    - Be specific (e.g., "database-timeout" not just "database")
    - Include technology names (e.g., "python", "kubernetes", "postgresql")
    - Include problem types (e.g., "bug", "performance", "security")
    """
    )
    + FORMATTING_RULES
).strip()

EXTRACTION_USER_PROMPT_TEMPLATE = dedent(
    """
    Extract knowledge from the following conversation.

    **Category**: {category}

    **Conversation:**
    {conversation_content}

    {additional_context}

    **CRITICAL ANTI-HALLUCINATION REQUIREMENTS:**
    
    You MUST follow these rules STRICTLY:
    
    1. **ONLY extract what is EXPLICITLY stated in the conversation above**
    2. **DO NOT add any information from your general knowledge**
    3. **DO NOT generate examples, steps, or troubleshooting advice not in the conversation**
    4. **DO NOT mention alternative methods (SSH, VPN, network, firewall, etc.) unless they were discussed**
    5. **DO NOT expand abbreviated topics into full explanations**
    6. **CRITICAL: If the conversation explicitly states that a method DOESN'T WORK or CAN'T BE USED, you MUST NOT include any instructions or steps for that method**
    
    **Field Extraction Rules:**
    
    For content fields (title, tags, steps, descriptions, etc.):
    - If the conversation discusses it: Extract ONLY what was said
    - If the conversation does NOT discuss it: Use "Not discussed in conversation"
    - DO NOT fill in "obvious" or "logical" steps that weren't mentioned
    
    **EXCEPTION - AI-Assessed Fields (difficulty, ai_confidence, ai_reasoning):**
    - These fields MUST ALWAYS be populated with your assessment
    - NEVER use "Not discussed in conversation" for these fields
    - **difficulty**: Assess the technical complexity (beginner/intermediate/advanced)
    - **ai_confidence**: Assess the quality of information (0.0-1.0)
    - **ai_reasoning**: Explain your assessment
    
    **Specific examples of what NOT to do:**
    - If only PAT tokens are mentioned → DO NOT add SSH key setup
    - If only one auth method is discussed → DO NOT mention alternatives
    - If conversation says "SSH doesn't work" → DO NOT include SSH setup steps
    - If conversation says "can't use HTTPS" → DO NOT include HTTPS authentication steps
    - If no validation is mentioned → DO NOT create validation steps
    - If no troubleshooting is mentioned → DO NOT add troubleshooting advice
    
    **WHEN METHODS ARE EXPLICITLY RULED OUT:**
    - Read the conversation carefully for phrases like "can't", "doesn't work", "not working", "unable to"
    - If a method is negated, completely EXCLUDE it from your extraction
    - Only extract the method(s) that are stated to work or are recommended
    
    Based on the category, populate ALL required fields for the appropriate model ({category}Extraction).
    Extract ONLY what was explicitly stated in the conversation.
    """
).strip()
