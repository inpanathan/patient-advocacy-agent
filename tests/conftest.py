"""Root test configuration.

Sets APP_ENV=test and MODEL_BACKEND=mock before any application code
imports, ensuring tests use mock models (configs/test.yaml) regardless
of .env settings.

To run with real models, override explicitly:
    MODEL_BACKEND=local uv run pytest tests/integration/test_local_models.py -v
"""

import os

os.environ["APP_ENV"] = "test"
os.environ.setdefault("MODEL_BACKEND", "mock")
