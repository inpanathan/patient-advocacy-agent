---
name: add-endpoint
description: Scaffold a new API endpoint following project patterns, including route, models, and tests
disable-model-invocation: true
argument-hint: "[method] [path] [description]"
---

Add a new API endpoint based on: $ARGUMENTS

1. Read the relevant router files in `src/api/` and `main.py` to understand existing patterns:
   - `src/api/auth_routes.py` — authentication endpoints
   - `src/api/patient_routes.py` — patient endpoints
   - `src/api/case_routes.py` — case management endpoints
   - `src/api/doctor_routes.py` — doctor endpoints
   - `src/api/facility_routes.py` — facility endpoints
   - `src/api/dashboard_routes.py` — dashboard endpoints
   - `src/api/routes.py` — main router aggregator
   - `src/api/schemas.py` — Pydantic request/response models
2. Read `src/utils/errors.py` for error handling conventions

3. Determine which router file the new endpoint belongs in (by domain). Implement the endpoint:
   - Define Pydantic request/response models in `src/api/schemas.py`
   - Add the route to the appropriate router — it mounts at `/api/v1` automatically
   - Use `async def` for the handler
   - Add type hints for parameters and return type
   - Raise `AppError(code=ErrorCode.X, ...)` for error cases
   - Log key events with `logger.info("event_name", key=value)`
   - Include medical disclaimer in patient-facing responses

4. Write tests in the appropriate test file under `tests/integration/`:
   - Use the existing `client` fixture (TestClient with lifespan)
   - Test the happy path
   - Test validation errors (400)
   - Test not-found cases (404) if applicable
   - Test auth requirements (401/403) if the endpoint requires authentication

5. Run quality checks:
   ```bash
   uv run ruff check src/ tests/ --fix && uv run mypy src/ --ignore-missing-imports && uv run pytest tests/ -x -q
   ```

6. Fix any failures before finishing
