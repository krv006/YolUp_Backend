"""IELTS Writing AI oqimi: baholash -> TAKLIF -> o'qituvchi tasdiqlaydi.

Holatlar (`ExamAttempt.ai_results['writing'].status`):
  running  — Gemini baholayapti (fon oqimi);
  proposed — taklif tayyor; ball hali o'quvchiga/umumiy bandga o'tmagan;
  approved — o'qituvchi tasdiqladi (`manual_scores['writing']` ga yozildi),
             AI izohi o'quvchiga ko'rinadi;
  failed   — xato (`error`), qayta urinish mumkin.
AI hech qachon ballni o'zi qo'ymaydi — uy vazifasidagi "AI taklifi -> o'qituvchi
tasdiqlaydi" oqimi bilan bir xil.
"""
import logging
import threading
from datetime import datetime, timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from . import scoring as scoring_engines
from . import selectors, writing_ai
from .models import Exam, ExamAnswer, ExamAttempt, ExamSection

logger = logging.getLogger('apps')

WRITING_KEY = 'writing'
# `running` shundan uzoq tursa — oqim qulagan deb hisoblanadi, qayta boshlash mumkin
STALE_RUNNING = timedelta(minutes=10)
MAX_AUTO_ATTEMPTS = 3
# Cron bir yurishda ko'pi bilan shuncha insho baholaydi (kvota/vaqtni boshqarish)
CRON_BATCH = 10


def writing_section(exam: Exam):
    """IELTS imtihonining qo'lda baholanadigan `writing` bo'limi (yo'q bo'lsa None)."""
    if exam.scoring.get('type') != 'ielts':
        return None
    return exam.sections.filter(
        key=WRITING_KEY, kind=ExamSection.Kind.SECTION, manual=True,
    ).select_related('quiz').first()


def collect_tasks(attempt: ExamAttempt, section: ExamSection) -> list:
    """Bo'lim savollaridan Task ro'yxati: oxirgi savol — Task 2, qolganlari — Task 1
    (bitta savol bo'lsa — Task 2, ya'ni insho)."""
    if section.quiz_id is None:
        return []
    questions = list(section.quiz.questions.order_by('order', 'created_at'))
    answers = {
        a.question_id: ((a.answer or {}).get('value_text') or '')
        for a in ExamAnswer.objects.filter(attempt=attempt, section=section)
    }
    tasks = []
    for index, question in enumerate(questions):
        number = 2 if index == len(questions) - 1 else 1
        tasks.append({'number': number, 'prompt': question.text, 'answer': answers.get(question.id, '')})
    return tasks


def _entry(attempt: ExamAttempt) -> dict:
    return (attempt.ai_results or {}).get(WRITING_KEY) or {}


def _is_busy(entry: dict) -> bool:
    if entry.get('status') != 'running':
        return False
    started = entry.get('started_at')
    try:
        return timezone.now() - datetime.fromisoformat(started) < STALE_RUNNING
    except (TypeError, ValueError):
        return False


def _claim(attempt_id) -> bool:
    """`running` deb belgilaydi. Allaqachon band yoki tasdiqlangan bo'lsa — False."""
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_for_update().get(pk=attempt_id)
        entry = _entry(attempt)
        if entry.get('status') == 'approved' or _is_busy(entry):
            return False
        results = dict(attempt.ai_results or {})
        results[WRITING_KEY] = {
            'status': 'running', 'started_at': timezone.now().isoformat(),
            'attempts': int(entry.get('attempts') or 0),
        }
        attempt.ai_results = results
        attempt.save(update_fields=['ai_results', 'updated_at'])
    return True


def run_check(attempt_id) -> None:
    """Baholashni bajarib natijani saqlaydi (fon oqimida yoki cron'da chaqiriladi)."""
    attempt = ExamAttempt.objects.select_related('exam', 'student').get(pk=attempt_id)
    section = writing_section(attempt.exam)
    previous = _entry(attempt)
    attempts = int(previous.get('attempts') or 0) + 1
    try:
        if section is None:
            raise writing_ai.WritingAIError('Bu imtihonda IELTS Writing bo\'limi yo\'q.')
        result = writing_ai.grade_writing(collect_tasks(attempt, section))
        entry = {
            'status': 'proposed', 'proposed_band': result['writing_band'], 'result': result,
            'generated_at': timezone.now().isoformat(), 'attempts': attempts,
        }
    except Exception as exc:  # AI/tarmoq xatosi — o'qituvchiga ko'rsatiladi
        logger.warning('IELTS Writing AI xatosi (attempt=%s): %s', attempt_id, exc)
        entry = {'status': 'failed', 'error': str(exc)[:1000], 'attempts': attempts}
    attempt.refresh_from_db(fields=['ai_results'])  # parallel o'zgarishlarni ezmaslik
    results = dict(attempt.ai_results or {})
    results[WRITING_KEY] = entry
    attempt.ai_results = results
    attempt.save(update_fields=['ai_results', 'updated_at'])


