#!/usr/bin/env bash
# Stop the Patient Advocacy Agent server.
#
# Usage:
#   bash scripts/stop_server.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDFILE="$PROJECT_ROOT/.server.pid"

if [[ ! -f "$PIDFILE" ]]; then
    echo "No server PID file found. Server may not be running."
    exit 0
fi

SERVER_PID=$(cat "$PIDFILE")

if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Stopping server (PID: $SERVER_PID)..."
    kill "$SERVER_PID"

    # Wait up to 5 seconds for graceful shutdown
    for _ in {1..10}; do
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done

    # Force kill if still running
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Graceful shutdown timed out, force killing..."
        kill -9 "$SERVER_PID" 2>/dev/null
    fi

    echo "Server stopped."
else
    echo "Server process (PID: $SERVER_PID) is not running."
fi

rm -f "$PIDFILE"
