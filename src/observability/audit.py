"""Audit trail for prediction provenance.

Records which model version, data version, config, and RAG context
produced each prediction, enabling full traceability.

Covers: REQ-OBS-063
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AuditRecord:
    """A single audit trail entry for one prediction."""

    trace_id: str
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    model_id: str = ""
    model_version: str = ""
    config_hash: str = ""
    data_version: str = ""
    icd_codes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    escalated: bool = False
    escalation_reason: str = ""
    rag_record_ids: list[str] = field(default_factory=list)
    rag_top_score: float = 0.0
    image_captured: bool = False
    patient_language: str = ""
    fitzpatrick_type: str = ""
    disclaimer_included: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


class AuditTrail:
    """Manages the audit trail for prediction provenance.

    Stores records in memory and can persist to a JSONL file
    for compliance and debugging.
    """

    def __init__(self, persist_path: str | None = None) -> None:
        self._records: list[AuditRecord] = []
        self._persist_path = Path(persist_path) if persist_path else None

    def record(self, entry: AuditRecord) -> None:
        """Add an audit record."""
        self._records.append(entry)
        logger.info(
            "audit_record_created",
            trace_id=entry.trace_id,
            session_id=entry.session_id,
            model_id=entry.model_id,
            icd_codes=entry.icd_codes,
            escalated=entry.escalated,
        )

        # Persist if configured
        if self._persist_path:
            self._append_to_file(entry)

    def get_by_session(self, session_id: str) -> list[AuditRecord]:
        """Get all audit records for a session."""
        return [r for r in self._records if r.session_id == session_id]

    def get_by_trace(self, trace_id: str) -> AuditRecord | None:
        """Get audit record by trace ID."""
        for r in self._records:
            if r.trace_id == trace_id:
                return r
        return None

    @property
    def size(self) -> int:
        """Number of audit records."""
        return len(self._records)

    def _append_to_file(self, entry: AuditRecord) -> None:
        """Append a record to the JSONL audit file."""
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def export_all(self) -> list[dict]:
        """Export all records as dictionaries."""
        return [r.to_dict() for r in self._records]
