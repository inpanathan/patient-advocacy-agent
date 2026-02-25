"""LoRA adapter loader for MedGemma inference.

Applies QLoRA adapters to a loaded MedGemma model when
``settings.llm.lora_adapter_path`` is configured.

This module is separate from the model implementation to avoid
modifying the protected ``src/models/local/`` files.

Covers: REQ-MOD-001
"""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from src.utils.config import settings

logger = structlog.get_logger(__name__)


def maybe_apply_lora_adapter(model_obj: object) -> None:
    """Apply LoRA adapters to a LocalMedicalModel if configured.

    Checks ``settings.llm.lora_adapter_path``. If set and the adapter
    directory exists, loads and merges the LoRA weights into the model
    in-place.

    Args:
        model_obj: A LocalMedicalModel instance with ``_model`` attribute.
    """
    adapter_path = settings.llm.lora_adapter_path
    if not adapter_path:
        return

    adapter_dir = Path(adapter_path)
    # Check both direct path and adapter subdirectory
    if not adapter_dir.exists():
        adapter_dir = Path(adapter_path) / "adapter"
    if not adapter_dir.exists():
        logger.warning(
            "lora_adapter_path_not_found",
            path=adapter_path,
            hint="Run: bash scripts/finetune_medgemma.sh",
        )
        return

    if not hasattr(model_obj, "_model"):
        logger.warning("model_has_no_model_attribute", model_type=type(model_obj).__name__)
        return

    try:
        from peft import PeftModel

        t0 = time.monotonic()
        logger.info("loading_lora_adapter", path=str(adapter_dir))

        model_obj._model = PeftModel.from_pretrained(  # type: ignore[attr-defined]
            model_obj._model,  # type: ignore[attr-defined]
            str(adapter_dir),
        )
        model_obj._model = model_obj._model.merge_and_unload()  # type: ignore[attr-defined]
        model_obj._model.eval()  # type: ignore[attr-defined]

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("lora_adapter_loaded", path=str(adapter_dir), merge_ms=elapsed)

    except ImportError:
        logger.warning("peft_not_installed", hint="uv add peft")
    except Exception as e:
        logger.warning("lora_adapter_load_failed", error=str(e))
