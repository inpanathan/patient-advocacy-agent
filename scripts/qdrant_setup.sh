#!/usr/bin/env bash
# Create or verify the Qdrant collection for SCIN embeddings (idempotent).
#
# Usage:
#   bash scripts/qdrant_setup.sh              # Create collection if missing
#   bash scripts/qdrant_setup.sh --drop       # Drop and recreate (dev only)
#   bash scripts/qdrant_setup.sh --status     # Show collection info
#
# Requires: Qdrant running on the configured host/port.

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
DIMENSION="${EMBEDDING__DIMENSION:-1152}"  # MedSigLIP-448 outputs 1152-dim vectors
APP_ENV="${APP_ENV:-dev}"
QDRANT_URL="http://${QDRANT_HOST}:${QDRANT_PORT}"

# ── Parse arguments ────────────────────────────────────────────────────
ACTION="${1:-create}"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Qdrant Collection Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Host:       $QDRANT_HOST"
echo "  Port:       $QDRANT_PORT"
echo "  Collection: $COLLECTION"
echo "  Dimension:  $DIMENSION"
echo ""

# ── Check Qdrant is running ────────────────────────────────────────────
if ! curl -sf --max-time 3 "${QDRANT_URL}/healthz" > /dev/null 2>&1; then
    echo -e "${RED}✗ Qdrant is not reachable at ${QDRANT_URL}${NC}"
    echo "  Start it with: docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant"
    exit 1
fi
echo -e "${GREEN}✓${NC} Qdrant is running"

# ── Helper: check if collection exists ─────────────────────────────────
collection_exists() {
    local status
    status=$(curl -sf -o /dev/null -w "%{http_code}" "${QDRANT_URL}/collections/${COLLECTION}")
    [[ "$status" == "200" ]]
}

# ── Helper: get collection point count ─────────────────────────────────
collection_count() {
    curl -sf "${QDRANT_URL}/collections/${COLLECTION}" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "0"
}

# ── Status ──────────────────────────────────────────────────────────────
if [[ "$ACTION" == "--status" ]]; then
    if collection_exists; then
        echo -e "${GREEN}✓${NC} Collection '${COLLECTION}' exists"
        echo ""
        curl -sf "${QDRANT_URL}/collections/${COLLECTION}" | python3 -m json.tool
    else
        echo -e "${YELLOW}○${NC} Collection '${COLLECTION}' does not exist"
    fi
    exit 0
fi

# ── Drop ────────────────────────────────────────────────────────────────
if [[ "$ACTION" == "--drop" ]]; then
    if [[ "$APP_ENV" == "production" ]]; then
        echo -e "${RED}✗ Drop is blocked in production (APP_ENV=production)${NC}"
        exit 1
    fi

    if collection_exists; then
        COUNT=$(collection_count)
        echo -e "${YELLOW}⚠  WARNING: This will DELETE collection '${COLLECTION}' with ${COUNT} points.${NC}"
        echo ""
        read -rp "Type 'yes' to confirm: " answer
        if [[ "$answer" != "yes" ]]; then
            echo -e "${RED}✗ Aborted.${NC}"
            exit 1
        fi
        curl -sf -X DELETE "${QDRANT_URL}/collections/${COLLECTION}" > /dev/null
        echo -e "${GREEN}✓${NC} Deleted collection '${COLLECTION}'"
    else
        echo -e "${YELLOW}○${NC} Collection '${COLLECTION}' does not exist, nothing to drop"
    fi

    # Fall through to recreate
    echo ""
fi

# ── Create (idempotent) ────────────────────────────────────────────────
if collection_exists; then
    COUNT=$(collection_count)
    echo -e "${GREEN}✓${NC} Collection '${COLLECTION}' already exists (${COUNT} points)"
else
    curl -sf -X PUT "${QDRANT_URL}/collections/${COLLECTION}" \
        -H "Content-Type: application/json" \
        -d "{
            \"vectors\": {
                \"size\": ${DIMENSION},
                \"distance\": \"Cosine\"
            }
        }" > /dev/null
    echo -e "${GREEN}✓${NC} Created collection '${COLLECTION}' (dimension=${DIMENSION}, distance=Cosine)"
fi

echo ""
echo -e "${GREEN}✓ Qdrant setup complete${NC}"
echo ""
echo "Next steps:"
echo "  bash scripts/qdrant_index.sh              # Index SCIN embeddings"
echo "  bash scripts/qdrant_index.sh --force       # Force re-index from scratch"
echo "  bash scripts/qdrant_setup.sh --status      # Verify collection"
