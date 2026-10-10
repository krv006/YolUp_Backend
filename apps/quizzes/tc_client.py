"""Tashqi "Test-creator" xizmati (RJalol/Test-creator) bilan ishlash.

Bu — bizning backend ichidagi AI EMAS: alohida Docker xizmati (`deploy/test-creator/`), tashqariga
ochilmaydi, faqat bizning backend ichki tarmoq orqali chaqiradi. Xizmat sozlanmagan
(`TEST_CREATOR_URL` bo'sh) bo'lsa "AI bilan test yaratish" o'chiq turadi.

Xizmatdagi to'liq oqim (uning API'sidan, 2026-10 versiyasi):
  POST /auth/login                             — JWT (biz bitta "xizmat hisobi" bilan kiramiz)
  GET  /subjects, /standards, /standards/{id}/versions  (standart kodi -> id: GET /standards)
  POST /documents (multipart file, subject_id) — material yuklash
  POST /documents/{id}/process                 — fon (Celery) tahlil; GET /documents/{id}/status
  POST /blueprints                             — test rejasi (standart + savollar soni)
  POST /tests/generate                         — FONDA boshlaydi (202); GET /tests/{id} — holat:
                                                 generating -> ready | partial | failed
  GET  /tests/{id}/export?format=json&mode=teacher — bizning JSON importer o'qiydigan eksport
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger('apps')

# Bizning standart kodi -> Test-creator'dagi `Standard.code`
STANDARD_CODES = {'uzbmb': 'UZBMB', 'ielts': 'IELTS_ACADEMIC', 'sat': 'DIGITAL_SAT'}

# Bizning Course.Subject -> Test-creator fan kodi (qolganlari GENERAL)
_SUBJECT_CODES = {
    'math': 'MATH', 'english': 'ENGLISH', 'physics': 'PHYSICS', 'chemistry': 'CHEMISTRY',
    'history': 'HISTORY', 'biology': 'BIOLOGY',
}

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.txt', '.md', '.csv', '.xlsx', '.xlsm'}

_state = {'token': None}


class TestCreatorError(Exception):
    """`permanent=True` — qayta urinish foydasiz (xizmat so'rovni rad etdi); aks holda vaqtinchalik
    (tarmoq/server xatosi) — keyingi siklda qayta uriniladi."""

    def __init__(self, message: str, *, permanent: bool = False):
        super().__init__(message)
        self.permanent = permanent


def enabled() -> bool:
    return bool(getattr(settings, 'TEST_CREATOR_URL', '')) and bool(getattr(settings, 'TEST_CREATOR_EMAIL', '')) \
        and bool(getattr(settings, 'TEST_CREATOR_PASSWORD', ''))


def tc_subject_code(course_subject: str) -> str:
    return _SUBJECT_CODES.get(course_subject or '', 'GENERAL')


def _url(path: str) -> str:
    return settings.TEST_CREATOR_URL.rstrip('/') + path


def _raw(method: str, path: str, *, timeout=None, **kwargs) -> requests.Response:
    try:
        return requests.request(
            method, _url(path), timeout=timeout or settings.TEST_CREATOR_TIMEOUT, **kwargs,
        )
    except requests.RequestException as exc:
        raise TestCreatorError(f'Test-creator xizmatiga ulanib bo\'lmadi: {exc}') from exc


def _detail(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    detail = body.get('detail') if isinstance(body, dict) else body
    return str(detail)[:300]


def _login() -> str:
    credentials = {'email': settings.TEST_CREATOR_EMAIL, 'password': settings.TEST_CREATOR_PASSWORD}
    response = _raw('POST', '/auth/login', json=credentials)
    if response.status_code == 401:
        # Birinchi ishga tushirish: xizmat hisobi hali yo'q — ro'yxatdan o'tkazishga urinamiz
        # (xizmatda ro'yxatdan o'tish yopiq bo'lsa, hisob `create-user` bilan oldindan yaratilgan bo'lishi kerak).
        register = _raw('POST', '/auth/register', json={
            **credentials, 'organization_name': settings.TEST_CREATOR_ORG_NAME, 'full_name': 'Edu Platform',
        })
        if register.status_code == 403:  # yangi versiyada ro'yxatdan o'tish odatda yopiq (ALLOW_REGISTRATION=false)
            raise TestCreatorError(
                "Test-creator'da xizmat hisobi yo'q. Uni serverda yarating: `python -m app.cli create-user` "
                "(deploy/test-creator/README.md, 3-qadam).", permanent=True,
            )
        if register.status_code not in (200, 201):
            raise TestCreatorError(
                f'Test-creator xizmat hisobi yaratilmadi ({register.status_code}): {_detail(register)}',
                permanent=True,
            )
        response = register
    if response.status_code >= 500:
        raise TestCreatorError(f'Test-creator kirish xatosi ({response.status_code})')
    if response.status_code != 200 and response.status_code != 201:
        raise TestCreatorError(
            f'Test-creator kirish rad etildi ({response.status_code}): {_detail(response)}', permanent=True,
        )
    return response.json()['access_token']


def _request(method: str, path: str, *, timeout=None, **kwargs) -> requests.Response:
    """Avtorizatsiyali so'rov. Token eskirsa (401) bir marta qayta kiradi. 5xx — vaqtinchalik xato,
    4xx — doimiy (so'rovning o'zi noto'g'ri)."""
    for attempt in (1, 2):
        if _state['token'] is None:
            _state['token'] = _login()
        headers = {'Authorization': f'Bearer {_state["token"]}'}
        response = _raw(method, path, timeout=timeout, headers=headers, **kwargs)
        if response.status_code == 401 and attempt == 1:
            _state['token'] = None
            continue
        break
    if response.status_code >= 500:
        raise TestCreatorError(f'Test-creator server xatosi ({response.status_code}): {_detail(response)}')
    if response.status_code >= 400:
        raise TestCreatorError(
            f'Test-creator so\'rovni rad etdi ({response.status_code}): {_detail(response)}', permanent=True,
        )
    return response


def _subject_id(code: str) -> str | None:
    subjects = _request('GET', '/subjects').json()
    by_code = {s['code']: s['id'] for s in subjects}
    return by_code.get(code) or by_code.get('GENERAL')


def _standard_version_id(our_code: str) -> str:
    tc_code = STANDARD_CODES[our_code]
    standards = _request('GET', '/standards').json()
    standard = next((item for item in standards if item.get('code') == tc_code), None)
    if standard is None:
        raise TestCreatorError(f"Test-creator'da «{tc_code}» standarti topilmadi.", permanent=True)
    versions = _request('GET', f'/standards/{standard["id"]}/versions').json()  # eng yangisi birinchi
    if not versions:
        raise TestCreatorError(f"Test-creator'da «{tc_code}» standarti versiyasi topilmadi.", permanent=True)
    return versions[0]['id']


def upload_document(*, filename: str, content: bytes, course_subject: str, title: str) -> str:
    """Materialni yuklaydi va fon tahlilini boshlaydi. Qaytaradi: hujjat id."""
    subject_id = _subject_id(tc_subject_code(course_subject))
    params = {'title': title}
    if subject_id:
        params['subject_id'] = subject_id  # bilimlar xaritasi shu fan bo'yicha tuziladi
    document = _request(
        'POST', '/documents', params=params, files={'file': (filename, content)},
        timeout=settings.TEST_CREATOR_GENERATE_TIMEOUT,
    ).json()
    _request('POST', f'/documents/{document["id"]}/process')
    return document['id']


def document_status(document_id: str) -> dict:
    """`extraction_status`: pending/parsing/chunking/embedding/knowledge_extraction/done/failed."""
    return _request('GET', f'/documents/{document_id}/status').json()


def start_generation(*, document_id: str, standard: str, title: str, count: int) -> str:
    """Reja tuzadi va test yaratishni FONDA boshlaydi (xizmat 202 qaytaradi). Qaytaradi: test id."""
    blueprint = _request('POST', '/blueprints', json={
        'standard_version_id': _standard_version_id(standard),
        'document_id': document_id,
        'name': title,
        'requested_total': count,
    }).json()
    started = _request('POST', '/tests/generate', json={'blueprint_id': blueprint['id'], 'title': title}).json()
    return started['id']


def test_status(test_id: str) -> dict:
    """`status`: generating | ready | partial | failed; `error_message`; `capacity_notes`."""
    return _request('GET', f'/tests/{test_id}').json()


def export_json(test_id: str) -> bytes:
    """O'qituvchi nusxasi (javoblar bilan) JSON ko'rinishida (`apps.quizzes.test_creator_import` o'qiydi)."""
    return _request(
        'GET', f'/tests/{test_id}/export', params={'format': 'json', 'mode': 'teacher'},
        timeout=settings.TEST_CREATOR_GENERATE_TIMEOUT,
    ).content
