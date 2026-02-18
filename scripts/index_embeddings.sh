#!/usr/bin/env bash
# Index SCIN embeddings into the vector store.
#
# Usage:
#   bash scripts/index_embeddings.sh
#
# Once started, press 'b' to send to background, or 'q' to stop.
#
# Covers: REQ-RUN-001

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export SERVICE_NAME="Embedding Indexing"
export PIDFILE="$PROJECT_ROOT/.index_embeddings.pid"
export LOGFILE="$PROJECT_ROOT/.index_embeddings.log"
export CMD="uv run python -m src.pipelines.index_embeddings"

source "$PROJECT_ROOT/scripts/_run_with_background.sh"
