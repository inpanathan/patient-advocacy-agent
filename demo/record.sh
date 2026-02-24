#!/usr/bin/env bash
# Master orchestrator: generate narration, record screen, merge into final MP4.
#
# Usage: bash demo/record.sh
#
# Prerequisites:
#   1. sudo apt install ffmpeg
#   2. cd demo/playwright && npm install && npx playwright install chromium
#   3. Backend running on :8001 (healthy)
#   4. Frontend running on :5173
#   5. Database seeded (uv run python scripts/seed_db.py)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEMO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ─── Prerequisites ────────────────────────────────────────────────────────────

log "Checking prerequisites..."

command -v ffmpeg  &>/dev/null || fail "ffmpeg not found. Install: sudo apt install ffmpeg"
command -v piper   &>/dev/null || fail "piper not found. Install: pip install piper-tts"
command -v npx     &>/dev/null || fail "npx not found. Install: sudo apt install nodejs npm"

# Check Playwright is installed
if [ ! -d "$SCRIPT_DIR/playwright/node_modules" ]; then
    log "Installing Playwright..."
    (cd "$SCRIPT_DIR/playwright" && npm install && npx playwright install chromium)
fi

# Check backend health
if ! curl -s --max-time 5 http://localhost:8001/health > /dev/null 2>&1; then
    fail "Backend not healthy at http://localhost:8001/health. Start it first."
fi

# Check frontend (Vite uses basicSsl plugin, so it's HTTPS)
if ! curl -sk --max-time 5 https://localhost:5173 > /dev/null 2>&1; then
    fail "Frontend not running at https://localhost:5173. Start it first."
fi

# Check dashboard page is served by backend
if ! curl -s --max-time 5 http://localhost:8001/dashboard > /dev/null 2>&1; then
    warn "Dashboard page not accessible at http://localhost:8001/dashboard — Scene 4 may fail"
fi

# Check Piper model exists
PIPER_MODEL="$PROJECT_ROOT/models/piper/en_US-lessac-medium.onnx"
if [ ! -f "$PIPER_MODEL" ]; then
    fail "Piper model not found at $PIPER_MODEL"
fi

# Check demo image exists
DEMO_IMAGE="$PROJECT_ROOT/data/raw/scin/images/-101827005996397499_1.jpg"
if [ ! -f "$DEMO_IMAGE" ]; then
    warn "Demo SCIN image not found at $DEMO_IMAGE — image upload will be skipped"
fi

log "All prerequisites OK."

# ─── Step 1: Reset + Seed Database ────────────────────────────────────────────

log "Step 1/5: Seeding database..."
(cd "$PROJECT_ROOT" && uv run python scripts/seed_db.py 2>&1) || warn "Seed script returned non-zero (may be OK if already seeded)"

# ─── Step 2: Generate Narration ───────────────────────────────────────────────

log "Step 2/5: Generating narration with Piper TTS..."
(cd "$PROJECT_ROOT" && uv run python demo/narration/generate_narration.py)

if [ ! -f "$OUTPUT_DIR/narration/timing.json" ]; then
    fail "Narration generation failed — timing.json not found"
fi

log "Narration generated."

# ─── Step 3: Record Screen with Playwright ────────────────────────────────────

log "Step 3/5: Recording screen with Playwright..."
(cd "$SCRIPT_DIR/playwright" && npx playwright test demo-recording.spec.ts --reporter=list 2>&1) || {
    warn "Playwright test had issues — checking for video output anyway"
}

# Find the video file Playwright produced
VIDEO_FILE=$(find "$OUTPUT_DIR/playwright-results" -name "*.webm" -type f 2>/dev/null | head -1)
if [ -z "$VIDEO_FILE" ]; then
    fail "No video file found in $OUTPUT_DIR/playwright-results/"
fi

log "Screen recording: $VIDEO_FILE"

# ─── Step 4: Build Combined Audio Track ───────────────────────────────────────

log "Step 4/5: Building combined narration track..."
(cd "$PROJECT_ROOT" && uv run python demo/narration/build_audio_track.py)

NARRATION_FILE="$OUTPUT_DIR/narration_combined.wav"
if [ ! -f "$NARRATION_FILE" ]; then
    fail "Combined narration not found at $NARRATION_FILE"
fi

log "Combined narration: $NARRATION_FILE"

# ─── Step 5: Merge Video + Audio ──────────────────────────────────────────────

log "Step 5/5: Merging video + narration with ffmpeg..."
bash "$SCRIPT_DIR/post_process.sh" "$VIDEO_FILE" "$NARRATION_FILE" "$OUTPUT_DIR/demo_final.mp4"

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
log "Demo video ready!"
echo ""
echo "  Output: $OUTPUT_DIR/demo_final.mp4"
echo ""
echo "  Next steps:"
echo "    1. Review the video: mpv $OUTPUT_DIR/demo_final.mp4"
echo "    2. (Optional) Trim/polish in a video editor"
echo "    3. Upload to Kaggle writeup"
echo "============================================"
