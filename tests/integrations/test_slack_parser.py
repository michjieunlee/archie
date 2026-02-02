"""
Tests for Slack permalink parser.
Owner: ① Slack · GitHub Integration & Flow Owner
"""

import pytest
from app.integrations.slack.parser import parse_permalink, ParsedPermalink


class TestParsePermalink:
    """Test suite for Slack permalink parsing."""

    def test_valid_permalink(self):
        """Test parsing a valid Slack permalink."""
        permalink = "https://myworkspace.slack.com/archives/C123ABC456/p1234567890123456"
        result = parse_permalink(permalink)

        assert isinstance(result, ParsedPermalink)
        assert result.workspace == "myworkspace"
        assert result.channel_id == "C123ABC456"
        assert result.thread_ts == "1234567890.123456"

    def test_invalid_permalink_format(self):
        """Test that invalid formats raise ValueError."""
        invalid_urls = [
            "https://slack.com/archives/C123/p123",
            "https://myworkspace.slack.com/messages/C123",
            "not-a-url",
        ]
        for url in invalid_urls:
            with pytest.raises(ValueError):
                parse_permalink(url)
