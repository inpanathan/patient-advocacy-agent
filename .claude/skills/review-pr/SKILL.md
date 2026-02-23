---
name: review-pr
description: Review the current branch changes against the base branch — code quality, security, medical compliance, and correctness
disable-model-invocation: true
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash(git diff *), Bash(git log *), Bash(gh pr *)
---

Review the current branch's changes for merge readiness.

## Step 1: Gather context

```bash
git log --oneline main..HEAD
```

```bash
git diff main...HEAD --stat
```

```bash
git diff main...HEAD
```

## Step 2: Review each changed file for

**Correctness**
- Logic errors, missing edge cases, off-by-one errors
- Async/await correctness
- Missing error handling (should use AppError with ErrorCode)

**Security**
- Input validation at API boundaries
- No hardcoded secrets or credentials
- Safe handling of user-provided paths and data
- No PII/PHI in logs or error responses

**Medical compliance**
- Medical disclaimers present in patient-facing outputs
- Malignancy escalation logic intact (100% escalation rate)
- Consent verification for image capture not bypassed
- No code that prescribes or diagnoses
- PII redaction applied to all patient data before logging

**Project conventions**
- Uses structlog, not print()
- Config via settings singleton, not raw env vars
- Pydantic models for API schemas
- Tests exist for new public functions

**Code quality**
- No dead code or commented-out blocks
- Clear naming and reasonable function length
- Type hints on all function signatures

## Step 3: Output

Provide a structured review:

### Summary
One-paragraph assessment: ready to merge, needs minor fixes, or needs significant rework.

### Findings
For each issue:
- **File:line** — location
- **Severity** — must-fix / should-fix / nit
- **Issue** — what's wrong
- **Suggestion** — specific fix

### Checklist
- [ ] Tests pass
- [ ] No security issues
- [ ] No PII/PHI exposure
- [ ] Medical disclaimers present
- [ ] Escalation logic intact
- [ ] Follows project conventions
- [ ] Error handling is complete
- [ ] No dead code
