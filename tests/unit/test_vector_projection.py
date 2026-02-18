"""Tests for PCA 2D projection of embeddings."""

from __future__ import annotations

import numpy as np

from src.observability.vector_projection import compute_2d_projection


class TestVectorProjection:
    """Tests for compute_2d_projection."""

    def test_returns_correct_structure(self) -> None:
        embeddings = np.random.default_rng(42).random((10, 64)).astype(np.float32)
        metadata = [
            {"diagnosis": f"diag_{i}", "icd_code": f"L{i:02d}", "fitzpatrick_type": "III"}
            for i in range(10)
        ]
        result = compute_2d_projection(embeddings, metadata, max_points=100)
        assert len(result.points) == 10
        assert result.total_embeddings == 10
        assert result.sampled == 10
        for p in result.points:
            assert "x" in p
            assert "y" in p
            assert "diagnosis" in p
            assert "icd_code" in p

    def test_subsampling_respects_max_points(self) -> None:
        embeddings = np.random.default_rng(42).random((100, 32)).astype(np.float32)
        metadata = [{"diagnosis": f"d{i}"} for i in range(100)]
        result = compute_2d_projection(embeddings, metadata, max_points=20)
        assert result.sampled == 20
        assert result.total_embeddings == 100
        assert len(result.points) == 20

    def test_empty_embeddings(self) -> None:
        embeddings = np.array([], dtype=np.float32).reshape(0, 64)
        result = compute_2d_projection(embeddings, [], max_points=10)
        assert result.points == []
        assert result.total_embeddings == 0
        assert result.sampled == 0

    def test_single_embedding(self) -> None:
        embeddings = np.random.default_rng(42).random((1, 16)).astype(np.float32)
        metadata = [{"diagnosis": "test", "icd_code": "L00"}]
        result = compute_2d_projection(embeddings, metadata, max_points=10)
        assert len(result.points) == 1
        assert result.points[0]["diagnosis"] == "test"
