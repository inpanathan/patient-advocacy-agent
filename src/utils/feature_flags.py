"""Feature flags module for gradual rollout and A/B testing.

Feature flags allow enabling/disabling features without code changes.
Flags can be overridden via environment variables with the prefix FEATURE_.

Covers: REQ-CFG-005
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class FeatureFlags:
    """Runtime feature flags.

    Each flag defaults to False (disabled). Override by setting
    environment variables like FEATURE_VOICE_PIPELINE=true.
    """

    voice_pipeline: bool = False
    image_capture: bool = False
    rag_retrieval: bool = False
    soap_generation: bool = False
    case_history_email: bool = False
    medgemma_live: bool = False
    bias_monitoring: bool = False
    distributed_tracing: bool = False

    @classmethod
    def from_env(cls) -> FeatureFlags:
        """Load flags from environment variables.

        Any env var matching FEATURE_<FLAG_NAME>=true enables the flag.
        """
        kwargs: dict[str, bool] = {}
        for f in cls.__dataclass_fields__:
            env_key = f"FEATURE_{f.upper()}"
            env_val = os.getenv(env_key, "").lower()
            if env_val in ("true", "1", "yes"):
                kwargs[f] = True
            elif env_val in ("false", "0", "no"):
                kwargs[f] = False
        return cls(**kwargs)


# Singleton — import this from anywhere
flags = FeatureFlags.from_env()
