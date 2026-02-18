#!/usr/bin/env bash
# =============================================================================
# start_autonomous_build.sh
#
# Launches Claude Code in fully autonomous "hands-off until done" mode to build
# the Patient Advocacy Agent from the implementation plan.
#
# The agent will:
#   - Read CLAUDE.md for operating instructions
#   - Read the implementation plan for phase/task breakdown
#   - Execute each phase, writing code, tests, and docs
#   - Self-correct via build-test-fix feedback loops
#   - Stub external dependencies it can't access
#   - Commit after each completed task
#   - Log phase completions and blockers
#   - Continue until all phases are Done or all unblocked tasks exhausted
#
# Usage:
#   ./scripts/start_autonomous_build.sh                 # Start from Phase 0
#   ./scripts/start_autonomous_build.sh --phase 3       # Resume from Phase 3
#   ./scripts/start_autonomous_build.sh --dry-run       # Show prompt, don't launch
#   ./scripts/start_autonomous_build.sh --safe           # Prompt-per-tool mode (safer)
#
# Modes:
#   Default (no flag):  Full autonomy. Uses --dangerously-skip-permissions.
#                       The agent runs without asking permission for any tool.
#                       Use this for true hands-off execution.
#
#   --safe:             Permission-guarded mode. Claude will ask before
#                       running shell commands. Slower but you can review.
#
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ---- Defaults ----
START_PHASE=0
DRY_RUN=false
SAFE_MODE=false

# ---- Parse args ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phase)
            START_PHASE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --safe)
            SAFE_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--phase N] [--dry-run] [--safe]"
            echo ""
            echo "Options:"
            echo "  --phase N   Start/resume from phase N (default: 0)"
            echo "  --dry-run   Print the prompt without launching"
            echo "  --safe      Run with permission prompts (not fully autonomous)"
            echo ""
            echo "Examples:"
            echo "  $0                    # Full autonomous build from scratch"
            echo "  $0 --phase 3          # Resume from Phase 3"
            echo "  $0 --safe --phase 0   # Build with permission prompts"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}============================================${NC}"
echo -e "${CYAN}${BOLD}  Patient Advocacy Agent — Autonomous Build ${NC}"
echo -e "${CYAN}${BOLD}============================================${NC}"
echo ""

# ---- Prerequisite Checks ----
echo -e "${YELLOW}Checking prerequisites...${NC}"

ERRORS=0

# Check claude is installed
if ! command -v claude &>/dev/null; then
    echo -e "${RED}  ✗ 'claude' CLI not found.${NC}"
    echo -e "    Install: ${CYAN}npm install -g @anthropic-ai/claude-code${NC}"
    ERRORS=$((ERRORS + 1))
else
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "${GREEN}  ✓ claude CLI found ($CLAUDE_VERSION)${NC}"
fi

# Check uv is installed
if ! command -v uv &>/dev/null; then
    echo -e "${RED}  ✗ 'uv' not found.${NC}"
    echo -e "    Install: ${CYAN}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}  ✓ uv found${NC}"
fi

# Check git repo
if [ ! -d ".git" ]; then
    echo -e "${RED}  ✗ Not a git repository${NC}"
    ERRORS=$((ERRORS + 1))
else
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo -e "${GREEN}  ✓ git repository (branch: $BRANCH)${NC}"
fi

# Check key files exist
KEY_FILES=(
    "CLAUDE.md"
    "coding-agent/plans/implementation_plan_v1.md"
    "docs/requirements/project_requirements_v1.md"
    "docs/requirements/common_requirements.md"
    "docs/requirements/common_requirements_controller.json"
    "docs/requirements/documentation_requirements.md"
    "docs/requirements/documentation_requirements_controller.json"
)

for f in "${KEY_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo -e "${RED}  ✗ Missing: $f${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}  ✓ $f${NC}"
    fi
done

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo -e "${RED}${BOLD}$ERRORS prerequisite(s) failed. Fix them and re-run.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}${BOLD}All prerequisites passed.${NC}"
echo ""

# ---- Ensure directories exist ----
mkdir -p coding-agent/logs
mkdir -p docs/adr docs/architecture docs/design docs/runbook
mkdir -p tests/unit tests/integration tests/evaluation tests/safety tests/fixtures
mkdir -p .github/workflows
mkdir -p src/models/mocks src/models/protocols

