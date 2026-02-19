#!/usr/bin/env bash
# Alembic migration wrapper.
#
# Usage:
#   bash scripts/db_migrate.sh init               # Auto-generate initial migration from ORM models
#   bash scripts/db_migrate.sh generate "message"  # Auto-generate migration from model changes
#   bash scripts/db_migrate.sh upgrade             # Apply all pending migrations (head)
#   bash scripts/db_migrate.sh upgrade +1           # Apply next migration only
#   bash scripts/db_migrate.sh downgrade -1         # Roll back one migration
#   bash scripts/db_migrate.sh status              # Show current revision and pending migrations
#   bash scripts/db_migrate.sh history             # Show migration history

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

cd "$PROJECT_ROOT"

ACTION="${1:-status}"
shift || true

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Alembic Migrations — $ACTION${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Verify database connection ──────────────────────────────────────────
if ! db_check_connection; then
    echo -e "${RED}✗ Cannot connect to database at $DB_HOST:$DB_PORT/$DB_NAME${NC}"
    echo "  Run 'sudo bash scripts/db_setup.sh' first."
    exit 1
fi
echo -e "${GREEN}✓${NC} Database connection OK"
echo ""

case "$ACTION" in
    init)
        # Check if any migrations already exist
        VERSIONS_DIR="$PROJECT_ROOT/alembic/versions"
        mkdir -p "$VERSIONS_DIR"
        if ls "$VERSIONS_DIR"/*.py 1>/dev/null 2>&1; then
            echo -e "${YELLOW}⚠  Migrations already exist in alembic/versions/${NC}"
            echo "  Use 'generate' to create a new migration from model changes."
            echo "  Use 'init --force' to generate anyway."
            if [[ "${1:-}" != "--force" ]]; then
                exit 1
            fi
        fi
        echo "Generating initial migration from ORM models..."
        uv run alembic revision --autogenerate -m "initial schema"
        echo ""
        echo -e "${GREEN}✓${NC} Initial migration generated"
        echo ""
        echo "Review the migration file in alembic/versions/"
        echo "Then run: bash scripts/db_migrate.sh upgrade"
        ;;

    generate)
        MESSAGE="${1:-auto migration}"
        echo "Generating migration: '$MESSAGE'..."
        uv run alembic revision --autogenerate -m "$MESSAGE"
        echo ""
        echo -e "${GREEN}✓${NC} Migration generated"
        echo "Review the migration file, then run: bash scripts/db_migrate.sh upgrade"
        ;;

    upgrade)
        TARGET="${1:-head}"
        echo "Upgrading to: $TARGET..."
        uv run alembic upgrade "$TARGET"
        echo ""
        echo -e "${GREEN}✓${NC} Upgrade complete"
        # Show current revision
        echo ""
        echo "Current revision:"
        uv run alembic current
        ;;

    downgrade)
        TARGET="${1:--1}"
        echo -e "${YELLOW}Downgrading: $TARGET${NC}"
        confirm_destructive "This will roll back migration(s) and may lose data."
        uv run alembic downgrade "$TARGET"
        echo ""
        echo -e "${GREEN}✓${NC} Downgrade complete"
        echo ""
        echo "Current revision:"
        uv run alembic current
        ;;

    status)
        echo "Current revision:"
        uv run alembic current 2>&1 || echo -e "${YELLOW}  (no migrations applied yet)${NC}"
        echo ""
        echo "Pending migrations:"
        # Show heads vs current to identify pending
        uv run alembic heads 2>&1 || true
        echo ""
        echo "History:"
        uv run alembic history --verbose 2>&1 | head -20 || echo -e "${YELLOW}  (no migration history)${NC}"
        ;;

    history)
        uv run alembic history --verbose
        ;;

    *)
        echo -e "${RED}✗ Unknown action: $ACTION${NC}"
        echo ""
        echo "Usage: $0 {init|generate|upgrade|downgrade|status|history}"
        echo ""
        echo "  init                    Auto-generate initial migration from models"
        echo "  generate \"message\"      Auto-generate migration from model changes"
        echo "  upgrade [target]        Apply migrations (default: head)"
        echo "  downgrade [target]      Roll back migrations (default: -1)"
        echo "  status                  Show current migration status"
        echo "  history                 Show full migration history"
        exit 1
        ;;
esac
