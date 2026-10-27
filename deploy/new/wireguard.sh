#!/usr/bin/env bash
# Ikki server o'rtasida YOPIQ kanal (WireGuard): baza va Redis internetga ochilmasdan MEDIA serverga ko'rinadi,
# MEDIA serverdagi yozuv API'si faqat shu kanal orqali tinglaydi.
#
# Ikki bosqich. Ikkala serverda ham root sifatida (yoki sudo bilan):
#
#   1) Har serverda ochiq kalitni oling:
#        bash wireguard.sh core            (APP/RS 2000 da)  -> chiqqan OCHIQ KALITni yozib oling
#        bash wireguard.sh media           (MEDIA/RS 4000 da) -> chiqqan OCHIQ KALITni yozib oling
#   2) Har serverda ikkinchisining PUBLIC IP va OCHIQ KALITi bilan ulang:
#        bash wireguard.sh core  <MEDIA_PUBLIC_IP> <MEDIA_OCHIQ_KALIT>     (APP serverda)
#        bash wireguard.sh media <APP_PUBLIC_IP>   <APP_OCHIQ_KALIT>       (MEDIA serverda)
#
# Kanal manzillari: APP = 10.10.0.1, MEDIA = 10.10.0.2 (.env dagi CORE_WG_IP / MEDIA_WG_IP bilan mos).
# Qayta ishga tushirsa ham zarar yo'q (idempotent). Maxfiy kalit serverdan chiqmaydi.
set -euo pipefail

ROLE="${1:-}"
PEER_IP="${2:-}"
PEER_KEY="${3:-}"
case "$ROLE" in
  core)  ME=10.10.0.1; PEER=10.10.0.2 ;;
  media) ME=10.10.0.2; PEER=10.10.0.1 ;;
  *) echo "Ishlatish: bash wireguard.sh core|media [<ikkinchi_server_public_ip> <ikkinchi_server_ochiq_kalit>]"; exit 1 ;;
esac
[ "$(id -u)" = 0 ] || { echo "root sifatida ishga tushiring (sudo bash wireguard.sh ...)"; exit 1; }
export DEBIAN_FRONTEND=noninteractive

apt-get install -y wireguard >/dev/null
install -d -m 700 /etc/wireguard
if [ ! -f /etc/wireguard/private.key ]; then
  (umask 077; wg genkey > /etc/wireguard/private.key)
fi
wg pubkey < /etc/wireguard/private.key > /etc/wireguard/public.key

if [ -z "$PEER_IP" ] || [ -z "$PEER_KEY" ]; then
  echo
  echo "Bu serverning OCHIQ kaliti (xavfsiz, ikkinchi serverga berish mumkin):"
  cat /etc/wireguard/public.key
  echo
  echo "Keyingi qadam: ikkala serverning ochiq kalitini olgach, 2-bosqich buyrug'ini ishga tushiring (fayl boshidagi izoh)."
  exit 0
fi

cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = ${ME}/24
ListenPort = 51820
PrivateKey = $(cat /etc/wireguard/private.key)

[Peer]
PublicKey = ${PEER_KEY}
AllowedIPs = ${PEER}/32
Endpoint = ${PEER_IP}:51820
PersistentKeepalive = 25
EOF
chmod 600 /etc/wireguard/wg0.conf
systemctl enable wg-quick@wg0 >/dev/null 2>&1
systemctl restart wg-quick@wg0

# Firewall: WireGuard portiga FAQAT ikkinchi serverdan; xizmat portlariga FAQAT kanal ichidan
ufw allow from "$PEER_IP" to any port 51820 proto udp comment 'WireGuard (ikkinchi server)'
if [ "$ROLE" = "core" ]; then
  ufw allow in on wg0 to any port 5432 proto tcp comment 'Postgres (MEDIA rec)'
  ufw allow in on wg0 to any port 6379 proto tcp comment 'Redis (MEDIA rec)'
else
  ufw allow in on wg0 to any port 8000 proto tcp comment 'Yozuv API (APP Caddy)'
fi
ufw reload >/dev/null

# Docker WireGuard manzilida port ochadi — kanal docker'dan OLDIN ko'tarilgan bo'lsin (qayta yoqilganda ham)
install -d /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/wireguard.conf <<'EOF'
[Unit]
After=wg-quick@wg0.service
Wants=wg-quick@wg0.service
EOF
systemctl daemon-reload

echo
echo ">> Tekshiruv (ikkinchi server ham 2-bosqichni bajargan bo'lsa ishlaydi):"
if ping -c 3 -W 2 "$PEER" >/dev/null 2>&1; then
  echo "OK: $PEER ga kanal orqali ping o'tdi"
else
  echo "Hali ping o'tmadi — ikkinchi serverda 2-bosqich bajarilganini va ikkala serverda ham ufw'da 51820/udp ochilganini tekshiring."
fi
wg show wg0 | sed 's/^\(  *private key:\).*/\1 (yashirin)/'
