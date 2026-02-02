"""
Prompt 1: KB Candidate Extraction
Owner: ③ AI Core · Compliance · Knowledge Logic Owner

This prompt extracts KB candidates from Slack threads.
"""

EXTRACTION_PROMPT = """
You are an expert at identifying valuable knowledge from team conversations.

Analyze the following Slack thread and determine if it contains knowledge worth documenting.

## Thread Content
{thread_content}

## Analysis Criteria
1. **Troubleshooting**: Does this thread document a problem and its solution?
2. **Decision Making**: Does it capture important technical or business decisions with rationale?
3. **How-to Knowledge**: Does it explain how to do something that others might need?
4. **Architecture/Design**: Does it discuss system design or architectural choices?
5. **Best Practices**: Does it share tips, tricks, or best practices?

## Output Format (JSON)
{{
    "is_kb_candidate": true/false,
    "kb_type": "troubleshooting|decision|howto|architecture|best_practice|not_kb_worthy",
    "confidence_score": 0.0-1.0,
    "title_suggestion": "Suggested title for KB document",
    "summary": "Brief summary of the knowledge",
    "key_points": ["Key point 1", "Key point 2", ...],
    "reasoning": "Explanation of why this is/isn't KB-worthy"
}}

Analyze the thread and respond with JSON only.
"""

# Few-shot examples for better extraction
EXTRACTION_EXAMPLES = [
    {
        "thread": "User A: API keeps timing out\nUser B: Check if you're hitting rate limits\nUser A: That was it! Added retry with backoff and it works now",
        "expected": {
            "is_kb_candidate": True,
            "kb_type": "troubleshooting",
            "title_suggestion": "Handling API Rate Limit Timeouts",
        },
    },
    # TODO: Add more examples
]
