"""Local SigLIP-2 embedding model implementation.

Loads SigLIP-so400m-patch14-384 via Hugging Face transformers
for on-device multimodal (image + text) embedding generation.

VRAM budget: ~1.5GB at fp32 (lightweight enough for CPU too).
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import structlog
import torch
from numpy.typing import NDArray
from PIL import Image
from transformers import AutoModel, AutoProcessor

from src.utils.config import settings

logger = structlog.get_logger(__name__)


def _resolve_device(device: str) -> str:
    """Resolve 'auto' to the best available device."""
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


class LocalEmbeddingModel:
    """SigLIP-2 multimodal embedding model for local inference."""

    def __init__(self) -> None:
        model_id = settings.embedding.model_id
        device = _resolve_device(settings.embedding.device)

        logger.info("loading_local_embedding_model", model_id=model_id, device=device)
        t0 = time.monotonic()

        self._processor = AutoProcessor.from_pretrained(model_id)
        self._model = AutoModel.from_pretrained(model_id).to(device)
        self._model.eval()
        self._device = device
        self._model_id = model_id
        self._dimension: int = int(self._model.config.vision_config.hidden_size)

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(
            "local_embedding_model_loaded",
            model_id=model_id,
            dimension=self._dimension,
            load_ms=elapsed,
        )

    @property
    def dimension(self) -> int:
        """Embedding vector dimensionality."""
        return self._dimension

    def _normalize(self, vec: NDArray[np.float32]) -> NDArray[np.float32]:
        """L2-normalize embedding vectors."""
        norms = np.linalg.norm(vec, axis=-1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        result: NDArray[np.float32] = vec / norms
        return result

    def embed_image(self, image_path: str) -> NDArray[np.float32]:
        """Generate normalized embedding from an image file."""
        t0 = time.monotonic()

        image = Image.open(image_path).convert("RGB")
        inputs = self._processor(images=image, return_tensors="pt").to(self._device)

        with torch.no_grad():
            outputs = self._model.get_image_features(**inputs)

        embedding = outputs.cpu().numpy().astype(np.float32).squeeze(0)
        result = self._normalize(embedding)

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("local_embed_image", image_path=image_path, latency_ms=elapsed)
        return result

    def embed_text(self, text: str) -> NDArray[np.float32]:
        """Generate normalized embedding from text."""
        t0 = time.monotonic()

        inputs = self._processor(text=text, return_tensors="pt", padding=True).to(
            self._device
        )

        with torch.no_grad():
            outputs = self._model.get_text_features(**inputs)

        embedding = outputs.cpu().numpy().astype(np.float32).squeeze(0)
        result = self._normalize(embedding)

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("local_embed_text", text_len=len(text), latency_ms=elapsed)
        return result

    def embed_batch(self, items: list[dict[str, Any]]) -> NDArray[np.float32]:
        """Generate embeddings for a batch of items."""
        embeddings: list[NDArray[np.float32]] = []
        for item in items:
            if "image_path" in item:
                embeddings.append(self.embed_image(item["image_path"]))
            elif "text" in item:
                embeddings.append(self.embed_text(item["text"]))
            else:
                logger.warning("unknown_embed_item", item_keys=list(item.keys()))
                embeddings.append(np.zeros(self._dimension, dtype=np.float32))
        return np.stack(embeddings)
