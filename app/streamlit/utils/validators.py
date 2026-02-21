"""
Validation utilities for input data.
"""
import re


def validate_github_url(url: str) -> tuple[bool, str]:
    """
    Validate GitHub repository URL format.
    Only accepts full GitHub URLs in the format: https://github.com/owner/repo

    Args:
        url: The GitHub repository URL to validate

    Returns:
        tuple: (is_valid, message)
    """
    if not url:
        return False, "GitHub repository URL is required."

    # Pattern for full GitHub URL: https://github.com/owner/repo
    pattern = r'^https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+/?$'

    if not re.match(pattern, url.strip()):
        return False, "Invalid GitHub URL format. Please use the full URL format: https://github.com/owner/repo"

    return True, "Valid GitHub repository URL."


def validate_github_token(token: str) -> tuple[bool, str]:
    """
    Validate GitHub token format.
    Accepts tokens in the following formats:
    - ghp_: Classic Personal Access Token
    - github_pat_: Fine-grained Personal Access Token
    - gho_: OAuth Access Token
    - ghu_: GitHub App user access token
    - ghs_: GitHub App installation access token
    - ghr_: GitHub App refresh token

    Args:
        token: The GitHub token to validate

    Returns:
        tuple: (is_valid, message)
    """
    if not token:
        return False, "GitHub token is required."

    token = token.strip()

    # Check for valid token prefixes
    valid_prefixes = ('ghp_', 'github_pat_', 'gho_', 'ghu_', 'ghs_', 'ghr_')
    if token.startswith(valid_prefixes):
        # Basic length check (GitHub tokens are typically 40+ characters)
        if len(token) >= 40:
            return True, "Valid GitHub token format."
        else:
            return False, "GitHub token appears to be too short. Please verify your token."

    return False, "Invalid token format. GitHub tokens should start with one of: ghp_, github_pat_, gho_, ghu_, ghs_, ghr_"


def extract_owner_repo_from_url(url: str) -> tuple[str, str]:
    """
    Extract owner and repo name from GitHub URL.

    Args:
        url: GitHub repository URL (https://github.com/owner/repo)

    Returns:
        tuple: (owner, repo) or (None, None) if invalid
    """
    pattern = r'https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)/?$'
    match = re.match(pattern, url.strip())

    if match:
        return match.group(1), match.group(2)

    return None, None
