# API Endpoints Documentation

## Main Knowledge Base Endpoints

The service provides three main API endpoints for knowledge base management, all under the `/api/kb` prefix.

---

## 1. Update KB from Slack Messages

**Endpoint**: `GET /api/kb/from-slack`

**Description**: Fetch Slack messages from a channel, extract knowledge, and create a KB article.

**Query Parameters**:
- `channel_id` (optional): Slack channel ID. If not provided, uses the configured default.
- `from_datetime` (optional): Start datetime for message range (ISO 8601 format)
- `to_datetime` (optional): End datetime for message range (ISO 8601 format)
- `limit` (optional, default=100, max=100): Maximum number of messages to fetch

**Examples**:
```bash
# Fetch last 50 messages
GET /api/kb/from-slack?limit=50

# Fetch messages in date range
GET /api/kb/from-slack?from_datetime=2026-01-01T00:00:00Z&to_datetime=2026-01-05T23:59:59Z

# Fetch from specific channel
GET /api/kb/from-slack?channel_id=C123ABC456&limit=100
```

**Pipeline**:
1. Fetch Slack messages with automatic thread expansion
2. Mask PII data using SAP GenAI Orchestration V2
3. Extract KB using AI (categorization + structured extraction)
4. Match against existing KB (TODO: not yet implemented)
5. Generate KB document (TODO: not yet implemented)
6. Create GitHub PR (TODO: not yet implemented)

**Response Model**: `KBProcessingResponse`
```json
{
  "status": "success",
  "action": "create",
  "messages_fetched": 87,
  "kb_article_title": "Database Connection Troubleshooting",
  "kb_category": "troubleshooting",
  "ai_confidence": 0.85,
  "ai_reasoning": "This conversation contains...",
  "pr_url": null,
  "file_path": null
}
```

**Status Codes**:
- `200`: Success (with action: create/update/ignore)
- `500`: Internal server error

---

## 2. Update KB from Free Text

**Endpoint**: `POST /api/kb/from-text`

**Description**: Convert free text input into a KB article.

**Request Body**:
```json
{
  "text": "We had an issue with API timeout errors. The solution was to increase the connection timeout from 30s to 60s in the config file.",
  "title": "API Timeout Fix",
  "metadata": {
    "source": "manual",
    "author": "user123"
  }
}
```

**Parameters**:
- `text` (required): Free text input to process into KB
- `title` (optional): Title for the conversation
- `metadata` (optional): Additional metadata as key-value pairs

**Pipeline**:
1. Convert text to StandardizedConversation format
2. Mask PII data using SAP GenAI Orchestration V2
3. Extract KB using AI (categorization + structured extraction)
4. Match against existing KB (TODO: not yet implemented)
5. Generate KB document (TODO: not yet implemented)
6. Create GitHub PR (TODO: not yet implemented)

**Response Model**: `KBProcessingResponse`
```json
{
  "status": "success",
  "action": "create",
  "text_length": 142,
  "kb_article_title": "API Timeout Resolution",
  "kb_category": "troubleshooting",
  "ai_confidence": 0.92,
  "ai_reasoning": "Clear problem-solution structure...",
  "pr_url": null,
  "file_path": null
}
```

**Status Codes**:
- `200`: Success (with action: create/update/ignore)
- `500`: Internal server error

---

## 3. Query Knowledge Base (Q&A)

**Endpoint**: `POST /api/kb/query`

**Description**: Ask questions about the knowledge base and get answers with relevant sources.

**Request Body**:
```json
{
  "query": "How do I fix API timeout errors?",
}
```

**Parameters**:
- `query` (required): User's question about the knowledge base

**Pipeline**:
1. Parse and understand the query
2. Search KB repository using LLM-based semantic search (TODO: not yet implemented)
3. Rank and retrieve relevant articles
4. Generate natural language answer using LLM
5. Return formatted response with sources

**Response Model**: `KBQueryResponse`
```json
{
  "status": "success",
  "query": "How do I fix API timeout errors?",
  "answer": "Based on the knowledge base, API timeout errors can be resolved by increasing the connection timeout from 30s to 60s in the configuration file...",
  "sources": [
    {
      "title": "API Timeout Resolution",
      "category": "troubleshooting",
      "excerpt": "To fix API timeout errors, increase the connection timeout...",
      "relevance_score": 0.95,
      "file_path": "troubleshooting/api-timeout.md",
      "github_url": "https://github.com/.../troubleshooting/api-timeout.md"
    }
  ],
  "total_sources": 1
}
```

**Status Codes**:
- `200`: Success
- `500`: Internal server error

---

## Supporting Endpoints

### Health Check
**Endpoint**: `GET /health`

**Description**: Check if the service is running.

**Response**:
```json
{
  "status": "healthy",
  "service": "Archie"
}
```

### Slack Message Fetch (Low-level)
**Endpoint**: `GET /api/slack/fetch`

**Description**: Raw Slack conversation fetching (used internally by `/api/kb/from-slack`).

---

## Response Models

### KBProcessingResponse
Used by both `/from-slack` and `/from-text` endpoints.

```typescript
{
  status: "success" | "error"
  action: "create" | "update" | "ignore" | "error"
  reason?: string  // For ignore/error cases
  
  // KB article info
  kb_article_title?: string
  kb_category?: string
  ai_confidence?: number  // 0.0 - 1.0
  ai_reasoning?: string
  
  // GitHub PR info
  pr_url?: string
  file_path?: string
  
  // Metadata
  messages_fetched?: number  // For Slack
  text_length?: number       // For text input
}
```

### KBQueryResponse
Used by `/query` endpoint.

```typescript
{
  status: "success" | "error"
  query: string
  answer?: string
  sources: KBSearchSource[]
  total_sources: number
  reason?: string  // For error cases
}
```

### KBSearchSource
Individual search result in query response.

```typescript
{
  title: string
  category: string
  excerpt: string
  relevance_score: number  // 0.0 - 1.0
  file_path: string
  github_url: string
}
```

---

## Authentication

**Current**: No authentication (for hackathon demo)

**Future**: Should implement API key or OAuth authentication for production use.

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "status": "error",
  "action": "error",
  "reason": "Detailed error message here"
}
```

For HTTP errors (e.g., 500), FastAPI also includes:
```json
{
  "detail": "Failed to process: specific error message"
}
```

---

## Testing the API

### Using curl

```bash
# Test Slack fetch
curl "http://localhost:8000/api/kb/from-slack?limit=10"

# Test text input
curl -X POST "http://localhost:8000/api/kb/from-text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We fixed the database timeout by increasing pool size to 20.",
    "title": "Database Fix"
  }'

# Test query
curl -X POST "http://localhost:8000/api/kb/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to fix database issues?",
  }'
```

### Using FastAPI Swagger UI

Navigate to: `http://localhost:8000/docs`

---

## Implementation Status

✅ **Completed**:
- Main API endpoints structure
- Slack conversation fetching with thread expansion
- PII masking with SAP GenAI Orchestration V2
- KB extraction with AI (categorization + structured extraction)
- Request/response models
- Error handling

🚧 **TODO** (marked in code):
- KB matching against existing documents
- KB document generation (markdown with templates)
- GitHub PR creation
- KB search implementation (for Q&A)
- LLM-based answer generation (for Q&A)

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Integration Details](./API_INTEGRATION.md)
- [KB Repository Structure](./KB_REPOSITORY_STRUCTURE.md)
- [Implementation Plans](./IMPLEMENTATION_PLANS.md)