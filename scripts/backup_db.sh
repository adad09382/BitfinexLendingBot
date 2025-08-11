#!/bin/bash
# BitfinexLendingBot 數據庫備份腳本
# 用於定期備份 PostgreSQL 數據庫

set -e

# 配置變量
DB_NAME="bitfinex_bot"
DB_USER="bitfinex_user"
BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bitfinex_bot_backup_${DATE}.sql"

# 創建備份目錄
mkdir -p "${BACKUP_DIR}"

# 執行備份
echo "Starting database backup at $(date)"
pg_dump -h postgres -U "${DB_USER}" -d "${DB_NAME}" \
    --verbose \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > "${BACKUP_FILE}"

# 壓縮備份文件
gzip "${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

echo "Backup completed: ${BACKUP_FILE}"

# 檢查備份文件大小
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "Backup size: ${BACKUP_SIZE}"

# 清理舊備份 (保留最近7天)
find "${BACKUP_DIR}" -name "bitfinex_bot_backup_*.sql.gz" -mtime +7 -delete

# 驗證備份文件
if [ -s "${BACKUP_FILE}" ]; then
    echo "Backup verification: SUCCESS"
    exit 0
else
    echo "Backup verification: FAILED - Empty backup file"
    exit 1
fi