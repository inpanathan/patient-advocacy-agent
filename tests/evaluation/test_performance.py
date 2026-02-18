"""Performance and latency tests.

Validates that key operations complete within acceptable time bounds
and that the system can handle expected load.

Covers: REQ-TST-031 - REQ-TST-035
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from src.models.embedding_model import get_embedding_model, normalize_embeddings
from src.models.protocols.voice import STTResult
from src.models.rag_retrieval import VectorIndex
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession, SessionStore


class TestEmbeddingPerformance:
    """Embedding operations must meet latency requirements."""

    MAX_SINGLE_EMBED_MS = 100  # Max time for single embedding
    MAX_BATCH_EMBED_MS = 500  # Max time for batch of 50

    def test_single_text_embedding_latency(self):
        """Single text embedding completes within threshold."""
        model = get_embedding_model()
        start = time.perf_counter()
        model.embed_text("itchy rash on forearm")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert (
            elapsed_ms < self.MAX_SINGLE_EMBED_MS
        ), f"Single embedding took {elapsed_ms:.1f}ms > {self.MAX_SINGLE_EMBED_MS}ms"

    def test_batch_embedding_latency(self):
        """Batch of 50 text embeddings completes within threshold."""
        model = get_embedding_model()
        items = [{"text": f"test condition {i}"} for i in range(50)]
        start = time.perf_counter()
        model.embed_batch(items)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert (
            elapsed_ms < self.MAX_BATCH_EMBED_MS
        ), f"Batch embedding took {elapsed_ms:.1f}ms > {self.MAX_BATCH_EMBED_MS}ms"

    def test_normalization_performance(self):
        """Normalization of 1000 vectors completes quickly."""
        raw = np.random.randn(1000, 128).astype(np.float32)
        start = time.perf_counter()
        normalize_embeddings(raw)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"Normalization took {elapsed_ms:.1f}ms"


class TestRetrievalPerformance:
    """Vector retrieval must meet latency requirements."""

    MAX_SEARCH_MS = 200  # Max time for a single search

    def test_index_search_latency(self):
        """Search in an index of 1000 vectors completes within threshold."""
        model = get_embedding_model()
        index = VectorIndex()

        # Build index of 1000 items
        emb_list = []
        meta_list = []
        for i in range(1000):
            emb_list.append(model.embed_text(f"condition {i}"))
            meta_list.append(
                {
                    "record_id": f"rec_{i}",
                    "diagnosis": f"diag_{i}",
                    "icd_code": f"L{i % 99:02d}.0",
                }
            )
        index.add(np.array(emb_list, dtype=np.float32), meta_list)

        query = model.embed_text("eczema on arm")
        start = time.perf_counter()
        results = index.search(query, top_k=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert (
            elapsed_ms < self.MAX_SEARCH_MS
        ), f"Search took {elapsed_ms:.1f}ms > {self.MAX_SEARCH_MS}ms"
        assert len(results) == 10


class TestInterviewPerformance:
    """Interview agent must respond within latency threshold."""

    MAX_RESPONSE_MS = 200  # Max time for agent response

    @pytest.mark.asyncio
    async def test_greeting_latency(self):
        """Greeting response completes quickly."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
        start = time.perf_counter()
        await agent.process_utterance(session, stt)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < self.MAX_RESPONSE_MS

    @pytest.mark.asyncio
    async def test_interview_response_latency(self):
        """Interview response completes quickly."""
        agent = PatientInterviewAgent()
        session = PatientSession()
        stt = STTResult(text="Hi", language="en", confidence=0.9, duration_ms=0)
        await agent.process_utterance(session, stt)

        stt2 = STTResult(text="I have a rash", language="en", confidence=0.9, duration_ms=0)
        start = time.perf_counter()
        await agent.process_utterance(session, stt2)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < self.MAX_RESPONSE_MS


class TestSOAPPerformance:
    """SOAP generation must meet latency threshold."""

    MAX_SOAP_MS = 300  # Max time for SOAP generation

    @pytest.mark.asyncio
    async def test_soap_generation_latency(self):
        """SOAP generation completes within threshold."""
        session = PatientSession()
        session.add_transcript("Red itchy rash on forearm for 3 days")
        start = time.perf_counter()
        await generate_soap_note(session)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < self.MAX_SOAP_MS


class TestSessionScalability:
    """Session management must handle expected concurrent load."""

    def test_create_100_concurrent_sessions(self):
        """SessionStore handles 100 concurrent sessions."""
        store = SessionStore()
        sessions = []
        for _ in range(100):
            session = store.create()
            sessions.append(session)

        assert len(sessions) == 100
        # All should be retrievable
        for session in sessions:
            retrieved = store.get(session.session_id)
            assert retrieved is not None

    def test_session_creation_throughput(self):
        """Session creation throughput is adequate."""
        store = SessionStore()
        start = time.perf_counter()
        for _ in range(1000):
            store.create()
        elapsed_ms = (time.perf_counter() - start) * 1000
        # 1000 sessions should take < 1 second
        assert elapsed_ms < 1000, f"1000 session creations took {elapsed_ms:.1f}ms"
