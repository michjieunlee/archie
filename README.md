# Archie - AI-Powered Knowledge Base Assistant

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-beta-yellow)

<p align="center">
  <img src="img/logo1.png" alt="Archie Logo" width="120" height="120" style="border-radius: 12px;">
</p>

**Archie** is an intelligent agent that automatically extracts decision-making, troubleshooting, and know-how from conversations and transforms them into a structured, living Knowledge Base (KB).

> **Note:** This is an independent hackathon project. Copyright © 2026 Jieun (Michelle) Lee, Juyon Bae, Soohyun Choi.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Guide](#setup-guide)
- [How-To Guides](#how-to-guides)
  - [Setting Up a Knowledge Base Repository](#setting-up-a-knowledge-base-repository)
  - [Creating a GitHub Personal Access Token](#creating-a-github-personal-access-token)
  - [Generating a Slack Bot Token](#generating-a-slack-bot-token)
  - [Finding Your Slack Channel ID](#finding-your-slack-channel-id)
  - [Configuring SAP GenAI SDK](#configuring-sap-genai-sdk)
- [Running the Application](#running-the-application)
- [Using Archie](#using-archie)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Documentation](#documentation)
- [Known Limitations](#known-limitations)
- [License](#license)
- [Contributing](#contributing)

---

## Overview

Archie provides a chat-based interface to:

- **Chat**: Ask questions, request summaries, or seek clarifications
- **Connect to GitHub**: Link a Knowledge Base repository to store and manage KB documents
- **Connect to Slack**: Extract messages from Slack channels for KB generation
- **Upload Files**: Attach text files for direct KB creation
- **Query KB**: Search and retrieve information from your existing knowledge base

```
Multi-Input Sources → AI Processing (PII Masking) → KB Generation → GitHub PR
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Source Input** | Slack API integration, file upload, direct text input |
| **PII Masking** | Automatic anonymization of personal information before AI processing |
| **Intelligent KB Extraction** | AI-powered analysis to identify knowledge-worthy content |
| **Smart Matching** | Determines whether to create new KB articles or update existing ones |
| **GitHub Integration** | Automatic PR creation with generated KB documents |
| **Chat Interface** | Streamlit-based conversational UI for easy interaction |

---

## Architecture

![Archie Architecture](img/architecture.png)

Archie consists of two main services:
- **Backend API (FastAPI)**: Handles integrations, AI processing, and KB operations
- **Frontend UI (Streamlit)**: Provides the chat interface and integration management

---

## Prerequisites

Before setting up Archie, ensure you have:

- **Python 3.11+** installed
- **Git** installed
- **Slack workspace** with bot permissions (for Slack integration)
- **GitHub account** with a repository for your Knowledge Base
- **SAP GenAI SDK access** (API URL, Key, and Deployment ID)

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/archie.git
cd archie
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Install Streamlit frontend dependencies:
```bash
pip install -r app/streamlit/requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials (see [How-To Guides](#how-to-guides) for details on obtaining each value):

```bash
# App Settings
DEBUG=false
PORT=8001

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your-personal-access-token
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=knowledge-base
GITHUB_DEFAULT_BRANCH=main

# SAP GenAI SDK Configuration
AICORE_AUTH_URL=https://your-auth-url.authentication.sap.hana.ondemand.com
AICORE_CLIENT_ID=your-client-id
AICORE_CLIENT_SECRET=your-client-secret
AICORE_RESOURCE_GROUP=your-resource-group
AICORE_BASE_URL=https://api.ai.your-region.sap.hana.ondemand.com

# Processing Configuration
DRY_RUN=false  # Set to true to skip GitHub PR creation (for testing)
```

---

## How-To Guides

### Setting Up a Knowledge Base Repository

Your Knowledge Base repository is where Archie will store generated KB documents.

1. **Create a new GitHub repository** (or use an existing one)
   - Go to [github.com/new](https://github.com/new)
   - Name it something like `knowledge-base` or `team-kb`
   - Initialize with a README (recommended)

2. **Recommended folder structure**:
   ```
   knowledge-base/
   ├── README.md
   ├── decisions/          # Decision records
   ├── processes/          # Process documentation
   ├── troubleshooting/    # Troubleshooting guides
   ├── references/         # Reference materials
   └── general/            # General knowledge articles
   ```

3. **Note the repository details** for your `.env` file:
   - `GITHUB_REPO_OWNER`: Your GitHub username or organization name
   - `GITHUB_REPO_NAME`: The repository name (e.g., `knowledge-base`)

---

### Creating a GitHub Personal Access Token

A Personal Access Token (PAT) allows Archie to create branches and pull requests in your KB repository.

1. Go to **GitHub Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
   - Direct link: [github.com/settings/tokens](https://github.com/settings/tokens)

2. Click **"Generate new token (classic)"**

3. Configure the token:
   - **Note**: `Archie KB Access` (or any descriptive name)
   - **Expiration**: Choose based on your security requirements
   - **Scopes**: Select the following:
     - ✅ `repo` (Full control of private repositories)

4. Click **"Generate token"**

5. **Copy the token immediately** (it won't be shown again)
   - Add it to your `.env` file as `GITHUB_TOKEN`

> ⚠️ **Security Note**: Never commit your token to version control. Keep it secure.

---

### Generating a Slack Bot Token

A Slack Bot Token allows Archie to read messages from your Slack channels. Follow these steps to create a Slack app and generate a bot token.

#### 1. Create a New Slack App

1. Go to the **Slack API portal**: [api.slack.com/apps](https://api.slack.com/apps/)
2. Click **"Create New App"**
3. Select **"From an app manifest"**
4. Choose your workspace from the dropdown
5. Click **"Next"**

#### 2. Configure the App with the Manifest

1. Select **JSON** as the format
2. Replace the default manifest with the following configuration:

```json
{
    "display_information": {
        "name": "Archie"
    },
    "features": {
        "bot_user": {
            "display_name": "Archie",
            "always_online": false
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "channels:history",
                "channels:read",
                "groups:history",
                "groups:read"
            ]
        }
    },
    "settings": {
        "org_deploy_enabled": false,
        "socket_mode_enabled": false,
        "token_rotation_enabled": false
    }
}
```

3. Click **"Next"** to review the configuration
4. Click **"Create"** to finish creating the app

#### 3. Install the App to Your Workspace

1. In the Slack api settings, go to **"Install App"** in the left sidebar
2. Click **"Install to Workspace"**
3. Review the permissions and click **"Allow"**

![Slack App Installation](img/slack_app_installation.png)

#### 4. Copy the Bot Token

1. After installation, you'll see the **"Bot User OAuth Token"** on the same page
2. The token starts with `xoxb-` (e.g., `xoxb-1234567890-1234567890-abcdefghijklmnopqrstuvwx`)
3. Click **"Copy"** to copy the token
4. Add this token to your `.env` file as `SLACK_BOT_TOKEN`

> ⚠️ **Security Note**: Keep your bot token secure. Never commit it to version control or share it publicly.

#### 5. Invite the Bot to Channels

Before Archie can read messages from a channel, you must invite the bot:

1. Open the Slack channel you want to extract messages from
2. Type `/invite @Archie` in the message box
3. Press Enter to invite the bot
4. You should see a confirmation message that the bot was added

> **Note**: The bot can only read messages from channels it has been invited to. You'll need to invite it to each channel you want to use with Archie.

#### Verify Permissions

The manifest above grants these essential permissions:
- **`channels:history`**: Read messages from public channels
- **`channels:read`**: View basic information about public channels
- **`groups:history`**: Read messages from private channels (if invited)
- **`groups:read`**: View basic information about private channels

If you need to modify permissions later:
1. Go to your app settings at [api.slack.com/apps](https://api.slack.com/apps/)
2. Select your app
3. Navigate to **"OAuth & Permissions"**
4. Update the **"Bot Token Scopes"** as needed
5. Reinstall the app to apply changes

---

### Finding Your Slack Channel ID

Archie needs the Channel ID (not the channel name) to fetch messages.

**Method 1: From Slack Web/Desktop App**
1. Open Slack and navigate to the channel
2. Click on the channel name at the top
3. Scroll down in the modal/popup that appears
4. Find the **Channel ID** at the bottom (starts with `C`, e.g., `C01234ABCDE`)

**Method 2: From Channel Link**
1. Right-click on the channel name → "Copy link"
2. The link format is: `https://workspace.slack.com/archives/C01234ABCDE`
3. The Channel ID is the last part: `C01234ABCDE`

> **Note**: The Slack Bot Token (`SLACK_BOT_TOKEN`) must be configured in your `.env` file. This token is typically obtained when setting up a Slack App. The bot must be invited to any channel you want to extract messages from.

---

### Configuring SAP GenAI SDK

Archie uses SAP's Generative AI Hub for AI processing. You need credentials from SAP BTP (Business Technology Platform).

1. **Obtain credentials from SAP BTP Cockpit**:
   - Navigate to your SAP AI Core service instance
   - Go to **Service Keys** and create or view a service key
   - Extract the following values:

2. **Required environment variables**:
   ```bash
   # Authentication
   AICORE_AUTH_URL=<from service key: "url" under "uaa">
   AICORE_CLIENT_ID=<from service key: "clientid" under "uaa">
   AICORE_CLIENT_SECRET=<from service key: "clientsecret" under "uaa">

   # API Configuration
   AICORE_RESOURCE_GROUP=<your resource group>
   AICORE_BASE_URL=<from service key: "serviceurls.AI_API_URL">
   ```

3. **Alternative environment variable names** (also supported):
   ```bash
   SAP_GENAI_API_URL=<AI API URL>
   SAP_GENAI_API_KEY=<client secret>
   SAP_GENAI_DEPLOYMENT_ID=<deployment ID if using specific deployment>
   ```

> **Note**: Contact your SAP BTP administrator if you don't have access to the AI Core service instance.

---

## Running the Application

Archie consists of two services that need to run simultaneously:

### Start the Backend API (FastAPI)

**Option 1: Using the run script** (recommended)
```bash
python run.py
```

**Option 2: Using uvicorn directly**
```bash
uvicorn app.main:app --reload --port 8001
```

The API will be available at:
- API: `http://localhost:8001`
- API Documentation: `http://localhost:8001/docs`

### Start the Frontend UI (Streamlit)

In a **separate terminal**:
```bash
cd app/streamlit && streamlit run app.py
```

The UI will be available at: `http://localhost:8501`

### Port Configuration

| Service | Default Port | Environment Variable |
|---------|--------------|---------------------|
| Backend API | 8001 | `PORT` |
| Frontend UI | 8501 | `--server.port` flag |

To change the backend port:
```bash
PORT=8002 python run.py
```

To change the frontend port:
```bash
cd app/streamlit && streamlit run app.py --server.port 8502
```

---

## Using Archie

### 1. Access the Application

Open your browser and navigate to `http://localhost:8501`

### 2. Connect Integrations

From the left sidebar, click on the integration buttons to configure:

**GitHub Connection:**
1. Click the **GitHub** button in the sidebar
2. Enter your KB repository URL (e.g., `https://github.com/your-org/knowledge-base`)
3. Enter your Personal Access Token
4. Click **Connect**

**Slack Connection:**
1. Click the **Slack** button in the sidebar
2. Enter the Channel ID (e.g., `C01234ABCDE`)
3. Click **Connect**

### 3. Interact with Archie

Once connected, you can:

- **Chat**: Type questions or requests in the chat input
- **Extract from Slack**: Ask Archie to extract KB articles from recent Slack messages
- **Upload Files**: Click "ATTACH FILES" to upload text files for KB generation
- **Query KB**: Ask questions about your existing knowledge base

**Example prompts:**
- "Extract knowledge from the last 20 Slack messages"
- "Create a KB article from the attached file"
- "What do we know about deployment procedures?"
- "Summarize the troubleshooting guides in our KB"

---

## Project Structure

```
archie/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration settings
│   │
│   ├── api/routes/             # API endpoints
│   │   ├── slack.py            # Slack integration API
│   │   ├── github.py           # GitHub integration API
│   │   ├── kb.py               # Knowledge Base API
│   │   └── credentials.py      # Credential management
│   │
│   ├── integrations/           # External service integrations
│   │   ├── slack/              # Slack API client
│   │   └── github/             # GitHub API client & PR creation
│   │
│   ├── ai_core/                # AI processing modules
│   │   ├── masking/            # PII masking
│   │   ├── extraction/         # KB extraction logic
│   │   ├── matching/           # KB matching (create/update decisions)
│   │   ├── generation/         # Document generation
│   │   ├── prompts/            # AI prompts
│   │   └── templates/          # KB document templates
│   │
│   ├── models/                 # Data models
│   ├── services/               # Business logic orchestration
│   │
│   └── streamlit/              # Frontend application
│       ├── app.py              # Streamlit entry point
│       ├── components/         # UI components
│       ├── config/             # Frontend configuration
│       ├── prompts/            # Chat prompts
│       ├── services/           # API client services
│       └── utils/              # Utility functions
│
├── docs/                       # Documentation
├── img/                        # Images and logos
├── tests/                      # Test suite
├── .env.example                # Environment template
├── requirements.txt            # Backend dependencies
└── README.md                   # This file
```

---

## Running Tests

```bash
pytest tests/ -v
```

For test coverage:
```bash
pytest tests/ -v --cov=app
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and data flow |
| [API_INTEGRATION.md](docs/API_INTEGRATION.md) | API documentation |
| [KB_MANAGEMENT_API_ENDPOINTS.md](docs/KB_MANAGEMENT_API_ENDPOINTS.md) | API endpoints and usage examples |
| [GITHUB_INTEGRATION.md](docs/GITHUB_INTEGRATION.md) | GitHub integration details |
| [SLACK_INTEGRATION.md](docs/SLACK_INTEGRATION.md) | Slack integration details |
| [KB_REPOSITORY_STRUCTURE.md](docs/KB_REPOSITORY_STRUCTURE.md) | KB repository organization |
| [KB_WRITING_GUIDELINES.md](docs/KB_WRITING_GUIDELINES.md) | Guidelines for KB documents |
| [KB_MATCHER_IMPLEMENTATION.md](docs/KB_MATCHER_IMPLEMENTATION.md) | KB matching algorithm details |
| [KB_QNA_IMPLEMENTATION.md](docs/KB_QNA_IMPLEMENTATION.md) | Q&A feature implementation |

---

## Troubleshooting

### Common Issues

**"Connection refused" when starting the UI**
- Ensure the backend API is running on port 8001
- Check that `PORT` in `.env` matches the running backend

**"Invalid GitHub token"**
- Verify your token hasn't expired
- Ensure the token has `repo` scope
- Check for trailing whitespace in `.env`

**"Slack channel not found"**
- Verify the Channel ID (not channel name) is correct
- Ensure the Slack bot is invited to the channel
- Check that `SLACK_BOT_TOKEN` is valid

**AI processing errors**
- Verify SAP GenAI SDK credentials are correctly configured
- Check network connectivity to SAP AI Core services

---

## Known Limitations

- **SAP GenAI SDK Required**: This project requires SAP BTP (Business Technology Platform) access to use the SAP GenAI SDK. Users need valid SAP credentials to run the AI processing features.
- **Single Slack Channel**: Currently supports monitoring one Slack channel at a time.
- **GitHub PAT Authentication**: Uses Personal Access Tokens rather than GitHub App authentication.
- **Single Instance**: Designed for single-team use without multi-user authentication.
- **Language Support**: LLM processing currently optimized for English language only.

---

## License

Copyright © 2026 Jieun (Michelle) Lee, Juyon Bae, Soohyun Choi. All rights reserved.

--