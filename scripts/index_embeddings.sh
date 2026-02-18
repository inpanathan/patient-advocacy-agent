#!/usr/bin/env bash
# Index SCIN embeddings into vector store
# Covers: REQ-RUN-001
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "=== Embedding Indexing ==="
uv run python -m src.pipelines.index_embeddings
