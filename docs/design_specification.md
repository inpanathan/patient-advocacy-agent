# Design Specification

**Patient Advocacy Agent — Module-Level Design**

## 1. Module Responsibilities

### `src/api/routes.py`
- Defines all HTTP endpoints (session CRUD, interaction, consent, SOAP, case history)
- Request/response validation via Pydantic models
- Error handling: maps AppError to HTTP status codes

### `src/pipelines/patient_interview.py`
- Orchestrates the conversational interview state machine
- Stage transitions: greeting -> interview -> consent -> image_capture
- Escalation keyword detection (melanoma, cancer, etc.)
- De-escalation for non-medical cases (paint, tattoo, etc.)
- Always includes "not a doctor" disclaimer

### `src/pipelines/soap_generator.py`
- Generates SOAP notes from session transcript + RAG context + image analysis
- Delegates to MedicalModel.generate_soap()
- Always attaches disclaimer to output
- Structured logging of ICD codes and confidence

### `src/pipelines/case_history.py`
- Formats CaseHistory from session + SOAP note
- Generates CASE-{uuid_prefix} identifiers
- Includes escalation status and reason

### `src/pipelines/patient_explanation.py`
- Generates plain-language patient explanations for TTS
- Uses simple, short sentences for illiterate patients
- Never prescribes, always recommends seeing a doctor

### `src/models/` (factory pattern)
- `medical_model.py` — MedGemma factory (returns mock or real)
- `embedding_model.py` — SigLIP-2 factory with normalization
- `stt.py`, `tts.py`, `language_detection.py` — Voice service factories
- `rag_retrieval.py` — VectorIndex + RAGRetriever with caching

### `src/models/protocols/`
- `embedding.py` — EmbeddingModelProtocol (embed_image, embed_text, embed_batch)
- `voice.py` — STTProtocol, TTSProtocol, LanguageDetectorProtocol
- `medical.py` — MedicalModelProtocol (generate, generate_soap), SOAPNote dataclass

### `src/models/mocks/`
- `mock_embedding.py` — SHA-256 based deterministic embeddings
- `mock_voice.py` — Fixed STT/TTS/language detection results
- `mock_medical.py` — Realistic SOAP notes with L20.0/L25.0 ICD codes

### `src/data/`
- `scin_schema.py` — SCINRecord with Fitzpatrick types, ICD validation
- `scin_loader.py` — Loads and validates SCIN metadata
- `quality.py` — Duplicate, missing field, and category checks
- `drift.py` — Distribution drift detection with configurable thresholds
- `lineage.py` — Data processing step tracking

### `src/utils/`
- `config.py` — Layered config: defaults < YAML < env vars
- `logger.py` — structlog with JSON/console output
- `errors.py` — ErrorCode enum + AppError exception
- `session.py` — PatientSession with stage transitions, SessionStore
- `pii_redactor.py` — Regex-based PII/PHI redaction
- `feature_flags.py` — Boolean flags from env vars

### `src/observability/`
- `metrics.py` — MetricsCollector with counters and histograms
- `alerts.py` — AlertRule definitions and AlertEvaluator
- `audit.py` — AuditTrail for prediction provenance
- `safety_evaluator.py` — Runtime safety compliance checks

## 2. Interfaces

### API Contract
All endpoints use JSON request/response bodies. See `/docs` (Swagger) for full OpenAPI spec.

### Model Protocol Pattern
```python
class MedicalModelProtocol(Protocol):
    async def generate(self, prompt: str) -> MedicalModelResponse: ...
    async def generate_soap(self, transcript: str, ...) -> SOAPNote: ...
```
Implementations: `MockMedicalModel` (dev), `MedGemmaModel` (production, TODO).

### Session State Machine
```
GREETING -> INTERVIEW -> IMAGE_CONSENT -> IMAGE_CAPTURE -> ANALYSIS -> EXPLANATION -> COMPLETE
                                       \-> INTERVIEW (consent denied)
Any stage -> ESCALATED (if escalation keywords detected)
```

## 3. Error Handling

- All errors extend `AppError` with `ErrorCode` enum
- API layer converts AppError to HTTP response with code and message
- Structured logging includes trace_id for correlation
- Graceful degradation: RAG failures return empty context, not crash

## 4. NFR Constraints

| Requirement | Design Response |
|---|---|
| Latency < 2s per turn | Async processing, mock models < 200ms |
| 100 concurrent sessions | In-memory SessionStore with dict lookup |
| Fitzpatrick equity | Equal embedding dimensions, equal SOAP quality |
| PII protection | Regex redaction before logging |
| No prescriptions | Safety evaluator pattern matching |
