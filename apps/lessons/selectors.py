"""Lessons selector layer — "kim nimani ko'radi" qoidalari bitta joyda.

Ota-ona faqat TASDIQLANGAN bog'lanishdagi bolasining ma'lumotini ko'radi —
bu rozilik modelining texnik kafolati.
"""
from django.db.models import QuerySet

from apps.accounts.models import ParentChildLink, User

from .models import Attendance, Course, Enrollment, Lesson, LessonRating

_APPROVED = ParentChildLink.Status.APPROVED
_ENROLLED = Enrollment.Status.APPROVED


def courses_for(user: User) -> QuerySet[Course]:
    if user.role == User.Role.TEACHER:
        return Course.objects.filter(teacher=user)
    if user.role == User.Role.STUDENT:
        return Course.objects.filter(enrollments__student=user, enrollments__status=_ENROLLED)
    if user.role == User.Role.PARENT:
        return Course.objects.filter(
            enrollments__status=_ENROLLED,
            enrollments__student__parent_links__parent=user,
            enrollments__student__parent_links__status=_APPROVED,
        ).distinct()
    return Course.objects.all()


def ratings_for_teacher(teacher: User) -> QuerySet[LessonRating]:
    """O'qituvchining BARCHA darslariga qo'yilgan baholar (talaba fikri bilan) —
    eng yangisi birinchi. O'qituvchining o'z profilida ham, admin panelida
    ham ishlatiladi (apps.accounts.views)."""
    return LessonRating.objects.filter(
        lesson__course__teacher=teacher, lesson__is_deleted=False,
    ).select_related('lesson', 'lesson__course', 'student')


def lessons_for(user: User) -> QuerySet[Lesson]:
    qs = Lesson.objects.select_related('course')
    if user.role == User.Role.TEACHER:
        return qs.filter(course__teacher=user)
    if user.role == User.Role.STUDENT:
        return qs.filter(
            course__enrollments__student=user, course__enrollments__status=_ENROLLED,
        )
    if user.role == User.Role.PARENT:
        return qs.filter(
            course__enrollments__status=_ENROLLED,
            course__enrollments__student__parent_links__parent=user,
            course__enrollments__student__parent_links__status=_APPROVED,
        ).distinct()
    return qs


def focus_summary(lesson, student) -> dict:
    """Fokus jurnalidan chiqish-qaytish TAHLILI (EduTech.docx: ota-ona nazorati).

    Har bir `exit` keyingi `return` bilan juftlanadi:
      - jami tashqarida bo'lgan vaqt (sekund)
      - eng uzun yo'qlik (sekund)
      - to'liq taymlayn: qachon chiqdi, qachon qaytdi, qancha turdi
    Qaytmagan chiqish (dars oxirigacha) taymlaynda `returned_at: null` bo'ladi
    va davomiyligi chegara sifatida dars tugashi/`left_at` gacha hisoblanadi.
    """
    events = list(
        lesson.focus_events.filter(student=student).order_by('created_at')
        .values_list('kind', 'created_at')
    )
    timeline = []
    total = 0.0
    longest = 0.0
    open_exit = None
    for kind, at in events:
        if kind == 'exit' and open_exit is None:
            open_exit = at
        elif kind == 'return' and open_exit is not None:
            seconds = max(0.0, (at - open_exit).total_seconds())
            timeline.append({
                'left_at': open_exit, 'returned_at': at, 'seconds': round(seconds),
            })
            total += seconds
            longest = max(longest, seconds)
            open_exit = None
    if open_exit is not None:
        # qaytmadi — davomiyligi darsdan chiqqan/dars tugagan vaqtgacha
        att = lesson.attendances.filter(student=student).first()
        end = (att.left_at if att and att.left_at else None)
        seconds = max(0.0, (end - open_exit).total_seconds()) if end else None
        timeline.append({
            'left_at': open_exit, 'returned_at': None,
            'seconds': round(seconds) if seconds is not None else None,
        })
        if seconds:
            total += seconds
            longest = max(longest, seconds)
    return {
        'exits': sum(1 for k, _ in events if k == 'exit'),
        'away_seconds': round(total),
        'longest_seconds': round(longest),
        'timeline': timeline,
    }


def attendance_for(user: User) -> QuerySet[Attendance]:
    qs = Attendance.objects.select_related('lesson', 'student')
    if user.role == User.Role.TEACHER:
        return qs.filter(lesson__course__teacher=user)
    if user.role == User.Role.STUDENT:
        return qs.filter(student=user)
    if user.role == User.Role.PARENT:
        return qs.filter(
            student__parent_links__parent=user,
            student__parent_links__status=_APPROVED,
        )
    return qs
