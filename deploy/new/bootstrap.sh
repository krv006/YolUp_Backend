#!/usr/bin/env bash
# Yangi netcup serverini birinchi marta tayyorlash (Ubuntu 24.04, root sifatida, BIR MARTA):
#
#   bash bootstrap.sh app            # APP server (sayt, baza)
#   bash bootstrap.sh media          # MEDIA server (LiveKit)
#   bash bootstrap.sh app --lock-ssh # + parol bilan kirishni o'chirish (faqat SSH kalit sinab ko'rilgandan KEYIN)
#
# Nima qiladi: yangilaydi, Docker o'rnatadi, `deploy` foydalanuvchisini yaratadi (root'ning SSH kalitlari ko'chiriladi),
# firewall (ufw), fail2ban, avtomatik xavfsizlik yangilanishlari, tarmoq sozlamalari.
# Qayta ishga tushirsa ham zarar yo'q (idempotent).
set -euo pipefail

ROLE="${1:-}"
LOCK_SSH="${2:-}"
[[ "$ROLE" == "app" || "$ROLE" == "media" ]] || { echo "Ishlatish: bash bootstrap.sh app|media [--lock-ssh]"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "root sifatida ishga tushiring"; exit 1; }
export DEBIAN_FRONTEND=noninteractive

echo ">> 1/7 Tizimni yangilash..."
apt-get update -y
apt-get -y full-upgrade
apt-get install -y ca-certificates curl gnupg git ufw fail2ban unattended-upgrades chrony htop rsync tmux

echo ">> 2/7 Vaqt mintaqasi..."
timedatectl set-timezone Asia/Tashkent

echo ">> 3/7 Docker (rasmiy apt repozitoriy)..."
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }
EOF
systemctl enable --now docker
systemctl restart docker

echo ">> 4/7 'deploy' foydalanuvchisi..."
id deploy >/dev/null 2>&1 || adduser --disabled-password --gecos "" deploy
usermod -aG sudo,docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
if [ -f /root/.ssh/authorized_keys ]; then
  install -m 600 -o deploy -g deploy /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
fi
# Parolsiz hisob uchun sudo parolsiz (kirish faqat SSH kalit bilan)
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-deploy
chmod 440 /etc/sudoers.d/90-deploy
install -d -o deploy -g deploy /var/www/edu_platform /var/backups/edu

echo ">> 5/7 Firewall (ufw)..."
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP (Caddy, sertifikat)'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 443/udp comment 'HTTP/3'
if [ "$ROLE" = "media" ]; then
  ufw allow 7881/tcp comment 'LiveKit TCP'
  ufw allow 7882/udp comment 'LiveKit media'
fi
ufw --force enable

echo ">> 6/7 fail2ban va avtomatik xavfsizlik yangilanishlari..."
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
bantime = 1h
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ">> 7/7 Tarmoq sozlamalari..."
if [ "$ROLE" = "media" ]; then
  # LiveKit: ko'p UDP trafik uchun katta bufer
  cat > /etc/sysctl.d/99-livekit.conf <<'EOF'
net.core.rmem_max = 26214400
net.core.wmem_max = 26214400
EOF
  sysctl --system >/dev/null
fi

if [ "$LOCK_SSH" = "--lock-ssh" ]; then
  if [ ! -s /home/deploy/.ssh/authorized_keys ]; then
    echo "!! 'deploy' uchun SSH kalit yo'q — parol bilan kirish O'CHIRILMADI (aks holda serverdan chiqib ketasiz)."
  else
    cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
    systemctl reload ssh || systemctl reload sshd
    echo ">> SSH: parol va root bilan kirish o'chirildi. Endi faqat: ssh deploy@<IP>"
  fi
fi

cat <<EOF

Tayyor ($ROLE server). Keyingi qadamlar:
  1) YANGI terminal oynasida tekshiring:   ssh deploy@<bu serverning IP'si>     (parolsiz, kalit bilan kirishi kerak)
  2) Ishlagan bo'lsa, shu serverda:        bash bootstrap.sh $ROLE --lock-ssh     (parol bilan kirishni o'chiradi)
  3) Keyin:  ssh deploy@<IP>  ->  cd /var/www/edu_platform  ->  loyihani yuklab, docker compose'ni ishga tushiring
EOF
