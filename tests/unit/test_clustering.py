"""Tests for clustering evaluation."""

from __future__ import annotations

import numpy as np

from src.evaluation.clustering import (
    ClusteringMetrics,
    compute_silhouette_score,
    evaluate_clustering,
)
from src.models.embedding_model import normalize_embeddings


class TestSilhouetteScore:
    """Test silhouette score computation."""

    def test_well_separated_clusters(self):
        """Well-separated clusters have positive silhouette score."""
        rng = np.random.default_rng(42)
        # Two clusters centered far apart
        cluster_a = rng.standard_normal((20, 64)).astype(np.float32) + 5.0
        cluster_b = rng.standard_normal((20, 64)).astype(np.float32) - 5.0
        embeddings = normalize_embeddings(np.vstack([cluster_a, cluster_b]))
        labels = ["A"] * 20 + ["B"] * 20

        score = compute_silhouette_score(embeddings, labels)
        assert score > 0

    def test_single_point_returns_zero(self):
        """Single point can't be evaluated."""
        emb = np.ones((1, 64), dtype=np.float32)
        assert compute_silhouette_score(emb, ["A"]) == 0.0

    def test_single_cluster_returns_zero(self):
        """Single cluster can't be compared."""
        emb = np.ones((5, 64), dtype=np.float32)
        assert compute_silhouette_score(emb, ["A"] * 5) == 0.0


class TestEvaluateClustering:
    """Test full clustering evaluation."""

    def test_returns_metrics(self):
        """Evaluation returns ClusteringMetrics."""
        rng = np.random.default_rng(42)
        emb = normalize_embeddings(rng.standard_normal((20, 64)).astype(np.float32))
        labels = ["A"] * 10 + ["B"] * 10

        metrics = evaluate_clustering(emb, labels)
        assert isinstance(metrics, ClusteringMetrics)
        assert metrics.n_clusters == 2
        assert metrics.n_samples == 20
        assert "A" in metrics.per_label_scores
        assert "B" in metrics.per_label_scores

    def test_per_label_coherence(self):
        """Per-label coherence is computed for multi-sample clusters."""
        rng = np.random.default_rng(42)
        # Very tight cluster
        tight = np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32), (5, 1))
        # Random points
        random_ = normalize_embeddings(rng.standard_normal((5, 3)).astype(np.float32))
        emb = np.vstack([tight, random_])
        labels = ["tight"] * 5 + ["random"] * 5

        metrics = evaluate_clustering(emb, labels)
        # Tight cluster should have higher coherence
        assert metrics.per_label_scores["tight"] > metrics.per_label_scores["random"]
