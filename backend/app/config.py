"""SENTINEL AI X — Application Configuration."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    RELEASE = "release"


class Settings(BaseSettings):
    """
    Central configuration loaded from environment variables.

    All NVIDIA Build model assignments are configurable so the system
    can swap models without changing any business logic.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────
    app_name: str = "sentinel-ai-x"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-to-a-random-64-char-string"

    # ── NVIDIA Build API ───────────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Model routing — assign by capability, not a single LLM
    nvidia_reasoning_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    nvidia_code_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    nvidia_lightweight_model: str = "nvidia/llama-3.3-nemotron-nano-8b-v1"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_rerank_model: str = "nvidia/llama-nemotron-rerank-v2"
    nvidia_vision_model: str = "nvidia/llama-nemotron-nano-vl-8b-v1"
    nvidia_safety_model: str = "nvidia/llama-guard-3-8b"

    # ── PostgreSQL ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://sentinel:sentinel_secret@localhost:5432/sentinel"

    # ── Redis ──────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Neo4j ──────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentinel_graph"

    # ── Additional LLM APIs (Optional) ─────────────────────────────
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # ── Qdrant ─────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "sentinel"

    # ── GitHub ─────────────────────────────────────────────────────
    github_app_id: str = ""
    github_app_slug: str = ""
    github_app_private_key: str = ""
    github_private_key: str = ""
    github_app_private_key_path: str = "./github-app-key.pem"
    github_app_installation_id: int = 0
    github_webhook_secret: str = ""
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    github_graphql_url: str = "https://api.github.com/graphql"
    frontend_url: str = "http://localhost:3000"

    # ── JWT Auth ───────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # ── Celery ─────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Paths ──────────────────────────────────────────────────────
    repo_cache_dir: Path = Path("/tmp/repos")

    # ── Convenience ────────────────────────────────────────────────
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() in {"release", "production", "prod"}:
            return False
        return value
    @property
    def is_production(self) -> bool:
        return self.app_env in {Environment.PRODUCTION, Environment.RELEASE}

    def get_model_for_tier(self, tier: str) -> str:
        """Return the configured model ID for a given capability tier."""
        tier_map = {
            "reasoning": self.nvidia_reasoning_model,
            "code": self.nvidia_code_model,
            "lightweight": self.nvidia_lightweight_model,
            "embedding": self.nvidia_embedding_model,
            "rerank": self.nvidia_rerank_model,
            "vision": self.nvidia_vision_model,
            "safety": self.nvidia_safety_model,
        }
        model = tier_map.get(tier)
        if model is None:
            raise ValueError(f"Unknown model tier: {tier!r}. Choose from {list(tier_map)}")
        return model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
