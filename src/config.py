"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Any


class Settings(BaseSettings):
    """Central configuration — reads from .env or OS env vars."""

    # ── Supabase ──────────────────────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon/public key")
    supabase_service_key: str = Field(..., description="Supabase service-role key")

    # ── Supabase Auth (Phase 5) ────────────────────────────────
    supabase_jwt_secret: str = Field("", description="Supabase JWT signing secret for token verification")

    # ── LLM Providers ─────────────────────────────────────────
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    groq_api_key: Optional[str] = Field(None, description="Groq API key")
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API key")
    openrouter_model: str = Field("openrouter/free", description="OpenRouter model name")
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API key")
    
    # Selection
    llm_provider: str = Field("groq", description="Preferred LLM provider (groq | openrouter | openai | anthropic)")
    groq_model: str = Field("groq/llama-3.3-70b-versatile", description="Default Groq model")

    def get_llm(self) -> Any:
        """Return a configured CrewAI LLM instance based on llm_provider."""
        from crewai import LLM

        if self.llm_provider == "groq":
            return LLM(model=self.groq_model, api_key=self.groq_api_key)
        elif self.llm_provider == "openrouter":
            return LLM(model=self.openrouter_model, api_key=self.openrouter_api_key)
        elif self.llm_provider == "openai":
            return LLM(model="gpt-4o", api_key=self.openai_api_key)
        elif self.llm_provider == "anthropic":
            return LLM(model="claude-3-5-sonnet-20240620", api_key=self.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    # ── Application ───────────────────────────────────────────
    app_env: str = Field("development", description="development | staging | production")
    log_level: str = Field("INFO", description="Logging level")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Ignore NEXT_PUBLIC_* and other extra fields from .env
    }


def get_settings() -> Settings:
    """Singleton-like accessor for settings."""
    return Settings()
