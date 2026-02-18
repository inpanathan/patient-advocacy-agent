"""PII/PHI redaction utilities.

Redacts personally identifiable and protected health information
from text before logging or storage.

Covers: REQ-LOG-006, REQ-OBS-028, REQ-OBS-030, REQ-OBS-061
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Patterns for common PII/PHI
_PATTERNS = [
    # Names (simple heuristic: capitalized words after common prefixes)
    (r"\b(Mr|Mrs|Ms|Dr|Patient)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", "[REDACTED_NAME]"),
    # Email addresses
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[REDACTED_EMAIL]"),
    # Phone numbers (various formats)
    (r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b", "[REDACTED_PHONE]"),
    # Dates of birth (MM/DD/YYYY, DD-MM-YYYY, etc.)
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "[REDACTED_DATE]"),
    # National IDs / SSN patterns
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    # GPS coordinates
    (r"-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}", "[REDACTED_LOCATION]"),
    # Village/location names after "village" or "from"
    (r"\b(?:village|from)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", "[REDACTED_LOCATION]"),
]

_COMPILED_PATTERNS = [(re.compile(p), r) for p, r in _PATTERNS]


def redact_pii(text: str) -> str:
    """Remove PII/PHI from text.

    Args:
        text: Input text potentially containing PII.

    Returns:
        Text with PII replaced by redaction markers.
    """
    result = text
    for pattern, replacement in _COMPILED_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_dict(data: dict) -> dict:  # type: ignore[type-arg]
    """Redact PII from all string values in a dictionary.

    Args:
        data: Dictionary with potentially sensitive values.

    Returns:
        New dictionary with PII redacted.
    """
    result: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = redact_pii(value)
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, list):
            result[key] = [redact_pii(v) if isinstance(v, str) else v for v in value]
        else:
            result[key] = value
    return result
