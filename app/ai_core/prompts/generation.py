"""
Prompt 3: KB Draft / Update
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

This prompt generates or updates KB documents.
"""

# Shared formatting rules - used by both extraction and generation
FORMATTING_RULES = """
FORMATTING GUIDELINES

Choose the most appropriate format based on content:

1. Use bullet points or numbered lists when:
   - There are distinct, separate items (like multiple decisions)
   - Items are enumerated explicitly in the source
   - Content is a checklist or sequential steps

2. Use prose paragraphs when:
   - Content is explanatory or contextual
   - Ideas flow naturally together
   - There's a single main point or narrative

3. CRITICAL - When using lists, each item MUST be on its own line:
   - NEVER inline items like "1) item. 2) item. 3) item."
   - NEVER use semicolons to separate items on one line
   - Each item gets its own line with proper markdown (- or 1.)

Let the content dictate the format. Use your judgment.

WRONG - inline list:
1) First. 2) Second. 3) Third.

CORRECT - proper list:
1. First
2. Second
3. Third
"""

# YAML formatting rules for frontmatter generation
YAML_FORMATTING_RULES = """
YAML FRONTMATTER RULES (CRITICAL)

When generating YAML frontmatter (the section between --- markers), follow these rules STRICTLY:

1. **String Values with Special Characters MUST be Properly Formatted**
   - If a value contains colons (:), quotes ("), apostrophes ('), or hashes (#), use literal block scalar
   - Use the pipe symbol (|) for multi-line or complex strings
   - Example:
     title: "Simple title without special chars"
     ai_reasoning: |
       This text can have: colons, "quotes", and other special characters
       without causing YAML parsing errors

2. **Multi-line Strings - ALWAYS Use Literal Block Scalar**
   - For any multi-line content, use the pipe (|) symbol
   - This preserves line breaks and doesn't require escaping
   - Indent content by 2 spaces after the pipe
   - Example:
     ai_reasoning: |
       First line with "quotes"
       Second line with colons: like this
       Third line is fine too

3. **Simple Single-line Strings**
   - For short, simple strings without special characters, use double quotes
   - Example: title: "Fix deployment errors"
   
4. **Tags Must Be Properly Formatted**
   - Each tag in quotes, comma-separated in array format
   - Example: tags: ["terraform", "github-actions", "linting"]

5. **Never Use Flow-Style for Complex Strings**
   - WRONG: ai_reasoning: 'Text with "quotes" causes: errors'
   - WRONG: ai_reasoning: "Text with nested \"quotes\" and: colons"
   - RIGHT: Use literal block scalar (|) for anything complex

COMMON YAML MISTAKES TO AVOID

❌ WRONG (causes parsing errors):
ai_reasoning: 'This explains: run "command" first'
ai_reasoning: "When jobs are delayed: run \"terraform run\" and proceed"

✓ CORRECT (use literal block scalar):
ai_reasoning: |
  This explains: run "command" first
  
ai_reasoning: |
  When jobs are delayed: run "terraform run" and proceed

❌ WRONG (mixing quote styles):
title: 'Fix "linter" errors'

✓ CORRECT (use simple double quotes for short strings):
title: "Fix linter errors"

REMEMBER: When in doubt, use literal block scalar (|) for any string that:
- Contains colons (:)
- Contains quotes (" or ')
- Contains hashes (#)
- Spans multiple lines
- Is longer than one sentence
"""

GENERATION_PROMPT = """
You are a technical writer creating knowledge base documentation.

## Task
{task_type}  # "Create new document" or "Update existing document"

## Source Thread
{conversation_content}

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

""" + YAML_FORMATTING_RULES + """

""" + FORMATTING_RULES + """

## Markdown Template
{template}

Generate the complete markdown document following these guidelines.
"""

UPDATE_PROMPT = """
You are a technical writer updating knowledge base documentation.

## Task
Update the existing KB document based on new information.

## Existing Document
{existing_content}

## New Information
{new_information}

""" + YAML_FORMATTING_RULES + """

## Update Guidelines
CRITICAL: Follow these rules when updating KB documents:

1. **DO NOT Add New Sections**
   - DO NOT append a "## New Information" section or any similar new section at the end
   - DO NOT create duplicate sections with slightly different names
   - Instead, merge the new information INTO the appropriate EXISTING sections only

2. **Merge Content Into Existing Sections**
   - Identify which existing section(s) the new information belongs to
   - Update only those specific fields/lines within existing sections
   - For reference documents: if only a link changed, update ONLY that specific link field (e.g., "Primary Resource")
   - Keep all other content unchanged

3. **Preserve Title and Tags**
   - DO NOT change the title unless the meaning actually changes
   - DO NOT change tags unless the meaning actually changes
   - If content is merely paraphrased but keeps the same meaning, DO NOT update it

4. **Preserve Formatting and Structure**
   - Maintain the existing markdown structure exactly
   - Keep the same bullet point style (- or *)
   - Preserve all section headers and hierarchy
   - Do not remove or add sections

5. **Ignore Frontmatter Metadata**
   - DO NOT update any YAML frontmatter fields (between --- delimiters)
   - Frontmatter fields like last_updated, ai_confidence, etc. are handled programmatically
   - Only update the document body content

6. **Formatting Compliance**
   - ONE item per line - never combine multiple bullets or numbered items
   - Use hyphens (-) for bullets, numbers (1. 2. 3.) for ordered lists
   - No special characters (•, ◦, ▪)

7. **Minimal Changes**
   - Make the smallest possible changes that incorporate the new information
   - Preserve unchanged sections entirely
   - Only modify what is necessary

## Example (Reference Document)
If the new information shows an updated link from:
- Old: https://wiki.example.page/infra-service-responsibles
- New: https://wiki.example.page/infra-service/responsibles

Then ONLY update the "Primary Resource" field:
```
## Primary Resource
https://wiki.example.page/infra-service/responsibles
```

Do NOT add a "## New Information" section. Do NOT duplicate existing sections.

## Required Output
Provide the complete updated markdown document with:
- New information merged into appropriate existing sections (NOT as separate sections)
- Only the necessary content changes applied
- All frontmatter metadata unchanged (will be updated programmatically)
- No duplicate or new section headers
"""

# Template sections for different KB types
TEMPLATE_SECTIONS = {
    "troubleshooting": ["Problem", "Root Cause", "Solution", "Prevention"],
    "decision": ["Context", "Decision", "Rationale", "Consequences"],
    "howto": ["Overview", "Prerequisites", "Steps", "Verification"],
    "architecture": ["Context", "Design", "Tradeoffs", "Related"],
    "best_practice": ["Overview", "Practice", "Examples", "Anti-patterns"],
}
