# Patient Advocacy Agent - Implementation Plan v1

**Created:** 2026-02-18
**Status:** In Progress — Phases 0-1 Done, Phase 2 In Progress
**Total Requirements:** 157 (116 common + 41 documentation)
**Phases:** 11
**Source Documents:**
- `docs/requirements/project_requirements_v1.md`
- `docs/requirements/common_requirements.md`
- `docs/requirements/common_requirements_controller.json`
- `docs/requirements/documentation_requirements.md`
- `docs/requirements/documentation_requirements_controller.json`

---

## Phase 0: Project Foundation & Scaffolding

**Goal:** Establish the project skeleton, tooling, README, and developer environment so
that all subsequent phases have a stable base.

**Duration Estimate:** Sprint 1

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 0.1 | Fix `pyproject.toml` (rename from `person-of-interest` to `patient-advocacy-agent`, add description) | — | Done |
| 0.2 | Set up Python virtual environment (uv / poetry) with `.python-version` (3.12+) | REQ-DEP-002 | Done |
| 0.3 | Create `requirements.txt` / `pyproject.toml` dependency groups (core, dev, test, docs) and pin versions | REQ-DEP-001 | Done |
| 0.4 | Document system-level requirements (CUDA, GPU drivers, OS packages for audio/WebRTC) in `docs/system_requirements.md` | REQ-DEP-004 | Done |
| 0.5 | Create layered configuration module (`src/utils/config.py`) with defaults + env overrides + startup validation | REQ-CFG-001, REQ-CFG-002, REQ-CFG-003 | Done |
| 0.6 | Create `configs/` environment files: `dev.yaml`, `staging.yaml`, `production.yaml` | REQ-CFG-002 | Done |
| 0.7 | Set up centralized structured logger (`src/utils/logger.py`) with JSON output, core fields, log levels | REQ-LOG-001, REQ-LOG-002, REQ-LOG-008, REQ-LOG-012, REQ-LOG-014 | Done |
| 0.8 | Define consistent error response format (`src/utils/errors.py`) | REQ-ERR-001 | Done |
| 0.9 | Create `.env.example` with all required env vars; add `.env` to `.gitignore` | REQ-SEC-001 | Done |
| 0.10 | Build `README.md` from template, linking to all docs | REQ-AGT-001 | Done |
| 0.11 | Set up `pre-commit` hooks (ruff, mypy, black) | REQ-CIC-001 | Done |
| 0.12 | Create initial GitHub Actions CI pipeline (`lint + type-check + unit tests`) | REQ-CIC-001, REQ-CIC-005 | Done |
| 0.13 | Add `pip-audit` / `trivy` to CI for dependency vulnerability scanning | REQ-DEP-003, REQ-SEC-005 | Done |
| 0.14 | Create `scripts/setup.sh` for one-command dev environment setup | REQ-RUN-001 | Done |
| 0.15 | Set up experiment config versioning (hyperparameters in `configs/experiments/`) | REQ-CFG-004 | Done |
| 0.16 | Create feature flags module (`src/utils/feature_flags.py`) | REQ-CFG-005 | Done |

### Deliverables
- Working dev environment with `uv run main.py`
- CI pipeline passing on every PR
- Structured logger, config loader, error format available as imports
- README.md linking to all documentation

### Dependencies
- None (first phase)

---

## Phase 1: Data Pipeline & SCIN Database

**Goal:** Ingest, validate, version, and index the SCIN database (2GB, Harvard University)
for downstream RAG retrieval and model fine-tuning.

