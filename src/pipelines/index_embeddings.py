"""SCIN embedding indexer.

Embeds all SCIN images and stores them in the vector index
with associated metadata for retrieval.

Covers: REQ-DAT-002
"""

from __future__ import annotations

import structlog

from src.data.scin_schema import SCINRecord
from src.models.embedding_model import get_embedding_model
from src.models.rag_retrieval import VectorIndex

logger = structlog.get_logger(__name__)


def index_scin_records(
    records: list[SCINRecord],
    index: VectorIndex,
    batch_size: int = 32,
    data_dir: str = "",
) -> int:
    """Embed and index all SCIN records.

    Args:
        records: List of validated SCIN records.
        index: Vector index to add embeddings to.
        batch_size: Number of records to process per batch.
        data_dir: Base directory for resolving relative image paths.

    Returns:
        Number of records indexed.
    """
    from pathlib import Path

    base = Path(data_dir) if data_dir else Path()
    model = get_embedding_model()
    total_indexed = 0

    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        items = [{"image_path": str(base / r.image_path)} for r in batch]
        metadata = [
            {
                "record_id": r.record_id,
                "diagnosis": r.diagnosis,
                "icd_code": r.icd_code,
                "fitzpatrick_type": r.fitzpatrick_type,
                "image_path": r.image_path,
                "body_location": r.body_location,
                "severity": r.severity,
            }
            for r in batch
        ]

        embeddings = model.embed_batch(items)
        index.add(embeddings, metadata)
        total_indexed += len(batch)

        logger.info(
            "indexing_progress",
            indexed=total_indexed,
            total=len(records),
            pct=f"{total_indexed / len(records) * 100:.1f}%",
        )

    logger.info("indexing_complete", total_indexed=total_indexed)
    return total_indexed


def main() -> None:
    """CLI entry point for SCIN embedding indexing."""
    import argparse
    import json
    from pathlib import Path

    from src.utils.config import settings
    from src.utils.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Index SCIN embeddings into vector store")
    parser.add_argument(
        "--data-dir",
        default=settings.scin.data_dir,
        help="Path to SCIN data directory",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    metadata_path = data_dir / "metadata.json"

    if not metadata_path.exists():
        logger.error("metadata_not_found", path=str(metadata_path))
        logger.info("hint", run="bash scripts/init_data.sh --mock")
        return

    with open(metadata_path) as f:
        raw = json.load(f)

    raw_records = raw if isinstance(raw, list) else raw.get("records", [])

    records = []
    for r in raw_records:
        try:
            records.append(SCINRecord(**r))
        except (TypeError, ValueError) as e:
            logger.warning("skipping_invalid_record", error=str(e))

    if not records:
        logger.warning("no_valid_records")
        return

    index = VectorIndex()
    total = index_scin_records(records, index, batch_size=args.batch_size, data_dir=str(data_dir))
    logger.info("indexing_cli_done", total_indexed=total)


if __name__ == "__main__":
    main()
