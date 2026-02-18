# Patient Advocacy Agent — Autonomous Agent Instructions

## Mission

You are building the **Patient Advocacy Agent**: an agentic system that provides
dermatological triage to illiterate patients in frontier villages of the Global South via
a voice-only interface. It produces SOAP-formatted case histories for remote physicians and
plain-language explanations for patients. **It is NOT a doctor.**

## Critical Rules

1. **Never play doctor.** The system must never prescribe medication, diagnose definitively,
   or claim to be a medical professional. Always include a "seek professional medical help"
   disclaimer.
2. **Never commit secrets.** API keys, credentials, and tokens go in `.env` (gitignored).
3. **Never store PII in plain text.** All patient data (voice, images, case histories) must
   be redacted in logs and encrypted at rest.
4. **Never use Streamlit.** This is a production web application (FastAPI + WebRTC).
5. **Always ask permission before taking a picture.** Permission-gated image capture is mandatory.
6. **Always escalate suspected malignancies immediately.** 100% escalation rate is non-negotiable.

## Source of Truth

All requirements and the implementation plan live in these files:

| Document | Path |
|----------|------|
| Project Requirements | `docs/requirements/project_requirements_v1.md` |
| Common Requirements | `docs/requirements/common_requirements.md` |
| Common Controller | `docs/requirements/common_requirements_controller.json` |
| Documentation Requirements | `docs/requirements/documentation_requirements.md` |
| Doc Controller | `docs/requirements/documentation_requirements_controller.json` |
| **Implementation Plan** | `coding-agent/plans/implementation_plan_v1.md` |
| README Template | `docs/templates/README_template.md` |
| App Cheatsheet | `docs/app_cheatsheet.md` |

**Read the implementation plan before starting any work.** It defines 11 phases with
explicit task lists, requirement traceability, and dependencies.

## Workflow — How to Work Autonomously

### Progress Tracking

1. Before starting a phase, update its tasks in
   `coding-agent/plans/implementation_plan_v1.md` from `Pending` to `In Progress`.
2. After completing a task, update it to `Done`.
3. After completing a phase, write a brief summary to
   `coding-agent/logs/phase_N_complete.md` with what was built, decisions made, and any
   issues encountered.
4. If blocked, mark the task as `Blocked — [reason]`, document the blocker in
   `coding-agent/logs/blockers.md`, and **move to the next unblocked task or phase**.
5. Commit working code frequently (after each completed task or logical unit of work).

### Phase Execution Order

Follow the dependency graph from the implementation plan:

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 ─┐
Phase 0 → Phase 4 (parallel with 1-3) ──┤
                                         └→ Phase 5 → Phase 6 → Phase 7, 8 → Phase 9
Phase 10 (parallel with 9) ─────────────────────────────────────────────────→ Phase 11
```

Phase 4 (Voice Pipeline) can be built in parallel with Phases 1-3. Start it after Phase 0
is complete.

### For Each Task

1. Read the task description and its mapped requirements from the controller JSONs.
2. Check if there are existing files to modify before creating new ones.
3. Write the code with structured logging, error handling, type hints, and docstrings.
4. Write tests alongside the code (not after).
5. Run the tests: `uv run pytest tests/ -x -q`
6. If tests pass, commit with a descriptive message.
7. Update the task status in the implementation plan.

### Git Workflow

- Commit after each completed task or logical unit.
- Commit messages: `Phase N.M: <what was done> [REQ-XXX-NNN]`
- Example: `Phase 0.5: Add layered config module with startup validation [REQ-CFG-001, REQ-CFG-003]`
- Do NOT push unless explicitly instructed. Work on local commits.

## Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.12+ | Use type hints everywhere |
| Package Manager | uv | Already set up with `pyproject.toml` |
| Web Framework | FastAPI | Not Streamlit. Production-grade. |
| Camera/Audio | WebRTC (aiortc) | For real-time voice + image capture |
| Embedding Model | SigLIP-2 | Fine-tune with contrastive loss |
| Medical Model | MedGemma | For SOAP generation and ICD codes |
| Vector Store | ChromaDB or Qdrant | Document choice as ADR |
| RAG Database | SCIN (Harvard, 2GB) | Text + images, dermatological |
| Experiment Tracking | MLflow | Log hyperparams, metrics, artifacts |
| Data Versioning | DVC | For SCIN snapshots and training sets |
| Testing | pytest | With pytest-asyncio for async code |
| Linting | ruff | Fast, replaces flake8+isort+black |
| Type Checking | mypy | Strict mode |
| CI | GitHub Actions | Pipelines as code |
| Config | pydantic-settings | Layered config with validation |
| Logging | structlog | JSON structured logging |

## Project Structure

```
patient_advocacy_agent/
├── CLAUDE.md                    # This file — agent instructions
├── pyproject.toml               # Project config and dependencies
├── main.py                      # Application entry point
├── src/
│   ├── models/                  # ML models (SigLIP-2, MedGemma, STT, TTS, lang detect)
│   ├── data/                    # Data loading, SCIN ingestion, schema validation
│   ├── features/                # Feature engineering, embedding generation
│   ├── utils/                   # Config, logger, errors, session, feature flags, PII redaction
│   ├── evaluation/              # Clustering eval, retrieval eval, SOAP scoring, bias metrics
│   └── pipelines/               # Training, indexing, inference, patient interview, SOAP gen
├── configs/
│   ├── dev.yaml                 # Dev environment config
│   ├── staging.yaml             # Staging config
│   ├── production.yaml          # Production config
│   └── experiments/             # Hyperparameter configs (versioned)
├── data/
│   ├── raw/                     # Raw SCIN data (DVC-tracked, not in git)
│   ├── interim/                 # Intermediate processing
│   └── processed/               # Ready for training/inference
├── models/                      # Saved weights, checkpoints (DVC-tracked)
├── tests/
│   ├── unit/                    # Unit tests per module
│   ├── integration/             # Pipeline integration tests
│   ├── evaluation/              # Model evaluation tests
│   ├── safety/                  # Safety and compliance tests
│   └── fixtures/                # Test data fixtures
├── scripts/                     # Operational scripts
├── docs/
│   ├── requirements/            # All requirement docs + controllers
│   ├── templates/               # Document templates
│   ├── architecture/            # Architecture overview (C4/Mermaid)
│   ├── design/                  # Design specification
│   ├── runbook/                 # Deployment & operational runbook
│   ├── adr/                     # Architecture Decision Records
│   └── app_cheatsheet.md        # Operational cheatsheet
├── coding-agent/
│   ├── plans/                   # Implementation plans
│   └── logs/                    # Phase completion logs, blockers
└── .github/
    └── workflows/               # CI/CD pipelines
