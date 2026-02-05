# Archie API Integration Guide

This document provides comprehensive API interfaces and data models for team integration, particularly for the AI Core team (③) and GitHub integration components.

## Data Models

### StandardizedThread (Primary Interface)

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

class SourceType(str, Enum):
    SLACK = "slack"
    FILE = "file" 
    TEXT = "text"

class StandardizedMessage(BaseModel):
    """Platform-agnostic message format."""
    id: str                           # Unique message identifier
    author_id: str                    # User/author identifier (may be masked)
    author_name: Optional[str] = None # Display name (may be None for privacy)
    content: str                      # Message text content
    timestamp: datetime               # Message timestamp
    is_masked: bool = False          # Whether PII masking was applied
    metadata: Dict[str, Any] = {}    # Additional platform-specific data

class StandardizedThread(BaseModel):
    """Platform-agnostic conversation thread format."""
    id: str                          # Unique thread identifier
    source: SourceType               # Input source (slack, file, text)
    source_url: Optional[str] = None # Original URL (for Slack threads)
    channel_id: str                  # Channel/context identifier
    channel_name: Optional[str] = None
    messages: List[StandardizedMessage]
    participant_count: int           # Number of unique participants
    created_at: datetime            # Thread start time
    last_activity_at: datetime      # Last message time
    metadata: Dict[str, Any] = {}   # Additional context data
```

### AI Processing Models

```python
class KBExtractionResult(BaseModel):
    """Result of KB extraction analysis."""
    thread_id: str
    is_kb_worthy: bool
    confidence_score: float          # 0.0 to 1.0
    reasoning: str                   # AI explanation
    suggested_title: str
    category: str                    # e.g., "troubleshooting", "process", "decision"
    tags: List[str]
    key_topics: List[str]
    estimated_value: str            # "high", "medium", "low"

class KBMatchResult(BaseModel):
    """Result of matching against existing KB."""
    action: str                     # "create", "update", "merge", "ignore"
    confidence_score: float
    reasoning: str
    related_documents: List[str]    # IDs of related existing documents
    merge_candidates: List[str]     # Documents that could be merged
    
class KBGenerationResult(BaseModel):
    """Result of KB document generation."""
    title: str
    content: str                    # Generated markdown content
    file_path: str                 # Suggested file path in KB repo
    category: str
    tags: List[str]
    metadata: Dict[str, Any]
    ai_confidence: float
    source_threads: List[str]      # Source thread IDs
```

## API Endpoints

### Input Processing Endpoints

#### 1. Slack Channel Scan
```http
POST /api/input/slack
Content-Type: application/json

{
    "workspace_url": "https://yourworkspace.slack.com",
    "channel_id": "C0AC762HXBQ", 
    "time_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-07T23:59:59Z"
    },
    "bot_token": "xoxb-your-token",
    "options": {
        "include_threads": true,
        "max_messages": 1000,
        "exclude_bots": true
    }
}
```

### GitHub KB Repository Endpoints

#### 1. Fetch Existing KB Repository
```http
POST /api/github/fetch-kb
Content-Type: application/json

{
    "repo_owner": "your-org",
    "repo_name": "knowledge-base", 
    "branch": "main",
    "github_token": "ghp_your-token",
    "options": {
        "include_categories": ["troubleshooting", "processes", "decisions"],
        "parse_markdown": true,
        "extract_metadata": true
    }
}
```

**Response:**
```json
{
    "status": "success",
    "kb_documents": [
        {
            "file_path": "troubleshooting/database/connection-issues.md",
            "title": "Database Connection Issues",
            "category": "troubleshooting", 
            "tags": ["database", "connection"],
            "content": "# Database Connection Issues\n\n## Overview\n...",
            "metadata": {
                "created_date": "2024-01-10",
                "last_updated": "2024-01-15",
                "difficulty": "intermediate"
            }
        }
    ],
    "repository_stats": {
        "total_documents": 45,
        "categories": {
            "troubleshooting": 20,
            "processes": 15,
            "decisions": 10
        },
        "last_update": "2024-01-15T14:30:00Z"
    }
}
```

#### 2. Create KB Update PR
```http
POST /api/github/create-kb-pr
Content-Type: application/json

