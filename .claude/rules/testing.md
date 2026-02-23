---
paths:
  - "tests/**/*.py"
---

# Testing Conventions

## Structure
- Unit tests: `tests/unit/` — mirrors `src/` directory structure
- Integration tests: `tests/integration/` — API and cross-module tests
- Evaluation tests: `tests/evaluation/` — model quality, clustering, retrieval, bias metrics
- Safety tests: `tests/safety/` — security, load, bias/fairness, regulatory compliance, GenAI regression
- Fixtures: `tests/fixtures/` — shared test data files (SCIN samples, audio fixtures)

## Naming
- Test files: `test_<module>.py`
- Test functions: `test_<what>_<scenario>` (e.g., `test_create_case_with_missing_field_returns_422`)
- Fixtures: descriptive nouns (e.g., `client`, `sample_case`, `auth_headers`, `mock_soap_response`)

## Patterns
- Use `pytest.fixture()` decorator, not setup/teardown methods
- API tests use the `client` fixture from `TestClient(create_app())` with lifespan context
- Assert on specific values in response body, not just status codes
- One assertion focus per test — test one behavior, not multiple
- Tests must be independent — no shared mutable state, no ordering dependencies
- Use `pytest.raises(AppError)` for testing error cases, check `.code` on the caught exception
- Use `MODEL_BACKEND=mock` environment variable for tests that need ML model stubs
- Database tests should use test fixtures with proper setup/teardown isolation

## Medical domain test patterns
- SOAP validation: verify output contains Subjective, Objective, Assessment, Plan sections
- Escalation tests: verify malignancy keywords trigger immediate escalation
- Disclaimer tests: verify "seek professional medical help" appears in patient outputs
- PII redaction tests: verify patient names/locations are stripped from logs
- Consent tests: verify image capture requires explicit permission

## What not to do
- Don't mock structlog or the config singleton unless explicitly needed
- Don't mock FastAPI internals — use the real TestClient
- Don't use `unittest.TestCase` — use plain pytest functions
- Don't write tests that depend on external services without a skip marker
