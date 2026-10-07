"""Yuklanadigan fayllar uchun taxmin qilib bo'lmaydigan (uuid) nomlar.

Nega: `/media/` Caddy orqali ochiq tarqatiladi, asl fayl nomi (`IMG_1234.jpg`)
esa taxmin qilinadi. Nomni tasodifiy qilish — yangi fayllarni topib bo'lmaydigan
qiladi. Asl nom DB'da alohida maydonda saqlanadi (`Submission.original_name`,
`Assignment.attachment_name`) va yuklab olishda shu ishlatiladi. Kengaytma
saqlanadi (AI tekshiruv turni shundan aniqlaydi).
"""
import os
import uuid

from django.utils import timezone


def _random_name(filename: str) -> str:
    return f'{uuid.uuid4().hex}{os.path.splitext(filename or "")[1].lower()}'


def _dated(prefix: str, filename: str) -> str:
    return f'{prefix}/{timezone.now():%Y/%m}/{_random_name(filename)}'


def homework_submission_path(instance, filename: str) -> str:
    return _dated('homework', filename)


def homework_task_path(instance, filename: str) -> str:
    return _dated('homework/tasks', filename)


def certificate_path(instance, filename: str) -> str:
    return _dated('certificates', filename)
