"""In-memory ring buffer for structured log capture.

Captures structlog JSON output in a fixed-size ring buffer for the
dashboard log viewer. Older entries are evicted when the buffer is full.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class LogRecord:
    """A single captured log record."""

    timestamp: str
    level: str
    event: str
    logger_name: str
    fields: dict[str, object] = field(default_factory=dict)


class LogBuffer:
    """Thread-safe ring buffer for log records.

    Args:
        max_size: Maximum number of records to retain. Oldest are evicted first.
    """

    def __init__(self, max_size: int = 5000) -> None:
        self._buffer: deque[LogRecord] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def append(self, record: LogRecord) -> None:
        """Add a log record (oldest evicted when full)."""
        with self._lock:
            self._buffer.append(record)

    def query(
        self,
        *,
        level: str = "",
        event: str = "",
        search: str = "",
        session_id: str = "",
        since: str = "",
        limit: int = 200,
    ) -> list[LogRecord]:
        """Filter and return matching records.

        Args:
            level: Filter by log level (e.g. "ERROR").
            event: Filter by event name (exact match).
            search: Free-text search across event and field values.
            session_id: Filter by session_id field.
            since: ISO timestamp — only return records after this time.
            limit: Maximum number of records to return.
        """
        with self._lock:
            results: list[LogRecord] = []
            for rec in reversed(self._buffer):
                if level and rec.level.upper() != level.upper():
                    continue
                if event and event.lower() not in rec.event.lower():
                    continue
                if session_id and rec.fields.get("session_id") != session_id:
                    continue
                if since and rec.timestamp < since:
                    continue
                if search:
                    search_lower = search.lower()
                    haystack = (
                        rec.event.lower()
                        + " "
                        + " ".join(str(v).lower() for v in rec.fields.values())
                    )
                    if search_lower not in haystack:
                        continue
                results.append(rec)
                if len(results) >= limit:
                    break
            return results

    @property
    def size(self) -> int:
        """Number of records currently in the buffer."""
        return len(self._buffer)

    def clear(self) -> None:
        """Remove all records."""
        with self._lock:
            self._buffer.clear()


class BufferHandler(logging.Handler):
    """stdlib logging handler that captures records into a LogBuffer.

    Parses structlog JSON output and extracts structured fields.
    """

    def __init__(self, buffer: LogBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        """Parse the log record and append to buffer."""
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            # Try to parse as JSON (structlog JSONRenderer output)
            fields: dict[str, object] = {}
            event = msg
            try:
                parsed = json.loads(msg)
                if isinstance(parsed, dict):
                    event = str(parsed.pop("event", msg))
                    parsed.pop("timestamp", None)
                    parsed.pop("level", None)
                    parsed.pop("logger", None)
                    fields = parsed
            except (json.JSONDecodeError, TypeError):
                pass

            log_record = LogRecord(
                timestamp=datetime.now(tz=UTC).isoformat(),
                level=record.levelname,
                event=event,
                logger_name=record.name or "",
                fields=fields,
            )
            self._buffer.append(log_record)
        except Exception:  # noqa: BLE001
            # Never let logging crash the application
            pass


# Singleton
_log_buffer: LogBuffer | None = None


def get_log_buffer() -> LogBuffer:
    """Get the global log buffer singleton."""
    global _log_buffer  # noqa: PLW0603
    if _log_buffer is None:
        _log_buffer = LogBuffer()
    return _log_buffer
