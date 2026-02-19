"""Patient session management.

Tracks the state of each patient interaction: language, interview stage,
captured images, consent status, and generated outputs.

Covers: REQ-OBS-035, REQ-OBS-037
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SessionStage(StrEnum):
    """Stages of a patient interaction session."""

    GREETING = "greeting"
    LANGUAGE_DETECTION = "language_detection"
    INTERVIEW = "interview"
    IMAGE_CONSENT = "image_consent"
    IMAGE_CAPTURE = "image_capture"
    ANALYSIS = "analysis"
    EXPLANATION = "explanation"
    COMPLETE = "complete"
    ESCALATED = "escalated"


class PatientSession(BaseModel):
    """State for a single patient interaction session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    stage: SessionStage = SessionStage.GREETING
    detected_language: str = ""
    language_confidence: float = 0.0
    transcript: list[str] = Field(default_factory=list)
    conversation: list[dict[str, str]] = Field(default_factory=list)
    image_consent_given: bool = False
    captured_images: list[str] = Field(default_factory=list)
    soap_note_id: str = ""
    escalated: bool = False
    escalation_reason: str = ""
    image_analysis: str = ""
    answered_topics: dict[str, str] = Field(default_factory=dict)

    def advance_to(self, stage: SessionStage) -> None:
        """Advance session to a new stage."""
        logger.info(
            "session_stage_changed",
            session_id=self.session_id,
            from_stage=self.stage,
            to_stage=stage,
        )
        self.stage = stage

    def add_transcript(self, text: str) -> None:
        """Add a transcript segment."""
        self.transcript.append(text)

    def grant_image_consent(self) -> None:
        """Record that the patient has consented to image capture."""
        self.image_consent_given = True
        logger.info(
            "image_consent_granted",
            session_id=self.session_id,
        )

    def mark_escalated(self, reason: str) -> None:
        """Mark session as escalated (suspected malignancy or emergency)."""
        self.escalated = True
        self.escalation_reason = reason
        self.stage = SessionStage.ESCALATED
        logger.warning(
            "session_escalated",
            session_id=self.session_id,
            reason=reason,
        )


class SessionStore:
    """In-memory session store."""

    def __init__(self) -> None:
        self._sessions: dict[str, PatientSession] = {}

    def create(self) -> PatientSession:
        """Create a new patient session."""
        session = PatientSession()
        self._sessions[session.session_id] = session
        logger.info("session_created", session_id=session.session_id)
        return session

    def get(self, session_id: str) -> PatientSession | None:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("session_deleted", session_id=session_id)
            return True
        return False

    @property
    def active_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)
