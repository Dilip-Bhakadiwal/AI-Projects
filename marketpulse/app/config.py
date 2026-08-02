"""
app/config.py — Centralised settings using pydantic-settings.
All env vars are loaded from .env automatically.
"""
import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "marketpulse/.env", os.path.join(os.path.dirname(__file__), "../.env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketpulse"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not v:
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/marketpulse"
        # Ensure postgresql+asyncpg:// scheme for SQLAlchemy async engine
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg does not support 'sslmode=', it requires 'ssl='
        if "sslmode=" in v:
            v = v.replace("sslmode=", "ssl=")
        return v

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    nvidia_api_key: str = ""
    openrouter_api_key: str = ""

    # API Security
    api_key: str = "dev-key"

    # Ingestion
    poll_interval_minutes: int = 15
    price_change_alert_threshold: float = 0.02  # 2%

    # Logging
    log_level: str = "INFO"

    @property
    def llm_base_url(self) -> str:
        """Use NVIDIA NIM if key is set, otherwise OpenRouter."""
        if self.nvidia_api_key:
            return "https://integrate.api.nvidia.com/v1"
        return "https://openrouter.ai/api/v1"

    @property
    def llm_api_key(self) -> str:
        if self.nvidia_api_key:
            return self.nvidia_api_key
        if self.openrouter_api_key:
            return self.openrouter_api_key
        raise ValueError("No LLM API key configured. Set NVIDIA_API_KEY or OPENROUTER_API_KEY in .env")

    @property
    def llm_model(self) -> str:
        """Free model — NVIDIA NIM meta/llama-3.1-8b-instruct or OpenRouter Gemma."""
        if self.nvidia_api_key:
            return "meta/llama-3.1-8b-instruct"
        return "google/gemma-4-26b-a4b-it:free"


# Single instance used everywhere
settings = Settings()
