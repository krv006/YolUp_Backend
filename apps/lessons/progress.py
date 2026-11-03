"""O'qituvchi uchun o'quvchilar progressi: to'lov, davomat, uy vazifalari, qo'shilgan sana — bitta javobda.

Ta'riflar (o'qituvchi va ota-ona bir xil raqamni ko'rsin — qarang apps/analytics/child.py, attendance_summary.py):
  - davomat % va fokus % — `attendance_summary.course_summary` bilan AYNAN bir xil (shu modul uni qayta ishlatadi).
  - vazifalar = kursdagi FAOL vazifalar, o'quvchi qo'shilgandan keyingilari (muddati yoki yaratilgan sanasi bo'yicha) +
    qo'shilishidan oldin bo'lsa ham topshirganlari. `submitted` — oxirgi topshirig'i bor va "qayta topshiring" so'ralmagan;
    `missed` — muddati o'tgan va topshirilmagan; `average` — tasdiqlangan (DONE) oxirgi topshiriqlar bahosi, 10 ballik.
  - to'lov — o'qituvchi qo'lda belgilaydi (to'lov tizimi yo'q): oy uchun yozuv bor = to'lagan. `unpaid_months` — o'quvchi
    qo'shilgan oydan joriy oygacha to'lov belgisi yo'q oylar soni.
  - qo'shilgan sana = tasdiqlangan yozilish yozuvining yaratilgan vaqti (`joined_at`).
"""
from datetime import date

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.homework.models import Assignment, Submission

from . import attendance_summary
from .models import Attendance, CoursePayment, Enrollment, Lesson

SCALE = 10
MIN_PERIOD = date(2020, 1, 1)
MAX_MONTHS_AHEAD = 12


# ── yordamchilar ───────────────────────────────────────────────────────────

def ensure_teacher(course, user: User) -> None:
    if user.role != User.Role.SUPER_ADMIN and not (user.role == User.Role.TEACHER and course.teacher_id == user.pk):
        raise PermissionDenied(_("Faqat shu kurs o'qituvchisi uchun."))


def _month_floor(day: date) -> date:
    return day.replace(day=1)


def _next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def current_period(now=None) -> date:
    return _month_floor(timezone.localtime(now or timezone.now()).date())


def parse_period(value, now=None) -> date:
    """`YYYY-MM` -> oyning 1-kuni (bo'sh bo'lsa — joriy oy). Noto'g'ri bo'lsa 400."""
    today = current_period(now)
    if not value:
        return today
    try:
        year, month = (int(part) for part in str(value).split('-'))
        period = date(year, month, 1)
    except (ValueError, TypeError):
        raise ValidationError({'month': _("YYYY-MM ko'rinishida bo'lishi kerak.")}) from None
    latest = today
    for _step in range(MAX_MONTHS_AHEAD):
        latest = _next_month(latest)
    if period < MIN_PERIOD or period > latest:
        raise ValidationError({'month': _("Oy ruxsat etilgan oraliqdan tashqarida.")})
    return period


def _months(start: date, stop: date) -> list:
    """start..stop (ikkalasi ham kiradi) oylarning 1-kunlari."""
    result, cursor = [], start
    while cursor <= stop:
        result.append(cursor)
        cursor = _next_month(cursor)
    return result


def _name(user: User) -> str:
    return attendance_summary._name(user)


def _enrollments(course) -> dict:
    """{student_id: Enrollment} — tasdiqlangan yozilganlar."""
    return {
        e.student_id: e for e in Enrollment.objects.filter(course=course, status=Enrollment.Status.APPROVED).select_related('student')
    }


def _payment_view(payment, *, period: date, fee) -> dict:
    return {
        'period': f'{period:%Y-%m}',
        'status': 'paid' if payment else 'unpaid',
        'amount': (payment.amount if payment.amount is not None else fee) if payment else None,
        'paid_at': payment.paid_at if payment else None,
        'note': payment.note if payment else '',
    }


def _payments_by_student(course, student_ids) -> dict:
    """{student_id: {period: CoursePayment}}"""
    result: dict = {}
    for payment in CoursePayment.objects.filter(course=course, student_id__in=list(student_ids)):
        result.setdefault(payment.student_id, {})[payment.period] = payment
    return result


def _unpaid_months(joined: date, paid: dict, today: date) -> int:
    return sum(1 for month in _months(_month_floor(joined), today) if month not in paid)


def _assignments(course) -> list:
    return list(Assignment.objects.filter(course=course, status=Assignment.Status.ACTIVE).order_by('due_at', 'created_at'))