# ---- Build the prompt ----
if [ "$START_PHASE" -eq 0 ]; then
    RESUME_CTX="Start from Phase 0, Task 0.1 and work forward through all 11 phases."
    FIRST_STEPS="1. Read CLAUDE.md (your full operating instructions).
2. Read coding-agent/plans/implementation_plan_v1.md (your task list).
3. Begin Phase 0, Task 0.1: Fix pyproject.toml.
4. Work through every task in Phase 0.
5. After Phase 0, proceed to Phase 1 AND start Phase 4 where possible (they parallelize).
6. Continue phase by phase until done."
else
    RESUME_CTX="Resume from Phase $START_PHASE. Read the implementation plan to find the first Pending task and continue from there."
    FIRST_STEPS="1. Read CLAUDE.md (your full operating instructions).
2. Read coding-agent/plans/implementation_plan_v1.md to see current progress.
3. Find the first Pending task in Phase $START_PHASE.
4. Continue working through all remaining phases until done."
fi

read -r -d '' PROMPT << PROMPT_EOF || true
You are the autonomous build agent for the Patient Advocacy Agent project.

Your mission: implement the ENTIRE project from its current state to completion, working
hands-off without human intervention. You have full autonomy to create files, run commands,
install packages, and make architectural decisions.

## How to Start

$FIRST_STEPS

## Key Context

- $RESUME_CTX
- CLAUDE.md contains your complete operating instructions, coding standards, technology
  stack, decision rules, feedback loops, and recovery procedures. READ IT FIRST.
- The implementation plan at coding-agent/plans/implementation_plan_v1.md defines 11 phases
  with specific tasks, requirement traceability, and a dependency graph.
- All 157 requirements are enabled (implement: "Y", enable: "Y") in the controller JSONs.

## Autonomy Rules

- Do NOT ask questions. Make reasonable decisions and document them as ADRs.
- Do NOT stop when hitting a blocker. Stub/mock it and continue.
- Do NOT wait for external services. Create interfaces + mocks.
- DO commit after every completed task.
- DO run tests after every code change (build-test-fix loop).
- DO update task status in the implementation plan as you go.
- DO log phase completions to coding-agent/logs/phase_N_complete.md.
- DO write a final BUILD_COMPLETE.md when all phases are done.

## Self-Correction

After every task:
1. uv run ruff check src/ tests/ --fix
2. uv run pytest tests/ -x -q
3. If either fails, fix and retry (max 3 times)
4. If still failing, document in coding-agent/logs/blockers.md and move on

Begin now. Read CLAUDE.md first, then start executing the implementation plan.
PROMPT_EOF

# ---- Launch ----
echo -e "${CYAN}${BOLD}Configuration:${NC}"
echo -e "  Start Phase:   ${GREEN}$START_PHASE${NC}"
echo -e "  Project Root:  ${GREEN}$PROJECT_ROOT${NC}"
echo -e "  Mode:          ${GREEN}$([ "$SAFE_MODE" = true ] && echo "Safe (permission prompts)" || echo "Full Autonomy (hands-off)")${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}${BOLD}=== DRY RUN — Prompt that would be sent ===${NC}"
    echo ""
    echo "$PROMPT"
    echo ""
    echo -e "${YELLOW}${BOLD}=== End of prompt ===${NC}"
    echo ""
    echo "To launch for real:"
    echo "  $0 --phase $START_PHASE"
    exit 0
fi

# Log the start
echo "$(date -Iseconds) — Autonomous build started (Phase $START_PHASE, $([ "$SAFE_MODE" = true ] && echo "safe" || echo "autonomous") mode)" \
    >> coding-agent/logs/build_sessions.log

if [ "$SAFE_MODE" = true ]; then
    echo -e "${YELLOW}Launching in SAFE mode (you'll be prompted for permissions)...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop at any time. Resume with: $0 --phase N${NC}"
    echo ""
    exec claude -p "$PROMPT"
else
    echo -e "${RED}${BOLD}Launching in FULL AUTONOMY mode (--dangerously-skip-permissions)${NC}"
    echo -e "${YELLOW}The agent will run without asking for any permissions.${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop at any time. Resume with: $0 --phase N${NC}"
    echo ""
    sleep 2
    exec claude -p "$PROMPT" --dangerously-skip-permissions
fi
