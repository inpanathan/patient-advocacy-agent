#!/usr/bin/env bash
# Sync common_requirements_controller.json from common_requirements.md.
# Preserves existing implement/enable flags; adds new reqs with "N"/"N".
#
# Usage:
#   ./scripts/sync_requirements.sh            # apply changes
#   ./scripts/sync_requirements.sh --dry-run   # preview only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/sync_requirements_controller.py" "$@"
