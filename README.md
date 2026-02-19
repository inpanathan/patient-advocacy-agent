
# Patient Advocacy Agent

An agentic system providing dermatological triage via voice-only interface for
underserved communities in the Global South. Produces SOAP-formatted case
histories for remote physicians and plain-language explanations for patients.

**This system is NOT a doctor.** It always includes a "seek professional medical
help" disclaimer and never prescribes medication or makes definitive diagnoses.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Data](#data)
- [Models](#models)
- [Installation](#installation)
- [Usage](#usage)
- [Training](#training)
- [Evaluation](#evaluation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

- **Problem:** Patients in frontier villages lack access to dermatologists.
  Many are illiterate and cannot use text-based interfaces.
- **Approach:** Voice-only agentic interview using MedGemma (medical LLM),
  SigLIP-2 (multimodal embeddings), and RAG over the Harvard SCIN database.
- **Users:** Patients (voice interface), remote physicians (SOAP case histories).
- **Key techniques:** Contrastive loss fine-tuning, multimodal RAG, WebRTC
  voice pipeline, permission-gated image capture.

## Features

- Voice-only patient interview with language detection (5+ languages)
- Permission-gated image capture via WebRTC camera
- Multimodal RAG retrieval from Harvard SCIN dermatological database
- SOAP note generation with ICD code suggestions
- Critical case escalation (100% escalation rate for suspected malignancies)
- De-escalation for non-medical cases (paint, tattoo, mild acne)
- Bias monitoring across Fitzpatrick skin types (I-VI)
- Structured JSON logging with PII/PHI redaction

## Project Structure

```text
patient_advocacy_agent/
├── CLAUDE.md                    # Autonomous agent instructions
├── pyproject.toml               # Project config and dependencies
├── main.py                      # Application entry point
├── src/
│   ├── models/                  # ML models (SigLIP-2, MedGemma, STT, TTS)
│   ├── data/                    # Data loading, SCIN ingestion
│   ├── features/                # Feature engineering, embeddings
│   ├── utils/                   # Config, logger, errors, feature flags
│   ├── evaluation/              # Clustering, retrieval, SOAP scoring
│   └── pipelines/               # Training, indexing, inference
├── configs/                     # Environment configs + experiments
├── data/                        # Local data (DVC-tracked)
├── models/                      # Saved weights (DVC-tracked)
├── tests/                       # Unit, integration, safety, evaluation
├── scripts/                     # Operational scripts
├── docs/                        # Requirements, architecture, runbooks
└── .github/workflows/           # CI/CD pipelines
```

## Data

- **SCIN Database:** Harvard University, 2GB dermatological dataset with
  images, diagnosis labels, ICD codes, and Fitzpatrick skin type metadata.
- Data is versioned with DVC and not stored in git.
- See `docs/system_requirements.md` for storage requirements.

## Models

| Model | Purpose | Type |
|-------|---------|------|
| SigLIP-2 | Multimodal embeddings (image + text) | Fine-tuned with contrastive loss |
| MedGemma | Medical LLM for SOAP generation, ICD coding | API or local inference |
| STT | Speech-to-text (5+ languages) | Google Cloud Speech |
| TTS | Text-to-speech (patient explanations) | Google Cloud TTS |

## Installation

### Quick Setup

```bash
# Clone the repository
git clone <repo-url>
cd patient_advocacy_agent

# One-command setup (installs deps, creates .env, sets up pre-commit)
./scripts/setup.sh
```

### Manual Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Install pre-commit hooks
uv run pre-commit install
```

### System Dependencies

See `docs/system_requirements.md` for OS-level packages needed for
audio/video processing (WebRTC, OPUS, VP8).

## Usage

```bash
# Start the server
uv run python main.py

# Health check
curl http://localhost:8001/health

# API documentation (dev mode only)
open http://localhost:8001/docs
```

## Training

```bash
# Fine-tune SigLIP-2 embeddings on SCIN database
uv run python -m src.pipelines.train_embeddings --config configs/experiments/default.yaml

# Index embeddings into vector store
uv run python -m src.pipelines.index_embeddings
```

## Evaluation

```bash
# Run clustering evaluation
uv run python -m src.evaluation.clustering

# Run retrieval evaluation
uv run python -m src.evaluation.retrieval_eval

# Run bias metrics across Fitzpatrick types
uv run python -m src.evaluation.bias_metrics
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -x -q

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run specific categories
uv run pytest tests/unit/ -x -q
uv run pytest tests/integration/ -x -q
uv run pytest tests/safety/ -x -q

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/ --ignore-missing-imports
```

## Documentation

| Document | Path |
|----------|------|
| Project Requirements | `docs/requirements/project_requirements_v1.md` |
| System Requirements | `docs/system_requirements.md` |
| Architecture Overview | `docs/architecture/` |
| Design Specification | `docs/design/` |
| Deployment Runbook | `docs/runbook/` |
| ADRs | `docs/adr/` |
| App Cheatsheet | `docs/app_cheatsheet.md` |

## Contributing

1. Create a feature branch from `master`
2. Write tests alongside code
3. Ensure all tests pass: `uv run pytest tests/ -x -q`
4. Ensure lint passes: `uv run ruff check src/ tests/`
5. Submit a pull request

## License

TBD
