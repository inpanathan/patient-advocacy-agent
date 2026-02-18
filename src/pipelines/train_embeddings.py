"""Embedding fine-tuning training pipeline.

Orchestrates the training loop for fine-tuning SigLIP-2 with contrastive
loss on the SCIN database. Uses mock model in development mode.

Covers: REQ-OBS-055
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import structlog
from numpy.typing import NDArray

from src.models.embedding_model import get_embedding_model, normalize_embeddings
from src.models.losses import contrastive_loss

logger = structlog.get_logger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration."""

    batch_size: int = 32
    learning_rate: float = 1e-4
    epochs: int = 10
    temperature: float = 0.07
    seed: int = 42


@dataclass
class TrainingMetrics:
    """Metrics collected during training."""

    epoch: int = 0
    loss: float = 0.0
    avg_loss_per_epoch: list[float] = field(default_factory=list)
    best_loss: float = float("inf")
    best_epoch: int = 0


def create_training_pairs(
    records: list[dict],
    model: object,
    batch_size: int = 32,
    seed: int = 42,
) -> list[tuple[NDArray[np.float32], NDArray[np.float32]]]:
    """Create positive pairs for contrastive training.

    Pairs images with the same diagnosis as positive pairs.
    Different diagnoses serve as in-batch negatives.

    Args:
        records: List of dicts with "image_path" and "diagnosis" keys.
        model: Embedding model (used for batch embedding).
        batch_size: Number of pairs per batch.
        seed: Random seed for reproducibility.

    Returns:
        List of (embeddings_a, embeddings_b) pairs.
    """
    rng = np.random.default_rng(seed)

    # Group records by diagnosis
    by_diagnosis: dict[str, list[dict]] = {}
    for r in records:
        diag = r.get("diagnosis", "unknown")
        by_diagnosis.setdefault(diag, []).append(r)

    # Create pairs: same diagnosis = positive pair
    pairs_a: list[dict] = []
    pairs_b: list[dict] = []

    for _diag, group in by_diagnosis.items():
        if len(group) < 2:
            continue
        indices = list(range(len(group)))
        rng.shuffle(indices)
        for i in range(0, len(indices) - 1, 2):
            pairs_a.append(group[indices[i]])
            pairs_b.append(group[indices[i + 1]])

    # Batch the pairs
    batches = []
    for start in range(0, len(pairs_a), batch_size):
        end = min(start + batch_size, len(pairs_a))
        batch_a = [{"image_path": p["image_path"]} for p in pairs_a[start:end]]
        batch_b = [{"image_path": p["image_path"]} for p in pairs_b[start:end]]

        if hasattr(model, "embed_batch"):
            emb_a = model.embed_batch(batch_a)
            emb_b = model.embed_batch(batch_b)
            batches.append((emb_a, emb_b))

    return batches


def run_training(
    records: list[dict],
    config: TrainingConfig | None = None,
) -> TrainingMetrics:
    """Run the embedding fine-tuning training loop.

    In mock mode, this simulates training by computing contrastive loss
    on mock embeddings. In production, it would fine-tune the actual model.

    Args:
        records: List of SCIN records as dicts with "image_path" and "diagnosis".
        config: Training configuration. Uses defaults if None.

    Returns:
        TrainingMetrics with loss history.
    """
    if config is None:
        config = TrainingConfig()

    np.random.seed(config.seed)
    model = get_embedding_model()
    metrics = TrainingMetrics()

    logger.info(
        "training_started",
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        temperature=config.temperature,
        num_records=len(records),
    )

    batches = create_training_pairs(records, model, config.batch_size, config.seed)

    if not batches:
        logger.warning("no_training_batches", reason="insufficient_pairs")
        return metrics

    for epoch in range(config.epochs):
        epoch_losses = []

        for emb_a, emb_b in batches:
            emb_a = normalize_embeddings(emb_a)
            emb_b = normalize_embeddings(emb_b)
            loss = contrastive_loss(emb_a, emb_b, temperature=config.temperature)
            epoch_losses.append(loss)

        avg_loss = float(np.mean(epoch_losses))
        metrics.avg_loss_per_epoch.append(avg_loss)
        metrics.epoch = epoch + 1

        if avg_loss < metrics.best_loss:
            metrics.best_loss = avg_loss
            metrics.best_epoch = epoch + 1

        logger.info(
            "training_epoch_complete",
            epoch=epoch + 1,
            avg_loss=f"{avg_loss:.6f}",
            best_loss=f"{metrics.best_loss:.6f}",
        )

    metrics.loss = metrics.avg_loss_per_epoch[-1] if metrics.avg_loss_per_epoch else 0.0

    logger.info(
        "training_complete",
        final_loss=f"{metrics.loss:.6f}",
        best_loss=f"{metrics.best_loss:.6f}",
        best_epoch=metrics.best_epoch,
    )

    return metrics


def main() -> None:
    """CLI entry point for embedding fine-tuning."""
    import argparse
    import json

    from src.utils.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="SigLIP-2 embedding fine-tuning")
    parser.add_argument(
        "--config",
        default="configs/experiments/default.yaml",
        help="Path to training config YAML",
    )
    parser.add_argument(
        "--data-dir",
        default="data/raw/scin",
        help="Path to SCIN data directory",
    )
    args = parser.parse_args()

    # Load training records
    from pathlib import Path

    data_dir = Path(args.data_dir)
    metadata_path = data_dir / "metadata.json"

    if metadata_path.exists():
        with open(metadata_path) as f:
            records = json.load(f)
        if isinstance(records, dict):
            records = records.get("records", [])
        # Resolve relative image paths against data_dir
        for r in records:
            if "image_path" in r:
                r["image_path"] = str(data_dir / r["image_path"])
    else:
        logger.warning("no_metadata_found", path=str(metadata_path))
        logger.info("using_mock_data", hint="Run: bash scripts/init_data.sh --mock")
        records = [
            {"image_path": f"data/raw/scin/images/00{i}.jpg", "diagnosis": f"L{20 + i % 5}.0"}
            for i in range(1, 7)
        ]

    # Load config overrides if YAML exists
    config = TrainingConfig()
    config_path = Path(args.config)
    if config_path.exists():
        import yaml  # type: ignore[import-untyped]

        with open(config_path) as f:
            overrides = yaml.safe_load(f) or {}
        for k, v in overrides.items():
            if hasattr(config, k):
                setattr(config, k, v)

    logger.info("training_cli_start", records=len(records), config=str(config_path))
    metrics = run_training(records, config)
    logger.info(
        "training_cli_done",
        epochs=metrics.epoch,
        final_loss=f"{metrics.loss:.6f}",
        best_loss=f"{metrics.best_loss:.6f}",
    )


if __name__ == "__main__":
    main()
