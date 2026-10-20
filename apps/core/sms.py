"""SMS yuborish (parolni tiklash, 2FA kodi). Provayder sozlamadan tanlanadi:

  - `SMS_BACKEND=eskiz` (yoki `ESKIZ_EMAIL`/`ESKIZ_PASSWORD` berilsa avtomatik) — Eskiz.uz (notify.eskiz.uz).
  - `SMS_BACKEND=console` — faqat log'ga yozadi (ishlab chiqish va testlar; xabarlar `sent` ro'yxatida).
  - bo'sh — provayder ULANMAGAN: `send_sms` 503 (`sms_not_configured`) beradi, kod yuborilgan deb yolg'on aytilmaydi.

Eskiz uchun kerak: `ESKIZ_EMAIL`, `ESKIZ_PASSWORD` va (ixtiyoriy) `ESKIZ_FROM` (standart `4546`). Eskiz sinov rejimida faqat
tasdiqlangan shablon matnlarini o'tkazadi — matn `SMS_CODE_TEMPLATE` orqali o'zgartiriladi.
"""
import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

logger = logging.getLogger('apps')

sent: list = []  # `console` backend: [(telefon, matn)] — testlar tekshiradi


class SmsNotConfigured(APIException):
    status_code = 503
    default_code = 'sms_not_configured'
    default_detail = _("SMS xizmati hali ulanmagan. Keyinroq urinib ko'ring yoki administrator bilan bog'laning.")


class SmsFailed(APIException):
    status_code = 502
    default_code = 'sms_failed'
    default_detail = _("SMS yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring.")


def normalize_phone(raw: str) -> str:
    """`+998 90 123-45-67`, `901234567`, `998901234567` -> `998901234567` (faqat raqamlar). Bo'sh/noto'g'ri -> ''."""
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 9:
        digits = '998' + digits
    return digits if 9 <= len(digits) <= 15 else ''


def phone_variants(raw: str) -> list:
    """Bazada telefon turli ko'rinishda saqlangan bo'lishi mumkin — qidirish uchun mumkin bo'lgan yozilishlar."""
    digits = normalize_phone(raw)
    if not digits:
        return []
    tail = digits[-9:]
    return list(dict.fromkeys([(raw or '').strip(), f'+{digits}', digits, tail, f'+998 {tail[:2]} {tail[2:5]} {tail[5:7]} {tail[7:]}']))


def mask_phone(raw: str) -> str:
    digits = normalize_phone(raw)
    return f'+{digits[:3]}{"*" * max(len(digits) - 7, 2)}{digits[-4:]}' if digits else ''


def backend_name() -> str:
    name = (getattr(settings, 'SMS_BACKEND', '') or '').lower()
    if not name and getattr(settings, 'ESKIZ_EMAIL', '') and getattr(settings, 'ESKIZ_PASSWORD', ''):
        return 'eskiz'
    return name


def configured() -> bool:
    return backend_name() in ('eskiz', 'console')


def _eskiz_token(force: bool = False) -> str:
    token = None if force else cache.get('sms:eskiz:token')
    if token:
        return token
    response = requests.post(
        'https://notify.eskiz.uz/api/auth/login',
        data={'email': settings.ESKIZ_EMAIL, 'password': settings.ESKIZ_PASSWORD}, timeout=10,
    )
    response.raise_for_status()
    token = (response.json().get('data') or {}).get('token')
    if not token:
        raise SmsFailed()
    cache.set('sms:eskiz:token', token, 20 * 24 * 3600)
    return token


def _eskiz_send(phone: str, text: str) -> None:
    payload = {'mobile_phone': phone, 'message': text, 'from': getattr(settings, 'ESKIZ_FROM', '4546')}
    for attempt in (0, 1):
        response = requests.post(
            'https://notify.eskiz.uz/api/message/sms/send', data=payload,
            headers={'Authorization': f'Bearer {_eskiz_token(force=bool(attempt))}'}, timeout=10,
        )
        if response.status_code == 401 and not attempt:
            continue  # token eskirgan — yangilab qayta urinamiz
        response.raise_for_status()
        return


def send_sms(raw_phone: str, text: str) -> None:
    """SMS yuboradi. Provayder yo'q — `SmsNotConfigured` (503); provayder xatosi — `SmsFailed` (502)."""
    phone = normalize_phone(raw_phone)
    if not phone:
        raise SmsFailed(_("Telefon raqami noto'g'ri."))
    name = backend_name()
    if name == 'console':
        sent.append((phone, text))
        logger.info('SMS (console) -> %s: %s', phone, text)
        return
    if name != 'eskiz':
        raise SmsNotConfigured()
    try:
        _eskiz_send(phone, text)
    except SmsFailed:
        raise
    except Exception:  # noqa: BLE001 — tarmoq/provayder xatosi mijozga ichki tafsilotsiz
        logger.exception('SMS yuborilmadi (%s)', mask_phone(phone))
        raise SmsFailed() from None


def code_text(code: str) -> str:
    template = getattr(settings, 'SMS_CODE_TEMPLATE', '') or 'YolUp tasdiqlash kodi: {code}. Hech kimga bermang.'
    return template.format(code=code)
