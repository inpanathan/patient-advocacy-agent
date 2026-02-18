"""Integration tests for dashboard API endpoints and HTML pages."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src.observability.alerts import AlertEvaluator
from src.observability.audit import AuditTrail
from src.observability.dashboard_aggregator import DashboardAggregator, DashboardState
from src.observability.safety_evaluator import SafetyEvaluator
from src.utils.session import SessionStore


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with dashboard wired up."""
    from main import create_app

    app = create_app()

    # Wire dashboard aggregator manually (normally done in lifespan)
    state = DashboardState(
        start_time=time.monotonic(),
        session_store=SessionStore(),
        alert_evaluator=AlertEvaluator(),
        audit_trail=AuditTrail(),
        safety_evaluator=SafetyEvaluator(),
    )
    app.state.dashboard_aggregator = DashboardAggregator(state)

    return TestClient(app)


class TestDashboardAPIEndpoints:
    """Test all 10 JSON API endpoints."""

    def test_health_overview(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/health-overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "uptime_seconds" in data
        assert "active_sessions" in data

    def test_performance(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "prediction_latency" in data
        assert "confidence_values" in data
        assert "icd_code_counts" in data

    def test_vector_space(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/vector-space?max_points=100")
        assert resp.status_code == 200
        data = resp.json()
        assert "points" in data
        assert "total_embeddings" in data

    def test_safety(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/safety")
        assert resp.status_code == 200
        data = resp.json()
        assert "pass_rate" in data
        assert "escalation_rate" in data

    def test_bias(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/bias")
        assert resp.status_code == 200
        data = resp.json()
        assert "by_fitzpatrick" in data
        assert "by_language" in data

    def test_alerts(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/alerts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_audit_trail(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/audit-trail?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_logs(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/logs?level=INFO&limit=50")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_logs_filter_by_level(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/logs?level=ERROR")
        assert resp.status_code == 200
        data = resp.json()
        for record in data:
            assert record["level"] == "ERROR"

    def test_time_series(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/time-series?metric=prediction_latency_ms&bucket=60")
        assert resp.status_code == 200
        data = resp.json()
        assert "metric" in data
        assert "buckets" in data
        assert "bucket_seconds" in data

    def test_request_stats(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/request-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "total_errors" in data
        assert "endpoints" in data


class TestDashboardHTMLPages:
    """Test that HTML pages render with navigation."""

    def test_overview_page(self, client: TestClient) -> None:
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Overview" in resp.text
        assert "nav-bar" in resp.text
        assert "Patient Advocacy Agent" in resp.text

    def test_logs_page(self, client: TestClient) -> None:
        resp = client.get("/dashboard/logs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Log Viewer" in resp.text
        assert "nav-bar" in resp.text

    def test_metrics_page(self, client: TestClient) -> None:
        resp = client.get("/dashboard/metrics")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Metrics Explorer" in resp.text
        assert "nav-bar" in resp.text

    def test_pages_have_nav_links(self, client: TestClient) -> None:
        """All pages should link to each other via navigation."""
        for url in ["/dashboard", "/dashboard/logs", "/dashboard/metrics"]:
            resp = client.get(url)
            assert "/dashboard" in resp.text
            assert "/dashboard/logs" in resp.text
            assert "/dashboard/metrics" in resp.text