**Duration Estimate:** Sprint 2-3

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 1.1 | Research SCIN database format: schema, image formats, diagnosis labels, ICD codes, metadata fields | REQ-TST-004 | Done |
| 1.2 | Create data ingestion pipeline (`src/data/scin_loader.py`): download/mount SCIN, parse records | REQ-DAT-002 | Done |
| 1.3 | Implement data schema validation (column names, types, required fields, ICD code ranges, Fitzpatrick types) | REQ-TST-004, REQ-TST-005, REQ-OBS-012 | Done |
| 1.4 | Implement data quality checks: missing values, duplicates, outliers, invalid categories | REQ-TST-006, REQ-TST-007, REQ-OBS-013 | Done |
| 1.5 | Compute and store baseline statistics (mean, std, quantiles per feature) for drift comparison | REQ-TST-008, REQ-OBS-015 | Done |
| 1.6 | Set up DVC for dataset versioning (SCIN snapshots, training sets, evaluation sets) | REQ-DAT-001 | Blocked — DVC requires external storage config |
| 1.7 | Configure artifact storage (S3/GCS/local) for SCIN database + models (not in git) | REQ-DAT-004 | Blocked — awaiting cloud provider decision |
| 1.8 | Implement data lineage tracking (`src/data/lineage.py`): raw source -> processed -> features | REQ-DAT-005, REQ-OBS-009 | Done |
| 1.9 | Define data retention and deletion policies for patient data (voice, images, case histories) | REQ-DAT-003, REQ-OBS-060 | Done |
| 1.10 | Create data pipeline validation tests (`tests/data/test_scin_loader.py`) | REQ-DAT-002, REQ-TST-016 | Done |
| 1.11 | Add data drift alerting thresholds and alert stubs | REQ-TST-009, REQ-OBS-017, REQ-OBS-018 | Done |
| 1.12 | Create `scripts/init_data.sh` to download/initialize SCIN data | REQ-RUN-001 | Done |

### Deliverables
- SCIN database ingested, validated, and versioned with DVC
- Baseline statistics stored for drift comparison
- Data lineage tracking from raw to processed
- Data quality tests passing in CI

### Dependencies
- Phase 0 (config, logger, error handling)

---

## Phase 2: Embedding Model & Fine-Tuning Pipeline

**Goal:** Load SigLIP-2, fine-tune with contrastive loss for isotropic embeddings on the
SCIN database, and validate via clustering.

**Duration Estimate:** Sprint 3-5

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 2.1 | Integrate SigLIP-2 model (`src/models/embedding_model.py`): load, preprocess images, generate embeddings | REQ-CST-009, REQ-CST-011 | Pending |
| 2.2 | Implement contrastive loss function (`src/models/losses.py`) for embedding fine-tuning | REQ-TST-012 | Pending |
| 2.3 | Build fine-tuning training loop (`src/pipelines/train_embeddings.py`): data loading, training, checkpointing | REQ-OBS-055 | Pending |
| 2.4 | Implement embedding normalization (unit hypersphere) and isotropy measurement | REQ-TST-011 | Pending |
| 2.5 | Implement clustering evaluation (`src/evaluation/clustering.py`): silhouette score, per-diagnosis clustering | REQ-TST-021 | Pending |
| 2.6 | Set up experiment tracking (MLflow / W&B): log hyperparams, metrics, artifacts per run | REQ-OBS-055, REQ-OBS-056, REQ-CFG-004 | Pending |
| 2.7 | Record model registry entries: dataset ref, code version, hyperparams, eval metrics, environment info | REQ-OBS-004 - REQ-OBS-011 | Pending |
| 2.8 | Lock in baseline model (pre-fine-tuned SigLIP-2) for regression comparison | REQ-TST-022 | Pending |
| 2.9 | Implement invariance tests: image rotation, lighting changes should preserve predictions | REQ-TST-024 | Pending |
| 2.10 | Implement directional expectation tests | REQ-TST-025 | Pending |
| 2.11 | Evaluate metrics per Fitzpatrick skin type (I-VI) for bias detection | REQ-TST-023, REQ-TST-036, REQ-OBS-045 | Pending |
| 2.12 | Document observed bias disparities and mitigation steps | REQ-TST-037, REQ-OBS-046 | Pending |
| 2.13 | Sign and verify model artifacts | REQ-SEC-006 | Pending |
| 2.14 | Fix random seeds for reproducibility | REQ-TST-044 | Pending |
| 2.15 | Create `scripts/train_embeddings.sh` | REQ-RUN-001 | Pending |
| 2.16 | Unit tests for: contrastive loss, embedding normalization, clustering metrics, preprocessing transforms | REQ-TST-010, REQ-TST-011, REQ-TST-012 | Pending |

### Deliverables
- Fine-tuned embedding model with silhouette score above threshold
- Experiment tracking with full lineage
- Bias report across Fitzpatrick skin types
- Model registered and signed

