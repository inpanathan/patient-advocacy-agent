"""Protocol definitions for embedding model implementations.

Defines the interface that all embedding models must satisfy,
enabling mock/real switching via configuration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@runtime_checkable
class EmbeddingModelProtocol(Protocol):
    """Interface for multimodal embedding models."""

    @property
    def dimension(self) -> int:
        """Embedding vector dimensionality."""
        ...

    def embed_image(self, image_path: str) -> NDArray[np.float32]:
        """Generate embedding from an image file.

        Args:
            image_path: Path to the image file.

        Returns:
            Normalized embedding vector on the unit hypersphere.
        """
        ...

    def embed_text(self, text: str) -> NDArray[np.float32]:
        """Generate embedding from text.

        Args:
            text: Input text string.

        Returns:
            Normalized embedding vector on the unit hypersphere.
        """
        ...

    def embed_batch(
        self, items: list[dict[str, Any]]
    ) -> NDArray[np.float32]:
        """Generate embeddings for a batch of items.

        Args:
            items: List of dicts with either "image_path" or "text" key.

        Returns:
            Array of shape (N, dimension) with normalized embeddings.
        """
        ...
