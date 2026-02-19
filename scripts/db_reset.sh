#!/usr/bin/env bash
# Nuclear database reset: drop all tables, re-migrate, re-seed.
#
# Usage:
#   bash scripts/db_reset.sh           # Interactive confirmation
#   bash scripts/db_reset.sh --force   # Skip confirmation (still blocked in production)
#
# BLOCKED in production (APP_ENV=production).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

cd "$PROJECT_ROOT"

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  Database Reset (DESTRUCTIVE)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Environment: $APP_ENV"
echo "  Database:    $DB_NAME"
echo "  Host:        $DB_HOST:$DB_PORT"
echo ""

# ── Block in production ─────────────────────────────────────────────────
require_non_production

# ── Confirm ─────────────────────────────────────────────────────────────
if [[ "$FORCE" != true ]]; then
    confirm_destructive "This will DROP ALL TABLES in '$DB_NAME', re-run migrations, and re-seed."
fi

# ── Verify database connection ──────────────────────────────────────────
if ! db_check_connection; then
    echo -e "${RED}✗ Cannot connect to database${NC}"
    exit 1
fi

# ── Step 1: Drop all tables ────────────────────────────────────────────
echo ""
echo "Step 1/3: Dropping all tables..."
run_psql -d "$DB_NAME" -c "
    DO \$\$
    DECLARE
        r RECORD;
    BEGIN
        -- Drop all tables
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
        -- Drop all custom enum types
        FOR r IN (SELECT typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'public' AND t.typtype = 'e') LOOP
            EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
        END LOOP;
    END \$\$;
"
echo -e "${GREEN}✓${NC} All tables and enums dropped"

# ── Step 2: Re-run migrations ──────────────────────────────────────────
echo ""
echo "Step 2/3: Running migrations..."
uv run alembic upgrade head
echo -e "${GREEN}✓${NC} Migrations applied"

# ── Step 3: Re-seed ────────────────────────────────────────────────────
echo ""
echo "Step 3/3: Seeding development data..."
uv run python scripts/seed_db.py
echo -e "${GREEN}✓${NC} Data seeded"

# ── Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Database reset complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show table counts
echo "Tables:"
for table in facility_pools facilities users doctor_pools patients cases case_images case_audio; do
    COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "—")
    echo -e "  ${GREEN}✓${NC} $table: $COUNT rows"
done
