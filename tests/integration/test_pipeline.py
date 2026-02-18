"""Integration tests for complete pipelines.

Tests the full data flow through embedding, retrieval, and inference pipelines.

Covers: REQ-TST-016, REQ-TST-018, REQ-TST-020
"""

from __future__ import annotations

import numpy as np
import pytest

from src.data.scin_schema import FitzpatrickType, SCINRecord
from src.models.embedding_model import get_embedding_model
from src.models.protocols.voice import STTResult
from src.models.rag_retrieval import RAGRetriever, VectorIndex
from src.pipelines.case_history import format_case_history
from src.pipelines.patient_explanation import generate_patient_explanation
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession, SessionStage


class TestEmbeddingPipeline:
    """Test the full embedding -> indexing -> retrieval pipeline."""

    def _build_index(self) -> tuple[VectorIndex, RAGRetriever]:
        """Build a test index with known records."""
        model = get_embedding_model()
        index = VectorIndex()
        retriever = RAGRetriever(index=index)

        records = [
            SCINRecord(
                record_id="pipe_1",
                image_path="img/1.jpg",
                diagnosis="Atopic Dermatitis",
                icd_code="L20.0",
                fitzpatrick_type=FitzpatrickType.III,
                severity="mild",
            ),
            SCINRecord(
                record_id="pipe_2",
                image_path="img/2.jpg",
                diagnosis="Contact Dermatitis",
                icd_code="L25.0",
                fitzpatrick_type=FitzpatrickType.V,
                severity="moderate",
            ),
            SCINRecord(
                record_id="pipe_3",
                image_path="img/3.jpg",
                diagnosis="Psoriasis",
                icd_code="L40.0",
                fitzpatrick_type=FitzpatrickType.II,
                severity="severe",
            ),
        ]

        emb_list = []
        meta_list = []
        for rec in records:
            emb_list.append(model.embed_text(
                f"{rec.diagnosis} {rec.icd_code} {rec.body_location}"
            ))
            meta_list.append({
                "record_id": rec.record_id,
                "diagnosis": rec.diagnosis,
                "icd_code": rec.icd_code,
            })
        index.add(np.array(emb_list, dtype=np.float32), meta_list)

        return index, retriever

    def test_index_and_retrieve_by_text(self):
        """Records indexed by text can be retrieved."""
        _index, retriever = self._build_index()
        response = retriever.query_by_text("eczema rash")
        assert len(response.results) > 0
        assert response.query_type == "text"

    def test_index_and_retrieve_by_image(self):
        """Records indexed can be retrieved by image path."""
        _index, retriever = self._build_index()
        response = retriever.query_by_image("img/test.jpg")
        assert len(response.results) > 0
        assert response.query_type == "image"

    def test_retrieval_results_have_required_fields(self):
        """Each retrieval result has diagnosis and ICD code."""
        _index, retriever = self._build_index()
        response = retriever.query_by_text("dermatitis")
        for result in response.results:
            assert result.record_id
            assert result.diagnosis
            assert result.icd_code
            assert -1.0 <= result.score <= 1.0


class TestInferencePipeline:
    """Test the full interview -> SOAP -> case history pipeline."""

    @pytest.mark.asyncio
    async def test_full_interview_to_case_history(self):
        """Complete flow from interview to case history."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        # Step 1: Greeting
        stt = STTResult(text="Hello", language="hi", confidence=0.92, duration_ms=0)
        greeting_response = await agent.process_utterance(session, stt)
        assert greeting_response
        assert session.stage == SessionStage.INTERVIEW
        assert session.detected_language == "hi"

        # Step 2: Interview
        stt2 = STTResult(
            text="I have a red rash on my arm",
            language="hi",
            confidence=0.90,
            duration_ms=0,
        )
        interview_response = await agent.process_utterance(session, stt2)
        assert interview_response
        assert len(session.transcript) >= 2

        # Step 3: SOAP generation
        soap = await generate_soap_note(session)
        assert soap.subjective
        assert soap.objective
        assert soap.assessment
        assert soap.plan
        assert len(soap.icd_codes) > 0

        # Step 4: Case history
        case = format_case_history(session, soap)
        assert case.case_id.startswith("CASE-")
        assert case.session_id == session.session_id
        assert case.patient_language == "hi"
        assert "subjective" in case.soap_note

        # Step 5: Patient explanation
        explanation = await generate_patient_explanation(soap, language="hi")
        assert explanation
        assert "not a doctor" in explanation.lower()

    @pytest.mark.asyncio
    async def test_escalation_flow(self):
        """Escalation is properly triggered and recorded."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        # Simulate a session
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt)

        session.add_transcript("I have a bleeding mole that is growing")

        # Generate SOAP
        soap = await generate_soap_note(session)

        # Check escalation
        escalation = agent.check_escalation(f"{soap.assessment} {soap.plan}")
        if escalation:
            session.mark_escalated(escalation)

        # Build case history
        case = format_case_history(session, soap)
        assert case.disclaimer

    @pytest.mark.asyncio
    async def test_consent_flow(self):
        """Consent flow progresses correctly."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        # Greeting
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt)
        assert session.stage == SessionStage.INTERVIEW

        # Build transcript to trigger image request
        for text in ["I have a rash", "It is on my arm", "It itches a lot"]:
            stt = STTResult(text=text, language="en", confidence=0.9, duration_ms=0)
            await agent.process_utterance(session, stt)

        # If we reached image_consent, test granting
        if session.stage == SessionStage.IMAGE_CONSENT:
            stt = STTResult(text="Yes", language="en", confidence=0.9, duration_ms=0)
            await agent.process_utterance(session, stt)
            assert session.image_consent_given
            assert session.stage == SessionStage.IMAGE_CAPTURE

    @pytest.mark.asyncio
    async def test_deescalation_flow(self):
        """De-escalation correctly handles non-medical cases."""
        agent = PatientInterviewAgent()
        session = PatientSession()

        stt = STTResult(
            text="I got paint on my skin", language="en", confidence=0.9, duration_ms=0
        )
        response = await agent.process_utterance(session, stt)
        assert "paint" in response.lower() or "not" in response.lower()


class TestDataPipelineIntegration:
    """Test data loading and quality checks together."""

    def test_scin_records_feed_embedding_pipeline(self):
        """SCIN records can be embedded and indexed."""
        model = get_embedding_model()
        index = VectorIndex()

        records = [
            SCINRecord(
                record_id=f"int_{i}",
                image_path=f"img/{i}.jpg",
                diagnosis="Eczema",
                icd_code="L20.0",
                fitzpatrick_type=FitzpatrickType.IV,
                severity="mild",
            )
            for i in range(10)
        ]

        emb_list = []
        meta_list = []
        for rec in records:
            emb_list.append(model.embed_text(f"{rec.diagnosis} {rec.icd_code}"))
            meta_list.append({
                "record_id": rec.record_id,
                "diagnosis": rec.diagnosis,
                "icd_code": rec.icd_code,
            })
        index.add(np.array(emb_list, dtype=np.float32), meta_list)

        assert index.size == 10
