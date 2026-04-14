#!/usr/bin/env bash
# =============================================================================
# load_adventureworks.sh
#
# One-time script: converts AdventureWorks CSVs from Microsoft +| format to
# TSV, then loads them into the running Docker PostgreSQL container.
#
# Usage:
#   ./scripts/load_adventureworks.sh [path/to/AdventureWorks-for-Postgres]
#
# The argument defaults to ~/AdventureWorks-for-Postgres if not provided.
# Run this AFTER: docker compose up -d (container must be running)
# =============================================================================

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────

AW_REPO="${1:-$HOME/AdventureWorks-for-Postgres}"
AW_CSVS="$AW_REPO/AdventureWorks-oltp-install-script"
INSTALL_SQL="$(realpath "$AW_REPO/install.sql")"
CONVERT_PY="$(realpath "$(dirname "$0")/../docker/postgres/convert_csvs.py")"

# Load .env if present (for DATABASE_URL / DB_PORT)
ENV_FILE="$(dirname "$0")/../.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ENV_FILE" | grep -v '^\s*$' | xargs)
fi

DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5433/adventureworks}"

# ── Pre-flight checks ─────────────────────────────────────────────────────────

echo ""
echo "=== AdventureWorks Loader ==="
echo ""

if [[ ! -d "$AW_REPO" ]]; then
  echo "ERROR: AdventureWorks repo not found at: $AW_REPO"
  echo "Usage: $0 /path/to/AdventureWorks-for-Postgres"
  exit 1
fi

if [[ ! -d "$AW_CSVS" ]]; then
  echo "ERROR: CSV directory not found at: $AW_CSVS"
  echo "Make sure you've extracted AdventureWorks-oltp-install-script.zip into the repo."
  exit 1
fi

if [[ ! -f "$INSTALL_SQL" ]]; then
  echo "ERROR: install.sql not found at: $INSTALL_SQL"
  exit 1
fi

if ! command -v psql &>/dev/null; then
  echo "ERROR: psql not found. Install the PostgreSQL client:"
  echo "  sudo apt install postgresql-client"
  exit 1
fi

# Check container is reachable
if ! psql "$DB_URL" -c "SELECT 1" &>/dev/null; then
  echo "ERROR: Cannot connect to PostgreSQL at $DB_URL"
  echo "Make sure the container is running:  docker compose up -d"
  exit 1
fi

echo "Config:"
echo "  AW repo:  $AW_REPO"
echo "  DB URL:   $DB_URL"
echo ""

# ── Check if already loaded ────────────────────────────────────────────────────

ORDER_COUNT=$(psql "$DB_URL" -tAc "SELECT COUNT(*) FROM sales.salesorderheader" 2>/dev/null || echo "0")
if [[ "$ORDER_COUNT" -gt 0 ]]; then
  echo "AdventureWorks already loaded ($ORDER_COUNT orders found). Skipping."
  echo "To reload, drop and recreate the database first."
  exit 0
fi

# ── Step 1: Convert CSVs ──────────────────────────────────────────────────────

echo "Step 1/2 — Converting CSVs (Microsoft +| format → TSV)..."
echo ""

# Run convert_csvs.py from the CSV directory so it processes files in-place
(cd "$AW_CSVS" && python3 "$CONVERT_PY")

echo ""

# ── Step 2: Load via psql ─────────────────────────────────────────────────────

echo "Step 2/2 — Loading into PostgreSQL (this takes ~1-2 minutes)..."
echo ""

# psql must run from the CSV directory so \copy finds the files,
# but -f points to install.sql one level up.
(cd "$AW_CSVS" && psql "$DB_URL" -v ON_ERROR_STOP=0 -f "$INSTALL_SQL")

# ── Verify ────────────────────────────────────────────────────────────────────

echo ""
echo "=== Verification ==="
psql "$DB_URL" -c "
  SELECT
    'Orders'   AS table_name, COUNT(*) AS rows FROM sales.salesorderheader
  UNION ALL SELECT
    'Products',                COUNT(*)         FROM production.product
  UNION ALL SELECT
    'Persons',                 COUNT(*)         FROM person.person
  UNION ALL SELECT
    'Inventory',               COUNT(*)         FROM production.productinventory;
"

echo ""
echo "Done! Run 'python scripts/verify_setup.py' for the full check."
