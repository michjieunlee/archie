from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Archie"
    debug: bool = False

    # Slack
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # GitHub
    github_token: str = ""
    github_repo_owner: str = ""
    github_repo_name: str = ""
    github_default_branch: str = "main"

    # OpenAI (for KB Extraction via gen_ai_hub proxy)
    # No API key needed - uses gen_ai_hub proxy
    openai_model: str = "gpt-5"
    temperature: float = 0.0
    max_tokens: int = 4000

    # SAP GenAI SDK
    sap_genai_api_url: str = ""
    sap_genai_api_key: str = ""
    sap_genai_deployment_id: str = ""
    sap_genai_endpoint: str = ""

    # Processing Configuration
    batch_size_masking: int = 20  # Messages per orchestration call
    orchestration_timeout: int = 30  # Seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
