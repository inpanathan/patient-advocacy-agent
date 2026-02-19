# Project Specification for The Patient Advocacy Agent

## 1. Goal

The project is to create an agentic system that functions as a "Patient Advocate".

### Motivation and Narrative

The target audience is frontier villages in the Global South, where the physician-to-patient ratio
can be worse than 1:1000 or even 1:10,000.

### Story: Primary Care Units

In many such areas, the government establishes primary care units staffed with employees
(e.g., a compounder, nurse, physician). However, the defining quality of these units is that
"government opens them, employees close the door". The staff disappears, drawing free
salaries, leaving the facility locked.

The project aims to create an accessible unit (a camera, microphone, and speaker) to provide
sensible dermatological guidance. This project is designed to be one of social utility. This aligns
with the objective from MIT, whose motto ("Ma's moto") is "technology and the service of
mankind". The goal is to build a project of actual, tangible value that could be deployed to
make an impact.

## 2. Deliverables

### Required Outputs

The agent's job is to create a complete case history, delivered in two versions:

- **For the Physician:** A formal case history (including the stored image) sent to a remote
  healthcare facility.
- **For the Patient:** An explanation in simple, layman's language (via voice) detailing the
  options and plan.

### Interface and Technical Requirements

- **Interface:** The patient interface must be voice-only. No text typing.
- **Rationale:** The target user base is presumed to be illiterate. Illiteracy is no longer a
  handicap in a world with microphones and cameras.
- **Language:** Must support a minimum of 5 languages, including language detection. The
  ambitious goal is 100 languages.
- **Privacy:** The agent must explicitly ask for and receive permission before taking a picture
  ("permission-gated pictures").
- **Standard:** Do not use a Streamlit interface. The goal is a real product deployed on the
  web.
- **Technology:** This is a classic agentic RAG project requiring multimodal search.
  - Use WebRTC for the camera.
  - Use the SCIN database from Harvard University (2GB of text and images) for RAG.
  - Use models like MedGemma and SigLIP-2.

### Advanced Methodology

Fine-tune the multimodal embedding model for the retrieval system.

- **Training Method:** The training should be conducted using a contrastive loss
  function.
- **Goal (Isotropy):** The objective is to achieve a more isotropic distribution of the
  embeddings within the unit hypersphere. This separation of concepts in the vector
  space leads to better and more reliable retrieval results.
- **Testing Method (Clustering):** A tangible method to test the correctness of the
  embedding model is to run clustering on the resulting image embeddings. A
  successful, well-trained embedding model will demonstrate that images of the same
  diagnosis (e.g., all images of eczema) naturally cluster together in the embedding
  hyperspace.

## 3. High-Level Requirements

### Core Rule: Do Not Play Doctor

This is the most critical rule. The system is not a doctor. The unauthorized practice of medicine
is illegal. The agent's role is to provide guidance where none currently exists and act as a
"patient advocate," similar to a nurse's assistant who remotely prepares a case history.

### Medical Framework: SOAP

The agent will follow the medical SOAP (Subjective, Objective, Assessment, Plan) framework.

- **S (Subjective):** The patient's narrative, captured via voice. The agent must filter medically
  relevant information (e.g., "itching") from irrelevant noise (e.g., "my child was crying").
- **O (Objective):** The medically relevant information, including a picture of the skin condition.
- **A (Assessment):** An evaluation of what the condition could be, presented as a set of
  possible ICD codes with supporting evidence.
- **P (Plan):** Contextual guidance for the patient in a remote village. This must include
  transportation directions, urgency, and what to expect.

## 4. Scope and Common Sense

The system must balance guidance with the "do not play doctor" rule.

- **Critical Cases:** If a malignancy is suspected, the agent must urge immediate action.
- **Non-Critical Cases (De-escalation):** The system must have a list of critical conditions. If
  the issue does not match, it can de-escalate.
  - **Example (Blue Paint):** If it looks like paint, the agent should interrogate: "Did you try
    washing your hand?".
  - **Example (Tattoo):** The agent must be smart enough to ask, "Is that a tattoo?".
  - **Example (Mild Acne):** Reassuring a teenager that it is just acne is a valuable service.
    Suggesting "take a bath with Lifebuoy soap" is acceptable local advice, not a medical
    prescription.

The agent's role is to do the leg work for the patient: gather information, connect them to a
provider, and arrange logistics.

## 5. Success Metrics

Quantifiable targets that determine project success.

- **Case Completion Rate:** Percentage of patient interactions that produce a complete SOAP
  note and physician case history.
- **Referral Accuracy:** Percentage of cases where the suggested ICD codes match a
  physician's subsequent diagnosis (measured via feedback loop).
- **Language Detection Accuracy:** Minimum 95% correct language identification across
  supported languages.
- **Critical Case Escalation Rate:** 100% of suspected malignancies must trigger an
  immediate escalation recommendation.
