"""Darslar va davomat ro'yxati filtrlari (ota-ona kabineti: farzand va sana oralig'i bo'yicha)."""
import re
from datetime import datetime, time

import django_filters
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts import consent
from apps.accounts.models import User

from .models import Attendance, Enrollment, Lesson


def parse_bound(value, *, end: bool):
    """ISO sana-vaqt yoki faqat sana (`2026-11-02`): sana bo'lsa quyi chegara — kun boshi, yuqori chegara — kun oxiri (mahalliy vaqt)."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):  # faqat sana (Django parse_datetime uni yarim tun deb olardi — shuning uchun avval)
        try:
            day = parse_date(value)
        except ValueError:
            day = None
        if day is None:
            raise ValidationError({'detail': _("Sana YYYY-MM-DD yoki ISO sana-vaqt ko'rinishida bo'lishi kerak.")})
        return timezone.make_aware(datetime.combine(day, time.max if end else time.min))
    try:
        moment = parse_datetime(value)
    except ValueError:
        moment = None
    if moment is None:
        raise ValidationError({'detail': _("Sana YYYY-MM-DD yoki ISO sana-vaqt ko'rinishida bo'lishi kerak.")})
    return timezone.make_aware(moment) if timezone.is_naive(moment) else moment


class BoundFilter(django_filters.CharFilter):
    def __init__(self, *args, lookup, end, **kwargs):
        super().__init__(*args, **kwargs)
        self._lookup, self._end = lookup, end

    def filter(self, qs, value):
        bound = parse_bound(value, end=self._end)
        return qs.filter(**{f'{self.field_name}__{self._lookup}': bound}) if bound else qs


def allowed_student(user: User, student_id) -> None:
    """`?student=` — ota-ona faqat TASDIQLANGAN farzandi, o'quvchi faqat o'zi uchun; o'qituvchi/admin uchun cheklov yo'q
    (ularning ro'yxati allaqachon o'z kurslari bilan cheklangan)."""
    if user.role == User.Role.PARENT:
        consent.approved_child(user, student_id)
    elif user.role == User.Role.STUDENT and str(user.pk) != str(student_id):
        raise PermissionDenied(_("Faqat o'zingizning ma'lumotingiz."))


class LessonFilter(django_filters.FilterSet):
    """`?course=&status=` (avvalgidek) + `?student=<uuid>` (shu o'quvchi qatnashadigan kurslar darslari) +
    `?starts_at__gte=` / `?starts_at__lte=` (sana yoki ISO sana-vaqt)."""

    student = django_filters.UUIDFilter(method='filter_student')
    starts_at__gte = BoundFilter(field_name='starts_at', lookup='gte', end=False)
    starts_at__lte = BoundFilter(field_name='starts_at', lookup='lte', end=True)

    class Meta:
        model = Lesson
        fields = ['course', 'status']

    def filter_student(self, queryset, name, value):
        allowed_student(self.request.user, value)
        return queryset.filter(course__enrollments__student_id=value, course__enrollments__status=Enrollment.Status.APPROVED)


class AttendanceFilter(django_filters.FilterSet):
    """`?lesson=&student=` (avvalgidek) + `?course=<uuid>` + `?from=` / `?to=` (dars boshlanish sanasi bo'yicha; sana yoki ISO)."""

    course = django_filters.UUIDFilter(field_name='lesson__course_id')
    date_from = BoundFilter(field_name='lesson__starts_at', lookup='gte', end=False)
    date_to = BoundFilter(field_name='lesson__starts_at', lookup='lte', end=True)

    class Meta:
        model = Attendance
        fields = ['lesson', 'student']

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:  # `from`/`to` Python kalit so'zi, shuning uchun so'rov parametrini ichki nomga ko'chiramiz
            data = data.copy()
            for alias, real in (('from', 'date_from'), ('to', 'date_to')):
                if alias in data and real not in data:
                    data[real] = data[alias]
        super().__init__(data, *args, **kwargs)
