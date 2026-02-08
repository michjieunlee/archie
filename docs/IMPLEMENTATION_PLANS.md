# Implementation Plans

Concise implementation guidance for the complete living KB system.

## 🎯 System Overview
**Goal**: Transform conversations into living knowledge base updates
**Architecture**: Multi-input → AI Processing → GitHub KB Updates
**Key Feature**: Living KB - existing GitHub repository context drives all AI decisions

---

## Team Structure & Responsibilities

### ① Integration Owner
**Core Responsibilities**: Slack API, GitHub operations, Joule endpoints
**Key Files**: `app/integrations/slack/client.py`, `app/integrations/github/client.py`
**Main Tasks**:
- Slack thread expansion with StandardizedConversation model
- GitHub KB reading + complex PR operations (create/update/append)
- Multi-input processing (Slack/file/text)
- Joule API endpoints for progress tracking

**Implementation Focus**:
```python
# Slack Integration
SlackClient.fetch_conversations_with_threads() -> StandardizedConversation
SlackClient.convert_to_standardized_conversation(slack_conversation: StandardizedConversation)

# GitHub Integration
GitHubClient.read_kb_repository() - fetch existing KB for context
GitHubClient.create_kb_pr() - complex operations (create/update/append)

# APIs
GET /api/slack/extract, /api/input/file, /api/input/text
/api/joule/extract-knowledge, /api/joule/status, /api/joule/results
```

### ② AI/Knowledge Owner
**Core Responsibilities**: SAP GenAI SDK, PII masking, KB operations
**Key Files**: `app/ai_core/masking/`, `app/ai_core/extraction/`, `app/ai_core/matching/`
**Main Tasks**:
- PII masking with SAP GenAI SDK batch processing (USER_1, USER_2 format)
- Knowledge extraction WITH existing KB context
- Complex KB operations (create/update/append/replace)
- AI reasoning and confidence scoring

**Implementation Focus**:
```python
# Processing Pipeline
PIIMasker.mask_threads() - SAP GenAI Data Masking API
KBExtractor.extract_knowledge() - conversation analysis + confidence
KBMatcher.match_against_existing() - semantic comparison vs existing KB
KBGenerator.generate_documents() - create/update operations with reasoning

# Key Concept: Living KB Context
Input: StandardizedConversation + ExistingKBContext
Output: KBOperationResult (with create/update/append instructions)
```

### ③ Joule Interface Owner
**Core Responsibilities**: User interface, progress tracking, result display
**Main Tasks**:
- Joule conversation interface for triggering extraction
- Real-time progress tracking and status reporting
- Display KB updates and AI reasoning to users
- Multi-input support (Slack/file/text)

**Implementation Focus**:
```python
# User Interface Flow
1. Accept input (Slack permalink, file, text)
2. Call Archie APIs + monitor progress
3. Display results: KB documents, AI reasoning, GitHub PR links
4. Handle errors gracefully with user-friendly messages

# API Integration
GET /api/slack/extract → POST /api/knowledge/process → Display results
```

---

## Data Contracts

**Core Data Flow**:
```
StandardizedConversation + ExistingKBContext → AI Processing → KBOperationResult → GitHub PR
```

**Key Models** (see `app/models/thread.py`):
- `StandardizedConversation` - Platform-agnostic conversation format
- `ExistingKBContext` - Current state of KB repository
- `KBOperationResult` - AI decisions for KB operations (create/update/append)

**Living KB Operations**:
- `CREATE` - New document
- `UPDATE` - Replace entire document
- `APPEND` - Add section to existing document
- `REPLACE` - Replace specific section
- `MERGE` - Combine with existing document

---

## Technical Approach

**GitHub Integration**: Personal access token (not GitHub App)
**Empty KB Handling**: Treat as empty context, no errors
**Parallel Development**: Mock AI responses enable independent work
**AI Integration**: SAP GenAI SDK with fallback options

**Demo Strategy**:
- Primary: Slack channel scan → living KB analysis → GitHub PR with updates
- Secondary: File upload → knowledge extraction → new documents
- Backup: Pre-cached responses for API failures