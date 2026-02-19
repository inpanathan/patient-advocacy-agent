# App Cheatsheet

**Patient Advocacy Agent — Quick Reference**

## URLs & Endpoints

### Local Development
| URL | Description |
|---|---|
| `http://localhost:5173` | Frontend (React dev server, proxies API to backend) |
| `http://localhost:8000` | Backend API root |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | Swagger/OpenAPI docs |
| `http://localhost:8000/redoc` | ReDoc API docs |

### Monitoring Dashboard
| URL | Description |
|---|---|
| `http://localhost:8000/dashboard` | Overview dashboard (health, alerts, vector space, safety, bias) |
| `http://localhost:8000/dashboard/logs` | Log Viewer (search/filter structured logs) |
| `http://localhost:8000/dashboard/metrics` | Metrics Explorer (time-series, API calls, errors) |

### Dashboard API Endpoints (prefix: `/api/v1/dashboard`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health-overview` | Status, uptime, sessions, counters |
| `GET` | `/performance` | Latency percentiles, confidence, ICD codes |
| `GET` | `/vector-space?max_points=500` | 2D PCA scatter data |
| `GET` | `/safety` | Safety pass rate, violations, escalation |
| `GET` | `/bias` | Metrics by Fitzpatrick type and language |
| `GET` | `/alerts` | Active alerts with runbook URLs |
| `GET` | `/audit-trail?limit=50` | Recent audit records |
| `GET` | `/logs?level=&event=&search=&limit=200` | Filtered log records |
| `GET` | `/time-series?metric=&bucket=60` | Time-bucketed metric data |
| `GET` | `/request-stats` | API call counts, errors, latency by path |

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
| `APP_ENV` | `dev` | Environment: dev, staging, production, test |
| `APP_DEBUG` | `true` | Debug mode |
| `MODEL_BACKEND` | `mock` | Model backend: `mock`, `local`, `cloud` |
| `USE_MOCKS` | `true` | Use mock models (no GPU required) |
| `SECRET_KEY` | (required in prod) | Application secret key |
| `LLM__MEDGEMMA_MODEL_ID` | `google/medgemma-4b-it` | HF model ID for local LLM |
| `LLM__GOOGLE_API_KEY` | — | Gemini API key (cloud mode) |
| `LLM__DEVICE` | `auto` | Device for local LLM: cuda, cpu, auto |
| `EMBEDDING__MODEL_ID` | `google/siglip-so400m-patch14-384` | Embedding model |
| `EMBEDDING__DEVICE` | `auto` | Device for embeddings: cuda, cpu, auto |
| `VOICE__WHISPER_MODEL_SIZE` | `large-v3` | Faster-Whisper model size (local) |
| `VOICE__PIPER_VOICES_DIR` | `models/piper` | Piper TTS voice model directory |
| `VOICE__GOOGLE_CLOUD_PROJECT` | — | GCP project ID (cloud mode) |
| `VOICE__GOOGLE_APPLICATION_CREDENTIALS` | — | GCP service account JSON path |
| `VECTOR_STORE_TOP_K` | `10` | RAG retrieval top-K |

## Monitoring

| Dashboard | Description | Runbook |
|---|---|---|
| Prediction Metrics | Confidence, latency, ICD distribution | `docs/runbook/low_confidence.md` |
| Escalation Rate | % sessions escalated | `docs/runbook/high_escalation.md` |
| Latency | p50/p95/p99 for all components | `docs/runbook/high_latency.md` |
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

All operational scripts live in `scripts/`. Every manual step required to run the application has a corresponding script (REQ-RUN-001).

### First-Time Setup

```bash
# Full developer environment setup (Python, uv, deps, .env, pre-commit, dirs)
bash scripts/setup.sh
```

### Model Downloads (required for local mode)

```bash
# Download ALL local models (MedGemma 4B, SigLIP-2, Whisper, Piper voices)
bash scripts/download_models.sh

# Download only Piper TTS voice models (all 6 languages)
bash scripts/download_piper_voices.sh

# Download Piper voices for specific languages only
bash scripts/download_piper_voices.sh en hi es
```

