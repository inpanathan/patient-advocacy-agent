# Deployment & Operational Runbook

**Patient Advocacy Agent — Deployment Guide**

## 1. Environments

| Environment | Purpose | Config File |
|---|---|---|
| Development | Local dev with mocks | `configs/dev.yaml` |
| Staging | Pre-production validation | `configs/staging.yaml` |
| Production | Live patient triage | `configs/production.yaml` |

## 2. Infrastructure Topology

```
[Load Balancer]
    |
[FastAPI Server (N replicas)]
    |
[Vector Store (ChromaDB)]  [MedGemma API]  [STT/TTS Services]
    |
[SCIN Database (read-only)]
```

## 3. Deployment Steps

### Local Development
```bash
# One-time setup
bash scripts/setup.sh

# Start server
bash scripts/start_server.sh development
```

### Local Mode (GPU — real models)

Running with `MODEL_BACKEND=local` requires downloading gated and large model
weights before first start. Follow these steps in order.

#### Prerequisites

```bash
# 1. Install the Hugging Face CLI (if not already installed)
pip install --user huggingface-cli
# Or via uv:
uv tool install huggingface-cli

# Verify installation
huggingface-cli --version
```

#### Hugging Face Authentication

MedGemma 4B is a **gated model**. You must request access and authenticate
before downloading.

```bash
# 2. Go to https://huggingface.co/google/medgemma-4b-it
#    Click "Agree and access repository" to accept the license.
#    (Approval may take a few minutes.)

# 3. Create an access token at https://huggingface.co/settings/tokens
#    - Token type: Read
#    - Copy the token (starts with hf_...)

# 4. Log in from the terminal
huggingface-cli login
#    Paste your token when prompted.
```

#### Download Models

```bash
# 5. Download all local models (~20GB total):
#    - MedGemma 4B instruction-tuned (~8GB)
#    - SigLIP-2 so400m-patch14-384 (~1.5GB)
#    - Faster-Whisper large-v3 (~3GB)
#    - Piper TTS voice models (~500MB)
bash scripts/download_models.sh
```

#### Download SCIN Dataset

