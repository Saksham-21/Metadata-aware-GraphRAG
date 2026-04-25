"""
app/core/config.py
──────────────────
Central settings loaded once at startup from .env (or environment variables).
Access anywhere via:  from app.core.config import settings
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    PROJECT_NAME: str = "Metadata-Aware GraphRAG"
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ──────────────────────────────────────────────────
    # Comma-separated list in .env  →  "http://localhost:3000,http://..."
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── PostgreSQL ────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://...   (runtime async)
    SYNC_DATABASE_URL: str  # postgresql+psycopg2://...  (alembic only)

    # ── JWT ───────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 h

    # ── ChromaDB ──────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_PREFIX: str = "graphrag"

    # ── Neo4j ─────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ── Gemini ────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — reads .env once, reused everywhere."""
    return Settings()


# Convenience alias used throughout the app
settings: Settings = get_settings()
