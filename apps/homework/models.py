"""Uy vazifasi modellari (AI-home-checker integratsiyasi).

Oqim:
  - O'qituvchi kursga vazifa (Assignment) beradi.
  - O'quvchi faylini yuklaydi (PDF/rasm/DOCX yoki Speaking uchun audio).
  - Gemini savolma-savol tekshiradi (apps/homework/ai.py) va JSON natija
    Submission.result ga yoziladi — bola, o'qituvchi va ota-ona ko'radi.
"""
from django.conf import settings
from django.db.models import (
    CASCADE,
    SET_NULL,
    CharField,
    DateTimeField,
    FileField,
    FloatField,
    ForeignKey,
    JSONField,
    TextChoices,
    TextField,
)

from apps.core.models import TimeStampedUUIDModel
from apps.core.uploads import homework_submission_path, homework_task_path


class Assignment(TimeStampedUUIDModel):
    """O'qituvchi bergan uy vazifasi. Fan kursdan olinadi (course.subject)."""

    course = ForeignKey('lessons.Course', CASCADE, related_name='assignments')
    # Vazifa qaysi (tugagan) darsga/mavzuga tegishli — ixtiyoriy, bir dars
    # bo'yicha bir nechta vazifa berish mumkin (FK, cheklovsiz).
    lesson = ForeignKey(
        'lessons.Lesson', SET_NULL, null=True, blank=True, related_name='assignments',
    )
    title = CharField(max_length=200)
    description = TextField(blank=True)
    # O'qituvchi rich editor'da yozgan vazifa matni — server tomonda
    # tozalangan (sanitize) HTML saqlanadi
    body = TextField(blank=True)
    # Vazifa fayli (Word/PDF/rasm) — o'qituvchi tayyorini yuklaydi,
    # o'quvchilar yuklab oladi
    attachment = FileField(upload_to=homework_task_path, null=True, blank=True)
    attachment_name = CharField(max_length=255, blank=True)
    due_at = DateTimeField(null=True, blank=True, db_index=True)
    # Til fanlari uchun ko'nikma: writing / reading / listening / speaking.
    # Bo'sh bo'lsa — oddiy fan sifatida tekshiriladi.
    skill_key = CharField(max_length=20, blank=True)
    # O'qituvchining AI'ga qo'shimcha ko'rsatmasi ("7-sinf darajasida", "qat'iy bo'l")
    extra_instructions = TextField(blank=True)
    # Deadline eslatmalari faqat BIR MARTA yuborilishi uchun (send_deadline_reminders
    # davriy chaqirilganda takror yubormasin) — apps/homework/services.py
    reminder_halfway_sent_at = DateTimeField(null=True, blank=True)
    reminder_1h_sent_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} @ {self.course.title}'


class Submission(TimeStampedUUIDModel):
    """O'quvchining topshirig'i + AI tekshiruv natijasi.

    Oqim: AI tekshirgach status PENDING_REVIEW bo'ladi — bu bosqichda
    `result`/`overall_score`/`grade` AI TAKLIFI (AI natijasidan nusxa),
    lekin o'quvchiga hali ko'rsatilmaydi. O'qituvchi ko'rib chiqadi,
    xohlasa tahrirlaydi va tasdiqlaydi — shundagina status DONE bo'ladi
    va natija o'quvchiga ochiladi. AI'ning ASL (o'zgarmas) natijasi
    `ai_result`/`ai_overall_score`/`ai_grade`da fon/log sifatida saqlanadi.
    """

    class Status(TextChoices):
        CHECKING = 'checking', 'Tekshirilmoqda'
        PENDING_REVIEW = 'pending_review', "O'qituvchi ko'rib chiqishi kutilmoqda"
        DONE = 'done', 'Tasdiqlangan'
        ERROR = 'error', 'Xatolik'

    assignment = ForeignKey('homework.Assignment', CASCADE, related_name='submissions')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='homework_submissions')
    file = FileField(upload_to=homework_submission_path)
    original_name = CharField(max_length=255)
    status = CharField(max_length=15, choices=Status.choices, default=Status.CHECKING, db_index=True)
    # Yakuniy (hozirgi) natija — dastlab AI'nikidan nusxa, o'qituvchi
    # tasdiqlashda ustidan yozishi mumkin. Shu maydonlar o'quvchiga ko'rinadi.
    result = JSONField(null=True, blank=True)
    overall_score = FloatField(null=True, blank=True)
    grade = CharField(max_length=40, blank=True)
    # AI'ning ASL natijasi — o'zgarmas, faqat audit/taqqoslash uchun
    # (o'qituvchiga ko'rinadi, o'quvchiga emas).
    ai_result = JSONField(null=True, blank=True)
    ai_overall_score = FloatField(null=True, blank=True)
    ai_grade = CharField(max_length=40, blank=True)
    reviewed_by = ForeignKey(
        settings.AUTH_USER_MODEL, SET_NULL, null=True, blank=True,
        related_name='homework_reviews',
    )
    reviewed_at = DateTimeField(null=True, blank=True)
    error = TextField(blank=True)
    checked_at = DateTimeField(null=True, blank=True)
    # Topshirilgan payt (`request.LANGUAGE_CODE`, `Accept-Language`dan) saqlanadi
    # — shu til AI feedback'iga ishlatiladi. O'qituvchi "qayta tekshirish"ni
    # ancha keyin, BOSHQA so'rov kontekstida bosishi mumkin, shuning uchun
    # birinchi tekshiruvdagi til shu yerda saqlanib, keyingi qayta
    # tekshirishlarda ham izchil ishlatiladi (2026-09-06).
    feedback_language = CharField(max_length=8, default='uz')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} → {self.assignment.title} [{self.status}]'


class AssignmentFocusEvent(TimeStampedUUIDModel):
    """O'quvchi vazifa sahifasidan chiqib-kirishi — vaqt kuzatuvi
    (darslardagi FocusEvent uslubida, lekin Assignment uchun)."""

    class Kind(TextChoices):
        EXIT = 'exit', 'Sahifadan chiqdi'
        RETURN = 'return', 'Sahifaga qaytdi'

    assignment = ForeignKey('homework.Assignment', CASCADE, related_name='focus_events')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='homework_focus_events')
    kind = CharField(max_length=8, choices=Kind.choices)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.student.username} · {self.kind} @ {self.assignment.title}'
