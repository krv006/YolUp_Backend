"""Test (variantli savollar) modellari.

Oqim:
  - O'qituvchi kursga (ixtiyoriy: aniq darsga) test yaratadi — bir nechta
    savol, har birida bir nechta variant, faqat bittasi to'g'ri.
  - O'quvchi testni topshiradi — cheklanmagan marta qayta urinishi mumkin
    (mashq/o'rganish uslubi, imtihon emas — vaqt chegarasi yo'q).
  - Baholash DARHOL va AVTOMATIK — AI kerak emas, oddiy taqqoslash
    (apps.homework'dagi AI-tekshiruvdan farqli, shu sabab alohida app).
"""
from datetime import timedelta

from django.conf import settings
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    PositiveIntegerField,
    TextField,
)

from apps.core.models import TimeStampedUUIDModel


class Quiz(TimeStampedUUIDModel):
    course = ForeignKey('lessons.Course', CASCADE, related_name='quizzes')
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
        return f'{self.title} @ {self.course.title}'


class Question(TimeStampedUUIDModel):
    quiz = ForeignKey(Quiz, CASCADE, related_name='questions')
    text = TextField()
    order = PositiveIntegerField(default=0)
    points = PositiveIntegerField(default=1)

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


class MockTest(TimeStampedUUIDModel):
    """Imtihon-simulyatsiyasi (EduTech: faqat Student uchun Workspace'dagi
    "Mock Test") — mavjud testlardan bir nechtasini birlashtirib, vaqt
    chegarasi bilan bitta seansda topshiriladigan rejim. Savollar qayta
    yozilmaydi — mavjud `Quiz`lardan tuziladi, baholash ham xuddi shu
    mexanizm (`services.submit_attempt`) orqali ishlaydi."""

    course = ForeignKey('lessons.Course', CASCADE, related_name='mock_tests')
    title = CharField(max_length=200)
    description = TextField(blank=True)
    time_limit_minutes = PositiveIntegerField()
    quizzes = ManyToManyField(Quiz, through='MockTestSection', related_name='mock_tests')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class MockTestSection(TimeStampedUUIDModel):
    """`MockTest` tarkibidagi bitta testning tartibi (bo'lim sifatida)."""

    mock_test = ForeignKey(MockTest, CASCADE, related_name='sections')
    quiz = ForeignKey(Quiz, CASCADE, related_name='+')
    order = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = [('mock_test', 'quiz')]

    def __str__(self):
        return f'{self.mock_test.title} · #{self.order} {self.quiz.title}'


class MockTestAttempt(TimeStampedUUIDModel):
    """O'quvchining bitta imtihon-simulyatsiyasi seansi. `started_at` +
    `mock_test.time_limit_minutes` = topshirish muddati (`deadline`) —
    `services.submit_mock_test` shundan kechikkan urinishni rad etadi."""

    mock_test = ForeignKey(MockTest, CASCADE, related_name='attempts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='mock_test_attempts')
    started_at = DateTimeField(auto_now_add=True)
    submitted_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} · {self.mock_test.title}'

    @property
    def deadline(self):
        return self.started_at + timedelta(minutes=self.mock_test.time_limit_minutes)

    @property
    def total_score(self) -> int:
        return sum(attempt.score for attempt in self.quiz_attempts.all())

    @property
    def total_max_score(self) -> int:
        return sum(attempt.max_score for attempt in self.quiz_attempts.all())


class QuizAttempt(TimeStampedUUIDModel):
    """O'quvchining bitta urinishi. Cheklanmagan — xohlagancha qayta topshiradi.

    `mock_test_attempt` bo'sh bo'lmasa — bu urinish alohida emas, balki bitta
    `MockTestAttempt` seansining bir bo'lagi sifatida yaratilgan."""

    quiz = ForeignKey(Quiz, CASCADE, related_name='attempts')
    student = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='quiz_attempts')
    score = PositiveIntegerField(default=0)
    max_score = PositiveIntegerField(default=0)
    mock_test_attempt = ForeignKey(
        MockTestAttempt, SET_NULL, null=True, blank=True, related_name='quiz_attempts',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} · {self.quiz.title} · {self.score}/{self.max_score}'


class AnswerResponse(TimeStampedUUIDModel):
    attempt = ForeignKey(QuizAttempt, CASCADE, related_name='answers')
    question = ForeignKey(Question, CASCADE, related_name='+')
    # Savol o'chirilgan variant bilan javob berilgan bo'lsa ham tarix saqlansin — SET_NULL.
    selected_option = ForeignKey(Option, SET_NULL, null=True, blank=True, related_name='+')
    is_correct = BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.question_id} · {"to\'g\'ri" if self.is_correct else "xato"}'
