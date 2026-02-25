#!/usr/bin/env bash
# Merge Playwright screen recording with Piper TTS narration into final MP4.
#
# Usage: bash demo/post_process.sh <video.webm> <narration.wav> <output.mp4>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VIDEO="${1:?Usage: post_process.sh <video.webm> <narration.wav> <output.mp4>}"
NARRATION="${2:?Usage: post_process.sh <video.webm> <narration.wav> <output.mp4>}"
OUTPUT="${3:-${SCRIPT_DIR}/output/demo_final.mp4}"

if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found. Install with: sudo apt install ffmpeg"
    exit 1
fi

if [ ! -f "$VIDEO" ]; then
    echo "ERROR: Video file not found: $VIDEO"
    exit 1
fi

if [ ! -f "$NARRATION" ]; then
    echo "ERROR: Narration file not found: $NARRATION"
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

echo "Merging video + narration..."
echo "  Video:     $VIDEO"
echo "  Narration: $NARRATION"
echo "  Output:    $OUTPUT"

ffmpeg -y \
    -i "$VIDEO" \
    -i "$NARRATION" \
    -c:v libx264 -crf 18 -preset slow \
    -c:a aac -b:a 192k \
    -map 0:v:0 -map 1:a:0 \
    -shortest \
    -movflags +faststart \
    "$OUTPUT"

echo ""
echo "Done! Output: $OUTPUT"
echo "Duration: $(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" 2>/dev/null | cut -d. -f1)s"
echo "Size: $(du -h "$OUTPUT" | cut -f1)"
