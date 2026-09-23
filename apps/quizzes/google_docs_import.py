"""Ochiq (public) Google Docs hujjatidan test savollarini import qilish.

O'qituvchi Google Docs'da xuddi `.docx` import kutgan formatda matn yozadi
(`docx_import.py`dagi hujjatga qarang), hujjatni "Havolaga ega har kim
ko'ra oladi" qilib ulashadi va bizga faqat havolani beradi.

OAuth KERAK EMAS — Google'ning ochiq eksport manzili (`/export?format=txt`)
hujjat "ochiq" bo'lsa hech qanday autentifikatsiyasiz matnni qaytaradi (bu
Google Sheets'dagi kabi ochiq eksport, Google Forms'dan farqli — Forms
tuzilishini o'qish esa har doim OAuth talab qiladi, shuning uchun Forms
emas, aynan Docs tanlangan).

Xavfsizlik: foydalanuvchi bergan URL to'g'ridan-to'g'ri so'ralmaydi — undan
faqat hujjat ID'si (qat'iy regex bilan) ajratib olinadi, so'ng BIZ o'zimiz
`docs.google.com` manziliga o'zimiz tuzgan eksport havolasini so'raymiz
(SSRF'ning oldi olinadi — host har doim docs.google.com bo'ladi).
"""
import re

import requests
from rest_framework.exceptions import ValidationError

from .docx_import import _normalize, parse_lines

MAX_RESPONSE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB — oddiy matn hujjati uchun ko'p ortig'i bilan yetarli
_REQUEST_TIMEOUT_SEC = 10

_DOC_ID_RE = re.compile(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)')


def _extract_doc_id(url: str) -> str:
    match = _DOC_ID_RE.search((url or '').strip())
    if not match:
        raise ValidationError({'url': "Google Docs havolasi noto'g'ri ko'rinishda."})
    return match.group(1)


def _fetch_doc_text(doc_id: str) -> str:
    export_url = f'https://docs.google.com/document/d/{doc_id}/export?format=txt'
    try:
        response = requests.get(export_url, timeout=_REQUEST_TIMEOUT_SEC, allow_redirects=True)
    except requests.RequestException as exc:
        raise ValidationError({'url': f"Google Docs'ga ulanib bo'lmadi: {exc}"}) from exc

    # Yopiq (ulashilmagan) hujjat so'ralsa, Google login sahifasiga (HTML)
    # yo'naltiradi — buni aniq xabar bilan ajratamiz.
    content_type = response.headers.get('Content-Type', '')
    if response.status_code != 200 or 'text/plain' not in content_type:
        raise ValidationError({'url': (
            "Hujjatni o'qib bo'lmadi — u \"Havolaga ega har kim ko'ra oladi\" "
            "qilib ulashilganiga ishonch hosil qiling."
        )})
    if len(response.content) > MAX_RESPONSE_SIZE_BYTES:
        raise ValidationError({'url': "Hujjat juda katta."})
    return response.text


def parse_google_doc(*, url: str) -> dict:
    """`url` — ochiq Google Docs havolasi. Qaytaradi: `docx_import.parse_lines`
    bilan bir xil shakl (preview — hech narsa saqlanmaydi)."""
    doc_id = _extract_doc_id(url)
    text = _fetch_doc_text(doc_id)
    lines = [_normalize(line) for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValidationError({'url': "Hujjat bo'sh."})
    return parse_lines(lines)
