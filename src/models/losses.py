"""Contrastive loss function for embedding fine-tuning.

Implements NT-Xent (Normalized Temperature-scaled Cross Entropy) loss
for contrastive learning of isotropic embeddings on the unit hypersphere.

Covers: REQ-TST-012
"""

from __future__ import annotations

import numpy as np
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


def contrastive_loss(
    embeddings_a: NDArray[np.float32],
    embeddings_b: NDArray[np.float32],
    temperature: float = 0.07,
) -> float:
    """Compute NT-Xent contrastive loss.

    For each pair (a_i, b_i), the positive pair should have higher similarity
    than all negative pairs in the batch.

    Args:
        embeddings_a: First set of embeddings, shape (N, D).
        embeddings_b: Second set of embeddings (positive pairs), shape (N, D).
        temperature: Temperature scaling factor.

    Returns:
        Scalar loss value.

    Raises:
        ValueError: If input shapes don't match.
    """
    if embeddings_a.shape != embeddings_b.shape:
        msg = (
            f"Shape mismatch: embeddings_a={embeddings_a.shape}, "
            f"embeddings_b={embeddings_b.shape}"
        )
        raise ValueError(msg)

    if len(embeddings_a) == 0:
        return 0.0

    # Normalize
    a_norm = embeddings_a / np.maximum(np.linalg.norm(embeddings_a, axis=1, keepdims=True), 1e-8)
    b_norm = embeddings_b / np.maximum(np.linalg.norm(embeddings_b, axis=1, keepdims=True), 1e-8)

    # Similarity matrix: (N, N)
    sim_matrix = (a_norm @ b_norm.T) / temperature

    # For numerical stability
    sim_matrix = sim_matrix - np.max(sim_matrix, axis=1, keepdims=True)

    # Labels: positive pairs are on the diagonal
    exp_sim = np.exp(sim_matrix)
    row_sums = np.sum(exp_sim, axis=1)

    # Loss: -log(exp(sim_ii) / sum_j(exp(sim_ij)))
    pos_sim = np.diag(exp_sim)
    losses = -np.log(pos_sim / row_sums + 1e-8)

    return float(np.mean(losses))


def contrastive_loss_with_margin(
    embeddings_a: NDArray[np.float32],
    embeddings_b: NDArray[np.float32],
    temperature: float = 0.07,
    margin: float = 0.2,
) -> float:
    """Contrastive loss with margin for harder negatives.

    Adds a margin to push negative pairs further apart.

    Args:
        embeddings_a: First set of embeddings, shape (N, D).
        embeddings_b: Second set of embeddings, shape (N, D).
        temperature: Temperature scaling factor.
        margin: Minimum margin between positive and negative similarities.

    Returns:
        Scalar loss value.
    """
    if embeddings_a.shape != embeddings_b.shape:
        msg = "Shape mismatch"
        raise ValueError(msg)

    if len(embeddings_a) == 0:
        return 0.0

    n = len(embeddings_a)

    a_norm = embeddings_a / np.maximum(np.linalg.norm(embeddings_a, axis=1, keepdims=True), 1e-8)
    b_norm = embeddings_b / np.maximum(np.linalg.norm(embeddings_b, axis=1, keepdims=True), 1e-8)

    sim_matrix = a_norm @ b_norm.T

    # Positive pair similarities (diagonal)
    pos_sims = np.diag(sim_matrix)

    # For each row, compute max negative similarity
    mask = ~np.eye(n, dtype=bool)
    neg_sims = np.where(mask, sim_matrix, -np.inf)
    max_neg_sims = np.max(neg_sims, axis=1)

    # Margin loss: max(0, margin - (pos - neg))
    margin_violations = np.maximum(0.0, margin - (pos_sims - max_neg_sims))

    return float(np.mean(margin_violations))
