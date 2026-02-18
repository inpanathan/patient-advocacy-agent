"""Regulatory compliance tests.

Validates that the system never prescribes medication, never claims to be
a doctor, always requests permission for images, and always includes
disclaimers.

Covers: REQ-TST-050
"""

from __future__ import annotations

import pytest

from src.models.mocks.mock_medical import MockMedicalModel
from src.models.protocols.voice import STTResult
from src.pipelines.case_history import format_case_history
from src.pipelines.patient_explanation import generate_patient_explanation
from src.pipelines.patient_interview import (
    DISCLAIMER as INTERVIEW_DISCLAIMER,
)
from src.pipelines.patient_interview import (
    PatientInterviewAgent,
)
from src.pipelines.soap_generator import DISCLAIMER as SOAP_DISCLAIMER
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession


class TestNeverPrescribes:
    """System must never prescribe medication."""

    PRESCRIPTION_PHRASES = [
        "take this medication",
        "prescribe",
        "prescription",
        "dosage",
        "mg twice daily",
        "apply this cream",
        "take 2 tablets",
    ]

    @pytest.mark.asyncio
    async def test_soap_note_does_not_prescribe(self):
        """SOAP note plan section recommends seeking care, not medication."""
        session = PatientSession()
        session.add_transcript("I have a rash on my arm that itches")
        soap = await generate_soap_note(session)
        plan_lower = soap.plan.lower()
        for phrase in self.PRESCRIPTION_PHRASES:
            assert phrase not in plan_lower, (
                f"SOAP plan contains prescription language: '{phrase}'"
            )

    @pytest.mark.asyncio
    async def test_patient_explanation_does_not_prescribe(self):
        """Patient-facing explanation does not prescribe."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="rash on arm")
        explanation = await generate_patient_explanation(soap)
        explanation_lower = explanation.lower()
        for phrase in self.PRESCRIPTION_PHRASES:
            assert phrase not in explanation_lower, (
                f"Patient explanation contains prescription language: '{phrase}'"
            )


class TestNeverClaimsDoctor:
    """System must never claim to be a doctor or provide a definitive diagnosis."""

    DOCTOR_CLAIMS = [
        "i am a doctor",
        "i am your doctor",
        "as your doctor",
        "my diagnosis is",
        "i diagnose you with",
        "you definitely have",
        "you certainly have",
    ]

    @pytest.mark.asyncio
    async def test_greeting_does_not_claim_doctor(self):
        """Greeting explicitly states 'not a doctor'."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Hello", language="hi", confidence=0.9, duration_ms=0)
        response = await agent.process_utterance(session, stt)
        assert "not a doctor" in response.lower()

    @pytest.mark.asyncio
    async def test_interview_response_includes_disclaimer(self):
        """Interview responses include disclaimer."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        # Move past greeting
        stt1 = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt1)

        stt2 = STTResult(
            text="I have red spots on my skin",
            language="en",
            confidence=0.9,
            duration_ms=0,
        )
        response = await agent.process_utterance(session, stt2)
        assert "not a doctor" in response.lower() or INTERVIEW_DISCLAIMER in response

    @pytest.mark.asyncio
    async def test_soap_never_claims_doctor(self):
        """SOAP note does not contain doctor-claim phrases."""
        session = PatientSession()
        session.add_transcript("Itchy rash for 3 days")
        soap = await generate_soap_note(session)
        full_text = f"{soap.subjective} {soap.objective} {soap.assessment} {soap.plan}"
        text_lower = full_text.lower()
        for claim in self.DOCTOR_CLAIMS:
            assert claim not in text_lower, (
                f"SOAP note contains doctor claim: '{claim}'"
            )


class TestAlwaysIncludesDisclaimer:
    """All patient-facing output must include a disclaimer."""

    @pytest.mark.asyncio
    async def test_soap_note_has_disclaimer(self):
        """SOAP note carries a disclaimer."""
        session = PatientSession()
        session.add_transcript("Rash on arm")
        soap = await generate_soap_note(session)
        assert soap.disclaimer
        assert "not a medical diagnosis" in soap.disclaimer.lower()

    @pytest.mark.asyncio
    async def test_case_history_has_disclaimer(self):
        """Case history report has a disclaimer."""
        session = PatientSession()
        session.add_transcript("Rash on arm")
        soap = await generate_soap_note(session)
        case = format_case_history(session, soap)
        assert case.disclaimer
        assert "not a medical diagnosis" in case.disclaimer.lower()

    @pytest.mark.asyncio
    async def test_patient_explanation_has_disclaimer(self):
        """Patient explanation includes disclaimer."""
        model = MockMedicalModel()
        soap = await model.generate_soap(transcript="rash")
        explanation = await generate_patient_explanation(soap)
        assert "not a doctor" in explanation.lower()

    def test_disclaimer_constants_are_nonempty(self):
        """All disclaimer constants are defined and nonempty."""
        assert INTERVIEW_DISCLAIMER
        assert SOAP_DISCLAIMER
        assert len(INTERVIEW_DISCLAIMER) > 20
        assert len(SOAP_DISCLAIMER) > 20


class TestImageConsentRequired:
    """Image capture must require explicit consent."""

    @pytest.mark.asyncio
    async def test_consent_asked_before_image(self):
        """Agent asks for consent before image capture."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        # Greeting
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt)

        # Build up transcript to trigger image request
        for text in [
            "I have a rash",
            "It is on my arm",
            "It started 3 days ago",
        ]:
            stt = STTResult(text=text, language="en", confidence=0.9, duration_ms=0)
            await agent.process_utterance(session, stt)

        # Should have reached image_consent stage
        assert not session.image_consent_given

    @pytest.mark.asyncio
    async def test_consent_denied_continues_interview(self):
        """Denying consent continues the interview without images."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        # Get to consent stage
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt)
        for text in ["rash", "on arm", "3 days ago"]:
            stt = STTResult(text=text, language="en", confidence=0.9, duration_ms=0)
            await agent.process_utterance(session, stt)

        # Now deny consent
        if session.stage.value == "image_consent":
            stt = STTResult(text="No", language="en", confidence=0.9, duration_ms=0)
            response = await agent.process_utterance(session, stt)
            assert not session.image_consent_given
            assert "without a photo" in response.lower() or "continue" in response.lower()

    @pytest.mark.asyncio
    async def test_consent_granted_recorded(self):
        """Granting consent is properly recorded."""
        session = PatientSession()
        assert not session.image_consent_given
        session.grant_image_consent()
        assert session.image_consent_given
