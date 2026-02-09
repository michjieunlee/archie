# GitHub Integration Setup

Quick setup guide for Archie's GitHub integration with knowledge base management.

## Setup

### Environment
Create `.env` file:
```bash
GITHUB_TOKEN=your_personal_access_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=your_test_repository
GITHUB_DEFAULT_BRANCH=main
```

### GitHub Token
Create token at: GitHub Settings → Developer settings → Personal access tokens
Required permissions: `repo`, `pull_requests`, `contents`

### Test Repository
Create a GitHub repository with markdown files in folders:
```
your-test-repository/
├── troubleshooting/
│   └── sample-issue.md
├── processes/
│   └── sample-process.md
└── decisions/
    └── sample-decision.md
```

### Testing

Each integration has its own comprehensive test suite:

```bash
# Test Slack integration
python tests/integrations/test_slack_integration.py --mock      # Mock data (default)
python tests/integrations/test_slack_integration.py --real      # Real Slack API
python tests/integrations/test_slack_integration.py --quick     # Quick test

# Test GitHub integration
python tests/integrations/test_github_integration.py --mock     # Mock data (default)
python tests/integrations/test_github_integration.py --real     # Real GitHub API
python tests/integrations/test_github_integration.py --quick    # Quick test
```

**Real API Testing** requires credentials in `.env`:

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_ID=C1234567890

# GitHub
GITHUB_TOKEN=your_github_token
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo-name
```

**Basic pytest Usage:**
```bash
pytest tests/ -v                                    # All tests
pytest tests/integrations/test_github_integration.py  # Specific test file
```

## Manual Testing

### 1. Basic Functionality
```python
python -c "
import asyncio
from app.integrations.github.client import GitHubClient

async def test():
    client = GitHubClient()
    categories = await client._discover_categories()
    print(f'Categories: {categories}')
    docs = await client.read_kb_repository()
    print(f'Found {len(docs)} documents')

asyncio.run(test())
"
```

### 2. API Testing
```bash
# Start server
uvicorn app.main:app --reload --port 8000

# Test endpoints
curl -X GET "http://localhost:8000/github/kb/documents"

curl -X POST "http://localhost:8000/github/kb/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Document",
    "content": "# Test\n\nContent here",
    "file_path": "troubleshooting/test.md"
  }'
```

### 3. Batch Operations
```bash
curl -X POST "http://localhost:8000/github/kb/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Batch",
    "operations": [
      {"action": "create", "file_path": "test.md", "content": "Test content"}
    ]
  }'
```

## Troubleshooting

### Common Issues

**GitHub Authentication Error**
- Check token validity: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`
- Verify repository access and permissions

**Repository Not Found**
- Verify `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` are correct
- Ensure token has access to the repository

**Empty Categories**
- Check repository has folders with `.md` files
- Verify branch name is correct (`main` vs `master`)

**API Tests Fail**
- Ensure `.env` file is configured correctly
- Check if repository exists and is accessible
- Verify all required environment variables are set

### Debug Commands
```bash
# Check repository access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$GITHUB_REPO_OWNER/$GITHUB_REPO_NAME

# Check rate limit
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

## Expected Results

**Unit Tests**: All 17 tests should pass
**Integration**: Categories auto-discovered, full document content returned
**API**: All endpoints return `status: "success"` with proper PR URLs
**Manual**: PRs created successfully in GitHub with correct content and labels