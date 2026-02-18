# Troubleshooting Guide

## Common Issues

### 1. `uv sync` fails with "package not found"
**Cause:** hatchling can't find the source package directory.
**Fix:** Ensure `pyproject.toml` has:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```

### 2. Tests fail with "No module named src"
**Cause:** Package not installed in editable mode.
**Fix:** Run `uv sync --extra dev` to install all dependencies.

### 3. mypy reports "import-untyped" for yaml
**Cause:** PyYAML doesn't ship type stubs.
**Fix:** Add `# type: ignore[import-untyped]` to the import line.

### 4. ruff reports E741 "ambiguous variable name"
**Cause:** Single-letter variable names like `I` or `l`.
**Fix:** Add `# noqa: E741` to the specific line or rename the variable.

### 5. SOAP generation returns 400 "No transcript data"
**Cause:** Trying to generate a SOAP note before any patient interaction.
**Fix:** Ensure at least one `/interact` call before `/soap`.

### 6. Session returns 404
**Cause:** Session was deleted or never created.
**Fix:** Create a new session via `POST /api/v1/sessions`.

### 7. Health check fails in Docker
**Cause:** Application not ready or port mismatch.
**Fix:** Check `docker compose logs app` and verify port 8000 is exposed.

### 8. High prediction latency alert
**Cause:** Model inference or RAG retrieval is slow.
**Fix:** See `docs/runbooks/high_latency.md`.

### 9. PII appearing in logs
**Cause:** `redact_pii()` not called before logging.
**Fix:** Ensure all user-provided text passes through PII redactor before structlog.

### 10. Escalation not triggering
**Cause:** Keyword not in the escalation list.
**Fix:** Check `ESCALATION_KEYWORDS` in `src/pipelines/patient_interview.py`.

## Debug Commands

```bash
# Check application health
curl http://localhost:8000/health

# View structured logs
docker compose logs app | jq .

# Run specific test
uv run pytest tests/unit/test_config.py -v

# Check coverage
uv run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Validate config
uv run python -c "from src.utils.config import load_settings; print(load_settings())"
```
