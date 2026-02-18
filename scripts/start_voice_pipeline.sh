#!/usr/bin/env bash
# Start the voice pipeline (WebRTC server)
# Covers: REQ-RUN-001
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "=== Voice Pipeline ==="
uv run python -m src.pipelines.webrtc_server
