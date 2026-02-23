#!/usr/bin/env bash
# Fine-tune MedGemma 4B with QLoRA on SCIN dermatology data.
#
# Usage:
#   bash scripts/finetune_medgemma.sh              # Full pipeline: prep → train → eval
#   bash scripts/finetune_medgemma.sh --prep-only   # Data preparation only
#   bash scripts/finetune_medgemma.sh --train-only   # Training only (data must exist)
#   bash scripts/finetune_medgemma.sh --eval-only    # Evaluation only (adapters must exist)
#
# Requires: SCIN data present, GPU recommended (RTX 3090+ with 24GB VRAM).
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

ACTION="${1:-full}"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  MedGemma QLoRA Fine-Tuning Pipeline${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

SCIN_METADATA="data/raw/scin/metadata.json"
TRAIN_DATA="data/processed/finetune/train.jsonl"
VAL_DATA="data/processed/finetune/val.jsonl"
ADAPTER_DIR="models/medgemma-lora-derm"
EVAL_RESULTS="data/processed/finetune/eval_results.json"

# ── Preflight checks ──────────────────────────────────────────────────
if [[ ! -f "$SCIN_METADATA" ]]; then
    echo -e "${RED}SCIN metadata not found at ${SCIN_METADATA}${NC}"
    echo "  Run: bash scripts/init_data.sh --mock"
    exit 1
fi
echo -e "${GREEN}✓${NC} SCIN metadata found"

# ── Step 1: Data Preparation ──────────────────────────────────────────
if [[ "$ACTION" != "--train-only" && "$ACTION" != "--eval-only" ]]; then
    echo ""
    echo -e "${CYAN}Step 1/3: Preparing fine-tuning data...${NC}"
    uv run python -m src.pipelines.prepare_finetune_data \
        --data-dir data/raw/scin \
        --output-dir data/processed/finetune \
        --val-fraction 0.1

    if [[ -f "$TRAIN_DATA" && -f "$VAL_DATA" ]]; then
        TRAIN_COUNT=$(wc -l < "$TRAIN_DATA")
        VAL_COUNT=$(wc -l < "$VAL_DATA")
        echo -e "${GREEN}✓${NC} Data prepared: ${TRAIN_COUNT} train, ${VAL_COUNT} val"
    else
        echo -e "${RED}Data preparation failed${NC}"
        exit 1
    fi
fi

if [[ "$ACTION" == "--prep-only" ]]; then
    echo ""
    echo -e "${GREEN}✓ Data preparation complete${NC}"
    exit 0
fi

# ── Step 2: QLoRA Training ───────────────────────────────────────────
if [[ "$ACTION" != "--eval-only" ]]; then
    echo ""
    echo -e "${CYAN}Step 2/3: Fine-tuning MedGemma with QLoRA...${NC}"
    echo "  Config: r=16, alpha=32, epochs=3, lr=2e-4, batch=4, grad_accum=4"
    echo ""

    CMD="uv run python -m src.pipelines.finetune_medgemma \
        --train-data ${TRAIN_DATA} \
        --val-data ${VAL_DATA} \
        --output-dir ${ADAPTER_DIR} \
        --epochs 3 \
        --lr 2e-4 \
        --batch-size 4 \
        --grad-accum 4 \
        --lora-r 16 \
        --lora-alpha 32"

    export SERVICE_NAME="MedGemma QLoRA Training"
    export PIDFILE="$PROJECT_ROOT/.finetune.pid"
    export LOGFILE="$PROJECT_ROOT/.finetune.log"
    export CMD

    if [[ "$ACTION" == "--train-only" ]]; then
        source "$PROJECT_ROOT/scripts/_run_with_background.sh"
        exit 0
    fi

    # For full pipeline, run inline (not backgroundable)
    eval "$CMD"

    if [[ -d "$ADAPTER_DIR" ]]; then
        echo -e "${GREEN}✓${NC} LoRA adapters saved to ${ADAPTER_DIR}"
    else
        echo -e "${RED}Training failed — no adapters saved${NC}"
        exit 1
    fi
fi

# ── Step 3: Evaluation ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}Step 3/3: Evaluating fine-tuned model...${NC}"

uv run python -m src.evaluation.finetune_eval \
    --val-data "$VAL_DATA" \
    --output "$EVAL_RESULTS"

if [[ -f "$EVAL_RESULTS" ]]; then
    echo -e "${GREEN}✓${NC} Evaluation results saved to ${EVAL_RESULTS}"
    echo ""
    echo "Results:"
    python3 -m json.tool "$EVAL_RESULTS"
else
    echo -e "${YELLOW}Evaluation did not produce results${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Fine-tuning pipeline complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "  1. Set LLM__LORA_ADAPTER_PATH=models/medgemma-lora-derm in .env"
echo "  2. Restart the server: bash scripts/start_server.sh"
echo "  3. The LoRA adapter will be loaded automatically at inference time"
