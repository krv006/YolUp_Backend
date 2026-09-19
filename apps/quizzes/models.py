"""Test (variantli savollar) modellari.

Oqim:
  - O'qituvchi kursga (ixtiyoriy: aniq darsga) test yaratadi — bir nechta
    savol, har birida bir nechta variant, faqat bittasi to'g'ri.
  - O'quvchi testni topshiradi — cheklanmagan marta qayta urinishi mumkin
    (mashq/o'rganish uslubi, imtihon emas — vaqt chegarasi yo'q).
  - Baholash DARHOL va AVTOMATIK — AI kerak emas, oddiy taqqoslash
    (apps.homework'dagi AI-tekshiruvdan farqli, shu sabab alohida app).
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
    TextField,
    TextChoices,
)

from apps.core.models import TimeStampedUUIDModel
from apps.lessons.models import Course


class Quiz(TimeStampedUUIDModel):
    # Guruhsiz (fan bo'yicha) test uchun `course` bo'sh — bunday test o'quvchilarga
    # ko'rinmaydi, faqat muallif (`author`) o'qituvchi ko'radi va guruhga nusxalaydi.
    course = ForeignKey('lessons.Course', CASCADE, null=True, blank=True, related_name='quizzes')
    author = ForeignKey(
        settings.AUTH_USER_MODEL, SET_NULL, null=True, blank=True, related_name='authored_quizzes',
    )
    subject = CharField(max_length=100, choices=Course.Subject.choices, blank=True)
    # Aniq (tugagan yoki tugamagan) darsga bog'lash ixtiyoriy — Assignment bilan bir xil naqsh.
    lesson = ForeignKey(
        'lessons.Lesson', SET_NULL, null=True, blank=True, related_name='quizzes',
    )
    title = CharField(max_length=200)
    description = TextField(blank=True)
    # Muddat — informatsion (Assignment.due_at bilan bir xil naqsh): topshirishni
    # BLOKLAMAYDI, faqat o'quvchiga/interfeysga qachongacha ekanini ko'rsatadi.
    due_at = DateTimeField(null=True, blank=True, db_index=True)
    # Ochilish kuni — bo'sh bo'lsa darhol ochiq. Belgilansa, shu vaqtgacha
    # STUDENT/PARENT uchun ko'rinmaydi (selectors.quizzes_for); o'qituvchi/admin
    # tayyorlash uchun har doim ko'radi.
    opens_at = DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} @ {self.course.title if self.course_id else self.subject}'


class Question(TimeStampedUUIDModel):
    class Type(TextChoices):
        SINGLE = 'single', "Bitta to'g'ri javob"
        MULTIPLE = 'multiple', "Bir nechta to'g'ri javob"
        TRUE_FALSE = 'true_false', "To'g'ri / noto'g'ri"
        NUMERIC = 'numeric', 'Son kiritish'
        TEXT = 'text', 'Matn kiritish'
        MATCHING = 'matching', 'Moslashtirish'
        ORDERING = 'ordering', 'Tartibga solish'
        FILL_BLANK = 'fill_blank', "Bo'sh joyni to'ldirish"

    quiz = ForeignKey(Quiz, CASCADE, related_name='questions')
    type = CharField(max_length=20, choices=Type.choices, default=Type.SINGLE)
    text = TextField()
    order = PositiveIntegerField(default=0)
    points = PositiveIntegerField(default=2)
    # Turga xos javob kaliti (true_false/numeric/text/matching/fill_blank).
    # single/multiple/ordering javoblari Option jadvalida saqlanadi.
    answer_key = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.text[:60]


class Option(TimeStampedUUIDModel):
    question = ForeignKey(Question, CASCADE, related_name='options')
    text = CharField(max_length=500)
    is_correct = BooleanField(default=False)
    order = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.text[:60]


class QuizAttempt(TimeStampedUUIDModel):
    """O'quvchining bitta urinishi. Cheklanmagan — xohlagancha qayta topshiradi."""

    quiz = ForeignKey(Quiz, CASCADE, related_name='attempts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='quiz_attempts')
    # Qisman ball mumkin (matching/fill_blank) — 2 xonagacha yaxlitlanadi.
    score = FloatField(default=0)
    max_score = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} · {self.quiz.title} · {self.score}/{self.max_score}'


class AnswerResponse(TimeStampedUUIDModel):
    attempt = ForeignKey(QuizAttempt, CASCADE, related_name='answers')
    question = ForeignKey(Question, CASCADE, related_name='+')
    # Savol o'chirilgan variant bilan javob berilgan bo'lsa ham tarix saqlansin — SET_NULL.
    selected_option = ForeignKey(Option, SET_NULL, null=True, blank=True, related_name='+')
    # O'quvchining xom javobi (turga xos) va o'qiladigan ko'rinishi.
    answer = JSONField(null=True, blank=True)
    given_display = TextField(null=True, blank=True)
    earned_points = FloatField(default=0)
    is_correct = BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.question_id} · {"to\'g\'ri" if self.is_correct else "xato"}'
