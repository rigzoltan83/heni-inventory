#!/bin/bash

set -euo pipefail


BACKUP_ROOT="/backup/heni-inventory"
SOURCE_DIR="/opt/heni-inventory"

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

DB_CONTAINER="family-db"
DB_NAME="heni_inventory"
DB_USER="heni_inventory_user"

LOG_FILE="${BACKUP_ROOT}/backup.log"


log()
{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" \
        >> "${LOG_FILE}"
}


cleanup_failed_backup()
{
    if [ -d "${BACKUP_DIR}" ]; then
        rm -rf "${BACKUP_DIR}"
    fi
}


mkdir -p "${BACKUP_ROOT}"

trap \
    'log "HIBA: a mentés megszakadt."; cleanup_failed_backup' \
    ERR

mkdir -p "${BACKUP_DIR}"

log "Heni Inventory backup indul: ${TIMESTAMP}"


# --------------------------------------------------
# PostgreSQL adatbázis
# --------------------------------------------------

docker exec \
    "${DB_CONTAINER}" \
    pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -Fc \
    > "${BACKUP_DIR}/heni_inventory.dump"


# --------------------------------------------------
# Teljes alkalmazás
#
# Tartalmazza többek között:
# - forráskód
# - .env
# - migrations
# - feltöltött termékképek
# - Git repository
# - venv
#
# Csak ideiglenes/cache fájlokat hagyunk ki.
# --------------------------------------------------

tar \
    --exclude='heni-inventory/.gunicorn' \
    --exclude='heni-inventory/.cache' \
    --exclude='heni-inventory/.pytest_cache' \
    --exclude='heni-inventory/__pycache__' \
    --exclude='heni-inventory/app/__pycache__' \
    --exclude='heni-inventory/app/*/__pycache__' \
    --exclude='heni-inventory/app/*/*/__pycache__' \
    -czf \
    "${BACKUP_DIR}/heni-inventory-files.tar.gz" \
    -C /opt \
    heni-inventory


# --------------------------------------------------
# Ellenőrzés
# --------------------------------------------------

test -s \
    "${BACKUP_DIR}/heni_inventory.dump"

test -s \
    "${BACKUP_DIR}/heni-inventory-files.tar.gz"


# --------------------------------------------------
# 3 napnál régebbi timestamp backupok törlése
#
# A backup.log megmarad.
# --------------------------------------------------

find "${BACKUP_ROOT}" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -mmin +4320 \
    -exec rm -rf {} \;


log "Heni Inventory backup sikeres: ${BACKUP_DIR}"

trap - ERR

exit 0