**Note:** MedGemma 4B is a gated model. You must first run `huggingface-cli login` and accept the license at [the model page](https://huggingface.co/google/medgemma-4b-it).

### Database Management

```bash
# Create PostgreSQL user + database (idempotent, needs sudo)
sudo bash scripts/db_setup.sh

# Generate initial migration from ORM models
bash scripts/db_migrate.sh init

# Apply all pending migrations
bash scripts/db_migrate.sh upgrade

# Generate a new migration after model changes
bash scripts/db_migrate.sh generate "add column X to table Y"

# Roll back one migration
bash scripts/db_migrate.sh downgrade -1

# Show migration status (current revision, pending)
bash scripts/db_migrate.sh status

# Seed development data (skip if already seeded)
bash scripts/db_seed.sh

# Seed with reset (truncate all tables first)
bash scripts/db_seed.sh --reset

# Full database health check (connection, tables, row counts, size)
bash scripts/db_status.sh

# Back up database (compressed custom format)
bash scripts/db_backup.sh

# Back up as plain SQL
bash scripts/db_backup.sh --sql

# Restore from backup (auto-detects format)
bash scripts/db_restore.sh backups/<filename>

# Nuclear reset: drop all, re-migrate, re-seed (blocked in production)
bash scripts/db_reset.sh
```

**Database configuration** is read from `.env` — see the `DATABASE__*` variables. All destructive scripts (`db_reset.sh`, `db_restore.sh`) require typing "yes" to confirm and are blocked when `APP_ENV=production`.

### Starting the Application

```bash
# Backend — development server (with hot reload)
bash scripts/start_server.sh

# Backend — staging (2 workers)
bash scripts/start_server.sh staging

# Backend — production (4 workers)
bash scripts/start_server.sh production

# Backend — Docker
bash scripts/start_server.sh docker

# Frontend — dev server (proxies /api to backend on :8000)
bash frontend/scripts/start.sh           # http://localhost:5173

# Frontend — production build
bash frontend/scripts/start.sh build     # outputs to frontend/dist/

# Frontend — preview production build
bash frontend/scripts/start.sh preview

# Frontend — stop
bash frontend/scripts/stop.sh

# Start voice pipeline (WebRTC)
bash scripts/start_voice_pipeline.sh
```

**Typical dev workflow:** Start the backend first (`bash scripts/start_server.sh`), then in a second terminal start the frontend (`bash frontend/scripts/start.sh`). The Vite dev server on port 5173 proxies API calls to the backend on port 8000. Press `b` to background either process, or `q` to stop. You can also stop the frontend later with `bash frontend/scripts/stop.sh`.

### Data & Embeddings

```bash
# Initialize SCIN data directory structure
bash scripts/init_data.sh

# Initialize with mock data for development
bash scripts/init_data.sh --mock

# Download real SCIN dataset from Google Cloud Storage (~2GB)
bash scripts/download_scin.sh

# Download metadata only (skip images, fast)
bash scripts/download_scin.sh --skip-images

# Download a subset for testing (first N cases)
bash scripts/download_scin.sh --limit 100

# Run SigLIP-2 embedding fine-tuning
bash scripts/train_embeddings.sh

# Index SCIN embeddings into the vector store
bash scripts/index_embeddings.sh
```

### Git Workflows

```bash
# First-time git setup (user config, remote, etc.)
bash scripts/git_setup.sh

# Commit and push changes
bash scripts/git_push.sh
```

### Sync Requirements Controller

Regenerates `docs/common_requirements_controller.json` from `docs/common_requirements.md`. Preserves any `implement`/`enable` flags already set to `"Y"`.

```bash
# Preview changes (no files written)
./scripts/sync_requirements.sh --dry-run

# Apply changes
./scripts/sync_requirements.sh
```

### Running in Local Mode (Complete Checklist)

```bash
# 1. Setup environment
bash scripts/setup.sh

# 2. Set MODEL_BACKEND=local in .env
#    (setup.sh creates .env from .env.example — edit the MODEL_BACKEND line)

# 3. Install ML + voice dependencies
uv pip install -e ".[ml,voice]"

# 4. Setup PostgreSQL database
sudo bash scripts/db_setup.sh        # Create user + database
bash scripts/db_migrate.sh init       # Generate initial migration
bash scripts/db_migrate.sh upgrade    # Apply migrations
bash scripts/db_seed.sh               # Seed development data

# 5. Login to Hugging Face (required for gated models like MedGemma)
huggingface-cli login

# 6. Download all model weights (~20GB)
bash scripts/download_models.sh

# 7. Download SCIN dataset (~2GB, no auth required)
bash scripts/download_scin.sh

# 8. Index SCIN embeddings into the vector store
bash scripts/index_embeddings.sh

# 9. Start the server
bash scripts/start_server.sh

# 10. Verify with integration tests
MODEL_BACKEND=local uv run pytest tests/integration/test_local_models.py -v
```