def _dispatch(attempt_id) -> None:
    if not getattr(settings, 'EXAM_AI_ASYNC', True):
        run_check(attempt_id)
        return

    def _target(pk):
        try:
            run_check(pk)
        finally:
            close_old_connections()

    threading.Thread(target=_target, args=(attempt_id,), daemon=True).start()


def _owner_check(teacher, exam: Exam) -> None:
    if exam.created_by_id != teacher.id and exam.course.teacher_id != teacher.id:
        raise PermissionDenied(_('Bu imtihon sizga tegishli emas.'))


def _attempt_of(exam: Exam, student_id) -> ExamAttempt:
    if not selectors.enrolled_students(exam).filter(pk=student_id).exists():
        raise NotFound(_("O'quvchi topilmadi."))
    attempt = ExamAttempt.objects.filter(exam=exam, student_id=student_id).first()
    if attempt is None:
        raise ValidationError({'detail': _("Bu o'quvchi imtihonda qatnashmagan.")})
    return attempt


def request_check(*, teacher, exam: Exam, student_id) -> dict:
    """O'qituvchi AI baholashni qo'lda boshlaydi (yoki xatodan keyin qayta uradi)."""
    _owner_check(teacher, exam)
    if writing_section(exam) is None:
        raise ValidationError({'detail': _("Bu imtihonda IELTS Writing bo'limi yo'q.")})
    attempt = _attempt_of(exam, student_id)
    if timezone.now() < exam.ends_at and not attempt.finished_at:
        raise ValidationError({'detail': _("AI baholash imtihon tugagandan keyin boshlanadi.")})
    if _entry(attempt).get('status') == 'approved':
        raise ValidationError({'detail': _("Bu natija allaqachon tasdiqlangan.")})
    if not _claim(attempt.pk):
        raise ValidationError({'detail': _("AI baholash allaqachon davom etmoqda.")})
    _dispatch(attempt.pk)
    attempt.refresh_from_db(fields=['ai_results'])
    return {'status': _entry(attempt).get('status', 'running')}


def approve(*, teacher, exam: Exam, student_id, band=None) -> ExamAttempt:
    """AI taklifini tasdiqlaydi: band (berilmasa AI taklifi) `manual_scores`ga o'tadi."""
    _owner_check(teacher, exam)
    attempt = _attempt_of(exam, student_id)
    entry = _entry(attempt)
    if entry.get('status') not in ('proposed', 'approved'):
        raise ValidationError({'detail': _("AI taklifi hali tayyor emas.")})
    if band is None:
        band = entry['proposed_band']
    else:
        try:
            band = scoring_engines.validate_manual(exam.scoring, WRITING_KEY, band)
        except scoring_engines.ManualScoreError as exc:
            raise ValidationError({'band': str(exc)})
    attempt.manual_scores = {**(attempt.manual_scores or {}), WRITING_KEY: float(band)}
    results = dict(attempt.ai_results or {})
    results[WRITING_KEY] = {
        **entry, 'status': 'approved', 'approved_band': float(band),
        'approved_by': str(teacher.id), 'approved_at': timezone.now().isoformat(),
    }
    attempt.ai_results = results
    attempt.save(update_fields=['manual_scores', 'ai_results', 'updated_at'])
    return attempt


def ai_payload(attempt: ExamAttempt, staff: bool) -> dict:
    """Natijaga qo'shiladigan AI bloki. O'qituvchi — hamma holat va taklif;
    o'quvchi/ota-ona — faqat TASDIQLANGAN izoh."""
    payload = {}
    for key, entry in (attempt.ai_results or {}).items():
        status = entry.get('status')
        if staff:
            payload[key] = {
                'status': status, 'proposed_band': entry.get('proposed_band'),
                'approved_band': entry.get('approved_band'), 'result': entry.get('result'),
                'error': entry.get('error', ''), 'generated_at': entry.get('generated_at'),
            }
        elif status == 'approved':
            payload[key] = {'status': 'approved', 'result': entry.get('result')}
    return payload


def pending_attempts(limit: int = CRON_BATCH) -> list:
    """Tugagan IELTS imtihonlarida hali AI taklifi yo'q (yoki xato bilan tugagan,
    urinishlari tugamagan) insholar — cron avtomatik baholaydi."""
    now = timezone.now()
    exams = Exam.objects.filter(
        ends_at__lt=now, ends_at__gt=now - timedelta(days=14), scoring__type='ielts',
    ).order_by('ends_at')
    found = []
    for exam in exams:
        section = writing_section(exam)
        if section is None:
            continue
        answered = set(
            ExamAnswer.objects.filter(attempt__exam=exam, section=section).values_list('attempt_id', flat=True)
        )
        for attempt in exam.attempts.filter(pk__in=answered):
            entry = _entry(attempt)
            status = entry.get('status')
            if status in ('proposed', 'approved') or _is_busy(entry):
                continue
            if status == 'failed' and int(entry.get('attempts') or 0) >= MAX_AUTO_ATTEMPTS:
                continue
            found.append(attempt.pk)
            if len(found) >= limit:
                return found
    return found
