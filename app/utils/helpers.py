"""
Shared Utility Functions

Common helper functions used across multiple modules.
"""

from typing import Any, List


def flatten_list(items: Any) -> List[str]:
    """
    Flatten a potentially nested list to a single-level list of strings.

    Handles various formats:
    - Nested lists: [["a", "b"]] → ["a", "b"]
    - Flat lists: ["a", "b"] → ["a", "b"]
    - Single string: "a" → ["a"]
    - None/empty: None → []

    Args:
        items: Any value that could be a list, nested list, or string

    Returns:
        Flat list of strings
    """
    if not items:
        return []

    if isinstance(items, str):
        return [items]

    if not isinstance(items, list):
        return [str(items)]

    # Flatten nested lists
    result = []
    for item in items:
        if isinstance(item, list):
            for subitem in item:
                if isinstance(subitem, str):
                    result.append(subitem)
                else:
                    result.append(str(subitem))
        elif isinstance(item, str):
            result.append(item)
        else:
            result.append(str(item))

    return result


def format_kb_document_content(kb_document: "KBDocument") -> str:
    """
    Format KB document content based on category.

    This is a shared utility used by both KBMatcher (for matching) and
    KBGenerator (for AI-powered updates). Formats the document content
    in a structured way based on the document's category.

    Args:
        kb_document: The KB document to format

    Returns:
        Formatted string representation of the document content
    """
    extraction = kb_document.extraction_output
    category = kb_document.category.value

    if category == "troubleshooting":
        return f"""### Problem Description
{extraction.problem_description}

### Environment
- **System**: {extraction.system_info}
- **Version**: {extraction.version_info}
- **Environment**: {extraction.environment}

### Symptoms
{extraction.symptoms}

### Root Cause
{extraction.root_cause}

### Solution
{extraction.solution_steps}

### Prevention
{extraction.prevention_measures}

### Related Links
{extraction.related_links or 'None'}"""

    elif category == "processes":
        return f"""### Overview
{extraction.process_overview}

### Prerequisites
{extraction.prerequisites}

### Step-by-Step Process
{extraction.process_steps}

### Validation
{extraction.validation_steps}

### Troubleshooting
{extraction.common_issues}

### Related Processes
{extraction.related_processes or 'None'}"""

    elif category == "decisions":
        return f"""### Context
{extraction.decision_context}

### Decision
{extraction.decision_made}

### Rationale
{extraction.reasoning}

### Alternatives Considered
{extraction.alternatives}

### Consequences
#### Positive
{extraction.positive_consequences}

#### Negative
{extraction.negative_consequences}

### Implementation Notes
{extraction.implementation_notes or 'None'}"""

    elif category == "references":
        return f"""### Question Context
{extraction.question_context}

### Resource Type
{extraction.resource_type}

### Primary Resource
{extraction.primary_resource}

### Additional Resources
{extraction.additional_resources or 'None'}

### Resource Description
{extraction.resource_description}

### Usage Context
{extraction.usage_context}

### Access Requirements
{extraction.access_requirements or 'None'}

### Related Topics
{extraction.related_topics or 'None'}"""

    elif category == "general":
        return f"""### Summary
{extraction.summary}

### Key Topics
{extraction.key_topics}

### Key Points
{extraction.key_points}

### Mentioned Resources
{extraction.mentioned_resources or 'None'}

### Participants Context
{extraction.participants_context}"""

    else:
        return "Content format not available for this category"
