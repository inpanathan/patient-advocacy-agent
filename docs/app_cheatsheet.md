# App Cheatsheet

**Patient Advocacy Agent — Quick Reference**

## URLs & Endpoints

### Local Development
| URL | Description |
|---|---|
| `http://localhost:8000` | Application root |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | Swagger/OpenAPI docs |
| `http://localhost:8000/redoc` | ReDoc API docs |

### API Endpoints (prefix: `/api/v1`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sessions` | Create new patient session |
| `GET` | `/sessions/{id}` | Get session status |
| `DELETE` | `/sessions/{id}` | Delete session |
| `POST` | `/sessions/{id}/interact` | Process patient utterance |
| `POST` | `/sessions/{id}/consent` | Record image consent |
| `POST` | `/sessions/{id}/soap` | Generate SOAP note |
| `GET` | `/sessions/{id}/case-history` | Get formatted case history |

## Commands

```bash
# Start development server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
uv run pytest tests/

# Run by category
uv run pytest tests/unit/          # Unit tests
uv run pytest tests/integration/   # Integration tests
uv run pytest tests/evaluation/    # Model evaluation
uv run pytest tests/safety/        # Safety & compliance

# Lint and type check
uv run ruff check src/ tests/ --fix
uv run mypy src/

# Coverage report
uv run pytest tests/ --cov=src --cov-report=html
```

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment: development, staging, production |
| `DEBUG` | `true` | Debug mode |
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `console` | Log format: console, json |
| `USE_MOCKS` | `true` | Use mock models (no GPU required) |
| `SECRET_KEY` | (required in prod) | Application secret key |
| `MEDGEMMA_API_KEY` | — | MedGemma API key |
| `EMBEDDING_MODEL_ID` | `google/siglip-so400m-patch14-384` | Embedding model |
| `VECTOR_STORE_TOP_K` | `10` | RAG retrieval top-K |

## Monitoring

| Dashboard | Description | Runbook |
|---|---|---|
| Prediction Metrics | Confidence, latency, ICD distribution | `docs/runbooks/low_confidence.md` |
| Escalation Rate | % sessions escalated | `docs/runbooks/high_escalation.md` |
| Latency | p50/p95/p99 for all components | `docs/runbooks/high_latency.md` |
| Safety Compliance | Prescription/disclaimer violations | — |
| Bias Metrics | Per-Fitzpatrick, per-language stats | — |

## Key Files

| Path | Description |
|---|---|
| `main.py` | FastAPI application entry point |
| `src/api/routes.py` | All HTTP endpoint definitions |
| `src/pipelines/patient_interview.py` | Interview agent logic |
| `src/pipelines/soap_generator.py` | SOAP note generation |
| `src/models/medical_model.py` | Medical AI model factory |
| `src/observability/metrics.py` | Metrics collection |
| `src/observability/alerts.py` | Alert rules and evaluation |
| `src/observability/audit.py` | Prediction audit trail |
| `configs/dev.yaml` | Development configuration |

## Scripts

### Sync Requirements Controller

Regenerates `docs/common_requirements_controller.json` from `docs/common_requirements.md`. Preserves any `implement`/`enable` flags already set to `"Y"`.

```bash
# Preview changes (no files written)
./scripts/sync_requirements.sh --dry-run

# Apply changes
./scripts/sync_requirements.sh
```
