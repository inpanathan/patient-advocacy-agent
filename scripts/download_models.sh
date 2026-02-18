#!/usr/bin/env bash
# Download all required local models for MODEL_BACKEND=local.
#
# Usage:
#   bash scripts/download_models.sh
#
# This pre-caches model weights so the first real inference run
# doesn't incur a long download. Models are stored in the
# Hugging Face cache (~/.cache/huggingface/).

set -euo pipefail

echo "=== Downloading MedGemma 4B (instruction-tuned) ==="
uv run python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
model_id = 'google/medgemma-4b-it'
print(f'Downloading tokenizer: {model_id}')
AutoTokenizer.from_pretrained(model_id)
print(f'Downloading model: {model_id}')
AutoModelForCausalLM.from_pretrained(model_id)
print('MedGemma 4B download complete.')
"

echo ""
echo "=== Downloading SigLIP-2 (so400m-patch14-384) ==="
uv run python -c "
from transformers import AutoModel, AutoProcessor
model_id = 'google/siglip-so400m-patch14-384'
print(f'Downloading processor: {model_id}')
AutoProcessor.from_pretrained(model_id)
print(f'Downloading model: {model_id}')
AutoModel.from_pretrained(model_id)
print('SigLIP-2 download complete.')
"

echo ""
echo "=== Downloading Faster-Whisper large-v3 ==="
uv run python -c "
from faster_whisper import WhisperModel
print('Downloading Whisper large-v3 (CPU mode for caching)...')
WhisperModel('large-v3', device='cpu', compute_type='int8')
print('Faster-Whisper large-v3 download complete.')
"

echo ""
echo "=== Downloading Piper TTS voice models ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${SCRIPT_DIR}/download_piper_voices.sh"

echo ""
echo "=== All model downloads complete ==="
