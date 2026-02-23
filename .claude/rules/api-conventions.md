---
paths:
  - "src/api/**/*.py"
  - "tests/integration/**/*.py"
---

# API Conventions

## Multi-router architecture
- Routes are organized across multiple router files in `src/api/`:
  - `auth_routes.py` — Authentication and token endpoints
  - `patient_routes.py` — Patient registration and case status
  - `case_routes.py` — Case CRUD, status updates, SOAP retrieval
  - `doctor_routes.py` — Doctor case queue, review, recommendations
  - `facility_routes.py` — Facility management
  - `dashboard_routes.py` — Admin observability dashboard
  - `routes.py` — Main router aggregator, health endpoint, session management
- All routers are registered in `main.py` and mount under `/api/v1`
- New endpoints go in the appropriate domain router, not in `routes.py`
- Pydantic request/response models are defined in `src/api/schemas.py`

## Endpoints
- Use `async def` for all handlers
- Use HTTP method decorators: `@router.get`, `@router.post`, `@router.put`, `@router.delete`
- Use plural nouns for resource paths: `/cases`, `/patients`, `/facilities`
- Return Pydantic response models, not raw dicts
- Include medical disclaimer in patient-facing response models

## Request/Response models
- Define Pydantic models in `src/api/schemas.py`
- Use `Field(...)` for required fields with descriptions
- Name models with suffix: `CaseCreate`, `CaseResponse`, `CaseList`
- List responses should include a count: `{"items": [...], "count": N}`

## Error handling
- Raise `AppError(code=ErrorCode.X, message="...", context={...})` for all error cases
- Never return raw `{"error": "..."}` dicts — the `AppError` handler in `main.py` does this
- Map error codes to HTTP status: VALIDATION_ERROR=400, UNAUTHORIZED=401, NOT_FOUND=404, RATE_LIMITED=429

## Logging
- Log at entry and exit of significant operations: `logger.info("case_created", case_id=case.id)`
- Use snake_case event names, not sentences
- Include relevant IDs and counts as structured fields
- Never log PII/PHI — use the PII redactor for patient data
