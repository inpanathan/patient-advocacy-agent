"""Tests for embedding model and utilities."""

from __future__ import annotations

import numpy as np

from src.models.embedding_model import compute_isotropy, normalize_embeddings
from src.models.mocks.mock_embedding import MockEmbeddingModel


class TestMockEmbeddingModel:
    """Test mock embedding model."""

    def test_embed_image_returns_correct_shape(self):
        """Image embedding has correct dimension."""
        model = MockEmbeddingModel(dimension=768)
        emb = model.embed_image("test.jpg")
        assert emb.shape == (768,)

    def test_embed_text_returns_correct_shape(self):
        """Text embedding has correct dimension."""
        model = MockEmbeddingModel(dimension=768)
        emb = model.embed_text("a rash on the arm")
        assert emb.shape == (768,)

    def test_embeddings_are_normalized(self):
        """Mock embeddings are on the unit hypersphere."""
        model = MockEmbeddingModel(dimension=768)
        emb = model.embed_image("test.jpg")
        norm = np.linalg.norm(emb)
        assert abs(norm - 1.0) < 1e-5

    def test_deterministic_output(self):
        """Same input produces same embedding."""
        model = MockEmbeddingModel(dimension=768, seed=42)
        emb1 = model.embed_image("test.jpg")
        emb2 = model.embed_image("test.jpg")
        np.testing.assert_array_equal(emb1, emb2)

    def test_different_inputs_different_embeddings(self):
        """Different inputs produce different embeddings."""
        model = MockEmbeddingModel(dimension=768)
        emb1 = model.embed_image("a.jpg")
        emb2 = model.embed_image("b.jpg")
        assert not np.allclose(emb1, emb2)

    def test_embed_batch(self):
        """Batch embedding returns correct shape."""
        model = MockEmbeddingModel(dimension=768)
        items = [{"image_path": "a.jpg"}, {"text": "rash"}, {"image_path": "b.jpg"}]
        batch = model.embed_batch(items)
        assert batch.shape == (3, 768)

    def test_dimension_property(self):
        """Dimension property returns configured value."""
        model = MockEmbeddingModel(dimension=512)
        assert model.dimension == 512


class TestNormalizeEmbeddings:
    """Test embedding normalization."""

    def test_normalizes_to_unit_length(self):
        """Embeddings are normalized to unit L2 norm."""
        rng = np.random.default_rng(42)
        emb = rng.standard_normal((10, 768)).astype(np.float32)
        normed = normalize_embeddings(emb)
        norms = np.linalg.norm(normed, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_handles_zero_vector(self):
        """Zero vector doesn't cause division by zero."""
        emb = np.zeros((1, 768), dtype=np.float32)
        normed = normalize_embeddings(emb)
        assert not np.any(np.isnan(normed))


class TestIsotropy:
    """Test isotropy measurement."""

    def test_random_embeddings_moderate_isotropy(self):
        """Random normalized embeddings have moderate isotropy."""
        rng = np.random.default_rng(42)
        emb = rng.standard_normal((100, 768)).astype(np.float32)
        normed = normalize_embeddings(emb)
        score = compute_isotropy(normed)
        assert 0.5 < score < 1.0

    def test_single_embedding_perfect_isotropy(self):
        """Single embedding returns isotropy of 1.0."""
        emb = np.ones((1, 768), dtype=np.float32)
        assert compute_isotropy(emb) == 1.0

    def test_identical_embeddings_zero_isotropy(self):
        """Identical embeddings have near-zero isotropy."""
        emb = np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32), (10, 1))
        score = compute_isotropy(emb)
        assert score < 0.1