```

## Coding Standards

### Python Style
- **Type hints** on all function signatures and class attributes.
- **Docstrings** on all public modules, classes, and functions (Google style).
- **No print statements.** Use `structlog` for all output.
- **No bare except clauses.** Catch specific exceptions.
- **Async-first** for I/O-bound operations (FastAPI, WebRTC, API calls).

### Logging Pattern
```python
import structlog
logger = structlog.get_logger()

# Every log must include structured context
logger.info("soap_generated",
    patient_session_id=session.id,
    model="medgemma-v1",
    icd_codes=["L20.0", "L30.9"],
    latency_ms=elapsed,
    prompt_id=prompt.id)
```

### Error Handling Pattern
```python
from src.utils.errors import AppError, ErrorCode

# Consistent error responses
raise AppError(
    code=ErrorCode.RAG_RETRIEVAL_FAILED,
    message="Vector store query timed out",
    context={"query_id": qid, "timeout_ms": 5000})
```

### Config Pattern
```python
from src.utils.config import settings

# Validated at startup, fails fast
model_path = settings.models.medgemma_path
temperature = settings.llm.temperature
```

### Test Pattern
```python
# tests/unit/test_<module>.py
# One test file per source module
# Use fixtures from tests/fixtures/
# Fix random seeds: use @pytest.fixture with seed=42
```

## Decision Rules

### Always
- Use structured JSON logging with `structlog`
- Include `patient_session_id` and `trace_id` in all logs
- Redact PII/PHI before logging (patient names, locations, images)
- Validate inputs at service boundaries
- Set timeouts on all external calls (default: 30s)
- Use retries with exponential backoff for transient failures
- Write tests alongside code
- Document ADRs for technology choices
- Include "seek professional medical help" disclaimer in all patient outputs
- Escalate suspected malignancies immediately
- Ask permission before image capture

### Ask First (Document as Open Question)
- Choosing between vector store options (ChromaDB vs Qdrant vs other)
- Cloud provider for deployment
- Specific language priorities for initial 5-language support
- Case history delivery mechanism (email vs API vs portal)

### Never
- Store PII/PHI in plain text or logs
- Prescribe medication or claim to be a doctor
- Commit secrets, API keys, or credentials
- Use Streamlit for the interface
- Use `print()` instead of structured logging
- Skip tests for new code
- Force-push or rewrite git history
- Create files outside the project structure

## Handling Open Questions

The implementation plan lists 8 open questions. When you encounter one during
implementation:

1. Make a **reasonable default choice** based on the project context.
2. Document the choice and rationale as an ADR in `docs/adr/`.
3. Mark it clearly as "provisional — awaiting stakeholder confirmation."
4. Log it in `coding-agent/logs/decisions.md`.
5. Continue implementation — do not block on open questions.

**Default choices for common open questions:**
- **Vector store:** ChromaDB (simpler setup, good for prototyping, can migrate later)
- **STT/TTS:** Google Cloud Speech-to-Text / Text-to-Speech (best language coverage)
- **Initial 5 languages:** Hindi, Bengali, Tamil, Swahili, Spanish (Global South coverage)
- **Case history delivery:** Email via SMTP (simplest, works with existing infra)
- **Deployment:** Docker containers, deployable to any cloud

## Test Execution

```bash
# Run all tests
uv run pytest tests/ -x -q

