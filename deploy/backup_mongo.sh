#!/usr/bin/env bash
# ============================================================
#  Nubo - Backup automatico de MongoDB Atlas -> VPS (+ opcional DO Spaces)
#  Usa mongodump. Guarda copias comprimidas y rota las antiguas.
#  Programar con cron (ver instrucciones al final).
# ============================================================
set -euo pipefail

# ---- Config ----
# Lee la URI desde deploy/backend.env (clave MONGO_URL) para no duplicar secretos.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/backend.env"
MONGO_URI="$(grep -E '^MONGO_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
DB_NAME="$(grep -E '^DB_NAME=' "$ENV_FILE" | head -1 | cut -d= -f2-)"

BACKUP_DIR="/opt/nubo-backups"
RETENTION_DAYS=14                      # cuantos dias conservar
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/nubo_${DB_NAME}_${STAMP}"

mkdir -p "$BACKUP_DIR"

echo "==> [$(date)] Iniciando backup de '${DB_NAME}'..."

# mongodump (requiere mongodb-database-tools instalado, ver abajo)
mongodump --uri="${MONGO_URI}" --db="${DB_NAME}" --gzip --archive="${OUT}.archive.gz"

echo "==> Backup creado: ${OUT}.archive.gz"

# ---- (Opcional) Subir a DigitalOcean Spaces / S3 ----
# Requiere 's3cmd' o 'aws cli' configurado. Descomenta si lo usas:
# aws s3 cp "${OUT}.archive.gz" "s3://nubo-backups/" --endpoint-url https://fra1.digitaloceanspaces.com

# ---- Rotacion: borrar backups mas viejos que RETENTION_DAYS ----
find "$BACKUP_DIR" -name "nubo_*.archive.gz" -mtime +${RETENTION_DAYS} -print -delete

echo "==> [$(date)] Backup completado. Copias actuales:"
ls -lh "$BACKUP_DIR" | tail -n +2

# ============================================================
#  INSTALACION (una vez en el VPS Ubuntu):
#    # MongoDB Database Tools (mongodump)
#    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb.gpg --dearmor
#    echo "deb [signed-by=/usr/share/keyrings/mongodb.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb.list
#    apt-get update && apt-get install -y mongodb-database-tools
#
#  PROGRAMAR con cron (backup diario a las 03:30):
#    chmod +x /opt/nubo/deploy/backup_mongo.sh
#    crontab -e
#    # anade esta linea:
#    30 3 * * * /opt/nubo/deploy/backup_mongo.sh >> /var/log/nubo-backup.log 2>&1
#
#  RESTAURAR una copia:
#    mongorestore --uri="<MONGO_URI>" --gzip --archive=/opt/nubo-backups/ARCHIVO.archive.gz --nsInclude="nubo_produccion.*"
# ============================================================
