"""OAuth'siz, ochiq Google Forms'dan savol/variant matnini o'qish (scraping).

MUHIM — BU RASMIY API EMAS: Google'ning hujjatlashtirilmagan ichki formati
(`FB_PUBLIC_LOAD_DATA_` JS o'zgaruvchisi, forma sahifasiga ko'milgan) o'qiladi.
2026-09-23'da haqiqiy, ochiq forma bilan tasdiqlangan tuzilma asosida
yozilgan (quyidagi savol turi kodlari shu tarzda tekshirilgan). Google sahifa
formatini o'zgartirsa, bu importer ogohlantirishsiz ishlamay qolishi mumkin —
`docx_import`/`google_docs_import`dan farqli, rasmiy/barqaror kanal emas.

TO'G'RI JAVOB HAQIDA MA'LUMOT SAHIFADA UMUMAN YO'Q — Google javob kalitini
ochiq (to'ldirish) sahifasiga hech qachon yubormaydi, aks holda o'quvchi
manba kodidan javobni o'qib olardi. Shuning uchun BARCHA import qilingan
savollar `is_correct=False` bilan keladi va `warnings`da
'answer_not_detected' deb belgilanadi — DOCX importerning "javob
aniqlanmadi" holati bilan bir xil, o'qituvchi preview ekranida o'zi
to'g'ri variantni belgilaydi.

Qo'llab-quvvatlanadigan savol turlari (`FB_PUBLIC_LOAD_DATA_` ichidagi kod,
haqiqiy forma bilan tasdiqlangan):
    2 — bitta tanlov (Multiple choice / radio) -> bizning 'single'
    4 — bir nechta tanlov (Checkboxes)          -> bizning 'multiple'
Boshqa turlar (qisqa javob, paragraf, dropdown, chiziqli shkala, grid,
sana/vaqt, fayl yuklash — tasdiqlanmagan yoki variantlari yo'q) IMPORT
QILINMAYDI, `warnings`da 'unsupported_type' bilan belgilanadi.
"""
import json
import re

import requests
from rest_framework.exceptions import ValidationError

MAX_RESPONSE_SIZE_BYTES = 3 * 1024 * 1024
_REQUEST_TIMEOUT_SEC = 10

_FORM_URL_RE = re.compile(r'docs\.google\.com/forms/d/e/([a-zA-Z0-9_-]+)')
_DATA_VAR_RE = re.compile(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\])\s*;', re.DOTALL)

_TYPE_SINGLE = 2
_TYPE_MULTIPLE = 4
_SUPPORTED_TYPES = {_TYPE_SINGLE: 'single', _TYPE_MULTIPLE: 'multiple'}


def _extract_form_id(url: str) -> str:
    match = _FORM_URL_RE.search((url or '').strip())
    if not match:
        raise ValidationError({'url': "Google Forms havolasi noto'g'ri ko'rinishda (.../forms/d/e/<id>/viewform kutilgan)."})
    return match.group(1)


def _fetch_form_html(form_id: str) -> str:
    view_url = f'https://docs.google.com/forms/d/e/{form_id}/viewform'
    try:
        response = requests.get(view_url, timeout=_REQUEST_TIMEOUT_SEC, allow_redirects=True)
    except requests.RequestException as exc:
        raise ValidationError({'url': f"Google Forms'ga ulanib bo'lmadi: {exc}"}) from exc
    if response.status_code != 200:
        raise ValidationError({'url': (
            "Formani o'qib bo'lmadi — u \"Havolaga ega har kim to'ldira oladi\" "
            "qilib ulashilganiga ishonch hosil qiling."
        )})
    if len(response.content) > MAX_RESPONSE_SIZE_BYTES:
        raise ValidationError({'url': 'Forma sahifasi juda katta.'})
    return response.text


def _extract_load_data(html: str) -> list:
    match = _DATA_VAR_RE.search(html)
    if not match:
        raise ValidationError({'url': (
            "Forma tuzilishini o'qib bo'lmadi (Google ichki formatni o'zgartirgan bo'lishi mumkin)."
        )})
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValidationError({'url': "Forma ma'lumotini o'qib bo'lmadi."}) from exc


def parse_google_form(*, url: str) -> dict:
    """`url` — ochiq Google Forms `viewform` havolasi. Qaytaradi:
    `docx_import.parse_lines` bilan bir xil shakl (preview — hech narsa
    saqlanmaydi). To'g'ri javoblar HECH QACHON aniqlanmaydi — barcha
    savol `warnings`da belgilanadi, o'qituvchi preview'da tuzatadi."""
    form_id = _extract_form_id(url)
    html = _fetch_form_html(form_id)
    data = _extract_load_data(html)

    try:
        form_body = data[1]
        title = form_body[0] or ''
        raw_questions = form_body[1] or []
    except (IndexError, TypeError) as exc:
        raise ValidationError({'url': "Forma tuzilishi kutilganidan farq qiladi."}) from exc

    questions = []
    warnings = []
    for index, raw_q in enumerate(raw_questions):
        number = index + 1
        try:
            q_text = raw_q[1] or ''
            q_type = raw_q[3]
            entries = raw_q[4]
            raw_options = (entries[0][1] or []) if entries else []
            option_texts = [opt[0].strip() for opt in raw_options if opt and opt[0] and opt[0].strip()]
        except (IndexError, TypeError):
            warnings.append({'question_number': number, 'reason': 'unsupported_type'})
            continue

        mapped_type = _SUPPORTED_TYPES.get(q_type)
        if mapped_type is None:
            warnings.append({'question_number': number, 'reason': 'unsupported_type'})
            continue
        if len(option_texts) < 2:
            warnings.append({'question_number': number, 'reason': 'not_enough_options'})
            continue

        questions.append({
            'type': mapped_type,
            'text': q_text.strip(),
            'order': len(questions),
            'options': [
                {'text': text, 'is_correct': False, 'order': i}
                for i, text in enumerate(option_texts)
            ],
        })
        warnings.append({'question_number': number, 'reason': 'answer_not_detected'})

    return {
        'title': title.strip()[:200],
        'description': '',
        'questions': questions,
        'warnings': warnings,
    }
