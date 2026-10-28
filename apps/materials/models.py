"""Guruh materiallari: o'qituvchi darslik, audio, fayl yuklaydi; guruh o'quvchilari ko'radi va yuklab oladi."""
from django.conf import settings
from django.db.models import CASCADE, SET_NULL, CharField, FileField, ForeignKey, PositiveBigIntegerField

from apps.core.models import TimeStampedUUIDModel
from apps.core.uploads import material_path


class Material(TimeStampedUUIDModel):
    course = ForeignKey('lessons.Course', CASCADE, related_name='materials')
    uploaded_by = ForeignKey(settings.AUTH_USER_MODEL, SET_NULL, null=True, blank=True, related_name='uploaded_materials')
    title = CharField(max_length=200)
    file = FileField(upload_to=material_path)
    original_name = CharField(max_length=255)
    size = PositiveBigIntegerField(default=0)
    kind = CharField(max_length=10, default='other')  # pdf | doc | audio | video | image | other

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} · {self.course_id}'
