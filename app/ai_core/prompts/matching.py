"""
Prompt 2: KB Matching (create / update / ignore)
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

This prompt compares with existing KB to decide create/update/ignore.
"""

MATCHING_PROMPT = """
You are a knowledge base curator. Determine if new content should create a new document,
update an existing document, or be ignored.

## New Content
Title: {candidate_title}
Summary: {candidate_summary}
Key Points:
{candidate_key_points}

## Existing Knowledge Base Documents
{existing_docs}

## Decision Criteria
1. **CREATE**: Content is valuable and doesn't overlap significantly with existing docs
2. **UPDATE**: Content adds valuable information to an existing document
3. **IGNORE**: Content is duplicate, too minor, or not valuable enough

## Output Format (JSON)
{{
    "action": "create|update|ignore",
    "confidence_score": 0.0-1.0,
    "reasoning": "Explanation of the decision",
    "matched_document_path": "path/to/doc.md (only if UPDATE)",
    "suggested_path": "knowledge/category/filename.md (only if CREATE)",
    "suggested_category": "category name (only if CREATE)"
}}

Analyze and respond with JSON only.
"""
