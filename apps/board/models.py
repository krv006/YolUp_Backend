"""Doska modellari (EduTech.docx: Zoom whiteboard uslubi).

Qoidalar:
  - Har dars uchun bir nechta sheet (lenta — tepadan pastga).
  - Chizish: o'qituvchi doim; o'quvchi faqat ruxsat (BoardGrant) olgach.
  - O'chirish sababi majburiy — BoardErase jurnalida saqlanadi.
  - Doska faqat platforma ichida ko'rinadi (auth'siz URL yo'q).
"""
from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    JSONField,
    PositiveIntegerField,
    TextField,
    UniqueConstraint,
)

from apps.core.models import TimeStampedUUIDModel

# Chizish koordinata maydoni — front bilan kelishilgan o'lcham
SHEET_W, SHEET_H = 1600, 900


class BoardSheet(TimeStampedUUIDModel):
    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='board_sheets')
    index = PositiveIntegerField(default=0)
    # Sahifa nomi ("Mavzu: Present Perfect") — bo'sh bo'lsa frontend raqam ko'rsatadi
    title = CharField(max_length=120, blank=True, default='')
    # [{id, color, width, points: [[x, y], ...], by}] — by = chizgan foydalanuvchi
    strokes = JSONField(default=list)

    class Meta:
        ordering = ['index']
        constraints = [
            UniqueConstraint(fields=['lesson', 'index'], name='unique_lesson_sheet_index'),
        ]

    def __str__(self):
        return f'{self.lesson_id} · sheet {self.index} ({len(self.strokes)} strokes)'


class BoardGrant(TimeStampedUUIDModel):
    """O'qituvchi o'quvchiga doskada chizish ruxsatini berdi."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='board_grants')
    student = ForeignKey('accounts.User', CASCADE, related_name='board_grants')

    class Meta:
        constraints = [
            UniqueConstraint(fields=['lesson', 'student'], name='unique_lesson_board_grant'),
        ]


class BoardErase(TimeStampedUUIDModel):
    """O'chirish jurnali — sabab MAJBURIY (EduTech.docx)."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='board_erases')
    user = ForeignKey('accounts.User', CASCADE, related_name='board_erases')
    sheet_index = PositiveIntegerField()
    reason = TextField()
    stroke_ids = JSONField(default=list)

    class Meta:
        ordering = ['-created_at']
