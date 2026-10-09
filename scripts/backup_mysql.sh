#!/usr/bin/env bash
set -euo pipefail

: "${DB_NAME:?Set DB_NAME before running the backup}"
: "${DB_USER:?Set DB_USER before running the backup}"

if [[ -n "${DB_PASSWORD:-}" ]]; then
  export MYSQL_PWD="$DB_PASSWORD"
fi

backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/${DB_NAME}-${timestamp}.sql.gz"

mysqldump \
  --host="${DB_HOST:-127.0.0.1}" \
  --port="${DB_PORT:-3306}" \
  --user="$DB_USER" \
  --single-transaction \
  --routines \
  --triggers \
  "$DB_NAME" | gzip > "$backup_file"

echo "Wrote $backup_file"