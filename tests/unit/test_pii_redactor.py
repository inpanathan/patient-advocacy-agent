"""Tests for PII/PHI redaction."""

from __future__ import annotations

from src.utils.pii_redactor import redact_dict, redact_pii


class TestPIIRedaction:
    """Test PII redaction patterns."""

    def test_redact_email(self):
        """Email addresses are redacted."""
        text = "Contact patient at john@example.com for follow-up"
        result = redact_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "john@example.com" not in result

    def test_redact_phone(self):
        """Phone numbers are redacted."""
        text = "Call +91-9876543210 for updates"
        result = redact_pii(text)
        assert "[REDACTED_PHONE]" in result

    def test_redact_ssn(self):
        """SSN-like patterns are redacted."""
        text = "ID: 123-45-6789"
        result = redact_pii(text)
        assert "[REDACTED_" in result  # May match SSN or phone pattern
        assert "123-45-6789" not in result

    def test_redact_name_with_prefix(self):
        """Names with prefixes are redacted."""
        text = "Patient John Smith presented with rash"
        result = redact_pii(text)
        assert "[REDACTED_NAME]" in result

    def test_no_false_positive_on_medical_terms(self):
        """Medical terms are not redacted."""
        text = "Atopic Dermatitis L20.0 on forearm"
        result = redact_pii(text)
        assert "Atopic Dermatitis" in result
        assert "L20.0" in result

    def test_redact_dict(self):
        """Dictionary values are redacted."""
        data = {
            "patient": "Mr. John",
            "email": "john@example.com",
            "diagnosis": "Eczema",
        }
        result = redact_dict(data)
        assert result["diagnosis"] == "Eczema"
        assert "john@example.com" not in result["email"]

    def test_redact_nested_dict(self):
        """Nested dictionaries are recursively redacted."""
        data = {"contact": {"email": "test@test.com"}}
        result = redact_dict(data)
        assert "test@test.com" not in result["contact"]["email"]
