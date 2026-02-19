#!/usr/bin/env bash
# Back up the database using pg_dump.
#
# Usage:
#   bash scripts/db_backup.sh          # Custom format (compressed, supports pg_restore)
#   bash scripts/db_backup.sh --sql    # Plain SQL format (human-readable)
#   bash scripts/db_backup.sh --dir /path/to/backups  # Custom backup directory
#
# Backups are saved to PROJECT_ROOT/backups/ with timestamps.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

FORMAT="custom"
BACKUP_DIR="$PROJECT_ROOT/backups"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sql)     FORMAT="sql"; shift ;;
        --dir)     BACKUP_DIR="$2"; shift 2 ;;
        *)
            echo -e "${RED}✗ Unknown argument: $1${NC}"
            echo "Usage: $0 [--sql] [--dir /path/to/backups]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Database Backup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Verify database connection ──────────────────────────────────────────
if ! db_check_connection; then
    echo -e "${RED}✗ Cannot connect to database${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Database connection OK"

# ── Create backup directory ─────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Generate filename ───────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [[ "$FORMAT" == "sql" ]]; then
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"
else
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
fi

# ── Run pg_dump ─────────────────────────────────────────────────────────
echo "Backing up '$DB_NAME' to:"
echo "  $BACKUP_FILE"
echo ""

START_TIME=$(date +%s)

if [[ "$FORMAT" == "sql" ]]; then
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        --format=plain --no-owner --no-acl \
        "$DB_NAME" > "$BACKUP_FILE"
else
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        --format=custom --compress=9 --no-owner --no-acl \
        "$DB_NAME" > "$BACKUP_FILE"
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ── Report ──────────────────────────────────────────────────────────────
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo -e "${GREEN}✓${NC} Backup complete"
echo ""
echo "  File:     $BACKUP_FILE"
echo "  Format:   $FORMAT"
echo "  Size:     $FILE_SIZE"
echo "  Duration: ${ELAPSED}s"
echo ""
echo "Restore with:"
echo "  bash scripts/db_restore.sh $BACKUP_FILE"
