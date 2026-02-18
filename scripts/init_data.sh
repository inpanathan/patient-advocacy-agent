#!/usr/bin/env bash
# =============================================================================
# init_data.sh — Initialize SCIN data directory and download/mount data
#
# Usage:
#   ./scripts/init_data.sh
#   ./scripts/init_data.sh --mock    # Create mock data for development
#
# Covers: REQ-RUN-001
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

MOCK_MODE=false
if [[ "${1:-}" == "--mock" ]]; then
    MOCK_MODE=true
fi

echo -e "${GREEN}=== SCIN Data Initialization ===${NC}"

# Create data directories
mkdir -p data/raw/scin/images
mkdir -p data/interim
mkdir -p data/processed
mkdir -p data/chroma

if [ "$MOCK_MODE" = true ]; then
    echo -e "${YELLOW}Creating mock SCIN data for development...${NC}"

    # Copy sample fixture as mock data
    if [ -f "tests/fixtures/scin_sample.json" ]; then
        cp tests/fixtures/scin_sample.json data/raw/scin/metadata.json
        echo -e "${GREEN}✓ Mock metadata.json created from test fixtures${NC}"
    else
        echo -e "${YELLOW}Warning: tests/fixtures/scin_sample.json not found${NC}"
    fi

    # Create placeholder images
    for i in $(seq -w 1 6); do
        touch "data/raw/scin/images/00${i}.jpg"
    done
    echo -e "${GREEN}✓ Mock image placeholders created${NC}"

else
    echo ""
    echo "To download the real SCIN dataset from Google Cloud Storage:"
    echo "  bash scripts/download_scin.sh"
    echo ""
    echo "Prerequisites:"
    echo "  uv pip install google-cloud-storage"
    echo "  gcloud auth application-default login"
    echo ""
    echo "For development with mock data, run:"
    echo "  bash scripts/init_data.sh --mock"
fi

echo ""
echo -e "${GREEN}=== Data directories ready ===${NC}"
