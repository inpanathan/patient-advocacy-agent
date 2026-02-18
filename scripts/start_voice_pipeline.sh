#!/usr/bin/env bash
# Start the voice pipeline (WebRTC server).
#
# Usage:
#   bash scripts/start_voice_pipeline.sh
#
# Once started, press 'b' to send to background, or 'q' to stop.
#
# Covers: REQ-RUN-001

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export SERVICE_NAME="Voice Pipeline"
export PIDFILE="$PROJECT_ROOT/.voice_pipeline.pid"
export LOGFILE="$PROJECT_ROOT/.voice_pipeline.log"
export CMD="uv run python -m src.pipelines.webrtc_server"

source "$PROJECT_ROOT/scripts/_run_with_background.sh"
