"""Patient Advocacy Agent — application entry point.

Starts the FastAPI server with structured logging and validated configuration.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import Request

from src.utils.config import settings
from src.utils.logger import get_logger, setup_logging

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: F821
    """App startup/shutdown lifecycle.

    Startup: load SCIN data, build RAG index, init database.
    Shutdown: close database, log clean exit.
    """
    from src.data.scin_loader import SCINLoader
    from src.models.rag_retrieval import RAGRetriever, VectorIndex
    from src.pipelines.index_embeddings import index_scin_records

    # ---- Database init (guarded by settings.database.enabled) ----
    if settings.database.enabled:
        from src.db.engine import init_db

        await init_db()
        logger.info("database_initialized")

    # ---- SCIN data + RAG index ----
    index = VectorIndex()
    scin_path = Path(settings.scin.data_dir) / "metadata.json"

    if scin_path.exists():
        try:
            loader = SCINLoader(settings.scin.data_dir)
            records = loader.load()
            index_scin_records(records, index, data_dir=settings.scin.data_dir)
            logger.info("scin_data_loaded", record_count=index.size)
        except Exception as exc:
            logger.warning("scin_load_failed", error=str(exc))
    else:
        logger.warning("scin_data_not_found", path=str(scin_path))

    retriever = RAGRetriever(index, top_k=settings.vector_store.top_k)
    app.state.rag_retriever = retriever  # type: ignore[attr-defined]
    app.state.vector_index = index  # type: ignore[attr-defined]

    # ---- Case session bridge ----
    from src.api.case_session_bridge import CaseSessionBridge

    app.state.case_session_bridge = CaseSessionBridge()  # type: ignore[attr-defined]

    # ---- Dashboard observability singletons ----
    from src.api.routes import _session_store
    from src.observability.alerts import AlertEvaluator
    from src.observability.audit import AuditTrail
    from src.observability.dashboard_aggregator import DashboardAggregator, DashboardState
    from src.observability.safety_evaluator import SafetyEvaluator

    dashboard_state = DashboardState(
        start_time=time.monotonic(),
        session_store=_session_store,
        alert_evaluator=AlertEvaluator(),
        audit_trail=AuditTrail(),
        safety_evaluator=SafetyEvaluator(),
        vector_index=index,
    )
    app.state.dashboard_aggregator = dashboard_state  # type: ignore[attr-defined]
    app.state.dashboard_aggregator = DashboardAggregator(dashboard_state)  # type: ignore[attr-defined]

    yield

    # ---- Shutdown ----
    if settings.database.enabled:
        from src.db.engine import close_db

        await close_db()

    logger.info("app_shutdown")


def create_app():
    """Create and configure the FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    from src.api.routes import router
    from src.utils.errors import AppError

    app = FastAPI(
        title="Patient Advocacy Agent",
        description=(
            "Dermatological triage via voice-only interface for underserved communities. "
            "Produces SOAP-formatted case histories for remote physicians. "
            "**This system is NOT a doctor.**"
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS middleware — include Vite dev server
    origins = ["*"] if settings.app_debug else ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Existing API routes ----
    app.include_router(router, prefix="/api/v1")

    # ---- New multi-tenant routes ----
    from src.api.auth_routes import router as auth_router
    from src.api.case_routes import router as case_router
    from src.api.doctor_routes import router as doctor_router
    from src.api.facility_routes import router as facility_router
    from src.api.patient_routes import router as patient_router

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(facility_router, prefix="/api/v1")
    app.include_router(patient_router, prefix="/api/v1")
    app.include_router(case_router, prefix="/api/v1")
    app.include_router(doctor_router, prefix="/api/v1")

    # ---- Dashboard API + pages ----
    from src.api.dashboard_page import router as dashboard_page_router
    from src.api.dashboard_routes import router as dashboard_api_router
    from src.api.logs_page import router as logs_page_router
    from src.api.metrics_page import router as metrics_page_router

    app.include_router(dashboard_api_router, prefix="/api/v1/dashboard")
    app.include_router(dashboard_page_router)
    app.include_router(logs_page_router)
    app.include_router(metrics_page_router)

    # ---- Request tracking middleware ----
    from src.observability.metrics import get_metrics_collector

    @app.middleware("http")
    async def track_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - start) * 1000
        collector = get_metrics_collector()
        path = request.url.path
        collector.increment("request_count")
        collector.observe_latency(
            "request_latency",
            elapsed,
            labels={"method": request.method, "path": path, "status": str(response.status_code)},
        )
        if response.status_code >= 400:
            collector.increment("request_errors")
        return response

    @app.get("/health")
    async def health_check(request: Request):
        index = getattr(request.app.state, "vector_index", None)
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "0.1.0",
            "model_backend": settings.model_backend,
            "scin_records": index.size if index else 0,
            "database_enabled": settings.database.enabled,
        }

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):  # noqa: ARG001
        return JSONResponse(
            status_code=_error_code_to_status(exc.code),
            content=exc.to_dict(),
        )

    # ---- Static file serving for React SPA ----
    # Mount AFTER all API routes so they take priority.
    # StaticFiles with html=True serves index.html for unmatched paths (SPA routing).
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="spa")

    return app


def _error_code_to_status(code: str) -> int:
    """Map AppError codes to HTTP status codes."""
    mapping = {
        "VALIDATION_ERROR": 400,
        "UNAUTHORIZED": 401,
        "AUTH_FAILED": 401,
        "TOKEN_EXPIRED": 401,
        "TOKEN_INVALID": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "RATE_LIMITED": 429,
    }
    return mapping.get(code, 500)


def main() -> None:
    """Initialize logging, validate config, and start the server."""
    setup_logging(
        level=settings.logging.level,
        fmt=settings.logging.format,
    )
    logger = get_logger(__name__)

    logger.info(
        "starting_server",
        env=settings.app_env,
        debug=settings.app_debug,
        host=settings.server.host,
        port=settings.server.port,
    )

    uvicorn.run(
        "main:create_app",
        factory=True,
        host=settings.server.host,
        port=settings.server.port,
        workers=settings.server.workers,
        reload=settings.server.reload,
    )


if __name__ == "__main__":
    main()
