#!/usr/bin/env bash
# Full quality check: lint, format, typecheck, tests.
#
# Usage:
#   bash scripts/check_all.sh          # run everything
#   bash scripts/check_all.sh --fix    # auto-fix lint and format issues
#
# Exit code is non-zero if any step fails.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=true
fi

PASSED=0
FAILED=0

run_step() {
    local name="$1"
    shift
    echo ""
    echo "=== $name ==="
    if "$@"; then
        echo "  PASSED"
        ((PASSED++))
    else
        echo "  FAILED"
        ((FAILED++))
    fi
}

if [[ "$FIX_MODE" == true ]]; then
    run_step "Ruff lint (autofix)" uv run ruff check src/ tests/ --fix
    run_step "Ruff format" uv run ruff format src/ tests/
else
    run_step "Ruff lint" uv run ruff check src/ tests/
    run_step "Ruff format check" uv run ruff format --check src/ tests/
fi

run_step "Mypy typecheck" uv run mypy src/ --ignore-missing-imports
run_step "Tests" uv run pytest tests/ -x -q --tb=short

echo ""
echo "=== Summary ==="
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"

if [[ $FAILED -gt 0 ]]; then
    echo ""
    echo "Quality check FAILED ($FAILED step(s) failed)"
    exit 1
else
    echo ""
    echo "All checks PASSED"
    exit 0
fi
