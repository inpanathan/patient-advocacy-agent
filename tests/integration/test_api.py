"""Integration tests for the API endpoints.

Tests the full request/response cycle through the FastAPI application.

Covers: REQ-TST-020, REQ-TST-019
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "env" in data
        assert "version" in data


class TestSessionAPI:
    """Test session management endpoints."""

    def test_create_session(self, client):
        """Create a new session."""
        response = client.post("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["stage"] == "greeting"

    def test_get_session(self, client):
        """Get session details."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_get_nonexistent_session(self, client):
        """Getting nonexistent session returns 404."""
        response = client.get("/api/v1/sessions/nonexistent")
        assert response.status_code == 404

    def test_delete_session(self, client):
        """Delete a session."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.delete(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_resp = client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 404


class TestInteractionAPI:
    """Test patient interaction endpoints."""

    def test_interact_greeting(self, client):
        """First interaction triggers greeting response."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.post(
            f"/api/v1/sessions/{session_id}/interact",
            json={"text": "Hello", "language": "hi"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"]
        assert data["stage"] == "interview"

    def test_interact_nonexistent_session(self, client):
        """Interacting with nonexistent session returns 404."""
        response = client.post(
            "/api/v1/sessions/nonexistent/interact",
            json={"text": "Hello"},
        )
        assert response.status_code == 404

    def test_consent_endpoint(self, client):
        """Consent can be granted via API."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.post(
            f"/api/v1/sessions/{session_id}/consent",
            json={"consent": True},
        )
        assert response.status_code == 200
        assert response.json()["consent"] is True


class TestMedicalAPI:
    """Test medical endpoints (SOAP, case history)."""

    def _create_session_with_transcript(self, client):
        """Helper to create a session with some interaction."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        # Add some interaction to build transcript
        client.post(
            f"/api/v1/sessions/{session_id}/interact",
            json={"text": "I have a rash on my arm", "language": "en"},
        )
        return session_id

    def test_generate_soap(self, client):
        """SOAP note is generated from session data."""
        session_id = self._create_session_with_transcript(client)

        response = client.post(f"/api/v1/sessions/{session_id}/soap")
        assert response.status_code == 200
        data = response.json()
        assert data["subjective"]
        assert data["objective"]
        assert data["assessment"]
        assert data["plan"]
        assert len(data["icd_codes"]) > 0
        assert "not a medical diagnosis" in data["disclaimer"]

    def test_soap_without_transcript_fails(self, client):
        """SOAP generation requires transcript data."""
        create_resp = client.post("/api/v1/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.post(f"/api/v1/sessions/{session_id}/soap")
        assert response.status_code == 400

    def test_get_case_history(self, client):
        """Case history is formatted correctly."""
        session_id = self._create_session_with_transcript(client)

        response = client.get(f"/api/v1/sessions/{session_id}/case-history")
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"].startswith("CASE-")
        assert data["session_id"] == session_id
        assert "subjective" in data["soap_note"]
        assert data["disclaimer"]
