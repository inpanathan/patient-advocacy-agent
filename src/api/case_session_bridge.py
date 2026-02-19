"""Bridge between DB-backed cases and in-memory PatientSessions.

Maps case_id → PatientSession so the existing PatientInterviewAgent
and generate_soap_note() work unchanged. On case completion, data is
written to the DB and the in-memory session is discarded.
"""

from __future__ import annotations

import uuid

from src.utils.logger import get_logger
from src.utils.session import PatientSession

logger = get_logger(__name__)


class CaseSessionBridge:
    """In-memory map from case_id to PatientSession."""

    def __init__(self) -> None:
        self._sessions: dict[str, PatientSession] = {}

    def get_or_create(self, case_id: uuid.UUID, language: str = "en") -> PatientSession:
        """Get the session for a case, creating one if needed."""
        key = str(case_id)
        if key not in self._sessions:
            session = PatientSession()
            session.detected_language = language
            self._sessions[key] = session
            logger.info(
                "case_session_created",
                case_id=key,
                session_id=session.session_id,
            )
        return self._sessions[key]

    def get(self, case_id: uuid.UUID) -> PatientSession | None:
        """Get the session for a case, or None."""
        return self._sessions.get(str(case_id))

    def discard(self, case_id: uuid.UUID) -> None:
        """Remove the session for a completed case."""
        key = str(case_id)
        if key in self._sessions:
            del self._sessions[key]
            logger.info("case_session_discarded", case_id=key)

    @property
    def active_count(self) -> int:
        """Number of active case sessions."""
        return len(self._sessions)
