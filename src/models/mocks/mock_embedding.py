"""Mock embedding model for development and testing.

Returns deterministic embeddings based on input hashing,
enabling reproducible tests without GPU or real model weights.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


class MockEmbeddingModel:
    """Mock SigLIP-2 embedding model.

    Generates deterministic embeddings from input hashing.
    Embeddings are normalized to the unit hypersphere.
    """

    def __init__(self, dimension: int = 768, seed: int = 42) -> None:
        self._dimension = dimension
        self._rng = np.random.default_rng(seed)
        logger.info("mock_embedding_model_loaded", dimension=dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_embedding(self, key: str) -> NDArray[np.float32]:
        """Generate a deterministic embedding from a string key."""
        h = hashlib.sha256(key.encode()).digest()
        seed = int.from_bytes(h[:8], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dimension).astype(np.float32)
        # Normalize to unit hypersphere
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_image(self, image_path: str) -> NDArray[np.float32]:
        """Generate mock embedding from image path."""
        return self._hash_to_embedding(f"image:{image_path}")

    def embed_text(self, text: str) -> NDArray[np.float32]:
        """Generate mock embedding from text."""
        return self._hash_to_embedding(f"text:{text}")

    def embed_batch(self, items: list[dict[str, Any]]) -> NDArray[np.float32]:
        """Generate mock embeddings for a batch."""
        embeddings = []
        for item in items:
            if "image_path" in item:
                embeddings.append(self.embed_image(item["image_path"]))
            elif "text" in item:
                embeddings.append(self.embed_text(item["text"]))
            else:
                embeddings.append(self._hash_to_embedding("unknown"))
        return np.stack(embeddings)
