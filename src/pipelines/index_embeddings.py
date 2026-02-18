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
) -> int:
    """Embed and index all SCIN records.

    Args:
        records: List of validated SCIN records.
        index: Vector index to add embeddings to.
        batch_size: Number of records to process per batch.

    Returns:
        Number of records indexed.
    """
    model = get_embedding_model()
    total_indexed = 0

    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        items = [{"image_path": r.image_path} for r in batch]
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
