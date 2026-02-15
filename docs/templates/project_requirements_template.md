# Project Specification for AI Coding Agent

## 1. Goal

- One-sentence summary of what you want built.
- What problem this solves and who it is for.

## 2. Deliverables

- What concrete outputs you expect (e.g., codebase, API endpoints, CLI tool, tests, docs).
- Target languages and frameworks (e.g., Python 3.11, FastAPI, React, PyTorch).

## 3. High-Level Requirements

- Core user flows or use cases.
- Main features or components.
- What “v1” MUST include vs. nice-to-have items.

## 4. Functional Requirements

Describe behavior in terms of inputs, processing, and outputs.

- Feature 1: **Name**
  - Purpose:
  - Inputs:
  - Outputs:
  - Detailed behavior:
  - Edge cases:

- Feature 2: **Name**
  - Purpose:
  - Inputs:
  - Outputs:
  - Detailed behavior:
  - Edge cases:

(Add more as needed.)

## 5. Non-Functional Requirements

- Performance (e.g., handle 1k req/min, process 1M rows in < 5 min).
- Security and privacy (e.g., do not log PII, sanitize inputs).
- Reliability & robustness (e.g., graceful error handling, retries).
- Maintainability (e.g., modular design, comments, docstrings).
- Portability (e.g., must run in Docker, no system-specific paths).

## 6. Tech Stack and Constraints

- Programming languages:
- Frameworks/libraries:
- Dependencies allowed / disallowed:
- Environment (OS, CPU/GPU, Docker, cloud platform):
- Database / storage decisions:
- Any architectural constraints (monolith vs. services, sync vs. async).

## 7. Project Structure

Describe or request a structure.

- Preferred layout (example):

  - `src/` – application code
  - `tests/` – unit/integration tests
  - `configs/` – configuration files
  - `scripts/` – helper scripts (run, train, deploy)
  - `docs/` – additional documentation

- Naming conventions (files, classes, functions).

## 8. Data and Models (AI/ML-Specific)

- Data sources and formats (CSV, Parquet, JSON, DB tables, APIs).
- Input schema(s) with types and example records.
- Target variable(s) and task type (classification, regression, generation, RL, etc.).
- Model families to use or avoid (e.g., XGBoost, Transformers, Llama, custom CNN).
- Training constraints (time, GPU/CPU limits, max dataset size).
- Evaluation metrics (e.g., accuracy, F1, AUROC, BLEU).
- Expected artifacts (trained model files, checkpoints, pipelines).

## 9. Example Scenarios (Few-Shot Specs)

Provide concrete examples to steer behavior.

- Example 1
  - Input:
  - Expected processing steps:
  - Expected output:

- Example 2
  - Input:
  - Expected processing steps:
  - Expected output:

(Add more if needed.)

## 10. Interfaces and APIs

If applicable:

- HTTP endpoints (path, method, request/response schema).
- CLI commands and flags.
- Library functions/classes that should be exposed and how they are called.

## 11. Testing and Validation

- Testing tools (e.g., pytest, unittest).
- Types of tests required (unit, integration, E2E).
- Minimum coverage expectations (if any).
- Explicit acceptance criteria, e.g.:
  - “These sample inputs should produce these outputs.”
  - “All tests in `tests/` must pass.”

## 12. Code Style and Quality

- Style guide (PEP8, Black, isort, Ruff, ESLint, Prettier, etc.).
- Docstring style (NumPy, Google, reStructuredText).
- Commenting expectations.
- Example of “good” code snippet (optional).

## 13. Workflow and Tools Usage

Explain how you want the AI to operate.

- Preferred workflow (plan first, then implement; small PR-style changes; etc.).
- How often to ask clarifying questions vs. make assumptions.
- Whether to refactor existing code or keep changes minimal.
- Any restrictions on modifying files (e.g., do not touch CI config).

## 14. Out of Scope / Boundaries

- Things the agent must not do (e.g., no external network calls, no paid APIs).
- Features explicitly excluded from this iteration.
- Any legal or compliance constraints (licenses, data residency).

## 15. Output Format for This Session

- How you want responses formatted (single code block, patch-style diffs, step-by-step plan then code, etc.).
- Any metadata to include (file paths, instructions to run, migration notes).

