"""Tests for the in-memory log buffer."""

from __future__ import annotations

from src.observability.log_buffer import LogBuffer, LogRecord


def _make_record(
    level: str = "INFO",
    event: str = "test_event",
    logger_name: str = "test",
    fields: dict | None = None,
    timestamp: str = "2025-01-01T00:00:00+00:00",
) -> LogRecord:
    return LogRecord(
        timestamp=timestamp,
        level=level,
        event=event,
        logger_name=logger_name,
        fields=fields or {},
    )


class TestLogBuffer:
    """Tests for LogBuffer ring buffer behavior."""

    def test_stores_records(self) -> None:
        buf = LogBuffer(max_size=10)
        rec = _make_record()
        buf.append(rec)
        assert buf.size == 1
        results = buf.query(limit=10)
        assert len(results) == 1
        assert results[0].event == "test_event"

    def test_evicts_oldest_when_full(self) -> None:
        buf = LogBuffer(max_size=3)
        for i in range(5):
            buf.append(_make_record(event=f"event_{i}"))
        assert buf.size == 3
        results = buf.query(limit=10)
        # Most recent first
        events = [r.event for r in results]
        assert events == ["event_4", "event_3", "event_2"]

    def test_query_filter_by_level(self) -> None:
        buf = LogBuffer(max_size=100)
        buf.append(_make_record(level="INFO", event="info_event"))
        buf.append(_make_record(level="ERROR", event="error_event"))
        buf.append(_make_record(level="INFO", event="info_event_2"))

        results = buf.query(level="ERROR", limit=10)
        assert len(results) == 1
        assert results[0].event == "error_event"

    def test_query_filter_by_event(self) -> None:
        buf = LogBuffer(max_size=100)
        buf.append(_make_record(event="prediction_recorded"))
        buf.append(_make_record(event="session_created"))
        buf.append(_make_record(event="prediction_failed"))

        results = buf.query(event="prediction", limit=10)
        assert len(results) == 2

    def test_query_filter_by_search(self) -> None:
        buf = LogBuffer(max_size=100)
        buf.append(_make_record(event="soap_generated", fields={"icd_codes": "L20.0"}))
        buf.append(_make_record(event="other_event", fields={"data": "unrelated"}))

        results = buf.query(search="L20", limit=10)
        assert len(results) == 1
        assert results[0].event == "soap_generated"

    def test_query_filter_by_session_id(self) -> None:
        buf = LogBuffer(max_size=100)
        buf.append(_make_record(fields={"session_id": "abc-123"}))
        buf.append(_make_record(fields={"session_id": "def-456"}))

        results = buf.query(session_id="abc-123", limit=10)
        assert len(results) == 1

    def test_empty_buffer_returns_empty_list(self) -> None:
        buf = LogBuffer(max_size=100)
        results = buf.query(limit=10)
        assert results == []

    def test_clear(self) -> None:
        buf = LogBuffer(max_size=100)
        buf.append(_make_record())
        buf.append(_make_record())
        assert buf.size == 2
        buf.clear()
        assert buf.size == 0

    def test_query_respects_limit(self) -> None:
        buf = LogBuffer(max_size=100)
        for i in range(20):
            buf.append(_make_record(event=f"event_{i}"))
        results = buf.query(limit=5)
        assert len(results) == 5
