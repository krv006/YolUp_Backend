"""Imtihon (mock test) modellari — IELTS / SAT / Milliy sertifikat / custom.

Oqim:
  - O'qituvchi guruhida imtihon e'lon qiladi: shablonni tanlaydi, har bo'limga
    o'zining (e'lon qilingan) testini biriktiradi, boshlanish sanasi-vaqtini
    belgilaydi.
  - Imtihon SINXRON: hamma uchun bir vaqtda boshlanadi, bo'lim/tanaffus
    chegaralari `starts_at` + bo'limlar davomiyligidan hisoblanadi (server soati
    — brauzerni aldab bo'lmaydi). Kech kirgan o'quvchi joriy bo'limning
    qolgan vaqtini oladi.
  - Qayta topshirish YO'Q (har o'quvchiga bitta ExamAttempt).
"""
from django.conf import settings
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKey,
    JSONField,
    PositiveIntegerField,
    TextChoices,
    TextField,
    UniqueConstraint,
)

from apps.core.models import TimeStampedUUIDModel


class ExamTemplate(TimeStampedUUIDModel):
    """O'qituvchining custom shabloni. Tayyor (IELTS/SAT/Milliy) shablonlar
    DB'da emas — `presets.SYSTEM_TEMPLATES` da."""

    owner = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='exam_templates')
    name = CharField(max_length=120)
    description = TextField(blank=True)
    items = JSONField(default=list)
    scoring = JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Exam(TimeStampedUUIDModel):
    course = ForeignKey('lessons.Course', CASCADE, related_name='exams')
    created_by = ForeignKey(
        settings.AUTH_USER_MODEL, SET_NULL, null=True, blank=True, related_name='created_exams',
    )
    title = CharField(max_length=200)
    # 'ielts' | 'sat' | 'milliy' | 'custom' — faqat ko'rsatish uchun
    template_key = CharField(max_length=20)
    # Shablondan nusxa — keyingi o'zgarishlar bu imtihonga ta'sir qilmaydi
    scoring = JSONField(default=dict)
    starts_at = DateTimeField(db_index=True)
    # starts_at + (vaqtli bo'limlar yig'indisi); yaratishda saqlanadi
    ends_at = DateTimeField(db_index=True)

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return f'{self.title} @ {self.course_id}'


class ExamSection(TimeStampedUUIDModel):
    class Kind(TextChoices):
        SECTION = 'section', "Bo'lim"
        BREAK = 'break', 'Tanaffus'
        OFFLINE = 'offline', "Alohida topshiriladigan qism"

    exam = ForeignKey(Exam, CASCADE, related_name='sections')
    order = PositiveIntegerField(default=0)
    kind = CharField(max_length=10, choices=Kind.choices, default=Kind.SECTION)
    key = CharField(max_length=50)
    group = CharField(max_length=50, blank=True)
    title = CharField(max_length=200)
    minutes = PositiveIntegerField(default=0)
    # Ballni o'qituvchi qo'lda qo'yadi (avtomatik tekshirib bo'lmaydi)
    manual = BooleanField(default=False)
    weight = FloatField(default=1)
    # Test o'chirilsa (yoki hali tanlanmagan offline) bo'lim bo'sh qoladi
    quiz = ForeignKey('quizzes.Quiz', SET_NULL, null=True, blank=True, related_name='exam_sections')

    class Meta:
        ordering = ['order']
        constraints = [
            UniqueConstraint(fields=['exam', 'order'], name='unique_exam_section_order'),
            UniqueConstraint(fields=['exam', 'key'], name='unique_exam_section_key'),
        ]

    def __str__(self):
        return f'{self.exam_id} · {self.order} · {self.title}'


class ExamAttempt(TimeStampedUUIDModel):
    """O'quvchining imtihondagi yagona urinishi (qayta topshirish yo'q)."""

    exam = ForeignKey(Exam, CASCADE, related_name='attempts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='exam_attempts')
    # O'quvchi imtihonni muddatidan oldin o'zi yakunlagan bo'lsa
    finished_at = DateTimeField(null=True, blank=True)
    # {bo'lim_kaliti: ball} — o'qituvchi qo'lda kiritgan (IELTS Writing/Speaking va h.k.)
    manual_scores = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(fields=['exam', 'student'], name='unique_exam_student'),
        ]

    def __str__(self):
        return f'{self.student_id} · {self.exam_id}'


class ExamAnswer(TimeStampedUUIDModel):
    attempt = ForeignKey(ExamAttempt, CASCADE, related_name='answers')
    section = ForeignKey(ExamSection, CASCADE, related_name='answers')
    # Savol o'chirilsa javob ham o'chadi — shuning uchun test savollarini
    # imtihonga biriktirilgandan keyin o'zgartirish taqiqlanadi (quizzes.services).
    question = ForeignKey('quizzes.Question', CASCADE, related_name='+')
    answer = JSONField(null=True, blank=True)
    given_display = TextField(null=True, blank=True)
    earned_points = FloatField(default=0)

    class Meta:
        ordering = ['created_at']
        constraints = [
            UniqueConstraint(fields=['attempt', 'question'], name='unique_exam_answer'),
        ]
