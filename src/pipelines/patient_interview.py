"""Patient interview agent.

Orchestrates the conversational interview loop: greeting, language detection,
symptom extraction, consent-gated image capture, and case completion.

Covers: Phase 5 tasks
"""

from __future__ import annotations

import structlog

from src.models.medical_model import get_medical_model
from src.models.protocols.voice import STTResult
from src.utils.session import PatientSession, SessionStage

logger = structlog.get_logger(__name__)

DISCLAIMER = (
    "I am an AI assistant, not a doctor. My assessment is for informational purposes only. "
    "Please seek professional medical help for proper evaluation and treatment."
)

ESCALATION_KEYWORDS = [
    "melanoma",
    "malignant",
    "cancer",
    "tumor",
    "rapidly growing",
    "bleeding mole",
    "asymmetric lesion",
    "irregular border",
]

DE_ESCALATION_KEYWORDS = [
    "paint",
    "tattoo",
    "ink",
    "marker",
    "sticker",
    "henna",
    "dye",
]


class PatientInterviewAgent:
    """Conversational agent for patient interviews.

    Manages the interview flow, extracts symptoms, handles consent,
    and determines when to escalate or de-escalate.
    """

    def __init__(self) -> None:
        self._model = get_medical_model()

    async def process_utterance(
        self,
        session: PatientSession,
        stt_result: STTResult,
    ) -> str:
        """Process a patient utterance and return the agent's response.

        Args:
            session: Current patient session.
            stt_result: Transcribed speech from the patient.

        Returns:
            Agent response text (to be synthesized via TTS).
        """
        session.add_transcript(stt_result.text)

        # Check for de-escalation keywords
        if self._should_deescalate(stt_result.text):
            logger.info(
                "de_escalation_detected",
                session_id=session.session_id,
                text_snippet=stt_result.text[:50],
            )
            return self._deescalation_response()

        # Generate response based on stage
        if session.stage == SessionStage.GREETING:
            return await self._handle_greeting(session, stt_result)
        elif session.stage == SessionStage.INTERVIEW:
            return await self._handle_interview(session, stt_result)
        elif session.stage == SessionStage.IMAGE_CONSENT:
            return await self._handle_consent(session, stt_result)
        else:
            return await self._handle_interview(session, stt_result)

    async def _handle_greeting(
        self,
        session: PatientSession,
        stt_result: STTResult,
    ) -> str:
        """Handle the greeting phase."""
        session.detected_language = stt_result.language
        session.language_confidence = stt_result.confidence
        session.advance_to(SessionStage.INTERVIEW)

        logger.info(
            "greeting_complete",
            session_id=session.session_id,
            language=stt_result.language,
            confidence=stt_result.confidence,
        )

        return (
            "Hello, I am a health assistant. I am not a doctor. "
            "I will ask you some questions to help a doctor understand your condition. "
            "Can you tell me what is bothering you?"
        )

    async def _handle_interview(
        self,
        session: PatientSession,
        stt_result: STTResult,
    ) -> str:
        """Handle the interview phase — extract symptoms."""
        response = await self._model.generate(
            prompt=(
                f"Patient says: '{stt_result.text}'\n\n"
                "You are a medical triage assistant (NOT a doctor). "
                "Ask a follow-up question to better understand the skin condition. "
                "Keep your response simple and clear for an illiterate patient. "
                "If you have enough information, say 'I would like to take a photo "
                "of the affected area to help the doctor.'"
            ),
        )

        # Check if we should request image consent
        if self._should_request_image(response.text, session):
            session.advance_to(SessionStage.IMAGE_CONSENT)
            return (
                "Thank you for telling me about your condition. "
                "I would like to take a photo of the affected area to help the doctor. "
                "Is that okay with you? Please say yes or no."
            )

        return response.text + f"\n\n{DISCLAIMER}"

    async def _handle_consent(
        self,
        session: PatientSession,
        stt_result: STTResult,
    ) -> str:
        """Handle image consent response."""
        text_lower = stt_result.text.lower()
        if any(word in text_lower for word in ["yes", "ok", "okay", "sure", "fine"]):
            session.grant_image_consent()
            session.advance_to(SessionStage.IMAGE_CAPTURE)
            return "Thank you. I will now take a photo. Please hold still."
        else:
            session.advance_to(SessionStage.INTERVIEW)
            return (
                "That is okay. We will continue without a photo. "
                "Can you describe what the affected area looks like?"
            )

    def _should_request_image(
        self,
        response_text: str,
        session: PatientSession,
    ) -> bool:
        """Determine if we should request image consent."""
        if session.image_consent_given:
            return False
        # After 3+ transcript entries, suggest image
        return len(session.transcript) >= 3

    def _should_deescalate(self, text: str) -> bool:
        """Check if the patient's description suggests a non-medical case."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in DE_ESCALATION_KEYWORDS)

    def _deescalation_response(self) -> str:
        """Return a de-escalation response."""
        return (
            "It sounds like what you are describing may not be a skin condition. "
            "Things like paint, tattoos, or henna are not medical issues. "
            "If you have a different concern, I am happy to help. "
            "Otherwise, there is nothing to worry about."
        )

    def check_escalation(self, soap_text: str) -> str | None:
        """Check if a SOAP note warrants immediate escalation.

        Args:
            soap_text: Combined SOAP note text.

        Returns:
            Escalation reason if needed, None otherwise.
        """
        text_lower = soap_text.lower()
        for keyword in ESCALATION_KEYWORDS:
            if keyword in text_lower:
                return f"Suspected malignancy: '{keyword}' detected in assessment"
        return None
