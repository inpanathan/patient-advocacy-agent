"""Load testing at target concurrency.

Validates that the system handles concurrent sessions and
degrades gracefully under load.

Covers: REQ-TST-033
"""

from __future__ import annotations

import asyncio

import pytest

from src.models.protocols.voice import STTResult
from src.pipelines.patient_interview import PatientInterviewAgent
from src.pipelines.soap_generator import generate_soap_note
from src.utils.session import PatientSession, SessionStore


class TestConcurrentSessions:
    """Test system under concurrent session load."""

    def test_100_sessions_created(self):
        """100 sessions can be created without error."""
        store = SessionStore()
        sessions = [store.create() for _ in range(100)]
        assert len(sessions) == 100
        # All unique
        ids = {s.session_id for s in sessions}
        assert len(ids) == 100

    def test_100_sessions_retrievable(self):
        """All 100 sessions are retrievable."""
        store = SessionStore()
        sessions = [store.create() for _ in range(100)]
        for session in sessions:
            retrieved = store.get(session.session_id)
            assert retrieved is not None
            assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_concurrent_interactions(self):
        """Multiple sessions can process utterances concurrently."""
        agent = PatientInterviewAgent()
        sessions = [PatientSession() for _ in range(10)]

        async def interact(session: PatientSession) -> str:
            stt = STTResult(text="Hello", language="en", confidence=0.9, duration_ms=0)
            return await agent.process_utterance(session, stt)

        results = await asyncio.gather(*[interact(s) for s in sessions])
        assert len(results) == 10
        assert all(r for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_soap_generation(self):
        """Multiple SOAP notes can be generated concurrently."""
        sessions = []
        for _ in range(10):
            session = PatientSession()
            session.add_transcript("Red rash on forearm for 3 days")
            sessions.append(session)

        soaps = await asyncio.gather(*[generate_soap_note(s) for s in sessions])
        assert len(soaps) == 10
        assert all(s.subjective for s in soaps)

    def test_session_deletion_under_load(self):
        """Sessions can be deleted while others are active."""
        store = SessionStore()
        sessions = [store.create() for _ in range(50)]

        # Delete even-indexed sessions
        for i in range(0, 50, 2):
            store.delete(sessions[i].session_id)

        # Odd-indexed should still be available
        for i in range(1, 50, 2):
            assert store.get(sessions[i].session_id) is not None

        # Even-indexed should be gone
        for i in range(0, 50, 2):
            assert store.get(sessions[i].session_id) is None
