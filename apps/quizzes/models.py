"""Test (variantli savollar) modellari.

Oqim:
  - O'qituvchi kursga (ixtiyoriy: aniq darsga) test yaratadi — bir nechta
    savol, har birida bir nechta variant, faqat bittasi to'g'ri.
  - O'quvchi testni topshiradi — cheklanmagan marta qayta urinishi mumkin
    (mashq/o'rganish uslubi, imtihon emas — vaqt chegarasi yo'q).
  - Baholash DARHOL va AVTOMATIK — AI kerak emas, oddiy taqqoslash
    (apps.homework'dagi AI-tekshiruvdan farqli, shu sabab alohida app).
"""
import os
import uuid

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
    TextField,
    TextChoices,
)

from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.models import TimeStampedUUIDModel
from apps.core.uploads import ai_quiz_source_path
from apps.lessons.models import Course


def quiz_audio_path(instance, filename: str) -> str:
    """Taxmin qilib bo'lmaydigan fayl nomi (uuid) — audio URL'i ochiq `/media/`
    orqali beriladi, shuning uchun nomni topib bo'lmasligi himoya vazifasini o'taydi."""
    return f'quiz_audio/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}'


class Quiz(TimeStampedUUIDModel):
    class Status(TextChoices):
        DRAFT = 'draft', 'Qoralama'
        PUBLISHED = 'published', "E'lon qilingan"

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
    # `draft` — DB'ga doimiy yozilgan, lekin o'quvchi/ota-onaga ko'rinmaydi va
    # to'g'ri javoblari to'liq belgilanmagan bo'lishi mumkin (import qilingan
    # test); `published` — hamma ko'radi, faqat to'liq test bo'la oladi.
    status = CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    # Mavzu — majburiy (frontend validatsiya qiladi, backend ham talab qiladi).
    # `title` esa ixtiyoriy nom; bo'sh bo'lsa frontend ro'yxatda `topic`ni ko'rsatadi.
    topic = CharField(max_length=200, blank=True)
    title = CharField(max_length=200, blank=True)
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
        name = self.title or self.topic
        return f'{name} @ {self.course.title if self.course_id else self.subject}'


class QuestionGroup(TimeStampedUUIDModel):
    """Bir nechta savolga umumiy material: sarlavha, matn parchasi va/yoki audio
    (IELTS Reading/Listening, SAT passage). Savol `group` orqali bog'lanadi;
    guruhsiz savollar (eski testlar, importlar) o'zgarishsiz ishlaydi."""

    quiz = ForeignKey('quizzes.Quiz', CASCADE, related_name='groups')
    order = PositiveIntegerField(default=0)
    title = CharField(max_length=200, blank=True)
    passage = TextField(blank=True)
    audio = FileField(upload_to=quiz_audio_path, null=True, blank=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title or str(self.id)


@receiver(post_delete, sender=QuestionGroup)
def _delete_group_audio(sender, instance, **kwargs):
    if instance.audio:
        instance.audio.delete(save=False)


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
    group = ForeignKey(
        'quizzes.QuestionGroup', SET_NULL, null=True, blank=True, related_name='questions',
    )
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


class AiQuizJob(TimeStampedUUIDModel):
    """Materialdan AI bilan test yaratish ishi (tashqi Test-creator xizmati).

    O'qituvchi fayl yuklaydi — ish `queued` bo'ladi; cron (`sync_ai_quizzes`) uni bosqichma-bosqich
    olib boradi va oxirida natija `draft` test bo'lib saqlanadi. O'qituvchi tahrirlab e'lon qiladi.
    """

    class Status(TextChoices):
        QUEUED = 'queued', 'Navbatda'
        PROCESSING = 'processing', 'Material tahlil qilinmoqda'
        GENERATING = 'generating', 'Savollar yaratilmoqda'
        DONE = 'done', 'Tayyor'
        FAILED = 'failed', 'Xato'

    class Standard(TextChoices):
        UZBMB = 'uzbmb', 'Milliy sertifikat (UZBMB)'
        IELTS = 'ielts', 'IELTS Academic'
        SAT = 'sat', 'Digital SAT'

    ACTIVE_STATUSES = ('queued', 'processing', 'generating')

    teacher = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='ai_quiz_jobs')
    course = ForeignKey('lessons.Course', SET_NULL, null=True, blank=True, related_name='+')
    subject = CharField(max_length=100, choices=Course.Subject.choices, blank=True)
    topic = CharField(max_length=200)
    title = CharField(max_length=200, blank=True)
    # Bo'sh = imtihon qoidalari bo'yicha AI generator (apps/quizzes/ai_exam.py); to'ldirilgan = Test-creator (eski yo'l)
    standard = CharField(max_length=10, choices=Standard.choices, blank=True, default='')
    question_count = PositiveIntegerField(default=20)
    source_file = FileField(upload_to=ai_quiz_source_path, null=True, blank=True)
    source_name = CharField(max_length=255, blank=True)
    # AI generator materiali: yuklangan fayllar/qo'yilgan matndan olingan toza matn (bo'sh bo'lishi mumkin —
    # u holda AI mavzu va qoidalar bo'yicha matnni o'zi yozadi). Fayllarning o'zi saqlanmaydi.
    source_text = TextField(blank=True)  # faqat qo'yilgan (paste) matn; fayllar fonda o'qiladi
    # Yuklangan material fayllari: [{'path': saqlash yo'li, 'name': asl nomi}] — fonda matnga aylantirilib o'chiriladi
    source_paths = JSONField(default=list, blank=True)
    # Imtihon nomi ("IELTS Academic Reading", "SAT"...) — qoidalar berilmasa AI uning rasmiy tuzilmasini o'zi eslaydi
    exam_name = CharField(max_length=120, blank=True)
    # Imtihon qoidalari (format) — fayl yoki matn; bo'sh bo'lsa oddiy variantli test
    rules_file = FileField(upload_to=ai_quiz_source_path, null=True, blank=True)
    rules_name = CharField(max_length=255, blank=True)
    rules_text = TextField(blank=True)
    # AI tuzgan reja va tayyor bo'limlar (xato bo'lsa qayta boshlamasdan davom etish uchun)
    plan = JSONField(default=dict, blank=True)
    summary = CharField(max_length=300, blank=True)
    status = CharField(max_length=12, choices=Status.choices, default=Status.QUEUED, db_index=True)
    error = TextField(blank=True)
    warnings = JSONField(default=list, blank=True)
    tc_document_id = CharField(max_length=64, blank=True)
    # Savollar yaratish bosqichidagi muvaffaqiyatsiz urinishlar soni (Gemini limiti va h.k.)
    attempts = PositiveIntegerField(default=0)
    quiz = ForeignKey('quizzes.Quiz', SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.topic} [{self.status}]'
