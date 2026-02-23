---
paths:
  - "src/utils/config.py"
  - "configs/**"
  - ".env*"
---

# Configuration Rules

## Layered config precedence (highest wins)
1. Environment variables (from `.env` or system)
2. YAML file (`configs/{APP_ENV}.yaml`)
3. Hardcoded defaults in `Settings` class

## Adding new config values
- Add the field to `Settings` or a nested `*Settings` class in `src/utils/config.py`
- Provide a sensible default for development
- Add validation if the value has constraints (use `@field_validator`)
- Add the variable to `.env.example` with a comment
- Add it to `configs/dev.yaml` if it differs from the class default
- Access everywhere via `from src.utils.config import settings`

## Nested settings groups
- `settings.database` — PostgreSQL connection (url, enabled, pool_size)
- `settings.scin` — SCIN data paths (data_dir, raw, interim, processed)
- `settings.vector_store` — ChromaDB/Qdrant (backend, collection, top_k, threshold)
- `settings.models` — Model backends (embedding_backend, medical_backend, stt_backend, tts_backend)
- `settings.llm` — LLM parameters (temperature, max_tokens, timeout)
- `settings.security` — Auth settings (secret_key, jwt_expiry, cors_origins)
- `settings.logging` — Log settings (level, structured)
- `settings.feature_flags` — Feature toggles (use_mocks, enable_voice, enable_video)
- Access with dot notation: `settings.database.url`
- Set via env vars with `__` delimiter: `DATABASE__URL=postgresql://...`

## Security
- Never commit `.env` — only `.env.example`
- Production must set `SECRET_KEY` and `APP_DEBUG=false` (validated at startup)
- Don't log secret values — structlog fields are visible in JSON output
- `model_backend` must be one of: `mock`, `local`, `cloud`
- Database connection strings must never appear in logs