### Dependencies
- Phase 0 (config, logger), Phase 1 (SCIN data)

---

## Phase 3: Vector Store & RAG Retrieval

**Goal:** Build the multimodal RAG pipeline: index SCIN embeddings in a vector store and
implement retrieval with query-by-image and query-by-text.

**Duration Estimate:** Sprint 5-6

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 3.1 | Select and set up vector store (e.g., ChromaDB, Qdrant, Weaviate) — document decision as ADR | REQ-CST-003 | Pending |
| 3.2 | Build SCIN embedding indexer (`src/pipelines/index_embeddings.py`): embed all SCIN images, store with metadata | REQ-DAT-002 | Pending |
| 3.3 | Implement retrieval service (`src/models/rag_retrieval.py`): query-by-image, query-by-text, hybrid search | — | Pending |
| 3.4 | Add retrieval precision/recall evaluation (`src/evaluation/retrieval_eval.py`) on held-out test set | REQ-OBS-019, REQ-TST-021 | Pending |
| 3.5 | Implement timeouts, retries with backoff for vector store queries | REQ-ERR-003, REQ-ERR-004 | Pending |
| 3.6 | Add graceful degradation: cached results if vector store is temporarily unavailable | REQ-ERR-002 | Pending |
| 3.7 | Log retrieval metadata: query embedding, top-K results, confidence scores, latency | REQ-OBS-027, REQ-OBS-029, REQ-LOG-003 | Pending |
| 3.8 | Integration test: SCIN data -> embeddings -> index -> retrieval -> relevant results | REQ-TST-016, REQ-TST-018 | Pending |
| 3.9 | Create `scripts/index_embeddings.sh` | REQ-RUN-001 | Pending |
| 3.10 | Measure retrieval latency (p50/p95/p99) | REQ-OBS-021, REQ-TST-031 | Pending |

### Deliverables
- Vector store indexed with all SCIN embeddings
- RAG retrieval service with precision/recall metrics
- ADR documenting vector store selection
- Latency benchmarks

### Dependencies
- Phase 2 (fine-tuned embedding model)

---

## Phase 4: Voice Pipeline (Input & Output)

**Goal:** Build the voice-only patient interface: speech-to-text, language detection,
text-to-speech, all via WebRTC.

**Duration Estimate:** Sprint 4-6 (can partially parallel Phase 2-3)

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 4.1 | Set up WebRTC server for camera and audio streaming (`src/pipelines/webrtc_server.py`) | — | Pending |
| 4.2 | Integrate speech-to-text (STT) service (`src/models/stt.py`): support minimum 5 languages | — | Pending |
| 4.3 | Implement language detection (`src/models/language_detection.py`) with confidence thresholds | — | Pending |
| 4.4 | Integrate text-to-speech (TTS) service (`src/models/tts.py`): generate patient explanations in detected language | — | Pending |
| 4.5 | Implement permission-gated image capture: agent asks permission via voice, waits for consent, then captures via WebRTC | — | Pending |
| 4.6 | Validate and sanitize all voice/image inputs before processing | REQ-SEC-002 | Pending |
| 4.7 | Measure voice pipeline latency (p50/p95/p99): STT, language detection, TTS, end-to-end | REQ-OBS-021, REQ-TST-031 | Pending |
| 4.8 | Unit tests: STT on known audio fixtures, language detection accuracy, TTS output format, invalid input handling | REQ-TST-010, REQ-TST-013 | Pending |
| 4.9 | Test language detection accuracy (target >= 95%) across supported languages | REQ-TST-023 | Pending |
| 4.10 | Implement fallback: text-based output if TTS fails | REQ-ERR-002 | Pending |
| 4.11 | Log all voice pipeline events with AI-specific fields | REQ-LOG-003, REQ-LOG-005 | Pending |
| 4.12 | PII/PHI redaction for voice transcriptions in logs | REQ-LOG-006, REQ-OBS-061 | Pending |
| 4.13 | Create `scripts/start_voice_pipeline.sh` | REQ-RUN-001 | Pending |

### Deliverables
- Working voice input/output pipeline with WebRTC
- Language detection with >= 95% accuracy on 5+ languages
- Permission-gated image capture
- Latency benchmarks for conversational flow

