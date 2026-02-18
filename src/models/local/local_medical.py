"""Local MedGemma 4B medical model implementation.

Loads MedGemma 4B instruction-tuned model via Hugging Face transformers
for on-device SOAP note generation and clinical reasoning.

VRAM budget: ~8GB at fp16 on RTX 3090.
"""

from __future__ import annotations

import re
import time

import structlog
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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


def _resolve_device(device: str) -> str:
    """Resolve 'auto' to the best available device."""
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


class LocalMedicalModel:
    """MedGemma 4B instruction-tuned model for local inference."""

    def __init__(self) -> None:
        model_id = settings.llm.medgemma_model_id
        device = _resolve_device(settings.llm.device)

        logger.info("loading_local_medical_model", model_id=model_id, device=device)
        t0 = time.monotonic()

        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map=device,
        )
        self._model.eval()
        self._device = device
        self._model_id = model_id

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("local_medical_model_loaded", model_id=model_id, load_ms=elapsed)

    async def generate(
        self, prompt: str, *, temperature: float = 0.3
    ) -> MedicalModelResponse:
        """Generate a response from MedGemma."""
        t0 = time.monotonic()

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        prompt_tokens = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=settings.llm.max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.9,
            )

        new_tokens = outputs[0][prompt_tokens:]
        text = str(self._tokenizer.decode(new_tokens, skip_special_tokens=True))
        completion_tokens = len(new_tokens)
        elapsed = int((time.monotonic() - t0) * 1000)

        logger.info(
            "local_medical_generate",
            model_id=self._model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed,
        )

        return MedicalModelResponse(
            text=text,
            model_id=self._model_id,
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
        """Generate a SOAP note from patient interview data."""
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

    # Extract ICD codes from the icd_codes section or full text
    icd_source = sections.get("icd_codes", text)
    icd_codes = ICD_PATTERN.findall(icd_source)

    # Extract confidence score
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
