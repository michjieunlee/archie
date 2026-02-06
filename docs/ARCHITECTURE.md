# Archie Architecture Overview

This document provides visual architecture diagrams and system design overview for the updated multi-input, batch processing architecture with thread expansion and PII masking.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             ARCHIE SYSTEM                                      │
│                      Conversations → LIVING Knowledge Base                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   INPUT SOURCES     │    │  PROCESSING LAYER   │    │   OUTPUT LAYER      │
│                     │    │                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ Slack API       │ │    │ │ Data            │ │    │ │ GitHub PR       │ │
│ │ • Channel Scan  │ │    │ │ Standardization │ │    │ │ • KB Updates    │ │
│ │ • Thread Expand │ │────▶│ │      +          │ │────▶│ │ • New Documents │ │
│ │ • Rate Limiting │ │    │ │ KB Context      │ │    │ │ • Modifications │ │
│ └─────────────────┘ │    │ │      ↓          │ │    │ └─────────────────┘ │
│                     │    │ │ StandardizedConversation │                   │
│ ┌─────────────────┐ │    │ │ + ExistingKB    │ │    │ ┌─────────────────┐ │
│ │ File Upload     │ │────▶│ └─────────────────┘ │    │ │ Joule Interface │ │
│ │ • JSON Export   │ │    │                     │────▶│ │ • Status        │ │
│ │ • CSV Format    │ │    │ ┌─────────────────┐ │    │ │ • Progress      │ │
│ │ • Plain Text    │ │    │ │ LIVING KB       │ │    │ │ • Results       │ │
│ └─────────────────┘ │    │ │ AI PROCESSING   │ │    │ └─────────────────┘ │
│                     │    │ │ (Batch Mode)    │ │    │                     │
│ ┌─────────────────┐ │    │ │                 │ │    │                     │
│ │ Text Input      │ │────▶│ │ 1. PII Masking  │ │    │                     │
│ │ • Direct Paste  │ │    │ │ 2. KB Extraction│ │    │                     │
│ │ • Chat Format   │ │    │ │ 3. KB Matching  │ │    │                     │
│ │ • Meeting Notes │ │    │ │    vs EXISTING  │ │    │                     │
│ └─────────────────┘ │    │ │ 4. KB Operations│ │    │                     │
│                     │    │ │    Create/Update│ │    │                     │
│ ┌─────────────────┐ │    │ └─────────────────┘ │    │                     │
│ │ EXISTING KB     │ │    │                     │    │                     │
│ │ (GitHub Repo)   │ │────▶│ (MANDATORY INPUT) │    │                     │
│ │ • All Documents │ │    │                     │    │                     │
│ │ • Categories    │ │    │                     │    │                     │
│ │ • Metadata      │ │    │                     │    │                     │
│ └─────────────────┘ │    │                     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```


```

## Multi-Input Processing Flow

### 1. Slack API Processing Flow

```
┌──────────────┐
│ Slack API    │
│ Input        │
└──────┬───────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Channel Scan │───▶│ Thread Expand│───▶│ Rate Limiter │
│ • History    │    │ • Replies    │    │ • Queue      │
│ • Pagination │    │ • Context    │    │ • Backoff    │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                              │
┌──────────────┐                              │
│ File Upload  │                              │
│ Processing   │                              │
└──────┬───────┘                              │
       │                                      ▼
       ▼                              ┌──────────────┐
┌──────────────┐                     │ Conversation │
│ Text Input   │────────────────────▶│ Converter    │
│ Processing   │                     └──────┬───────┘
└──────────────┘                            │
                                            ▼
                                    ┌──────────────┐
                                    │ StandardizedConversation │
                                    │ with Rich    │
                                    │ Metadata     │
                                    └──────────────┘
```

### 2. AI Processing Pipeline (Batch Mode)

```
┌─────────────────────┐
│ StandardizedConversation │
│ (with expansion)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ PII MASKING         │
│ • Batch process     │
│ • USER_X format     │
│ • Privacy compliance│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ KB EXTRACTION       │
│ • Batch analysis    │
│ • Worthiness score  │
│ • Category tagging  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ KB MATCHING         │
│ • Existing KB scan  │
│ • Similarity check  │
│ • Merge/Update logic│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ KB GENERATION       │
│ • Document creation │
│ • Markdown format   │
│ • File path suggest │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ List[               │
│ KBGenerationResult] │
└─────────────────────┘
```

