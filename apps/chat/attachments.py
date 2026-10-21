"""Chat fayllarini tekshirish: ruxsat etilgan turlar, hajm, rasm/PDF yaroqliligi, ovozli xabar."""
import os

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from .models import Message

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_VOICE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

IMAGES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
AUDIO = {
    '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.oga': 'audio/ogg', '.opus': 'audio/ogg',
    '.webm': 'audio/webm', '.wav': 'audio/wav', '.aac': 'audio/aac',
}
# `.webm` ovoz sifatida qoladi (brauzer yozuvlari); video uchun mp4/mov/m4v
VIDEOS = {'.mp4': 'video/mp4', '.mov': 'video/quicktime', '.m4v': 'video/x-m4v'}
DOCUMENTS = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
}
ALLOWED = {**IMAGES, **AUDIO, **VIDEOS, **DOCUMENTS}

# Safari/iOS ovoz yozuvi `audio/mp4` ni ko'pincha `.mp4` nomi bilan beradi — faqat ovozli xabar sifatida qabul qilinadi
VOICE_ONLY = {'.mp4': 'audio/mp4'}

# Brauzerda sahifa ichida ochilishi xavfsiz turlar; qolganlari yuklab olinadi
INLINE_TYPES = {'application/pdf', *IMAGES.values(), *AUDIO.values(), *VIDEOS.values()}

MAX_WAVEFORM = 200


def _check_image(upload) -> None:
    from PIL import Image

    try:
        upload.seek(0)
        Image.open(upload).verify()
    except Exception:
        raise ValidationError({'file': _('Rasm fayli buzilgan.')}) from None
    finally:
        upload.seek(0)


def _pdf_pages(upload):
    upload.seek(0)
    head = upload.read(5)
    upload.seek(0)
    if head != b'%PDF-':
        raise ValidationError({'file': _('PDF fayli buzilgan.')})
    try:
        from pypdf import PdfReader

        return len(PdfReader(upload).pages)
    except Exception:
        return None
    finally:
        upload.seek(0)


def clean_waveform(raw) -> list:
    """Ovoz to'lqini: butun sonlar ro'yxati (0..255); noto'g'ri bo'lsa bo'sh — frontend o'zi chizadi."""
    if not isinstance(raw, list):
        return []
    values = []
    for item in raw[:MAX_WAVEFORM]:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return []
        values.append(max(0, min(255, int(item))))
    return values


def inspect_upload(upload, requested_type: str = '') -> dict:
    """Yuklangan fayl haqidagi ma'lumot (xabar maydonlari). Turni mijoz aytgan `content_type`dan emas,
    kengaytmadan aniqlaymiz — soxta turdan himoya."""
    name = os.path.basename(upload.name or '')[:255] or 'fayl'
    ext = os.path.splitext(name)[1].lower()
    voice = requested_type == Message.Type.VOICE
    mime = (VOICE_ONLY.get(ext) if voice else None) or ALLOWED.get(ext)  # ovozli xabarda `.mp4` — audio
    if mime is None:
        raise ValidationError({'file': _("Bu turdagi fayl yuborib bo'lmaydi (%(ext)s).") % {'ext': ext or '-'}})
    if ext in VIDEOS and not voice:
        if upload.size > MAX_VIDEO_BYTES:
            raise ValidationError({'file': _('Video 50 MB dan katta.')})
    elif upload.size > MAX_FILE_BYTES:
        raise ValidationError({'file': _('Fayl 20 MB dan katta.')})
    if upload.size == 0:
        raise ValidationError({'file': _("Fayl bo'sh.")})

    pages = None
    if requested_type == Message.Type.VOICE:
        if ext not in AUDIO and ext not in VOICE_ONLY:
            raise ValidationError({'file': _("Ovozli xabar audio fayl bo'lishi kerak.")})
        if upload.size > MAX_VOICE_BYTES:
            raise ValidationError({'file': _('Ovozli xabar 10 MB dan katta.')})
        message_type = Message.Type.VOICE
    elif ext in IMAGES:
        _check_image(upload)
        message_type = Message.Type.IMAGE
    elif ext in VIDEOS:
        message_type = Message.Type.VIDEO
    else:
        message_type = Message.Type.FILE
        if ext == '.pdf':
            pages = _pdf_pages(upload)
    return {
        'message_type': message_type, 'file_name': name, 'file_type': mime,
        'file_size': upload.size, 'page_count': pages,
    }
