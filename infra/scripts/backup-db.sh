#!/usr/bin/env bash
# GDF-AutoMon: TimescaleDB backup script.
# Run daily via cron: 0 2 * * * /path/to/backup-db.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/gdf-automon}"
KEEP_DAYS="${KEEP_DAYS:-14}"

# Load .env
if [[ -f "$INFRA_DIR/.env" ]]; then
  set -o allexport; source "$INFRA_DIR/.env"; set +o allexport
fi

POSTGRES_USER="${POSTGRES_USER:-gdf}"
POSTGRES_DB="${POSTGRES_DB:-gdfautomon}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/gdf_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up $POSTGRES_DB to $BACKUP_FILE..."
docker exec gdf-timescaledb pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"
echo "Backup complete: $(du -h "$BACKUP_FILE" | cut -f1)"

# Prune old backups
find "$BACKUP_DIR" -name "gdf_*.sql.gz" -mtime "+$KEEP_DAYS" -delete
echo "Pruned backups older than $KEEP_DAYS days."
