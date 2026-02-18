"""Embedding model wrapper for SigLIP-2.

Loads the SigLIP-2 model, preprocesses images and text, and generates
normalized embeddings on the unit hypersphere.

TODO: Requires actual SigLIP-2 model weights at settings.embedding.model_path.
      Falls back to mock implementation when settings.use_mocks=True.

Covers: REQ-CST-009, REQ-CST-011
"""

from __future__ import annotations

import numpy as np
import structlog
from numpy.typing import NDArray

from src.models.mocks.mock_embedding import MockEmbeddingModel
from src.models.protocols.embedding import EmbeddingModelProtocol
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def get_embedding_model() -> EmbeddingModelProtocol:
    """Factory to get the appropriate embedding model based on model_backend setting.

    SigLIP-2 is used for both local and cloud modes since there is no
    direct cloud API equivalent for multimodal embeddings.
    """
    backend = settings.model_backend

    if settings.use_mocks or backend == "mock":
        logger.info("using_mock_embedding_model")
        return MockEmbeddingModel(dimension=settings.embedding.dimension)

    if backend in ("local", "cloud"):
        from src.models.local.local_embedding import LocalEmbeddingModel

        logger.info("using_local_embedding_model", backend=backend)
        return LocalEmbeddingModel()

    msg = f"Unknown model_backend: {backend}"
    raise ValueError(msg)


def normalize_embeddings(embeddings: NDArray[np.float32]) -> NDArray[np.float32]:
    """Normalize embeddings to the unit hypersphere.

    Ensures isotropic distribution for contrastive learning.

    Args:
        embeddings: Array of shape (N, D).

    Returns:
        L2-normalized array of the same shape.
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)  # avoid division by zero
    result: NDArray[np.float32] = embeddings / norms
    return result


def compute_isotropy(embeddings: NDArray[np.float32]) -> float:
    """Measure isotropy of embedding distribution.

    Higher values (closer to 1.0) indicate more uniform distribution
    on the unit hypersphere, which is desirable for retrieval.

    Args:
        embeddings: Normalized array of shape (N, D).

    Returns:
        Isotropy score between 0 and 1.
    """
    if len(embeddings) < 2:
        return 1.0

    # Compute pairwise cosine similarities
    sim_matrix = embeddings @ embeddings.T
    n = len(embeddings)
    # Exclude diagonal
    mask = ~np.eye(n, dtype=bool)
    off_diag = sim_matrix[mask]

    # Isotropy: 1 - abs(mean cosine similarity)
    # Perfect isotropy -> mean similarity ~= 0
    return float(1.0 - abs(np.mean(off_diag)))
