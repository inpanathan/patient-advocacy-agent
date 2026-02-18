"""Tests for embedding training pipeline."""

from __future__ import annotations

from src.models.mocks.mock_embedding import MockEmbeddingModel
from src.pipelines.train_embeddings import (
    TrainingConfig,
    TrainingMetrics,
    create_training_pairs,
    run_training,
)


class TestTrainingPairs:
    """Test training pair creation."""

    def test_creates_pairs_from_same_diagnosis(self):
        """Same-diagnosis records are paired together."""
        records = [
            {"image_path": "a1.jpg", "diagnosis": "Eczema"},
            {"image_path": "a2.jpg", "diagnosis": "Eczema"},
            {"image_path": "b1.jpg", "diagnosis": "Psoriasis"},
            {"image_path": "b2.jpg", "diagnosis": "Psoriasis"},
        ]
        model = MockEmbeddingModel(dimension=64)
        batches = create_training_pairs(records, model, batch_size=32, seed=42)
        assert len(batches) >= 1

    def test_no_pairs_with_single_record_per_diagnosis(self):
        """Single records per diagnosis can't form pairs."""
        records = [
            {"image_path": "a.jpg", "diagnosis": "Eczema"},
            {"image_path": "b.jpg", "diagnosis": "Psoriasis"},
        ]
        model = MockEmbeddingModel(dimension=64)
        batches = create_training_pairs(records, model, batch_size=32, seed=42)
        assert len(batches) == 0


class TestRunTraining:
    """Test training pipeline execution."""

    def test_training_completes(self):
        """Training runs to completion with mock data."""
        records = [
            {"image_path": f"img_{i}.jpg", "diagnosis": "Eczema"}
            for i in range(10)
        ] + [
            {"image_path": f"img_{i + 10}.jpg", "diagnosis": "Psoriasis"}
            for i in range(10)
        ]
        config = TrainingConfig(epochs=3, batch_size=8, seed=42)
        metrics = run_training(records, config)

        assert isinstance(metrics, TrainingMetrics)
        assert metrics.epoch == 3
        assert len(metrics.avg_loss_per_epoch) == 3
        assert metrics.best_loss <= metrics.avg_loss_per_epoch[0]

    def test_training_with_no_records(self):
        """Training with no records returns empty metrics."""
        metrics = run_training([], TrainingConfig(epochs=2))
        assert metrics.epoch == 0
        assert metrics.loss == 0.0
