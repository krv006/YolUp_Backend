"""Ikki server bir-birini kuzatadi va holat o'zgarsa (yiqildi / tiklandi) Telegram yoki webhook orqali xabar beradi.

    python manage.py watchdog

Tashqi hisob kerak emas: APP serveri MEDIA'ni (LiveKit va yozuv xizmati), MEDIA serveri APP'ni tekshiradi. Ikkalasi ham bir vaqtda
yiqilsa kuzatuvchi ham yo'q, shuning uchun tashqi monitoring (masalan UptimeRobot) baribir foydali.

Sozlash (.env, ikkala serverda):
    ALERT_TELEGRAM_BOT_TOKEN=...   ALERT_TELEGRAM_CHAT_ID=...    (@BotFather'dan bot oching, guruhga/o'zingizga qo'shing)
    ALERT_WEBHOOK_URL=https://...  (ixtiyoriy: Slack/Discord kabi `{"text": ...}` qabul qiladigan manzil)
    WATCHDOG_FAIL_AFTER=2          (ketma-ket nechta muvaffaqiyatsiz tekshiruvdan keyin "yiqildi" deyiladi; standart 2)
Hech biri berilmasa faqat log yoziladi (ERROR). Holat fayli diskda (`logs/watchdog_state.json`): Redis/WireGuard ishlamay qolganda ham ishlaydi.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger('apps')
TIMEOUT = 8


def check_url(url: str, headers=None, expect_status=(200,)) -> tuple:
    """(ok, tafsilot). Javob berdimi va kutilgan holatdami."""
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 — manzillar o'z sozlamamizdan
            return response.status in expect_status, f'HTTP {response.status}'
    except urllib.error.HTTPError as exc:
        return exc.code in expect_status, f'HTTP {exc.code}'
    except Exception as exc:  # noqa: BLE001 — tarmoq xatosi, vaqt tugashi va h.k. "yiqilgan" degani
        return False, type(exc).__name__


def targets() -> list:
    """Shu serverdan tekshiriladigan narsalar: [(nom, url, sarlavhalar)]."""
    result = []
    if settings.SERVER_ROLE == 'media':
        domain = os.getenv('DOMAIN') or (settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else '')
        if domain and domain != '*':
            result.append(('APP (sayt va API)', f'https://{domain}/api/health/', {}))
    else:
        livekit = settings.LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://')
        result.append(('MEDIA: LiveKit (jonli dars)', livekit, {}))
        upstream = os.getenv('REC_UPSTREAM')  # APP'dagi Caddy ham shu manzilga yozuvlarni yuboradi (WireGuard orqali)
        if upstream:
            host = (settings.ALLOWED_HOSTS or [''])[0]
            result.append(('MEDIA: yozuv xizmati', f'http://{upstream}/api/health/', {'Host': host, 'X-Forwarded-Proto': 'https'}))
    return result


def state_path() -> Path:
    return Path(os.getenv('WATCHDOG_STATE_FILE', settings.BASE_DIR / 'logs' / 'watchdog_state.json'))


def load_state() -> dict:
    try:
        return json.loads(state_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        path = state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding='utf-8')
    except OSError:
        logger.exception('watchdog holati saqlanmadi')


def send_alert(text: str) -> bool:
    """Telegram va/yoki webhook'ga yuboradi. Hech biri sozlanmagan bo'lsa False."""
    sent = False
    token, chat = os.getenv('ALERT_TELEGRAM_BOT_TOKEN'), os.getenv('ALERT_TELEGRAM_CHAT_ID')
    if token and chat:
        data = urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode()
        sent = _post(f'https://api.telegram.org/bot{token}/sendMessage', data, {}) or sent
    webhook = os.getenv('ALERT_WEBHOOK_URL')
    if webhook:
        sent = _post(webhook, json.dumps({'text': text}).encode(), {'Content-Type': 'application/json'}) or sent
    return sent


def _post(url: str, data: bytes, headers: dict) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=TIMEOUT):  # noqa: S310
            return True
    except Exception:  # noqa: BLE001 — xabar yuborilmasa ham tekshiruv davom etsin
        logger.exception('alert yuborilmadi')
        return False


class Command(BaseCommand):
    help = "Ikkinchi serverni tekshiradi; yiqilsa/tiklansa Telegram yoki webhook orqali xabar beradi."

    def handle(self, *args, **options):
        fail_after = max(1, int(os.getenv('WATCHDOG_FAIL_AFTER', '2')))
        role = settings.SERVER_ROLE or 'app'
        state = load_state()
        for name, url, headers in targets():
            ok, detail = check_url(url, headers)
            entry = state.get(name, {'fails': 0, 'down': False})
            if ok:
                if entry['down']:
                    logger.warning('watchdog: %s tiklandi', name)
                    send_alert(f'✅ TIKLANDI: {name} yana ishlayapti ({role} serveridan ko\'rinishi).')
                entry = {'fails': 0, 'down': False}
            else:
                entry['fails'] += 1
                logger.error('watchdog: %s ishlamayapti (%s), ketma-ket %s marta', name, detail, entry['fails'])
                if entry['fails'] >= fail_after and not entry['down']:
                    entry['down'] = True
                    send_alert(f'🚨 YIQILDI: {name} javob bermayapti ({detail}). {role} serveridan {entry["fails"]} marta ketma-ket tekshirildi.')
            state[name] = entry
            self.stdout.write(f'{name}: {"OK" if ok else "XATO"} ({detail})')
        save_state(state)