{
    "repo_owner": "your-org",
    "repo_name": "knowledge-base",
    "github_token": "ghp_your-token",
    "operations": [
        {
            "type": "create",
            "file_path": "troubleshooting/slack/rate-limits.md",
            "content": "# Slack Rate Limit Handling\n\n...",
            "source_threads": ["slack-123", "slack-456"]
        },
        {
            "type": "update", 
            "file_path": "processes/deployment/ci-cd.md",
            "operation": "append",
            "section": "## New Deployment Steps",
            "content": "### Updated Process\n...",
            "source_threads": ["slack-789"]
        }
    ],
    "pr_metadata": {
        "title": "Knowledge Update: 3 documents from Slack conversations",
        "description": "Auto-generated KB update from Archie\n\n**AI Confidence**: 0.85\n**Source**: Slack #dev-team (Jan 15-22)",
        "branch_name": "kb-update-2024-01-22"
    }
}
```

### Joule Integration Endpoints

#### 1. Trigger Knowledge Extraction
```http
POST /api/joule/extract-knowledge
Content-Type: application/json

{
    "input_type": "slack" | "file" | "text",
    "input_data": {
        // Varies by input_type - same as /api/input/* endpoints
    },
    "user_context": {
        "user_id": "user123",
        "session_id": "session456",
        "preferences": {
            "categories": ["troubleshooting", "processes"],
            "confidence_threshold": 0.7
        }
    }
}
```

#### 2. Get Processing Status
```http
GET /api/joule/status/{job_id}
```

**Response:**
```json
{
    "job_id": "job_12345",
    "status": "processing" | "completed" | "failed",
    "progress": {
        "stage": "kb_matching" | "ai_processing" | "pr_creation",
        "percentage": 65,
        "estimated_remaining": "2 minutes"
    },
    "results": {
        "threads_processed": 12,
        "kb_documents_created": 3,
        "kb_documents_updated": 2,
        "pr_url": "https://github.com/org/kb/pull/123"
    },
    "errors": []
}
```

#### 3. Get Extraction Results
```http
GET /api/joule/results/{job_id}
```

**Response:**
```json
{
    "job_id": "job_12345",
    "extraction_summary": {
        "total_conversations": 15,
        "kb_worthy_conversations": 8,
        "average_confidence": 0.82,
        "processing_time": "3.5 minutes"
    },
    "generated_documents": [
        {
            "title": "Slack Integration Best Practices",
            "file_path": "processes/integrations/slack.md",
            "operation": "create",
            "confidence": 0.89,
            "ai_reasoning": "Conversation contains comprehensive troubleshooting steps...",
            "source_threads": ["slack-123", "slack-124"]
        }
    ],
    "pr_details": {
        "url": "https://github.com/org/kb/pull/123",
        "title": "Knowledge Update: 8 documents from Slack conversations",
        "files_changed": 8,
        "additions": 245,
        "deletions": 12
    }
}
```

**Response:**
```json
{
    "status": "success",
    "threads": [/* Array of StandardizedThread */],
    "stats": {
        "total_messages": 245,
        "total_threads": 12,
        "participants": 8,
        "processing_time_ms": 1250
    },
    "warnings": [
        "Hit rate limit, processing may be slower",
        "Some messages were filtered out due to permissions"
    ]
}
```

#### 2. File Upload Processing
```http
POST /api/input/file
Content-Type: multipart/form-data

file: [conversation_history.json]
format: "slack_export" | "csv" | "plain_text"
options: {
    "detect_threads": true,
    "group_by_time": 3600  // seconds
}
```

#### 3. Direct Text Input
```http
POST /api/input/text
Content-Type: application/json

{
    "content": "User1: How do we handle...\nUser2: The process is...",
    "format": "chat" | "email" | "meeting_notes",
    "metadata": {
        "title": "Discussion about X",
        "participants": ["User1", "User2"],
        "date": "2024-01-15"
    }
}
```

### AI Processing Endpoints (For AI Core Team ③)

#### Batch KB Extraction
```http
POST /api/kb/extract
Content-Type: application/json

{
    "threads": [/* Array of StandardizedThread */],
    "options": {
        "min_confidence": 0.6,
        "categories": ["troubleshooting", "process", "decision"],
        "exclude_short_threads": true
    }
}
```

**Expected Response:**
```json
{
    "results": [/* Array of KBExtractionResult */],
    "summary": {
        "total_processed": 12,
        "kb_worthy": 8,
        "average_confidence": 0.74
    }
}
```

#### KB Matching
```http
POST /api/ai/match-batch  
Content-Type: application/json

