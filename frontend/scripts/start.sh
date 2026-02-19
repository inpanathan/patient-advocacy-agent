#!/usr/bin/env bash
# Start the React frontend dev server.
#
# Usage:
#   bash frontend/scripts/start.sh           # Dev server (default)
#   bash frontend/scripts/start.sh build     # Production build
#   bash frontend/scripts/start.sh preview   # Preview production build
#
# Once started in dev mode, press 'b' to send to background, or 'q' to stop.
# After backgrounding: tail -f .frontend.log  |  kill $(cat .frontend.pid)

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "$FRONTEND_DIR/.." && pwd)"

MODE="${1:-dev}"

# Ensure node_modules exist
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

case "$MODE" in
  dev)
    export SERVICE_NAME="Frontend (dev)"
    export PIDFILE="$PROJECT_ROOT/.frontend.pid"
    export LOGFILE="$PROJECT_ROOT/.frontend.log"
    export CMD="npm --prefix $FRONTEND_DIR run dev"
    source "$PROJECT_ROOT/scripts/_run_with_background.sh"
    ;;
  build)
    echo "Building frontend for production..."
    (cd "$FRONTEND_DIR" && npm run build)
    echo "Build complete: $FRONTEND_DIR/dist/"
    ;;
  preview)
    export SERVICE_NAME="Frontend (preview)"
    export PIDFILE="$PROJECT_ROOT/.frontend.pid"
    export LOGFILE="$PROJECT_ROOT/.frontend.log"
    export CMD="npm --prefix $FRONTEND_DIR run preview"
    source "$PROJECT_ROOT/scripts/_run_with_background.sh"
    ;;
  *)
    echo "Usage: $0 {dev|build|preview}"
    exit 1
    ;;
esac
