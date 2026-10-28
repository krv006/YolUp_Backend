"""Uy vazifasi service layer — vazifa berish, topshirish, o'qituvchi baholashi.

O'quvchi fayl yuklaydi -> topshiriq darhol `pending_review` holatida o'qituvchiga
tushadi -> o'qituvchi ballni o'zi qo'yib tasdiqlaydi (`review_submission`) -> shundan
keyin natija o'quvchiga ochiladi. (AI/Gemini tekshiruv olib tashlangan.)
"""
import json
import logging
import math
import re
import time
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson

from apps.quizzes import llm

from . import ai_client, ai_grader, rules
from .models import Assignment, AssignmentFocusEvent, Submission, SubmissionFile

logger = logging.getLogger('apps')


class ServiceUnavailable(APIException):
    status_code = 503
    default_code = 'service_unavailable'
    default_detail = _('Xizmat vaqtincha mavjud emas.')

# Suiiste'moldan himoya (fayl yuklash/xotira): soatiga topshirish chegarasi
MAX_SUBMITS_PER_ASSIGNMENT_HOUR = 5
MAX_SUBMITS_PER_HOUR = 20

# Ichki AI baholash (OpenAI): bitta cron siklida ko'pi bilan shuncha topshiriq / shuncha soniya
ENGINE_PER_RUN = 8
ENGINE_TIME_BUDGET = 75
ENGINE_MAX_ATTEMPTS = 3
AI_FAILED_NOTE = "AI baholay olmadi — o'zingiz baholang."


# Vazifa fayli (o'qituvchi biriktiradi) — faqat yuklab olinadi
ATTACHMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.webp'}

# Rich editor HTML'iga ruxsat etilgan teglar — XSS'dan himoya
_ALLOWED_TAGS = {
    'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'strike',
    'h2', 'h3', 'ul', 'ol', 'li', 'blockquote', 'div', 'span', 'sub', 'sup',
}


def sanitize_html(html: str) -> str:
    """O'qituvchi yozgan HTML'ni tozalaydi. nh3 (Rust ammonia) bo'lsa u bilan,
    bo'lmasa konservativ regex fallback (skript/atributlar olib tashlanadi)."""
    html = (html or '').strip()
    if not html:
        return ''
    try:
        import nh3
        return nh3.clean(html, tags=_ALLOWED_TAGS, attributes={})
    except ImportError:
        # Fallback: teg atributlarini butunlay olib tashlaymiz va faqat
        # ruxsat etilgan teglarni qoldiramiz
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)

        def _tag(m):
            closing, name = m.group(1), m.group(2).lower()
            if name in _ALLOWED_TAGS:
                return f'<{closing}{name}>'
            return ''
        return re.sub(r'<\s*(/?)\s*([a-zA-Z0-9]+)[^>]*>', _tag, html)


