"""Materialdan AI bilan test yaratish — ishlar va ularni yurgizish.

Ikki yo'l:
  * IMTIHON QOIDALARI bo'yicha (asosiy, `standard` bo'sh): o'qituvchi material bilan birga imtihon qoidalari
    hujjatini/matnini yuklaydi (yoki yuklamaydi — u holda oddiy variantli test). Generator `ai_exam` + `llm`
    (OpenAI-mos API) — butun ish bitta cron qadamida bajariladi (`_run_engine`).
  * Test-creator (eski, `standard` berilgan): quyidagi bosqichli oqim.

Test-creator oqimi:
  1. `create_job` — o'qituvchi fayl yuklaydi, ish `queued` bo'ladi (HTTP so'rov darhol qaytadi).
  2. `sync_jobs` (cron, `sync_ai_quizzes` buyrug'i) ishni bosqichma-bosqich olib boradi:
       queued -> materialni xizmatga yuboradi, tahlil boshlanadi        -> processing
       processing -> tahlil tugaguncha kutadi; tugasa darhol:            -> generating
       generating -> reja + savollar + eksport -> `draft` test            -> done
  3. Natija `draft` test (o'quvchiga ko'rinmaydi); o'qituvchi tahrirlab e'lon qiladi.

Xato bo'lsa (xizmat o'chiq, material o'qilmadi, vaqt tugadi) ish `failed` bo'ladi va sababi
`error` maydonida o'qituvchiga ko'rsatiladi; platformaning qolgan qismi ishlayveradi.
"""
import io
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User

from . import ai_exam, llm, material_text, services, tc_client, test_creator_import
from .models import AiQuizJob, Quiz

logger = logging.getLogger('apps')

MAX_SOURCE_MB = 20
MAX_RULES_MB = 5
MAX_RULES_TEXT = 30000
MIN_QUESTIONS, MAX_QUESTIONS = 5, 60
MAX_ACTIVE_PER_TEACHER = 3
MAX_PER_DAY = 10
_BATCH = 5  # bir siklda ko'pi bilan nechta ish
# Savollar yaratish (Gemini) muvaffaqiyatsiz bo'lsa: ko'pi bilan shuncha urinish, urinishlar orasida pauza.
# (Tashqi xizmat sababni aytmaydi, odatda Gemini'ning kunlik limiti tugagan bo'ladi — cheksiz urinish limitni yeydi.)
MAX_GENERATE_ATTEMPTS = 3
GENERATE_RETRY_PAUSE = timedelta(minutes=2)
PROCESSING_MAX = timedelta(minutes=15)  # materialni tahlil qilish odatda 1 daqiqadan kam davom etadi
GENERATE_FAILED_MESSAGE = (
    "AI savollarni yarata olmadi (ehtimol AI xizmatining kunlik limiti tugagan). Birozdan keyin qayta urinib ko'ring."
)


def _check_file(upload, field: str, max_mb: int) -> None:
    ext = Path(upload.name or '').suffix.lower()
    if ext not in tc_client.ALLOWED_EXTENSIONS:
        raise ValidationError({field: _("Fayl turi qo'llab-quvvatlanmaydi. Ruxsat: %(types)s.") % {
            'types': ', '.join(sorted(tc_client.ALLOWED_EXTENSIONS)),
        }})
    if upload.size > max_mb * 1024 * 1024:
        raise ValidationError({field: _('Fayl %(size).1f MB; chegara %(max_mb)s MB.') % {
            'size': upload.size / 1024 / 1024, 'max_mb': max_mb,
        }})


