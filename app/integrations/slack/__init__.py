# Slack integration module
from app.integrations.slack.client import SlackClient
from app.integrations.slack.parser import parse_permalink

__all__ = ["SlackClient", "parse_permalink"]
