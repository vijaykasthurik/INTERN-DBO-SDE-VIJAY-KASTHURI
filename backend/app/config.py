"""Application configuration module using Pydantic Settings.

Manages environment variables, default configurations, security parameters,
database URLs, and LLM provider selections with full type safety.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lumen Application Settings."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core App
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Lumen AI Data Analyst", alias="APP_NAME")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Security & Encryption
    secret_key: str = Field(
        default="development-insecure-secret-key-32-chars-minimum-required",
        alias="SECRET_KEY",
    )
    key_encryption_secret: str = Field(
        default="",
        alias="KEY_ENCRYPTION_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_days: int = Field(default=7, alias="JWT_REFRESH_EXPIRE_DAYS")
    shared_pool_hourly_limit: int = Field(default=30, alias="SHARED_POOL_HOURLY_LIMIT")

    # Storage & Database
    database_url: str = Field(default="sqlite:///./data/lumen.db", alias="DATABASE_URL")
    data_dir: str = Field(default="./data", alias="DATA_DIR")
    max_upload_mb: int = Field(default=50, alias="MAX_UPLOAD_MB")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    # LLM Settings
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_fallback_order: str = Field(
        default="mock,gemini,groq,openrouter,openai_compat",
        alias="LLM_FALLBACK_ORDER",
    )

    # Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_fast: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL_FAST")
    gemini_model_strong: str = Field(
        default="gemini-2.0-flash-thinking-exp-01-21",
        alias="GEMINI_MODEL_STRONG",
    )

    # Groq Shared Pool
    groq_api_url: str = Field(
        default="https://api.groq.com/openai/v1/chat/completions",
        alias="GROQ_API_URL",
    )
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_api_key_1: str = Field(default="", alias="GROQ_API_KEY_1")
    groq_api_key_2: str = Field(default="", alias="GROQ_API_KEY_2")
    groq_api_key_3: str = Field(default="", alias="GROQ_API_KEY_3")
    groq_api_key_4: str = Field(default="", alias="GROQ_API_KEY_4")
    groq_api_key_5: str = Field(default="", alias="GROQ_API_KEY_5")
    groq_api_key_6: str = Field(default="", alias="GROQ_API_KEY_6")
    groq_api_key_7: str = Field(default="", alias="GROQ_API_KEY_7")
    groq_model_fast: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL_FAST")
    groq_model_strong: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL_STRONG")

    # Z.AI Shared
    zai_api_key: str = Field(default="", alias="ZAI_API_KEY")
    zai_model: str = Field(default="glm-4.5", alias="ZAI_MODEL")

    # Hugging Face Shared
    hf_api_key: str = Field(default="", alias="HF_API_KEY")
    hf_model: str = Field(default="meta-llama/Llama-3.1-8B-Instruct", alias="HF_MODEL")

    # OpenRouter
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model_fast: str = Field(
        default="google/gemini-2.0-flash-001",
        alias="OPENROUTER_MODEL_FAST",
    )
    openrouter_model_strong: str = Field(
        default="anthropic/claude-3.5-sonnet",
        alias="OPENROUTER_MODEL_STRONG",
    )

    # OpenAI Compatible
    openai_compat_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_COMPAT_BASE_URL",
    )
    openai_compat_api_key: str = Field(default="", alias="OPENAI_COMPAT_API_KEY")
    openai_compat_model_fast: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_COMPAT_MODEL_FAST",
    )
    openai_compat_model_strong: str = Field(
        default="gpt-4o",
        alias="OPENAI_COMPAT_MODEL_STRONG",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list of trimmed strings."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def groq_keys_pool(self) -> list[str]:
        """Collect all matching GROQ_API_KEY_<n> or primary GROQ_API_KEY from environment or settings."""
        import os

        keys: list[str] = []
        for i in range(1, 21):
            val = getattr(self, f"groq_api_key_{i}", None) or os.getenv(f"GROQ_API_KEY_{i}")
            if val and val.strip():
                keys.append(val.strip())

        if not keys and self.groq_api_key:
            keys.append(self.groq_api_key.strip())

        return keys

    @property
    def fallback_providers_list(self) -> list[str]:
        """Return list of fallback provider identifiers."""
        return [p.strip() for p in self.llm_fallback_order.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton instance of application settings."""
    return Settings()