## Team Ownership Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           TEAM RESPONSIBILITIES                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ ① INTEGRATION       │    │ ② AI CORE           │    │ SHARED MODELS       │
│ OWNER               │    │ OWNER               │    │                     │
│                     │    │                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ Slack API       │ │    │ │ PII Masking     │ │    │ │ StandardizedConversation│ │
│ │ • Client        │ │    │ │ • SAP GenAI SDK │ │    │ │ • StandardizedMessage│ │
│ │ • Models        │ │    │ │ • USER_X Format │ │    │ │                 │ │
│ │ • Thread Expand │ │    │ └─────────────────┘ │    │ └─────────────────┘ │
│ └─────────────────┘ │    │                     │    │                     │
│                     │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ ┌─────────────────┐ │    │ │ KB Extraction   │ │    │ │ KBExtractionResult│ │
│ │ GitHub API      │ │    │ │ • Worthiness    │ │    │ │ • KBMatchResult │ │
│ │ • Client        │ │    │ │ • Categorization│ │    │ │ • KBGenerationRes││
│ │ • PR Creation   │ │    │ │ • Confidence    │ │    │ └─────────────────┘ │
│ │ • Batch PRs     │ │    │ └─────────────────┘ │    │                     │
│ └─────────────────┘ │    │                     │    │                     │
│                     │    │ ┌─────────────────┐ │    │                     │
│ ┌─────────────────┐ │    │ │ KB Matching     │ │    │                     │
│ │ Input Processing│ │    │ │ • Similarity    │ │    │                     │
│ │ • Multi-source  │ │    │ │ • Update Logic  │ │    │                     │
│ │ • Standardization│ │    │ │ • Merging       │ │    │                     │
│ └─────────────────┘ │    │ └─────────────────┘ │    │                     │
│                     │    │                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │    │                     │
│ │ API Routes      │ │    │ │ KB Generation   │ │    │                     │
│ │ • Input Endpoints│ │    │ │ • Document      │ │    │                     │
│ │ • Slack Routes  │ │    │ │ • Templates     │ │    │                     │
│ │ • GitHub Routes │ │    │ │ • Prompts       │ │    │                     │
│ └─────────────────┘ │    │ └─────────────────┘ │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## API Integration Points

### Input Layer APIs

```
GET /api/slack/fetch
├── SlackClient.fetch_conversations_with_threads()
├── SlackClient.convert_to_standardized_conversation()
└── Return StandardizedConversation with rich metadata

POST /api/input/file
├── File parsing logic
├── Format detection
└── Convert to StandardizedConversation

POST /api/input/text
├── Text parsing logic
├── Structure detection
└── Convert to StandardizedConversation
```

### AI Processing APIs

```
POST /api/kb/extract
├── PIIMasker.mask_conversations()
├── KBExtractor.extract_batch()
└── Return List[KBExtractionResult]

POST /api/kb/match
├── KBMatcher.match_batch()
└── Return List[KBMatchResult]

POST /api/kb/generate
├── KBGenerator.generate_batch()
└── Return List[KBGenerationResult]
```

### Output Layer APIs

```
POST /api/github/create-batch-pr
├── PRManager.create_batch_pr()
├── Branch creation
├── Multiple file commits
└── PR with AI reasoning
```

## Performance Considerations

### Slack API Rate Limiting

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Request      │───▶│ Rate Limiter │───▶│ Exponential  │
│ Queue        │    │ • 100/min    │    │ Backoff      │
│              │    │ • Monitor 429│    │ • 1s, 2s, 4s│
└──────────────┘    └──────────────┘    └──────────────┘
```

### Memory Management

```
Large Channel Processing:
┌─────────────────┐
│ Channel (1000+) │
│ Messages        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Chunk into      │
│ 100-message     │
│ batches         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Process each    │
│ chunk separately│
│ (streaming)     │
└─────────────────┘
```

### AI Processing Optimization

```
Batch Processing:
┌─────────────────┐
│ 3-5 conversations│
│ per AI call     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parallel        │
│ processing      │
│ where possible  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 30s timeout     │
│ per AI batch    │
└─────────────────┘
```

## Error Handling Flow

```
┌─────────────────┐
│ Input Processing│
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ Validation      │───▶│ User-friendly   │
│ Errors          │    │ Error Response  │
└─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ Slack API       │───▶│ Retry Logic     │
│ Errors          │    │ • Rate Limit    │
└─────────────────┘    │ • Permission    │
         │              │ • Network       │
         ▼              └─────────────────┘
┌─────────────────┐
│ AI Processing   │
│ Errors          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ Partial Success │───▶│ Continue with   │
│ Handling        │    │ Successful      │
└─────────────────┘    │ Results         │
                       └─────────────────┘