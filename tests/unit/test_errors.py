"""Tests for the error handling module."""

from __future__ import annotations

from src.utils.errors import AppError, ErrorCode


class TestErrorCode:
    """Test error code enumeration."""

    def test_error_codes_are_strings(self):
        """All error codes are string values."""
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert ErrorCode.RAG_RETRIEVAL_FAILED == "RAG_RETRIEVAL_FAILED"

    def test_all_error_codes_unique(self):
        """No duplicate error code values."""
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestAppError:
    """Test AppError exception class."""

    def test_basic_error(self):
        """Create an error with code and message."""
        err = AppError(code=ErrorCode.INTERNAL_ERROR, message="Something broke")
        assert str(err) == "Something broke"
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.context == {}

    def test_error_with_context(self):
        """Create an error with structured context."""
        err = AppError(
            code=ErrorCode.RAG_RETRIEVAL_FAILED,
            message="Vector store query timed out",
            context={"query_id": "q-123", "timeout_ms": 5000},
        )
        assert err.context["query_id"] == "q-123"
        assert err.context["timeout_ms"] == 5000

    def test_error_to_dict(self):
        """Serialize error to API response format."""
        err = AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            context={"field": "age"},
        )
        d = err.to_dict()
        assert d["error"]["code"] == "VALIDATION_ERROR"
        assert d["error"]["message"] == "Invalid input"
        assert d["error"]["context"]["field"] == "age"

    def test_error_with_cause(self):
        """Error can chain to an original cause."""
        original = ValueError("bad value")
        err = AppError(
            code=ErrorCode.DATA_VALIDATION_FAILED,
            message="Schema check failed",
            cause=original,
        )
        assert err.__cause__ is original

    def test_error_is_exception(self):
        """AppError can be raised and caught."""
        with __import__("pytest").raises(AppError) as exc_info:
            raise AppError(code=ErrorCode.NOT_FOUND, message="Resource not found")
        assert exc_info.value.code == ErrorCode.NOT_FOUND

    def test_error_repr(self):
        """Repr is informative."""
        err = AppError(code=ErrorCode.INTERNAL_ERROR, message="boom")
        assert "INTERNAL_ERROR" in repr(err)
        assert "boom" in repr(err)
