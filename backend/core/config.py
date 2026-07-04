"""
core/config.py

Centralized application configuration using pydantic-settings.
All values are loaded from environment variables / `.env` file.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Research Platform API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    SECRET_KEY: str = "change-this-to-a-long-random-string"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://research_user:research_pass@localhost:5432/research_platform"
    )

    # ── Redis / Celery ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── ChromaDB ─────────────────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "research_knowledge_base"

    # ── Embeddings ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # ── OpenRouter (primary LLM provider) ───────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL_PRIMARY: str = "deepseek/deepseek-chat-v3:free"
    OPENROUTER_MODEL_REASONING: str = "deepseek/deepseek-r1:free"
    OPENROUTER_MODEL_FAST: str = "qwen/qwen3-8b:free"
    OPENROUTER_MODEL_ALT: str = "meta-llama/llama-3.3-70b-instruct:free"
    OPENROUTER_MODEL_LIGHT: str = "google/gemma-3-12b-it:free"

    # ── Groq (fallback LLM provider) ────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL_PRIMARY: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FAST: str = "gemma2-9b-it"

    # ── Search Tools ─────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""

    # ── Clerk Auth ───────────────────────────────────────────────────────
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_SECRET_KEY: str = ""
    CLERK_JWT_ISSUER: str = ""
    CLERK_WEBHOOK_SECRET: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30

    # ── Abuse / cost controls ────────────────────────────────────────────
    # Caps how many non-terminal research sessions a single user may have
    # running at once — protects shared free-tier LLM/search quotas from
    # being exhausted by one user firing off many concurrent runs.
    MAX_CONCURRENT_RESEARCH_SESSIONS: int = 2

    # ── Reports / PDF ────────────────────────────────────────────────────
    REPORTS_STORAGE_PATH: str = "./storage/reports"
    MAX_REPORT_SOURCES: int = 20

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-parsing env on every import."""
    return Settings()


settings = get_settings()
