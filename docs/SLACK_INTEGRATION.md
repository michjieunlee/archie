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
- ✅ **Thread expansion** with context preservation
- ✅ **Complete pipeline**: Extract → Mask → Convert
- ✅ **Message ordering** (no chronological sorting)
- ✅ **PII masking** with USER_1, USER_2 format
- ✅ **Enhanced PII validation** with before/after content visibility (verbose mode)
- ✅ **API connectivity** validation (real mode only)

## Usage

Once configured, the Slack integration automatically:

1. **Extracts conversations** with complete thread expansion
2. **Preserves context** by keeping thread replies with parent messages
3. **Applies PII masking** with USER_1, USER_2 format
4. **Provides rich metadata** including participant counts and processing stats

**API Endpoint**: `GET /api/slack/extract`

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