def _latest_submissions(assignments, student_ids) -> dict:
    """{(student_id, assignment_id): ENG SO'NGGI topshiriq} — bitta so'rovda."""
    latest: dict = {}
    qs = Submission.objects.filter(assignment__in=assignments, student_id__in=list(student_ids)).order_by(
        'assignment_id', 'student_id', '-created_at',
    )
    for sub in qs:
        latest.setdefault((sub.student_id, sub.assignment_id), sub)
    return latest


def _relevant(assignment, joined_at, submission) -> bool:
    """O'quvchiga tegishli vazifa: qo'shilgandan keyingi yoki u allaqachon topshirgan."""
    return submission is not None or (assignment.due_at or assignment.created_at) >= joined_at


def _assignment_state(assignment, submission, now) -> str:
    if submission is None:
        return 'missed' if assignment.due_at and assignment.due_at < now else 'not_submitted'
    if submission.status == Submission.Status.RESUBMIT_REQUESTED:
        return 'resubmit'
    if submission.status == Submission.Status.DONE:
        return 'done'
    return 'awaiting_review'  # AI tekshirmoqda / o'qituvchi tasdiqlashi kutilmoqda / xatolik


def _score10(submission):
    if submission is not None and submission.status == Submission.Status.DONE and submission.overall_score is not None:
        return round(submission.overall_score / SCALE, 1)
    return None


def _homework_summary(assignments, student_id, joined_at, latest, now) -> dict:
    total = submitted = done = awaiting = resubmit = missed = 0
    scores = []
    for assignment in assignments:
        submission = latest.get((student_id, assignment.id))
        if not _relevant(assignment, joined_at, submission):
            continue
        total += 1
        state = _assignment_state(assignment, submission, now)
        if state == 'missed':
            missed += 1
        elif state == 'resubmit':
            resubmit += 1
        elif state != 'not_submitted':
            submitted += 1
            if state == 'done':
                done += 1
                scores.append(_score10(submission))
            else:
                awaiting += 1
    scores = [score for score in scores if score is not None]
    return {
        'total': total, 'submitted': submitted, 'checked': done, 'awaiting_review': awaiting, 'resubmit_requested': resubmit,
        'missed': missed, 'completion_percent': round(submitted * 100 / total) if total else None,
        'average': round(sum(scores) / len(scores), 1) if scores else None, 'scale': SCALE,
    }


# ── ochiq funksiyalar ──────────────────────────────────────────────────────

def course_progress(*, course, viewer: User, range_key: str = 'all', period: date | None = None, now=None) -> dict:
    """GET /courses/<id>/progress/?range=all|30d|month&month=YYYY-MM — kursdagi har o'quvchi uchun umumiy progress."""
    ensure_teacher(course, viewer)
    now = now or timezone.now()
    today = current_period(now)
    period = period or today
    enrollments = _enrollments(course)
    students = sorted((e.student for e in enrollments.values()), key=lambda u: _name(u).lower())
    attendance = attendance_summary.course_summary(course=course, viewer=viewer, range_key=range_key, now=now)
    attendance_rows = {row['id']: row for row in attendance['students']}
    # Oxirgi qatnashgan dars (barcha vaqt bo'yicha, bitta so'rovda)
    last_visit: dict = {}
    for record in Attendance.objects.filter(
        lesson__course=course, lesson__is_deleted=False, student_id__in=list(enrollments), joined_at__isnull=False,
    ).order_by('-joined_at').values('student_id', 'joined_at'):
        last_visit.setdefault(record['student_id'], record['joined_at'])

    assignments = _assignments(course)
    latest = _latest_submissions(assignments, enrollments)
    payments = _payments_by_student(course, enrollments)

    rows = []
    for student in students:
        joined_at = enrollments[student.pk].created_at
        paid = payments.get(student.pk, {})
        att = attendance_rows.get(str(student.pk), {})
        rows.append({
            'id': str(student.pk), 'name': _name(student), 'username': student.username,
            'joined_at': joined_at,
            'last_visit_at': last_visit.get(student.pk),
            'attendance': {
                'percent': att.get('attendance_percent'), 'attended': att.get('attended_count', 0),
                'total': attendance['lesson_count'], 'focus_percent': att.get('focus_percent'),
            },
            'homework': _homework_summary(assignments, student.pk, joined_at, latest, now),
            'payment': {
                **_payment_view(paid.get(period), period=period, fee=course.monthly_fee),
                'unpaid_months': _unpaid_months(joined_at.date(), paid, today),
            },
        })
    paid_count = sum(1 for row in rows if row['payment']['status'] == 'paid')
    completions = [row['homework']['completion_percent'] for row in rows if row['homework']['completion_percent'] is not None]
    return {
        'course_id': str(course.pk), 'course_title': course.title, 'monthly_fee': course.monthly_fee,
        'range': range_key, 'month': f'{period:%Y-%m}', 'lesson_count': attendance['lesson_count'],
        'summary': {
            'students': len(rows), 'paid': paid_count, 'unpaid': len(rows) - paid_count,
            'attendance_percent': attendance['attendance_percent'], 'focus_percent': attendance['focus_percent'],
            'homework_completion_percent': round(sum(completions) / len(completions)) if completions else None,
        },
        'students': rows,
    }


