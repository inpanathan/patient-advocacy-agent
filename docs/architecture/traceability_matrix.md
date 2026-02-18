# Traceability Matrix

**Requirements -> Architecture Drivers -> Design Decisions -> Tests**

## Configuration & Dependencies

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-CFG-001 | Layered config | pydantic-settings + YAML | `src/utils/config.py` | `test_config.py` |
| REQ-CFG-002 | Environment-specific | Config YAML files | `configs/*.yaml` | `test_config.py` |
| REQ-CFG-003 | Startup validation | `validate_production()` | `src/utils/config.py` | `test_config.py` |
| REQ-CFG-005 | Feature flags | Boolean env flags | `src/utils/feature_flags.py` | `test_feature_flags.py` |
| REQ-DEP-001 | Dependency management | uv + pyproject.toml | `pyproject.toml` | CI pipeline |
| REQ-DEP-002 | Reproducibility | Docker + uv.lock | `Dockerfile` | CI Docker build |
| REQ-DEP-003 | Vulnerability scanning | pip-audit in CI | `.github/workflows/ci.yaml` | CI security job |

## Logging & Observability

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-LOG-001 | Structured logging | structlog JSON | `src/utils/logger.py` | `test_logger.py` |
| REQ-OBS-019-026 | Model dashboard | MetricsCollector | `src/observability/metrics.py` | `test_metrics.py` |
| REQ-OBS-027-032 | Prediction logging | record_prediction() | `src/observability/metrics.py` | `test_metrics.py` |
| REQ-OBS-047-048 | Safety monitoring | SafetyEvaluator | `src/observability/safety_evaluator.py` | `test_safety_evaluator.py` |
| REQ-OBS-049-052 | Alert thresholds | AlertEvaluator | `src/observability/alerts.py` | `test_alerts.py` |
| REQ-OBS-063 | Audit trail | AuditTrail (JSONL) | `src/observability/audit.py` | `test_audit.py` |

## Data Pipeline

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-TST-004 | Schema validation | Pydantic models | `src/data/scin_schema.py` | `test_scin_schema.py` |
| REQ-OBS-012 | Data quality | Quality checks | `src/data/quality.py` | `test_quality.py` |
| REQ-OBS-015 | Drift detection | Distribution comparison | `src/data/drift.py` | `test_drift.py` |

## Model & Retrieval

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-TST-012 | Embedding quality | Protocol + mock pattern | `src/models/embedding_model.py` | `test_embedding_model.py` |
| REQ-TST-016 | Retrieval pipeline | VectorIndex + RAGRetriever | `src/models/rag_retrieval.py` | `test_rag_retrieval.py`, `test_pipeline.py` |
| REQ-TST-021-025 | Metric thresholds | Evaluation test suite | `tests/evaluation/test_model_eval.py` | Nightly CI |

## Safety & Compliance

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-TST-030 | GenAI regression | Golden prompt suite | `tests/safety/test_genai_regression.py` | CI safety job |
| REQ-TST-036-039 | Bias/fairness | Fitzpatrick equity tests | `tests/safety/test_bias_fairness.py` | CI safety job |
| REQ-TST-050 | Regulatory | Never prescribes tests | `tests/safety/test_regulatory.py` | CI safety job |
| REQ-SEC-003 | PII protection | Regex redaction | `src/utils/pii_redactor.py` | `test_pii_redactor.py` |

## CI/CD

| Requirement | Architecture Driver | Design Decision | Implementation | Test |
|---|---|---|---|---|
| REQ-CIC-001 | Automated CI | GitHub Actions | `.github/workflows/ci.yaml` | On every commit |
| REQ-CIC-002 | Nightly evaluation | Scheduled workflow | `.github/workflows/nightly.yaml` | Nightly at 2 AM |
| REQ-TST-043 | Promotion criteria | Gate documentation | `docs/promotion_criteria.md` | — |
