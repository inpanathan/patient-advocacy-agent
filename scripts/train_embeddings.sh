#!/usr/bin/env bash
# =============================================================================
# train_embeddings.sh — Run SigLIP-2 embedding fine-tuning
#
# Usage:
#   ./scripts/train_embeddings.sh
#   ./scripts/train_embeddings.sh --config configs/experiments/default.yaml
#
# Covers: REQ-RUN-001
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

CONFIG="${1:-configs/experiments/default.yaml}"

echo "=== Embedding Fine-Tuning ==="
echo "Config: $CONFIG"
echo ""

uv run python -m src.pipelines.train_embeddings --config "$CONFIG"