# ── yordamchilar ────────────────────────────────────────────────────────────
def _get_course(course_id) -> Course:
    try:
        return Course.objects.get(pk=course_id)
    except (Course.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Kurs topilmadi.'))


def _get_assignment(assignment_id) -> Assignment:
    try:
        return Assignment.objects.select_related('course', 'lesson').get(pk=assignment_id)
    except (Assignment.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Vazifa topilmadi.'))


def _get_submission(submission_id) -> Submission:
    try:
        return Submission.objects.select_related(
            'assignment__course', 'student',
        ).get(pk=submission_id)
    except (Submission.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Topshiriq topilmadi.'))


def _is_enrolled(user: User, course: Course) -> bool:
    return Enrollment.objects.filter(
        course=course, student=user, status=Enrollment.Status.APPROVED,
    ).exists()


def _is_parent_of(parent: User, student: User) -> bool:
    return ParentChildLink.objects.filter(
        parent=parent, student=student, status=ParentChildLink.Status.APPROVED,
    ).exists()


def _ensure_visible(user: User, a: Assignment) -> None:
    """Qoralama vazifa faqat o'z o'qituvchisiga ko'rinadi; boshqalar uchun u yo'q."""
    if a.status == Assignment.Status.DRAFT and a.course.teacher_id != user.id:
        raise NotFound(_('Topshiriq topilmadi.'))


def _bool(value, default=None):
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _clean_status(value) -> str:
    value = str(value or Assignment.Status.ACTIVE).strip().lower()
    if value == 'published':  # ikkinchi frontend hujjatidagi nom
        value = Assignment.Status.ACTIVE
    if value not in Assignment.Status.values:
        raise ValidationError({'status': _("draft yoki active (published) bo'lishi kerak.")})
    return value


def _clean_grading(grading, max_score):
    """Baholash turi va maksimal ball: five -> 5, none -> 0, hundred -> 1..1000 (standart 100)."""
    grading = str(grading or Assignment.Grading.FIVE).strip().lower()
    if grading not in Assignment.Grading.values:
        raise ValidationError({'grading': _("five, hundred yoki none bo'lishi kerak.")})
    if grading == Assignment.Grading.FIVE:
        return grading, 5
    if grading == Assignment.Grading.NONE:
        return grading, 0
    try:
        top = int(max_score) if max_score not in (None, '') else 100
    except (TypeError, ValueError):
        raise ValidationError({'max_score': _("Son bo'lishi kerak.")}) from None
    if not 1 <= top <= 1000:
        raise ValidationError({'max_score': _('1 dan 1000 gacha.')})
    return grading, top


def _publish(assignment: Assignment) -> None:
    """Vazifa e'lon qilinadi: o'quvchilarga bildirishnoma va (yoqilgan bo'lsa) chatga vazifa kartasi."""
    assignment.published_at = timezone.now()
    assignment.save(update_fields=['published_at'])
    _notify_new_assignment(assignment)
    if assignment.announce_in_chat:
        from apps.chat.services import post_assignment_card

        post_assignment_card(assignment)  # kurs chatida vazifa kartasi


def _can_view_course(user: User, course: Course) -> bool:
    if course.teacher_id == user.id or _is_enrolled(user, course):
        return True
    # Ota-ona: bolasi shu kursga yozilgan bo'lsa ko'radi
    child_ids = ParentChildLink.objects.filter(
        parent=user, status=ParentChildLink.Status.APPROVED,
    ).values_list('student_id', flat=True)
    return Enrollment.objects.filter(
        course=course, student_id__in=child_ids, status=Enrollment.Status.APPROVED,
    ).exists()


def _file_size(field) -> int | None:
    """Fayl hajmi baytda; fayl yo'q yoki diskda topilmasa None."""
    if not field:
        return None
    try:
        return field.size
    except (OSError, ValueError):
        return None


def _assignment_dict(a: Assignment) -> dict:
    return {
        'status': a.status,
        'published': a.status == Assignment.Status.ACTIVE,
        'announce_in_chat': a.announce_in_chat,
        'allow_late': a.allow_late,
        'ai_check': a.ai_check,
        'grading': a.grading,
        'max_score': a.max_score,
        'id': str(a.id),
        'course_id': str(a.course_id),
        'course_title': a.course.title,
        'subject': a.course.subject,
        'title': a.title,
        'description': a.description,
        'body': a.body,
        'attachment_name': a.attachment_name,
        'attachment_size': _file_size(a.attachment),
        'has_attachment': bool(a.attachment),
        'due_at': a.due_at,
        'skill_key': a.skill_key,
        'lesson_id': str(a.lesson_id) if a.lesson_id else None,
        'lesson_title': (a.lesson.title or a.course.title) if a.lesson_id else None,
        'lesson_starts_at': a.lesson.starts_at if a.lesson_id else None,
        'created_at': a.created_at,
    }


def _submission_files(s: Submission) -> list:
    """Barcha fayllar (asosiysi birinchi): `[{name, size, mime, index}]` — yuklab olish: `.../submissions/<id>/file/?index=<index>`."""
    import mimetypes

    files = [{'name': s.original_name, 'size': _file_size(s.file), 'mime': mimetypes.guess_type(s.original_name)[0] or '', 'index': 0}]
    for i, extra in enumerate(s.extra_files.all(), start=1):
        files.append({'name': extra.original_name, 'size': extra.size, 'mime': mimetypes.guess_type(extra.original_name)[0] or '', 'index': i})
    return files


def _submission_dict(s: Submission, include_result: bool = True, is_teacher: bool = False, for_parent: bool = False) -> dict:
    due = s.assignment.due_at
    # O'qituvchi tasdiqlamaguncha (PENDING_REVIEW) AI'ning taklif qilgan
    # ball/bahosi o'quvchi/ota-onaga ko'rsatilmaydi — faqat o'qituvchiga.
    # AI ishlayotgan paytda (CHECKING) o'quvchi uchun ham "o'qituvchi kutilmoqda" ko'rinadi.
    waiting = s.status in (Submission.Status.PENDING_REVIEW, Submission.Status.CHECKING)
    # Ota-onaga natija faqat o'qituvchi "ota-onaga ko'rsatish"ni o'chirmagan bo'lsa ko'rinadi
    hide_result = (waiting and not is_teacher) or (for_parent and not s.share_with_parent)
    shown_status = (
        Submission.Status.PENDING_REVIEW if (s.status == Submission.Status.CHECKING and not is_teacher) else s.status
    )
    data = {
        'id': str(s.id),
        'assignment_id': str(s.assignment_id),
        'student_id': str(s.student_id),
        'student_name': f'{s.student.first_name} {s.student.last_name}'.strip() or s.student.username,
        'file_name': s.original_name,
        'files': _submission_files(s),
        'comment': s.comment,
        'status': shown_status,
        'overall_score': None if hide_result else s.overall_score,
        'grade': '' if hide_result else s.grade,
        'grade_value': None if hide_result else s.grade_value,
        'grading': s.assignment.grading,
        'max_score': s.assignment.max_score,
        'share_with_parent': s.share_with_parent,
        'teacher_comment': '' if hide_result else s.teacher_comment,
        'resubmit_comment': s.resubmit_comment if s.status == Submission.Status.RESUBMIT_REQUESTED else '',
        'error': s.error,
        'is_late': bool(due and s.created_at and s.created_at > due),
        'created_at': s.created_at,
        'checked_at': s.checked_at,
    }
    if include_result:
        data['result'] = None if hide_result else s.result
    if is_teacher:
        data['reviewed_at'] = s.reviewed_at
        data['reviewed_by'] = s.reviewed_by.username if s.reviewed_by_id else None
        data['ai_overall_score'] = s.ai_overall_score
        data['ai_grade'] = s.ai_grade
        if include_result:
            data['ai_result'] = s.ai_result
            data['focus'] = focus_summary(assignment_id=s.assignment_id, student=s.student)
    return data


# ── vazifa (Assignment) ─────────────────────────────────────────────────────
def _parse_due(due_at):
    """datetime-local ('2026-08-05T14:30') yoki ISO satrni aware datetime'ga."""
    if not due_at:
        return None
    if isinstance(due_at, str):
        parsed = parse_datetime(due_at)
        if parsed is None:
            raise ValidationError({'due_at': _("Muddat formati noto'g'ri.")})
        due_at = parsed
    if timezone.is_naive(due_at):
        due_at = timezone.make_aware(due_at)
    return due_at


def _resolve_lesson(*, course: Course, lesson_id) -> Lesson | None:
    """Vazifa bog'lanadigan dars — faqat shu kursning TUGAGAN darsi bo'lishi kerak."""
    if not lesson_id:
        return None
    try:
        lesson = Lesson.objects.get(pk=lesson_id, course=course)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    if lesson.status != Lesson.Status.FINISHED:
        raise ValidationError({'lesson_id': _("Faqat tugagan darsga vazifa bog'lash mumkin.")})
    return lesson


def create_assignment(*, teacher: User, course_id, title: str, description: str = '',
                      body: str = '', due_at=None, skill_key: str = '', lesson_id=None,
                      extra_instructions: str = '', attachment=None, status='active', announce_in_chat=True,
                      allow_late=True, grading='five', max_score=None, ai_check=None) -> dict:
    course = _get_course(course_id)
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi vazifa bera oladi."))
    if not (title or '').strip():
        raise ValidationError({'title': _('Vazifa nomi majburiy.')})
    skill_key = (skill_key or '').strip().lower()
    if skill_key and skill_key not in rules.SKILL_KEYS:
        raise ValidationError({
                'skill_key': _("Noto'g'ri ko'nikma: %(skills)s") % {'skills': sorted(rules.SKILL_KEYS)},
            })
    lesson = _resolve_lesson(course=course, lesson_id=lesson_id)
    status = _clean_status(status)
    grading, top = _clean_grading(grading, max_score)

    attachment_name = ''
    if attachment is not None:
        ext = Path(attachment.name or '').suffix.lower()
        if ext not in ATTACHMENT_EXTENSIONS:
            raise ValidationError({'attachment': _("'%(ext)s' qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
                'ext': ext, 'allowed': ', '.join(sorted(ATTACHMENT_EXTENSIONS)),
            }})
        if attachment.size > rules.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError({
                'attachment': _('Fayl %(max_mb)s MB dan katta.') % {'max_mb': rules.MAX_FILE_SIZE_MB},
            })
        attachment_name = (attachment.name or 'vazifa')[:255]

    assignment = Assignment.objects.create(
        course=course,
        lesson=lesson,
        title=title.strip(),
        description=(description or '').strip(),
        body=sanitize_html(body),
        attachment=attachment,
        attachment_name=attachment_name,
        due_at=_parse_due(due_at),
        skill_key=skill_key,
        extra_instructions=(extra_instructions or '').strip(),
        status=status,
        announce_in_chat=_bool(announce_in_chat, True),
        allow_late=_bool(allow_late, True),
        ai_check=_bool(ai_check, True),
        grading=grading,
        max_score=top,
    )
    if status == Assignment.Status.ACTIVE:
        _publish(assignment)
    return _assignment_dict(assignment)


def _enrolled_students(course: Course):
    return User.objects.filter(
        enrollments__course=course, enrollments__status=Enrollment.Status.APPROVED,
    )


def _notify_new_assignment(assignment: Assignment) -> None:
    """Vazifa berilgan zahoti kursga yozilgan hamma o'quvchiga bildirishnoma."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    description = f'«{assignment.course.title}»: yangi uy vazifasi — «{assignment.title}».'
    for student in _enrolled_students(assignment.course):
        send_notification(
            sender=assignment.course.teacher, description=description,
            target_type=Notification.Target.USER, user_id=student.id,
            link_type='assignment', link_id=str(assignment.id),
        )


def send_deadline_reminders(*, now=None) -> dict:
    """Deadline yaqinlashganda hali topshirmagan o'quvchilarga eslatma.

    Davriy chaqirish uchun mo'ljallangan (management command + tashqi cron —
    loyihada Celery yo'q). Ikki nuqta, ikkalasi ham FAQAT BIR MARTA
    yuboriladi (reminder_*_sent_at bilan belgilanadi):
      - "yarim vaqt" — vazifa berilgan (created_at) va due_at orasidagi
        oraliqning yarmi o'tganda
      - "1 soat qoldi" — due_at'dan 1 soat oldin
    Faqat hali Submission topshirmagan o'quvchilarga yuboriladi.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    now = now or timezone.now()
    sent = {'halfway': 0, '1h': 0}

    from django.db.models import Q

    assignments = (
        Assignment.objects.filter(due_at__isnull=False, due_at__gt=now, status=Assignment.Status.ACTIVE)
        .filter(Q(reminder_halfway_sent_at__isnull=True) | Q(reminder_1h_sent_at__isnull=True))
        .select_related('course', 'course__teacher')
    )
    for a in assignments:
        if a.due_at <= a.created_at:
            continue  # noto'g'ri/darhol muddat — hisoblash mantiqsiz, o'tkazib yuboriladi
        submitted_ids = set(
            Submission.objects.filter(assignment=a).values_list('student_id', flat=True)
        )
        pending = [s for s in _enrolled_students(a.course) if s.id not in submitted_ids]
        if not pending:
            continue

        halfway_at = a.created_at + (a.due_at - a.created_at) / 2
        if a.reminder_halfway_sent_at is None and now >= halfway_at:
            description = f'«{a.course.title}»: «{a.title}» topshirish muddatining yarmi o\'tdi.'
            for student in pending:
                send_notification(
                    sender=a.course.teacher, description=description,
                    target_type=Notification.Target.USER, user_id=student.id,
                    link_type='assignment', link_id=str(a.id),
                )
            a.reminder_halfway_sent_at = now
            a.save(update_fields=['reminder_halfway_sent_at'])
            sent['halfway'] += len(pending)

        if a.reminder_1h_sent_at is None and now >= a.due_at - timedelta(hours=1):
            description = f'«{a.course.title}»: «{a.title}» topshirish muddatiga 1 soat qoldi!'
            for student in pending:
                send_notification(
                    sender=a.course.teacher, description=description,
                    target_type=Notification.Target.USER, user_id=student.id,
                    link_type='assignment', link_id=str(a.id),
                )
            a.reminder_1h_sent_at = now
            a.save(update_fields=['reminder_1h_sent_at'])
            sent['1h'] += len(pending)

    return sent


def delete_assignment(*, teacher: User, assignment_id) -> None:
    a = _get_assignment(assignment_id)
    if a.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi vazifani o'chira oladi."))
    a.delete()


_UNSET = object()  # "maydon umuman yuborilmadi" — bo'sh qiymatdan (o'chirish) farqlash uchun


def update_assignment(
    *, teacher: User, assignment_id, title=_UNSET, description=_UNSET, body=_UNSET,
    due_at=_UNSET, skill_key=_UNSET, lesson_id=_UNSET, extra_instructions=_UNSET,
    attachment=_UNSET, status=_UNSET, announce_in_chat=_UNSET, allow_late=_UNSET, grading=_UNSET, max_score=_UNSET,
    ai_check=_UNSET,
) -> dict:
    """Vazifani qisman yangilaydi (PATCH) — faqat yuborilgan maydonlar
    o'zgaradi, `create_assignment` bilan bir xil validatsiya."""
    a = _get_assignment(assignment_id)
    if a.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi vazifani tahrirlashi mumkin."))

    fields = []
    if title is not _UNSET:
        if not (title or '').strip():
            raise ValidationError({'title': _('Vazifa nomi majburiy.')})
        a.title = title.strip()
        fields.append('title')
    if description is not _UNSET:
        a.description = (description or '').strip()
        fields.append('description')
    if body is not _UNSET:
        a.body = sanitize_html(body)
        fields.append('body')
    if due_at is not _UNSET:
        a.due_at = _parse_due(due_at)
        fields.append('due_at')
    if skill_key is not _UNSET:
        skill_key = (skill_key or '').strip().lower()
        if skill_key and skill_key not in rules.SKILL_KEYS:
            raise ValidationError({
                'skill_key': _("Noto'g'ri ko'nikma: %(skills)s") % {'skills': sorted(rules.SKILL_KEYS)},
            })
        a.skill_key = skill_key
        fields.append('skill_key')
    if lesson_id is not _UNSET:
        a.lesson = _resolve_lesson(course=a.course, lesson_id=lesson_id)
        fields.append('lesson')
    if extra_instructions is not _UNSET:
        a.extra_instructions = (extra_instructions or '').strip()
        fields.append('extra_instructions')
    if attachment is not _UNSET and attachment is not None:
        ext = Path(attachment.name or '').suffix.lower()
        if ext not in ATTACHMENT_EXTENSIONS:
            raise ValidationError({'attachment': _("'%(ext)s' qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
                'ext': ext, 'allowed': ', '.join(sorted(ATTACHMENT_EXTENSIONS)),
            }})
        if attachment.size > rules.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError({
                'attachment': _('Fayl %(max_mb)s MB dan katta.') % {'max_mb': rules.MAX_FILE_SIZE_MB},
            })
        a.attachment = attachment
        a.attachment_name = (attachment.name or 'vazifa')[:255]
        fields += ['attachment', 'attachment_name']

    if announce_in_chat is not _UNSET:
        a.announce_in_chat = _bool(announce_in_chat, True)
        fields.append('announce_in_chat')
    if allow_late is not _UNSET:
        a.allow_late = _bool(allow_late, True)
        fields.append('allow_late')
    if ai_check is not _UNSET:
        a.ai_check = _bool(ai_check, True)
        fields.append('ai_check')
    if grading is not _UNSET or max_score is not _UNSET:
        new_grading, top = _clean_grading(a.grading if grading is _UNSET else grading, a.max_score if max_score is _UNSET else max_score)
        if (new_grading, top) != (a.grading, a.max_score):
            if a.submissions.filter(status=Submission.Status.DONE).exists():
                raise ValidationError({'grading': _("Baholangan topshiriqlar bor — baholash turini o'zgartirib bo'lmaydi.")})
            a.grading, a.max_score = new_grading, top
            fields += ['grading', 'max_score']
    publish_now = False
    if status is not _UNSET:
        new_status = _clean_status(status)
        if new_status != a.status:
            if new_status == Assignment.Status.DRAFT:
                raise ValidationError({'status': _("E'lon qilingan vazifani qoralamaga qaytarib bo'lmaydi.")})
            a.status = new_status
            fields.append('status')
            publish_now = True

    if fields:
        a.save(update_fields=fields)
    if publish_now:
        _publish(a)  # qoralama e'lon qilindi: bildirishnoma va chat kartasi endi tushadi
    return _assignment_dict(a)


def assignment_file(*, user: User, assignment_id) -> tuple:
    a = _get_assignment(assignment_id)
    if not _can_view_course(user, a.course):
        raise PermissionDenied(_("Bu faylni ko'rish huquqingiz yo'q."))
    _ensure_visible(user, a)
    if not a.attachment:
        raise NotFound(_("Bu vazifada biriktirilgan fayl yo'q."))
    return a.attachment.path, a.attachment_name or 'vazifa'


def list_assignments(*, user: User, course_id, status=None) -> list:
    course = _get_course(course_id)
    if not _can_view_course(user, course):
        raise PermissionDenied(_("Bu kurs vazifalarini ko'rish huquqingiz yo'q."))
    result = []
    queryset = course.assignments.select_related('lesson').all()
    if course.teacher_id != user.id:
        queryset = queryset.filter(status=Assignment.Status.ACTIVE)  # qoralamalar faqat o'qituvchiga
    elif status in ('draft', 'active', 'published'):
        queryset = queryset.filter(status=_clean_status(status))
    for a in queryset:
        item = _assignment_dict(a)
        if course.teacher_id == user.id:
            item['submissions_count'] = a.submissions.count()
        else:
            # O'quvchi (yoki ota-ona — bolasining) oxirgi topshirig'i holati
            student_ids = [user.id]
            if user.role == 'parent':
                student_ids = list(ParentChildLink.objects.filter(
                    parent=user, status=ParentChildLink.Status.APPROVED,
                ).values_list('student_id', flat=True))
            last = a.submissions.filter(student_id__in=student_ids).first()
            item['my_submission'] = (
                _submission_dict(last, include_result=False, for_parent=user.role == 'parent') if last else None
            )
        result.append(item)
    return result


def get_assignment(*, user: User, assignment_id) -> dict:
    a = _get_assignment(assignment_id)
    if not _can_view_course(user, a.course):
        raise PermissionDenied(_("Bu vazifani ko'rish huquqingiz yo'q."))
    _ensure_visible(user, a)
    data = _assignment_dict(a)
    if a.course.teacher_id == user.id:
        data['ai_group_summary'] = _stored_summary(a)
        subs = list(a.submissions.select_related('student', 'assignment'))
        data['submissions'] = [
            _submission_dict(s, include_result=False, is_teacher=True) for s in subs
        ]
        # Statistika: nechta o'quvchidan nechtasi topshirdi, o'rtacha ball
        scores = [s.overall_score for s in subs if s.overall_score is not None]
        data['stats'] = {
            'students_count': Enrollment.objects.filter(
                course=a.course, status=Enrollment.Status.APPROVED,
            ).count(),
            'submitted_count': len({s.student_id for s in subs}),
            'avg_score': round(sum(scores) / len(scores), 1) if scores else None,
        }
    else:
        student_ids = [user.id]
        if user.role == 'parent':
            student_ids = list(ParentChildLink.objects.filter(
                parent=user, status=ParentChildLink.Status.APPROVED,
            ).values_list('student_id', flat=True))
        data['submissions'] = [
            _submission_dict(s, include_result=False, for_parent=user.role == 'parent')
            for s in a.submissions.filter(student_id__in=student_ids).select_related('student')
        ]
    return data


# ── topshirish va o'qituvchi baholashi ──────────────────────────────────────────────
MAX_SUBMISSION_FILES = 5


def submit(*, student: User, assignment_id, upload, extra_uploads=(), comment: str = '') -> dict:
    a = _get_assignment(assignment_id)
    if not _is_enrolled(student, a.course):
        raise PermissionDenied(_("Bu kursga yozilmagansiz — vazifa topshira olmaysiz."))
    _ensure_visible(student, a)
    if a.due_at and not a.allow_late and timezone.now() > a.due_at:
        raise ValidationError({'detail': _("Topshirish muddati tugagan — bu vazifaga endi topshirib bo'lmaydi.")})
    if upload is None:
        raise ValidationError({'file': _('Fayl majburiy.')})
    extra_uploads = list(extra_uploads or [])
    if 1 + len(extra_uploads) > MAX_SUBMISSION_FILES:
        raise ValidationError({'files': _("Bir topshiriqda ko'pi bilan %(n)s ta fayl.") % {'n': MAX_SUBMISSION_FILES}})

    for item in (upload, *extra_uploads):
        ext = Path(item.name or '').suffix.lower()
        if ext not in rules.ALLOWED_EXTENSIONS:
            raise ValidationError({'file': _("'%(ext)s' qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
                'ext': ext, 'allowed': ', '.join(sorted(rules.ALLOWED_EXTENSIONS)),
            }})
        if ext in rules.AUDIO_EXTENSIONS and a.skill_key != 'speaking':
            raise ValidationError({'file': _("Audio faqat Speaking vazifalari uchun.")})
        if item.size > rules.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError({'file': _('Fayl %(size).1f MB; chegara %(max_mb)s MB.') % {
                'size': item.size / 1024 / 1024, 'max_mb': rules.MAX_FILE_SIZE_MB,
            }})

    hour_ago = timezone.now() - timedelta(hours=1)
    recent = Submission.objects.filter(student=student, created_at__gte=hour_ago)
    if recent.filter(assignment=a).count() >= MAX_SUBMITS_PER_ASSIGNMENT_HOUR:
        raise ValidationError({'file': _(
            "Bu vazifaga soatiga %(n)s martadan ko'p topshirib bo'lmaydi. Birozdan keyin urinib ko'ring."
        ) % {'n': MAX_SUBMITS_PER_ASSIGNMENT_HOUR}})
    if recent.count() >= MAX_SUBMITS_PER_HOUR:
        raise ValidationError({'file': _(
            "Soatiga %(n)s tadan ko'p fayl topshirib bo'lmaydi. Birozdan keyin urinib ko'ring."
        ) % {'n': MAX_SUBMITS_PER_HOUR}})

    submission = Submission.objects.create(
        assignment=a,
        student=student,
        file=upload,
        original_name=(upload.name or 'homework')[:255],
        comment=(comment or '').strip()[:2000],
        status=Submission.Status.PENDING_REVIEW,
    )
    for order, extra in enumerate(extra_uploads, start=1):
        SubmissionFile.objects.create(
            submission=submission, file=extra, original_name=(extra.name or 'file')[:255], size=extra.size, order=order,
        )
    if not a.ai_check or not _start_ai_check(submission):
        # AI sozlanmagan yoki ishlamayapti — o'qituvchi to'g'ridan-to'g'ri baholaydi
        _notify_new_submission(submission)
    return _submission_dict(submission)


def _ai_mode() -> str:
    """`external` — tashqi AI-home-checker (HOMEWORK_AI_URL sozlangan bo'lsa), `engine` — ichki OpenAI
    baholash (OPENAI_API_KEY bor bo'lsa), bo'sh — AI yo'q: o'qituvchi qo'lda baholaydi."""
    if ai_client.enabled():
        return 'external'
    return 'engine' if ai_grader.enabled() else ''


def _start_ai_check(submission: Submission) -> bool:
    """AI tekshiruvni boshlaydi (tashqi xizmat yoki ichki OpenAI). Muvaffaqiyatli bo'lsa topshiriq
    `checking` holatiga o'tadi va natijani `sync_ai_results` (cron) olib keladi.
    AI yo'q yoki xizmat ishlamasa — False qaytaradi, topshiriq o'qituvchiga qo'lda baholashga tushadi."""
    mode = _ai_mode()
    if not mode:
        return False
    if mode == 'engine':  # so'rov ichida AI chaqirilmaydi: cron fonda baholaydi
        Submission.objects.filter(pk=submission.pk).update(
            status=Submission.Status.CHECKING, ai_external_id=ai_grader.ENGINE_ID, error='',
            check_attempts=F('check_attempts') + 1, updated_at=timezone.now(),
        )
        submission.refresh_from_db()
        return True
    attempt = submission.check_attempts
    try:
        external_id = ai_client.submit(submission, attempt=attempt)
    except ai_client.AIServiceError as exc:
        logger.warning('Uy vazifasi AI xizmatiga yuborilmadi (%s): %s', submission.id, exc)
        return False
    Submission.objects.filter(pk=submission.pk).update(
        status=Submission.Status.CHECKING, ai_external_id=external_id, error='',
        check_attempts=F('check_attempts') + 1,
    )
    submission.refresh_from_db()
    return True


def _student_label(student: User) -> str:
    return f'{student.first_name} {student.last_name}'.strip() or student.username


def _notify_new_submission(submission: Submission) -> None:
    """O'qituvchiga "yangi topshiriq — baholash kerak" deb xabar beradi.
    Bildirishnoma xatosi topshirishga ta'sir qilmasligi kerak."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    assignment = submission.assignment
    try:
        send_notification(
            sender=submission.student,
            description=(
                f'«{assignment.course.title}»: {_student_label(submission.student)} vazifani topshirdi '
                f'— «{assignment.title}». Baholashingiz kerak.'
            ),
            target_type=Notification.Target.USER, user_id=assignment.course.teacher_id,
            link_type='submission', link_id=str(submission.id), kind='homework_pending_review',
        )
    except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
        logger.warning('homework_pending_review bildirishnomasi yuborilmadi', exc_info=True)


def _notify_reviewed(submission: Submission, teacher: User, updated: bool) -> None:
    """O'qituvchi natijani tasdiqlagach (yoki tuzatgach) o'quvchiga xabar beradi."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    assignment = submission.assignment
    verb = 'yangilandi' if updated else 'tayyor'
    try:
        send_notification(
            sender=teacher,
            description=f'«{assignment.course.title}»: «{assignment.title}» vazifasi natijasi {verb}.',
            target_type=Notification.Target.USER, user_id=submission.student_id,
            link_type='submission', link_id=str(submission.id), kind='homework_reviewed',
        )
    except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
        logger.warning('homework_reviewed bildirishnomasi yuborilmadi', exc_info=True)


def get_submission(*, user: User, submission_id) -> dict:
    s = _get_submission(submission_id)
    is_teacher = s.assignment.course.teacher_id == user.id
    allowed = is_teacher or s.student_id == user.id or _is_parent_of(user, s.student)
    if not allowed:
        raise PermissionDenied(_("Bu topshiriqni ko'rish huquqingiz yo'q."))
    return _submission_dict(s, is_teacher=is_teacher, for_parent=not is_teacher and s.student_id != user.id)


def submission_file(*, user: User, submission_id, index=None) -> tuple:
    s = _get_submission(submission_id)
    allowed = (
        s.student_id == user.id
        or s.assignment.course.teacher_id == user.id
        or _is_parent_of(user, s.student)
    )
    if not allowed:
        raise PermissionDenied(_("Bu faylni ko'rish huquqingiz yo'q."))
    if index not in (None, '', '0', 0):
        try:
            extra = s.extra_files.all()[int(index) - 1]
        except (ValueError, IndexError):
            raise NotFound(_('Fayl topilmadi.'))
        return extra.file.path, extra.original_name
    return s.file.path, s.original_name


def recheck(*, user: User, submission_id) -> dict:
    """AI'ni qayta ishga tushiradi (faqat AI xizmati sozlangan bo'lsa). Sozlanmagan bo'lsa
    — tushunarli xato: topshiriqni qo'lda baholash kerak."""
    s = _get_submission(submission_id)
    if s.assignment.course.teacher_id != user.id:
        raise PermissionDenied(_("Qayta tekshirishni faqat kurs o'qituvchisi boshlaydi."))
    if not _ai_mode():
        raise ValidationError({'detail': _(
            "AI tekshiruv o'chirilgan. Topshiriqni o'zingiz baholang (ball qo'yib tasdiqlang)."
        )})
    if s.status == Submission.Status.CHECKING:
        raise ValidationError({'detail': _("AI tekshiruv allaqachon davom etmoqda.")})
    if s.status == Submission.Status.DONE:
        raise ValidationError({'detail': _("Tasdiqlangan natijani qayta tekshirib bo'lmaydi.")})
    if not _start_ai_check(s):
        raise ValidationError({'detail': _("AI xizmati hozir javob bermayapti. Birozdan keyin urinib ko'ring.")})
    return _submission_dict(s, is_teacher=True)


# ── AI natijasini olib kelish (cron: `manage.py sync_homework_ai`) ──────────
def _apply_ai_result(s: Submission, payload: dict) -> None:
    result = payload.get('ai_result') or payload.get('final_result') or {}
    score = result.get('overall_score')
    try:
        value = float(score) if score is not None else None
    except (TypeError, ValueError):
        value = None
    if value is not None and not (math.isfinite(value) and 0 <= value <= 100):
        value = None
    grade = rules.grade_label(value) if value is not None else str(result.get('grade') or '')[:40]
    s.ai_result, s.ai_overall_score, s.ai_grade = result, value, grade
    # Yakuniy maydonlar dastlab AI'nikidan nusxa — o'qituvchi tasdiqlaganda ustidan yozadi
    s.result, s.overall_score, s.grade = result, value, grade
    s.error = ''


def _release_for_manual(s: Submission, reason: str = '') -> None:
    s.status = Submission.Status.PENDING_REVIEW
    s.error = reason[:2000]
    s.checked_at = timezone.now()
    s.save()
    _notify_new_submission(s)


def _grade_in_app(s: Submission, now) -> str:
    """Ichki OpenAI baholash: 'done' | 'failed' (o'qituvchiga qo'lda) | 'waiting' (keyingi siklda qayta uriniladi)."""
    try:
        result = ai_grader.grade(s)
    except ai_grader.GraderError as exc:
        _release_for_manual(s, str(exc))
        return 'failed'
    except llm.LLMError as exc:
        logger.warning('Uy vazifasi AI bilan baholanmadi (%s): %s', s.id, exc)
        if exc.permanent or s.check_attempts >= ENGINE_MAX_ATTEMPTS:
            _release_for_manual(s, AI_FAILED_NOTE)
            return 'failed'
        # vaqtincha xato: keyingi siklda qayta; navbat adolatli aylansin deb vaqtni yangilaymiz
        Submission.objects.filter(pk=s.pk).update(check_attempts=F('check_attempts') + 1, updated_at=now)
        return 'waiting'
    except Exception:  # noqa: BLE001 — kutilmagan xato topshiriqni abadiy kutdirmasin
        logger.exception('Uy vazifasi AI baholashida kutilmagan xato (%s)', s.id)
        _release_for_manual(s, AI_FAILED_NOTE)
        return 'failed'
    _apply_ai_result(s, {'ai_result': result})
    s.status = Submission.Status.PENDING_REVIEW
    s.checked_at = now
    s.save()
    _notify_new_submission(s)
    return 'done'


def sync_ai_results(*, now=None, batch: int = 50) -> dict:
    """`checking` topshiriqlar uchun AI xizmatidan natijani oladi. Tayyor bo'lsa — o'qituvchi
    baholashiga (ball AI taklifi bilan to'ldirilgan), xato yoki uzoq kutilsa — qo'lda baholashga."""
    now = now or timezone.now()
    give_up = timedelta(minutes=getattr(settings, 'HOMEWORK_AI_GIVE_UP_MINUTES', 15))
    done = failed = waiting = 0
    engine_started, engine_runs = time.monotonic(), 0
    pending = Submission.objects.filter(status=Submission.Status.CHECKING).select_related(
        'assignment__course__teacher', 'student').order_by('updated_at')[:batch]
    for s in pending:
        too_old = now - s.updated_at > give_up
        if s.ai_external_id == ai_grader.ENGINE_ID:
            if not ai_grader.enabled() or too_old:
                _release_for_manual(s, AI_FAILED_NOTE)
                failed += 1
            elif engine_runs >= ENGINE_PER_RUN or time.monotonic() - engine_started > ENGINE_TIME_BUDGET:
                waiting += 1  # navbat keyingi sikl uchun (cron'ni uzoq band qilmaymiz)
            else:
                engine_runs += 1
                outcome = _grade_in_app(s, now)
                done, failed, waiting = done + (outcome == 'done'), failed + (outcome == 'failed'), waiting + (outcome == 'waiting')
            continue
        if not s.ai_external_id or not ai_client.enabled():
            _release_for_manual(s, "AI xizmati sozlanmagan — o'zingiz baholang.")
            failed += 1
            continue
        try:
            payload = ai_client.fetch(s.ai_external_id)
        except ai_client.AIServiceError as exc:
            logger.warning('AI natijasini olib bo\'lmadi (%s): %s', s.id, exc)
            if too_old:
                _release_for_manual(s, "AI xizmati javob bermadi — o'zingiz baholang.")
                failed += 1
            else:
                waiting += 1
            continue
        status = payload.get('status')
        if status in ('pending_review', 'approved') and (payload.get('ai_result') or payload.get('final_result')):
            _apply_ai_result(s, payload)
            s.status = Submission.Status.PENDING_REVIEW
            s.checked_at = now
            s.save()
            _notify_new_submission(s)
            done += 1
        elif status in ('grading_failed', 'not_found'):
            _release_for_manual(s, "AI baholay olmadi — o'zingiz baholang.")
            failed += 1
        elif too_old:
            _release_for_manual(s, "AI kutilgandan uzoq ishladi — o'zingiz baholang.")
            failed += 1
        else:
            waiting += 1
    return {'done': done, 'failed': failed, 'waiting': waiting}


# ── o'qituvchi baholashi/tasdiqlashi ────────────────────────────────────────
def review_submission(*, teacher: User, submission_id, overall_score=None,
                      grade: str = '', result=None, grade_value=None, share_with_parent=None,
                      teacher_comment=None) -> dict:
    """O'qituvchi topshiriqni baholaydi. Vazifa baholash turiga qarab:

      - `five`: `grade_value` 1-5 (yoki eski `overall_score` 0-100); `overall_score` = baho*20.
      - `hundred`: `grade_value` 0..max_score (yoki eski `overall_score` 0-100); `overall_score` foizga keltiriladi.
      - `none`: baho yo'q — faqat izoh (`result`) bilan tasdiqlanadi.

    `overall_score` har doim 0-100 (hisobotlar uchun), xom baho — `grade_value`. `share_with_parent=false` bo'lsa ota-ona
    natijani ko'rmaydi. Tasdiqlangan (DONE) natijani ham tuzatish mumkin — o'quvchiga "natija yangilandi" deb xabar boradi."""
    s = _get_submission(submission_id)
    if s.assignment.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi baholaydi."))
    if s.status not in (Submission.Status.PENDING_REVIEW, Submission.Status.DONE):
        raise ValidationError(
            _("Faqat baholashni kutayotgan yoki baholangan topshiriqni baholash mumkin.")
        )
    a = s.assignment

    def number(value, field):
        try:
            number_value = float(value)
        except (TypeError, ValueError):
            raise ValidationError({field: _("Raqam bo'lishi kerak.")}) from None
        if not math.isfinite(number_value):
            raise ValidationError({field: _("Raqam bo'lishi kerak.")})
        return number_value

    if a.grading == Assignment.Grading.NONE:
        s.overall_score, s.grade_value, grade = None, None, ''
        s.grade = ''
    else:
        if grade_value is not None and grade_value != '':
            raw = number(grade_value, 'grade')
            if a.grading == Assignment.Grading.FIVE:
                if not 1 <= raw <= 5:
                    raise ValidationError({'grade': _("Baho 1 dan 5 gacha bo'lishi kerak.")})
                s.overall_score = raw * 20
            else:
                if not 0 <= raw <= a.max_score:
                    raise ValidationError({'grade': _("Baho 0 dan %(max)s gacha bo'lishi kerak.") % {'max': a.max_score}})
                s.overall_score = raw * 100 / a.max_score
            s.grade_value = raw
        elif overall_score is not None:
            percent = number(overall_score, 'overall_score')
            if not 0 <= percent <= 100:
                raise ValidationError({'overall_score': _("Ball 0 dan 100 gacha bo'lishi kerak.")})
            s.overall_score = percent
            s.grade_value = round(percent / 20, 1) if a.grading == Assignment.Grading.FIVE else round(percent * a.max_score / 100, 1)
        if s.overall_score is None:
            raise ValidationError({'overall_score': _("Baho kiritilishi shart.")})
    if result is not None and not isinstance(result, dict):
        raise ValidationError({'result': _("Natija obyekt (JSON) shaklida bo'lishi kerak.")})
    was_done = s.status == Submission.Status.DONE
    if a.grading != Assignment.Grading.NONE:
        if grade:
            s.grade = grade.strip()[:40]
        elif grade_value not in (None, '') or overall_score is not None or not s.grade:
            s.grade = rules.grade_label(s.overall_score)
    if result is not None:
        s.result = result
        if teacher_comment is None and isinstance(result.get('teacher_comment'), str):
            teacher_comment = result['teacher_comment']  # eski usul: izoh `result` ichida kelgan
    if teacher_comment is not None:
        if not isinstance(teacher_comment, str):
            raise ValidationError({'teacher_comment': _("Matn bo'lishi kerak.")})
        s.teacher_comment = teacher_comment.strip()[:2000]
    if share_with_parent is not None:
        s.share_with_parent = bool(_bool(share_with_parent, True))
    s.status = Submission.Status.DONE
    s.reviewed_by = teacher
    s.reviewed_at = timezone.now()
    s.save()
    _notify_reviewed(s, teacher, updated=was_done)
    return _submission_dict(s, is_teacher=True)


@transaction.atomic
def request_resubmit(*, teacher: User, submission_id, comment: str = '') -> dict:
    """O'qituvchi topshiriqni qayta topshirishga qaytaradi: holat `resubmit_requested`, o'quvchiga bildirishnoma boradi
    va u yangi fayl yuklay oladi (eskisi tarix sifatida qoladi)."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    s = _get_submission(submission_id)
    if s.assignment.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi qayta topshirishni so'rashi mumkin."))
    if s.status in (Submission.Status.CHECKING, Submission.Status.RESUBMIT_REQUESTED):
        raise ValidationError({'detail': _("Bu topshiriq hozir qayta topshirishga qaytarib bo'lmaydigan holatda.")})
    s.status = Submission.Status.RESUBMIT_REQUESTED
    s.resubmit_comment = (comment or '').strip()[:2000]
    s.resubmit_requested_at = timezone.now()
    s.save(update_fields=['status', 'resubmit_comment', 'resubmit_requested_at', 'updated_at'])
    note = f' Izoh: {s.resubmit_comment}' if s.resubmit_comment else ''
    try:
        send_notification(
            sender=teacher, target_type=Notification.Target.USER, user_id=s.student_id, kind='homework_resubmit',
            description=f'«{s.assignment.course.title}»: «{s.assignment.title}» vazifasini qayta topshirishingiz so\'raldi.{note}',
            link_type='assignment', link_id=str(s.assignment_id),
        )
    except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
        logger.warning('homework_resubmit bildirishnomasi yuborilmadi', exc_info=True)
    return _submission_dict(s, is_teacher=True)


REMIND_COOLDOWN = 10 * 60


def remind_missing(*, teacher: User, assignment_id, message=None, notify_parents=False) -> dict:
    """Hali topshirmagan (tasdiqlangan) o'quvchilarga eslatma: `{notified}` (+ `parents_notified`, agar `notify_parents` so'ralgan bo'lsa). `message` — o'qituvchi
    tahrirlagan matn (bo'sh bo'lsa standart matn); `notify_parents` — ota-onalarga ham. Bir vazifaga 10 daqiqada bir marta."""
    from django.core.cache import cache

    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    a = _get_assignment(assignment_id)
    if a.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi eslatma yuboradi."))
    if a.status != Assignment.Status.ACTIVE:
        raise ValidationError({'detail': _("Qoralama vazifaga eslatma yuborib bo'lmaydi.")})
    if message is not None and not isinstance(message, str):
        raise ValidationError({'message': _("Matn bo'lishi kerak.")})
    custom = (message or '').strip()
    if len(custom) > 500:
        raise ValidationError({'message': _('Xabar 500 belgidan oshmasligi kerak.')})
    if not cache.add(f'hw:remind:{a.id}', 1, REMIND_COOLDOWN):
        raise ValidationError({'detail': _("Eslatma yaqinda yuborilgan. Birozdan keyin qayta urinib ko'ring."), 'retry_after': REMIND_COOLDOWN})
    submitted = set(Submission.objects.filter(assignment=a).values_list('student_id', flat=True))
    description = custom or f'«{a.course.title}»: «{a.title}» vazifasini hali topshirmadingiz.'
    missing = [student for student in _enrolled_students(a.course) if student.id not in submitted]
    for student in missing:
        send_notification(
            sender=teacher, description=description, target_type=Notification.Target.USER, user_id=student.id,
            kind='homework_reminder', link_type='assignment', link_id=str(a.id),
        )
    result = {'notified': len(missing)}
    if _bool(notify_parents, False):
        parents_notified = 0
        if missing:
            sent = send_notification(
                sender=teacher, description=description, target_type=Notification.Target.PARENTS_OF,
                user_ids=[student.id for student in missing],
                kind='homework_reminder', link_type='assignment', link_id=str(a.id),
            )
            parents_notified = sent.recipients.count()
        result['parents_notified'] = parents_notified  # faqat `notify_parents` so'ralganda
    return result


AI_SUMMARY_TTL = 10 * 60
AI_SUMMARY_SYSTEM = (
    "Sen o'qituvchi yordamchisisan. Berilgan uy vazifasi natijalari (o'quvchilar anonim) asosida guruh bo'yicha qisqa "
    "xulosa va keyingi darsga tavsiyalar yoz. Faqat JSON qaytar: "
    '{"summary": "2-4 gapli umumiy xulosa", "topics": ["qiynalgan mavzular"], '
    '"recommendations": ["aniq tavsiyalar"]}. '
    "O'zbek tilida yoz. Natijalarda yo'q narsani o'ylab topma."
)


def ai_summary(*, teacher: User, assignment_id) -> dict:
    """Guruhga AI xulosa va tavsiya: `{summary, topics, recommendations}`. AI kaliti yo'q bo'lsa 503; topshiriq yo'q bo'lsa 400."""
    from django.core.cache import cache

    a = _get_assignment(assignment_id)
    if a.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi guruh xulosasini ko'radi."))
    if not llm.enabled():
        raise ServiceUnavailable(_("AI xizmati ulanmagan (OPENAI_API_KEY)."))
    latest: dict = {}
    for submission in a.submissions.order_by('-created_at'):
        latest.setdefault(submission.student_id, submission)  # har o'quvchining oxirgisi
    if not latest:
        raise ValidationError({'detail': _("Hali birorta topshiriq yo'q.")})
    digest = []
    for index, submission in enumerate(list(latest.values())[:40], 1):
        digest.append({
            "o'quvchi": index, 'holat': submission.status, 'ball': submission.overall_score, 'baho': submission.grade,
            'on_vaqt': not (a.due_at and submission.created_at > a.due_at),
            'natija': json.dumps(submission.result or {}, ensure_ascii=False)[:500],
        })
    key = f'hw:aisum:{a.id}:{len(latest)}:{max(s.updated_at for s in latest.values()).timestamp()}'
    cached = cache.get(key)
    if cached:
        return _with_summary_meta(a, cached)
    user_prompt = (
        f'Vazifa: «{a.title}» ({a.course.title}). {a.description}\n'
        f'Natijalar ({len(digest)} ta topshiriq):\n{json.dumps(digest, ensure_ascii=False)[:12000]}'
    )
    try:
        data = llm.chat_json(AI_SUMMARY_SYSTEM, user_prompt)
    except llm.LLMError as exc:
        raise ServiceUnavailable(str(exc)) from None

    def texts(value):
        return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []

    result = {
        'summary': str(data.get('summary') or '').strip(), 'topics': texts(data.get('topics')),
        'recommendations': texts(data.get('recommendations')), 'submissions_count': len(latest),
    }
    cache.set(key, result, AI_SUMMARY_TTL)
    return _with_summary_meta(a, result)


def _with_summary_meta(a: Assignment, result: dict) -> dict:
    """Tayyor xulosani vazifada saqlaydi va `text` + `created_at` bilan qaytaradi (`GET /assignments/{id}/` ham shuni beradi)."""
    if a.ai_summary != result or not a.ai_summary_at:
        a.ai_summary, a.ai_summary_at = result, timezone.now()
        a.save(update_fields=['ai_summary', 'ai_summary_at', 'updated_at'])
    return {**result, 'text': result['summary'], 'created_at': a.ai_summary_at}


def _stored_summary(a: Assignment):
    if not a.ai_summary:
        return None
    return {**a.ai_summary, 'text': a.ai_summary.get('summary', ''), 'created_at': a.ai_summary_at}


def ai_stats(*, teacher: User, period: str = 'today') -> dict:
    """Vazifalar sahifasidagi AI banneri: davr ichida AI tekshirgan topshiriqlar (`checked`) va hozir o'qituvchi
    tasdig'ini kutayotganlar (`pending_confirm`). `period`: today | week | month."""
    from datetime import timedelta

    if period not in ('today', 'week', 'month'):
        raise ValidationError({'period': _("today, week yoki month bo'lishi kerak.")})
    now = timezone.localtime()
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'week':
        since -= timedelta(days=6)
    elif period == 'month':
        since -= timedelta(days=29)
    mine = Submission.objects.filter(assignment__course__teacher=teacher)
    return {
        'period': period,
        'checked': mine.filter(checked_at__gte=since).count(),
        'pending_confirm': mine.filter(status=Submission.Status.PENDING_REVIEW).count(),
    }


# ── vazifa sahifasida vaqt kuzatuvi ─────────────────────────────────────────
def record_focus(*, student: User, assignment_id, kind: str) -> dict:
    a = _get_assignment(assignment_id)
    if not _is_enrolled(student, a.course):
        raise PermissionDenied(_("Bu kursga yozilmagansiz."))
    _ensure_visible(student, a)
    if kind not in AssignmentFocusEvent.Kind.values:
        raise ValidationError({'kind': _('exit yoki return.')})
    AssignmentFocusEvent.objects.create(assignment=a, student=student, kind=kind)
    return {'ok': True}


def focus_summary(*, assignment_id, student: User) -> dict:
    """Vazifa sahifasida chiqib-kirish tahlili — jami/eng uzun tashqarida
    o'tgan vaqt va sahifada o'tgan taxminiy vaqt (lessons.focus_summary uslubida,
    lekin dars davomati chegarasi yo'qligi sabab ochiq chiqish `hozir`gacha hisoblanadi)."""
    events = list(
        AssignmentFocusEvent.objects.filter(assignment_id=assignment_id, student=student)
        .order_by('created_at').values_list('kind', 'created_at')
    )
    if not events:
        return {
            'exits': 0, 'away_seconds': 0, 'longest_seconds': 0,
            'on_page_seconds': 0, 'total_seconds': 0, 'timeline': [],
        }
    timeline = []
    total_away = 0.0
    longest = 0.0
    open_exit = None
    for kind, at in events:
        if kind == AssignmentFocusEvent.Kind.EXIT and open_exit is None:
            open_exit = at
        elif kind == AssignmentFocusEvent.Kind.RETURN and open_exit is not None:
            seconds = max(0.0, (at - open_exit).total_seconds())
            timeline.append({'left_at': open_exit, 'returned_at': at, 'seconds': round(seconds)})
            total_away += seconds
            longest = max(longest, seconds)
            open_exit = None
    now = timezone.now()
    last_seen = events[-1][1]
    if open_exit is not None:
        seconds = max(0.0, (now - open_exit).total_seconds())
        timeline.append({'left_at': open_exit, 'returned_at': None, 'seconds': round(seconds)})
        total_away += seconds
        longest = max(longest, seconds)
        last_seen = now
    total_seconds = max(0.0, (last_seen - events[0][1]).total_seconds())
    return {
        'exits': sum(1 for k, _ in events if k == AssignmentFocusEvent.Kind.EXIT),
        'away_seconds': round(total_away),
        'longest_seconds': round(longest),
        'on_page_seconds': round(max(0.0, total_seconds - total_away)),
        'total_seconds': round(total_seconds),
        'timeline': timeline,
    }


def get_progress_report(*, user: User, student_id=None) -> dict:
    """Uspevaemost hisoboti: fan bo'yicha uy vazifasi bajarilish foizi va
    o'rtacha ball + umumiy (barcha fanlar bo'yicha) yagona ko'rsatkich.

    `student_id` berilmasa — chaqiruvchining o'zi (STUDENT bo'lishi shart).
    Berilsa — faqat APPROVED bog'langan ota-ona ko'ra oladi.

    O'rtacha ballga faqat status=DONE (o'qituvchi tasdiqlagan) topshiriqlar
    kiradi — AI'ning tasdiqlanmagan taklifi (pending_review) hisobga
    olinmaydi, xuddi o'quvchiga alohida submission ko'rinishida ham
    yashirilgani kabi. Bir vazifaga bir necha marta topshirilgan bo'lsa
    (qayta yuklash) — faqat ENG SO'NGGISI hisoblanadi.
    """
    if student_id:
        if not ParentChildLink.objects.filter(
            parent=user, student_id=student_id, status=ParentChildLink.Status.APPROVED,
        ).exists():
            raise PermissionDenied(_("Bu o'quvchining hisobotini ko'rish huquqingiz yo'q."))
        try:
            student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
        except (User.DoesNotExist, ValueError, TypeError):
            raise NotFound(_("O'quvchi topilmadi."))
    else:
        if user.role != User.Role.STUDENT:
            raise ValidationError({'student_id': _('Bu maydon majburiy.')})
        student = user

    courses = Course.objects.filter(
        enrollments__student=student, enrollments__status=Enrollment.Status.APPROVED,
    ).distinct()

    subjects = []
    total_assignments = 0
    total_submitted = 0
    all_scores = []
    for course in courses:
        assignments_count = Assignment.objects.filter(course=course).count()
        submissions = (
            Submission.objects.filter(assignment__course=course, student=student)
            .order_by('assignment_id', '-created_at')
        )
        latest_by_assignment = {}
        for sub in submissions:
            latest_by_assignment.setdefault(sub.assignment_id, sub)
        submitted_count = len(latest_by_assignment)
        done_scores = [
            s.overall_score for s in latest_by_assignment.values()
            if s.status == Submission.Status.DONE and s.overall_score is not None
        ]
        avg_score = round(sum(done_scores) / len(done_scores), 1) if done_scores else None

        subjects.append({
            'course_id': str(course.id), 'course_title': course.title, 'subject': course.subject,
            'assignments_total': assignments_count, 'assignments_submitted': submitted_count,
            'completion_pct': (
                round(submitted_count / assignments_count * 100, 1) if assignments_count else 0.0
            ),
            'avg_score': avg_score,
        })
        total_assignments += assignments_count
        total_submitted += submitted_count
        all_scores.extend(done_scores)

    return {
        'student_id': str(student.id),
        'subjects': subjects,
        'overall': {
            'assignments_total': total_assignments,
            'assignments_submitted': total_submitted,
            'completion_pct': (
                round(total_submitted / total_assignments * 100, 1) if total_assignments else 0.0
            ),
            'avg_score': round(sum(all_scores) / len(all_scores), 1) if all_scores else None,
        },
    }
