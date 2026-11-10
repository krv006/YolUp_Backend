"""To'lov muddati, eslatmalar va to'lamaganlar soni (2026-11-10).

Qoidalar (egasi bilan kelishilgan):
  - O'qituvchi har guruh uchun to'lov kunini (har oyning 1-28 kuni) belgilaydi.
  - Eslatma vaqti: muddatdan 3, 5 va/yoki 7 kun oldin (bir nechtasini birga tanlash mumkin — ochiq savol 2 bo'yicha ruxsat berilgan).
  - Eslatma O'QUVCHIGA ham, ota-onaga ham boradi — faqat shu oy to'lanmagan bo'lsa (`CoursePayment` yo'q).
  - Muddat o'tgan va to'lanmagan bo'lsa holat `overdue`. O'qituvchining ro'yxatlarida `unpaid_count`/`overdue_count` (joriy oy).
To'lov sozlanmagan guruhlar (`monthly_fee` ham, `payment_day` ham yo'q) "to'lamagan" hisoblanmaydi — shovqin bo'lmasin.
"""
import logging
from datetime import date

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import ParentChildLink, User

from .models import Course, CoursePayment, Enrollment, PaymentReminderLog

logger = logging.getLogger('apps')

REMINDER_CHOICES = (3, 5, 7)


def _first_of_month(day: date) -> date:
    return day.replace(day=1)


def _next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def local_today(now=None) -> date:
    return timezone.localtime(now or timezone.now()).date()


def is_overdue(course: Course, period: date, today: date) -> bool:
    """Shu oy uchun to'lanmagan bo'lsa kechikkanmi: o'tgan oy — ha; joriy oy — to'lov kuni o'tib ketgan bo'lsa."""
    if period < _first_of_month(today):
        return True
    if period == _first_of_month(today) and course.payment_day:
        return today.day > course.payment_day
    return False


def unpaid_counts_for_teacher(teacher: User, now=None) -> dict:
    """{course_id: {'unpaid': n, 'overdue': n}} — joriy oy, bitta so'rovda (ro'yxatlar uchun)."""
    today = local_today(now)
    period = _first_of_month(today)
    paid = CoursePayment.objects.filter(course=OuterRef('course_id'), student=OuterRef('student_id'), period=period)
    rows = (
        Enrollment.objects.filter(course__teacher=teacher, status=Enrollment.Status.APPROVED, course__is_deleted=False)
        .filter(Q(course__monthly_fee__isnull=False) | Q(course__payment_day__isnull=False))
        .annotate(paid=Exists(paid)).filter(paid=False)
        .values('course_id', 'course__payment_day').annotate(n=Count('pk'))
    )
    result = {}
    for row in rows:
        day = row['course__payment_day']
        result[row['course_id']] = {'unpaid': row['n'], 'overdue': row['n'] if day and today.day > day else 0}
    return result


def send_reminders(now=None) -> dict:
    """Kunlik vazifa: bugun muddatdan 3/5/7 kun oldin bo'lgan guruhlar uchun to'lamagan o'quvchilar va ularning ota-onalariga xabar.
    Har eslatma bir martadan (`PaymentReminderLog`) — buyruq qancha tez-tez ishlasa ham takrorlanmaydi."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    today = local_today(now)
    sent = {'students': 0, 'parents': 0}
    courses = Course.objects.filter(is_active=True, payment_day__isnull=False).exclude(payment_reminder_days=[]).select_related('teacher')
    for course in courses:
        reminder_days = {int(d) for d in (course.payment_reminder_days or []) if int(d) in REMINDER_CHOICES}
        for month in (_first_of_month(today), _next_month(_first_of_month(today))):
            due = month.replace(day=course.payment_day)
            days_left = (due - today).days
            if days_left not in reminder_days:
                continue
            paid = CoursePayment.objects.filter(course=course, student=OuterRef('student_id'), period=month)
            logged = PaymentReminderLog.objects.filter(course=course, student=OuterRef('student_id'), period=month, days_before=days_left)
            enrollments = (
                Enrollment.objects.filter(course=course, status=Enrollment.Status.APPROVED)
                .annotate(paid=Exists(paid), logged=Exists(logged)).filter(paid=False, logged=False).select_related('student')
            )
            fee = f"{course.monthly_fee:,}".replace(',', ' ') + " so'm" if course.monthly_fee else ''
            for enrollment in enrollments:
                student = enrollment.student
                try:
                    PaymentReminderLog.objects.create(course=course, student=student, period=month, days_before=days_left)
                except Exception:  # noqa: BLE001 — parallel ishga tushgan boshqa nusxa allaqachon yuborgan
                    continue
                data = {'course_id': str(course.id), 'period': f'{month:%Y-%m}', 'due': due.isoformat(), 'days_left': days_left}
                base = {'course': course.title, 'due': f'{due:%d.%m.%Y}', 'days': days_left, 'fee': fee}
                try:
                    send_notification(
                        sender=course.teacher, kind='payment_reminder', link_type='course', link_id=str(course.id), data=data,
                        description=_("«%(course)s» guruhi to'lovi muddati %(due)s (%(days)s kun qoldi). %(fee)s") % base,
                        target_type=Notification.Target.USER, user_id=student.id,
                    )
                    sent['students'] += 1
                    parent_ids = list(ParentChildLink.objects.filter(
                        student=student, status=ParentChildLink.Status.APPROVED,
                    ).values_list('parent_id', flat=True))
                    if parent_ids:
                        send_notification(
                            sender=course.teacher, kind='payment_reminder', link_type='course', link_id=str(course.id),
                            data={**data, 'student_id': str(student.id)},
                            description=_("O'quvchi %(child)s uchun «%(course)s» guruhi to'lovi muddati %(due)s (%(days)s kun qoldi). %(fee)s") % {
                                **base, 'child': student.get_full_name() or student.username,
                            },
                            target_type=Notification.Target.USERS, user_ids=parent_ids,
                        )
                        sent['parents'] += len(parent_ids)
                except Exception:  # noqa: BLE001
                    logger.exception('payment reminder failed for %s/%s', course.id, student.id)
    return sent
