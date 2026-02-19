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

## GitHub Markdown Guidelines
When writing KB documents, follow these strict formatting rules:

### Bullet Points
- DO NOT use special characters that GitHub cannot render (e.g., •, ◦, ▪)
- Use standard markdown bullet points with hyphens (-) or asterisks (*)
- Example CORRECT:
  - First point
  - Second point
- Example INCORRECT:
  • First point
  • Second point

### Numberings and Lists
- For numbered lists with complex conditions, use proper line breaks
- DO NOT use inline numbering like "(1) condition, (2) condition"
- Example CORRECT:
  1. First condition
  2. Second condition
  3. Third condition
- Example INCORRECT:
  "when all of the following apply: (1) Server is gerrit-prod, (2) Requester originates within Team Dev"

### Masked Values
- Only include masked values if absolutely necessary for understanding the context
- Prefer generic descriptions over specific masked URLs, names, or IDs
- Remove unnecessary masked references that don't add clarity
- Example: Instead of "use https://gerrit.your.corp/ as the 'MASKED_PERSON Instance Name' URL", use "use the instance URL https://gerrit.your.corp/"

### High Readability
- Use clear section headers
- Break long sentences into multiple lines or bullet points
- Use code blocks for commands, URLs, or technical references
- Add spacing between sections for better readability

### Related Links Section
- ALWAYS format links with bullet points using hyphens (-) or asterisks (*)
- Each link must be on a separate line starting with a bullet point marker
- Example CORRECT:
  ## Related Links
  
  - Jenkins job: https://jenkins.your.corp/view/project/job/project_ci_docker_push/
  - Build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1843/console
- Example INCORRECT (no bullet points - will render as single line):
  ## Related Links
  Jenkins job: https://jenkins.your.corp/view/project/job/project_ci_docker_push/
  Build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1843/console

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

6. **GitHub Markdown Compliance**
   - Ensure any new content uses proper GitHub markdown (no • bullets)
   - Use line breaks for numbered conditions, not inline "(1), (2)" format
   - Remove unnecessary masked values
   - ALWAYS format Related Links section with bullet points (- or *) on each line
   - Example: Each link must start with "- " to render properly on GitHub

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
