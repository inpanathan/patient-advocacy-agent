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
./scripts/setup.sh

# Start server
./scripts/start_server.sh development
```

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
| `MEDGEMMA_API_KEY` | MedGemma API access key |
| `USE_MOCKS` | Must be `false` |
| `LOG_FORMAT` | Should be `json` |

### Optional Variables
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
