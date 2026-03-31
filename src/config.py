"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Central configuration — reads from .env or OS env vars."""

    # ── Supabase ──────────────────────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon/public key")
    supabase_service_key: str = Field(..., description="Supabase service-role key")

    # ── LLM Providers ─────────────────────────────────────────
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")

    # ── Application ───────────────────────────────────────────
    app_env: str = Field("development", description="development | staging | production")
    log_level: str = Field("INFO", description="Logging level")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Singleton-like accessor for settings."""
    return Settings()
