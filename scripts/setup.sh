#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-command developer environment setup
#
# Usage:
#   ./scripts/setup.sh
#
# What it does:
#   1. Checks for required tools (Python 3.12+, uv, git)
#   2. Creates virtual environment and installs dependencies
#   3. Copies .env.example to .env if .env doesn't exist
#   4. Sets up pre-commit hooks
#   5. Creates required data directories
#   6. Verifies the setup by running tests
#
# Covers: REQ-RUN-001
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}=== Patient Advocacy Agent — Dev Setup ===${NC}"
echo ""

# ---- Check Python ----
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 not found. Install Python 3.12+.${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓ Python $PY_VERSION${NC}"

# ---- Check uv ----
if ! command -v uv &>/dev/null; then
    echo -e "${YELLOW}uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "${GREEN}✓ uv found${NC}"

# ---- Install dependencies ----
echo ""
echo "Installing dependencies..."
uv sync --extra dev --extra ml --extra voice
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ---- Create .env if missing ----
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from .env.example${NC}"
else
    echo -e "${YELLOW}✓ .env already exists (skipped)${NC}"
fi

# ---- Set up pre-commit ----
if [ -f ".pre-commit-config.yaml" ]; then
    uv run pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
fi

# ---- Create directories ----
mkdir -p data/raw data/interim data/processed data/chroma
mkdir -p models
mkdir -p configs/experiments
mkdir -p docs/adr docs/architecture docs/design docs/runbook
mkdir -p coding-agent/logs
echo -e "${GREEN}✓ Directories created${NC}"

# ---- Verify ----
echo ""
echo "Running verification tests..."
uv run pytest tests/ -x -q --tb=short
echo ""
echo -e "${GREEN}=== Setup complete! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run the server:  uv run python main.py"
echo "  3. Run tests:       uv run pytest tests/ -x -q"
echo "  4. Run linter:      uv run ruff check src/ tests/"
