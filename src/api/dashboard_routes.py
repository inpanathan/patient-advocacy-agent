"""JSON API endpoints for the monitoring dashboard.

All endpoints are under /api/v1/dashboard/ and return JSON data
consumed by the dashboard HTML pages.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from src.observability.dashboard_aggregator import DashboardAggregator

router = APIRouter(tags=["dashboard"])


def _aggregator(request: Request) -> DashboardAggregator:
    """Get the dashboard aggregator from app state."""
    return request.app.state.dashboard_aggregator  # type: ignore[no-any-return]


@router.get("/health-overview")
async def health_overview(request: Request) -> dict[str, Any]:
    """Status, uptime, sessions, counters."""
    return _aggregator(request).get_health_overview()


@router.get("/performance")
async def performance(request: Request) -> dict[str, Any]:
    """Latency percentiles, confidence, ICD codes."""
    return _aggregator(request).get_performance_metrics()


@router.get("/vector-space")
async def vector_space(
    request: Request,
    max_points: int = Query(default=500, ge=10, le=5000),
) -> dict[str, Any]:
    """2D PCA scatter data for vector index visualization."""
    return _aggregator(request).get_vector_space(max_points)


@router.get("/safety")
async def safety(request: Request) -> dict[str, Any]:
    """Safety pass rate, violations, escalation metrics."""
    return _aggregator(request).get_safety_metrics()


@router.get("/bias")
async def bias(request: Request) -> dict[str, Any]:
    """Metrics by Fitzpatrick type and language."""
    return _aggregator(request).get_bias_metrics()


@router.get("/alerts")
async def alerts(request: Request) -> list[dict[str, Any]]:
    """Active alerts, rule definitions, runbook URLs."""
    return _aggregator(request).get_active_alerts()


@router.get("/audit-trail")
async def audit_trail(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Recent audit records."""
    return _aggregator(request).get_audit_records(limit)


@router.get("/logs")
async def logs(
    request: Request,
    level: str = Query(default=""),
    event: str = Query(default=""),
    search: str = Query(default=""),
    session_id: str = Query(default=""),
    since: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Filtered log records from in-memory buffer."""
    return _aggregator(request).get_logs(
        level=level,
        event=event,
        search=search,
        session_id=session_id,
        since=since,
        limit=limit,
    )


@router.get("/time-series")
async def time_series(
    request: Request,
    metric: str = Query(default="prediction_latency_ms"),
    bucket: int = Query(default=60, ge=5, le=3600),
) -> dict[str, Any]:
    """Time-bucketed metric data for charts."""
    return _aggregator(request).get_time_series(metric, bucket)


@router.get("/request-stats")
async def request_stats(request: Request) -> dict[str, Any]:
    """API call counts, errors, latency by path."""
    return _aggregator(request).get_request_stats()
