"""JSON API endpoints for the monitoring dashboard.

All endpoints are under /api/v1/dashboard/ and return JSON data
consumed by the dashboard HTML pages.
"""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import structlog
from fastapi import APIRouter, Query, Request

from src.db.engine import get_session_factory
from src.db.models import Case, CaseImage
from src.observability.dashboard_aggregator import DashboardAggregator

logger = structlog.get_logger(__name__)

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
    method: str = Query(default="pca", pattern="^(pca|tsne|umap)$"),
) -> dict[str, Any]:
    """2D projection scatter data for vector index visualization."""
    return _aggregator(request).get_vector_space(max_points, method)


@router.get("/case-overlay")
async def case_overlay(
    request: Request,
    case_id: str = Query(..., description="Case UUID"),
    method: str = Query(default="pca", pattern="^(pca|tsne|umap)$"),
    max_points: int = Query(default=500, ge=10, le=5000),
) -> dict[str, Any]:
    """Project a case's image embeddings alongside the SCIN reference set."""
    # Validate UUID
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        return {"error": f"Invalid case ID: {case_id}", "points": []}

    # Fetch case and its images from DB
    try:
        factory = get_session_factory()
    except RuntimeError:
        return {"error": "Database not available", "points": []}

    async with factory() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(Case).where(Case.id == case_uuid).options(selectinload(Case.images))
        result = await session.execute(stmt)
        case: Case | None = result.scalar_one_or_none()

    if case is None:
        return {"error": f"Case not found: {case_id}", "points": []}

    images: list[CaseImage] = list(case.images) if case.images else []
    if not images:
        return {"error": "Case has no images", "points": []}

    # Embed each case image
    try:
        from src.models.embedding_model import get_embedding_model

        model = get_embedding_model()
        embeddings_list = []
        case_meta = []
        for img in images:
            emb = model.embed_image(img.file_path)
            embeddings_list.append(emb)
            case_meta.append(
                {
                    "diagnosis": ", ".join(case.icd_codes) if case.icd_codes else "Case image",
                    "icd_code": ", ".join(case.icd_codes) if case.icd_codes else "",
                    "fitzpatrick_type": "",
                    "record_id": str(case.id),
                }
            )
        case_embeddings = np.stack(embeddings_list).astype(np.float32)
    except Exception as exc:
        logger.warning("case_overlay_embed_failed", error=str(exc), case_id=case_id)
        return {"error": f"Failed to embed case images: {exc}", "points": []}

    return _aggregator(request).get_case_overlay(
        case_embeddings,
        case_meta,
        max_points,
        method,
    )


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
