# KB Document Writing Guidelines

This document outlines the guidelines for writing and updating Knowledge Base (KB) documents in the Archie system.

## Overview

KB documents are written in GitHub-flavored Markdown and must follow specific formatting rules to ensure consistency, readability, and proper rendering on GitHub.

## Writing New KB Documents

When creating new KB documents, follow these guidelines:

### 1. GitHub Markdown Compliance

#### Bullet Points
**DO NOT** use special characters that GitHub cannot render properly.

❌ **INCORRECT:**
```markdown
• First point
• Second point
◦ Sub-point
▪ Another sub-point
```

✅ **CORRECT:**
```markdown
- First point
- Second point
  - Sub-point
  - Another sub-point
```

**Rule:** Always use hyphens (`-`) or asterisks (`*`) for bullet points.

#### Numberings and Lists

When listing multiple conditions or steps, use proper line breaks instead of inline numbering.

❌ **INCORRECT:**
```markdown
The request qualifies when all of the following apply: (1) Server is gerrit-prod, (2) Requester/use case originates within Team Dev or Quality Engineering org, and (3) Request type is access/configuration (not operations).
```

✅ **CORRECT:**
```markdown
The request qualifies when all of the following apply:

1. Server is gerrit-prod
2. Requester/use case originates within Team Dev or Quality Engineering org
3. Request type is access/configuration (not operations)
```

**Rule:** Use numbered lists with line breaks for multiple conditions, not inline `(1), (2), (3)` format.

### 2. Masked Values

Only include masked values when they are essential for understanding the context.

❌ **INCORRECT (unnecessary masking):**
```markdown
For ServiceNow tickets:
1. Use https://gerrit.your.corp/ as the 'MASKED_PERSON Instance Name' URL
2. Include user IDs and detailed steps
3. If any condition does not apply, forward the request to MASKED_PERSON Gerrit maintainers on the same distribution list
```

✅ **CORRECT (essential context only):**
```markdown
For ServiceNow tickets:
1. Use the instance URL https://gerrit.your.corp/
2. Include user IDs and detailed steps
3. If any condition does not apply, forward the request to Gerrit maintainers
```

**Rule:** Remove masked placeholders that don't add clarity or understanding.

### 3. High Readability

#### Use Clear Section Headers
```markdown
## Problem Description
## Root Cause
## Solution Steps
## Prevention Measures
```

#### Break Long Sentences
Instead of:
```markdown
To resolve the database connection timeout issue, you need to first check the connection pool settings in the application configuration file, then verify the network connectivity between the application server and the database server, and finally ensure that the database server has sufficient resources and is not under heavy load.
```

Use:
```markdown
To resolve the database connection timeout issue:

1. Check the connection pool settings in the application configuration file
2. Verify the network connectivity between the application server and the database server
3. Ensure that the database server has sufficient resources and is not under heavy load
```

#### Use Code Blocks
For commands, URLs, or technical references:
```markdown
Run the following command:
```bash
npm install --save-dev eslint
```

Access the application at: `http://localhost:3000`
```

#### Add Spacing
```markdown
## Section 1

Content for section 1 goes here.

## Section 2

Content for section 2 goes here.
```

#### Format Related Links Properly

Always use bullet points (`-`) for links in the Related Links section.

❌ **INCORRECT (no bullet points):**
```markdown
## Related Links
Jenkins job: https://jenkins.your.corp/view/project/job/project_ci_docker_push/
Timed-out build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1843/console
Retriggered build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1845/console
```

✅ **CORRECT (with bullet points and inline links):**
```markdown
## Related Links

- Jenkins job: https://jenkins.your.corp/view/project/job/project_ci_docker_push/
- Timed-out build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1843/console
- Retriggered build log: https://jenkins.your.corp/view/project/job/project_ci_docker_push/1845/console
```

✅ **CORRECT (with bullet points and Markdown link syntax):**
```markdown
## Related Links

