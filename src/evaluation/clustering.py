"""Clustering evaluation for embedding quality.

Measures how well embeddings separate different diagnoses using
silhouette score and per-diagnosis cluster metrics.

Covers: REQ-TST-021
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


@dataclass
class ClusteringMetrics:
    """Clustering evaluation results."""

    silhouette_score: float = 0.0
    per_label_scores: dict[str, float] = field(default_factory=dict)
    n_clusters: int = 0
    n_samples: int = 0


def compute_silhouette_score(
    embeddings: NDArray[np.float32],
    labels: list[str],
) -> float:
    """Compute silhouette score for embeddings grouped by labels.

    Silhouette score measures how similar points are to their own cluster
    vs. neighboring clusters. Range: [-1, 1], higher is better.

    Args:
        embeddings: Array of shape (N, D).
        labels: List of N string labels.

    Returns:
        Mean silhouette score.
    """
    if len(embeddings) < 2 or len(set(labels)) < 2:
        return 0.0

    n = len(embeddings)
    unique_labels = sorted(set(labels))
    label_to_idx = {label: i for i, label in enumerate(unique_labels)}
    label_indices = np.array([label_to_idx[lbl] for lbl in labels])

    # Pairwise distance matrix (cosine distance = 1 - cosine similarity)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    normed = embeddings / norms
    sim_matrix = normed @ normed.T
    dist_matrix = 1.0 - sim_matrix

    silhouette_values = np.zeros(n)

    for i in range(n):
        own_label = label_indices[i]
        own_mask = label_indices == own_label
        own_mask[i] = False  # exclude self

        if own_mask.sum() == 0:
            silhouette_values[i] = 0.0
            continue

        # a(i): mean intra-cluster distance
        a_i = np.mean(dist_matrix[i, own_mask])

        # b(i): min mean distance to any other cluster
        b_i = float("inf")
        for other_label in range(len(unique_labels)):
            if other_label == own_label:
                continue
            other_mask = label_indices == other_label
            if other_mask.sum() == 0:
                continue
            mean_dist = np.mean(dist_matrix[i, other_mask])
            b_i = min(b_i, mean_dist)

        if b_i == float("inf"):
            silhouette_values[i] = 0.0
        else:
            silhouette_values[i] = (b_i - a_i) / max(a_i, b_i, 1e-8)

    return float(np.mean(silhouette_values))


def evaluate_clustering(
    embeddings: NDArray[np.float32],
    labels: list[str],
) -> ClusteringMetrics:
    """Full clustering evaluation.

    Args:
        embeddings: Array of shape (N, D).
        labels: List of N string labels (e.g., diagnosis names).

    Returns:
        ClusteringMetrics with overall and per-label scores.
    """
    unique_labels = sorted(set(labels))

    overall_score = compute_silhouette_score(embeddings, labels)

    per_label: dict[str, float] = {}
    for label in unique_labels:
        mask = [i for i, lbl in enumerate(labels) if lbl == label]
        if len(mask) >= 2:
            label_embeddings = embeddings[mask]
            # Per-label coherence: mean pairwise similarity within cluster
            norms = np.linalg.norm(label_embeddings, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-8)
            normed = label_embeddings / norms
            sim = normed @ normed.T
            n_l = len(mask)
            if n_l > 1:
                upper_tri = sim[np.triu_indices(n_l, k=1)]
                per_label[label] = float(np.mean(upper_tri))
            else:
                per_label[label] = 1.0
        else:
            per_label[label] = 1.0

    metrics = ClusteringMetrics(
        silhouette_score=overall_score,
        per_label_scores=per_label,
        n_clusters=len(unique_labels),
        n_samples=len(embeddings),
    )

    logger.info(
        "clustering_evaluation_complete",
        silhouette_score=f"{overall_score:.4f}",
        n_clusters=metrics.n_clusters,
        n_samples=metrics.n_samples,
    )

    return metrics