The [SCIN (Skin Condition Image Network)](https://github.com/google-research-datasets/scin)
dataset provides 10,000+ dermatological images for the RAG knowledge base.

```bash
# 6. Install Google Cloud Storage client
uv pip install google-cloud-storage

# 7. Authenticate with Google Cloud (for GCS bucket access)
gcloud auth application-default login

# 8. Download full SCIN dataset (~2GB: metadata + images)
bash scripts/download_scin.sh

# OR: Download metadata only (fast, ~10MB)
bash scripts/download_scin.sh --skip-images

# OR: Download a subset for testing
bash scripts/download_scin.sh --limit 100
```

The script downloads from the public GCS bucket `dx-scin-public-data`, converts
the CSV data into our `metadata.json` format, and saves images to `data/raw/scin/images/`.

#### Configure and Start

```bash
# 9. Set MODEL_BACKEND=local in .env
#    Edit .env and change: MODEL_BACKEND=local

# 10. Install ML + voice dependencies (if not already)
uv pip install -e ".[ml,voice]"

# 11. Index SCIN embeddings into the vector store
bash scripts/index_embeddings.sh

# 12. Start the server
bash scripts/start_server.sh development

# 13. Verify with integration tests
MODEL_BACKEND=local uv run pytest tests/integration/test_local_models.py -v
```

#### Troubleshooting Hugging Face Access

| Error | Cause | Fix |
|---|---|---|
| `401 Client Error` / `Access restricted` | Not logged in or license not accepted | Run `huggingface-cli login` and accept the license at the model page |
| `huggingface-cli: command not found` | CLI not installed | Run `pip install --user huggingface-cli` or `uv tool install huggingface-cli` |
| `403 Forbidden` | Token lacks read scope | Generate a new token with `Read` permission at https://huggingface.co/settings/tokens |
| `Repository not found` | Model ID typo or model removed | Verify `LLM__MEDGEMMA_MODEL_ID` in `.env` matches a valid HF repo |

#### Troubleshooting SCIN Download

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: google.cloud.storage` | GCS client not installed | Run `uv pip install google-cloud-storage` |
| `DefaultCredentialsError` | Not authenticated with Google Cloud | Run `gcloud auth application-default login` |
| `gcloud: command not found` | Google Cloud SDK not installed | Install from https://cloud.google.com/sdk/docs/install |
| `403 Forbidden` on bucket | Bucket access issue | The bucket `dx-scin-public-data` is public; check network/proxy settings |
| `metadata.json` missing after download | Script failed mid-download | Re-run `bash scripts/download_scin.sh`; it's idempotent |

### Docker
```bash
# Build and start
docker compose up --build

# With GPU support
docker compose --profile gpu up --build
```

### Staging
```bash
# Deploy via CI/CD (automatic on merge to main)
# Or manually:
APP_ENV=staging ./scripts/start_server.sh staging
```

### Production
```bash
# Only via CI/CD pipeline after all gates pass
# See docs/promotion_criteria.md for gate definitions
```

## 4. Configuration

### Required Environment Variables (Production)
| Variable | Description |
|---|---|
| `SECRET_KEY` | Application secret (fails startup if missing) |
| `APP_ENV` | Must be `production` |
| `MODEL_BACKEND` | `local` or `cloud` (not `mock`) |
| `USE_MOCKS` | Must be `false` |
| `LOG_FORMAT` | Should be `json` |

### Model Backend Variables
| Variable | Default | Used By | Description |
|---|---|---|---|
| `MODEL_BACKEND` | `mock` | All | `mock`, `local`, or `cloud` |
| `LLM__MEDGEMMA_MODEL_ID` | `google/medgemma-4b-it` | Local | HF model ID |
| `LLM__GOOGLE_API_KEY` | — | Cloud | Gemini API key |
| `LLM__DEVICE` | `auto` | Local | `cuda`, `cpu`, or `auto` |
| `EMBEDDING__MODEL_ID` | `google/siglip-so400m-patch14-384` | Local+Cloud | HF model ID |
| `EMBEDDING__DEVICE` | `auto` | Local+Cloud | `cuda`, `cpu`, or `auto` |
| `VOICE__WHISPER_MODEL_SIZE` | `large-v3` | Local | Faster-Whisper model size |
| `VOICE__PIPER_VOICES_DIR` | `models/piper` | Local | Piper voice model directory |
| `VOICE__GOOGLE_CLOUD_PROJECT` | — | Cloud | GCP project ID |
| `VOICE__GOOGLE_APPLICATION_CREDENTIALS` | — | Cloud | GCP service account JSON path |

### Other Optional Variables
| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `VECTOR_STORE_TOP_K` | `10` | RAG retrieval depth |
| `EMBEDDING_DIMENSION` | `768` | Embedding vector size |

## 5. Scaling

- **Horizontal**: Increase `--workers` in uvicorn or replicas in docker-compose
- **Vertical**: GPU memory for MedGemma/SigLIP-2 models
- **Session store**: Migrate from in-memory to Redis for multi-instance

## 6. Monitoring

See `docs/app_cheatsheet.md` for dashboard links.

### Health Check
```bash
curl http://localhost:8000/health
# {"status": "ok", "env": "development", "version": "0.1.0"}
```

### Key Metrics
- `prediction_latency_ms` — p50/p95/p99
- `prediction_confidence` — average
- `escalations_total` — count
- `retrievals_total` — count

## 7. Rollback

### Quick Rollback
```bash
# Revert to previous Docker image
docker compose down
docker compose up -d --no-build  # Uses cached previous image

# Or via Git
git revert HEAD
git push
# CI/CD will deploy the reverted version
```

### Model Rollback
Model version is configured via `MEDGEMMA_MODEL_ID` env var.
Change to previous version and restart.

## 8. SLOs

| Metric | Target |
|---|---|
| Availability | 99.5% |
| p95 Latency | < 2 seconds |
| Escalation accuracy | 100% (no missed malignancies) |
| Disclaimer presence | 100% |
| PII leakage | 0 incidents |

## 9. Incident Response

1. Check health endpoint
2. Review structured logs (JSON format)
3. Check fired alerts (see `src/observability/alerts.py`)
4. Follow relevant runbook in `docs/runbook/`
5. Escalate to platform team if unresolved