{
    "extractions": [/* Array of KBExtractionResult */],
    "existing_kb": [/* Array of existing KB documents */]
}
```

#### KB Generation
```http
POST /api/kb/generate
Content-Type: application/json

{
    "extractions": [/* KBExtractionResult with match results */],
    "template": "standard" | "troubleshooting" | "process"
}
```

## Integration Patterns

### For AI Core Team (③)

#### 1. Batch Processing Flow
```python
# Receive standardized threads from input processing
threads: List[StandardizedThread] = request_data["threads"]

# Step 1: PII Masking
masked_threads = await pii_masker.mask_batch(threads)

# Step 2: KB Extraction  
extractions = await kb_extractor.extract_batch(masked_threads)

# Step 3: KB Matching
matches = await kb_matcher.match_batch(extractions, existing_kb)

# Step 4: KB Generation
generations = await kb_generator.generate_batch(matches)

return generations
```

#### 2. Error Handling
```python
class AIProcessingError(Exception):
    def __init__(self, stage: str, thread_id: str, error: str):
        self.stage = stage
        self.thread_id = thread_id
        self.error = error

# Use this for consistent error reporting
try:
    result = await process_thread(thread)
except Exception as e:
    raise AIProcessingError("extraction", thread.id, str(e))
```

### For GitHub Integration

#### PR Creation with Batch Results
```http
POST /api/github/create-batch-pr
Content-Type: application/json

{
    "generations": [/* Array of KBGenerationResult */],
    "branch_name": "kb-update-2024-01-15",
    "pr_title": "Knowledge Base Update: 8 new documents",
    "pr_description": "Auto-generated from Slack conversations...",
    "metadata": {
        "source_channels": ["general", "dev-team"],
        "processing_date": "2024-01-15",
        "ai_confidence_avg": 0.82
    }
}
```

## Mock Responses (For Testing)

### Mock AI Extraction Response
```json
{
    "thread_id": "slack-123456", 
    "is_kb_worthy": true,
    "confidence_score": 0.85,
    "reasoning": "Thread contains detailed troubleshooting steps for database connection issues, with clear problem description and verified solution.",
    "suggested_title": "Troubleshooting Database Connection Timeouts",
    "category": "troubleshooting",
    "tags": ["database", "connection", "timeout", "troubleshooting"],
    "key_topics": ["connection pooling", "timeout configuration", "error handling"],
    "estimated_value": "high"
}
```

### Mock KB Generation Response  
```json
{
    "title": "Database Connection Timeout Resolution",
    "content": "# Database Connection Timeout Resolution\n\n## Problem\n...",
    "file_path": "troubleshooting/database/connection-timeouts.md",
    "category": "troubleshooting", 
    "tags": ["database", "connection", "timeout"],
    "metadata": {
        "difficulty": "intermediate",
        "estimated_read_time": "5 minutes"
    },
    "ai_confidence": 0.85,
    "source_threads": ["slack-123456"]
}
```

## Rate Limiting & Performance

### Slack API Limits
- **conversations.history**: 100+ requests/minute
- **conversations.replies**: 100+ requests/minute  
- **Recommendation**: Process in batches of 50 threads max
- **Implement**: Exponential backoff for 429 responses

### Memory Management
- **Large Channels**: Process in chunks of 100-200 messages
- **Batch Size**: Recommend 10-20 threads per AI batch call
- **Timeout**: Set 30s timeout for AI processing calls

## Error Codes

| Code | Description | Action |
|------|-------------|---------|
| `SLACK_RATE_LIMIT` | Hit Slack API rate limit | Retry with backoff |
| `SLACK_PERMISSION_DENIED` | Bot not in channel | Inform user |
| `AI_PROCESSING_TIMEOUT` | AI call timed out | Retry or skip |
| `AI_LOW_CONFIDENCE` | All extractions below threshold | Log and continue |
| `GITHUB_PR_FAILED` | PR creation failed | Retry or manual intervention |

This API design enables parallel development while maintaining clear interfaces between team members' work areas.