### Dependencies
- Phase 0 (config, logger, error handling)
- Independent of Phase 1-3 for basic voice; integrates in Phase 6

---

## Phase 5: Medical AI Agent & SOAP Generation

**Goal:** Integrate MedGemma, build the agentic interview loop, and generate SOAP notes
with ICD code suggestions.

**Duration Estimate:** Sprint 6-8

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 5.1 | Integrate MedGemma model (`src/models/medical_model.py`): load, configure, prompt | REQ-CST-009 | Pending |
| 5.2 | Design and document prompting strategy for all agent roles (interview, SOAP generation, de-escalation, patient explanation) | REQ-CST-010 | Pending |
| 5.3 | Build patient interview agent (`src/pipelines/patient_interview.py`): conversational loop extracting symptoms, filtering noise | — | Pending |
| 5.4 | Implement SOAP note generator (`src/pipelines/soap_generator.py`): S (from transcript), O (from image + RAG), A (ICD codes from MedGemma + RAG), P (guidance) | — | Pending |
| 5.5 | Implement critical case escalation logic: malignancy detection triggers immediate escalation | — | Pending |
| 5.6 | Implement de-escalation logic: paint, tattoo, mild acne scenarios with common-sense questioning | — | Pending |
| 5.7 | Implement "do not play doctor" guardrails: never prescribe, never diagnose definitively, always include disclaimer | REQ-OBS-064, REQ-CST-012 | Pending |
| 5.8 | Implement prompt injection defenses for LLM-facing inputs (voice transcription -> LLM) | REQ-SEC-003 | Pending |
| 5.9 | Build physician case history formatter (`src/pipelines/case_history.py`): formal report with image, SOAP, ICD codes | — | Pending |
| 5.10 | Build patient explanation generator (`src/pipelines/patient_explanation.py`): simple language, voice output | — | Pending |
| 5.11 | Log all prompts and completions in dedicated prompt store | REQ-LOG-004, REQ-LOG-005, REQ-LOG-007 | Pending |
| 5.12 | Redact PII/PHI in all logged prompts and responses | REQ-LOG-006, REQ-OBS-028, REQ-OBS-030 | Pending |
| 5.13 | Tag logs with safety flags (escalation, de-escalation, disclaimer compliance) | REQ-OBS-031, REQ-OBS-047 | Pending |
| 5.14 | Define SOAP note evaluation criteria and scoring rubric | REQ-TST-026 | Pending |
| 5.15 | Create golden test set of prompts with expected SOAP outputs | REQ-TST-027 | Pending |
| 5.16 | Create adversarial prompt suite for policy violation testing | REQ-TST-028 | Pending |
| 5.17 | Implement automatic safety checks for flagged outputs (drug dosages, definitive diagnoses) | REQ-TST-029 | Pending |
| 5.18 | Set timeouts and retries for MedGemma API calls | REQ-ERR-003, REQ-ERR-004 | Pending |
| 5.19 | Log exceptions with full context (request ID, session ID, PII-redacted input) | REQ-ERR-005 | Pending |
| 5.20 | Document all configuration parameters (temperatures, token limits, thresholds) | REQ-CST-013 | Pending |

### Deliverables
- Working patient interview agent with SOAP note generation
- Critical case escalation and de-escalation logic
- Prompt injection defenses
- Golden test set and adversarial prompt suite
- Prompting strategy documented

### Dependencies
- Phase 3 (RAG retrieval), Phase 4 (voice pipeline)

---

## Phase 6: End-to-End Integration

**Goal:** Wire all components together into the complete patient interaction flow and
deploy as a web application (not Streamlit).