- **SOAP Note Generation Time:** End-to-end time from patient interaction start to completed
  SOAP note, target under 10 minutes.
- **Embedding Clustering Quality:** Images of the same diagnosis must cluster with a
  silhouette score above a defined threshold after fine-tuning.

## 6. Agent Interaction & Workflow

### 6.1 Workflow and Planning

- Use the README.md as the anchor for all project documentation and link to other documents
  from it.
- Always create a detailed implementation plan with steps and sub-steps before coding any
  feature.
- As implementation progresses, keep updating the plan with status so that if the session is
  interrupted, a new session can pick up where the previous one left off.

### 6.2 Troubleshooting Documentation

- Document all troubleshooting commands suggested and executed by the agent or developer
  in a persistent troubleshooting log.

## 7. Logging

### 7.1 Log Content and Structure

- Use structured logs (JSON or key-value format) queryable by fields such as `request_id`,
  `patient_session_id`, `language`, and `model`.
- Include consistent core fields in every log entry: `timestamp`, `level`, `service`,
  `request_id`, `trace_id`.
- Add AI-specific fields where relevant: `prompt_id`, `model` (e.g., MedGemma, SigLIP-2),
  `temperature`, `token_count_in`, `token_count_out`, `latency_ms`.

### 7.2 Prompt and AI Interaction Logging

- Log prompts and completions in a dedicated store (e.g., SQLite or JSONL pipeline) for
  analysis and quality improvement.
- Attach logs close to the client that calls the AI so every completion is recorded, including
  SOAP generation prompts and patient explanation prompts.
- Redact or hash sensitive data (patient names, location details, medical images, PII/PHI)
  before logs leave the application boundary.
- Separate "prompt analytics" logs (for refinement and UX) from operational logs (for
  debugging and monitoring).

### 7.3 Levels, Volume, and Performance

- Use standard log levels consistently: `DEBUG`, `INFO`, `WARN`, `ERROR`.
- Keep AI call traces at `INFO`, but only enable full prompt/response bodies at `DEBUG` to
  manage log volume.
- Add level checks or guards so expensive debug logs (e.g., full image embeddings) are not
  computed on hot paths.
- Sample high-volume events (e.g., repeated language detection calls) instead of logging
  every one.

### 7.4 Standardization

- Centralize logging through a shared logger utility; no scattered `print()` statements.
- Use AI to sweep and standardize logs (e.g., convert ad-hoc prints to structured log calls).
- For libraries and internal packages, accept a logger interface instead of instantiating a
  logger directly.

### 7.5 AI-Assisted Coding Workflow

- When using an AI coding assistant, log key lifecycle events: suggestion requested, accepted,
  rejected, modified.
- Correlate these events with code locations (file, function, line span) for traceability.
- For agentic workflows that refactor logging itself, log the agent's actions and rationale.
- In debugging sessions where AI inspects logs, treat the AI as a read-only consumer with no
  write access to production data.

## 8. Observability

### 8.1 Scope and Goals

- Define business goals and success metrics for the model/system (see Section 5).
- Define which components are in scope for observability: voice input pipeline, language
  detection, SOAP generation, image capture (WebRTC), RAG retrieval (SCIN database),
  embedding model (SigLIP-2), medical model (MedGemma), case history delivery, and
  patient explanation (voice output).
- Document owners (teams/people) responsible for each part of the stack.

### 8.2 Model Registry, Versioning, and Lineage

- Use a versioned model registry for all deployable models (MedGemma, SigLIP-2,
  fine-tuned embedding model, language detection model).
- For each model version, record:
  - Training dataset reference (SCIN database version, snapshot timestamp).
  - Model code version (commit hash, container image).
  - Hyperparameters and training configuration (contrastive loss parameters, learning rate,
    batch size, isotropy targets).
  - Evaluation metrics on validation/test sets (clustering silhouette score, retrieval
    precision/recall, ICD code accuracy).
- Track data inputs/outputs across pipelines for lineage.
- Track environment information (runtime, libraries, CUDA version, GPU type).
- Track pipeline parameter configuration linked to model versions.

### 8.3 Data Observability

- Validate data schema (types, required fields, ranges) for SCIN database ingestion and
  patient input data.
- Monitor for missing values, outliers, and invalid categories in training and inference data.
- Monitor feature freshness and lag for any streaming/online components.
- Compare live input distributions (e.g., skin condition types, patient demographics) to
  training baselines.
- Monitor output distributions (ICD code predictions, escalation rates) for drift.
- Set alerts for significant schema changes and large distribution shifts or spikes in
  null/invalid rates.

### 8.4 Model Performance Monitoring

- Define task metrics: retrieval precision/recall for RAG, ICD code prediction accuracy,
  SOAP note completeness score, clustering silhouette score for embeddings.
