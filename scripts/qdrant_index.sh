#!/usr/bin/env bash
# Index SCIN embeddings into Qdrant (skips if already complete).
#
# Usage:
#   bash scripts/qdrant_index.sh              # Index (skip if Qdrant is full)
#   bash scripts/qdrant_index.sh --force      # Drop collection and re-index
#   bash scripts/qdrant_index.sh --status     # Show index vs dataset counts
#
# Requires: Qdrant running, SCIN data present (bash scripts/init_data.sh).
#
# Once started, press 'b' to send to background, or 'q' to stop.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Colors ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Load config from .env ──────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" == \#* ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        if [[ "$key" == VECTOR_STORE__* || "$key" == EMBEDDING__* || "$key" == APP_ENV ]]; then
            export "$key=$value"
        fi
    done < "$ENV_FILE"
    set +a
fi

QDRANT_HOST="${VECTOR_STORE__QDRANT_HOST:-localhost}"
QDRANT_PORT="${VECTOR_STORE__QDRANT_PORT:-6333}"
COLLECTION="${VECTOR_STORE__COLLECTION_NAME:-scin_embeddings}"
QDRANT_URL="http://${QDRANT_HOST}:${QDRANT_PORT}"
SCIN_METADATA="data/raw/scin/metadata.json"

ACTION="${1:-index}"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Qdrant Embedding Indexer${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────
if ! curl -sf --max-time 3 "${QDRANT_URL}/healthz" > /dev/null 2>&1; then
    echo -e "${RED}✗ Qdrant is not reachable at ${QDRANT_URL}${NC}"
    echo "  Start it with: docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant"
    exit 1
fi
echo -e "${GREEN}✓${NC} Qdrant is running"

if [[ ! -f "$SCIN_METADATA" ]]; then
    echo -e "${RED}✗ SCIN metadata not found at ${SCIN_METADATA}${NC}"
    echo "  Run: bash scripts/init_data.sh --mock"
    exit 1
fi
echo -e "${GREEN}✓${NC} SCIN metadata found"

# ── Count expected vs indexed ──────────────────────────────────────────
EXPECTED=$(python3 -c "import json; d=json.load(open('${SCIN_METADATA}')); print(len(d) if isinstance(d,list) else len(d.get('records',[])))")
INDEXED=$(curl -sf "${QDRANT_URL}/collections/${COLLECTION}" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null \
    || echo "0")

echo ""
echo "  SCIN records:  $EXPECTED"
echo "  Qdrant points: $INDEXED"
echo ""

# ── Status only ─────────────────────────────────────────────────────────
if [[ "$ACTION" == "--status" ]]; then
    if [[ "$INDEXED" -ge "$EXPECTED" && "$INDEXED" -gt 0 ]]; then
        echo -e "${GREEN}✓ Index is complete${NC}"
    elif [[ "$INDEXED" -gt 0 ]]; then
        echo -e "${YELLOW}○ Index is partial (${INDEXED}/${EXPECTED})${NC}"
    else
        echo -e "${YELLOW}○ Index is empty${NC}"
    fi
    exit 0
fi

# ── Skip if already complete ───────────────────────────────────────────
if [[ "$ACTION" != "--force" && "$INDEXED" -ge "$EXPECTED" && "$INDEXED" -gt 0 ]]; then
    echo -e "${GREEN}✓ Index is already complete (${INDEXED}/${EXPECTED}), skipping.${NC}"
    echo "  Use --force to re-index from scratch."
    exit 0
fi

# ── Ensure collection exists ───────────────────────────────────────────
bash "$PROJECT_ROOT/scripts/qdrant_setup.sh" 2>/dev/null || true

# ── Build command ──────────────────────────────────────────────────────
CMD="uv run python -m src.pipelines.index_embeddings"
if [[ "$ACTION" == "--force" ]]; then
    echo -e "${YELLOW}⚠  Force re-index requested — collection will be recreated${NC}"
    CMD="$CMD --force-reindex"
fi

echo ""
echo "Starting embedding indexer..."
echo ""

export SERVICE_NAME="Qdrant Indexer"
export PIDFILE="$PROJECT_ROOT/.qdrant_index.pid"
export LOGFILE="$PROJECT_ROOT/.qdrant_index.log"
export CMD

source "$PROJECT_ROOT/scripts/_run_with_background.sh"
