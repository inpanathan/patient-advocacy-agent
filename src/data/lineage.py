"""Data lineage tracking for SCIN pipeline.

Tracks the transformation steps from raw SCIN data through processing
to features, enabling full traceability of any derived artifact.

Covers: REQ-DAT-005, REQ-OBS-009
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class LineageStep(BaseModel):
    """A single step in the data lineage chain."""

    step_name: str
    input_source: str
    output_target: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )
    record_count: int = 0
    metadata: dict = Field(default_factory=dict)


class DataLineage(BaseModel):
    """Full lineage chain for a dataset or artifact."""

    artifact_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )
    steps: list[LineageStep] = Field(default_factory=list)

    def add_step(
        self,
        step_name: str,
        input_source: str,
        output_target: str,
        record_count: int = 0,
        **metadata: object,
    ) -> None:
        """Record a transformation step."""
        step = LineageStep(
            step_name=step_name,
            input_source=input_source,
            output_target=output_target,
            record_count=record_count,
            metadata=metadata,
        )
        self.steps.append(step)
        logger.info(
            "lineage_step_recorded",
            artifact_id=self.artifact_id,
            step_name=step_name,
            input_source=input_source,
            output_target=output_target,
            record_count=record_count,
        )

    def save(self, path: str | Path) -> None:
        """Save lineage to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))
        logger.info("lineage_saved", artifact_id=self.artifact_id, path=str(path))

    @classmethod
    def load(cls, path: str | Path) -> DataLineage:
        """Load lineage from JSON file."""
        return cls.model_validate_json(Path(path).read_text())
