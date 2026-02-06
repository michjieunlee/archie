# Slack Integration Setup

Quick setup guide for Archie's Slack integration with thread expansion and PII masking.

## Setup (3 Steps)

### 1. Create Slack App
- Go to https://api.slack.com/apps
- Create new app → "From scratch" → Name it "Archie"
- **Add Bot Scopes**:
  - `channels:history` - Read public channel messages
  - `channels:read` - View channel info
  - `group:history` - Read private channel messages
  - `group:read` - View private channel info
- Install app to your workspace
- Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 2. Configure Environment
```bash
# Add to .env file
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_ID=C1234567890  # Optional, default channel to extract from
```

### 3. Test Setup
```bash
# Test with real Slack API
python tests/integrations/test_slack_integration.py --real
```

## Testing Modes

Archie includes comprehensive testing for the Slack integration:

```bash
# Mock data testing (no setup required)
python tests/integrations/test_slack_integration.py --mock

# Mock data with detailed PII validation output
python tests/integrations/test_slack_integration.py --mock --verbose

# Real Slack API testing (requires setup above)
python tests/integrations/test_slack_integration.py --real

# Real API with detailed output showing raw AND processed messages
python tests/integrations/test_slack_integration.py --real --verbose

# Quick validation (fast mock test)
python tests/integrations/test_slack_integration.py --quick

# List available channels (setup helper)
python tests/integrations/test_slack_integration.py --list-channels
```

### What Gets Tested
- ✅ **Thread expansion** with chronological insertion and global indexing
- ✅ **Conversation fetching**: Direct StandardizedConversation output  
- ✅ **Global indexing**: Sequential idx assignment with parent_idx references
- ✅ **Separation of concerns**: Fetch → Mask → Process (separate steps)
- ✅ **PII masking** with USER_1, USER_2 format (separate step)
- ✅ **Enhanced PII validation** with before/after content visibility (verbose mode)
- ✅ **API connectivity** validation (real mode only)
- ✅ **Max 100 message limit** enforcement

## Usage

Once configured, the Slack integration:

1. **Fetches conversations** with complete thread expansion and global indexing
2. **Preserves context** with chronological thread insertion and parent_idx references  
3. **Returns StandardizedConversation** with idx-based message ordering
4. **Separates PII masking** as independent processing step
5. **Provides rich metadata** including participant counts and processing stats

**API Endpoint**: `GET /api/slack/fetch` (returns unmasked StandardizedConversation)

### New Architecture

```python
# Step 1: Fetch conversations (pure fetching, no PII masking)
conversation = await client.fetch_conversations_with_threads(limit=50)

# Step 2: Apply PII masking separately  
pii_masker = PIIMasker()
masked_conversations = await pii_masker.mask_threads([conversation])

# Result: Clean separation of concerns
```

### Data Structure

**StandardizedConversation** with global message indexing:
```python
messages = [
    {idx: 0, parent_idx: None, content: "Main message 1"},
    {idx: 1, parent_idx: None, content: "Main message 2"}, 
    {idx: 2, parent_idx: 1, content: "Reply to message 2"},
    {idx: 3, parent_idx: 1, content: "Another reply to message 2"},
    {idx: 4, parent_idx: None, content: "Main message 3"}
]
```

*For complete API documentation including parameters, examples, and response formats, see [`docs/API_INTEGRATION.md`](./API_INTEGRATION.md).*

## Troubleshooting

### Common Issues

**❌ "SLACK_BOT_TOKEN not found"**
- Add bot token to `.env` file
- Format: `SLACK_BOT_TOKEN=xoxb-your-token-here`

**❌ "No messages found"**
- Check if bot is added to the channel
- Verify `SLACK_CHANNEL_ID` format (starts with `C`)
- Try different channel or time range

**❌ "Slack API error"**
- Verify required bot scopes are added
- Confirm app is installed to workspace
- Check token is for correct workspace

**❌ "Missing bot scopes"**
- Go to **OAuth & Permissions** in your Slack app
- Add required scopes, then **reinstall app**
- Copy the new bot token if regenerated

### Getting Channel ID

**Method 1**: Right-click channel → "Copy link" → ID is after `/archives/`
**Method 2**: Use web Slack → Channel URL contains the ID
**Format**: `C1234567890` (starts with C, followed by numbers/letters)

### Test Channel Setup

For optimal testing, create a test channel with:
- Main messages with some threaded replies
- 2-3 different participants
- Sample PII data (emails, phone numbers) for masking tests
- Mix of message types (text, reactions, attachments)

## Security & Permissions

### Required Bot Scopes
- `channels:history` - Read public channel messages
- `channels:read` - View public channel information
- `group:history` - Read private channel messages
- `group:read` - View private channel information

### Data Safety
- Bot token stored securely in `.env` (never committed to git)
- PII automatically masked with USER_1, USER_2 format
- **Read-only permissions** - bot cannot post messages
- Consider dedicated test channels for development

---

**For technical details, API specifications, and response formats, see [`docs/API_INTEGRATION.md`](./API_INTEGRATION.md).**