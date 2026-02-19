"""Multi-method 2D projection of SCIN embeddings for visualization.

Projects high-dimensional embeddings into 2D for the dashboard scatter plot.
Supports PCA, t-SNE, and UMAP with deterministic seeding and result caching.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


class ProjectionMethod(enum.Enum):
    """Supported dimensionality reduction methods."""

    pca = "pca"
    tsne = "tsne"
    umap = "umap"


@dataclass
class ProjectionResult:
    """2D projection result with metadata per point."""

    points: list[dict[str, Any]] = field(default_factory=list)
    total_embeddings: int = 0
    sampled: int = 0
    method: str = "pca"


# Cache with TTL
_cache: dict[str, tuple[float, ProjectionResult]] = {}
_CACHE_TTL_S = 300.0  # 5 minutes


def _fit_transform(
    method: ProjectionMethod,
    embeddings: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Dispatch to the appropriate dimensionality reduction algorithm.

    Args:
        method: Which projection method to use.
        embeddings: Array of shape (n, d).

    Returns:
        Array of shape (n, 2) with 2D coordinates.
    """
    n_samples = len(embeddings)
    n_features = embeddings.shape[1] if embeddings.ndim > 1 else 1

    if n_samples < 2 or n_features < 2:
        # Not enough data for meaningful projection
        if n_features == 1:
            return np.column_stack([embeddings, np.zeros(n_samples, dtype=np.float32)])
        return np.zeros((n_samples, 2), dtype=np.float32)

    if method == ProjectionMethod.tsne:
        try:
            from sklearn.manifold import TSNE

            perplexity = min(30, n_samples - 1)
            tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
            result: NDArray[np.float32] = np.asarray(
                tsne.fit_transform(embeddings),
                dtype=np.float32,
            )
            return result
        except ImportError:
            logger.warning("tsne_unavailable_fallback_pca")
            return _fit_transform(ProjectionMethod.pca, embeddings)

    if method == ProjectionMethod.umap:
        try:
            import umap

            reducer = umap.UMAP(n_components=2, random_state=42)
            umap_result: NDArray[np.float32] = np.asarray(
                reducer.fit_transform(embeddings),
                dtype=np.float32,
            )
            return umap_result
        except ImportError:
            logger.warning("umap_unavailable_fallback_pca")
            return _fit_transform(ProjectionMethod.pca, embeddings)

    # Default: PCA
    try:
        from sklearn.decomposition import PCA

        n_components = min(2, n_samples, n_features)
        if n_components < 2:
            pca = PCA(n_components=1, random_state=42)
            partial = pca.fit_transform(embeddings)
            return np.column_stack([partial, np.zeros(n_samples, dtype=np.float32)]).astype(
                np.float32
            )
        pca = PCA(n_components=2, random_state=42)
        pca_result: NDArray[np.float32] = np.asarray(
            pca.fit_transform(embeddings),
            dtype=np.float32,
        )
        return pca_result
    except ImportError:
        # Fallback: use first two dimensions
        if n_features >= 2:
            return embeddings[:, :2].astype(np.float32)
        return np.zeros((n_samples, 2), dtype=np.float32)


def compute_2d_projection(
    embeddings: NDArray[np.float32],
    metadata: list[dict[str, Any]],
    max_points: int = 500,
    method: ProjectionMethod = ProjectionMethod.pca,
) -> ProjectionResult:
    """Compute 2D projection of embeddings using the specified method.

    Args:
        embeddings: Array of shape (n, d) -- n embeddings of dimension d.
        metadata: List of metadata dicts per embedding (diagnosis, icd_code, etc.).
        max_points: Maximum number of points to return (subsampled if larger).
        method: Dimensionality reduction method (pca, tsne, umap).

    Returns:
        ProjectionResult with 2D coordinates and metadata.
    """
    n = len(embeddings)
    if n == 0 or len(metadata) == 0:
        return ProjectionResult(points=[], total_embeddings=0, sampled=0, method=method.value)

    # Check cache (keyed by method + n + max_points)
    cache_key = f"{method.value}_{n}_{max_points}"
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

    coords = _fit_transform(method, sampled_embeddings)

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
        method=method.value,
    )
    _cache[cache_key] = (now, result)
    return result


def project_single_point(
    reference_embeddings: NDArray[np.float32],
    reference_metadata: list[dict[str, Any]],
    new_embeddings: NDArray[np.float32],
    new_metadata: list[dict[str, Any]],
    max_points: int = 500,
    method: ProjectionMethod = ProjectionMethod.pca,
) -> ProjectionResult:
    """Project new point(s) alongside the reference SCIN embeddings.

    Appends the new embedding(s) to the reference set, runs the full
    projection, then marks which points are from the case overlay.

    Args:
        reference_embeddings: SCIN embeddings array of shape (n, d).
        reference_metadata: Metadata dicts for each SCIN embedding.
        new_embeddings: Case embedding(s) of shape (m, d).
        new_metadata: Metadata dicts for the case point(s).
        max_points: Max reference points to include (subsampled if larger).
        method: Dimensionality reduction method.

    Returns:
        ProjectionResult with all points; case points have is_case=True.
    """
    n = len(reference_embeddings)
    m = len(new_embeddings)
    if m == 0:
        return compute_2d_projection(reference_embeddings, reference_metadata, max_points, method)

    # Subsample reference set if needed
    rng = np.random.default_rng(seed=42)
    if n > max_points:
        indices = rng.choice(n, size=max_points, replace=False)
        indices.sort()
        ref_emb = reference_embeddings[indices]
        ref_meta = [reference_metadata[i] for i in indices]
    else:
        ref_emb = reference_embeddings
        ref_meta = list(reference_metadata)

    # Concatenate reference + new
    combined = np.vstack([ref_emb, new_embeddings])
    combined_meta = ref_meta + list(new_metadata)

    coords = _fit_transform(method, combined)

    n_ref = len(ref_emb)
    points = []
    for i, meta in enumerate(combined_meta):
        point = {
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "diagnosis": meta.get("diagnosis", ""),
            "icd_code": meta.get("icd_code", ""),
            "fitzpatrick_type": meta.get("fitzpatrick_type", ""),
            "record_id": meta.get("record_id", ""),
            "is_case": i >= n_ref,
        }
        points.append(point)

    return ProjectionResult(
        points=points,
        total_embeddings=n,
        sampled=n_ref + m,
        method=method.value,
    )
