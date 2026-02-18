"""Tests for the logging module."""

from __future__ import annotations

import logging

from src.utils.logger import get_logger, setup_logging


class TestSetupLogging:
    """Test logging configuration."""

    def test_setup_json_logging(self):
        """JSON logging mode configures without error."""
        setup_logging(level="INFO", fmt="json")
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 2  # StreamHandler + BufferHandler

    def test_setup_console_logging(self):
        """Console logging mode configures without error."""
        setup_logging(level="DEBUG", fmt="console")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_noisy_loggers_suppressed(self):
        """Third-party loggers are set to WARNING."""
        setup_logging(level="DEBUG", fmt="json")
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_returns_bound_logger(self):
        """get_logger returns a structlog BoundLogger."""
        setup_logging(level="INFO", fmt="json")
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_without_name(self):
        """get_logger works without a name argument."""
        setup_logging(level="INFO", fmt="json")
        logger = get_logger()
        assert logger is not None
