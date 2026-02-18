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

    app = FastAPI(
        title="Patient Advocacy Agent",
        description=(
            "Dermatological triage via voice-only interface for underserved communities. "
            "Produces SOAP-formatted case histories for remote physicians."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "env": settings.app_env}

    return app


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
