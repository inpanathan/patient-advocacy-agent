#!/usr/bin/env bash
# Start the Patient Advocacy Agent server.
#
# Usage:
#   ./scripts/start_server.sh            # Development mode
#   ./scripts/start_server.sh production  # Production mode

set -euo pipefail

MODE="${1:-development}"

case "$MODE" in
  development)
    echo "Starting server in development mode..."
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ;;
  staging)
    echo "Starting server in staging mode..."
    APP_ENV=staging uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
    ;;
  production)
    echo "Starting server in production mode..."
    APP_ENV=production uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    ;;
  docker)
    echo "Starting server via Docker..."
    docker compose up --build -d
    echo "Server running at http://localhost:8000"
    echo "Logs: docker compose logs -f"
    ;;
  *)
    echo "Usage: $0 {development|staging|production|docker}"
    exit 1
    ;;
esac
