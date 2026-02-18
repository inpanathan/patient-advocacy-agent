"""GenAI regression tests.

Golden prompt suite to detect regressions when model or prompt changes occur.
Each test captures expected behavior characteristics that must be preserved.

Covers: REQ-TST-030
"""

from __future__ import annotations

import pytest

from src.models.mocks.mock_medical import MockMedicalModel
from src.models.protocols.voice import STTResult
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession, SessionStage


class TestGoldenPromptSuite:
    """Golden prompt/response pairs that must remain stable across versions."""

    @pytest.mark.asyncio
    async def test_greeting_mentions_not_doctor(self):
        """Golden: greeting always includes 'not a doctor'."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        response = await agent.process_utterance(session, stt)
        assert "not a doctor" in response.lower()
        assert "tell me" in response.lower() or "bothering" in response.lower()

    @pytest.mark.asyncio
    async def test_greeting_advances_to_interview(self):
        """Golden: greeting moves session to interview stage."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Namaste", language="hi", confidence=0.92, duration_ms=0)
        await agent.process_utterance(session, stt)
        assert session.stage == SessionStage.INTERVIEW

    @pytest.mark.asyncio
    async def test_deescalation_response_format(self):
        """Golden: de-escalation response mentions non-medical nature."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(
            text="I got paint on my hand",
            language="en",
            confidence=0.9,
            duration_ms=0,
        )
        response = await agent.process_utterance(session, stt)
        assert "paint" in response.lower() or "not" in response.lower()
        assert "medical" in response.lower() or "worry" in response.lower()

    @pytest.mark.asyncio
    async def test_soap_note_structure_complete(self):
        """Golden: SOAP note always has all four sections populated."""
        session = PatientSession()
        session.add_transcript("I have a rash on my arm that is red and itchy")
        soap = await generate_soap_note(session)
        assert soap.subjective, "SOAP subjective is empty"
        assert soap.objective, "SOAP objective is empty"
        assert soap.assessment, "SOAP assessment is empty"
        assert soap.plan, "SOAP plan is empty"

    @pytest.mark.asyncio
    async def test_soap_note_has_icd_codes(self):
        """Golden: SOAP note always includes at least one ICD code."""
        session = PatientSession()
        session.add_transcript("Red bumpy rash on forearm for 2 days")
        soap = await generate_soap_note(session)
        assert len(soap.icd_codes) >= 1
        # All ICD codes should be dermatology range
        for code in soap.icd_codes:
            assert code.startswith("L"), f"ICD code {code} not in dermatology range"

    @pytest.mark.asyncio
    async def test_soap_confidence_in_range(self):
        """Golden: SOAP confidence is always between 0 and 1."""
        session = PatientSession()
        session.add_transcript("Itchy patches on my skin")
        soap = await generate_soap_note(session)
        assert 0.0 <= soap.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_soap_disclaimer_always_present(self):
        """Golden: SOAP note always has a disclaimer."""
        session = PatientSession()
        session.add_transcript("Skin rash description")
        soap = await generate_soap_note(session)
        assert soap.disclaimer
        assert "not a medical diagnosis" in soap.disclaimer.lower()


class TestModelResponseConsistency:
    """Ensure model responses maintain expected structure."""

    @pytest.mark.asyncio
    async def test_model_generate_returns_text(self):
        """Model.generate always returns non-empty text."""
        model = MockMedicalModel()
        response = await model.generate(prompt="Describe a rash")
        assert response.text
        assert len(response.text) > 10

    @pytest.mark.asyncio
    async def test_model_generate_tracks_tokens(self):
        """Model.generate reports token usage."""
        model = MockMedicalModel()
        response = await model.generate(prompt="Test prompt")
        assert response.prompt_tokens > 0
        assert response.completion_tokens > 0

    @pytest.mark.asyncio
    async def test_model_generate_reports_latency(self):
        """Model.generate reports latency."""
        model = MockMedicalModel()
        response = await model.generate(prompt="Test")
        assert response.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_soap_icd_codes_are_valid_format(self):
        """ICD codes from SOAP follow the expected format."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="itchy rash")
        for code in soap.icd_codes:
            # ICD-10 format: letter followed by 2 digits, optionally a dot and 1-4 digits
            assert len(code) >= 3
            assert code[0].isalpha()
            assert code[1:3].isdigit()


class TestEscalationRegression:
    """Escalation behavior must remain stable."""

    def test_melanoma_always_escalates(self):
        """The word 'melanoma' must always trigger escalation."""
        agent = PatientInterviewAgent()
        assert agent.check_escalation("Suspected melanoma") is not None

    def test_cancer_always_escalates(self):
        """The word 'cancer' must always trigger escalation."""
        agent = PatientInterviewAgent()
        assert agent.check_escalation("Possible skin cancer") is not None

    def test_benign_eczema_never_escalates(self):
        """Eczema without concerning features does not escalate."""
        agent = PatientInterviewAgent()
        assert agent.check_escalation("Mild eczema L20.0 on forearm") is None

    def test_escalation_returns_reason(self):
        """Escalation result includes a reason string."""
        agent = PatientInterviewAgent()
        reason = agent.check_escalation("Rapidly growing lesion on back")
        assert reason is not None
        assert "rapidly growing" in reason.lower()