- Define business KPIs: case completion rate, referral accuracy, critical case escalation rate,
  patient satisfaction (if feedback is collected).
- Measure latency and throughput (p50/p95/p99) for voice processing, RAG retrieval, SOAP
  generation, and end-to-end interaction.
- Track metrics by cohort/segment: by language, by skin condition category, by region, by
  Fitzpatrick skin type.
- For GenAI/LLM components, track prompt-response quality scores (human or automated
  evaluation) and safety issues (hallucination, PII leaks, inappropriate medical advice).
- Configure dashboards and alerts for performance degradation and latency/error rate
  regressions.

### 8.5 Logging (Inputs, Outputs, and Decisions)

- Log inference request metadata (timestamps, session IDs, model version) for every patient
  interaction.
- Log key features or feature summaries (with PII/PHI redacted or pseudonymized).
- Log predictions, confidence scores, and decision outcomes (ICD codes suggested,
  escalation decisions, de-escalation rationale).
- For LLM/GenAI components, log prompt, context, and response with redaction of patient
  identifiers.
- Tag logs with safety flags, user feedback, and evaluation scores.
- Ensure all logs are structured (JSON), centralized, queryable, and governed by retention and
  access policies appropriate for medical data.

### 8.6 Tracing and Infrastructure Metrics

- Implement distributed tracing across: voice input/WebRTC gateway, language detection
  service, RAG retrieval service (SCIN), model inference service (MedGemma/SigLIP-2),
  SOAP generation service, case history delivery, and patient voice output.
- Collect CPU, GPU, memory, disk, and network usage metrics for each component.
- Monitor container/pod restarts and health checks.
- Monitor queue lengths and backlog for any batch/stream pipelines.
- Link traces and metrics to model versions and patient session requests.

### 8.7 Explainability, Bias, and Safety

- Provide local explanations for individual predictions (e.g., which SCIN images were
  retrieved, which features drove the ICD code suggestion).
- Provide global insights into feature importance and model behavior.
- Compare performance across Fitzpatrick skin types (I-VI), languages, and geographic
  regions for bias monitoring. Dermatological AI bias against darker skin tones is a known
  critical risk.
- Log and track bias metrics pre- and post-deployment as part of model cards.
- Monitor for harmful or policy-violating content using safety evaluators (e.g., unauthorized
  medical advice, failure to escalate critical cases).
- Log safety incidents and mitigation actions for audit.

### 8.8 Alerting and Runbooks

- Define alert thresholds for: data quality and drift events, model performance drops,
  latency/error spikes, safety/bias incidents.
- Create runbooks for each alert type specifying possible root causes, immediate actions, and
  escalation paths.
- Test alerts and runbooks periodically (game days / chaos drills).

### 8.9 Experiment Tracking and Deployment

- Track experiment hyperparameters, datasets, seeds, and code versions for all embedding
  fine-tuning and model training runs.
- Store metrics and artifacts per run in a central tracking system (e.g., MLflow, Weights &
  Biases).
- Use canary / shadow / A-B deployments for new models or prompts.
- Compare metrics between old and new versions before full promotion.
- Ensure rollback is quick and traceable to a specific prior model version.

### 8.10 Compliance, Privacy, and Auditability

- Document data sources (SCIN database from Harvard, patient voice recordings, patient
  images), data use policies, and consent requirements.
- Enforce PII/PHI handling and redaction rules in all logs, datasets, and case histories.
  Patient voice recordings and medical images are protected health information.
- Enforce access controls for observability tools and raw logs containing medical data.
- Ensure you can reconstruct "which model, data, and config produced this prediction" for
  any given patient case history.

### 8.11 Project-Specific Observability

- Define domain-specific checks: critical case escalation accuracy, "do not play doctor"
  compliance monitoring, de-escalation appropriateness (e.g., correctly identifying paint,
  tattoos, mild acne).
- Create custom evaluation datasets and red-team scenarios for the patient advocacy agent
  (e.g., adversarial inputs mimicking serious conditions, edge cases in language detection,
  culturally sensitive scenarios).
- Document any additional governance or reporting needs (e.g., government health authority
  reporting requirements in target deployment regions).

## 9. Testing

### 9.1 Scope and Objectives

- **Primary Model Use Case:** Dermatological triage via voice-only interface with image
  capture, producing SOAP-formatted case histories.
- **Critical Risks:** Data quality of SCIN database, bias across skin tones, medical safety
  (missed malignancies), embedding drift, voice processing latency, language detection
  failures, prompt injection via voice input.
- **Test Environments:** dev (local), staging (cloud replica), production shadow (mirrored
  traffic without patient impact).

### 9.2 Data and Schema Testing

- Validate SCIN database schema: column names, types, required fields (image data,
  diagnosis labels, ICD codes, metadata).
- Enforce allowed ranges and categorical domains for ICD codes, Fitzpatrick types, and
  condition categories.
