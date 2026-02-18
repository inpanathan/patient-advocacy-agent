"""Consistent error response format for the Patient Advocacy Agent.

All application errors inherit from AppError and carry a machine-readable
error code, a human-readable message, and optional structured context.

Covers: REQ-ERR-001, REQ-ERR-005
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Machine-readable error codes for every known failure mode."""

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"

    # Configuration
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"

    # Data pipeline
    DATA_LOAD_FAILED = "DATA_LOAD_FAILED"
    DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED"
    DATA_DRIFT_DETECTED = "DATA_DRIFT_DETECTED"

    # Embedding / model
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"

    # RAG / vector store
    RAG_RETRIEVAL_FAILED = "RAG_RETRIEVAL_FAILED"
    RAG_INDEX_FAILED = "RAG_INDEX_FAILED"

    # Voice pipeline
    STT_FAILED = "STT_FAILED"
    TTS_FAILED = "TTS_FAILED"
    LANGUAGE_DETECTION_FAILED = "LANGUAGE_DETECTION_FAILED"
    WEBRTC_ERROR = "WEBRTC_ERROR"

    # Medical AI
    SOAP_GENERATION_FAILED = "SOAP_GENERATION_FAILED"
    ESCALATION_ERROR = "ESCALATION_ERROR"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"

    # External services
    EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT"
    EXTERNAL_UNAVAILABLE = "EXTERNAL_UNAVAILABLE"

    # Session
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"


class AppError(Exception):
    """Base application error with structured context.

    Usage:
        raise AppError(
            code=ErrorCode.RAG_RETRIEVAL_FAILED,
            message="Vector store query timed out",
            context={"query_id": qid, "timeout_ms": 5000},
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: dict[str, Any] | None = None,
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}
        self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON API responses."""
        return {
            "error": {
                "code": self.code.value,
                "message": str(self),
                "context": self.context,
            }
        }

    def __repr__(self) -> str:
        return f"AppError(code={self.code!r}, message={self!s}, context={self.context!r})"
