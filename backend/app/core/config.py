import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AlphaHive"
    VERSION: str = "1.0"
    ENVIRONMENT: str = Field("development", description="Deployment environment: development | production")

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "alphahive_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # LLM — LiteLLM proxy (OpenAI-compatible). One primary model + one fallback,
    # used by every agent (router, specialists, synthesis) — no per-role tiers.
    LITELLM_BASE_URL: Optional[str] = None
    LITELLM_API_KEY: Optional[str] = None
    LLM_MODEL_PRIMARY: str = "google/gemini-3.5-flash"
    LLM_MODEL_FALLBACK: str = "anthropic/claude-haiku-4-5"
    # Stronger model reserved for the final synthesis/decision step, which reads every
    # specialist agent's output and writes the actual investment recommendation.
    LLM_MODEL_SYNTHESIS: str = "anthropic/claude-sonnet-4-6"
    # Embedding model for SEC-filing RAG. Leave empty to disable real embeddings and use
    # the deterministic lexical mock (many LiteLLM keys have no embedding-model access —
    # attempting one just yields repeated 401s). Set to a model your key can reach to
    # enable true semantic SEC search, e.g. "openai/text-embedding-3-small".
    EMBEDDING_MODEL: Optional[str] = None

    # Market data API Keys
    FINNHUB_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    TWELVE_DATA_API_KEY: Optional[str] = None
    MARKETAUX_API_KEY: Optional[str] = None

    # Token Budget (LLM cost control)
    MAX_TOKENS_PER_SESSION: int = Field(
        100000,
        description="Maximum LLM tokens allowed per session before the budget gate blocks new runs."
    )

    # CORS — comma-separated allowed origins for production hardening
    # e.g. CORS_ORIGINS=https://app.example.com,https://dashboard.example.com
    CORS_ORIGINS: str = Field(
        "*",
        description="Comma-separated allowed CORS origins. Use '*' for open development access."
    )

    model_config = SettingsConfigDict(
        # config.py -> core -> app -> backend -> repo root (4 levels up)
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_cors_origins(self) -> List[str]:
        """Parse and return CORS origins as a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values) -> str:
        if isinstance(v, str) and v:
            return v
        # Access parameters dynamically from the validation context/values dict
        data = values.data
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "postgrespassword")
        host = data.get("POSTGRES_HOST", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "alphahive_db")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], values) -> str:
        if isinstance(v, str) and v:
            return v
        data = values.data
        host = data.get("REDIS_HOST", "localhost")
        port = data.get("REDIS_PORT", 6379)
        return f"redis://{host}:{port}/0"


settings = Settings()
