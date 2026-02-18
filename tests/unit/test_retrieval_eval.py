"""Tests for retrieval evaluation metrics."""

from __future__ import annotations

from src.evaluation.retrieval_eval import precision_at_k, recall_at_k, reciprocal_rank


class TestPrecisionAtK:
    """Test precision@K metric."""

    def test_perfect_precision(self):
        """All retrieved items are relevant."""
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert precision_at_k(retrieved, relevant, k=3) == 1.0

    def test_zero_precision(self):
        """No retrieved items are relevant."""
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b", "c"}
        assert precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_partial_precision(self):
        """Some retrieved items are relevant."""
        retrieved = ["a", "x", "b"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=3) == 2 / 3

    def test_empty_retrieved(self):
        """Empty retrieved list returns 0."""
        assert precision_at_k([], {"a"}, k=5) == 0.0


class TestRecallAtK:
    """Test recall@K metric."""

    def test_perfect_recall(self):
        """All relevant items are retrieved."""
        retrieved = ["a", "b", "c", "x"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_partial_recall(self):
        """Some relevant items are retrieved."""
        retrieved = ["a", "x", "y"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == 1 / 3

    def test_empty_relevant(self):
        """No relevant items returns 0."""
        assert recall_at_k(["a"], set(), k=1) == 0.0


class TestReciprocalRank:
    """Test reciprocal rank metric."""

    def test_first_position(self):
        """Relevant item at position 1."""
        assert reciprocal_rank(["a", "x", "y"], {"a"}) == 1.0

    def test_second_position(self):
        """Relevant item at position 2."""
        assert reciprocal_rank(["x", "a", "y"], {"a"}) == 0.5

    def test_no_relevant(self):
        """No relevant items returns 0."""
        assert reciprocal_rank(["x", "y", "z"], {"a"}) == 0.0
