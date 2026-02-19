"""Cloud medical model implementation using Google Gemini API.

Uses the google-genai SDK to call Gemini 2.0 Flash for
SOAP note generation and clinical reasoning.
"""

from __future__ import annotations

import re
import time

import structlog
from google import genai
from google.genai import types

from src.models.protocols.medical import MedicalModelResponse, SOAPNote
from src.utils.config import settings

logger = structlog.get_logger(__name__)

SOAP_SYSTEM_PROMPT = """\
You are a dermatological triage assistant. You are NOT a doctor. \
Your role is to produce a structured SOAP note for a remote physician \
based on a patient interview transcript and any available image or \
retrieval-augmented context.

Always include a disclaimer that this is an AI-assisted triage assessment \
and the patient should seek professional medical help.

Output format — use these exact section headers:
## Subjective
## Objective
## Assessment
## Plan
## ICD Codes
## Confidence
"""

ICD_PATTERN = re.compile(r"[A-Z]\d{2}(?:\.\d{1,2})?")


class CloudMedicalModel:
    """Google Gemini API-based medical model."""

    def __init__(self) -> None:
        api_key = settings.llm.google_api_key
        if not api_key:
            msg = (
                "LLM__GOOGLE_API_KEY must be set for cloud model backend. "
                "Set it in .env or environment variables."
            )
            raise ValueError(msg)

        self._client = genai.Client(api_key=api_key)
        self._model_name = "gemini-2.0-flash"
        logger.info("cloud_medical_model_initialized", model=self._model_name)

    async def generate(
        self, prompt: str, *, temperature: float = 0.3, max_tokens: int = 0
    ) -> MedicalModelResponse:
        """Generate a response using Gemini API."""
        t0 = time.monotonic()
        token_limit = max_tokens if max_tokens > 0 else settings.llm.max_tokens

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=token_limit,
            ),
        )

        text = response.text or ""
        elapsed = int((time.monotonic() - t0) * 1000)

        # Token counts from usage metadata
        prompt_tokens = 0
        completion_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        logger.info(
            "cloud_medical_generate",
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed,
        )

        return MedicalModelResponse(
            text=text,
            model_id=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed,
        )

    async def generate_soap(
        self,
        transcript: str,
        image_context: str = "",
        rag_context: str = "",
    ) -> SOAPNote:
        """Generate a SOAP note using Gemini API."""
        parts = [SOAP_SYSTEM_PROMPT, f"\n## Patient Transcript\n{transcript}"]
        if image_context:
            parts.append(f"\n## Image Analysis\n{image_context}")
        if rag_context:
            parts.append(f"\n## Similar Cases (RAG)\n{rag_context}")

        prompt = "\n".join(parts)
        response = await self.generate(prompt, temperature=settings.llm.temperature)
        return _parse_soap(response.text)


def _parse_soap(text: str) -> SOAPNote:
    """Parse SOAP sections from model output using section headers."""
    sections: dict[str, str] = {}
    current_section = ""
    lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip().lower()
        if stripped.startswith("## subjective"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "subjective"
            lines = []
        elif stripped.startswith("## objective"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "objective"
            lines = []
        elif stripped.startswith("## assessment"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "assessment"
            lines = []
        elif stripped.startswith("## plan"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "plan"
            lines = []
        elif stripped.startswith("## icd"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "icd_codes"
            lines = []
        elif stripped.startswith("## confidence"):
            if current_section:
                sections[current_section] = "\n".join(lines).strip()
            current_section = "confidence"
            lines = []
        else:
            lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(lines).strip()

    icd_source = sections.get("icd_codes", text)
    icd_codes = ICD_PATTERN.findall(icd_source)

    confidence = 0.0
    conf_text = sections.get("confidence", "")
    conf_match = re.search(r"(\d+(?:\.\d+)?)", conf_text)
    if conf_match:
        val = float(conf_match.group(1))
        confidence = val if val <= 1.0 else val / 100.0

    return SOAPNote(
        subjective=sections.get("subjective", text),
        objective=sections.get("objective", ""),
        assessment=sections.get("assessment", ""),
        plan=sections.get("plan", ""),
        icd_codes=icd_codes,
        confidence=confidence,
    )
