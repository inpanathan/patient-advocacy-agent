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

### Starting the Application

```bash
# Development server (with hot reload)
bash scripts/start_server.sh

# Staging (2 workers)
bash scripts/start_server.sh staging

# Production (4 workers)
bash scripts/start_server.sh production

# Docker
bash scripts/start_server.sh docker

# Start voice pipeline (WebRTC)
bash scripts/start_voice_pipeline.sh
```

### Data & Embeddings

```bash
# Initialize SCIN data directory structure
bash scripts/init_data.sh

# Initialize with mock data for development
bash scripts/init_data.sh --mock

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

# 4. Login to Hugging Face (required for gated models like MedGemma)
huggingface-cli login

# 5. Download all model weights (~20GB)
bash scripts/download_models.sh

# 6. Initialize data
bash scripts/init_data.sh

# 7. Start the server
bash scripts/start_server.sh

# 8. Verify with integration tests
MODEL_BACKEND=local uv run pytest tests/integration/test_local_models.py -v
```
