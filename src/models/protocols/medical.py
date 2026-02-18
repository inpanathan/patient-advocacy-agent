"""Protocol definitions for medical AI model.

Defines the interface for the medical LLM (MedGemma) used for
SOAP note generation, ICD coding, and patient interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class SOAPNote:
    """SOAP-formatted medical case note."""

    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    icd_codes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    disclaimer: str = (
        "This is an AI-assisted triage assessment, not a medical diagnosis. "
        "Please seek professional medical help for proper evaluation and treatment."
    )


@dataclass
class MedicalModelResponse:
    """Response from the medical AI model."""

    text: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


@runtime_checkable
class MedicalModelProtocol(Protocol):
    """Interface for medical AI models (MedGemma)."""

    async def generate(self, prompt: str, *, temperature: float = 0.3) -> MedicalModelResponse:
        """Generate a response from the medical model."""
        ...

    async def generate_soap(
        self,
        transcript: str,
        image_context: str = "",
        rag_context: str = "",
    ) -> SOAPNote:
        """Generate a SOAP note from patient interview data."""
        ...
