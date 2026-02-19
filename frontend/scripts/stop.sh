#!/usr/bin/env bash
# Stop the React frontend dev server.
#
# Usage:
#   bash frontend/scripts/stop.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PIDFILE="$PROJECT_ROOT/.frontend.pid"

if [[ ! -f "$PIDFILE" ]]; then
    echo "Frontend is not running (no PID file found)."
    exit 0
fi

PID=$(cat "$PIDFILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping frontend (PID: $PID)..."
    kill "$PID" 2>/dev/null
    # Wait up to 5 seconds for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force stopping frontend..."
        kill -9 "$PID" 2>/dev/null
    fi
    rm -f "$PIDFILE"
    echo "Frontend stopped."
else
    echo "Frontend process (PID: $PID) is not running. Cleaning up PID file."
    rm -f "$PIDFILE"
fi