# Run specific test category
uv run pytest tests/unit/ -x -q
uv run pytest tests/integration/ -x -q
uv run pytest tests/safety/ -x -q

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run linting
uv run ruff check src/ tests/
uv run mypy src/
```

## When You Get Stuck

1. **Import error / missing package:** Add it to `pyproject.toml` dependencies and run
   `uv sync`.
2. **Test failure:** Fix the code, not the test. If the test expectation is wrong, fix
   the test with a comment explaining why.
3. **External service unavailable (SCIN, MedGemma, etc.):** Create a mock/stub,
   document the stub in `coding-agent/logs/blockers.md`, and continue with the mock.
   Mark the task as `Blocked — external dependency`.
4. **Architecture uncertainty:** Make a decision, write an ADR, mark as provisional.
5. **Circular dependency between phases:** Implement the minimum interface/stub needed
   to unblock, then fill in the real implementation when the dependency is ready.

## Commit Message Format

```
Phase <N>.<M>: <imperative description> [REQ-XXX-NNN, ...]

<optional body explaining why>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Autonomous Feedback Loops

The key to hands-off execution is **self-correcting feedback loops**. After every
significant action, verify the result and fix issues before moving on.

### Build-Test-Fix Loop (after every task)

```
1. Write/modify code
2. Run: uv run ruff check src/ tests/ --fix
3. Run: uv run mypy src/ --ignore-missing-imports
4. Run: uv run pytest tests/ -x -q
5. If any step fails:
   a. Read the error output carefully
   b. Fix the issue (code, import, type annotation, test)
   c. Go back to step 2
   d. Max 3 retry attempts per issue; if still failing, mark task as
      Blocked and document in coding-agent/logs/blockers.md
6. If all pass: commit and move to next task
```

### Dependency Resolution Loop (when adding packages)

```
1. Add dependency: uv add <package>
2. Run: uv sync
3. If conflict: try alternative version or compatible package
4. Verify import works: uv run python -c "import <package>"
5. If still failing: document in blockers.md, create stub interface, continue
```

### Stub-and-Continue Pattern (for external dependencies)

When you hit something that requires credentials, hardware, or external services that
aren't available:

1. Create an **interface/protocol** (`src/models/protocols.py`) defining the expected API.
2. Create a **mock implementation** (`src/models/mocks/`) that returns realistic test data.
3. Create the **real implementation** with a clear `TODO: requires <credential/service>`
   comment at the top.
4. Wire the config to switch between mock and real via `settings.use_mocks = True`.
5. Write tests against the interface — they pass with the mock today and will pass with the
   real implementation later.
6. **Keep building.** Do not stop.

### Self-Check After Each Phase

After completing all tasks in a phase:

```
1. Run full test suite: uv run pytest tests/ -x -q --tb=short
2. Run lint: uv run ruff check src/ tests/
3. Run type check: uv run mypy src/ --ignore-missing-imports
4. Count: ensure no Pending tasks remain in the phase
5. Write phase completion log: coding-agent/logs/phase_N_complete.md
6. Git commit: "Phase N complete: <summary>"
7. Proceed to next phase
```

## Recovery From Failures

### If `uv sync` fails
- Check `pyproject.toml` for syntax errors
- Try `uv lock --upgrade` to resolve conflicts
- Pin specific versions if needed

### If tests fail after a code change
- The test is probably right; fix the code
- If the test expectation is genuinely wrong, fix the test with a comment
- Never delete a failing test to make CI green

### If the project won't start
- Check `uv run python -c "from src.utils.config import settings; print(settings)"` works
- Check `.env` exists (copy from `.env.example`)
- Check all required configs exist in `configs/`

### If you've been going in circles on the same issue for 3+ attempts
- Stop and document: what you tried, what failed, and why in `coding-agent/logs/blockers.md`
- Create a minimal stub/mock that makes the rest of the system work
- Mark the task as `Blocked` in the plan
- Move on to the next task

## Completion Criteria

The project is done when:
- [ ] All 11 phases have status `Done` in the implementation plan
- [ ] All 157 requirements have corresponding implementations
- [ ] All tests pass (`uv run pytest tests/ -x -q`)
- [ ] Linting passes (`uv run ruff check src/ tests/`)
- [ ] Type checking passes (`uv run mypy src/`)
- [ ] All 4 documents generated (architecture, design, runbook, PRD)
- [ ] README.md fully populated from template
- [ ] `app_cheatsheet.md` has all URLs and operational details
- [ ] `CHANGELOG.md` initialized with all changes

When all criteria are met, write a final summary to `coding-agent/logs/BUILD_COMPLETE.md`
with:
- Total tasks completed
- Tasks blocked (and why)
- ADRs created
- Key decisions made
- What needs human attention next