**Duration Estimate:** Sprint 8-9

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 6.1 | Build web application server (FastAPI / equivalent) with WebRTC integration | — | Pending |
| 6.2 | Implement end-to-end flow: patient speaks -> language detected -> interview loop -> permission-gated image -> RAG + MedGemma -> SOAP -> physician report + patient explanation (voice) | REQ-TST-020 | Pending |
| 6.3 | Implement session management (`src/utils/session.py`): patient session IDs, state tracking | — | Pending |
| 6.4 | Implement case history delivery to remote healthcare facility | — | Pending |
| 6.5 | Apply rate limiting and throttling to public-facing endpoints | REQ-SEC-007 | Pending |
| 6.6 | Enforce least-privilege access controls for APIs and data stores | REQ-SEC-004 | Pending |
| 6.7 | Implement distributed tracing across all services | REQ-OBS-035 - REQ-OBS-038, REQ-OBS-042 | Pending |
| 6.8 | Collect infrastructure metrics (CPU, GPU, memory, disk, network) per component | REQ-OBS-039 | Pending |
| 6.9 | End-to-end happy-path integration test | REQ-TST-020 | Pending |
| 6.10 | End-to-end error-path tests (errors surface with clear messages and codes) | REQ-TST-019 | Pending |
| 6.11 | Ensure all file paths and configs resolve correctly in CI | REQ-TST-017 | Pending |
| 6.12 | Generate OpenAPI/Swagger documentation for all endpoints | REQ-DOC-005 | Pending |
| 6.13 | Create `scripts/start_server.sh` | REQ-RUN-001 | Pending |
| 6.14 | Update `docs/app_cheatsheet.md` with all URLs, endpoints, operational details | REQ-RUN-002, REQ-RUN-003 | Pending |

### Deliverables
- Fully integrated web application with voice-only patient interface
- Distributed tracing and infrastructure metrics
- OpenAPI documentation
- E2E tests passing

### Dependencies
- Phase 3, Phase 4, Phase 5

---

## Phase 7: Comprehensive Testing

**Goal:** Build out the full test suite: unit, integration, model evaluation, GenAI-specific,
performance/load, bias/fairness, safety, and regression tests.

**Duration Estimate:** Sprint 9-10 (partially ongoing throughout)

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 7.1 | Complete unit test coverage: all preprocessing, feature engineering, serving code, default/fallback behavior | REQ-TST-010 - REQ-TST-015 | Pending |
| 7.2 | Complete integration tests: embedding pipeline, inference pipeline | REQ-TST-016, REQ-TST-018 | Pending |
| 7.3 | Model evaluation tests: define metric thresholds, run against baseline | REQ-TST-021 - REQ-TST-025 | Pending |
| 7.4 | GenAI regression tests: re-run golden prompt suite on each model/prompt change | REQ-TST-030 | Pending |
| 7.5 | Performance/load testing: p50/p95/p99 latency, throughput, scaling, degradation | REQ-TST-031 - REQ-TST-035 | Pending |
| 7.6 | Bias/fairness tests: metrics across Fitzpatrick types, languages, geographies | REQ-TST-036 - REQ-TST-039 | Pending |
| 7.7 | Regulatory/compliance tests: never prescribes, never claims doctor, always gets permission, always includes disclaimer | REQ-TST-050 | Pending |
| 7.8 | Domain-specific acceptance tests: ICD accuracy top-20, SOAP completeness, 100% escalation rate, de-escalation scenarios | REQ-TST-048 | Pending |
| 7.9 | Set up regression CI gate: fail if new versions regress beyond tolerance | REQ-TST-040 | Pending |
| 7.10 | Run unit + integration tests on every commit/PR | REQ-TST-041 | Pending |
| 7.11 | Set up scheduled (nightly/weekly) evaluation pipeline for model quality, safety | REQ-TST-042, REQ-CIC-002 | Pending |
| 7.12 | Document promotion criteria: required tests and thresholds for staging -> production | REQ-TST-043 | Pending |
| 7.13 | Record library versions, configs, artifacts for failed runs | REQ-TST-045 | Pending |
| 7.14 | Maintain test catalog with risk mapping | REQ-TST-046 | Pending |
| 7.15 | Link tests to runbooks for debugging common failures | REQ-TST-047 | Pending |

### Deliverables
- Full test suite with > 80% code coverage
- Bias report with Fitzpatrick type breakdown
- Regulatory compliance test suite
- CI gates preventing regressions

### Dependencies
- Phase 6 (fully integrated system to test)

---

## Phase 8: Observability, Monitoring & Alerting

**Goal:** Build dashboards, alerts, runbooks, and production monitoring across all
dimensions (data, model, infrastructure, safety).

