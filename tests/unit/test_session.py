"""Tests for session management."""

from __future__ import annotations

from src.utils.session import PatientSession, SessionStage, SessionStore


class TestPatientSession:
    """Test patient session model."""

    def test_create_session(self):
        """Session initializes with UUID and default stage."""
        session = PatientSession()
        assert session.session_id
        assert session.stage == SessionStage.GREETING
        assert session.image_consent_given is False

    def test_advance_stage(self):
        """Session stage can be advanced."""
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        assert session.stage == SessionStage.INTERVIEW

    def test_add_transcript(self):
        """Transcript segments can be added."""
        session = PatientSession()
        session.add_transcript("I have a rash")
        session.add_transcript("It started three days ago")
        assert len(session.transcript) == 2

    def test_grant_consent(self):
        """Image consent can be granted."""
        session = PatientSession()
        assert not session.image_consent_given
        session.grant_image_consent()
        assert session.image_consent_given

    def test_mark_escalated(self):
        """Session can be escalated."""
        session = PatientSession()
        session.mark_escalated("suspected melanoma")
        assert session.escalated
        assert session.escalation_reason == "suspected melanoma"
        assert session.stage == SessionStage.ESCALATED


class TestSessionStore:
    """Test session store."""

    def test_create_and_get(self):
        """Create and retrieve a session."""
        store = SessionStore()
        session = store.create()
        assert store.get(session.session_id) is session

    def test_get_nonexistent(self):
        """Getting nonexistent session returns None."""
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_delete(self):
        """Session can be deleted."""
        store = SessionStore()
        session = store.create()
        assert store.delete(session.session_id)
        assert store.get(session.session_id) is None

    def test_active_count(self):
        """Active count reflects current sessions."""
        store = SessionStore()
        store.create()
        store.create()
        assert store.active_count == 2
