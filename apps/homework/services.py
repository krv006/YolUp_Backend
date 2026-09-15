"""Uy vazifasi service layer — vazifa berish, topshirish, AI tekshiruv.

Tekshiruv fonda (thread) yuradi: o'quvchi faylni yuklagach darhol javob oladi
(status=checking), frontend polling bilan natijani kutadi. Testlarda
settings.HOMEWORK_CHECK_ASYNC=False qilib sinxron ishlatiladi.
"""
import re
import threading
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson

from . import ai
from .models import Assignment, AssignmentFocusEvent, Submission

# Vazifa fayli (o'qituvchi biriktiradi) — AI'ga bormaydi, faqat yuklab olinadi
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


def _assignment_dict(a: Assignment) -> dict:
    return {
        'id': str(a.id),
        'course_id': str(a.course_id),
        'course_title': a.course.title,
        'subject': a.course.subject,
        'title': a.title,
        'description': a.description,
        'body': a.body,
        'attachment_name': a.attachment_name,
        'has_attachment': bool(a.attachment),
        'due_at': a.due_at,
        'skill_key': a.skill_key,
        'lesson_id': str(a.lesson_id) if a.lesson_id else None,
        'lesson_title': a.course.title if a.lesson_id else None,
        'created_at': a.created_at,
    }


