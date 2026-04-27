#!/usr/bin/env bash
# GDF-AutoMon: Initialize database and run Alembic migrations.
# Run once after first `docker compose up`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$INFRA_DIR")"

echo "=== GDF-AutoMon: Database Initialization ==="

# Load .env if present
if [[ -f "$INFRA_DIR/.env" ]]; then
  set -o allexport
  source "$INFRA_DIR/.env"
  set +o allexport
fi

POSTGRES_USER="${POSTGRES_USER:-gdf}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-gdf_secure_2024}"
POSTGRES_DB="${POSTGRES_DB:-gdfautomon}"
DB_CONTAINER="${DB_CONTAINER:-gdf-timescaledb}"

# Wait for TimescaleDB to be ready
echo "Waiting for TimescaleDB..."
until docker exec "$DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null; do
  sleep 2
done
echo "TimescaleDB is ready."

# Enable TimescaleDB extension (if not already)
docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;" 2>&1 | grep -v "already exists" || true

docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";" 2>&1 | grep -v "already exists" || true

# Run Alembic migrations inside the backend container
echo "Running Alembic migrations..."
docker exec -e DATABASE_URL="postgresql+asyncpg://$POSTGRES_USER:$POSTGRES_PASSWORD@timescaledb:5432/$POSTGRES_DB" \
  gdf-backend alembic upgrade head

echo "=== Database initialization complete ==="
echo "Tables created:"
docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "\dt" 2>/dev/null | grep -E "sensors|readings|alerts|push"
