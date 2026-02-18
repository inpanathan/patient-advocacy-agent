# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-02-18

### Added
- **Phase 0**: Project foundation — pyproject.toml, config, logger, errors, feature flags, CI pipeline
- **Phase 1**: SCIN data pipeline — schema, loader, quality checks, drift detection, lineage tracking
- **Phase 2**: Embedding model — SigLIP-2 protocol/mock, contrastive loss, clustering evaluation
- **Phase 3+4**: RAG retrieval + voice pipeline — vector index, RAG retriever, STT/TTS/language detection mocks, session management, WebRTC stub
- **Phase 5**: Medical AI agent — MedGemma mock, patient interview state machine, SOAP generator, case history, patient explanation, PII redactor
- **Phase 6**: API integration — FastAPI endpoints for sessions, interaction, consent, SOAP, case history
- **Phase 7**: Comprehensive testing — regulatory compliance, bias/fairness, GenAI regression, model evaluation, performance benchmarks (223 tests)
- **Phase 8**: Observability — metrics collection, alert rules, audit trail, safety evaluator, runbooks
- **Phase 9**: CI/CD — Dockerfile, docker-compose, extended CI with safety gates, nightly evaluation workflow
- **Phase 10**: Documentation — architecture overview, design spec, deployment runbook, ADRs, PRD, glossary

### Security
- PII/PHI redaction on all logged data
- Non-root Docker container
- Never prescribes medication
- Consent-gated image capture
- Mandatory disclaimers on all outputs
