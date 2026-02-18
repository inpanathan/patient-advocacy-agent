"""Tests for patient interview agent."""

from __future__ import annotations

import pytest

from src.models.protocols.voice import STTResult
from src.pipelines.patient_interview import (
    PatientInterviewAgent,
)
from src.utils.session import PatientSession, SessionStage


class TestPatientInterviewAgent:
    """Test interview agent behavior."""

    @pytest.mark.asyncio
    async def test_greeting_phase(self):
        """Greeting advances to interview stage."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Hello", language="hi", confidence=0.95, duration_ms=1000)

        response = await agent.process_utterance(session, stt)
        assert session.stage == SessionStage.INTERVIEW
        assert session.detected_language == "hi"
        assert "not a doctor" in response.lower() or "health assistant" in response.lower()

    @pytest.mark.asyncio
    async def test_interview_adds_transcript(self):
        """Utterances are added to session transcript."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        stt = STTResult(text="I have a rash", language="en", confidence=0.9, duration_ms=500)

        await agent.process_utterance(session, stt)
        assert "I have a rash" in session.transcript

    @pytest.mark.asyncio
    async def test_image_consent_requested_after_enough_info(self):
        """Agent requests image consent after 3+ transcript entries."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        # Pre-fill transcript to trigger consent request
        session.transcript = ["symptom 1", "symptom 2"]

        stt = STTResult(text="symptom 3", language="en", confidence=0.9, duration_ms=500)
        await agent.process_utterance(session, stt)
        assert session.stage == SessionStage.IMAGE_CONSENT

    @pytest.mark.asyncio
    async def test_consent_granted(self):
        """Patient saying yes grants consent."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.IMAGE_CONSENT)
        stt = STTResult(text="Yes, okay", language="en", confidence=0.9, duration_ms=500)

        await agent.process_utterance(session, stt)
        assert session.image_consent_given is True
        assert session.stage == SessionStage.IMAGE_CAPTURE

    @pytest.mark.asyncio
    async def test_consent_denied(self):
        """Patient saying no skips image capture."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.IMAGE_CONSENT)
        stt = STTResult(
            text="No, I don't want that", language="en", confidence=0.9, duration_ms=500,
        )
        await agent.process_utterance(session, stt)
        assert session.image_consent_given is False
        assert session.stage == SessionStage.INTERVIEW

    @pytest.mark.asyncio
    async def test_deescalation(self):
        """De-escalation keywords trigger de-escalation response."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        stt = STTResult(
            text="I have paint on my hand",
            language="en",
            confidence=0.9,
            duration_ms=500,
        )

        response = await agent.process_utterance(session, stt)
        assert "not a skin condition" in response.lower() or "paint" in response.lower()

    def test_escalation_check_detects_malignancy(self):
        """Escalation keywords in SOAP trigger escalation."""
        agent = PatientInterviewAgent()
        reason = agent.check_escalation("Assessment: suspected melanoma with irregular borders")
        assert reason is not None
        assert "melanoma" in reason

    def test_escalation_check_no_trigger(self):
        """Normal SOAP text doesn't trigger escalation."""
        agent = PatientInterviewAgent()
        reason = agent.check_escalation("Assessment: mild contact dermatitis")
        assert reason is None
