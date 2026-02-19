#!/usr/bin/env bash
# Create the PostgreSQL user and database (idempotent).
#
# Usage:
#   sudo bash scripts/db_setup.sh          # Create user + database
#   sudo bash scripts/db_setup.sh --drop   # Drop and recreate (dev only)
#
# Requires: PostgreSQL server running, sudo access for 'postgres' user.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/scripts/_db_config.sh"

DROP=false
if [[ "${1:-}" == "--drop" ]]; then
    DROP=true
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Database Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Host:     $DB_HOST"
echo "  Port:     $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User:     $DB_USER"
echo ""

# ── Check PostgreSQL is running ─────────────────────────────────────────
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
    echo -e "${RED}✗ PostgreSQL is not running on $DB_HOST:$DB_PORT${NC}"
    echo "  Start it with: sudo systemctl start postgresql"
    exit 1
fi
echo -e "${GREEN}✓${NC} PostgreSQL is running"

# ── Drop (if requested) ────────────────────────────────────────────────
if [[ "$DROP" == true ]]; then
    require_non_production
    confirm_destructive "This will DROP the database '$DB_NAME' and user '$DB_USER'."

    echo "Dropping database and user..."
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Dropped database and user"
fi

# ── Create user (idempotent) ────────────────────────────────────────────
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    echo -e "${GREEN}✓${NC} User '$DB_USER' already exists"
else
    if [[ -z "$DB_PASSWORD" ]]; then
        echo -e "${RED}✗ DATABASE__PASSWORD is not set in .env${NC}"
        echo "  Set it before running this script."
        exit 1
    fi
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    echo -e "${GREEN}✓${NC} Created user '$DB_USER'"
fi

# ── Create database (idempotent) ────────────────────────────────────────
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    echo -e "${GREEN}✓${NC} Database '$DB_NAME' already exists"
else
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo -e "${GREEN}✓${NC} Created database '$DB_NAME'"
fi

# ── Grant privileges ───────────────────────────────────────────────────
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" >/dev/null 2>&1
echo -e "${GREEN}✓${NC} Granted privileges to '$DB_USER' on '$DB_NAME'"

# ── Verify connection ──────────────────────────────────────────────────
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Connection verified"
else
    echo -e "${RED}✗ Could not connect as $DB_USER to $DB_NAME${NC}"
    echo "  Check pg_hba.conf allows password authentication for this user."
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Database setup complete${NC}"
echo ""
echo "Next steps:"
echo "  bash scripts/db_migrate.sh init      # Generate initial migration"
echo "  bash scripts/db_migrate.sh upgrade   # Apply migrations"
echo "  bash scripts/db_seed.sh              # Seed development data"
