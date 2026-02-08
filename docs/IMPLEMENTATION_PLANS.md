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
# Slack Integration (✅ Working)
SlackClient.fetch_conversations_with_threads() -> StandardizedConversation
# Returns StandardizedConversation with thread expansion and global indexing

# GitHub Integration (🚧 Not yet implemented)
GitHubClient.read_kb_repository() - fetch existing KB for context (TODO)
GitHubClient.create_kb_pr() - complex operations (create/update/append) (TODO)

# APIs (Current endpoints)
GET /api/slack/fetch (✅ Working)
GET /api/kb/from-slack (✅ Working)
POST /api/kb/from-text (✅ Working)
POST /api/kb/query (⚠️ Placeholder only)
# Joule endpoints not yet implemented
```

### ② AI/Knowledge Owner
**Core Responsibilities**: SAP GenAI SDK, PII masking, KB operations
**Key Files**: `app/ai_core/masking/`, `app/ai_core/extraction/`, `app/ai_core/matching/`
**Main Tasks**:
- ✅ PII masking with SAP GenAI SDK batch processing (USER_1, USER_2 format)
- ✅ Knowledge extraction with category classification
- ✅ Template-based KB document generation
- ✅ AI reasoning and confidence scoring
- 🚧 Complex KB operations (currently only CREATE, update/append/replace not implemented)

**Implementation Focus**:
```python
# Processing Pipeline (Current Status)
PIIMasker.mask_conversations() - SAP GenAI Orchestration V2 (✅ Working)
KBExtractor.extract_knowledge() - category classification + structured extraction (✅ Working)
KBMatcher.match() - semantic comparison vs existing KB (🚧 Stub - always returns CREATE)
KBGenerator.generate_markdown() - template-based markdown generation (✅ Working)

# Key Concept: Living KB Context (Planned)
Input: StandardizedConversation + ExistingKBContext
Output: KBOperationResult (with create/update/append instructions)
# Note: ExistingKBContext fetching not yet implemented
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