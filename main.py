"""Patient Advocacy Agent — application entry point.

Starts the FastAPI server with structured logging and validated configuration.
"""

from __future__ import annotations

import uvicorn

from src.utils.config import settings
from src.utils.logger import get_logger, setup_logging


def create_app():
    """Create and configure the FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

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
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS middleware for WebRTC clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "0.1.0",
        }

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):  # noqa: ARG001
        return JSONResponse(
            status_code=_error_code_to_status(exc.code),
            content=exc.to_dict(),
        )

    return app


def _error_code_to_status(code: str) -> int:
    """Map AppError codes to HTTP status codes."""
    mapping = {
        "VALIDATION_ERROR": 400,
        "UNAUTHORIZED": 401,
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
