#!/usr/bin/env bash
# Download Piper TTS voice models for supported languages.
#
# Usage:
#   bash scripts/download_piper_voices.sh            # Download all supported voices
#   bash scripts/download_piper_voices.sh en hi es    # Download specific languages only
#
# Voice models are stored in models/piper/ as .onnx + .onnx.json pairs.
# The Piper release repository is: https://github.com/rhasspy/piper/blob/master/VOICES.md
#
# Covers: REQ-RUN-001

set -euo pipefail

PIPER_VOICES_DIR="${VOICE__PIPER_VOICES_DIR:-models/piper}"
PIPER_RELEASE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

# Supported language → voice model mapping
# Format: "lang_code|voice_path|voice_name"
# voice_path is the HF repo subdirectory structure under piper-voices
declare -A VOICE_MAP=(
    [en]="en/en_US/lessac/medium|en_US-lessac-medium"
    [hi]="hi/hi_IN/swara/medium|hi_IN-swara-medium"
    [es]="es/es_ES/sharvard/medium|es_ES-sharvard-medium"
    [bn]="bn/bn_BD/openjtalk/medium|bn_BD-openjtalk-medium"
    [ta]="ta/ta_IN/anbu/medium|ta_IN-anbu-medium"
    [sw]="sw/sw_KE/lanfrica/medium|sw_KE-lanfrica-medium"
)

# --------------------------------------------------------------------------

info()  { echo "  [INFO]  $*"; }
ok()    { echo "  [OK]    $*"; }
warn()  { echo "  [WARN]  $*" >&2; }
fail()  { echo "  [FAIL]  $*" >&2; }

download_voice() {
    local lang="$1"
    local entry="${VOICE_MAP[$lang]:-}"

    if [[ -z "$entry" ]]; then
        warn "No voice model defined for language: $lang (skipping)"
        return 1
    fi

    local voice_path="${entry%%|*}"
    local voice_name="${entry##*|}"
    local onnx_file="${PIPER_VOICES_DIR}/${voice_name}.onnx"
    local json_file="${PIPER_VOICES_DIR}/${voice_name}.onnx.json"

    # Skip if already downloaded
    if [[ -f "$onnx_file" && -f "$json_file" ]]; then
        ok "$lang ($voice_name) — already exists, skipping"
        return 0
    fi

    local onnx_url="${PIPER_RELEASE_BASE}/${voice_path}/${voice_name}.onnx"
    local json_url="${PIPER_RELEASE_BASE}/${voice_path}/${voice_name}.onnx.json"

    info "Downloading $lang → $voice_name ..."

    if ! curl -fSL --progress-bar -o "$onnx_file" "$onnx_url"; then
        fail "Failed to download $onnx_url"
        rm -f "$onnx_file"
        return 1
    fi

    if ! curl -fsSL -o "$json_file" "$json_url"; then
        fail "Failed to download $json_url"
        rm -f "$json_file"
        return 1
    fi

    ok "$lang ($voice_name) — downloaded"
    return 0
}

# --------------------------------------------------------------------------

echo "=== Piper TTS Voice Model Downloader ==="
echo ""

# Determine which languages to download
if [[ $# -gt 0 ]]; then
    LANGUAGES=("$@")
else
    LANGUAGES=("en" "hi" "es" "bn" "ta" "sw")
fi

echo "Target directory: $PIPER_VOICES_DIR"
echo "Languages: ${LANGUAGES[*]}"
echo ""

mkdir -p "$PIPER_VOICES_DIR"

success=0
failed=0

for lang in "${LANGUAGES[@]}"; do
    if download_voice "$lang"; then
        ((success++))
    else
        ((failed++))
    fi
done

echo ""
echo "=== Download complete: $success succeeded, $failed failed ==="

if [[ $failed -gt 0 ]]; then
    echo ""
    echo "Some voice models failed to download. This may be because:"
    echo "  - The voice model doesn't exist in the Piper release"
    echo "  - Network connectivity issues"
    echo ""
    echo "You can re-run this script to retry failed downloads."
    echo "The application will fall back to English if a voice is missing."
    exit 1
fi
