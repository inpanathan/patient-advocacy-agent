"""Tests for audit trail."""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.observability.audit import AuditRecord, AuditTrail


class TestAuditRecord:
    """Test AuditRecord creation and serialization."""

    def test_create_record(self):
        """Audit record has required fields."""
        record = AuditRecord(
            trace_id="trace-001",
            session_id="sess-001",
            model_id="mock-medgemma-v1",
            icd_codes=["L20.0"],
            confidence=0.78,
        )
        assert record.trace_id == "trace-001"
        assert record.timestamp  # Auto-set

    def test_to_dict(self):
        """Record serializes to dictionary."""
        record = AuditRecord(
            trace_id="trace-002",
            session_id="sess-002",
            model_id="medgemma",
            icd_codes=["L20.0", "L25.0"],
            confidence=0.85,
            escalated=True,
            escalation_reason="melanoma detected",
        )
        d = record.to_dict()
        assert d["trace_id"] == "trace-002"
        assert d["icd_codes"] == ["L20.0", "L25.0"]
        assert d["escalated"] is True


class TestAuditTrail:
    """Test AuditTrail operations."""

    def test_add_and_retrieve_by_session(self):
        """Records can be retrieved by session ID."""
        trail = AuditTrail()
        trail.record(AuditRecord(trace_id="t1", session_id="s1"))
        trail.record(AuditRecord(trace_id="t2", session_id="s1"))
        trail.record(AuditRecord(trace_id="t3", session_id="s2"))

        results = trail.get_by_session("s1")
        assert len(results) == 2

    def test_retrieve_by_trace_id(self):
        """Record can be retrieved by trace ID."""
        trail = AuditTrail()
        trail.record(AuditRecord(trace_id="t1", session_id="s1", model_id="v1"))
        result = trail.get_by_trace("t1")
        assert result is not None
        assert result.model_id == "v1"

    def test_nonexistent_trace_returns_none(self):
        """Missing trace ID returns None."""
        trail = AuditTrail()
        assert trail.get_by_trace("nonexistent") is None

    def test_size_tracking(self):
        """Size reflects number of records."""
        trail = AuditTrail()
        assert trail.size == 0
        trail.record(AuditRecord(trace_id="t1", session_id="s1"))
        assert trail.size == 1

    def test_export_all(self):
        """All records can be exported."""
        trail = AuditTrail()
        trail.record(AuditRecord(trace_id="t1", session_id="s1"))
        trail.record(AuditRecord(trace_id="t2", session_id="s2"))
        exported = trail.export_all()
        assert len(exported) == 2
        assert exported[0]["trace_id"] == "t1"

    def test_persist_to_file(self):
        """Records persist to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "audit.jsonl")
            trail = AuditTrail(persist_path=path)
            trail.record(AuditRecord(trace_id="t1", session_id="s1"))
            trail.record(AuditRecord(trace_id="t2", session_id="s2"))

            # Verify file has 2 lines
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2