def _submission_dict(s: Submission, include_result: bool = True, is_teacher: bool = False) -> dict:
    due = s.assignment.due_at
    # O'qituvchi tasdiqlamaguncha (PENDING_REVIEW) AI'ning taklif qilgan
    # ball/bahosi o'quvchi/ota-onaga ko'rsatilmaydi — faqat o'qituvchiga.
    hide_result = s.status == Submission.Status.PENDING_REVIEW and not is_teacher
    data = {
        'id': str(s.id),
        'assignment_id': str(s.assignment_id),
        'student_id': str(s.student_id),
        'student_name': f'{s.student.first_name} {s.student.last_name}'.strip() or s.student.username,
        'file_name': s.original_name,
        'status': s.status,
        'overall_score': None if hide_result else s.overall_score,
        'grade': '' if hide_result else s.grade,
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
                      extra_instructions: str = '', attachment=None) -> dict:
    course = _get_course(course_id)
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi vazifa bera oladi."))
    if not (title or '').strip():
        raise ValidationError({'title': _('Vazifa nomi majburiy.')})
    skill_key = (skill_key or '').strip().lower()
    if skill_key and skill_key not in ai.SKILLS:
        raise ValidationError({
                'skill_key': _("Noto'g'ri ko'nikma: %(skills)s") % {'skills': sorted(ai.SKILLS)},
            })
    lesson = _resolve_lesson(course=course, lesson_id=lesson_id)

    attachment_name = ''
    if attachment is not None:
        ext = Path(attachment.name or '').suffix.lower()
        if ext not in ATTACHMENT_EXTENSIONS:
            raise ValidationError({'attachment': _("'%(ext)s' qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
                'ext': ext, 'allowed': ', '.join(sorted(ATTACHMENT_EXTENSIONS)),
            }})
        if attachment.size > ai.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError({
                'attachment': _('Fayl %(max_mb)s MB dan katta.') % {'max_mb': ai.MAX_FILE_SIZE_MB},
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
    )
    _notify_new_assignment(assignment)
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
        Assignment.objects.filter(due_at__isnull=False, due_at__gt=now)
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
    attachment=_UNSET,
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
        if skill_key and skill_key not in ai.SKILLS:
            raise ValidationError({
                'skill_key': _("Noto'g'ri ko'nikma: %(skills)s") % {'skills': sorted(ai.SKILLS)},
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
        if attachment.size > ai.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError({
                'attachment': _('Fayl %(max_mb)s MB dan katta.') % {'max_mb': ai.MAX_FILE_SIZE_MB},
            })
        a.attachment = attachment
        a.attachment_name = (attachment.name or 'vazifa')[:255]
        fields += ['attachment', 'attachment_name']

    if fields:
        a.save(update_fields=fields)
    return _assignment_dict(a)


def assignment_file(*, user: User, assignment_id) -> tuple:
    a = _get_assignment(assignment_id)
    if not _can_view_course(user, a.course):
        raise PermissionDenied(_("Bu faylni ko'rish huquqingiz yo'q."))
    if not a.attachment:
        raise NotFound(_("Bu vazifada biriktirilgan fayl yo'q."))
    return a.attachment.path, a.attachment_name or 'vazifa'


def list_assignments(*, user: User, course_id) -> list:
    course = _get_course(course_id)
    if not _can_view_course(user, course):
        raise PermissionDenied(_("Bu kurs vazifalarini ko'rish huquqingiz yo'q."))
    result = []
    for a in course.assignments.select_related('lesson').all():
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
            item['my_submission'] = _submission_dict(last, include_result=False) if last else None
        result.append(item)
    return result


def get_assignment(*, user: User, assignment_id) -> dict:
    a = _get_assignment(assignment_id)
    if not _can_view_course(user, a.course):
        raise PermissionDenied(_("Bu vazifani ko'rish huquqingiz yo'q."))
    data = _assignment_dict(a)
    if a.course.teacher_id == user.id:
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
            _submission_dict(s, include_result=False)
            for s in a.submissions.filter(student_id__in=student_ids).select_related('student')
        ]
    return data


# ── topshirish va AI tekshiruv ──────────────────────────────────────────────
def submit(*, student: User, assignment_id, upload, feedback_language: str = 'uz') -> dict:
    a = _get_assignment(assignment_id)
    if not _is_enrolled(student, a.course):
        raise PermissionDenied(_("Bu kursga yozilmagansiz — vazifa topshira olmaysiz."))
    if upload is None:
        raise ValidationError({'file': _('Fayl majburiy.')})

    ext = Path(upload.name or '').suffix.lower()
    if ext not in ai.ALLOWED_EXTENSIONS:
        raise ValidationError({'file': _("'%(ext)s' qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
            'ext': ext, 'allowed': ', '.join(sorted(ai.ALLOWED_EXTENSIONS)),
        }})
    if ext in ai.AUDIO_EXTENSIONS and a.skill_key != 'speaking':
        raise ValidationError({'file': _("Audio faqat Speaking vazifalari uchun.")})
    if upload.size > ai.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError({'file': _('Fayl %(size).1f MB; chegara %(max_mb)s MB.') % {
            'size': upload.size / 1024 / 1024, 'max_mb': ai.MAX_FILE_SIZE_MB,
        }})

    submission = Submission.objects.create(
        assignment=a,
        student=student,
        file=upload,
        original_name=(upload.name or 'homework')[:255],
        status=Submission.Status.CHECKING,
        feedback_language=feedback_language,
    )
    _dispatch_check(submission)
    submission.refresh_from_db()
    return _submission_dict(submission)


def run_check(submission_id) -> None:
    """AI tekshiruvni bajaradi va natijani saqlaydi (thread ichida chaqiriladi).

    Natija PENDING_REVIEW holatida to'xtaydi — AI'nikini "yakuniy" deb hisoblab
    o'quvchiga ko'rsatmaymiz, o'qituvchi ko'rib chiqib tasdiqlashi kerak
    (`review_submission`). AI'ning asl natijasi `ai_*` maydonlarda saqlanadi.
    """
    submission = Submission.objects.select_related('assignment__course').get(pk=submission_id)
    a = submission.assignment
    try:
        result = ai.grade_file(
            submission.file.path,
            subject_text=a.course.subject,
            skill_key=a.skill_key,
            extra_instructions=a.extra_instructions,
            feedback_language=submission.feedback_language,
        )
        score = result.get('overall_score')
        overall_score = float(score) if score is not None else None
        # grade yorlig'ini har doim ball shkalasidan olamiz — model gohida
        # boshqacha yozishi mumkin
        grade = ai.grade_label(score) or str(result.get('grade') or '')

        submission.ai_result = result
        submission.ai_overall_score = overall_score
        submission.ai_grade = grade
        # Yakuniy maydonlar dastlab AI'nikidan nusxa — o'qituvchi tasdiqlaguncha
        # shu turadi, tasdiqlashda ustidan yozilishi mumkin.
        submission.result = result
        submission.overall_score = overall_score
        submission.grade = grade
        submission.status = Submission.Status.PENDING_REVIEW
        submission.error = ''
    except Exception as exc:  # AI/tarmoq xatosi — foydalanuvchiga ko'rsatiladi
        submission.status = Submission.Status.ERROR
        submission.error = str(exc)[:2000]
    submission.checked_at = timezone.now()
    submission.save()


def _dispatch_check(submission: Submission) -> None:
    if not getattr(settings, 'HOMEWORK_CHECK_ASYNC', True):
        run_check(submission.id)
        return

    def _target(sub_id):
        try:
            run_check(sub_id)
        finally:
            close_old_connections()

    threading.Thread(target=_target, args=(submission.id,), daemon=True).start()


def get_submission(*, user: User, submission_id) -> dict:
    s = _get_submission(submission_id)
    is_teacher = s.assignment.course.teacher_id == user.id
    allowed = is_teacher or s.student_id == user.id or _is_parent_of(user, s.student)
    if not allowed:
        raise PermissionDenied(_("Bu topshiriqni ko'rish huquqingiz yo'q."))
    return _submission_dict(s, is_teacher=is_teacher)


def submission_file(*, user: User, submission_id) -> tuple:
    s = _get_submission(submission_id)
    allowed = (
        s.student_id == user.id
        or s.assignment.course.teacher_id == user.id
        or _is_parent_of(user, s.student)
    )
    if not allowed:
        raise PermissionDenied(_("Bu faylni ko'rish huquqingiz yo'q."))
    return s.file.path, s.original_name


def recheck(*, user: User, submission_id) -> dict:
    s = _get_submission(submission_id)
    if s.assignment.course.teacher_id != user.id:
        raise PermissionDenied(_("Qayta tekshirishni faqat kurs o'qituvchisi boshlaydi."))
    s.status = Submission.Status.CHECKING
    s.error = ''
    s.save(update_fields=['status', 'error', 'updated_at'])
    _dispatch_check(s)
    s.refresh_from_db()
    return _submission_dict(s, is_teacher=True)


# ── o'qituvchi ko'rib chiqishi/tasdiqlashi ──────────────────────────────────
def review_submission(*, teacher: User, submission_id, overall_score=None,
                      grade: str = '', result=None) -> dict:
    """O'qituvchi AI natijasini ko'rib chiqadi — xohlasa ball/baho/feedbackni
    o'zgartiradi, so'ng tasdiqlaydi. Shundan keyingina o'quvchi natijani ko'radi.
    Faqat AI tekshirib bo'lgan (PENDING_REVIEW) topshiriqqa tegishli."""
    s = _get_submission(submission_id)
    if s.assignment.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi tasdiqlaydi."))
    if s.status != Submission.Status.PENDING_REVIEW:
        raise ValidationError(
            _("Faqat AI tekshirib bo'lgan (ko'rib chiqish kutilayotgan) topshiriqni tasdiqlash mumkin.")
        )
    if overall_score is not None:
        try:
            s.overall_score = float(overall_score)
        except (TypeError, ValueError):
            raise ValidationError({'overall_score': _("Ball raqam bo'lishi kerak.")})
    if grade:
        s.grade = grade.strip()[:40]
    if result is not None:
        s.result = result
    s.status = Submission.Status.DONE
    s.reviewed_by = teacher
    s.reviewed_at = timezone.now()
    s.save()
    return _submission_dict(s, is_teacher=True)


# ── vazifa sahifasida vaqt kuzatuvi ─────────────────────────────────────────
def record_focus(*, student: User, assignment_id, kind: str) -> dict:
    a = _get_assignment(assignment_id)
    if not _is_enrolled(student, a.course):
        raise PermissionDenied(_("Bu kursga yozilmagansiz."))
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
