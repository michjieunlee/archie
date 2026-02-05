# Archie - Conversations to Living Knowledge Base

An intelligent agent that automatically extracts decision-making, troubleshooting, and know-how from conversations and transforms them into a structured Knowledge Base (KB).

## Overview

```
Multi-Input Sources → Batch Processing → AI Extraction → KB Generation → GitHub PR
```

**Key Features:**
- **Multi-Input Processing**: Slack API, file upload, or direct text paste
- **Comprehensive Message Collection**: Scans ALL messages and threads in specified time periods
- **Batch AI Processing**: Processes multiple conversations simultaneously for better context
- **AI-powered structured document generation** with PII masking
- **Automatic GitHub PR creation** with generated KB documents
- **User-configurable workspace settings** for multi-tenant support

## Input Methods

### 1. **Slack API Integration** (Primary)
```
Channel + Time Range → Comprehensive Message Collection → KB Extraction
```
- Scans all messages in specified time period (default: 1 week)
- Automatically expands threaded conversations
- Handles both public and private channels
- Rate limiting and pagination support

### 2. **File Upload**
- Upload conversation history files
- Supports various formats (JSON, CSV, TXT)
- Converts to standardized format for processing

### 3. **Direct Text Input**
- Paste conversation text directly into Joule
- Manual input for quick KB extraction
- Useful for external conversations or legacy data

## Project Structure

```
archie/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration
│   │
│   ├── api/routes/             # API endpoints
│   │   ├── slack.py            # Slack-related API
│   │   ├── github.py           # GitHub-related API
│   │   └── knowledge.py        # KB pipeline API
│   │
│   ├── integrations/           # ① Owner's area
│   │   ├── slack/              # Slack API integration
│   │   │   ├── client.py       # Slack API client
│   │   │   ├── parser.py       # Permalink parsing
│   │   │   └── models.py       # Slack data models
│   │   └── github/             # GitHub API integration
│   │       ├── client.py       # GitHub API client
│   │       ├── pr.py           # PR creation logic
│   │       └── models.py       # GitHub data models
│   │
│   ├── ai_core/                # ② Owner's area
│   │   ├── masking/            # PII masking
│   │   │   └── pii_masker.py
│   │   ├── extraction/         # KB candidate extraction
│   │   │   └── kb_extractor.py
│   │   ├── matching/           # New vs Update decision
│   │   │   └── kb_matcher.py
│   │   ├── generation/         # Document generation
│   │   │   └── kb_generator.py
│   │   ├── prompts/            # AI prompts
│   │   │   ├── extraction.py
│   │   │   ├── matching.py
│   │   │   └── generation.py
│   │   └── templates/          # KB document templates
│   │       └── kb_template.md
│   │
│   ├── models/                 # Shared data models
│   │   ├── thread.py           # Standardized thread
│   │   └── knowledge.py        # KB document model
│   │
│   └── services/               # Business logic
│       └── pipeline.py         # Pipeline orchestration
│
├── tests/
│   ├── integrations/           # ① Tests
│   └── ai_core/                # ② Tests
│
├── requirements.txt
├── .env.example
└── README.md
```

## Team Structure
- **① Integration Owner**: Slack API, GitHub operations, Joule endpoints  
- **② AI/Knowledge Owner**: SAP GenAI SDK, PII masking, KB operations  
- **③ Joule Interface Owner**: User interface, progress tracking, result display

*See `docs/IMPLEMENTATION_PLANS.md` for detailed team responsibilities and implementation guidance.*

## Getting Started

### Prerequisites

- Python 3.11+
- Slack workspace with bot permissions
- GitHub personal access token
- SAP GenAI SDK access

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/archie.git
cd archie

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### API Documentation
*See `docs/API_INTEGRATION.md` for complete API endpoint documentation and data models.*

### Configuration

```bash
# Multi-workspace configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
GITHUB_TOKEN=ghp-your-token
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=knowledge-base

# AI Processing
SAP_GENAI_API_KEY=your-api-key
SAP_GENAI_ENDPOINT=https://your-endpoint.sap.com
```

### Running Tests

```bash
pytest tests/ -v
```

## Updated Pipeline Flow

### **Living KB Processing Architecture** (Primary)
```
1. Multi-Input Collection
   ├── Slack API: Channel + Time Range → All Messages + Threads
   ├── File Upload: Conversation History → Parsed Messages  
   └── Text Input: Direct Paste → Structured Conversations
   
2. Existing KB Context (① Owner)
   └── Fetch current KB repository → Parse existing documents → AI-searchable format

3. Data Standardization (① Owner)
   └── Convert all inputs → List[StandardizedThread] + Existing KB Context

4. Living KB AI Processing (② Owner)
   ├── PII Masking: Batch mask all conversations
   ├── KB Extraction: Evaluate conversations for KB worthiness
   ├── KB Matching: Semantic comparison against EXISTING KB documents
   └── KB Operations: Decide create/update/append/replace for existing documents

5. GitHub Integration (① Owner)
   └── Create PR with KB updates (new documents + modifications to existing)
```

### **Single Thread Processing** (Legacy Support)
```
1. User submits Slack thread permalink → POST /api/knowledge/process
2. Fetch thread messages (① Owner) → integrations/slack/client.py
3. PII Masking (② Owner) → ai_core/masking/pii_masker.py
4. KB Extraction (② Owner) → ai_core/extraction/kb_extractor.py
5. KB Matching (② Owner) → ai_core/matching/kb_matcher.py  
6. KB Generation (② Owner) → ai_core/generation/kb_generator.py
7. GitHub PR Creation (① Owner) → integrations/github/pr.py
```

## Documentation

- **Architecture**: `docs/ARCHITECTURE.md` - System architecture and data flow diagrams
- **API Integration**: `docs/API_INTEGRATION.md` - Complete API documentation and data models
- **Implementation Plans**: `docs/IMPLEMENTATION_PLANS.md` - Team responsibilities and development guidance
- **KB Structure**: `docs/KB_REPOSITORY_STRUCTURE.md` - Knowledge base repository organization

## Future Roadmap

- [ ] Teams chat integration
- [ ] Knowledge Q&A chatbot
- [ ] Automatic thread detection via Slack Events API
- [ ] KB search and retrieval API
