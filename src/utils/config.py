"""Layered configuration module with startup validation.

Loads config in order of precedence (highest wins):
  1. Environment variables (from .env or system)
  2. Environment-specific YAML file (configs/{APP_ENV}.yaml)
  3. Hardcoded defaults

Fails fast at startup if required values are missing or invalid.

Covers: REQ-CFG-001, REQ-CFG-002, REQ-CFG-003
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    show_locals: bool = False


class LLMSettings(BaseSettings):
    """LLM / MedGemma configuration."""

    medgemma_api_key: str = ""
    medgemma_model_id: str = "google/medgemma-4b-it"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_seconds: int = 30
    google_api_key: str = ""
    device: str = "auto"


class EmbeddingSettings(BaseSettings):
    """SigLIP-2 embedding model configuration."""

    model_path: str = "models/siglip2"
    model_id: str = "google/siglip-so400m-patch14-384"
    dimension: int = 768
    device: str = "auto"


class VectorStoreSettings(BaseSettings):
    """ChromaDB / vector store configuration."""

    persist_dir: str = "data/chroma"
    collection_name: str = "scin_embeddings"
    top_k: int = 10


class VoiceSettings(BaseSettings):
    """Voice pipeline configuration (STT, TTS, language detection)."""

    stt_api_key: str = ""
    tts_api_key: str = ""
    supported_languages: list[str] = Field(
        default=["hi", "bn", "ta", "sw", "es"],
    )
    stt_timeout_seconds: int = 15
    tts_timeout_seconds: int = 15
    whisper_model_size: str = "large-v3"
    piper_voices_dir: str = "models/piper"
    google_cloud_project: str = ""
    google_application_credentials: str = ""


class SCINSettings(BaseSettings):
    """SCIN dataset paths."""

    data_dir: str = "data/raw/scin"


class EmailSettings(BaseSettings):
    """SMTP configuration for case history delivery."""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    case_history_recipient: str = ""


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    enabled: bool = True
    host: str = "localhost"
    port: int = 5432
    name: str = "patient_advocacy"
    user: str = "patient_advocacy"
    password: str = ""
    pool_size: int = 5
    echo: bool = False

    @property
    def async_url(self) -> str:
        """SQLAlchemy async connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        """SQLAlchemy sync connection URL (for Alembic)."""
        return f"postgresql://{self.user}:{self.password}" f"@{self.host}:{self.port}/{self.name}"


class ServerSettings(BaseSettings):
    """Application server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False


class Settings(BaseSettings):
    """Root application settings.

    Merges environment variables, YAML config, and defaults.
    Validates at startup — the app will not start with invalid config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---- Top-level ----
    app_env: str = "dev"
    app_debug: bool = True
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    use_mocks: bool = True
    model_backend: str = "mock"

    # ---- Nested settings ----
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    scin: SCINSettings = Field(default_factory=SCINSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"dev", "staging", "production", "test"}
        if v not in allowed:
            msg = f"app_env must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("model_backend")
    @classmethod
    def validate_model_backend(cls, v: str) -> str:
        allowed = {"mock", "local", "cloud"}
        if v not in allowed:
            msg = f"model_backend must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Fail fast if production config is incomplete."""
        if self.app_env == "production":
            if self.secret_key == "CHANGE-ME-IN-PRODUCTION":
                msg = "SECRET_KEY must be set in production"
                raise ValueError(msg)
            if self.app_debug:
                msg = "APP_DEBUG must be false in production"
                raise ValueError(msg)
        return self


def _load_yaml_config(env: str) -> dict[str, Any]:
    """Load environment-specific YAML config if it exists."""
    config_path = PROJECT_ROOT / "configs" / f"{env}.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def load_settings() -> Settings:
    """Create and validate application settings.

    Merges: defaults < YAML config < environment variables.
    """
    import os

    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    env = os.getenv("APP_ENV", "dev")
    yaml_config = _load_yaml_config(env)

    return Settings(**yaml_config)


# Singleton — import this from anywhere
settings = load_settings()
