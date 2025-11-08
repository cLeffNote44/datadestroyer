#!/bin/bash
# Media Files Backup Script for Data Destroyer
# Usage: ./backup-media.sh

set -euo pipefail

# Configuration
MEDIA_DIR="${MEDIA_DIR:-./media}"
BACKUP_DIR="${BACKUP_DIR:-/backups/media}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="destroyer_media_${TIMESTAMP}.tar.gz"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log_info "Starting media files backup..."
log_info "Media directory: ${MEDIA_DIR}"

# Create tar.gz backup
if tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" -C "$(dirname ${MEDIA_DIR})" "$(basename ${MEDIA_DIR})"; then
    log_info "Media backup completed successfully"
    log_info "Backup size: $(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)"
else
    log_warn "Media backup failed"
    exit 1
fi

# Upload to S3 if configured
if [ -n "${AWS_S3_BACKUP_BUCKET:-}" ]; then
    log_info "Syncing media files to S3..."

    if aws s3 sync "${MEDIA_DIR}" "s3://${AWS_S3_BACKUP_BUCKET}/media/" --delete; then
        log_info "S3 sync completed successfully"
    else
        log_warn "S3 sync failed, but local backup is available"
    fi
fi

# Cleanup old backups (keep last 7 days of full backups)
log_info "Cleaning up old media backups..."
find "${BACKUP_DIR}" -name "destroyer_media_*.tar.gz" -type f -mtime +7 -delete

log_info "Media backup process completed!"
