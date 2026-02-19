#!/usr/bin/env bash
# Shared database configuration helper.
#
# Sourced by all db_*.sh scripts.  Reads DATABASE__* vars from .env and
# exports the canonical DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
# variables that pg_dump, psql, and createdb expect.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Colors ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color

# ── Load .env ───────────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    # Export only DATABASE__* and APP_ENV lines, ignoring comments and blanks
    set -a
    while IFS='=' read -r key value; do
        # Skip comments and blank lines
        [[ -z "$key" || "$key" == \#* ]] && continue
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # Only export DATABASE__ and APP_ENV vars
        if [[ "$key" == DATABASE__* || "$key" == APP_ENV ]]; then
            export "$key=$value"
        fi
    done < "$ENV_FILE"
    set +a
fi

# ── Export canonical variables ──────────────────────────────────────────
export DB_HOST="${DATABASE__HOST:-localhost}"
export DB_PORT="${DATABASE__PORT:-5432}"
export DB_NAME="${DATABASE__NAME:-patient_advocacy}"
export DB_USER="${DATABASE__USER:-patient_advocacy}"
export DB_PASSWORD="${DATABASE__PASSWORD:-}"
export APP_ENV="${APP_ENV:-dev}"

# ── Helper functions ────────────────────────────────────────────────────

# Build a psql connection string (without password — use PGPASSWORD env var)
db_conn_args() {
    echo "-h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME"
}

# Run psql with password set
run_psql() {
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$@"
}

# Run psql as the database superuser (for setup operations)
run_psql_admin() {
    sudo -u postgres psql "$@"
}

# Check if we can connect to the database
db_check_connection() {
    PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1
}

# Block destructive operations in production
require_non_production() {
    if [[ "$APP_ENV" == "production" ]]; then
        echo -e "${RED}✗ This operation is blocked in production (APP_ENV=production)${NC}"
        echo "  Set APP_ENV to 'dev' or 'staging' to proceed."
        exit 1
    fi
}

# Ask for confirmation before destructive operations
confirm_destructive() {
    local action="$1"
    echo -e "${YELLOW}⚠  WARNING: $action${NC}"
    echo ""
    read -rp "Type 'yes' to confirm: " answer
    if [[ "$answer" != "yes" ]]; then
        echo -e "${RED}✗ Aborted.${NC}"
        exit 1
    fi
}
