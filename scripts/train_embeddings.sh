#!/usr/bin/env bash
# Run SigLIP-2 embedding fine-tuning.
#
# Usage:
#   bash scripts/train_embeddings.sh
#   bash scripts/train_embeddings.sh --config configs/experiments/default.yaml
#
# Once started, press 'b' to send to background, or 'q' to stop.
#
# Covers: REQ-RUN-001

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

CONFIG="${1:-configs/experiments/default.yaml}"

export SERVICE_NAME="Embedding Fine-Tuning"
export PIDFILE="$PROJECT_ROOT/.train_embeddings.pid"
export LOGFILE="$PROJECT_ROOT/.train_embeddings.log"
export CMD="uv run python -m src.pipelines.train_embeddings --config $CONFIG"

source "$PROJECT_ROOT/scripts/_run_with_background.sh"
