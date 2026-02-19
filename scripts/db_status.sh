#!/usr/bin/env bash
# Database health check: connection, migration status, table row counts, DB size.
#
# Usage:
#   bash scripts/db_status.sh          # Full status report
#   bash scripts/db_status.sh --json   # Machine-readable JSON output

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

cd "$PROJECT_ROOT"

JSON_MODE=false
if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=true
fi

if [[ "$JSON_MODE" == false ]]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Database Status${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
fi

# ── Connection check ────────────────────────────────────────────────────
CONNECTION_OK=false
if db_check_connection; then
    CONNECTION_OK=true
fi

if [[ "$JSON_MODE" == false ]]; then
    echo "Connection:"
    echo "  Host:     $DB_HOST:$DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User:     $DB_USER"
    if [[ "$CONNECTION_OK" == true ]]; then
        echo -e "  Status:   ${GREEN}✓ Connected${NC}"
    else
        echo -e "  Status:   ${RED}✗ Cannot connect${NC}"
        echo ""
        echo "Run 'sudo bash scripts/db_setup.sh' to create the database."
        exit 1
    fi
    echo ""
fi

if [[ "$CONNECTION_OK" != true ]]; then
    if [[ "$JSON_MODE" == true ]]; then
        echo '{"connected": false}'
    fi
    exit 1
fi

# ── PostgreSQL version ──────────────────────────────────────────────────
PG_VERSION=$(run_psql -d "$DB_NAME" -tAc "SELECT version();" 2>/dev/null | head -1)

if [[ "$JSON_MODE" == false ]]; then
    echo "PostgreSQL:"
    echo "  $PG_VERSION"
    echo ""
fi

# ── Database size ───────────────────────────────────────────────────────
DB_SIZE=$(run_psql -d "$DB_NAME" -tAc "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null)

if [[ "$JSON_MODE" == false ]]; then
    echo "Database size: $DB_SIZE"
    echo ""
fi

# ── Migration status ────────────────────────────────────────────────────
CURRENT_REV=""
ALEMBIC_EXISTS=$(run_psql -d "$DB_NAME" -tAc "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version');" 2>/dev/null)
if [[ "$ALEMBIC_EXISTS" == "t" ]]; then
    CURRENT_REV=$(run_psql -d "$DB_NAME" -tAc "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null)
fi

if [[ "$JSON_MODE" == false ]]; then
    echo "Migrations:"
    if [[ -n "$CURRENT_REV" ]]; then
        echo -e "  Current revision: ${GREEN}$CURRENT_REV${NC}"
        # Check head
        HEAD_REV=$(uv run alembic heads 2>/dev/null | grep -oP '[a-f0-9]+' | head -1 || echo "")
        if [[ -n "$HEAD_REV" && "$HEAD_REV" == "$CURRENT_REV"* ]]; then
            echo -e "  Status: ${GREEN}✓ Up to date${NC}"
        elif [[ -n "$HEAD_REV" ]]; then
            echo -e "  Head revision:    ${YELLOW}$HEAD_REV${NC}"
            echo -e "  Status: ${YELLOW}⚠  Pending migrations${NC}"
        fi
    else
        echo -e "  Status: ${YELLOW}⚠  No migrations applied${NC}"
        echo "  Run: bash scripts/db_migrate.sh upgrade"
    fi
    echo ""
fi

# ── Table row counts ───────────────────────────────────────────────────
TABLE_DATA=$(run_psql -d "$DB_NAME" -tAc "
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename;
" 2>/dev/null)

if [[ "$JSON_MODE" == false ]]; then
    echo "Tables:"
    if [[ -z "$TABLE_DATA" ]]; then
        echo -e "  ${YELLOW}⚠  No tables found${NC}"
    else
        # Header
        printf "  %-25s %s\n" "Table" "Rows"
        printf "  %-25s %s\n" "─────────────────────────" "────────"
        TOTAL_ROWS=0
        while IFS= read -r table; do
            [[ -z "$table" ]] && continue
            COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null || echo "?")
            COUNT=$(echo "$COUNT" | xargs)
            printf "  %-25s %s\n" "$table" "$COUNT"
            if [[ "$COUNT" =~ ^[0-9]+$ ]]; then
                TOTAL_ROWS=$((TOTAL_ROWS + COUNT))
            fi
        done <<< "$TABLE_DATA"
        printf "  %-25s %s\n" "─────────────────────────" "────────"
        printf "  %-25s %s\n" "Total" "$TOTAL_ROWS"
    fi
    echo ""
fi

# ── Active connections ──────────────────────────────────────────────────
ACTIVE_CONNS=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='$DB_NAME';" 2>/dev/null)

if [[ "$JSON_MODE" == false ]]; then
    echo "Active connections: $ACTIVE_CONNS"
    echo ""
fi

# ── JSON output ─────────────────────────────────────────────────────────
if [[ "$JSON_MODE" == true ]]; then
    # Build JSON manually (avoid jq dependency)
    echo "{"
    echo "  \"connected\": true,"
    echo "  \"host\": \"$DB_HOST:$DB_PORT\","
    echo "  \"database\": \"$DB_NAME\","
    echo "  \"size\": \"$DB_SIZE\","
    echo "  \"migration_revision\": \"$CURRENT_REV\","
    echo "  \"active_connections\": $ACTIVE_CONNS,"
    echo "  \"environment\": \"$APP_ENV\""
    echo "}"
fi
