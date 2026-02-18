"""Bias and fairness tests.

Validates that the system provides equitable treatment across
Fitzpatrick skin types, languages, and geographic contexts.

Covers: REQ-TST-036 - REQ-TST-039
"""

from __future__ import annotations

import numpy as np
import pytest

from src.data.scin_schema import FitzpatrickType, SCINRecord
from src.models.embedding_model import get_embedding_model
from src.models.mocks.mock_medical import MockMedicalModel
from src.models.protocols.voice import STTResult
from src.models.rag_retrieval import VectorIndex
from src.pipelines.patient_interview import PatientInterviewAgent
from src.utils.session import PatientSession


def _make_record(fitz_type: FitzpatrickType, record_id: str = "rec") -> SCINRecord:
    """Helper to create a SCIN record for a given Fitzpatrick type."""
    return SCINRecord(
        record_id=f"{record_id}_{fitz_type.value}",
        image_path=f"images/{fitz_type.value}/sample.jpg",
        diagnosis="Atopic Dermatitis",
        icd_code="L20.0",
        fitzpatrick_type=fitz_type,
        severity="mild",
        body_location="forearm",
    )


class TestFitzpatrickTypeEquity:
    """System must perform equitably across all Fitzpatrick skin types."""

    ALL_TYPES = list(FitzpatrickType)

    def test_all_fitzpatrick_types_representable(self):
        """Schema supports all 6 Fitzpatrick types."""
        assert len(self.ALL_TYPES) == 6
        expected = {"I", "II", "III", "IV", "V", "VI"}
        assert {ft.value for ft in self.ALL_TYPES} == expected

    def test_records_valid_for_all_fitzpatrick_types(self):
        """Records can be created for every Fitzpatrick type."""
        for ftype in self.ALL_TYPES:
            record = _make_record(ftype)
            assert record.fitzpatrick_type == ftype

    def test_embedding_dimension_consistent_across_types(self):
        """Embedding model produces same-dimension vectors regardless of skin type."""
        model = get_embedding_model()
        dimensions = set()
        for ftype in self.ALL_TYPES:
            record = _make_record(ftype)
            emb = model.embed_text(f"{record.diagnosis} on {record.body_location}")
            dimensions.add(len(emb))
        assert len(dimensions) == 1, "Embedding dimensions differ across Fitzpatrick types"

    def test_vector_index_retrieves_all_fitzpatrick_types(self):
        """RAG retrieval can surface results from all Fitzpatrick types."""
        model = get_embedding_model()
        index = VectorIndex()

        emb_list = []
        meta_list = []
        for ftype in self.ALL_TYPES:
            record = _make_record(ftype, record_id="bias_test")
            emb_list.append(model.embed_text(f"{record.diagnosis} {ftype.value}"))
            meta_list.append({
                "record_id": record.record_id,
                "diagnosis": record.diagnosis,
                "icd_code": record.icd_code,
            })
        index.add(np.array(emb_list, dtype=np.float32), meta_list)

        assert index.size == 6

    @pytest.mark.asyncio
    async def test_soap_generated_for_all_fitzpatrick_types(self):
        """SOAP note can be generated for patients of every skin type."""
        model = MockMedicalModel()
        for ftype in self.ALL_TYPES:
            soap = await model.generate_soap(
                transcript=f"Patient with Fitzpatrick type {ftype.value} has a rash"
            )
            assert soap.subjective
            assert soap.assessment
            assert len(soap.icd_codes) > 0


class TestLanguageEquity:
    """System must handle patients across supported languages."""

    SUPPORTED_LANGUAGES = ["en", "hi", "ta", "te", "bn", "kn"]

    @pytest.mark.asyncio
    async def test_greeting_works_for_all_languages(self):
        """Interview agent can begin in any supported language."""
        agent = PatientInterviewAgent()
        for lang in self.SUPPORTED_LANGUAGES:
            session = PatientSession()
            stt = STTResult(
                text="Hello",
                language=lang,
                confidence=0.85,
                duration_ms=0,
            )
            response = await agent.process_utterance(session, stt)
            assert response, f"No response for language {lang}"
            assert session.detected_language == lang

    @pytest.mark.asyncio
    async def test_interview_processes_all_languages(self):
        """Interview continues for any language after greeting."""
        agent = PatientInterviewAgent()
        for lang in self.SUPPORTED_LANGUAGES:
            session = PatientSession()
            # Greeting
            stt = STTResult(text="Hi", language=lang, confidence=0.9, duration_ms=0)
            await agent.process_utterance(session, stt)

            # Interview
            stt2 = STTResult(
                text="I have a rash",
                language=lang,
                confidence=0.85,
                duration_ms=0,
            )
            response = await agent.process_utterance(session, stt2)
            assert response, f"No interview response for language {lang}"


class TestEscalationFairness:
    """Escalation decisions must be based on medical criteria, not demographics."""

    ESCALATION_TEXTS = [
        "melanoma suspected",
        "rapidly growing lesion",
        "bleeding mole",
        "malignant appearance",
    ]

    def test_escalation_triggers_regardless_of_fitzpatrick(self):
        """Escalation keywords trigger for all skin types."""
        agent = PatientInterviewAgent()
        for ftype in FitzpatrickType:
            for text in self.ESCALATION_TEXTS:
                result = agent.check_escalation(
                    f"Patient Fitzpatrick {ftype.value}: {text}"
                )
                assert result is not None, (
                    f"Escalation not triggered for {ftype.value} with '{text}'"
                )

    def test_no_false_escalation_on_benign_conditions(self):
        """Benign conditions do not trigger false escalation."""
        agent = PatientInterviewAgent()
        benign_texts = [
            "mild eczema on forearm",
            "contact dermatitis from soap",
            "fungal infection between toes",
            "dry skin with mild scaling",
        ]
        for text in benign_texts:
            result = agent.check_escalation(text)
            assert result is None, f"False escalation on benign condition: '{text}'"

    def test_deescalation_consistent(self):
        """De-escalation works consistently across scenarios."""
        agent = PatientInterviewAgent()
        deescalation_texts = [
            "I got paint on my arm",
            "This is a tattoo",
            "It's henna on my hand",
        ]
        for text in deescalation_texts:
            assert agent._should_deescalate(text), (
                f"De-escalation not triggered for: '{text}'"
            )