def student_progress(*, course, viewer: User, student_id, range_key: str = 'all', now=None) -> dict:
    """GET /courses/<id>/students/<sid>/progress/ — bitta o'quvchi: umumiy ko'rsatkichlar + dars, vazifa va to'lov tarixi."""
    ensure_teacher(course, viewer)
    now = now or timezone.now()
    enrollment = _enrollments(course).get(student_id)
    if enrollment is None:
        raise NotFound(_("O'quvchi bu kursda topilmadi."))
    student, joined_at, today = enrollment.student, enrollment.created_at, current_period(now)

    summary = next(
        row for row in course_progress(course=course, viewer=viewer, range_key=range_key, now=now)['students']
        if row['id'] == str(student.pk)
    )

    attendance = {
        a.lesson_id: a for a in Attendance.objects.filter(lesson__course=course, student=student)
    }
    lessons = []
    for lesson in Lesson.objects.filter(course=course, is_deleted=False, status=Lesson.Status.FINISHED).order_by('-starts_at'):
        record = attendance.get(lesson.pk)
        attended = record is not None and record.joined_at is not None
        lessons.append({
            'lesson_id': str(lesson.pk), 'title': lesson.title or course.title, 'starts_at': lesson.starts_at,
            'attended': attended,
            'joined_at': record.joined_at if attended else None, 'left_at': record.left_at if attended else None,
            'minutes': record.minutes if attended else None,
            'late_reason': record.late_reason if record else '', 'teacher_note': record.teacher_note if record else '',
        })

    assignments = _assignments(course)
    latest = _latest_submissions(assignments, [student.pk])
    homework = []
    for assignment in assignments:
        submission = latest.get((student.pk, assignment.id))
        if not _relevant(assignment, joined_at, submission):
            continue
        homework.append({
            'assignment_id': str(assignment.pk), 'title': assignment.title, 'due_at': assignment.due_at,
            'state': _assignment_state(assignment, submission, now),
            'submitted_at': submission.created_at if submission else None,
            'submission_id': str(submission.pk) if submission else None,
            'score': _score10(submission),
        })
    homework.sort(key=lambda item: item['due_at'] or now, reverse=True)

    paid = _payments_by_student(course, [student.pk]).get(student.pk, {})
    payments = [
        _payment_view(paid.get(month), period=month, fee=course.monthly_fee)
        for month in reversed(_months(_month_floor(joined_at.date()), today))
    ]
    return {**summary, 'course_id': str(course.pk), 'monthly_fee': course.monthly_fee, 'range': range_key,
            'lessons': lessons, 'assignments': homework, 'payments': payments}


def mark_paid(*, course, viewer: User, student_id, period: date, amount=None, note='', request=None) -> dict:
    """PUT /courses/<id>/students/<sid>/payments/<YYYY-MM>/ — oy to'langan deb belgilaydi (qayta chaqirish yangilaydi)."""
    ensure_teacher(course, viewer)
    if student_id not in _enrollments(course):
        raise NotFound(_("O'quvchi bu kursda topilmadi."))
    if amount is not None:
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            raise ValidationError({'amount': _("Summa butun son bo'lishi kerak.")}) from None
        if not 0 <= amount <= 1_000_000_000:
            raise ValidationError({'amount': _("Summa 0 dan 1 000 000 000 gacha bo'lishi kerak.")})
    note = str(note or '').strip()
    if len(note) > 200:
        raise ValidationError({'note': _("Izoh 200 belgidan oshmasligi kerak.")})
    payment, _created = CoursePayment.objects.update_or_create(
        course=course, student_id=student_id, period=period,
        defaults={'amount': amount, 'note': note, 'paid_at': timezone.now(), 'recorded_by': viewer},
    )
    audit.record(action='payment.mark', actor=viewer, target=payment, meta={'period': f'{period:%Y-%m}', 'amount': amount}, request=request)
    return _payment_view(payment, period=period, fee=course.monthly_fee)


def unmark_paid(*, course, viewer: User, student_id, period: date, request=None) -> None:
    """DELETE .../payments/<YYYY-MM>/ — belgini olib tashlaydi (yo'q bo'lsa ham xato emas)."""
    ensure_teacher(course, viewer)
    payment = CoursePayment.objects.filter(course=course, student_id=student_id, period=period).first()
    if payment is not None:
        audit.record(action='payment.unmark', actor=viewer, target=payment, meta={'period': f'{period:%Y-%m}'}, request=request)
        payment.delete()
