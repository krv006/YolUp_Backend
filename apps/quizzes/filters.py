"""Testlar ro'yxati filtrlari: `?course=&lesson=&subject=` (avvalgidek) + `?status=` va `?is_copy=`."""
import django_filters

from .models import Quiz


class QuizFilter(django_filters.FilterSet):
    """`?is_copy=false` — faqat ASL testlar (guruhga nusxalab berilganlari — nusxa — chiqmaydi). "Guruhga berish" ro'yxati
    shuni ishlatsin: o'qituvchining hamma tayyor testi (guruhda turganlari ham) bir marta chiqadi, nusxalar takrorlanmaydi.
    `?status=published|draft` — tayyor (e'lon qilingan) yoki qoralama."""

    is_copy = django_filters.BooleanFilter(method='filter_is_copy')

    class Meta:
        model = Quiz
        fields = ['course', 'lesson', 'subject', 'status']

    def filter_is_copy(self, queryset, name, value):
        return queryset.filter(source_quiz__isnull=not value)
