#!/usr/bin/env bash
# Start the Patient Advocacy Agent server.
#
# Usage:
#   bash scripts/start_server.sh              # Development mode
#   bash scripts/start_server.sh staging      # Staging mode
#   bash scripts/start_server.sh production   # Production mode
#   bash scripts/start_server.sh docker       # Docker compose
#
# Once started, press 'b' to send to background, or 'q' to stop.
# After backgrounding: tail -f .server.log  |  kill $(cat .server.pid)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODE="${1:-development}"

case "$MODE" in
  development)
    export SERVICE_NAME="Server ($MODE)"
    export PIDFILE="$PROJECT_ROOT/.server.pid"
    export LOGFILE="$PROJECT_ROOT/.server.log"
    export CMD="uv run uvicorn main:create_app --factory --reload --host 0.0.0.0 --port 8001"
    ;;
  staging)
    export SERVICE_NAME="Server ($MODE)"
    export PIDFILE="$PROJECT_ROOT/.server.pid"
    export LOGFILE="$PROJECT_ROOT/.server.log"
    export CMD="APP_ENV=staging uv run uvicorn main:create_app --factory --host 0.0.0.0 --port 8001 --workers 2"
    ;;
  production)
    export SERVICE_NAME="Server ($MODE)"
    export PIDFILE="$PROJECT_ROOT/.server.pid"
    export LOGFILE="$PROJECT_ROOT/.server.log"
    export CMD="APP_ENV=production uv run uvicorn main:create_app --factory --host 0.0.0.0 --port 8001 --workers 4"
    ;;
  docker)
    echo "Starting server via Docker..."
    docker compose up --build -d
    echo "Server running at http://localhost:8001"
    echo "Logs: docker compose logs -f"
    exit 0
    ;;
  *)
    echo "Usage: $0 {development|staging|production|docker}"
    exit 1
    ;;
esac

source "$PROJECT_ROOT/scripts/_run_with_background.sh"
