"""Uy vazifasi modellari.

Oqim:
  - O'qituvchi kursga vazifa (Assignment) beradi.
  - O'quvchi faylini yuklaydi (PDF/rasm/DOCX yoki Speaking uchun audio).
  - Topshiriq `pending_review` holatida o'qituvchiga tushadi; o'qituvchi ball
    (va ixtiyoriy izoh) qo'yib tasdiqlaydi — shundan keyin natija o'quvchi va
    ota-onaga ko'rinadi.

AI (Gemini) tekshiruv olib tashlangan (2026-10): `Submission.ai_*`, `check_attempts`,
`feedback_language`, `Assignment.extra_instructions` maydonlari eski ma'lumotlarni
saqlash uchun qoldirilgan, yangi topshiriqlarda ishlatilmaydi.
"""
from django.conf import settings
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateTimeField,
    FileField,
    FloatField,
    ForeignKey,
    JSONField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    TextChoices,
    TextField,
    UniqueConstraint,
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
    # Qoralama (o'quvchilarga ko'rinmaydi, chatga xabar tushmaydi) yoki faol (e'lon qilingan)
    class Status(TextChoices):
        DRAFT = 'draft', 'Qoralama'
        ACTIVE = 'active', 'Faol'

    status = CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    # Guruhga AI xulosa va tavsiya: oxirgi tayyor natija saqlanadi (sahifa ochilganda qayta hisoblamaslik uchun)
    ai_summary = JSONField(null=True, blank=True)
    ai_summary_at = DateTimeField(null=True, blank=True)
    published_at = DateTimeField(null=True, blank=True)
    # E'lon qilinganda vazifa kartasi guruh chatiga tushadimi; muddatdan keyin topshirish mumkinmi
    announce_in_chat = BooleanField(default=True)
    allow_late = BooleanField(default=True)
    # AI dastlabki tekshiruv shu vazifa uchun yoqilganmi (o'chirilsa topshiriq to'g'ridan-to'g'ri o'qituvchiga tushadi)
    ai_check = BooleanField(default=True)
    # Baholash turi: five (1-5), hundred (0..max_score), none (bahosiz, faqat izoh)
    class Grading(TextChoices):
        FIVE = 'five', '5 ballik'
        HUNDRED = 'hundred', '100 ballik'
        NONE = 'none', 'Bahosiz'

    grading = CharField(max_length=8, choices=Grading.choices, default=Grading.FIVE)
    max_score = PositiveSmallIntegerField(default=5)
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
        RESUBMIT_REQUESTED = 'resubmit_requested', "Qayta topshirish so'ralgan"

    assignment = ForeignKey('homework.Assignment', CASCADE, related_name='submissions')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='homework_submissions')
    file = FileField(upload_to=homework_submission_path)
    original_name = CharField(max_length=255)
    status = CharField(max_length=20, choices=Status.choices, default=Status.CHECKING, db_index=True)
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
    # O'qituvchi qo'ygan xom baho vazifa shkalasida (five: 1-5, hundred: 0..max_score); `overall_score` esa doim 0-100
    grade_value = FloatField(null=True, blank=True)
    # Natija (baho va izoh) ota-ona ilovasida ko'rinadimi
    share_with_parent = BooleanField(default=True)
    # O'qituvchining izohi (baho bilan birga o'quvchiga ko'rinadi). `result` (AI natijasi) dan ALOHIDA: o'qituvchi
    # "qayta tekshirish"ni bossa AI `result` ni yangidan yozadi, izoh esa saqlanib qoladi.
    teacher_comment = TextField(blank=True)
    # O'quvchi topshirishda yozgan izoh (o'qituvchi tekshirish sahifasida ko'radi)
    comment = TextField(blank=True, default='')
    resubmit_comment = TextField(blank=True)
    resubmit_requested_at = DateTimeField(null=True, blank=True)
    error = TextField(blank=True)
    checked_at = DateTimeField(null=True, blank=True)
    # Topshirilgan payt (`request.LANGUAGE_CODE`, `Accept-Language`dan) saqlanadi
    # — shu til AI feedback'iga ishlatiladi. O'qituvchi "qayta tekshirish"ni
    # ancha keyin, BOSHQA so'rov kontekstida bosishi mumkin, shuning uchun
    # birinchi tekshiruvdagi til shu yerda saqlanib, keyingi qayta
    # tekshirishlarda ham izchil ishlatiladi (2026-09-06).
    feedback_language = CharField(max_length=8, default='uz')
    # AI tekshiruv necha marta boshlangan (qotib qolgan tekshiruvlarni tiklash
    # cheklovi uchun — `recover_stuck_checks`)
    check_attempts = PositiveSmallIntegerField(default=0)
    # Tashqi AI xizmatidagi submission id (HOMEWORK_AI_URL sozlangan bo'lsa)
    ai_external_id = CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} → {self.assignment.title} [{self.status}]'


class HomeworkBoard(TimeStampedUUIDModel):
    """O'quvchining shu vazifa uchun shaxsiy doskasi (qoralama ham, topshirilgan holat ham shu yerda).

    `sheets` — [{"strokes": [...]}, ...]; chiziqlar dars doskasi (`apps.board`) bilan bir xil shaklda. Avtosaqlash
    butun holatni almashtiradi (`PUT`); topshirishda sahifalar rasmli PDF'ga aylantirilib oddiy `Submission` yaratiladi."""

    assignment = ForeignKey('homework.Assignment', CASCADE, related_name='boards')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='homework_boards')
    sheets = JSONField(default=list)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['assignment', 'student'], name='unique_homework_board_per_student'),
        ]

    def __str__(self):
        return f'{self.student_id} · {self.assignment_id} ({len(self.sheets)} sheet)'


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


class SubmissionFile(TimeStampedUUIDModel):
    """Topshiriqning QO'SHIMCHA fayllari (asosiy fayl `Submission.file` da; AI shuni tekshiradi). Bir topshiriqda jami 5 tagacha."""

    submission = ForeignKey('homework.Submission', CASCADE, related_name='extra_files')
    file = FileField(upload_to=homework_submission_path)
    original_name = CharField(max_length=255)
    size = PositiveIntegerField(default=0)
    order = PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'created_at']


class SubmissionDraft(TimeStampedUUIDModel):
    """O'quvchining topshirish oldidan yozgan izohi ("Qoralama saqlash") — boshqa qurilmadan ham davom ettirish uchun."""

    assignment = ForeignKey('homework.Assignment', CASCADE, related_name='drafts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='homework_drafts')
    comment = TextField(blank=True, default='')

    class Meta:
        constraints = [UniqueConstraint(fields=['assignment', 'student'], name='unique_homework_draft')]
