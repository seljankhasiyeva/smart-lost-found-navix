# src/config.py
"""
Central configuration for the Smart Lost & Found project.

Single source of truth for all environment variables.
Every other module imports `settings` from here — never os.environ directly.

Usage:
    from src.config import settings
    print(settings.llm_provider)
"""

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # AI / Vision-Language Model Provider
    # ------------------------------------------------------------------
    llm_provider: str = Field(
        default="anthropic",
        description="Main LLM/VLM provider: 'anthropic' | 'openai' | 'gemini'.",
    )

    llm_model: str = Field(
        default="claude-sonnet-4-6",
        description="Model name used for vision-language item description.",
    )

    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key. Store only in .env — never in source code.",
    )

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key. Store only in .env — never in source code.",
    )

    google_api_key: str = Field(
        default="",
        description="Google API key for Gemini provider. Store only in .env.",
    )

    # ------------------------------------------------------------------
    # Fallback Provider  (Bonus: multi-provider failover)
    # ------------------------------------------------------------------
    fallback_llm_provider: str = Field(
        default="",
        description="Secondary LLM provider used if primary fails. Leave empty to disable failover.",
    )

    fallback_llm_model: str = Field(
        default="",
        description="Model name for the fallback LLM provider.",
    )

    # ------------------------------------------------------------------
    # Embedding Provider
    # ------------------------------------------------------------------
    embedding_provider: str = Field(
        default="openai",
        description="Provider used for text embeddings: 'openai' | 'gemini'.",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name.",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql://postgres:dev@localhost:5432/lostfound",
        description="PostgreSQL connection URL (asyncpg format).",
    )

    # ------------------------------------------------------------------
    # Image / File Storage
    # ------------------------------------------------------------------
    image_store_dir: str = Field(
        default="image_store",
        validation_alias=AliasChoices("IMAGE_STORE_DIR", "IMAGE_STORAGE_DIR"),
        description="Directory where uploaded item images are stored. Gitignored at runtime.",
    )

    max_image_size_mb: int = Field(
        default=5,
        description="Maximum allowed image upload size in megabytes.",
    )

    # ------------------------------------------------------------------
    # AI Runtime / Concurrency
    # ------------------------------------------------------------------
    ai_concurrency_limit: int = Field(
        default=5,
        description="asyncio.Semaphore bound — max concurrent AI requests.",
    )

    ai_request_timeout: int = Field(
        default=30,
        description="Per-call timeout for AI requests in seconds.",
    )

    # ------------------------------------------------------------------
    # Token-aware Rate Limiting  (Bonus: token-aware rate limiter)
    # ------------------------------------------------------------------
    anthropic_tpm: int = Field(
        default=40000,
        description="Anthropic tokens-per-minute limit used by TokenBudget.",
    )

    openai_tpm: int = Field(
        default=90000,
        description="OpenAI tokens-per-minute limit used by TokenBudget.",
    )

    # ------------------------------------------------------------------
    # HTTP API
    # ------------------------------------------------------------------
    http_host: str = Field(
        default="0.0.0.0",
        description="Host address for the uvicorn HTTP server.",
    )

    http_port: int = Field(
        default=8000,
        description="Port for the uvicorn HTTP server.",
    )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL.",
    )


# Module-level singleton — import this everywhere
settings = Settings()
