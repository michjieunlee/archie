"""
Shared Utility Functions

Common helper functions used across multiple modules.
"""

import re
import yaml
import logging
from typing import Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


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


def sanitize_yaml_string(value: str) -> str:
    """
    Sanitize a string value to be YAML-safe using literal block scalar format.
    
    This function converts any string into a YAML-safe format using the literal
    block scalar syntax (|), which preserves special characters without escaping.
    
    Args:
        value: String value to sanitize
        
    Returns:
        YAML-safe string with literal block scalar syntax
    """
    if not value:
        return '""'
    
    # If string contains special YAML characters or is multiline, use literal block scalar
    has_special_chars = any(char in value for char in [':', '"', "'", '#', '\n'])
    
    if has_special_chars or len(value.split('\n')) > 1:
        # Use literal block scalar (|) with 2-space indentation
        lines = value.split('\n')
        indented_lines = ['  ' + line for line in lines]
        return '|\n' + '\n'.join(indented_lines)
    
    # For simple strings, use double quotes
    return f'"{value}"'


def fix_yaml_frontmatter(content: str) -> str:
    """
    Automatically fix common YAML frontmatter issues.
    
    This function programmatically fixes YAML frontmatter by:
    1. Extracting the frontmatter and body
    2. Parsing the YAML (if possible)
    3. Re-serializing with proper formatting using literal block scalars
    4. Reconstructing the markdown document
    
    Args:
        content: Markdown content with potentially invalid YAML frontmatter
        
    Returns:
        Markdown content with fixed YAML frontmatter
    """
    if not content.startswith("---"):
        logger.warning("Content does not start with YAML frontmatter marker")
        return content
    
    try:
        # Extract frontmatter and body
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if not match:
            logger.warning("Could not find valid frontmatter boundaries")
            return content
        
        frontmatter_yaml = match.group(1)
        body = match.group(2)
        
        # Try to parse the YAML first
        try:
            data = yaml.safe_load(frontmatter_yaml)
        except yaml.YAMLError:
            # If parsing fails, try to fix common issues line by line
            logger.info("YAML parsing failed, attempting line-by-line fix")
            data = {}
            current_key = None
            current_value = []
            
            for line in frontmatter_yaml.split('\n'):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Check if this is a key-value line
                if ':' in line_stripped and not line_stripped.startswith('-'):
                    # Save previous key if exists
                    if current_key:
                        data[current_key] = '\n'.join(current_value).strip()
                        current_value = []
                    
                    # Parse new key-value
                    parts = line_stripped.split(':', 1)
                    current_key = parts[0].strip()
                    if len(parts) > 1:
                        value = parts[1].strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        current_value.append(value)
                else:
                    # Continuation of previous value
                    if current_key:
                        current_value.append(line_stripped)
            
            # Save last key
            if current_key:
                data[current_key] = '\n'.join(current_value).strip()
        
        # Reconstruct YAML with proper formatting
        fixed_lines = []
        for key, value in data.items():
            if isinstance(value, list):
                # Handle lists (like tags)
                formatted_list = ', '.join([f'"{item}"' for item in value])
                fixed_lines.append(f'{key}: [{formatted_list}]')
            elif isinstance(value, (int, float)):
                # Numbers don't need quotes
                fixed_lines.append(f'{key}: {value}')
            elif isinstance(value, str):
                # Use sanitize function for strings
                sanitized = sanitize_yaml_string(value)
                if sanitized.startswith('|'):
                    # Multi-line format
                    fixed_lines.append(f'{key}: {sanitized}')
                else:
                    # Single-line format
                    fixed_lines.append(f'{key}: {sanitized}')
            else:
                # Fallback for other types
                fixed_lines.append(f'{key}: {yaml.dump(value, default_flow_style=True).strip()}')
        
        fixed_frontmatter = '\n'.join(fixed_lines)
        fixed_content = f'---\n{fixed_frontmatter}\n---\n{body}'
        
        logger.info("Successfully fixed YAML frontmatter")
        return fixed_content
        
    except Exception as e:
        logger.error(f"Error fixing YAML frontmatter: {e}", exc_info=True)
        return content


def validate_yaml_frontmatter(content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate YAML frontmatter in markdown content.
    
    Args:
        content: Markdown content with YAML frontmatter
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if YAML is valid, False otherwise
        - error_message: Error description if invalid, None if valid
    """
    if not content.startswith("---"):
        return False, "Content does not start with YAML frontmatter marker (---)"
    
    try:
        # Extract frontmatter using regex
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return False, "Could not find valid frontmatter boundaries (---...---)"
        
        frontmatter_yaml = match.group(1).strip()
        
        # Try to parse the YAML
        if frontmatter_yaml:
            yaml.safe_load(frontmatter_yaml)
        
        logger.debug("YAML frontmatter validation passed")
        return True, None
        
    except yaml.YAMLError as e:
        error_msg = f"YAML parsing error: {str(e)}"
        logger.warning(f"YAML validation failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during YAML validation: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


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