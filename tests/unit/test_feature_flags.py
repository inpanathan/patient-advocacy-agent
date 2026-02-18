"""Tests for the feature flags module."""

from __future__ import annotations


class TestFeatureFlags:
    """Test feature flags loading and defaults."""

    def test_default_flags_all_disabled(self):
        """All flags default to False."""
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.voice_pipeline is False
        assert flags.image_capture is False
        assert flags.rag_retrieval is False
        assert flags.soap_generation is False
        assert flags.medgemma_live is False

    def test_from_env_enables_flag(self, monkeypatch):
        """Setting FEATURE_VOICE_PIPELINE=true enables the flag."""
        monkeypatch.setenv("FEATURE_VOICE_PIPELINE", "true")
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags.from_env()
        assert flags.voice_pipeline is True

    def test_from_env_disables_flag(self, monkeypatch):
        """Setting FEATURE_VOICE_PIPELINE=false keeps the flag disabled."""
        monkeypatch.setenv("FEATURE_VOICE_PIPELINE", "false")
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags.from_env()
        assert flags.voice_pipeline is False

    def test_from_env_case_insensitive(self, monkeypatch):
        """Environment variable values are case-insensitive."""
        monkeypatch.setenv("FEATURE_IMAGE_CAPTURE", "TRUE")
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags.from_env()
        assert flags.image_capture is True

    def test_from_env_numeric_values(self, monkeypatch):
        """Numeric '1' and '0' work as true/false."""
        monkeypatch.setenv("FEATURE_RAG_RETRIEVAL", "1")
        monkeypatch.setenv("FEATURE_SOAP_GENERATION", "0")
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags.from_env()
        assert flags.rag_retrieval is True
        assert flags.soap_generation is False

    def test_from_env_unknown_vars_ignored(self, monkeypatch):
        """Unknown FEATURE_ vars don't cause errors."""
        monkeypatch.setenv("FEATURE_NONEXISTENT", "true")
        from src.utils.feature_flags import FeatureFlags

        flags = FeatureFlags.from_env()
        assert not hasattr(flags, "nonexistent")
