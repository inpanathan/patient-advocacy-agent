"""PCA 2D projection of SCIN embeddings for visualization.

Projects high-dimensional embeddings into 2D for the dashboard scatter plot.
Uses scikit-learn PCA with deterministic seeding and result caching.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class ProjectionResult:
    """2D projection result with metadata per point."""

    points: list[dict[str, Any]] = field(default_factory=list)
    total_embeddings: int = 0
    sampled: int = 0


# Cache with TTL
_cache: dict[str, tuple[float, ProjectionResult]] = {}
_CACHE_TTL_S = 300.0  # 5 minutes


def compute_2d_projection(
    embeddings: NDArray[np.float32],
    metadata: list[dict[str, Any]],
    max_points: int = 500,
) -> ProjectionResult:
    """Compute PCA 2D projection of embeddings.

    Args:
        embeddings: Array of shape (n, d) — n embeddings of dimension d.
        metadata: List of metadata dicts per embedding (diagnosis, icd_code, etc.).
        max_points: Maximum number of points to return (subsampled if larger).

    Returns:
        ProjectionResult with 2D coordinates and metadata.
    """
    n = len(embeddings)
    if n == 0 or len(metadata) == 0:
        return ProjectionResult(points=[], total_embeddings=0, sampled=0)

    # Check cache
    cache_key = f"{n}_{max_points}"
    now = time.monotonic()
    if cache_key in _cache:
        cached_time, cached_result = _cache[cache_key]
        if now - cached_time < _CACHE_TTL_S:
            return cached_result

    # Subsample if needed
    rng = np.random.default_rng(seed=42)
    if n > max_points:
        indices = rng.choice(n, size=max_points, replace=False)
        indices.sort()
        sampled_embeddings = embeddings[indices]
        sampled_metadata = [metadata[i] for i in indices]
    else:
        sampled_embeddings = embeddings
        sampled_metadata = metadata

    try:
        from sklearn.decomposition import PCA

        n_components = min(2, len(sampled_embeddings), sampled_embeddings.shape[1])
        if n_components < 2:
            # Not enough samples/features for 2D PCA — pad with zeros
            if n_components == 1:
                pca = PCA(n_components=1, random_state=42)
                partial = pca.fit_transform(sampled_embeddings)
                coords = np.column_stack([partial, np.zeros(len(sampled_embeddings))])
            else:
                coords = np.zeros((len(sampled_embeddings), 2), dtype=np.float32)
        else:
            pca = PCA(n_components=2, random_state=42)
            coords = pca.fit_transform(sampled_embeddings)
    except ImportError:
        # Fallback: use first two dimensions
        if sampled_embeddings.shape[1] >= 2:
            coords = sampled_embeddings[:, :2]
        else:
            coords = np.zeros((len(sampled_embeddings), 2), dtype=np.float32)

    points = []
    for i, meta in enumerate(sampled_metadata):
        points.append(
            {
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "diagnosis": meta.get("diagnosis", ""),
                "icd_code": meta.get("icd_code", ""),
                "fitzpatrick_type": meta.get("fitzpatrick_type", ""),
                "record_id": meta.get("record_id", ""),
            }
        )

    result = ProjectionResult(
        points=points,
        total_embeddings=n,
        sampled=len(points),
    )
    _cache[cache_key] = (now, result)
    return result
