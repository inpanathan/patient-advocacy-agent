"""SCIN database loader — ingestion, parsing, and validation.

Loads the Harvard SCIN dermatological database from disk, validates
records against the schema, computes baseline statistics, and provides
an iterable interface for downstream consumers.

Covers: REQ-DAT-002, REQ-TST-004, REQ-TST-005
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import structlog

from src.data.scin_schema import SCINDatasetStats, SCINRecord
from src.utils.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)


class SCINLoaderProtocol(Protocol):
    """Interface for SCIN data loading implementations."""

    def load(self) -> list[SCINRecord]:
        """Load and validate all SCIN records."""
        ...

    def compute_stats(self, records: list[SCINRecord]) -> SCINDatasetStats:
        """Compute baseline statistics from records."""
        ...


class SCINLoader:
    """Production SCIN database loader.

    Reads SCIN data from the configured directory, parses each record,
    validates against the schema, and reports quality issues.

    TODO: Requires actual SCIN dataset files at settings.scin.data_dir.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self._validation_errors: list[dict] = []

    def load(self) -> list[SCINRecord]:
        """Load and validate all SCIN records from disk.

        Returns:
            List of validated SCINRecord instances.

        Raises:
            AppError: If data directory doesn't exist or no valid records found.
        """
        if not self.data_dir.exists():
            raise AppError(
                code=ErrorCode.DATA_LOAD_FAILED,
                message=f"SCIN data directory not found: {self.data_dir}",
                context={"data_dir": str(self.data_dir)},
            )

        metadata_file = self.data_dir / "metadata.json"
        if not metadata_file.exists():
            raise AppError(
                code=ErrorCode.DATA_LOAD_FAILED,
                message=f"SCIN metadata file not found: {metadata_file}",
                context={"expected_path": str(metadata_file)},
            )

        raw_data = json.loads(metadata_file.read_text())
        records: list[SCINRecord] = []
        self._validation_errors = []

        for i, raw_record in enumerate(raw_data.get("records", [])):
            try:
                record = SCINRecord(**raw_record)
                records.append(record)
            except Exception as e:
                self._validation_errors.append(
                    {"index": i, "error": str(e), "record_id": raw_record.get("record_id", "?")}
                )

        logger.info(
            "scin_load_complete",
            total_raw=len(raw_data.get("records", [])),
            valid_records=len(records),
            validation_errors=len(self._validation_errors),
        )

        if not records:
            raise AppError(
                code=ErrorCode.DATA_VALIDATION_FAILED,
                message="No valid SCIN records found after validation",
                context={"errors": self._validation_errors[:10]},
            )

        return records

    @property
    def validation_errors(self) -> list[dict]:
        """Return validation errors from the last load()."""
        return self._validation_errors

    def compute_stats(self, records: list[SCINRecord]) -> SCINDatasetStats:
        """Compute baseline statistics from loaded records.

        These stats are stored for later drift comparison.
        """
        stats = SCINDatasetStats(total_records=len(records))

        for r in records:
            stats.records_per_diagnosis[r.diagnosis] = (
                stats.records_per_diagnosis.get(r.diagnosis, 0) + 1
            )
            stats.records_per_fitzpatrick[r.fitzpatrick_type] = (
                stats.records_per_fitzpatrick.get(r.fitzpatrick_type, 0) + 1
            )
            stats.records_per_severity[r.severity] = (
                stats.records_per_severity.get(r.severity, 0) + 1
            )
            stats.icd_code_distribution[r.icd_code] = (
                stats.icd_code_distribution.get(r.icd_code, 0) + 1
            )
            if r.image_path:
                stats.image_count += 1

            # Track missing optional fields
            for field_name in ("body_location", "age_group", "description"):
                if not getattr(r, field_name):
                    stats.missing_fields[field_name] = (
                        stats.missing_fields.get(field_name, 0) + 1
                    )

        logger.info(
            "scin_stats_computed",
            total_records=stats.total_records,
            unique_diagnoses=len(stats.records_per_diagnosis),
            unique_icd_codes=len(stats.icd_code_distribution),
            fitzpatrick_types=len(stats.records_per_fitzpatrick),
        )

        return stats
