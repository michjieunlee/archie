"""
API client for Archie backend.
Makes real HTTP calls to the FastAPI backend at app/api/routes.
"""

from typing import Any
import requests
import logging
from config.settings import API_BASE_URL, API_TIMEOUT
from utils.validators import (
    validate_github_url,
    validate_github_token,
    extract_owner_repo_from_url,
)

logger = logging.getLogger(__name__)


def _extract_error_detail(e: requests.HTTPError) -> str:
    """Pull a human-readable detail string from an HTTPError response."""
    try:
        return e.response.json().get("detail", str(e))
    except Exception:
        return str(e)


def _api_get(endpoint: str, params: dict | None = None) -> requests.Response:
    """Make a GET request to the backend API."""
    url = f"{API_BASE_URL}{endpoint}"
    return requests.get(url, params=params, timeout=API_TIMEOUT)


def _api_post(endpoint: str, json: dict | None = None) -> requests.Response:
    """Make a POST request to the backend API."""
    url = f"{API_BASE_URL}{endpoint}"
    return requests.post(url, json=json, timeout=API_TIMEOUT)


def connect_github(url: str, token: str) -> dict[str, Any]:
    """
    Validate inputs locally, then POST credentials to the backend.

    Calls: POST /api/github/connect

    Returns:
        dict with keys: success (bool), message (str), repo_full_name (str|None)
    """
    url_valid, url_msg = validate_github_url(url)
    if not url_valid:
        return {"success": False, "message": url_msg, "repo_full_name": None}

    token_valid, token_msg = validate_github_token(token)
    if not token_valid:
        return {"success": False, "message": token_msg, "repo_full_name": None}

    try:
        resp = _api_post("/api/github/connect", json={"repo_url": url, "token": token})
        resp.raise_for_status()
        data = resp.json()
        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "repo_full_name": data.get("repo_full_name"),
        }
    except requests.ConnectionError:
        return {"success": False, "message": "Cannot connect to backend API. Is it running?", "repo_full_name": None}
    except requests.HTTPError as e:
        detail = _extract_error_detail(e)
        return {"success": False, "message": f"GitHub connect failed: {detail}", "repo_full_name": None}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}", "repo_full_name": None}


def disconnect_github(url: str) -> dict:
    """
    Disconnect from a GitHub repository and clear backend credentials.

    Calls: POST /api/github/disconnect

    Returns:
        dict with keys: success (bool), message (str)
    """
    try:
        resp = _api_post("/api/github/disconnect")
        resp.raise_for_status()
        data = resp.json()
        return {"success": data.get("success", True), "message": data.get("message", "Disconnected")}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}"}


def connect_slack(channel_id: str) -> dict:
    """
    Store Slack channel credentials on the backend and validate the channel.

    Calls: POST /api/slack/connect

    Returns:
        dict with keys: success (bool), message (str), channel_name (str|None)
    """
    channel_id = channel_id.strip()

    if not channel_id:
        return {
            "success": False,
            "message": "Channel ID is required.",
            "channel_name": None,
        }

    try:
        resp = _api_post("/api/slack/connect", json={"channel_id": channel_id})
        resp.raise_for_status()
        data = resp.json()
        return {
            "success": data.get("success", False),
            "message": data.get("message", ""),
            "channel_name": data.get("channel_name"),
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "message": "Cannot connect to backend API. Is it running?",
            "channel_name": None,
        }
    except requests.HTTPError as e:
        detail = _extract_error_detail(e)
        return {
            "success": False,
            "message": f"Slack connection failed: {detail}",
            "channel_name": None,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {e}",
            "channel_name": None,
        }


def disconnect_slack(channel_id: str) -> dict:
    """
    Disconnect from a Slack channel and clear backend credentials.

    Calls: POST /api/slack/disconnect

    Returns:
        dict with keys: success (bool), message (str)
    """
    try:
        resp = _api_post("/api/slack/disconnect")
        resp.raise_for_status()
        data = resp.json()
        return {"success": data.get("success", True), "message": data.get("message", "Disconnected")}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}"}


# ── KB endpoints ──────────────────────────────────────────────────────
# Main entrypoint with three use case endpoints:
# 1. GET /api/kb/from-slack - Update KB from Slack messages
# 2. POST /api/kb/from-text - Update KB from free text
# 3. POST /api/kb/query - Query knowledge base (Q&A)

def kb_from_slack(
    from_datetime: str | None = None,
    to_datetime: str | None = None,
    limit: int = 20,
) -> dict:
    """
    Process Slack messages into a KB article.

    Calls: GET /api/kb/from-slack

    Returns:
        The KBProcessingResponse dict from the backend.
    """
    params = {"limit": limit}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime

    try:
        resp = _api_get("/api/kb/from-slack", params=params)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "action": "error", "reason": "Cannot connect to backend API"}
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"status": "error", "action": "error", "reason": detail}
    except Exception as e:
        return {"status": "error", "action": "error", "reason": str(e)}


def kb_from_text(text: str, title: str | None = None, metadata: dict | None = None) -> dict:
    """
    Process free text into a KB article.

    Calls: POST /api/kb/from-text

    Returns:
        The KBProcessingResponse dict from the backend.
    """
    payload = {"text": text}
    if title:
        payload["title"] = title
    if metadata:
        payload["metadata"] = metadata

    try:
        resp = _api_post("/api/kb/from-text", json=payload)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "action": "error", "reason": "Cannot connect to backend API"}
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"status": "error", "action": "error", "reason": detail}
    except Exception as e:
        return {"status": "error", "action": "error", "reason": str(e)}


def kb_query(query: str, conversation_history: list | None = None) -> dict:
    """
    Query the knowledge base.

    Args:
        query: User's question
        conversation_history: Optional recent conversation for context

    Calls: POST /api/kb/query

    Returns:
        The KBQueryResponse dict from the backend.
    """
    payload = {"query": query}
    if conversation_history:
        payload["conversation_history"] = conversation_history

    try:
        resp = _api_post("/api/kb/query", json=payload)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "query": query, "answer": None, "sources": [], "total_sources": 0, "reason": "Cannot connect to backend API"}
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"status": "error", "query": query, "answer": None, "sources": [], "total_sources": 0, "reason": detail}
    except Exception as e:
        return {"status": "error", "query": query, "answer": None, "sources": [], "total_sources": 0, "reason": str(e)}


def mask_message(text: str) -> dict:
    """
    Mask PII in a text message.

    Calls: POST /api/kb/mask-message

    Returns:
        dict with keys:
        - masked_text (str): The text with PII masked
        - is_masked (bool): Whether masking was applied
    """
    try:
        resp = _api_post("/api/kb/mask-message", json={"text": text})
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        logger.warning("Cannot connect to backend API for masking, returning original text")
        return {"masked_text": text, "is_masked": False, "error": "Cannot connect to backend API"}
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        logger.error(f"Error masking message: {detail}")
        return {"masked_text": text, "is_masked": False, "error": detail}
    except Exception as e:
        logger.error(f"Unexpected error masking message: {e}")
        return {"masked_text": text, "is_masked": False, "error": str(e)}