def create_job(*, teacher: User, upload, course, subject: str, topic: str, title: str, standard: str = '',
               question_count: int, rules_upload=None, rules_text: str = '') -> AiQuizJob:
    standard = standard or ''
    if standard:
        if not tc_client.enabled():
            raise ValidationError({'detail': _("AI bilan test yaratish hozir o'chirilgan. Testni qo'lda yarating yoki import qiling.")})
    elif not llm.enabled():
        raise ValidationError({'detail': _("AI bilan test yaratish hozir o'chirilgan (AI kaliti sozlanmagan). Testni qo'lda yarating yoki import qiling.")})
    if upload is None:
        raise ValidationError({'file': _('Material fayli majburiy.')})
    _check_file(upload, 'file', MAX_SOURCE_MB)
    if rules_upload is not None:
        _check_file(rules_upload, 'rules_file', MAX_RULES_MB)
    rules_text = (rules_text or '').strip()
    if len(rules_text) > MAX_RULES_TEXT:
        raise ValidationError({'rules_text': _('Qoidalar matni juda uzun (%(max)s belgigacha).') % {'max': MAX_RULES_TEXT}})
    if not topic.strip():
        raise ValidationError({'topic': _("Mavzu bo'sh bo'lishi mumkin emas.")})
    if not MIN_QUESTIONS <= question_count <= MAX_QUESTIONS:
        raise ValidationError({'question_count': _('Savollar soni %(min)s dan %(max)s gacha bo\'lishi kerak.') % {
            'min': MIN_QUESTIONS, 'max': MAX_QUESTIONS,
        }})
    if course is None:
        if not subject:
            raise ValidationError({'subject': _('Guruh yoki fan tanlanishi shart.')})
    else:
        if course.teacher_id != teacher.id:
            raise PermissionDenied(_('Bu kurs sizga tegishli emas.'))
        subject = course.subject

    mine = AiQuizJob.objects.filter(teacher=teacher)
    if mine.filter(status__in=AiQuizJob.ACTIVE_STATUSES).count() >= MAX_ACTIVE_PER_TEACHER:
        raise ValidationError({'detail': _("Sizda %(n)s ta test hali yaratilmoqda. Tugashini kuting.") % {
            'n': MAX_ACTIVE_PER_TEACHER,
        }})
    if mine.filter(created_at__gte=timezone.now() - timedelta(days=1)).count() >= MAX_PER_DAY:
        raise ValidationError({'detail': _("Bir kunda %(n)s tadan ko'p AI test yaratib bo'lmaydi.") % {'n': MAX_PER_DAY}})

    return AiQuizJob.objects.create(
        teacher=teacher, course=course, subject=subject, topic=topic.strip(), title=title.strip(),
        standard=standard, question_count=question_count, source_file=upload, source_name=upload.name or '',
        rules_file=rules_upload, rules_name=(rules_upload.name or '') if rules_upload is not None else '',
        rules_text=rules_text,
    )


# ─── Yurgizuvchi (cron) ────────────────────────────────────────────────────


def _fail(job: AiQuizJob, message: str) -> None:
    job.status = AiQuizJob.Status.FAILED
    job.error = message[:1000]
    job.save(update_fields=['status', 'error', 'updated_at'])
    _release_source(job)
    _notify(job, ok=False)


def _release_source(job: AiQuizJob) -> None:
    """Yuklangan material va qoidalar fayli kerak bo'lmagach diskdan o'chiriladi."""
    changed = []
    for field in ('source_file', 'rules_file'):
        stored = getattr(job, field)
        if stored:
            try:
                stored.delete(save=False)
            except Exception:  # noqa: BLE001
                logger.warning("AI test: yuklangan fayl o'chirilmadi", exc_info=True)
            setattr(job, field, None)
            changed.append(field)
    if changed:
        job.save(update_fields=changed + ['updated_at'])


def _notify(job: AiQuizJob, *, ok: bool) -> None:
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    if ok:
        text = f'«{job.topic}» uchun AI test tayyor — qoralama sifatida saqlandi. Ko\'rib chiqing va e\'lon qiling.'
        link_type, link_id = 'quiz', str(job.quiz_id)
    else:
        text = f'«{job.topic}» uchun AI test yaratilmadi: {job.error}'
        link_type, link_id = '', ''
    try:
        send_notification(
            sender=job.teacher, description=text, target_type=Notification.Target.USER, user_id=job.teacher_id,
            link_type=link_type, link_id=link_id, kind='ai_quiz_ready' if ok else 'ai_quiz_failed',
        )
    except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
        logger.warning('AI test bildirishnomasi yuborilmadi', exc_info=True)


def _start(job: AiQuizJob) -> None:
    content = job.source_file.read()
    job.source_file.close()
    job.tc_document_id = tc_client.upload_document(
        filename=job.source_name or Path(job.source_file.name).name, content=content,
        course_subject=job.subject, title=job.title or job.topic,
    )
    job.status = AiQuizJob.Status.PROCESSING
    job.save(update_fields=['tc_document_id', 'status', 'updated_at'])


