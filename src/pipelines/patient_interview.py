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

DISCLAIMER = (
    "I am not a doctor. This is not a medical diagnosis. "
    "Please seek professional medical help for proper evaluation and treatment."
)

INTERVIEW_SYSTEM_BASE = """\
You are a friendly health assistant helping a patient describe a skin problem. \
You are NOT a doctor. You are collecting information so a real doctor can help later.

Rules:
- Ask exactly ONE short question per turn (1 sentence, max 15 words).
- Use very simple language (the patient may be illiterate).
- Never diagnose, prescribe, or give medical advice.
- Never say "or" to offer multiple choices. Just pick the most important question.
- Do NOT repeat or re-ask anything listed under "What the patient has told you so far".
"""

TOPIC_QUESTIONS: dict[str, str] = {
    "chief_complaint": "What is the problem?",
    "location": "Where on your body is it?",
    "duration": "How long have you had it?",
    "progression": "Is it getting worse, better, or staying the same?",
    "symptoms": "Does it itch, hurt, or burn?",
}

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "chief_complaint": [
        "rash",
        "bump",
        "spot",
        "sore",
        "wound",
        "blister",
        "swelling",
        "patch",
        "pimple",
        "boil",
        "lump",
        "lesion",
        "mark",
        "skin",
        "eczema",
        "infection",
        "irritation",
        "redness",
        "discoloration",
        "scab",
        "wart",
        "ulcer",
        "bite",
        "sting",
        "hives",
        "acne",
        "ringworm",
        "fungus",
        "peeling",
        "flaking",
        "dry",
        "crack",
    ],
    "location": [
        "arm",
        "leg",
        "face",
        "back",
        "chest",
        "hand",
        "foot",
        "feet",
        "neck",
        "head",
        "scalp",
        "shoulder",
        "stomach",
        "belly",
        "knee",
        "elbow",
        "finger",
        "toe",
        "thigh",
        "shin",
        "wrist",
        "ankle",
        "forehead",
        "cheek",
        "nose",
        "ear",
        "lip",
        "palm",
        "hip",
        "groin",
        "buttock",
        "armpit",
        "body",
        "skin",
    ],
    "duration": [
        "day",
        "days",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "yesterday",
        "today",
        "last week",
        "last month",
        "long time",
        "few days",
        "couple days",
        "since",
        "ago",
        "recently",
        "just started",
        "morning",
        "night",
        "hours",
    ],
    "progression": [
        "worse",
        "better",
        "same",
        "spreading",
        "growing",
        "shrinking",
        "bigger",
        "smaller",
        "more",
        "less",
        "changing",
        "not changing",
        "stays",
        "increased",
        "decreased",
        "getting",
    ],
    "symptoms": [
        "itch",
        "itchy",
        "itching",
        "hurt",
        "hurts",
        "pain",
        "painful",
        "burn",
        "burns",
        "burning",
        "sting",
        "stinging",
        "bleed",
        "bleeding",
        "ooze",
        "oozing",
        "swell",
        "swollen",
        "tender",
        "sore",
        "numb",
        "tingle",
        "tingling",
        "hot",
        "warm",
        "throb",
        "throbbing",
    ],
}


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
        """Process a patient utterance and return the agent's response."""
        session.add_transcript(stt_result.text)
        session.conversation.append({"role": "patient", "text": stt_result.text})

        # Check for de-escalation keywords
        if self._should_deescalate(stt_result.text):
            logger.info(
                "de_escalation_detected",
                session_id=session.session_id,
                text_snippet=stt_result.text[:50],
            )
            response = self._deescalation_response()
            session.conversation.append({"role": "assistant", "text": response})
            return response

        # Generate response based on stage
        if session.stage == SessionStage.GREETING:
            response = await self._handle_greeting(session, stt_result)
        elif session.stage == SessionStage.IMAGE_CONSENT:
            response = await self._handle_consent(session, stt_result)
        else:
            response = await self._handle_interview(session, stt_result)

        session.conversation.append({"role": "assistant", "text": response})
        return response

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
        """Handle the interview phase — ask one question at a time."""
        # Extract topics from the latest patient utterance and merge
        new_topics = self._extract_topics(stt_result.text)
        for topic, matched in new_topics.items():
            if topic not in session.answered_topics:
                session.answered_topics[topic] = matched

        logger.info(
            "topics_tracked",
            session_id=session.session_id,
            answered=list(session.answered_topics.keys()),
            new=list(new_topics.keys()),
        )

        # If all topics covered, go straight to image consent
        unanswered = [t for t in TOPIC_QUESTIONS if t not in session.answered_topics]
        if not unanswered and self._should_request_image("enough information", session):
            session.advance_to(SessionStage.IMAGE_CONSENT)
            return (
                "Thank you for telling me about your condition. "
                "I would like to take a photo of the affected area to help the doctor. "
                "Is that okay with you?"
            )

        # Build dynamic prompt with answered/unanswered sections
        prompt = self._build_dynamic_prompt(session, unanswered)

        response = await self._model.generate(
            prompt=prompt,
            temperature=0.2,
        )

        # Clean up — take only the first sentence/question
        text = response.text.strip()
        # Remove any "Assistant:" prefix the model might echo
        if text.lower().startswith("assistant:"):
            text = text[len("assistant:") :].strip()
        # Take first sentence only
        for end_char in ["?", ".", "!"]:
            idx = text.find(end_char)
            if idx != -1:
                text = text[: idx + 1]
                break

        # Check if we have enough info to suggest photo
        if self._should_request_image(text, session):
            session.advance_to(SessionStage.IMAGE_CONSENT)
            return (
                "Thank you for telling me about your condition. "
                "I would like to take a photo of the affected area to help the doctor. "
                "Is that okay with you?"
            )

        logger.info(
            "interview_question",
            session_id=session.session_id,
            turn=len(session.conversation),
            question=text[:80],
            answered_topics=list(session.answered_topics.keys()),
            remaining_topics=unanswered,
        )

        return text

    def _extract_topics(self, text: str) -> dict[str, str]:
        """Extract interview topics from patient text using keyword matching.

        Returns dict of topic name to matched phrase snippet.
        Simple keyword matching is intentional — patients are illiterate
        and use basic terms.
        """
        text_lower = text.lower()
        detected: dict[str, str] = {}

        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    # Capture a snippet around the keyword for context
                    idx = text_lower.index(kw)
                    start = max(0, idx - 10)
                    end = min(len(text), idx + len(kw) + 10)
                    detected[topic] = text[start:end].strip()
                    break

        return detected

    def _build_dynamic_prompt(
        self,
        session: PatientSession,
        unanswered: list[str],
    ) -> str:
        """Build interview prompt with explicit answered/unanswered sections."""
        lines = [INTERVIEW_SYSTEM_BASE]

        # Show what's already been answered
        if session.answered_topics:
            lines.append("\nWhat the patient has told you so far:")
            for topic, snippet in session.answered_topics.items():
                label = TOPIC_QUESTIONS.get(topic, topic)
                lines.append(f'- {label} → Patient said: "{snippet}"')

        # Show what still needs to be asked
        if unanswered:
            lines.append("\nYou still need to ask about:")
            for topic in unanswered:
                lines.append(f"- {TOPIC_QUESTIONS[topic]}")
            lines.append("\nAsk the FIRST unanswered question from the list above.")
        else:
            lines.append(
                "\nAll topics are covered. Respond with: "
                '"Thank you. I have enough information. Let us take a photo now."'
            )

        # Append conversation history
        lines.append("\nConversation so far:")
        for turn in session.conversation:
            role = "Patient" if turn["role"] == "patient" else "Assistant"
            lines.append(f"{role}: {turn['text']}")
        lines.append("\nAssistant:")

        return "\n".join(lines)

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
            return "Thank you. Please take a photo of the affected area now."
        else:
            session.advance_to(SessionStage.INTERVIEW)
            return "That is okay. Can you describe what the affected area looks like?"

    def _should_request_image(
        self,
        response_text: str,
        session: PatientSession,
    ) -> bool:
        """Determine if we should request image consent."""
        if session.image_consent_given:
            return False
        # Model explicitly says it has enough info
        if "enough information" in response_text.lower() or "take a photo" in response_text.lower():
            return True
        # Most interview topics covered — move to image
        if len(session.answered_topics) >= 4:
            return True
        # After 5+ patient utterances, suggest photo
        patient_turns = sum(1 for t in session.conversation if t["role"] == "patient")
        return patient_turns >= 5

    def _should_deescalate(self, text: str) -> bool:
        """Check if the patient's description suggests a non-medical case."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in DE_ESCALATION_KEYWORDS)

    def _deescalation_response(self) -> str:
        """Return a de-escalation response."""
        return (
            "It sounds like what you are describing may not be a skin condition. "
            "Things like paint, tattoos, or henna are not medical issues. "
            "If you have a different concern, I am happy to help."
        )

    def check_escalation(self, soap_text: str) -> str | None:
        """Check if a SOAP note warrants immediate escalation."""
        text_lower = soap_text.lower()
        for keyword in ESCALATION_KEYWORDS:
            if keyword in text_lower:
                return f"Suspected malignancy: '{keyword}' detected in assessment"
        return None
