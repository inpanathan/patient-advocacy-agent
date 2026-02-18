"""Retrieval evaluation metrics.

Measures retrieval precision, recall, and latency for the RAG pipeline.

Covers: REQ-OBS-019, REQ-TST-021
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalMetrics:
    """Retrieval evaluation results."""

    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mean_reciprocal_rank: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    num_queries: int = 0


def precision_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int = 10,
) -> float:
    """Compute precision@K.

    Args:
        retrieved: Ordered list of retrieved record IDs.
        relevant: Set of relevant (ground truth) record IDs.
        k: Cutoff position.

    Returns:
        Precision@K value.
    """
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r_id in top_k if r_id in relevant)
    return hits / len(top_k)


def recall_at_k(
    retrieved: list[str],
    relevant: set[str],
    k: int = 10,
) -> float:
    """Compute recall@K.

    Args:
        retrieved: Ordered list of retrieved record IDs.
        relevant: Set of relevant (ground truth) record IDs.
        k: Cutoff position.

    Returns:
        Recall@K value.
    """
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r_id in top_k if r_id in relevant)
    return hits / len(relevant)


def reciprocal_rank(
    retrieved: list[str],
    relevant: set[str],
) -> float:
    """Compute reciprocal rank (position of first relevant result).

    Args:
        retrieved: Ordered list of retrieved record IDs.
        relevant: Set of relevant record IDs.

    Returns:
        1/rank of first relevant result, or 0 if none found.
    """
    for i, r_id in enumerate(retrieved):
        if r_id in relevant:
            return 1.0 / (i + 1)
    return 0.0
