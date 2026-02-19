#!/usr/bin/env bash
# Seed the database with development data.
#
# Usage:
#   bash scripts/db_seed.sh           # Seed (skip if data exists)
#   bash scripts/db_seed.sh --reset   # Truncate all tables first, then seed
#   bash scripts/db_seed.sh --check   # Just check if data exists, don't seed

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

cd "$PROJECT_ROOT"

RESET=false
CHECK_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --reset) RESET=true ;;
        --check) CHECK_ONLY=true ;;
        *)
            echo -e "${RED}✗ Unknown argument: $arg${NC}"
            echo "Usage: $0 [--reset|--check]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Database Seed${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Verify database connection ──────────────────────────────────────────
if ! db_check_connection; then
    echo -e "${RED}✗ Cannot connect to database${NC}"
    echo "  Run 'sudo bash scripts/db_setup.sh' first."
    exit 1
fi
echo -e "${GREEN}✓${NC} Database connection OK"

# ── Check if tables exist ──────────────────────────────────────────────
TABLE_COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null || echo "0")

if [[ "$TABLE_COUNT" -eq 0 ]]; then
    echo -e "${RED}✗ No tables found. Run migrations first:${NC}"
    echo "  bash scripts/db_migrate.sh upgrade"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found $TABLE_COUNT tables"

# ── Check if data exists ───────────────────────────────────────────────
USER_COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

if [[ "$CHECK_ONLY" == true ]]; then
    if [[ "$USER_COUNT" -gt 0 ]]; then
        echo -e "${GREEN}✓${NC} Database has $USER_COUNT users (already seeded)"
    else
        echo -e "${YELLOW}⚠  Database is empty (no users)${NC}"
    fi
    exit 0
fi

# ── Reset if requested ─────────────────────────────────────────────────
if [[ "$RESET" == true ]]; then
    require_non_production
    confirm_destructive "This will TRUNCATE all tables in '$DB_NAME'."
    echo "Truncating all tables..."
    run_psql -d "$DB_NAME" -c "
        DO \$\$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version') LOOP
                EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END \$\$;
    "
    echo -e "${GREEN}✓${NC} All tables truncated"
    USER_COUNT=0
fi

# ── Seed ────────────────────────────────────────────────────────────────
if [[ "$USER_COUNT" -gt 0 ]]; then
    echo -e "${YELLOW}⚠  Database already has $USER_COUNT users. Skipping seed.${NC}"
    echo "  Use --reset to truncate first, then re-seed."
    exit 0
fi

echo ""
echo "Seeding development data..."
uv run python scripts/seed_db.py

echo ""
echo -e "${GREEN}✓ Seed complete${NC}"
echo ""

# Show summary
echo "Seeded data:"
for table in facility_pools facilities users doctor_pools patients; do
    COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "?")
    echo -e "  ${GREEN}✓${NC} $table: $COUNT rows"
done