- Check for missing values and invalid values per feature in SCIN data and patient input.
- Detect duplicates and obvious outliers in training data.
- Compare basic stats (mean, std, quantiles) of incoming patient data vs. training baselines
  for distribution drift.
- Alert when drift exceeds defined thresholds.

### 9.3 Unit Tests (Code-Level)

- Test individual preprocessing transforms: audio-to-text transcription, language detection,
  image preprocessing, embedding generation.
- Assert shape, type, and invariants (e.g., normalized embedding vectors on the unit
  hypersphere) for all transforms.
- Cover metrics (contrastive loss function, clustering silhouette score), loss functions, and
  custom logic in utility functions.
- Ensure proper error handling for invalid inputs: corrupted images, unintelligible audio,
  unsupported languages, empty inputs.
- Test request parsing and response formatting in inference/serving code (WebRTC payloads,
  SOAP note format, case history format).
- Verify default values and fallback behavior when optional inputs are missing.
- Safety disclaimers (e.g., "not a doctor") should be tested at the session level, not
  per-response. For voice-first interfaces with illiterate users, repeating legal disclaimers
  every turn degrades UX.
- Do not rely on small LLMs (e.g., 4B parameter models) to track conversational state
  implicitly. Use explicit state tracking (keyword extraction, topic checklists) and test that
  answered topics are not re-asked.
- ICD code validators must cover multiple ICD chapters. Dermatological conditions appear in
  Chapter XII (L-codes for skin), Chapter I (B-codes for fungal infections), Chapter II
  (C-codes for neoplasms), and others.

### 9.4 Integration and End-to-End Tests

