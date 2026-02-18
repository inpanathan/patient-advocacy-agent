"""Tests for contrastive loss functions."""

from __future__ import annotations

import numpy as np
import pytest

from src.models.losses import contrastive_loss, contrastive_loss_with_margin


class TestContrastiveLoss:
    """Test NT-Xent contrastive loss."""

    def _make_embeddings(self, n: int, dim: int, seed: int = 42) -> np.ndarray:
        rng = np.random.default_rng(seed)
        emb = rng.standard_normal((n, dim)).astype(np.float32)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / norms

    def test_zero_loss_identical_pairs(self):
        """Identical pairs should have low loss."""
        emb = self._make_embeddings(4, 128)
        loss = contrastive_loss(emb, emb)
        # Should be close to -log(1/N) since all rows match diagonal
        assert loss >= 0

    def test_shape_mismatch_raises(self):
        """Mismatched shapes raise ValueError."""
        a = self._make_embeddings(4, 128)
        b = self._make_embeddings(3, 128)
        with pytest.raises(ValueError, match="Shape mismatch"):
            contrastive_loss(a, b)

    def test_empty_input_returns_zero(self):
        """Empty arrays return zero loss."""
        a = np.empty((0, 128), dtype=np.float32)
        assert contrastive_loss(a, a) == 0.0

    def test_loss_is_non_negative(self):
        """Loss should always be non-negative."""
        a = self._make_embeddings(8, 128, seed=1)
        b = self._make_embeddings(8, 128, seed=2)
        loss = contrastive_loss(a, b)
        assert loss >= 0

    def test_temperature_affects_loss(self):
        """Lower temperature produces larger loss values."""
        a = self._make_embeddings(8, 128, seed=1)
        b = self._make_embeddings(8, 128, seed=2)
        loss_high_t = contrastive_loss(a, b, temperature=1.0)
        loss_low_t = contrastive_loss(a, b, temperature=0.01)
        # Lower temperature sharpens the distribution
        assert loss_low_t != loss_high_t


class TestContrastiveLossWithMargin:
    """Test contrastive loss with margin."""

    def _make_embeddings(self, n: int, dim: int, seed: int = 42) -> np.ndarray:
        rng = np.random.default_rng(seed)
        emb = rng.standard_normal((n, dim)).astype(np.float32)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / norms

    def test_perfect_separation_zero_loss(self):
        """Well-separated pairs have zero margin loss."""
        # Create perfectly matched pairs
        a = self._make_embeddings(4, 128, seed=1)
        loss = contrastive_loss_with_margin(a, a, margin=0.0)
        assert loss == 0.0

    def test_shape_mismatch_raises(self):
        """Mismatched shapes raise ValueError."""
        a = self._make_embeddings(4, 128)
        b = self._make_embeddings(3, 128)
        with pytest.raises(ValueError):
            contrastive_loss_with_margin(a, b)

    def test_empty_input_returns_zero(self):
        """Empty arrays return zero loss."""
        a = np.empty((0, 128), dtype=np.float32)
        assert contrastive_loss_with_margin(a, a) == 0.0

    def test_loss_is_non_negative(self):
        """Margin loss is always non-negative."""
        a = self._make_embeddings(8, 128, seed=1)
        b = self._make_embeddings(8, 128, seed=2)
        loss = contrastive_loss_with_margin(a, b)
        assert loss >= 0
