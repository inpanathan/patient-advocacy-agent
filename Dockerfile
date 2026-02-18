FROM python:3.12-slim AS base

LABEL maintainer="Patient Advocacy Agent Team"
LABEL description="Dermatological triage agent for underserved communities"

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install dependencies (no dev extras in production)
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY src/ src/
COPY configs/ configs/
COPY main.py .

# Install the project itself
RUN uv sync --no-dev

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
