#!/bin/bash
# Database Backup Script for Data Destroyer
# Usage: ./backup-database.sh [retention_days]

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${1:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="destroyer_db_${TIMESTAMP}.sql.gz"

# Database connection (from environment or defaults)
DB_NAME="${POSTGRES_DB:-destroyer}"
DB_USER="${POSTGRES_USER:-destroyer}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log_info "Starting database backup..."
log_info "Database: ${DB_NAME}"
log_info "Backup file: ${BACKUP_FILE}"

# Perform backup
if docker-compose exec -T db pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -F p \
    -C \
    --if-exists \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"; then

    log_info "Database backup completed successfully"
    log_info "Backup size: $(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)"
else
    log_error "Database backup failed"
    exit 1
fi

# Upload to S3 if configured
if [ -n "${AWS_S3_BACKUP_BUCKET:-}" ]; then
    log_info "Uploading backup to S3..."

    if aws s3 cp \
        "${BACKUP_DIR}/${BACKUP_FILE}" \
        "s3://${AWS_S3_BACKUP_BUCKET}/database/${BACKUP_FILE}" \
        --storage-class STANDARD_IA; then

        log_info "S3 upload completed successfully"
    else
        log_warn "S3 upload failed, but local backup is available"
    fi
fi

# Cleanup old backups
log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "destroyer_db_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# Count remaining backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "destroyer_db_*.sql.gz" -type f | wc -l)
log_info "Total backups retained: ${BACKUP_COUNT}"

# Verify backup integrity
log_info "Verifying backup integrity..."
if gunzip -t "${BACKUP_DIR}/${BACKUP_FILE}"; then
    log_info "Backup integrity verified successfully"
else
    log_error "Backup integrity check failed!"
    exit 1
fi

log_info "Backup process completed!"
echo ""
echo "Backup location: ${BACKUP_DIR}/${BACKUP_FILE}"
echo "To restore: gunzip -c ${BACKUP_DIR}/${BACKUP_FILE} | docker-compose exec -T db psql -U ${DB_USER} -d postgres"
