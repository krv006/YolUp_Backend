#!/usr/bin/env bash
# APP serverda har kecha baza zaxirasi (pg_dump) + boshqa serverga nusxa.
#
# Sozlash (deploy foydalanuvchisida, bir marta):
#   1) MEDIA serverda:  sudo install -d -o deploy -g deploy /var/backups/edu-app
#   2) APP serverda SSH kalit yarating va MEDIA serverning ~/.ssh/authorized_keys iga qo'shing:
#        ssh-keygen -t ed25519 -f ~/.ssh/backup_key -N ""
#        ssh-copy-id -i ~/.ssh/backup_key.pub deploy@<MEDIA_IP>
#   3) crontab -e  ->  30 3 * * * BACKUP_HOST=deploy@<MEDIA_IP> /var/www/edu_platform/deploy/new/backup.sh >> /var/backups/edu/backup.log 2>&1
#
# TIKLASH (tekshirib ko'ring!):  cat db_YYYY-MM-DD_HHMM.dump | docker compose -f docker-compose.app.yml exec -T db \
#                                 pg_restore -U edtech -d edtech --clean --if-exists
set -euo pipefail
cd /var/www/edu_platform
DIR=/var/backups/edu
STAMP=$(date +%F_%H%M)
mkdir -p "$DIR"

docker compose -f docker-compose.app.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DIR/db_$STAMP.dump"
test -s "$DIR/db_$STAMP.dump" || { echo "XATO: bo'sh zaxira"; rm -f "$DIR/db_$STAMP.dump"; exit 1; }
find "$DIR" -name 'db_*.dump' -mtime +14 -delete
echo "$(date -Is) zaxira tayyor: db_$STAMP.dump ($(du -h "$DIR/db_$STAMP.dump" | cut -f1))"

if [ -n "${BACKUP_HOST:-}" ]; then
  rsync -az --delete-after -e "ssh -i $HOME/.ssh/backup_key -o StrictHostKeyChecking=accept-new" \
    "$DIR/" "$BACKUP_HOST:/var/backups/edu-app/"
  echo "$(date -Is) $BACKUP_HOST ga ko'chirildi"
fi