def _check_processing(job: AiQuizJob) -> bool:
    """True — tahlil tugadi, savollar yaratishga o'tish mumkin."""
    status = tc_client.document_status(job.tc_document_id)
    extraction = status.get('extraction_status')
    if extraction == 'failed':
        raise tc_client.TestCreatorError(
            status.get('error_message') or "Materialni tahlil qilib bo'lmadi.", permanent=True,
        )
    return extraction == 'done'


def _generate(job: AiQuizJob) -> None:
    job.status = AiQuizJob.Status.GENERATING
    job.save(update_fields=['status', 'updated_at'])
    raw = tc_client.generate_test_json(
        document_id=job.tc_document_id, standard=job.standard, title=job.title or job.topic,
        count=job.question_count,
    )
    try:
        preview = test_creator_import.parse_test_creator_json(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise tc_client.TestCreatorError(f"Xizmat javobini o'qib bo'lmadi: {exc}", permanent=True) from exc
    if not preview['questions']:
        raise tc_client.TestCreatorError(
            "Material asosida birorta ham savol yaratilmadi. Boshqa (to'liqroq) material bilan urinib ko'ring.",
            permanent=True,
        )
    with transaction.atomic():
        quiz = services.save_imported_quiz(
            teacher=job.teacher, preview=preview, topic=job.topic, course=job.course,
            subject=job.subject, title=job.title or preview.get('title', ''),
        )
        job.quiz = quiz
        job.warnings = preview.get('warnings', [])
        job.status = AiQuizJob.Status.DONE
        job.error = ''
        job.save(update_fields=['quiz', 'warnings', 'status', 'error', 'updated_at'])
    _release_source(job)
    _notify(job, ok=True)


def _read(stored, name: str, limit: int) -> str:
    stored.open('rb')
    try:
        return material_text.extract_text(stored.read(), name, max_chars=limit)
    finally:
        stored.close()


def _run_engine(job: AiQuizJob) -> None:
    """Imtihon qoidalari bo'yicha butun testni tuzadi (reja -> bo'limlar -> qoralama test).
    Tayyor bo'limlar `job.plan` da saqlanadi: xato bo'lsa keyingi urinish qolgan joyidan davom etadi."""
    job.status = AiQuizJob.Status.GENERATING
    job.save(update_fields=['status', 'updated_at'])

    material = _read(job.source_file, job.source_name, settings.AI_EXAM_MATERIAL_CHARS)
    rules = job.rules_text
    if job.rules_file:
        rules = _read(job.rules_file, job.rules_name, settings.AI_EXAM_RULES_CHARS) + '\n\n' + rules

    state = job.plan if isinstance(job.plan, dict) else {}
    plan = state.get('plan')
    if not plan:
        plan = ai_exam.plan_exam(rules, target_total=job.question_count, topic=job.topic)
        state = {'plan': plan, 'sections': {}}
        job.plan = state
        job.save(update_fields=['plan', 'updated_at'])
    sections = state.setdefault('sections', {})

    avoid = []
    for index in range(len(plan['sections'])):
        key = str(index)
        if key not in sections:
            sections[key] = ai_exam.generate_section(plan, index, material, avoid_topics=avoid)
            job.plan = state
            job.save(update_fields=['plan', 'updated_at'])
        done = sections[key]
        avoid.append(done['title'] or done['passage'][:80])

    groups, questions, summary = ai_exam.assemble(plan, [sections[str(i)] for i in range(len(plan['sections']))])
    if not questions:
        raise tc_client.TestCreatorError(
            "Material va qoidalar asosida birorta ham yaroqli savol chiqmadi. Boshqa (to'liqroq) material bilan "
            "urinib ko'ring.", permanent=True,
        )
    with transaction.atomic():
        quiz = services.create_quiz(
            teacher=job.teacher, topic=job.topic, course=job.course, subject=job.subject,
            title=job.title or plan.get('exam_name', ''), questions=questions, groups=groups,
            status=Quiz.Status.DRAFT,
        )
        job.quiz = quiz
        job.summary = summary[:300]
        job.status = AiQuizJob.Status.DONE
        job.error = ''
        job.save(update_fields=['quiz', 'summary', 'status', 'error', 'updated_at'])
    _release_source(job)
    _notify(job, ok=True)


def _advance(job: AiQuizJob) -> None:
    if not job.standard:
        _run_engine(job)
        return
    if job.status == AiQuizJob.Status.QUEUED:
        _start(job)
    if job.status == AiQuizJob.Status.PROCESSING and _check_processing(job):
        _generate(job)
    elif job.status == AiQuizJob.Status.GENERATING:
        _generate(job)  # cron yarim yo'lda to'xtagan bo'lsa — qaytadan


def _expired_reason(job: AiQuizJob, now, give_up) -> str:
    """Ish juda uzoq tursa (xizmat so'rovga javob bermasa ham) — sababli xato bilan yopiladi.
    Aks holda qotib qolgan ish ro'yxatda abadiy "aylanib" turardi."""
    if job.status == AiQuizJob.Status.PROCESSING and job.updated_at < now - PROCESSING_MAX:
        return ("Material tahlili tugamadi (xizmat javob bermadi yoki qayta ishga tushgan). "
                "Qayta urinib ko'ring.")
    if job.created_at < give_up:
        return f"Vaqt tugadi: ish {settings.TEST_CREATOR_GIVE_UP_MINUTES} daqiqada tugamadi. Qayta urinib ko'ring."
    return ''


def sync_jobs() -> dict:
    """Faol ishlarni bir qadam oldinga suradi. Qaytaradi: {'done': n, 'failed': n, 'waiting': n}."""
    result = {'done': 0, 'failed': 0, 'waiting': 0}
    engine_ok, bank_ok = llm.enabled(), tc_client.enabled()
    now = timezone.now()
    give_up = now - timedelta(minutes=settings.TEST_CREATOR_GIVE_UP_MINUTES)
    jobs = list(
        AiQuizJob.objects.filter(status__in=AiQuizJob.ACTIVE_STATUSES)
        .select_related('teacher', 'course').order_by('created_at')[:_BATCH]
    )
    for job in jobs:
        reason = _expired_reason(job, now, give_up)
        if reason:
            logger.warning('AI test ishi muddati tugadi (%s): %s', job.pk, reason)
            _fail(job, reason)
            result['failed'] += 1
            continue
        if (job.standard and not bank_ok) or (not job.standard and not engine_ok):
            result['waiting'] += 1  # tegishli xizmat sozlanmagan
            continue
        if (job.status == AiQuizJob.Status.GENERATING and job.attempts
                and job.updated_at > timezone.now() - GENERATE_RETRY_PAUSE):
            result['waiting'] += 1  # oxirgi muvaffaqiyatsiz urinishdan keyin pauza
            continue
        try:
            _advance(job)
        except tc_client.TestCreatorError as exc:
            if job.status == AiQuizJob.Status.GENERATING and not exc.permanent:
                job.attempts += 1
                job.save(update_fields=['attempts', 'updated_at'])
            if exc.permanent or job.created_at < give_up:
                logger.warning('AI test ishi xato (%s): %s', job.pk, exc)
                _fail(job, str(exc) if exc.permanent else f"Vaqt tugadi: {exc}")
            elif job.attempts >= MAX_GENERATE_ATTEMPTS:
                logger.warning("AI test ishi %s urinishdan keyin to'xtatildi (%s): %s", job.attempts, job.pk, exc)
                _fail(job, f'{GENERATE_FAILED_MESSAGE} ({str(exc)[:200]})')
            else:
                logger.info('AI test ishi vaqtincha kutmoqda (%s): %s', job.pk, exc)
        except Exception as exc:  # noqa: BLE001 — bitta ish butun siklni to'xtatmasin
            logger.exception('AI test ishi kutilmagan xato (%s)', job.pk)
            _fail(job, f'Kutilmagan xato: {exc}')
        job.refresh_from_db()
        key = 'done' if job.status == AiQuizJob.Status.DONE else 'failed' if job.status == AiQuizJob.Status.FAILED else 'waiting'
        result[key] += 1
    return result
