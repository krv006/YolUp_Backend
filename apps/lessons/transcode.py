"""Dars yozuvini iOS ochadigan formatga o'girish (H.264 + AAC, MP4).

Brauzerdan kelgan yozuv WebM (VP8/VP9 + Opus): Android/Chrome ochadi, iOS (AVFoundation) ochmaydi. Shuning uchun
yozuv tayyor bo'lgach (u darhol WebM bilan "Tayyor" bo'ladi) FONDA MP4 nusxa tayyorlanadi; stream shu nusxani beradi.
Asl WebM o'chirilmaydi.

Server yuklamasi: qayta kodlash CPU'ni yeydi, shuning uchun bu ish alohida `transcoder` xizmatida, BIR vaqtda
bitta yozuv, past ustuvorlik (`nice`) bilan bajariladi (docker-compose.prod.yml).
"""
import logging
import os
import shutil
import subprocess
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import LessonRecording

logger = logging.getLogger('apps')

CONVERTING = 'converting'
STALE_AFTER = timedelta(hours=6)  # "converting" shundan uzoq tursa (jarayon o'lgan) — qayta navbatga qaytariladi
TIMEOUT_SECONDS = 4 * 3600


def _pending() -> 'QuerySet':
    """Tayyor, lekin MP4 nusxasi yo'q yozuvlar. Allaqachon `.mp4` bo'lgan (eski egress) yozuvlar kerak emas."""
    return (
        LessonRecording.objects.filter(status=LessonRecording.Status.COMPLETED, mp4_file_name='', mp4_error='')
        .exclude(file_name='').exclude(file_name__iendswith='.mp4')
    )


def release_stale() -> int:
    """O'lgan jarayon qoldirgan "converting" belgisini olib tashlaydi (qayta uriniladi)."""
    return LessonRecording.objects.filter(
        mp4_error=CONVERTING, updated_at__lt=timezone.now() - STALE_AFTER,
    ).update(mp4_error='')


def _failed() -> 'QuerySet':
    return (
        LessonRecording.objects.filter(status=LessonRecording.Status.COMPLETED, mp4_file_name='')
        .exclude(mp4_error__in=['', CONVERTING]).exclude(file_name='').exclude(file_name__iendswith='.mp4')
    )


def next_pending(*, retry_failed: bool = False, limit: int = 1) -> list:
    """Navbatdagi yozuvlar (eskisi oldin). `retry_failed` — avval xato bilan tugaganlarini ham qo'shadi."""
    condition = Q(pk__in=_pending().values('pk'))
    if retry_failed:
        condition |= Q(pk__in=_failed().values('pk'))
    return list(LessonRecording.objects.filter(condition).order_by('created_at')[:limit])


def _has_video(path) -> bool:
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type',
         '-of', 'csv=p=0', str(path)],
        capture_output=True, text=True, timeout=120,
    )
    return result.returncode == 0 and 'video' in result.stdout


def _command(src, dst, *, video: bool) -> list:
    base = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(src)]
    if video:
        # Ekran yozuvi: 1280 px gacha, ~15 kadr/s — sifat yetarli, CPU va hajm kam
        codec = ['-vf', "scale='min(1280,iw)':-2,fps=15", '-c:v', 'libx264', '-preset', 'veryfast',
                 '-crf', '28', '-pix_fmt', 'yuv420p']
    else:
        codec = ['-vn']
    cmd = base + codec + ['-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(dst)]
    return (['nice', '-n', '15'] + cmd) if shutil.which('nice') else cmd


def convert(recording_pk) -> str:
    """Bitta yozuvni o'giradi. Qaytaradi: 'done' | 'failed' | 'skipped' (boshqa jarayon band qilgan yoki kerak emas)."""
    claimed = _pending().filter(pk=recording_pk).update(mp4_error=CONVERTING)
    if not claimed:
        claimed = _failed().filter(pk=recording_pk).update(mp4_error=CONVERTING)  # `--retry-failed`
    if not claimed:
        return 'skipped'
    recording = LessonRecording.objects.get(pk=recording_pk)
    src = settings.RECORDINGS_DIR / recording.file_name
    tmp = None
    try:
        if not src.exists():
            raise FileNotFoundError(f'Fayl topilmadi: {recording.file_name}')
        video = _has_video(src)
        extension = '.mp4' if video else '.m4a'
        final_name = f'{src.stem}{extension}'
        tmp = settings.RECORDINGS_DIR / f'{src.stem}.part{extension}'
        result = subprocess.run(_command(src, tmp, video=video), capture_output=True, text=True,
                                timeout=TIMEOUT_SECONDS)
        if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError(result.stderr[-400:] or 'ffmpeg xato bilan tugadi')
        os.replace(tmp, settings.RECORDINGS_DIR / final_name)
    except Exception as exc:  # noqa: BLE001 — yozuv baribir WebM bilan ishlayveradi
        logger.warning('recording %s MP4 ga o\'tmadi: %s', recording_pk, exc)
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        LessonRecording.objects.filter(pk=recording_pk).update(mp4_error=(str(exc) or 'xato')[:500])
        return 'failed'
    LessonRecording.objects.filter(pk=recording_pk).update(mp4_file_name=final_name, mp4_error='')
    logger.info('recording %s -> %s', recording_pk, final_name)
    return 'done'
