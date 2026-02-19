"""Tests for patient interview agent."""

from __future__ import annotations

import pytest

from src.models.protocols.voice import STTResult
from src.pipelines.patient_interview import (
    TOPIC_QUESTIONS,
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
    async def test_image_consent_requested_after_enough_topics(self):
        """Agent requests image consent when 4+ topics are answered."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        # Pre-fill 3 answered topics so the next utterance pushes to 4+
        session.answered_topics = {
            "chief_complaint": "rash",
            "location": "arm",
            "duration": "two weeks",
        }

        # This utterance covers "symptoms" (itchy) → 4 topics total → triggers consent
        stt = STTResult(text="It is very itchy", language="en", confidence=0.9, duration_ms=500)
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
            text="No, I don't want that",
            language="en",
            confidence=0.9,
            duration_ms=500,
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


class TestTopicExtraction:
    """Test keyword-based topic extraction."""

    def test_extract_chief_complaint(self):
        """Detects chief complaint from common skin terms."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("I have a rash on my body")
        assert "chief_complaint" in topics

    def test_extract_location(self):
        """Detects body location keywords."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("It is on my arm")
        assert "location" in topics

    def test_extract_duration(self):
        """Detects duration keywords."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("I have had it for two weeks")
        assert "duration" in topics

    def test_extract_progression(self):
        """Detects progression keywords."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("It is getting worse")
        assert "progression" in topics

    def test_extract_symptoms(self):
        """Detects symptom keywords."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("It hurts and itches a lot")
        assert "symptoms" in topics

    def test_extract_multiple_topics_single_utterance(self):
        """Extracts multiple topics from a rich patient utterance."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("I have a rash on my arm for two weeks")
        assert "chief_complaint" in topics
        assert "location" in topics
        assert "duration" in topics

    def test_extract_no_topics_from_greeting(self):
        """Returns empty dict for text without medical keywords."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("Hello how are you")
        assert topics == {}

    def test_extract_topics_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        agent = PatientInterviewAgent()
        topics = agent._extract_topics("I have a RASH on my ARM")
        assert "chief_complaint" in topics
        assert "location" in topics


class TestDynamicPrompt:
    """Test dynamic prompt construction."""

    def test_prompt_shows_unanswered_only(self):
        """Prompt lists only unanswered topics when some are already covered."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.answered_topics = {
            "chief_complaint": "rash",
            "location": "arm",
        }
        unanswered = [t for t in TOPIC_QUESTIONS if t not in session.answered_topics]
        prompt = agent._build_dynamic_prompt(session, unanswered)

        assert "What the patient has told you so far:" in prompt
        assert "rash" in prompt
        assert "arm" in prompt
        assert "You still need to ask about:" in prompt
        # Chief complaint and location should NOT be in unanswered section
        assert "How long have you had it?" in prompt
        assert "Does it itch, hurt, or burn?" in prompt

    def test_prompt_all_answered(self):
        """Prompt says all topics covered when nothing remains."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.answered_topics = {
            "chief_complaint": "rash",
            "location": "arm",
            "duration": "two weeks",
            "progression": "getting worse",
            "symptoms": "itchy",
        }
        prompt = agent._build_dynamic_prompt(session, [])

        assert "All topics are covered" in prompt
        assert "You still need to ask about:" not in prompt

    @pytest.mark.asyncio
    async def test_answered_topics_not_re_asked(self):
        """Topics detected in first utterance are tracked in session."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)

        stt = STTResult(
            text="I have a rash on my arm for two weeks",
            language="en",
            confidence=0.9,
            duration_ms=500,
        )
        await agent.process_utterance(session, stt)

        # These topics should have been detected
        assert "chief_complaint" in session.answered_topics
        assert "location" in session.answered_topics
        assert "duration" in session.answered_topics

    @pytest.mark.asyncio
    async def test_all_topics_triggers_image_consent(self):
        """When all 5 topics are covered, agent moves to image consent."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        session.advance_to(SessionStage.INTERVIEW)
        # Pre-fill 4 topics
        session.answered_topics = {
            "chief_complaint": "rash",
            "location": "arm",
            "duration": "two weeks",
            "symptoms": "itchy",
        }

        # This covers the last topic (progression)
        stt = STTResult(
            text="It is getting worse every day",
            language="en",
            confidence=0.9,
            duration_ms=500,
        )
        await agent.process_utterance(session, stt)

        assert "progression" in session.answered_topics
        assert session.stage == SessionStage.IMAGE_CONSENT
