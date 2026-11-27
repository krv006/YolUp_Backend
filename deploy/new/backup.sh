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
# Saqlash: kunlik 14 kun, haftalik ~6 oy, oylik ~13 oy (qarang pastda `find`).
# TIKLASH (tekshirib ko'ring!):  cat db_YYYY-MM-DD_HHMM.dump | docker exec -i edu_platform-db-1 \
#                                 pg_restore -U edtech -d edtech --clean --if-exists
set -euo pipefail
DIR=/var/backups/edu
STAMP=$(date +%F_%H%M)
mkdir -p "$DIR"

# `docker exec` (compose fayli joyiga bog'liq emas): papkalar qayta tuzilganda ham zaxira buzilmasin. Konteyner nomi: <loyiha>-db-1.
docker exec -i edu_platform-db-1 sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DIR/db_$STAMP.dump"
test -s "$DIR/db_$STAMP.dump" || { echo "XATO: bo'sh zaxira"; rm -f "$DIR/db_$STAMP.dump"; exit 1; }
# Saqlash muddati: kunlik nusxalar 14 kun; HAFTALIK (yakshanba) ~6 oy; OYLIK (1-sana) ~13 oy. Nusxalar kichik (~2 MB), shuning uchun
# uzoq saqlash deyarli bepul. Kunlik nom `db_YYYY-...`, haftalik `db_weekly_...`, oylik `db_monthly_...` (find shablonlari aralashmasin).
if [ "$(date +%u)" = 7 ]; then cp -p "$DIR/db_$STAMP.dump" "$DIR/db_weekly_$(date +%F).dump"; fi
if [ "$(date +%d)" = 01 ]; then cp -p "$DIR/db_$STAMP.dump" "$DIR/db_monthly_$(date +%Y-%m).dump"; fi
find "$DIR" -name 'db_[0-9]*.dump' -mtime +14 -delete
find "$DIR" -name 'db_weekly_*.dump' -mtime +190 -delete
find "$DIR" -name 'db_monthly_*.dump' -mtime +400 -delete
echo "$(date -Is) zaxira tayyor: db_$STAMP.dump ($(du -h "$DIR/db_$STAMP.dump" | cut -f1))"

if [ -n "${BACKUP_HOST:-}" ]; then
  rsync -az --delete-after -e "ssh -i $HOME/.ssh/backup_key -o StrictHostKeyChecking=accept-new" \
    "$DIR/" "$BACKUP_HOST:/var/backups/edu-app/"
  echo "$(date -Is) $BACKUP_HOST ga ko'chirildi"
fi