**Duration Estimate:** Sprint 10-11

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 8.1 | Set up centralized log aggregation (e.g., Loki, ELK, CloudWatch) | REQ-OBS-033 | Pending |
| 8.2 | Configure log retention and access policies for medical data | REQ-OBS-034, REQ-OBS-062 | Pending |
| 8.3 | Build model performance dashboard: task metrics, business KPIs, latency, by-segment views | REQ-OBS-019 - REQ-OBS-026 | Pending |
| 8.4 | Build data quality dashboard: schema checks, distribution drift, null/invalid rates | REQ-OBS-012 - REQ-OBS-018 | Pending |
| 8.5 | Implement prediction logging: ICD codes, confidence, escalation decisions, retrieval results | REQ-OBS-027 - REQ-OBS-032 | Pending |
| 8.6 | Implement explainability: which SCIN images retrieved, which features drove ICD suggestion | REQ-OBS-043, REQ-OBS-044 | Pending |
| 8.7 | Build bias monitoring dashboard: metrics per Fitzpatrick type, per language, per region | REQ-OBS-045, REQ-OBS-046 | Pending |
| 8.8 | Implement safety evaluators: "do not play doctor" compliance, escalation accuracy | REQ-OBS-047, REQ-OBS-048 | Pending |
| 8.9 | Define alert thresholds for: data drift, model perf drops, latency spikes, safety incidents | REQ-OBS-049 - REQ-OBS-052 | Pending |
| 8.10 | Create runbooks for each alert type: root causes, immediate actions, escalation paths | REQ-OBS-053 | Pending |
| 8.11 | Monitor container health, restarts, queue lengths | REQ-OBS-040, REQ-OBS-041 | Pending |
| 8.12 | Implement audit trail: reconstruct which model, data, config produced any prediction | REQ-OBS-063 | Pending |
| 8.13 | Create red-team evaluation dataset and adversarial scenarios | REQ-OBS-065 | Pending |
| 8.14 | Document governance and regulatory reporting requirements | REQ-OBS-066 | Pending |
| 8.15 | Wire production monitoring dashboards into `app_cheatsheet.md` | REQ-RUN-003 | Pending |

### Deliverables
- Centralized logging with medical data access controls
- Dashboards for model performance, data quality, bias, safety
- Alert rules with runbooks
- Audit trail for prediction provenance

### Dependencies
- Phase 6 (running system to monitor)

---

## Phase 9: CI/CD & Deployment

**Goal:** Automate the full build-test-deploy pipeline to staging and production with
quality gates, smoke tests, and rollback capability.

**Duration Estimate:** Sprint 11-12

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 9.1 | Containerize the application (Dockerfile + docker-compose) | REQ-DEP-002 | Pending |
| 9.2 | Extend GitHub Actions pipeline: lint -> type-check -> unit tests -> integration tests -> build | REQ-CIC-001, REQ-CIC-005 | Pending |
| 9.3 | Add scheduled nightly/weekly evaluation pipeline (model quality, bias, safety) | REQ-CIC-002 | Pending |
| 9.4 | Automate deployment to staging via pipeline (no manual steps) | REQ-CIC-003 | Pending |
| 9.5 | Automate deployment to production with canary/shadow strategy | REQ-CIC-003, REQ-OBS-057 | Pending |
| 9.6 | Add post-deploy smoke tests: voice processing, image capture, RAG retrieval, SOAP generation, case history delivery | REQ-CIC-004 | Pending |
| 9.7 | Implement model version comparison gate: compare old vs. new before promotion | REQ-OBS-058 | Pending |
| 9.8 | Implement quick rollback to prior model version | REQ-OBS-059 | Pending |
| 9.9 | Scan container images for vulnerabilities in CI | REQ-SEC-005 | Pending |
| 9.10 | Schedule periodic security review cadence | REQ-SEC-008 | Pending |
| 9.11 | Wire doc-drift detection into CI (flag stale docs) | REQ-DLP-002 | Pending |
| 9.12 | Define sign-off gates for infra changes and production deployments | REQ-DLP-007 | Pending |

### Deliverables
- Fully automated CI/CD from commit to production
- Canary deployments with automated rollback
- Post-deploy smoke tests
- Container vulnerability scanning in CI

### Dependencies
- Phase 7 (test suite for CI gates), Phase 8 (monitoring for canary validation)

---

