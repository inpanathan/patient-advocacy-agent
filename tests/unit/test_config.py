"""Tests for the configuration module."""

from __future__ import annotations

import pytest


class TestSettings:
    """Test layered configuration loading and validation."""

    def test_default_settings_load(self):
        """Settings load with defaults when no env vars or YAML override."""
        from src.utils.config import Settings

        s = Settings(app_env="dev")
        assert s.app_env == "dev"
        assert s.app_debug is True
        assert s.use_mocks is True

    def test_invalid_app_env_rejected(self):
        """Invalid app_env values raise ValidationError."""
        from src.utils.config import Settings

        with pytest.raises(ValueError, match="app_env must be one of"):
            Settings(app_env="invalid")

    def test_production_requires_secret_key(self, monkeypatch):
        """Production mode rejects default secret key."""
        from src.utils.config import Settings

        # Ensure .env file doesn't inject a SECRET_KEY value
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(ValueError, match="SECRET_KEY must be set in production"):
            Settings(app_env="production", app_debug=False, _env_file=None)

    def test_production_requires_debug_off(self):
        """Production mode requires debug=False."""
        from src.utils.config import Settings

        with pytest.raises(ValueError, match="APP_DEBUG must be false in production"):
            Settings(
                app_env="production",
                secret_key="real-secret-key-here",
                app_debug=True,
            )

    def test_valid_production_config(self):
        """Valid production config passes validation."""
        from src.utils.config import Settings

        s = Settings(
            app_env="production",
            app_debug=False,
            secret_key="a-real-production-secret",
        )
        assert s.app_env == "production"
        assert s.app_debug is False

    def test_nested_settings_defaults(self):
        """Nested settings have sensible defaults."""
        from src.utils.config import Settings

        s = Settings(app_env="dev")
        assert s.logging.level == "INFO"
        assert s.logging.format == "json"
        assert s.llm.temperature == 0.3
        assert s.embedding.dimension == 768
        assert s.vector_store.top_k == 10
        assert len(s.voice.supported_languages) == 5

    def test_settings_to_dict(self):
        """Settings can be serialized to dict."""
        from src.utils.config import Settings

        s = Settings(app_env="dev")
        d = s.model_dump()
        assert d["app_env"] == "dev"
        assert "logging" in d
        assert "llm" in d


class TestYamlConfigLoading:
    """Test YAML config file loading."""

    def test_load_yaml_config_missing_file(self):
        """Missing YAML file returns empty dict."""
        from src.utils.config import _load_yaml_config

        result = _load_yaml_config("nonexistent")
        assert result == {}

    def test_load_yaml_config_dev(self):
        """Dev YAML config loads successfully."""
        from src.utils.config import _load_yaml_config

        result = _load_yaml_config("dev")
        assert result.get("app_env") == "dev"
        assert result.get("use_mocks") is False
