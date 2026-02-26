# Knowledge Base QnA Feature Implementation

This document outlines the implementation of the Knowledge Base QnA feature for Archie, which allows users to query the knowledge base and receive answers based on the KB content.

## Overview

The Knowledge Base QnA feature enables users to:
1. Submit questions about topics covered in the knowledge base
2. Get accurate answers based strictly on available KB documents
3. See the sources of information used to generate the answer
4. Access direct links to the source documents for further reading

## Design Philosophy

The implementation follows a **simple, LLM-centric approach**:
- Minimal hard-coded logic
- Let the AI do the heavy lifting
- Simple keyword-based filtering, AI does semantic understanding
- Strict grounding to prevent hallucination

## Implementation Details

### 1. Simplified Prompt System (`app/ai_core/prompts/query.py`)

**System Prompt (`QNA_SYSTEM_PROMPT`)**:
- Ultra-strict instructions: answer ONLY from provided documents
- Two possible outputs: found with citation OR "I don't have information about this"
- Explicit prohibition against suggestions or general knowledge
- No assumptions or extrapolation allowed

**User Prompt (`create_qna_prompt`)**:
- Clean document list with titles, categories, and content
- Simple instructions: search docs → answer or say "not found"
- No complex scoring interpretations or special case handling
- Let LLM determine document relevance semantically

### 2. Lightweight Relevance Scoring (`_compute_document_relevance`)

Simple keyword-based scoring to provide rough filtering:
- **Exact query in title**: +1.5
- **Full query phrase in content**: +1.0
- **Title keyword matches**: +0.5 per keyword
- **Multi-word phrases (2-word)**: +0.5 in content, +0.8 in title
- **Individual keywords in content**: +0.15 per keyword
- **Category match**: +0.3
- **Tag matches**: +0.25 per tag

**Key parameters**:
- `MAX_DOCS`: 30 (increased to give LLM more context)
- `MIN_RELEVANCE`: 0.1 (low threshold, let LLM filter)
- **Philosophy**: Keyword matching is just a rough filter; LLM does real relevance determination

### 3. KB Orchestrator (`query_knowledge_base` method)

**Pipeline**:
1. Fetch all KB documents from GitHub repository
2. Compute basic relevance scores using keyword matching
3. Select top 30 documents (or all if fewer) above 0.1 threshold
4. Pass documents to LLM with strict prompt
5. Parse LLM response and extract cited sources
6. Return formatted response with answer and sources

**Logging enhancements**:
- Top 10 documents with paths and scores for debugging
- Clear visibility into what documents were considered

### 4. API Integration (`app/api/routes/kb.py`)

**Endpoint**: `POST /api/kb/query`
- Takes `query` string as input
- Returns `KBQueryResponse` with answer, sources, and metadata
- Proper error handling for GitHub access failures

## Key Features

### Anti-Hallucination Measures
1. **Strict system prompt**: Explicit prohibition against making up information
2. **Binary output**: Either found with citation OR explicit "not found" message
3. **No helpful suggestions**: LLM cannot offer alternatives or generic advice
4. **Document grounding**: Must cite specific documents in answer

### Generic & Maintainable
- No hard-coded patterns for specific information types (URLs, emails, etc.)
- No assumptions about query types or domain
- Simple scoring logic that's easy to understand and adjust
- Works for any type of query without special cases

### LLM-Centric
- LLM reads and understands documents semantically
- LLM determines if documents actually answer the question
- LLM handles extraction of specific information (URLs, values, etc.)
- Keyword scoring is just a rough pre-filter

## Usage

### API Request Example

```python
import requests
import json

response = requests.post(
    "http://localhost:8001/api/kb/query",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"query": "What is the url of the github onboarding link?"})
)

result = response.json()
print(result["answer"])
print(f"Sources: {len(result['sources'])}")
```

### Expected Behaviors

**When information is found**:
```json
{
  "status": "success",
  "query": "How do I create a service user?",
  "answer": "According to [Gerrit Service User Creation], you need...\n\nSources: [Gerrit Service User Creation]",
  "sources": [...],
  "total_sources": 1
}
```

**When information is NOT found**:
```json
{
  "status": "success",
  "query": "What is the url of the github onboarding link?",
  "answer": "I don't have information about this in the knowledge base",
  "sources": [],
  "total_sources": 0
}
```

## Relevance Scoring

### Maximum Possible Score
Theoretically unbounded, depends on query complexity:
- **Simple queries** (2-3 keywords): Max ~4-5
- **Complex queries** (5+ keywords): Max ~6-7+
- **Practical good match range**: 1.5 - 5.0
- **Current threshold**: 0.1 (intentionally very low)

### Example Score Calculation
Query: "github onboarding"
- Exact in title: +1.5
- Full phrase in content: +1.0
- Title keywords (2): +1.0
- Phrase in title: +0.8
- Individual keywords: +0.3
- **Total**: ~4.6

## Integration with Streamlit

The feature integrates with the Streamlit chat interface via intent classification:
- User questions should be classified as `kb_query` action
- Backend executes KB query and returns results
- Frontend formats response with sources section

**Note**: Ensure intent classifier routes questions to `kb_query` rather than `chat_only` to use KB functionality.

## Testing

Test module: `tests/test_kb_qna.py`
- Basic structure validation
- Response format verification
- Run with: `pytest tests/test_kb_qna.py -v`

## Future Improvements

Potential enhancements:

1. **Embedding-based search**: Vector embeddings for better semantic matching
2. **Hybrid search**: Combine keyword + embedding scores
3. **Conversation memory**: Support follow-up questions with context
4. **User feedback**: Collect thumbs up/down on answers to improve
5. **Result caching**: Cache frequent questions for performance
6. **Dynamic document limits**: Adjust based on document lengths

## Troubleshooting

### Issue: Wrong documents being returned
- Check logs for top 10 documents and their scores
- Verify document contains query keywords or phrases
- May need to adjust scoring weights

### Issue: LLM provides generic advice instead of "not found"
- Verify system prompt strictness
- Check that documents are actually being passed
- Ensure query is routed to `/api/kb/query` not general chat

### Issue: Correct document exists but not returned
- Check if document scores above 0.1 threshold
- Verify document is in top 30 by relevance
- May need to increase MAX_DOCS or adjust scoring
