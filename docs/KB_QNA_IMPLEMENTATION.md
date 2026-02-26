# Knowledge Base QnA Feature Implementation

This document outlines the implementation of the Knowledge Base QnA feature for Archie, which allows users to query the knowledge base and receive answers based on the KB content.

## Overview

The Knowledge Base QnA feature enables users to:
1. Submit questions about topics covered in the knowledge base
2. Get comprehensive answers based on relevant KB documents
3. See the sources of information used to generate the answer
4. Access direct links to the source documents for further reading

## Implementation Details

### 1. Prompt System

Created a specialized prompt system for QnA functionality:
- `app/ai_core/prompts/query.py` contains:
  - System prompt (`QNA_SYSTEM_PROMPT`) with instructions for LLM behavior
  - Helper function (`create_qna_prompt`) to format questions and KB documents for the LLM
  - Support for document relevance scores to help the LLM prioritize information

### 2. Document Relevance Ranking

Implemented a simple but effective document relevance ranking algorithm:
- `_compute_document_relevance` method ranks documents based on:
  - Title keyword matches (highest weight)
  - Full phrase matches in content
  - Individual keyword matches in content
  - Category and tag matches
  - Returns documents sorted by relevance score

### 3. KB Orchestrator Enhancement

Updated the KB orchestrator to handle knowledge base queries:
- `query_knowledge_base` method now:
  - Fetches all KB documents from GitHub
  - Computes relevance scores for documents based on the query
  - Selects the most relevant documents
  - Creates a specialized prompt with documents and relevance scores
  - Generates an answer using the LLM
  - Formats the response with sources and relevance information

### 4. API Integration

Enhanced the API endpoint in `app/api/routes/kb.py`:
- Updated documentation to reflect the new functionality
- Improved the response format with better examples
- Ensured proper error handling and logging

## Usage

To use the KB QnA feature:

```python
# API request example
import requests
import json

response = requests.post(
    "http://localhost:8001/api/kb/query",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"query": "How do I fix API timeout errors?"})
)

result = response.json()
print(result["answer"])
print(f"Sources: {len(result['sources'])}")
```

## Example Response

```json
{
  "status": "success",
  "query": "How do I fix API timeout errors?",
  "answer": "Based on the knowledge base, API timeout errors can be resolved by increasing the connection timeout from 30s to 60s in the config.json file under the api.timeout setting.\n\nSources: [API Timeout Resolution]",
  "sources": [
    {
      "title": "API Timeout Resolution",
      "category": "troubleshooting",
      "excerpt": "To fix API timeout errors, increase the connection timeout from 30s to 60s in config.json.",
      "relevance_score": 0.95,
      "file_path": "troubleshooting/api-timeout.md",
      "github_url": "https://github.com/your-org/your-repo/blob/main/troubleshooting/api-timeout.md"
    }
  ],
  "total_sources": 1
}
```

## Future Improvements

Potential enhancements for the future:

1. **Embedding-based search**: Implement vector embeddings for more accurate semantic search
2. **Conversation memory**: Support follow-up questions using conversation context
3. **Multi-document reasoning**: Better handling of information spread across multiple documents
4. **User feedback loop**: Collect feedback on answer quality to improve relevance ranking
5. **Auto-categorization**: Dynamically filter documents by category based on query intent
6. **Result caching**: Cache frequent questions for improved performance

## Testing

A test module (`tests/test_kb_qna.py`) has been added with:
- Unit tests to validate the basic structure
- A manual test function for demonstration purposes