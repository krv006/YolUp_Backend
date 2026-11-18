#!/bin/sh
# Chiquvchi SMTP'ning 25 va 465 portlarini yopadi (server va Docker konteynerlari uchun): netcup "Mail block" siyosati o'chirilgandan keyin
# server spam yuborishga ishlatilmasligi uchun. 587 OCHIQ qoladi (ilova Gmail/Brevo orqali shu portda xat yuboradi).
# Ishlatish: block-smtp-egress.sh add | del | status   (systemd: block-smtp-egress.service)
set -eu
PORTS="25,465"

apply() {
  for tool in iptables ip6tables; do
    command -v "$tool" >/dev/null 2>&1 || continue
    for chain in OUTPUT DOCKER-USER; do
      "$tool" -w -S "$chain" >/dev/null 2>&1 || continue   # DOCKER-USER docker ishga tushgach paydo bo'ladi
      case "$1" in
        add) "$tool" -w -C "$chain" -p tcp -m multiport --dports "$PORTS" -j REJECT --reject-with tcp-reset 2>/dev/null \
               || "$tool" -w -I "$chain" 1 -p tcp -m multiport --dports "$PORTS" -j REJECT --reject-with tcp-reset ;;
        del) while "$tool" -w -C "$chain" -p tcp -m multiport --dports "$PORTS" -j REJECT --reject-with tcp-reset 2>/dev/null; do
               "$tool" -w -D "$chain" -p tcp -m multiport --dports "$PORTS" -j REJECT --reject-with tcp-reset
             done ;;
      esac
    done
  done
}

case "${1:-status}" in
  add|del) apply "$1" ;;
  status)
    for tool in iptables ip6tables; do
      command -v "$tool" >/dev/null 2>&1 || continue
      for chain in OUTPUT DOCKER-USER; do
        "$tool" -w -S "$chain" 2>/dev/null | grep -- "--dports $PORTS" | sed "s/^/[$tool] /" || true
      done
    done ;;
  *) echo "ishlatish: $0 add|del|status" >&2; exit 2 ;;
esac