## Phase 10: Documentation Generation

**Goal:** Produce all required documents per the documentation requirements controller:
architecture overview, design spec, deployment runbook, and PRD.

**Duration Estimate:** Sprint 11-12 (parallel with Phase 9)

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 10.1 | Create document templates (consistent sections, headings, tables) | REQ-ADO-001 | Pending |
| 10.2 | Produce Architecture Overview with C4 context + container diagrams (Mermaid) | REQ-ADO-002, REQ-ADO-003, REQ-CST-015, REQ-CST-016 | Pending |
| 10.3 | Produce Design Specification: module responsibilities, interfaces, data models, error handling, NFR constraints | REQ-ADO-004 | Pending |
| 10.4 | Produce Deployment & Operational Runbook: environments, infra topology, CI/CD, config, scaling, SLOs | REQ-ADO-005, REQ-DOC-003 | Pending |
| 10.5 | Produce PRD/SRS Hybrid: user goals, functional reqs, quality attributes, acceptance criteria, dependencies | REQ-ADO-006 | Pending |
| 10.6 | Write docstrings for all public modules, classes, and functions | REQ-DOC-001 | Pending |
| 10.7 | Create Architecture Decision Records (ADRs): WebRTC, SCIN, contrastive loss, MedGemma/SigLIP-2, vector store | REQ-CST-003 | Pending |
| 10.8 | Build traceability matrix: requirements -> arch drivers -> design decisions | REQ-CST-001, REQ-CST-002 | Pending |
| 10.9 | Document NFR-to-design mapping: performance budgets, reliability targets, security boundaries | REQ-CST-004 - REQ-CST-008 | Pending |
| 10.10 | Document LLM/agent specifics: model versions, prompting strategy, tools, safety policies, config params | REQ-CST-009 - REQ-CST-014 | Pending |
| 10.11 | Create project glossary (SOAP, ICD, SCIN, Fitzpatrick, PHI, PII, RAG, WebRTC) | REQ-DLP-005 | Pending |
| 10.12 | Initialize changelog (CHANGELOG.md) | REQ-DOC-004 | Pending |
| 10.13 | Create troubleshooting guide | REQ-AGT-004 | Pending |
| 10.14 | Define document sign-off authority (project lead, medical advisor, security reviewer) | REQ-DLP-006 | Pending |

### Deliverables
- Architecture Overview (C4 diagrams in Mermaid)
- Design Specification
- Deployment & Operational Runbook
- PRD/SRS Hybrid
- ADRs, traceability matrix, glossary, changelog

### Dependencies
- Phase 6 (architecture solidified), Phase 9 (deployment finalized)

---

## Phase 11: Hardening & Production Readiness

**Goal:** Final hardening: security review, bias audit, compliance checks, load testing,
and documentation sign-off.

**Duration Estimate:** Sprint 12-13

### Tasks

| # | Task | Reqs Covered | Status |
|---|------|-------------|--------|
| 11.1 | Full security review: prompt injection, input validation, access controls, secret handling | REQ-SEC-001 - REQ-SEC-008 | Pending |
| 11.2 | Full bias audit: Fitzpatrick type analysis, language fairness, geographic equity | REQ-TST-036, REQ-OBS-045 | Pending |
| 11.3 | Regulatory compliance verification: "do not play doctor" enforcement, consent workflows | REQ-TST-050 | Pending |
| 11.4 | Load testing at target concurrency; validate scaling and graceful degradation | REQ-TST-033 | Pending |
| 11.5 | Test all alerts and runbooks (game day / chaos drill) | REQ-OBS-054 | Pending |
| 11.6 | Final document review and sign-off cycle | REQ-GEN-005, REQ-DLP-006, REQ-DLP-007 | Pending |
| 11.7 | Produce Validation / Open Issues sections in all documents | REQ-GEN-007 | Pending |
| 11.8 | Consistency check: all documents vs. original requirements | REQ-GEN-008 | Pending |
| 11.9 | Wire custom production dashboards and "tests in production" alerts | REQ-TST-049 | Pending |
| 11.10 | Final `app_cheatsheet.md` update with all production URLs and operational details | REQ-RUN-002, REQ-RUN-003 | Pending |

