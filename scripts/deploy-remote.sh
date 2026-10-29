#!/usr/bin/env bash
# Lokal kompyuterdan bitta buyruq bilan serverga deploy:
#   bash scripts/deploy-remote.sh
# Boshqa server/papka kerak bo'lsa:
#   SERVER=deploy@<SERVER_IP> APP_DIR=/var/www/edu_platform bash scripts/deploy-remote.sh
#
# Talab: SSH kalitingiz serverda bo'lishi kerak (bir marta):
#   ssh-copy-id deploy@<SERVER_IP>   (root bilan kirish o'chirilgan bo'lishi kerak)
set -euo pipefail

SERVER="${SERVER:?SERVER=deploy@<SERVER_IP> ni bering (manzil ochiq repoda saqlanmaydi)}"
APP_DIR="${APP_DIR:-/var/www/edu_platform}"

echo ">> Deploy: $SERVER -> $APP_DIR"
ssh "$SERVER" "set -e
  cd '$APP_DIR'
  git pull
  docker compose -f docker-compose.prod.yml up -d --build
  docker compose -f docker-compose.prod.yml ps
"
echo
echo ">> Tayyor: https://edu.thesofmebel.uz"
