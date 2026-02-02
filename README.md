# Archie - Slack Chat to Living Knowledge Base

An agent that automatically extracts decision-making, troubleshooting, and know-how from Slack conversations and transforms them into a Knowledge Base (KB).

## Overview

```
Slack Thread → PII Masking → KB Extraction → Matching → Generation → GitHub PR
```

**Key Features:**
- Detect KB-worthy conversations from Slack threads
- AI-powered structured document draft generation
- Automatic push to GitHub as PR
- (Planned) Teams chat extension support

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
│   ├── ai_core/                # ③ Owner's area
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
│   └── ai_core/                # ③ Tests
│
├── requirements.txt
├── .env.example
└── README.md
```

## Role Assignment

### ① Slack · GitHub Integration & Flow Owner

**Directories:** `app/integrations/`, `app/api/routes/slack.py`, `app/api/routes/github.py`

**Responsibilities:**
- Slack App setup and API integration
- Thread permalink parsing and message collection
- GitHub KB repo integration (branch, PR creation)
- Input data standardization

**Key Tasks:**
1. Slack PoC workspace + Archie App setup
2. `integrations/slack/client.py` - Implement conversations.replies API
3. `integrations/github/pr.py` - Implement PR creation flow
4. Prepare 2-3 demo Slack threads

### ③ AI Core · Compliance · Knowledge Logic Owner

**Directories:** `app/ai_core/`

**Responsibilities:**
- PII masking (SAP GenAI SDK Data Masking)
- KB candidate extraction and value evaluation
- New vs Update decision logic
- Document generation/update prompts

**Key Tasks:**
1. `ai_core/masking/pii_masker.py` - SAP GenAI SDK integration
2. `ai_core/prompts/` - Design and tune 3 prompts
3. `ai_core/templates/` - Define KB document templates
4. Implement explainability for "why AI made this decision"

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

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/slack/thread` | POST | Fetch Slack thread by permalink |
| `/api/github/pr` | POST | Create KB PR |
| `/api/knowledge/process` | POST | Full pipeline: thread → PR |

### Running Tests

```bash
pytest tests/ -v
```

## Pipeline Flow

```
1. User submits Slack thread permalink
   └── POST /api/knowledge/process

2. Fetch thread messages (① Owner)
   └── integrations/slack/client.py

3. Mask PII data (③ Owner)
   └── ai_core/masking/pii_masker.py

4. Extract KB candidate (③ Owner)
   └── ai_core/extraction/kb_extractor.py
   └── Prompt 1: Is this KB-worthy?

5. Match against existing KB (③ Owner)
   └── ai_core/matching/kb_matcher.py
   └── Prompt 2: Create vs Update vs Ignore?

6. Generate KB document (③ Owner)
   └── ai_core/generation/kb_generator.py
   └── Prompt 3: Generate markdown

7. Create GitHub PR (① Owner)
   └── integrations/github/pr.py
```

## Future Roadmap

- [ ] Teams chat integration
- [ ] Knowledge Q&A chatbot
- [ ] Automatic thread detection via Slack Events API
- [ ] KB search and retrieval API