- [Jenkins job](https://jenkins.your.corp/view/project/job/project_ci_docker_push/)
- [Timed-out build log (1843)](https://jenkins.your.corp/view/project/job/project_ci_docker_push/1843/console)
- [Retriggered build log (1845)](https://jenkins.your.corp/view/project/job/project_ci_docker_push/1845/console)
```

**Rule:** Always start each link line with a hyphen (`-`) or asterisk (`*`). Without bullet point markers, GitHub will render multiple lines as a single continuous paragraph.

## Updating Existing KB Documents

When updating KB documents, follow these strict rules:

### 1. Selective Updates Only

**Update ONLY lines that change the MEANING of the content.**

#### Example: Should NOT Update

Original:
```markdown
The service will restart automatically after configuration changes.
```

Proposed Update (same meaning, just rephrased):
```markdown
Configuration changes will trigger an automatic service restart.
```

**Decision:** ❌ Do NOT update - the meaning is the same.

#### Example: Should Update

Original:
```markdown
The service will restart automatically after configuration changes.
```

New Information:
```markdown
Manual restart is required after configuration changes.
```

**Decision:** ✅ Update - the meaning has changed from automatic to manual.

### 2. Do Not Change Tags or Titles

Unless the change affects the meaning, preserve the original tags and titles.

❌ **INCORRECT:**
```markdown
Original title: "Database Connection Timeout Issues"
Updated title: "Resolving Database Connection Timeouts"
```

✅ **CORRECT:**
```markdown
Keep title: "Database Connection Timeout Issues"
```

**Rule:** Only change titles/tags if the document's scope or focus has fundamentally changed.

### 3. Preserve Formatting

Maintain the existing markdown structure:
- Keep the same bullet point style (if using `-`, continue with `-`)
- Preserve section headers and hierarchy
- Maintain indentation patterns

### 4. Minimal Changes

Make the smallest possible changes that incorporate new information:

```markdown
## Original
The API supports JSON format for all requests.

## New Information
The API now supports both JSON and XML formats.

## Updated (Minimal Change)
The API supports JSON and XML formats for all requests.
```

## AI Prompt Integration

These guidelines are integrated into the AI generation prompts located in `app/ai_core/prompts/generation.py`:

- `GENERATION_PROMPT`: Used for creating new KB documents with AI assistance
- `UPDATE_PROMPT`: Used for AI-powered updates to existing KB documents

### Implementation Status

✅ **IMPLEMENTED** - The UPDATE_PROMPT is fully integrated into the system:

1. **KBGenerator** (`app/ai_core/generation/kb_generator.py`):
   - New `async def update_markdown()` method uses UPDATE_PROMPT
   - Intelligently merges new content with existing documents
   - Follows selective update guidelines (only changes that affect meaning)

2. **Orchestrator** (`app/services/kb_orchestrator.py`):
   - Detects UPDATE actions from KBMatcher
   - Fetches existing document content
   - Calls `update_markdown()` for AI-powered merging
   - Falls back to `generate_markdown()` if update fails

3. **Shared Utilities** (`app/utils/helpers.py`):
   - `format_kb_document_content()` provides consistent formatting
   - Shared between KBMatcher and KBGenerator
   - Reduces code duplication

### Update Flow

When KBMatcher determines content should UPDATE an existing document:

```
1. Matcher returns UPDATE action with document path
2. Orchestrator fetches existing document content from GitHub
3. Generator.update_markdown() is called with:
   - existing_content: Current markdown of the document
   - new_document: Newly extracted KB information
4. AI uses UPDATE_PROMPT to merge intelligently:
   - Only updates lines that change meaning
   - Preserves tags, titles, formatting
   - Makes minimal necessary changes
5. If AI update fails, falls back to generate_markdown()
6. Updated content is committed via GitHub PR
```

The prompts enforce these rules automatically during document generation and updates.

## Template Structure

KB documents follow category-specific templates located in `app/ai_core/templates/`:

- `troubleshooting.md`: For problem-solution documents
- `process.md`: For workflow and procedure documents
- `decision.md`: For architectural and design decisions
- `reference.md`: For technical reference materials
- `general.md`: For general knowledge articles

Each template includes:
- Frontmatter with metadata (title, tags, difficulty, etc.)
- Structured sections appropriate for the category
- Placeholders for content variables

## Example: Complete KB Document

```markdown
---
title: "Resolving npm Install Failures"
category: "troubleshooting"
tags: ["npm", "node", "dependency-management", "build-issues"]
difficulty: "intermediate"
created_date: "2026-02-15"
last_updated: "2026-02-15"
---

# Resolving npm Install Failures

## Problem Description

Users encounter errors when running `npm install` in the project directory.

## Environment

- **System**: macOS, Linux, Windows
- **Version**: Node.js 18+, npm 9+
- **Environment**: Development

## Symptoms

The following error appears during installation:

```
npm ERR! code ERESOLVE
npm ERR! ERESOLVE could not resolve
```

## Root Cause

Dependency version conflicts in package.json cause npm to fail resolution.

## Solution

Follow these steps to resolve the issue:

1. Clear the npm cache:
   ```bash
   npm cache clean --force
   ```

2. Delete existing dependencies:
   ```bash
   rm -rf node_modules package-lock.json
   ```

3. Reinstall with legacy peer deps:
   ```bash
   npm install --legacy-peer-deps
   ```

## Prevention

To prevent future conflicts:

- Keep dependencies updated regularly
- Use exact versions in package.json when possible
- Test dependency updates in a separate branch

## Related Links

- [npm cache issues](link-to-related-kb)
- [Node version management](link-to-related-kb)
```

## Validation

Before submitting a KB document:

1. ✅ Check for invalid bullet characters (•, ◦, ▪)
2. ✅ Verify no inline numbering like "(1), (2), (3)"
3. ✅ Remove unnecessary masked values
4. ✅ Ensure proper spacing and readability
5. ✅ Verify code blocks are properly formatted
6. ✅ Confirm all sections are complete

## Summary

Following these guidelines ensures:
- Consistent formatting across all KB documents
- Proper rendering on GitHub
- High readability for users
- Minimal maintenance overhead for updates
- Clear and actionable information