### Deliverables
- Security review report
- Bias audit report
- Compliance verification report
- All documents signed off
- Production-ready system

### Dependencies
- All previous phases

---

## Cross-Cutting Concerns (Applied Throughout All Phases)

These requirements are not phase-specific but must be applied continuously:

| Concern | Reqs | Applied In |
|---------|------|------------|
| Structured logging with AI fields | REQ-LOG-001 - REQ-LOG-003 | Every module |
| PII/PHI redaction in logs | REQ-LOG-006, REQ-OBS-061 | Every module touching patient data |
| Prompt/completion logging | REQ-LOG-004, REQ-LOG-005, REQ-LOG-007 | Every LLM call |
| Log level discipline | REQ-LOG-008 - REQ-LOG-011 | Every module |
| Logger injection pattern | REQ-LOG-014 | Every library/package |
| AI coding workflow logging | REQ-LOG-015 - REQ-LOG-018 | During development |
| Exception logging with context | REQ-ERR-005 | Every module |
| Timeouts + retries for external calls | REQ-ERR-003, REQ-ERR-004 | Every external call |
| Implementation plan updates | REQ-AGT-002, REQ-AGT-003 | After every phase |
| Plan-first documentation | REQ-GEN-001 | Before every document |
| Iterative doc refinement | REQ-GEN-002 - REQ-GEN-004 | Every doc update |
| Human checkpoints | REQ-GEN-005, REQ-GEN-006 | After every phase |
| Self-checks in docs | REQ-GEN-007, REQ-GEN-008 | Every document |
| Separation of concerns (code vs docs) | REQ-GEN-009 | Always |
| Docs stored in repo | REQ-DLP-001 | Always |
| Doc cache & reuse | REQ-DLP-004 | Every doc generation |
| Consistent terminology | REQ-DLP-005 | Every document |

---

## Phase Dependency Graph

```
Phase 0 (Foundation)
  ├── Phase 1 (Data Pipeline)
  │     └── Phase 2 (Embedding & Fine-Tuning)
  │           └── Phase 3 (Vector Store & RAG)
  │                 └──┐
  ├── Phase 4 (Voice)  │
  │     └──────────────┤
  │                    └── Phase 5 (Medical AI Agent)
  │                          └── Phase 6 (E2E Integration)
  │                                ├── Phase 7 (Testing)
  │                                ├── Phase 8 (Observability)
  │                                │     └──┐
  │                                └────────┤
  │                                         └── Phase 9 (CI/CD & Deployment)
  Phase 10 (Documentation) ←── Phases 6, 9
  Phase 11 (Hardening) ←── All phases
```

**Parallelizable:** Phase 4 (Voice) can run in parallel with Phases 1-3 (Data/Embedding/RAG).
Phase 10 (Documentation) can partially parallel Phase 9 (CI/CD).

---

## Requirements Traceability Summary

| Controller | Total Reqs | Covered in Plan | Coverage |
|-----------|-----------|----------------|----------|
| common_requirements_controller.json | 116 | 116 | 100% |
| documentation_requirements_controller.json | 41 | 41 | 100% |
| **Total** | **157** | **157** | **100%** |

---

## Open Questions

1. **SCIN Database Access:** How is the SCIN database obtained? Is there a license/DUA required?
2. **MedGemma Access:** Is MedGemma available via API or requires local hosting with GPU?
3. **Deployment Target:** Cloud provider preference (AWS/GCP/Azure) for staging/production?
4. **Language Priority:** Which 5 languages are the minimum for initial release?
5. **Physician Delivery:** How are case histories delivered to remote healthcare facilities (email, API, portal)?
6. **Hardware Spec:** What is the exact kiosk hardware spec at frontier villages (CPU, RAM, network)?
7. **Regulatory:** Which countries are initial deployment targets? What are their local medical regulations?
8. **Budget:** Are there GPU budget constraints for hosting MedGemma and SigLIP-2?

---

## Validation

- [ ] All 116 common requirements mapped to at least one phase task
- [ ] All 41 documentation requirements mapped to at least one phase task
- [ ] All phases have clear dependencies and deliverables
- [ ] Open questions documented for stakeholder resolution
- [ ] Plan follows REQ-AGT-002 (detailed implementation plan before coding)
