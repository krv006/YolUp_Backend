"""Tashqi "AI-home-checker" xizmati (RJalol/AI-home-checker) bilan ishlash.

Bu — bizning backend ichidagi AI EMAS: alohida Docker xizmati (`deploy/ai-home-checker/`),
uni biz oddiy HTTP so'rovlar bilan chaqiramiz. Xizmat sozlanmagan (`HOMEWORK_AI_URL`
bo'sh) yoki ishlamay qolsa, uy vazifasi to'g'ridan-to'g'ri o'qituvchiga baholash uchun
tushadi — AI bo'lmasa ham tizim ishlayveradi.

Xizmat API'si (uning README/api.py'sidan):
  POST /submissions       — fayl yuboradi, darhol `pending_ai` holatda id qaytaradi
  GET  /submissions/{id}  — holat: pending_ai | pending_review | approved | grading_failed,
                            `ai_result` — baholash JSON'i (overall_score, grade, questions[], summary)
Autentifikatsiya: `X-Internal-Api-Key` (butun API) + `X-Organization-Api-Key` (bizning tashkilot).
"""
import logging
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger('apps')

# Bizning Course.Subject kodi -> (xizmatdagi subject_key, maxsus fan nomi, til kaliti).
# Xizmat standart fanlari: math, physics, chemistry, biology, computer_science,
# essay, history, general; tillar: english, russian, turkish.
_SUBJECT_MAP = {
    'math': ('math', '', ''),
    'physics': ('physics', '', ''),
    'astronomy': ('physics', '', ''),
    'chemistry': ('chemistry', '', ''),
    'biology': ('biology', '', ''),
    'ecology': ('biology', '', ''),
    'computer_science': ('computer_science', '', ''),
    'history': ('history', '', ''),
    'literature': ('essay', '', ''),
    'geography': ('general', 'Geography', ''),
    'civics': ('general', 'Civics', ''),
    'economics': ('general', 'Economics', ''),
    'music': ('general', 'Music', ''),
    'art': ('general', 'Art', ''),
    'physical_education': ('general', 'Physical Education', ''),
    'technology': ('general', 'Technology', ''),
    'chess': ('general', 'Chess', ''),
    'english': ('general', 'English', 'english'),
    'russian': ('general', 'Russian', 'russian'),
    'turkish': ('general', 'Turkish', 'turkish'),
    'german': ('general', 'German', ''),
    'french': ('general', 'French', ''),
    'arabic': ('general', 'Arabic', ''),
    'chinese': ('general', 'Chinese', ''),
    'korean': ('general', 'Korean', ''),
    'japanese': ('general', 'Japanese', ''),
    'other': ('general', 'General', ''),
}
_SUPPORTED_LANGUAGE_KEYS = {'english', 'russian', 'turkish'}


class AIServiceError(Exception):
    pass


def enabled() -> bool:
    return bool(getattr(settings, 'HOMEWORK_AI_URL', '')) and bool(getattr(settings, 'HOMEWORK_AI_ORG_KEY', ''))


def subject_fields(course_subject: str, skill_key: str) -> dict:
    """Kurs fani + vazifa ko'nikmasi -> xizmatga yuboriladigan fan/til maydonlari."""
    subject_key, custom_name, language_key = _SUBJECT_MAP.get(course_subject or '', ('general', 'General', ''))
    fields = {'subject_key': subject_key, 'custom_subject_name': custom_name, 'language_key': '', 'skill_key': ''}
    if language_key in _SUPPORTED_LANGUAGE_KEYS and skill_key:
        fields.update(language_key=language_key, skill_key=skill_key)
    return fields


def _headers() -> dict:
    headers = {'X-Organization-Api-Key': settings.HOMEWORK_AI_ORG_KEY}
    internal = getattr(settings, 'HOMEWORK_AI_INTERNAL_KEY', '')
    if internal:
        headers['X-Internal-Api-Key'] = internal
    return headers


def _base() -> str:
    return settings.HOMEWORK_AI_URL.rstrip('/')


def _timeout() -> int:
    return getattr(settings, 'HOMEWORK_AI_TIMEOUT', 30)


def submit(submission, attempt: int = 0) -> str:
    """Faylni xizmatga yuboradi, xizmatdagi submission id'sini qaytaradi."""
    assignment = submission.assignment
    student = submission.student
    teacher = assignment.course.teacher
    data = {
        'teacher_external_id': str(teacher.id),
        'teacher_name': f'{teacher.first_name} {teacher.last_name}'.strip() or teacher.username,
        'student_external_id': str(student.id),
        'student_name': f'{student.first_name} {student.last_name}'.strip() or student.username,
        # Xizmat bir xil id'ni dublikat deb hisoblaydi — qayta tekshirishda har urinish uchun yangi id
        'external_submission_id': str(submission.id) if attempt == 0 else f'{submission.id}-r{attempt}',
        'extra_instructions': assignment.extra_instructions or '',
        **subject_fields(assignment.course.subject, assignment.skill_key),
    }
    path = Path(submission.file.path)
    try:
        with path.open('rb') as handle:
            response = requests.post(
                f'{_base()}/submissions', data=data,
                files={'file': (submission.original_name or path.name, handle)},
                headers=_headers(), timeout=_timeout(),
            )
    except (requests.RequestException, OSError) as exc:
        raise AIServiceError(f"AI xizmatiga ulanib bo'lmadi: {exc}") from exc
    if response.status_code != 200:
        raise AIServiceError(f'AI xizmati {response.status_code} qaytardi: {response.text[:200]}')
    external_id = (response.json() or {}).get('id')
    if not external_id:
        raise AIServiceError('AI xizmati submission id qaytarmadi.')
    return str(external_id)


def fetch(external_id: str) -> dict:
    try:
        response = requests.get(f'{_base()}/submissions/{external_id}', headers=_headers(), timeout=_timeout())
    except requests.RequestException as exc:
        raise AIServiceError(f"AI xizmatiga ulanib bo'lmadi: {exc}") from exc
    if response.status_code == 404:
        return {'status': 'not_found'}
    if response.status_code != 200:
        raise AIServiceError(f'AI xizmati {response.status_code} qaytardi: {response.text[:200]}')
    return response.json()
