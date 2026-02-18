# Test Catalog

**Patient Advocacy Agent — Test Suite Reference**

Maps each test to the requirement it validates and the associated risk area.

## Unit Tests (`tests/unit/`)

| Test Module | Tests | Requirements | Risk Area |
|---|---|---|---|
| `test_config.py` | Config loading, env validation, defaults | REQ-CFG-001, REQ-CFG-002, REQ-CFG-003 | Configuration |
| `test_logger.py` | Structured logging, JSON output, levels | REQ-LOG-001, REQ-LOG-002 | Observability |
| `test_errors.py` | Error codes, serialization, chaining | REQ-ERR-001 | Error handling |
| `test_feature_flags.py` | Feature flag loading, env overrides | REQ-CFG-005 | Configuration |
| `test_session.py` | Session lifecycle, stage transitions | — | Session management |
| `test_pii_redactor.py` | PII/PHI redaction patterns | REQ-SEC-003 | Privacy/Security |
| `test_scin_schema.py` | SCIN record validation, ICD ranges | REQ-TST-004, REQ-TST-005 | Data quality |
| `test_scin_loader.py` | Data loading, validation errors | REQ-TST-004 | Data pipeline |
| `test_quality.py` | Quality checks (duplicates, missing fields) | REQ-OBS-012 | Data quality |
| `test_drift.py` | Distribution drift detection | REQ-OBS-015 | Data monitoring |
| `test_lineage.py` | Data lineage tracking and persistence | — | Data provenance |
| `test_embedding_model.py` | Embedding generation, normalization | REQ-TST-012 | Model quality |
| `test_losses.py` | Contrastive loss computation | — | Training |
| `test_clustering.py` | Silhouette score, clustering eval | REQ-TST-023 | Model evaluation |
| `test_training.py` | Training loop, pair creation | — | Training pipeline |
| `test_retrieval_eval.py` | Precision@K, Recall@K, MRR | REQ-TST-024 | Retrieval quality |
| `test_rag_retrieval.py` | Vector index, RAG retriever | REQ-TST-016 | Retrieval pipeline |
| `test_voice_services.py` | STT, TTS, language detection mocks | — | Voice pipeline |
| `test_webrtc.py` | WebRTC server stub | — | Voice pipeline |
| `test_soap_generator.py` | SOAP note generation | — | Medical pipeline |
| `test_case_history.py` | Case history formatting | — | Medical pipeline |
| `test_patient_interview.py` | Interview flow, escalation, consent | — | Interview pipeline |

## Integration Tests (`tests/integration/`)

| Test Module | Tests | Requirements | Risk Area |
|---|---|---|---|
| `test_api.py` | Full API endpoint testing (health, sessions, interaction, SOAP, case history) | REQ-TST-019, REQ-TST-020, REQ-DOC-005 | End-to-end |
| `test_pipeline.py` | Embedding->indexing->retrieval pipeline, interview->SOAP->case history pipeline | REQ-TST-016, REQ-TST-018, REQ-TST-020 | Pipeline integration |

## Evaluation Tests (`tests/evaluation/`)

| Test Module | Tests | Requirements | Risk Area |
|---|---|---|---|
| `test_model_eval.py` | Embedding quality thresholds, retrieval accuracy, clustering, medical model output | REQ-TST-021 - REQ-TST-025 | Model quality |
| `test_performance.py` | Latency benchmarks (embedding, retrieval, SOAP, interview), session scalability | REQ-TST-031 - REQ-TST-035 | Performance |

## Safety Tests (`tests/safety/`)

| Test Module | Tests | Requirements | Risk Area |
|---|---|---|---|
| `test_regulatory.py` | Never prescribes, never claims doctor, always disclaims, consent required | REQ-TST-050 | Regulatory compliance |
| `test_bias_fairness.py` | Fitzpatrick equity, language equity, escalation fairness | REQ-TST-036 - REQ-TST-039 | Bias/Fairness |
| `test_genai_regression.py` | Golden prompts, model response stability, escalation regression | REQ-TST-030 | GenAI regression |

## Running Tests

```bash
# All tests
uv run pytest tests/

# By category
uv run pytest tests/unit/          # Unit tests
uv run pytest tests/integration/   # Integration tests
uv run pytest tests/evaluation/    # Model evaluation
uv run pytest tests/safety/        # Safety & compliance

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Failure Debugging

Each test failure includes:
- Session IDs and trace IDs in structured log output
- Clear assertion messages with actual vs. expected values
- Relevant configuration and feature flag state

For runbook-style debugging, see `docs/troubleshooting.md`.
