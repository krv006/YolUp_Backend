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
# 2026-11-10: MP4 tayyor bo'lguncha yangi yozuv hech kimga ochilmaydi. Server band paytda (jonli darslar) konvertatsiya
# boshlanmaydi (yuklama chegarasi), lekin yozuv `MAX_WAIT` dan uzoq kutmasligi uchun shundan keyin baribir boshlanadi.
# Hammasi bajarilmasa ham yozuv `HIDE_MAX` dan keyin asl WebM bilan ochiladi (konvertatsiya xizmati o'lib qolsa abadiy yopiq qolmasin).
MAX_WAIT = timedelta(hours=2)
HIDE_MAX = timedelta(hours=12)


def needs_mp4(recording) -> bool:
    """Yozuv iOS ochmaydigan formatda (WebM) va MP4 nusxasi hali yo'q."""
    name = (recording.file_name or '').lower()
    return bool(name) and not name.endswith('.mp4') and not recording.mp4_file_name


def is_converting(recording, now=None) -> bool:
    """Yozuv MP4 nusxa kutmoqda va hozircha hech kimga ochilmaydi. Konvertatsiya xato bilan tugagan yoki juda uzoq cho'zilgan bo'lsa —
    False (asl WebM bilan ochiladi)."""
    if not recording.convert_required or recording.mp4_file_name:
        return False
    if recording.mp4_error not in ('', CONVERTING):
        return False
    started = recording.ended_at or recording.created_at
    return not (started and (now or timezone.now()) - started > HIDE_MAX)


def system_busy() -> bool:
    """1 daqiqalik o'rtacha yuklama yadrolar soniga nisbatan chegaradan oshgan (standart 0,7; `TRANSCODE_MAX_LOAD_RATIO`)."""
    try:
        load = os.getloadavg()[0]
    except (OSError, AttributeError):
        return False
    return load > (os.cpu_count() or 1) * float(os.getenv('TRANSCODE_MAX_LOAD_RATIO', '0.7'))


def should_wait(recording, now=None) -> bool:
    """Server band va yozuv hali `MAX_WAIT` dan kam kutgan bo'lsa — keyinroq (yuklama kamayganda)."""
    if not system_busy():
        return False
    waited_since = recording.ended_at or recording.created_at
    return not (waited_since and (now or timezone.now()) - waited_since > MAX_WAIT)


def _after_conversion(recording_pk) -> None:
    """Konvertatsiya tugadi (muvaffaqiyatli yoki xato — xatoda asl WebM bilan ochiladi): endi yozuv ochiq, guruhga e'lon qilinadi.
    Faqat yangi (`convert_required`) yozuvlar uchun — eskilari allaqachon e'lon qilingan."""
    recording = LessonRecording.objects.select_related('lesson', 'lesson__course').get(pk=recording_pk)
    if not recording.convert_required:
        return
    from apps.live.services import _announce_recording_ready

    _announce_recording_ready(recording)


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
        # Ekran yozuvi: 1280 px gacha, ~15 kadr/s — sifat yetarli, CPU va hajm kam.
        # `-g 30` = har 2 soniyada kalit kadr: standart (250 kadr) har ~17 soniyada edi, o'tkazib yuborganda pleer shuncha
        # videoni dekod qilib qotardi. `-sc_threshold 0` — sahna o'zgarishida qo'shimcha kalit kadr qo'ymaydi (hajm barqaror).
        codec = ['-vf', "scale='min(1280,iw)':-2,fps=15", '-c:v', 'libx264', '-preset', 'veryfast',
                 '-crf', '28', '-g', '30', '-keyint_min', '30', '-sc_threshold', '0', '-pix_fmt', 'yuv420p']
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
        _safe_after(recording_pk)
        return 'failed'
    LessonRecording.objects.filter(pk=recording_pk).update(mp4_file_name=final_name, mp4_error='')
    logger.info('recording %s -> %s', recording_pk, final_name)
    _safe_after(recording_pk)
    return 'done'


def _safe_after(recording_pk) -> None:
    try:
        _after_conversion(recording_pk)
    except Exception:  # noqa: BLE001 — e'lon xatosi konvertatsiya natijasini buzmasin
        logger.exception('recording %s: post-conversion announce failed', recording_pk)