- Verify the embedding fine-tuning pipeline ("load SCIN data -> preprocess -> train with
  contrastive loss -> evaluate clustering") works on a small fixture dataset.
- Ensure all file paths and configs resolve correctly in CI.
- Verify the inference pipeline ("voice input -> language detection -> transcription -> RAG
  retrieval -> SOAP generation -> case history output") works with test inputs.
- Ensure errors surface with clear messages and appropriate status codes.
- Verify the full end-to-end happy path ("patient speaks -> image captured with permission ->
  SOAP note generated -> physician report sent -> patient explanation spoken") in a
  production-like environment.

### 9.5 Model Evaluation Tests

- Define target metrics and minimum thresholds: retrieval precision/recall for RAG,
  embedding clustering silhouette score, ICD code suggestion accuracy, SOAP note
  completeness.
- Lock in a baseline model (pre-fine-tuned SigLIP-2) for regression comparison.
- Evaluate metrics across key segments: per language, per Fitzpatrick skin type, per
  condition category.
- Run invariance tests: label-preserving perturbations (e.g., image rotation, lighting changes)
  should keep predictions stable.
- Run directional expectation tests: known changes (e.g., adding a rash symptom) should
  move predictions in expected directions.

### 9.6 Special Tests for GenAI / LLM Systems

- Define evaluation criteria for SOAP note quality: medical relevance, completeness,
  appropriate language level for patient explanations, ICD code accuracy.
- Maintain a curated set of prompts with expected qualities or reference outputs (golden
  test set).
- Create prompt suites to probe for policy violations: giving specific medical prescriptions,
  diagnosing without caveats, failing to escalate critical cases, leaking PII/PHI.
- Implement automatic checks or human review for flagged outputs (e.g., outputs that
  mention specific drug dosages).
- Re-run the core prompt suite on each major model/prompt change and compare scores to
  the baseline.

### 9.7 Performance, Load, and Reliability Testing

- Measure p50/p95/p99 latency under realistic load for: voice-to-text transcription, RAG
  retrieval, SOAP generation, end-to-end patient interaction. Voice-only interface demands
  low latency for conversational flow.
- Test throughput vs. target QPS and record resource usage (CPU, GPU, memory).
- Validate scaling behavior and graceful degradation under peak load (e.g., multiple
  concurrent patient sessions).
- Confirm rate limiting and backpressure mechanisms on public-facing endpoints.
- Test timeouts, partial failures, and fallback strategies (e.g., cached responses if RAG is
  temporarily unavailable, text fallback if voice synthesis fails).

### 9.8 Bias, Fairness, and Safety

- Compare retrieval accuracy and ICD code suggestion accuracy across Fitzpatrick skin
  types (I-VI). Dermatological AI has documented bias against darker skin tones; this is a
  critical test category.
- Document observed disparities and mitigation steps.
- Test domain-specific safety scenarios: missed malignancy escalation, inappropriate
  de-escalation of serious conditions, incorrect "do not play doctor" boundary enforcement.
- Check for harmful failure modes: worst-case behavior when the system encounters
  conditions outside the SCIN database, adversarial voice inputs, and ambiguous images.

### 9.9 Regression and CI/CD Integration

- Capture baseline metrics and behaviors; fail CI if new versions regress beyond an allowed
  tolerance.
- Run unit and key integration tests on every commit/PR.
- Run heavier evaluation tests (model accuracy, bias, safety) on scheduled or pre-release
  pipelines.
- Document required tests and thresholds for promoting a model to staging and production.

### 9.10 Reproducibility and Documentation

- Fix random seeds for all tests and training runs under test.
- Record library versions, configs, and model artifacts for failed runs to enable debugging.
- Maintain a catalog of tests (data, model, safety, performance) and what risks each test
  addresses.
- Link tests to runbooks for debugging common failures.

### 9.11 Project-Specific Tests

- Define dermatology-specific acceptance tests: ICD code accuracy for top-20 conditions in
  the SCIN database, SOAP note completeness scoring, critical case escalation rate
  (must be 100%), de-escalation appropriateness (paint, tattoo, mild acne scenarios).
- Wire custom dashboards and alerts into monitoring for "tests in production" (live case
  quality scoring).
- Implement regulatory/compliance-driven tests: verify the system never prescribes
  medication, never claims to be a doctor, always obtains image permission, always includes
  the "seek professional help" disclaimer.

## 10. Running the Application

- Create scripts for starting and running the application and place those scripts in the
  `scripts/` directory. This includes scripts for: starting the web server, launching the voice
  pipeline, initializing the RAG index, and running the embedding fine-tuning pipeline.
- Document how to run these scripts in a file named `app_cheatsheet.md`.
- Add all necessary URLs (web interface, API endpoints, model registry, monitoring
  dashboards, SCIN database location) and other operational details in the
  `app_cheatsheet.md`.
- When using FastAPI with a `create_app()` factory pattern, uvicorn requires the `--factory`
  flag and a function reference (e.g., `main:create_app`), not an attribute reference
  (`main:app`).
- Document gated HuggingFace model prerequisites in the deployment runbook: license
  acceptance on the model page, `huggingface-cli login` with a read-scoped token, then the
  download script. Include a troubleshooting table for common HuggingFace errors.

## 11. Security

- Store secrets (API keys for LLM providers, database credentials, model registry tokens) in
  a secrets manager or environment variables. Never commit secrets to the repository.
- Validate and sanitize all external inputs before processing: voice audio streams, uploaded
  images, WebRTC signaling data.
- Implement prompt injection defenses for LLM-facing inputs. The agent takes free-form
  patient voice input that is transcribed and fed to LLMs; this is a prompt injection attack
  surface.
- Enforce least-privilege access controls for services, APIs, and data stores. Medical data
  (images, case histories, voice recordings) requires strict access control.
- Scan container images and dependencies for known vulnerabilities before deployment.
- Sign and verify model artifacts (MedGemma, SigLIP-2, fine-tuned embedding models) to
  prevent tampering.
- Apply rate limiting and throttling to public-facing endpoints. The system is intended for
  web deployment.
- Conduct periodic security reviews and penetration testing, with special attention to medical
  data exposure risks.

## 12. Configuration Management

- Use layered configuration (defaults, environment overrides) with a single entry point
  (e.g., a `config.yaml` or environment-based settings module).
- Separate configuration per environment (dev, staging, production) without code changes.
- Validate all configuration values at startup and fail fast on invalid settings (e.g., missing
  model paths, invalid API keys, unsupported language codes).
- Version-control all hyperparameters and experiment configurations (contrastive loss
  parameters, embedding dimensions, clustering thresholds, model temperatures, token
  limits) alongside code.
- Use feature flags for incremental rollout of new capabilities (e.g., new language support,
  updated models, new de-escalation scenarios).
- When using Gemma-family models (MedGemma), always load with `bfloat16` precision, not
  `float16`. `float16` has only 5 exponent bits, causing logits to overflow to NaN/inf during
  sampling. `bfloat16` has the same exponent range as float32 with the memory savings of
  float16.
- Model factories (STT, TTS, medical model) must use singleton/caching patterns. Multiple
  module-level instantiations will load duplicate models, exhausting GPU memory.
- When changing a port number, grep the entire project for the old value. Port references
  appear in `.env`, config files, docker-compose, frontend proxy settings, scripts, and
  documentation.

## 13. Error Handling and Resilience

- Define a consistent error response format across all services and APIs (voice pipeline, RAG
  service, SOAP generation, case history delivery).
- Implement graceful degradation: fallback responses if the LLM is unavailable, cached
  retrieval results if the SCIN index is temporarily down, text-based output if voice
  synthesis fails.
- Set explicit timeouts for all external calls: LLM API calls, RAG retrieval queries, WebRTC
  signaling, case history delivery to remote healthcare facilities.
- Use retries with exponential backoff and jitter for transient failures (network issues, API
  rate limits, temporary model server unavailability).
- Log all exceptions with full context (stack trace, request ID, patient session ID, input
  summary with PII redacted) for post-incident analysis.
- Add CUDA out-of-memory detection with graceful fallback to CPU when multiple models (STT,
  TTS, medical) compete for a single GPU.
- Set connection timeouts on database pools. A missing or unreachable database causes
  requests to hang silently with no error returned to the client.
- API endpoints that advance conversational state (e.g., greeting to interview) must
  explicitly update the state machine. Do not rely on downstream handlers to infer state.

## 14. Dependency Management

- Pin all dependency versions in lock files (e.g., `requirements.txt`, `poetry.lock`,
  `package-lock.json`) for reproducible builds.
- Use virtual environments or containers to isolate project dependencies.
- Run automated vulnerability scanning on dependencies (e.g., `pip-audit`, `npm audit`,
  `trivy`) on a regular schedule.
- Document system-level requirements: OS packages, GPU drivers, CUDA versions required
  for MedGemma and SigLIP-2, audio processing libraries, WebRTC dependencies.

## 15. Documentation Standards

- Write docstrings for all public modules, classes, and functions.
- Maintain an architecture document describing system components, data flow, and
  integration points (voice pipeline, RAG, LLM, WebRTC, case history delivery).
- Create operational runbooks for deployment, rollback, and incident response.
- Keep a changelog that records notable changes, migrations, and breaking changes per
  release.
- Generate and publish API documentation (e.g., OpenAPI/Swagger) for all service endpoints.

## 16. CI/CD

- Enforce PR quality gates: linting, type checks, and unit tests must pass before merge.
- Run scheduled integration and evaluation tests (nightly or weekly) for model quality,
  retrieval accuracy, and safety compliance.
- Automate deployment to staging and production via pipeline (no manual steps).
- Run post-deploy smoke tests to verify critical paths: voice input processing, image capture,
  RAG retrieval, SOAP generation, case history delivery.
- Define pipelines as code (e.g., GitHub Actions YAML) and version-control them alongside
  the application code.

## 17. Data Management and Versioning

- Version datasets (SCIN database snapshots, fine-tuning training sets, evaluation sets) and
  data transformations using a data versioning tool (e.g., DVC, LakeFS).
- Validate data pipeline outputs at each stage before downstream consumption.
- Define and enforce data retention and deletion policies for patient medical images, voice
  recordings, and case histories. These are protected health information (PHI).
- Store large artifacts (models, SCIN database at 2GB, embedding indexes) in dedicated
  artifact storage (e.g., S3, GCS, Azure Blob), not in git.
- Track end-to-end data lineage from raw sources (SCIN database, patient input) through
  features (embeddings, transcriptions) to model predictions (ICD codes, SOAP notes).

## 18. Frontend & Browser Requirements

- Use the Pointer Events API (`onPointerDown`/`onPointerUp`) instead of separate mouse and
  touch event handlers. Separate handlers cause double-firing on touch devices.
- For push-to-talk, acquire the microphone stream once on component mount and keep it
  persistent. Only start/stop the MediaRecorder on press/release. Re-acquiring
  `getUserMedia` per press loses the beginning of speech (~100-500ms latency).
- WebRTC APIs (`getUserMedia`, `mediaDevices`) require a secure context (HTTPS or
  localhost). When serving from a LAN IP, use a dev SSL plugin (e.g.,
  `@vitejs/plugin-basic-ssl`) even during development.
- Use `navigator.mediaDevices.getUserMedia()` for cross-platform camera access, not the HTML
  `capture="environment"` attribute (which is mobile-only and falls back to a file picker on
  desktop).
- In React/JSX, use JavaScript Unicode escapes (`\uXXXX`) or actual Unicode characters, not
  HTML entities (`&#NNNN;`). HTML entities render as literal text in JSX.
- When async operations (e.g., `getUserMedia`) control UI state (e.g., a recording
  indicator), ensure the cleanup path always resets the state regardless of whether the async
  operation completed.

## 19. Async Database & Multi-Tenant Patterns

- In async SQLAlchemy, always use eager loading (`selectinload`, `joinedload`) for
  relationships. Lazy loading triggers `MissingGreenlet` errors in async contexts.
- Multi-tenant numbering schemes (patient numbers, case numbers) scoped per-tenant must use
  composite unique constraints (`UniqueConstraint('facility_id', 'patient_number')`), not
  global `unique=True`.
- SOAP note generation requires the full conversation history (both patient answers and
  assistant questions), not just raw patient transcript. Raw text alone produces incomplete
  Objective/Assessment/Plan sections.
- Always use absolute or config-driven paths for data directories. Relative paths break
  depending on which directory the server is started from.

## 20. API Design

- Register specific FastAPI routes (e.g., `/health`, API routers) before SPA catch-all routes
  (`/{full_path:path}`). Catch-all path parameters match everything and will intercept
  specific routes registered after them.
- Never use `from __future__ import annotations` in FastAPI route files. It turns annotations
  into strings, breaking FastAPI's runtime dependency injection for `Request`, `File`,
  `Depends`, and other parameters.
- Every data flow in the architecture diagram must have a corresponding API endpoint.
  Parameters that accept optional data but are never populated are dead code — wire the full
  pipeline end-to-end.
- Different user roles (admin, doctor, patient) need separate endpoints or role-aware
  authorization. Verify that frontend routes call endpoints matching the authenticated user's
  role.
- List/search endpoints must be registered before parameterized routes (e.g., `GET /cases/`
  before `GET /cases/{case_id}`) to avoid path conflicts in FastAPI.

## 21. Agent Document Outputs

The agent shall produce the following document types. Each document type shall follow a
consistent template (sections, headings, tables) to ensure uniform outputs across projects.

### 21.1 Architecture Overview

- **Purpose:** Describe the system's purpose, context, key components, and main data/control
  flows for the Patient Advocacy Agent.
- **Style:** Use C4-style context diagrams as the default notation.
- **Scope:** Voice input pipeline, language detection, WebRTC camera, RAG retrieval (SCIN),
  embedding model (SigLIP-2), medical model (MedGemma), SOAP generation, case history
  delivery, patient voice output.

### 21.2 Design Specification

- **Scope:** Module responsibilities, interfaces between voice/image/RAG/LLM services, data
  models (SOAP notes, case histories, ICD codes, patient sessions), error-handling
  strategies, and non-functional constraints.

### 21.3 Deployment & Operational Runbook

- **Scope:** Target deployment environments (frontier village kiosks, cloud infrastructure),
  infrastructure topology, CI/CD steps, configuration for each environment, scaling strategy
  for concurrent patient sessions, observability stack, and SLOs for voice latency, case
  completion, and system uptime.

### 21.4 Product / Requirements Document (PRD/SRS Hybrid)

- **Scope:** User goals (patient triage, physician case preparation), functional requirements
  (voice interface, 5+ languages, permission-gated pictures, SOAP framework), quality
  attributes (latency, accuracy, safety), acceptance criteria per requirement, and
  dependencies (SCIN database, MedGemma, SigLIP-2, WebRTC).

## 22. Agent Input Requirements

The agent shall only produce high-quality documentation when supplied with the following
structured inputs.

### 22.1 Problem Statement & Constraints

- **Business Goals:** Provide accessible dermatological triage in frontier villages with extreme
  physician-to-patient ratios (1:1000 to 1:10,000).
- **Target Users:** Illiterate or semi-literate patients in the Global South.
- **Success Metrics:** See Section 5.
- **Regulatory Limits:** Unauthorized practice of medicine is illegal. The system is a patient
  advocate, not a doctor. Local health authority regulations in target deployment countries
  must be identified and mapped.
- **Infrastructure Limits:** Low-bandwidth connectivity in frontier villages, limited power
  availability, basic hardware (camera, microphone, speaker).

### 22.2 Architectural Drivers

- Prioritized functional requirements (MoSCoW):
  - **Must Have:** Voice-only interface, permission-gated image capture, SOAP note
    generation, physician case history delivery, patient explanation in local language,
    language detection (minimum 5 languages), critical case escalation.
  - **Should Have:** De-escalation logic (paint, tattoo, mild acne scenarios), RAG retrieval
    with SCIN database, multimodal embedding search.
  - **Could Have:** 100-language support, offline fallback mode, patient feedback collection.
  - **Won't Have (this version):** Direct telemedicine video calls, prescription generation,
    electronic health record (EHR) integration.
- Quality-attribute scenarios: voice response latency under target threshold, 99.5% uptime,
  concurrent session handling, embedding retrieval speed.
- Concerns and constraints in structured form (see tables in architecture document).

### 22.3 Existing System Context

- Repository snapshot and high-level description to be maintained in README.md.
- Reference architectures: agentic RAG patterns, multimodal search pipelines, WebRTC
  media capture patterns.

### 22.4 Guardrails & Style

- **Naming Conventions:** To be defined for code (Python snake_case), APIs (RESTful
  resource naming), database tables, and configuration keys.
- **Diagram Notation:** C4 for architecture, Mermaid for sequence diagrams and flowcharts.
- **Document Voice:** Technical but accessible; medical terms must be defined on first use.
- **Decision Rules:**
  - **Always:** Ask permission before taking a picture. Include "seek professional medical
    help" disclaimer. Escalate suspected malignancies immediately. Redact PII/PHI in logs.
  - **Ask First:** Choosing a database technology. Selecting deployment infrastructure.
    Adding new language support.
  - **Never:** Store PII in plain text. Prescribe medication. Claim to be a doctor. Commit
    secrets to the repository. Use Streamlit for the interface.

### 22.5 Codebase Grounding

- For the Patient Advocacy Agent, the agent shall work against the indexed project
  repository and SCIN database documentation rather than raw, ad-hoc pastes, so that
  descriptions and diagrams are grounded in the actual codebase and data.

## 23. Generation & Review Practices

The documentation workflow shall be explicitly multi-step, not "one-shot big spec."

### 23.1 Plan-First Mode

- The agent shall outline sections, open questions, and assumptions before writing full prose
  for any document (architecture, design, runbook, or PRD).

### 23.2 Iterative Refinement

- Start with coarse documents (system context + container diagrams).
- Iterate into components, interfaces, and deployment details.
- Update earlier diagrams as the design evolves (e.g., when new services are added to the
  voice pipeline).

### 23.3 Human Checkpoints

- After each documentation phase (architectural drivers, architecture overview, detailed
  design, deployment runbook), a human must approve or comment.
- Feed diffs and comments back so the agent revises rather than rewriting from scratch.

### 23.4 Self-Checks

- The agent shall include a **Validation / Open Issues** section in every generated document,
  listing assumptions, risks, and items to confirm.
- The agent shall perform a consistency check against the original project requirements
  (this document) after generating each document.

### 23.5 Separation of Concerns

- Use separate runs/agents for code generation vs. documentation generation to keep the
  design stable and auditable. One agent generates the spec; another implements against it.

## 24. Content Standards

Each document shall meet the following content standards.

### 24.1 Traceability

- Map requirements (from this document and the controller JSONs) to architectural drivers to
  design decisions in traceability tables.
- Maintain these traceability tables as living documents updated with each design change.

### 24.2 Explicit Decisions

- Capture key trade-offs in an Architecture Decision Record (ADR) format: "chose X over Y
  because..." For example:
  - Why WebRTC over alternative camera APIs.
  - Why SCIN database over other dermatological datasets.
  - Why contrastive loss over other fine-tuning approaches.
  - Why MedGemma and SigLIP-2 over alternative models.

### 24.3 Non-Functional Details

- **Performance Budgets:** Voice-to-text latency, RAG retrieval latency, SOAP generation
  time, end-to-end interaction time.
- **Reliability Targets:** System uptime SLA, MTTR, MTBF for critical components.
- **Security Boundaries:** Network trust zones, encryption at rest and in transit for medical
  data, WebRTC security (SRTP/DTLS).
- **Observability Requirements:** See Section 8.
- **Design-to-NFR Mapping:** Each non-functional requirement must map to a specific design
  decision that addresses it.

### 24.4 LLM / Agent Specifics

- **Model Names and Versions:** MedGemma (version TBD), SigLIP-2 (version TBD),
  fine-tuned embedding model (versioned via model registry), language detection model
  (version TBD).
- **Prompting Strategy:** Document the prompting approach for SOAP note generation,
  patient interview, de-escalation questioning, critical case escalation, and patient
  explanation generation.
- **Tools Used:** WebRTC, SCIN database, vector store for embeddings, voice synthesis
  engine, language detection service.
- **Safety Policies:** "Do not play doctor" enforcement, critical case escalation rules,
  de-escalation criteria, PII/PHI protection.
- **Configuration Parameters:** Model temperatures, token limits, retry counts, timeout
  values, embedding dimensions, clustering thresholds, language detection confidence
  thresholds.

### 24.5 Diagrams

- For C4 (context, container, component), sequence, and deployment diagrams, generate
  text-based specs using Mermaid under a **Diagrams** section in each document.
- All diagrams must be versionable (stored as code in the repository) and reviewable in PRs.

## 25. Deployment & Lifecycle Practices

Documentation shall be treated as living artifacts maintained by agents, not one-off exports.

### 25.1 Repo-Stored Documentation

- Store all generated documents in the `docs/` directory of the repository.
- Wire an agent into CI to flag drift between code and documentation (e.g., new API
  endpoints not reflected in the architecture doc, changed config keys not updated in the
  runbook).

### 25.2 Orchestrated Updates

- Use orchestration (e.g., LangGraph or equivalent) so that when one agent introduces
  significant structural changes (new services, changed data flows), another agent updates
  the architecture and design documents accordingly.

### 25.3 Cache & Reuse

- The system shall retrieve relevant sections of past documents as context when generating
  new ones, to maintain consistency.
- Maintain a project glossary of terms (SOAP, ICD codes, SCIN, Fitzpatrick scale, PHI,
  PII, RAG, WebRTC) to ensure consistent terminology across all documents.

### 25.4 Governance

- Define who signs off on architecture and deployment documents (project lead, medical
  advisor if applicable, security reviewer for PHI-related sections).
- Require document sign-off before certain CI stages (e.g., infrastructure changes,
  production deployments, model promotions) can proceed.
