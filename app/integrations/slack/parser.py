"""
Slack Permalink Parser
Owner: ① Slack · GitHub Integration & Flow Owner

Parses Slack thread permalinks to extract channel_id and thread_ts.
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedPermalink:
    """Parsed Slack permalink components."""

    workspace: str
    channel_id: str
    thread_ts: str


def parse_permalink(permalink: str) -> ParsedPermalink:
    """
    Parse Slack thread permalink to extract channel and timestamp.

    Examples:
        https://myworkspace.slack.com/archives/C123ABC456/p1234567890123456
        -> channel_id: C123ABC456
        -> thread_ts: 1234567890.123456

    Args:
        permalink: Full Slack permalink URL

    Returns:
        ParsedPermalink with workspace, channel_id, and thread_ts

    Raises:
        ValueError: If permalink format is invalid
    """
    # Pattern: https://{workspace}.slack.com/archives/{channel_id}/p{timestamp}
    pattern = r"https://([^.]+)\.slack\.com/archives/([A-Z0-9]+)/p(\d+)"
    match = re.match(pattern, permalink)

    if not match:
        raise ValueError(f"Invalid Slack permalink format: {permalink}")

    workspace, channel_id, ts_raw = match.groups()

    # Convert timestamp: p1234567890123456 -> 1234567890.123456
    # Slack uses 10 digits before decimal, 6 after
    thread_ts = f"{ts_raw[:10]}.{ts_raw[10:]}"

    return ParsedPermalink(
        workspace=workspace,
        channel_id=channel_id,
        thread_ts=thread_ts,
    )
