#!/usr/bin/env bash
# Restore a database from a backup file.
#
# Usage:
#   bash scripts/db_restore.sh backups/patient_advocacy_20260218_120000.dump
#   bash scripts/db_restore.sh backups/patient_advocacy_20260218_120000.sql
#
# Auto-detects format (custom .dump vs plain .sql).
# BLOCKED in production (APP_ENV=production).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

cd "$PROJECT_ROOT"

BACKUP_FILE="${1:-}"

if [[ -z "$BACKUP_FILE" ]]; then
    echo -e "${RED}✗ No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup-file>"
    echo ""
    # List available backups
    BACKUP_DIR="$PROJECT_ROOT/backups"
    if [[ -d "$BACKUP_DIR" ]] && ls "$BACKUP_DIR"/*.{dump,sql} 1>/dev/null 2>&1; then
        echo "Available backups:"
        ls -lh "$BACKUP_DIR"/*.{dump,sql} 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    else
        echo "No backups found in $BACKUP_DIR/"
    fi
    exit 1
fi

# Resolve relative paths
if [[ ! "$BACKUP_FILE" = /* ]]; then
    BACKUP_FILE="$PROJECT_ROOT/$BACKUP_FILE"
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}✗ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Database Restore${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  File:        $(basename "$BACKUP_FILE")"
echo "  Size:        $(du -h "$BACKUP_FILE" | cut -f1)"
echo "  Database:    $DB_NAME"
echo "  Environment: $APP_ENV"
echo ""

# ── Block in production ─────────────────────────────────────────────────
require_non_production

# ── Confirm ─────────────────────────────────────────────────────────────
confirm_destructive "This will DROP existing data in '$DB_NAME' and restore from backup."

# ── Verify database connection ──────────────────────────────────────────
if ! db_check_connection; then
    echo -e "${RED}✗ Cannot connect to database${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Database connection OK"

# ── Detect format ───────────────────────────────────────────────────────
if [[ "$BACKUP_FILE" == *.sql ]]; then
    FORMAT="sql"
else
    FORMAT="custom"
fi
echo -e "${GREEN}✓${NC} Detected format: $FORMAT"

# ── Drop existing tables ───────────────────────────────────────────────
echo ""
echo "Dropping existing tables..."
run_psql -d "$DB_NAME" -c "
    DO \$\$
    DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
        FOR r IN (SELECT typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'public' AND t.typtype = 'e') LOOP
            EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
        END LOOP;
    END \$\$;
"
echo -e "${GREEN}✓${NC} Existing tables dropped"

# ── Restore ─────────────────────────────────────────────────────────────
echo ""
echo "Restoring from backup..."

START_TIME=$(date +%s)

if [[ "$FORMAT" == "sql" ]]; then
    run_psql -d "$DB_NAME" -f "$BACKUP_FILE"
else
    PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -d "$DB_NAME" --no-owner --no-acl \
        "$BACKUP_FILE"
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}✓${NC} Restore complete (${ELAPSED}s)"
echo ""

# ── Verify ──────────────────────────────────────────────────────────────
echo "Restored tables:"
TABLE_LIST=$(run_psql -d "$DB_NAME" -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
for table in $TABLE_LIST; do
    COUNT=$(run_psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "?")
    echo -e "  ${GREEN}✓${NC} $table: $COUNT rows"
done
