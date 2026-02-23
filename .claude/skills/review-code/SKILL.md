---
name: review-code
description: Review code for security vulnerabilities, bugs, medical compliance, and quality issues. Use when asked to review a file, module, or PR diff.
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash(git diff *), Bash(git log *)
---

Review the code specified by $ARGUMENTS for the following concerns:

## Security
- Injection vulnerabilities (SQL, command injection, XSS, prompt injection)
- Secrets or credentials hardcoded in source
- Insecure deserialization or eval usage
- Missing input validation at API boundaries
- CORS misconfiguration

## Medical compliance (CRITICAL)
- PII/PHI exposure: patient names, locations, medical data in logs or responses
- Missing medical disclaimer in patient-facing outputs
- Malignancy escalation: suspected malignancies must trigger immediate escalation
- Consent verification: image capture must be permission-gated
- No diagnostic claims: system must never prescribe or claim to be a doctor
- Audit trail: clinical data access must be logged

## Correctness
- Off-by-one errors, race conditions, unhandled edge cases
- Missing error handling — are AppError exceptions raised with proper ErrorCode?
- Async/await correctness — missing awaits, blocking calls in async functions
- Type mismatches that mypy wouldn't catch (e.g., Optional access without guard)

## Project conventions
- Uses structlog (`get_logger(__name__)`) instead of print or stdlib logging
- Config accessed via `settings` singleton, not raw env vars
- Pydantic models for API request/response schemas (in `src/api/schemas.py`)
- Tests exist for new public functions and endpoints
- PII redaction applied before logging patient data

## Output format
For each finding, report:
- **File and line**: exact location
- **Severity**: critical / warning / info
- **Issue**: what's wrong
- **Fix**: specific suggestion

Summarize with a count of findings by severity.
