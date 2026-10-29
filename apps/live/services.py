"""Live service layer — LiveKit token berish, davomat, diqqat tekshiruvi, share ruxsati."""
import asyncio
import os
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from livekit.api import AccessToken, LiveKitAPI, UpdateParticipantRequest, VideoGrants
from livekit.protocol.models import ParticipantPermission, TrackSource
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.lessons import services as lesson_services
from apps.lessons.models import AttentionCheck, Enrollment, FocusAlert, FocusEvent, Lesson, LessonBan

# O'qituvchi tokenidagi publish ruxsatlari (LiveKit `canPublishSources`)
TEACHER_PUBLISH_SOURCES = ('camera', 'microphone', 'screen_share', 'screen_share_audio')

ATTENTION_WINDOW_SEC = 15  # popup ekranda turadigan vaqt (EduTech.docx)
ATTENTION_GRACE_SEC = 8    # tarmoq kechikishi uchun qo'shimcha imkon

# Ulanish navbati (FIFO, cheklangan parallellik) — production'da o'lchangan
# (2026-09-02): bir darsga qisqa vaqt ichida ko'p o'quvchi ulansa, LiveKit'da
# CPU 5-8x portlaydi (har biri ICE/DTLS muzokarasini bir vaqtda boshlaydi).
# Bir vaqtda faqat _JOIN_QUEUE_BATCH_SIZE kishi ulansa, portlash deyarli
# yo'qoladi (sinovda: ~520% -> ~180%, ya'ni deyarli barqaror holat darajasi).
#
# DIQQAT: navbat DARS bo'yicha EMAS — butun server uchun BITTA (global).
# Sabab: LiveKit CPU'siga bitta darsning o'z ichidagi ulanishlari HAM,
# turli darslarning bir vaqtda boshlanishi HAM (masalan hammasi soat
# 18:00da) bir xil ta'sir qiladi — muhimi jami parallel muzokaralar soni,
# qaysi darsga tegishli ekani emas. Lesson-bo'yicha alohida navbat bitta
# darsni yaxshi silliqlaydi, lekin 150 ta TURLI dars bir vaqtda
# boshlansa, har birining BIRINCHI partiyasi baribir ustma-ust tushib
# qolar edi — global kalit buni ham qamrab oladi.
_JOIN_QUEUE_WINDOW_SECONDS = 15  # shu vaqt jim tursa navbat o'zi nolga qaytadi
_JOIN_QUEUE_BATCH_SIZE = 6
_JOIN_QUEUE_BATCH_INTERVAL_MS = 1200
# 2026-09-04: qat'iy CHEGARA (masalan 20s) ATAYLAB YO'Q — chegara qo'ysak,
# chegaraga yetgan HAMMASI o'sha nuqtaning o'zida (yoki hatto tasodifiy
# tarqatilgan tor oynada ham) zichlashib qolib, aynan oldini olishga
# harakat qilingan portlashning o'zini qayta yaratardi, faqat kechiktirilgan
# holda. Kechikish CHEKLANMAGAN o'sib boradi — bu safar HAR DOIM (N qancha
# katta bo'lmasin) xavfsiz tezlikda (6 kishi/1.2s, sinovda tasdiqlangan)
# ulanadi. Narxi: o'ta ekstremal portlashda (yuzlab kishi bir vaqtda) oxirgi
# kishi ancha kutishi mumkin — lekin server hech qachon xavf ostida qolmaydi.


def _compute_join_delay_ms() -> int:
    """FIFO navbat pozitsiyasini hisoblaydi (BUTUN SERVER bo'yicha, dars
    farqlanmaydi): kim OLDIN so'rasa, kichikroq pozitsiya oladi (Django
    keshining atomik `incr()`i — Redis'da bu haqiqatan atomik, poyga
    holati yo'q). Pozitsiya `_JOIN_QUEUE_BATCH_SIZE` kishilik
    partiyalarga bo'linadi, har partiya oldingisidan
    `_JOIN_QUEUE_BATCH_INTERVAL_MS` keyin ulanadi — CHEKLANMAGAN (qancha
    katta N bo'lmasin, bir xil xavfsiz tezlik saqlanadi). Kalit o'zi
    `_JOIN_QUEUE_WINDOW_SECONDS` jim turgach eskiradi — portlashsiz,
    kam-kam kelayotgan so'rovlarga deyarli tegilmaydi."""
    key = 'live:join_queue:global'
    try:
        position = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=_JOIN_QUEUE_WINDOW_SECONDS)
        position = 1
    return ((position - 1) // _JOIN_QUEUE_BATCH_SIZE) * _JOIN_QUEUE_BATCH_INTERVAL_MS


def issue_room_token(*, user: User, lesson_id, request=None) -> dict:
    """Dars xonasiga kirish tokeni.

    Faqat kurs o'qituvchisi yoki yozilgan o'quvchi. O'quvchiga davomat bosiladi
    (FRD: attendance.auto_mark), o'qituvchi kirsa dars LIVE bo'ladi.
    """
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))

    is_teacher = lesson.course.teacher_id == user.id
    is_enrolled = lesson.course.enrollments.filter(
        student=user, status=Enrollment.Status.APPROVED,
    ).exists()
    if not (is_teacher or is_enrolled):
        raise PermissionDenied(_("Bu darsga kirish huquqingiz yo'q."))
    if not is_teacher and LessonBan.objects.filter(lesson=lesson, student=user).exists():
        raise PermissionDenied(_("Siz bu darsdan chetlashtirilgansiz."))
    if lesson.status in (Lesson.Status.FINISHED, Lesson.Status.CANCELLED):
        raise ValidationError(_('Dars tugagan yoki bekor qilingan.'))
    # Bugun/kelajakka rejalashtirilgan darsga istalgan vaqt kirish mumkin
    # (aniq soatini kutish shart emas). Faqat KUNI allaqachon o'tib ketgan,
    # hech qachon boshlanmagan (hamon SCHEDULED) darslar bloklanadi — aks
    # holda ular abadiy "kirish mumkin" bo'lib qolar edi. Frontend tugmani
    # ham shu qoidaga ko'ra o'chiradi (apps/live/services.py bilan bir xil
    # mantiq — lekin bu yerda HAQIQIY himoya: to'g'ridan-to'g'ri havola
    # orqali chetlab o'tib bo'lmaydi).
    if lesson.status == Lesson.Status.SCHEDULED:
        local_now = timezone.localtime(timezone.now())
        local_starts_at = timezone.localtime(lesson.starts_at)
        if local_starts_at.date() < local_now.date():
            raise ValidationError(_("Bu darsning vaqti allaqachon o'tib ketgan."))

    # KRITIK XATO (2026-09-05 topilgan, ikki ishtirokchi bilan haqiqiy sinovda):
    # `can_publish_sources=[]` (bo'sh ro'yxat) LiveKit'da "cheklov YO'Q, hamma
    # manba OCHIQ" degani — "hech narsa mumkin emas" EMAS (rasmiy hujjatda
    # tasdiqlangan: https://docs.livekit.io/frontends/reference/tokens-grants/).
    # Ya'ni oldingi kod ("2026-09-04: kamera ham cheklandi" izohi bilan)
    # noto'g'ri taxminga asoslangan edi — `can_publish=True` + bo'sh
    # `can_publish_sources` kombinatsiyasi o'quvchiga darsga kirgan ZAHOTI
    # mikrofon, kamera VA ekran ulashishni TO'LIQ CHEKLOVSIZ ochib bergan,
    # grant_mic()/grant_camera()/grant_screen_share() esa amalda hech narsani
    # QO'SHIMCHA cheklamagan (cheklov boshidanoq yo'q edi). Endi o'quvchi uchun
    # `can_publish` butunlay YOPIQ boshlanadi — grant_*() funksiyalari uni
    # (aynan kerakli manba bilan birga) ANIQ ochadi.
    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(f'user-{user.id}')
        .with_name(user.get_full_name() or user.username)
        # 2026-09-05 topilgan: dars 2 soat davom etishi mumkin (yoki undan
        # biroz oshib ketishi) — token muddati AYNAN 2 soat bo'lsa, dars
        # oxiriga yaqin muddat tugab qolishi mumkin edi. LiveKit ulangan
        # klientga proaktiv yangi token yuboradi (uzilish bo'lmaydi), lekin
        # muddat tugagandan KEYIN qisqa tarmoq uzilishi + qayta ulanish bir
        # vaqtga to'g'ri kelsa — nazariy jihatdan xato berishi mumkin. Katta
        # zaxira bilan bu xavfni butunlay yo'qotamiz (hech qanday zarari yo'q).
        .with_ttl(timedelta(hours=8))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=lesson.room_name,
                room_admin=is_teacher,
                can_publish=is_teacher,
                can_subscribe=True,
                # O'qituvchi: manbalar ANIQ yozilgan (bo'sh/None "hammasi mumkin" degani, lekin mobil mijoz
                # `canPublishSources` ni o'qib mikrofon/kamera tugmalarini o'chirib qo'yardi)
                can_publish_sources=list(TEACHER_PUBLISH_SOURCES) if is_teacher else [],
            )
        )
    )

    if is_teacher and lesson.status == Lesson.Status.SCHEDULED:
        lesson.status = Lesson.Status.LIVE
        lesson.live_started_at = timezone.now()
        lesson.save(update_fields=['status', 'live_started_at'])
        # Guruh chatga "jonli dars boshlandi" signali (Telegram uslubidagi
        # guruh video chat chizig'i). Xato bo'lsa ham darsga kirish to'xtamasin.
        try:
            from apps.chat import realtime as chat_realtime
            chat_realtime.broadcast_lesson_live(lesson)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('lesson_live broadcast failed')
    elif is_teacher and lesson.status == Lesson.Status.LIVE:
        # 2026-09-04 tuzatildi: `live_started_at` avval FAQAT birinchi marta
        # LIVE'ga o'tganda yozilardi. O'qituvchi darsni tark etib (masalan
        # sahifani yopib), SOATLAR o'tib qaytadan kirsa — eski vaqt hamon
        # o'sha-o'sha qolganidan, auto_finish_expired_lessons darhol (yoki
        # keyingi cron aylanishida, 1-2 daqiqa ichida) uni "muddati o'tgan"
        # deb topib yopib qo'yardi — aynan qayta kirgan zahoti. Endi
        # o'qituvchi HAR safar kirganda bu vaqt yangilanadi — soat faqat
        # o'qituvchi CHINDAN uzoq vaqt (75+ daqiqa) qaytmasa ishga tushadi.
        lesson.live_started_at = timezone.now()
        lesson.save(update_fields=['live_started_at'])
    if user.role == User.Role.STUDENT:
        lesson_services.mark_joined(lesson=lesson, student=user)
        _ensure_attention_schedule(lesson=lesson, student=user)

    audit.record(action='room.join', actor=user, target=lesson, request=request)
    # O'qituvchi hech qachon kutmaydi — dars boshlanishi kechikmasin.
    join_delay_ms = 0 if is_teacher else _compute_join_delay_ms()
    return {
        'token': token.to_jwt(),
        'url': settings.LIVEKIT_URL,
        'room': lesson.room_name,
        'is_teacher': is_teacher,
        'join_delay_ms': join_delay_ms,
    }


def leave_room(*, user: User, lesson_id, request=None) -> bool:
    updated = lesson_services.mark_left(lesson_id=lesson_id, student=user)
    if updated:
        audit.record(action='room.leave', actor=user, meta={'lesson_id': str(lesson_id)}, request=request)
    return updated


# ── "Siz shu yerdamisiz?" — diqqat tekshiruvi ──────────────────────────────

def _ensure_attention_schedule(*, lesson: Lesson, student: User):
    """Dars oynasi ichida 3-5 ta tasodifiy tekshiruv vaqti yaratadi (server tomonda —
    o'quvchi jadvalni oldindan ko'ra olmaydi)."""
    if AttentionCheck.objects.filter(lesson=lesson, student=student).exists():
        return
    now = timezone.now()
    end = lesson.starts_at + timedelta(minutes=lesson.duration_min)
    start = max(now + timedelta(minutes=1), lesson.starts_at)
    window = (end - start).total_seconds()
    if window < 120:  # dars deyarli tugagan — tekshiruv qo'yilmaydi
        return
    count = random.randint(3, 5)
    offsets = sorted(random.sample(range(30, int(window) - 30), k=count))
    AttentionCheck.objects.bulk_create([
        AttentionCheck(lesson=lesson, student=student, due_at=start + timedelta(seconds=o))
        for o in offsets
    ])


def pending_attention(*, user: User, lesson_id) -> AttentionCheck | None:
    """Hozir ko'rsatilishi kerak bo'lgan tekshiruv (15s oynasi ichida, javobsiz)."""
    now = timezone.now()
    return AttentionCheck.objects.filter(
        lesson_id=lesson_id, student=user, answered_at__isnull=True,
        due_at__lte=now, due_at__gt=now - timedelta(seconds=ATTENTION_WINDOW_SEC),
    ).first()


def answer_attention(*, user: User, check_id) -> AttentionCheck:
    try:
        check = AttentionCheck.objects.get(pk=check_id, student=user)
    except (AttentionCheck.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Tekshiruv topilmadi.'))
    now = timezone.now()
    deadline = check.due_at + timedelta(seconds=ATTENTION_WINDOW_SEC + ATTENTION_GRACE_SEC)
    if check.answered_at is not None:
        return check
    if now > deadline:
        raise ValidationError(_('Vaqt tugadi — bu tekshiruv o\'tkazib yuborilgan.'))
    check.answered_at = now
    check.save(update_fields=['answered_at'])
    return check


# ── Anti-cheat: fokus jurnali ──────────────────────────────────────────────

def record_focus(*, user: User, lesson_id, kind: str) -> dict:
    """Chiqib-kirishni yozadi. 'exit' bo'lsa shu darsdagi jami chiqishlar soni va
    ogohlantirish darajasini qaytaradi: threshold'gacha — o'quvchining o'ziga
    ogohlantirish, threshold'da (bir marta) — ota-onaga FocusAlert yaratiladi.
    """
    if kind not in FocusEvent.Kind.values:
        raise ValidationError({'kind': _('exit yoki return.')})
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    event = FocusEvent.objects.create(lesson=lesson, student=user, kind=kind)

    # O'qituvchiga darhol ko'rinishi kerak (burchakda "diqqat qilmayapti"
    # belgisi) — doska WebSocket kanali orqali (dars davomida hamma shunga
    # ulangan, yangi ulanish ochish shart emas). Xato broadcast qilmasin.
    try:
        from apps.board import realtime as board_realtime
        board_realtime.broadcast_focus(
            lesson_id, student_id=str(user.id),
            name=user.first_name or user.username, kind=kind,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('focus broadcast failed')

    if kind != FocusEvent.Kind.EXIT:
        return {'kind': kind, 'exit_count': None, 'threshold': None, 'parent_notified': False}

    exit_count = FocusEvent.objects.filter(
        lesson=lesson, student=user, kind=FocusEvent.Kind.EXIT,
    ).count()
    threshold = settings.FOCUS_PARENT_ALERT_THRESHOLD
    parent_notified = exit_count >= threshold
    if parent_notified:
        # Faqat birinchi chegaradan oshgan safar yaratiladi — spam bo'lmasin
        FocusAlert.objects.get_or_create(
            lesson=lesson, student=user, defaults={'exit_count': exit_count},
        )
    return {
        'kind': event.kind, 'exit_count': exit_count,
        'threshold': threshold, 'parent_notified': parent_notified,
    }


def away_students(lesson: Lesson) -> list[dict]:
    """Hozir darsdan "chiqib ketgan" (oynadan chiqib, hali qaytmagan)
    o'quvchilar — o'qituvchi doskani (qayta) ochganda darhol ko'rishi uchun
    (WebSocket ulanishidan oldingi holatni ham qamrab oladi)."""
    # Faqat "o'zidan keyin hodisa yo'q chiqish" — ya'ni o'quvchining OXIRGI hodisasi chiqish bo'lganlar. Bazada filtrlanadi:
    # javobda faqat hozir chiqib turganlar (bir necha o'quvchi), butun jurnal (minglab qator) emas.
    later = FocusEvent.objects.filter(
        lesson=lesson, student=OuterRef('student'), created_at__gt=OuterRef('created_at'),
    )
    rows = (
        FocusEvent.objects.filter(lesson=lesson, kind=FocusEvent.Kind.EXIT)
        .annotate(has_later=Exists(later)).filter(has_later=False)
        .select_related('student').order_by('created_at')
    )
    names = {e.student_id: e.student.first_name or e.student.username for e in rows}
    return [{'student_id': str(sid), 'name': name} for sid, name in names.items()]


def request_mic(*, user: User, lesson_id, request=None) -> None:
    """O'quvchi mikrofon so'raydi ("qo'l ko'tarish").

    Bazaga ham yoziladi (MicRequest, idempotent — qayta so'rasa dublikat
    yaratilmaydi), NA FAQAT WebSocket orqali yuboriladi — shu sabab
    o'qituvchi so'rovdan keyin kirsa yoki sahifani yangilasa ham,
    `pending_mic_requests()` orqali joriy holat qayta tiklanadi.
    """
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    is_enrolled = lesson.course.enrollments.filter(
        student=user, status=Enrollment.Status.APPROVED,
    ).exists()
    if not is_enrolled:
        raise PermissionDenied(_("Bu darsga kirish huquqingiz yo'q."))

    from apps.lessons.models import MicRequest
    MicRequest.objects.get_or_create(lesson=lesson, student=user)

    try:
        from apps.board import realtime as board_realtime
        board_realtime.broadcast_mic_request(
            lesson_id, student_id=str(user.id),
            name=user.first_name or user.username,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('mic_request broadcast failed')

    audit.record(action='room.mic_request', actor=user, target=lesson, request=request)


def pending_mic_requests(lesson: Lesson) -> list[dict]:
    """Hozir javob kutilayotgan mikrofon so'rovlari — o'qituvchi doskani
    (qayta) ochganda darhol ko'rishi uchun (WebSocket ulanishidan oldingi
    yoki undan keyingi holatni ham qamrab oladi)."""
    from apps.lessons.models import MicRequest

    requests = MicRequest.objects.filter(lesson=lesson).select_related('student')
    return [
        {'student_id': str(r.student_id), 'name': r.student.first_name or r.student.username}
        for r in requests
    ]


# ── Kamera ruxsati (2026-09-04: mikrofon bilan bir xil naqsh — avval erkin edi) ──

def _cancel_media_request(*, kind: str, user: User, lesson_id, request=None) -> bool:
    """O'quvchi o'zining kutayotgan mikrofon/kamera so'rovini bekor qiladi (idempotent). Qaytaradi: bekor qilingan-qilinmagani."""
    from apps.board import realtime as board_realtime
    from apps.lessons.models import CameraRequest, MicRequest

    model, broadcast = (
        (MicRequest, board_realtime.broadcast_mic_request_cancelled) if kind == 'mic'
        else (CameraRequest, board_realtime.broadcast_camera_request_cancelled)
    )
    if not _is_uuid(lesson_id):
        raise NotFound(_('Dars topilmadi.'))
    deleted, _details = model.objects.filter(lesson_id=lesson_id, student=user).delete()
    if deleted:
        try:
            broadcast(lesson_id, student_id=str(user.id))
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('%s request cancel broadcast failed', kind)
        audit.record(action=f'room.{kind}_request_cancel', actor=user, request=request)
    return bool(deleted)


def cancel_mic_request(*, user: User, lesson_id, request=None) -> bool:
    return _cancel_media_request(kind='mic', user=user, lesson_id=lesson_id, request=request)


def cancel_camera_request(*, user: User, lesson_id, request=None) -> bool:
    return _cancel_media_request(kind='camera', user=user, lesson_id=lesson_id, request=request)


def request_camera(*, user: User, lesson_id, request=None) -> None:
    """O'quvchi kamera so'raydi. `request_mic` bilan bir xil naqsh."""
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    is_enrolled = lesson.course.enrollments.filter(
        student=user, status=Enrollment.Status.APPROVED,
    ).exists()
    if not is_enrolled:
        raise PermissionDenied(_("Bu darsga kirish huquqingiz yo'q."))

    from apps.lessons.models import CameraRequest
    CameraRequest.objects.get_or_create(lesson=lesson, student=user)

    try:
        from apps.board import realtime as board_realtime
        board_realtime.broadcast_camera_request(
            lesson_id, student_id=str(user.id),
            name=user.first_name or user.username,
        )
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('camera_request broadcast failed')

    audit.record(action='room.camera_request', actor=user, target=lesson, request=request)


def pending_camera_requests(lesson: Lesson) -> list[dict]:
    from apps.lessons.models import CameraRequest

    requests = CameraRequest.objects.filter(lesson=lesson).select_related('student')
    return [
        {'student_id': str(r.student_id), 'name': r.student.first_name or r.student.username}
        for r in requests
    ]


def grant_camera(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """O'qituvchi o'quvchiga kamera ruxsatini jonli ochadi — `grant_mic` bilan
    bir xil naqsh, mavjud ruxsatlarni (mikrofon/ekran) saqlab qolib qo'shadi."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))

    identity = f'user-{student.id}'

    async def _update():
        from livekit.protocol.room import RoomParticipantIdentity

        client = LiveKitAPI(
            url=_livekit_http_url(),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            info = await client.room.get_participant(RoomParticipantIdentity(
                room=lesson.room_name, identity=identity,
            ))
            sources = set(info.permission.can_publish_sources) | {TrackSource.CAMERA}
            await client.room.update_participant(UpdateParticipantRequest(
                room=lesson.room_name,
                identity=identity,
                permission=ParticipantPermission(
                    can_subscribe=True,
                    can_publish=True,
                    can_publish_data=True,
                    can_publish_sources=list(sources),
                ),
            ))
        finally:
            await client.aclose()

    asyncio.run(_update())

    from apps.lessons.models import CameraRequest
    CameraRequest.objects.filter(lesson=lesson, student=student).delete()

    try:
        from apps.board import realtime as board_realtime
        board_realtime.broadcast_camera_granted(lesson_id, student_id=str(student.id))
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('camera_granted broadcast failed')

    audit.record(
        action='room.grant_camera', actor=teacher, target=lesson,
        meta={'student_id': str(student.id)}, request=request,
    )
    return True


def deny_camera(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """O'qituvchi kamera so'rovini rad etadi — `deny_mic` bilan bir xil naqsh."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))

    from apps.lessons.models import CameraRequest
    deleted, _ = CameraRequest.objects.filter(lesson=lesson, student=student).delete()

    if deleted:
        try:
            from apps.board import realtime as board_realtime
            board_realtime.broadcast_camera_denied(lesson_id, student_id=str(student.id))
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('camera_denied broadcast failed')

        audit.record(
            action='room.deny_camera', actor=teacher, target=lesson,
            meta={'student_id': str(student.id)}, request=request,
        )
    return bool(deleted)


# ── Ekran share ruxsati (o'qituvchi beradi) ────────────────────────────────

def _livekit_http_url() -> str:
    """Server-server API chaqiriqlari uchun LiveKit manzili.

    LIVEKIT_API_URL berilgan bo'lsa — o'sha (prod: docker tarmog'i ichidan
    http://livekit:7880 — Caddy/TLS orqali aylanib yurmaydi). Bo'lmasa
    LIVEKIT_URL'dan hosil qilinadi (dev).
    """
    api_url = getattr(settings, 'LIVEKIT_API_URL', '')
    if api_url:
        return api_url
    return settings.LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://')


def grant_screen_share(*, teacher: User, lesson_id, identity: str, request=None) -> bool:
    """O'qituvchi o'quvchiga ekran ulashish ruxsatini jonli ochadi (LiveKit server
    API) — `grant_mic`/`grant_camera` bilan bir xil naqsh: mavjud ruxsatlarni
    (mikrofon/kamera) saqlab qolib, ustiga faqat ekran ulashishni qo'shadi.

    XATO EDI (2026-09-05 topilgan, ikki ishtirokchi bilan haqiqiy sinovda):
    avval bu funksiya butun ro'yxatni [CAMERA, MICROPHONE, SCREEN_SHARE,
    SCREEN_SHARE_AUDIO] bilan QATTIQ ALMASHTIRARDI — ya'ni o'qituvchi FAQAT
    ekran ulashishga ruxsat bermoqchi bo'lsa ham, o'quvchiga BEXOSDAN kamera
    va mikrofonni HAM ochib yuborardi (yoki oldin faqat mikrofon berilgan
    bo'lsa, uni ekran ulashish ruxsati BILAN ALMASHTIRIB, mikrofonni yo'qotib
    qo'yardi — chunki `update_participant` ro'yxatni to'liq ALMASHTIRADI,
    qo'shmaydi)."""
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi ruxsat beradi."))

    async def _update():
        from livekit.protocol.room import RoomParticipantIdentity

        client = LiveKitAPI(
            url=_livekit_http_url(),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            info = await client.room.get_participant(RoomParticipantIdentity(
                room=lesson.room_name, identity=identity,
            ))
            sources = set(info.permission.can_publish_sources) | {
                TrackSource.SCREEN_SHARE, TrackSource.SCREEN_SHARE_AUDIO,
            }
            await client.room.update_participant(UpdateParticipantRequest(
                room=lesson.room_name,
                identity=identity,
                permission=ParticipantPermission(
                    can_subscribe=True,
                    can_publish=True,
                    can_publish_data=True,
                    can_publish_sources=list(sources),
                ),
            ))
        finally:
            await client.aclose()

    asyncio.run(_update())
    audit.record(
        action='room.allow_share', actor=teacher, target=lesson,
        meta={'identity': identity}, request=request,
    )
    return True


def grant_mic(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """O'qituvchi o'quvchiga mikrofon ruxsatini jonli ochadi (LiveKit server
    API) — (agar oldin berilgan bo'lsa) kamera/ekran ulashish ruxsatini
    saqlab qolib, ustiga mikrofonni qo'shadi."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))

    identity = f'user-{student.id}'

    async def _update():
        from livekit.protocol.room import RoomParticipantIdentity

        client = LiveKitAPI(
            url=_livekit_http_url(),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            # Joriy ruxsatlarni o'qib, ustiga mikrofonni QO'SHAMIZ — agar
            # oldin ekran ulashish berilgan bo'lsa, uni tasodifan olib
            # tashlab qo'ymaslik uchun (update_participant butun ro'yxatni
            # ALMASHTIRADI, qo'shmaydi).
            info = await client.room.get_participant(RoomParticipantIdentity(
                room=lesson.room_name, identity=identity,
            ))
            sources = set(info.permission.can_publish_sources) | {TrackSource.MICROPHONE}
            await client.room.update_participant(UpdateParticipantRequest(
                room=lesson.room_name,
                identity=identity,
                permission=ParticipantPermission(
                    can_subscribe=True,
                    can_publish=True,
                    can_publish_data=True,
                    can_publish_sources=list(sources),
                ),
            ))
        finally:
            await client.aclose()

    asyncio.run(_update())

    from apps.lessons.models import MicRequest
    MicRequest.objects.filter(lesson=lesson, student=student).delete()

    try:
        from apps.board import realtime as board_realtime
        board_realtime.broadcast_mic_granted(lesson_id, student_id=str(student.id))
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('mic_granted broadcast failed')

    audit.record(
        action='room.grant_mic', actor=teacher, target=lesson,
        meta={'student_id': str(student.id)}, request=request,
    )
    return True


def deny_mic(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """O'qituvchi mikrofon so'rovini rad etadi — LiveKit ruxsati BERILMAYDI,
    faqat navbatdagi so'rov o'chiriladi. So'rov hal bo'lgani uchun (o'chirilgani
    uchun) o'quvchi keyin yana so'ray oladi."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))

    from apps.lessons.models import MicRequest
    deleted, _ = MicRequest.objects.filter(lesson=lesson, student=student).delete()

    if deleted:
        try:
            from apps.board import realtime as board_realtime
            board_realtime.broadcast_mic_denied(lesson_id, student_id=str(student.id))
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('mic_denied broadcast failed')

        audit.record(
            action='room.deny_mic', actor=teacher, target=lesson,
            meta={'student_id': str(student.id)}, request=request,
        )
    return bool(deleted)


# ── Taklif va chetlashtirish (Zoom uslubidagi invite/ban) ──────────────────

def mute_all(*, teacher: User, lesson_id, except_ids=None, request=None) -> int:
    """O'qituvchi hamma ishtirokchining (o'zi va `except_ids` dan tashqari) mikrofonini o'chiradi (LiveKit server API).
    Mikrofon ruxsati olinmaydi — o'quvchi xohlasa qayta yoqa oladi. Qaytaradi: ovozi o'chirilgan ishtirokchilar soni."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    skip = {f'user-{teacher.id}'} | {f'user-{i}' for i in (except_ids or [])}

    async def _mute() -> int:
        from livekit.protocol.models import TrackType
        from livekit.protocol.room import ListParticipantsRequest, MuteRoomTrackRequest

        client = LiveKitAPI(
            url=_livekit_http_url(), api_key=settings.LIVEKIT_API_KEY, api_secret=settings.LIVEKIT_API_SECRET,
        )
        muted = set()
        try:
            listing = await client.room.list_participants(ListParticipantsRequest(room=lesson.room_name))
            for participant in listing.participants:
                if participant.identity in skip:
                    continue
                for track in participant.tracks:
                    if track.type == TrackType.AUDIO and not track.muted:
                        await client.room.mute_published_track(MuteRoomTrackRequest(
                            room=lesson.room_name, identity=participant.identity, track_sid=track.sid, muted=True,
                        ))
                        muted.add(participant.identity)
        finally:
            await client.aclose()
        return len(muted)

    try:
        count = asyncio.run(_mute())
    except Exception as exc:  # noqa: BLE001 — LiveKit xatosi (xona yo'q, server javob bermadi) mijozga tafsilotsiz
        import logging

        logging.getLogger('apps').warning('mute_all LiveKit xatosi: %s', exc)
        if lesson.status != Lesson.Status.LIVE:
            return 0  # dars jonli emas — ovozi o'chiradigan hech kim yo'q
        raise ValidationError({'detail': _("Jonli dars serveriga ulanib bo'lmadi. Birozdan keyin urinib ko'ring.")}) from None
    audit.record(
        action='room.mute_all', actor=teacher, target=lesson, meta={'muted': count}, request=request,
    )
    return count


def lesson_presence(*, user: User, lesson_id) -> dict:
    """"N kishi darsda": hozir xonada bo'lganlar (kirgan va hali chiqmagan o'quvchilar + dars jonli bo'lsa o'qituvchi)
    va ularning avatarlari (ko'pi bilan 5 ta)."""
    from apps.lessons import selectors as lesson_selectors

    lesson = lesson_selectors.lessons_for(user).select_related('course', 'course__teacher').filter(pk=lesson_id).first() \
        if _is_uuid(lesson_id) else None
    if lesson is None:
        raise NotFound(_('Dars topilmadi.'))
    people = [
        row.student for row in
        lesson.attendances.filter(joined_at__isnull=False, left_at__isnull=True).select_related('student')
    ]
    if lesson.status == Lesson.Status.LIVE:
        people.insert(0, lesson.course.teacher)
    avatars = [person.avatar.url for person in people if person.avatar][:5]
    return {'count': len(people), 'avatars': avatars}


def lesson_waiting(*, user: User, lesson_id) -> dict:
    """Darsga kirish ekrani ("7 / 9 o'quvchi kutmoqda"): xonaga allaqachon kirgan, hali chiqmagan o'quvchilar.
    `students` (ism va avatar) — faqat kurs o'qituvchisiga; o'quvchiga faqat sonlar."""
    from apps.lessons import selectors as lesson_selectors

    lesson = lesson_selectors.lessons_for(user).select_related('course').filter(pk=lesson_id).first() \
        if _is_uuid(lesson_id) else None
    if lesson is None:
        raise NotFound(_('Dars topilmadi.'))
    people = [
        row.student for row in
        lesson.attendances.filter(joined_at__isnull=False, left_at__isnull=True).select_related('student')
        .order_by('joined_at')
    ]
    total = Enrollment.objects.filter(course=lesson.course, status=Enrollment.Status.APPROVED).count()
    data = {'waiting_count': len(people), 'total_count': total, 'students': []}
    if lesson.course.teacher_id == user.id:
        data['students'] = [{
            'id': str(person.id), 'name': person.get_full_name() or person.username,
            'avatar': person.avatar.url if person.avatar else None,
        } for person in people]
    return data


def lesson_signals(*, teacher: User, lesson_id) -> dict:
    """O'qituvchi uchun YENGIL holat: oynadan chiqib ketgan o'quvchilar va javob kutayotgan mikrofon/kamera so'rovlari.
    Ilgari frontend buni butun doskani (yuzlab kilobayt) har 2 soniyada so'rab olardi."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    return {
        'away_students': away_students(lesson),
        'pending_mic_requests': pending_mic_requests(lesson),
        'pending_camera_requests': pending_camera_requests(lesson),
    }


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _get_owned_lesson(*, teacher: User, lesson_id) -> Lesson:
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi shu amalni bajara oladi."))
    return lesson


def invite_to_lesson(*, teacher: User, lesson_id, student_id=None, request=None) -> int:
    """O'quvchiga (yoki student_id berilmasa — kursga APPROVED yozilgan
    HAMMAGA) "dars boshlandi, kiring" bildirishnomasini yuboradi.

    Faqat ogohlantirish — o'quvchi xonaga baribir o'zi token so'rab kiradi
    (room.token ruxsati bo'lsa allaqachon kira oladi); bu shunchaki uni
    xabardor qiladi.
    """
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)

    qs = lesson.course.enrollments.filter(status=Enrollment.Status.APPROVED).select_related('student')
    if student_id:
        qs = qs.filter(student_id=student_id)
        if not qs.exists():
            raise NotFound(_("O'quvchi bu kursga yozilmagan."))
    students = [e.student for e in qs]
    if not students:
        return 0

    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    description = f'«{lesson.title or lesson.course.title}» darsi boshlandi — hoziroq kiring.'
    for student in students:
        send_notification(
            sender=teacher, description=description,
            target_type=Notification.Target.USER, user_id=student.id, request=request,
        )
    audit.record(
        action='lesson.invite', actor=teacher, target=lesson,
        meta={'student_count': len(students)}, request=request,
    )
    return len(students)


def ban_participant(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """O'quvchini darsdan chetlashtiradi: hozir xonada bo'lsa darhol chiqarib
    yuboradi (LiveKit), va LessonBan yaratib qayta kirishini bloklaydi
    (issue_room_token shu jadvalni tekshiradi). Talaba hozir ulanmagan
    bo'lsa ham — ban baribir saqlanadi, keyingi token so'rovi rad etiladi.
    """
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))

    LessonBan.objects.get_or_create(lesson=lesson, student=student, defaults={'banned_by': teacher})

    async def _remove():
        from livekit.protocol.room import RoomParticipantIdentity

        client = LiveKitAPI(
            url=_livekit_http_url(),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            await client.room.remove_participant(RoomParticipantIdentity(
                room=lesson.room_name, identity=f'user-{student.id}',
            ))
        finally:
            await client.aclose()

    try:
        asyncio.run(_remove())
    except Exception:  # noqa: BLE001 — talaba hozir xonada bo'lmasligi mumkin, ban baribir saqlandi
        import logging
        logging.getLogger('apps').info('ban_participant: xonadan chiqarib bo\'lmadi (ulanmagan bo\'lishi mumkin)')

    audit.record(
        action='room.ban', actor=teacher, target=lesson,
        meta={'student_id': str(student.id)}, request=request,
    )
    return True


def unban_participant(*, teacher: User, lesson_id, student_id, request=None) -> bool:
    """Chetlashtirishni bekor qiladi — o'quvchi qayta token so'rab kira oladi."""
    lesson = _get_owned_lesson(teacher=teacher, lesson_id=lesson_id)
    deleted, _ = LessonBan.objects.filter(lesson=lesson, student_id=student_id).delete()
    if deleted:
        audit.record(
            action='room.unban', actor=teacher, target=lesson,
            meta={'student_id': str(student_id)}, request=request,
        )
    return bool(deleted)


# ── Dars video yozuvi (brauzerdan video + audio, chunked upload) ───────────
# EduTech.docx: "dars video zapisi avtomatik saqlansin — o'qituvchi guruhni
# o'chirmaguncha". 2026-08-28 optimallashtirish, 2-bosqich: video ENDI HAM
# server-tomon Track Egress orqali EMAS — audio kabi TO'LIQ o'qituvchi
# brauzeridan keladi. Sabab: Track Egress FAQAT bitta trackni (kamera YOKI
# ekran) yoza olardi, dars davomida almashtirishni qo'llab-quvvatlamas edi.
# Brauzerning o'zi ekranini (`getDisplayMedia` — LiveKit sahifasining o'zi,
# "print screen" kabi) yozib olsa — kim gapirsa, kim ekran ulashsa, kim
# kamerasini yoqsa — HAMMASI tabiiy ravishda ko'rinadi, serverda tanlov/
# almashtirish mantig'i kerak emas, va CPU endi VIDEO uchun HAM deyarli 0.
#
# Video va audio ikkalasi ham bo'lak-bo'lak (chunk) yuklanadi (apps.lessons
# .services.upload_recording_video_chunk/upload_recording_audio_chunk).
# Ikkalasi ham tayyor bo'lgach, fon jarayonida `ffmpeg`da vaqt farqiga
# moslab (qayta kodlashsiz) WebM faylga birlashtiriladi. Faqat BITTASI
# kelsa (ikkinchisi hech qachon kelmasa — brauzer qulab qolgan, ruxsat
# berilmagan) — MAVJUD bo'lgani bilan yakunlanadi, butunlay yo'qotilmaydi.
#
# 2026-09-05: avval har bir merge uchun cheklovsiz `threading.Thread`
# ochilardi — yuzlab dars bir vaqtda (masalan hammasi 18:00da) tugasa,
# yuzlab thread + ffmpeg protsess + DB ulanish bir zumda ochilib ketardi
# (backpressure yo'q). Endi belgilangan sondagi worker'li navbat orqali —
# ortiqchasi navbatda kutadi, server bir vaqtning o'zida zarba yemaydi.
_MERGE_WORKERS = int(os.environ.get('RECORDING_MERGE_WORKERS', '8'))
_merge_executor = ThreadPoolExecutor(max_workers=_MERGE_WORKERS, thread_name_prefix='recording-merge')


def _run_merge_in_pool(recording_pk) -> None:
    """`_merge_executor`ga yuboriladigan qobiq — pool'dagi thread QAYTA
    ISHLATILADI (bir martalik `threading.Thread`dan farqli), shuning uchun
    oldingi vazifadan qolgan Django DB ulanishi shu yerda tozalanadi
    ("the connection is closed" xatosining oldi olinadi). `_merge_recording`
    o'zi buni bilmaydi — u to'g'ridan-to'g'ri (masalan testlarda, joriy
    thread/tranzaksiyada) ham chaqirilishi mumkin, shu sabab tozalash
    faqat SHU qobiqda, pool orqali ishga tushganda qo'llanadi."""
    from django.db import close_old_connections

    close_old_connections()
    try:
        _merge_recording(recording_pk)
    finally:
        close_old_connections()


def end_room(lesson: Lesson) -> None:
    """LiveKit xonasini BUTUNLAY o'chiradi — barcha ishtirokchilarni (video/
    audio) bir vaqtda uzadi. Dars rejalashtirilgan vaqti tugab, avtomatik
    yakunlanganda ishlatiladi (apps.lessons.services.auto_finish_expired_lessons) —
    o'qituvchi qo'lda "tugatish"ni bosmagan bo'lsa ham, xona cheksiz ochiq
    qolib ketmasin. Xona allaqachon bo'sh/yo'q bo'lsa ham xato bermaydi
    (best-effort)."""
    import logging

    async def _delete():
        from livekit.protocol.room import DeleteRoomRequest

        client = LiveKitAPI(
            url=_livekit_http_url(),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            await client.room.delete_room(DeleteRoomRequest(room=lesson.room_name))
        finally:
            await client.aclose()

    try:
        asyncio.run(_delete())
    except Exception as exc:  # noqa: BLE001 — xona allaqachon yo'q bo'lishi mumkin
        logging.getLogger('apps').info('end_room: %s', exc)


def maybe_start_merge(lesson_id) -> None:
    """Video va audio (ikkalasi ham brauzerdan yuklangan) tayyor bo'lsa —
    belgilangan sondagi worker'li fon navbatiga (`_merge_executor`) qo'yib,
    ffmpeg bilan birlashtiradi. Ikkala tomondan ham (video finalize va audio
    finalize) chaqiriladi; DB-level atomik status o'tishi (RECORDING ->
    MERGING) ikki marta ishga tushishining oldini oladi."""
    from apps.lessons.models import LessonRecording

    recording = LessonRecording.objects.filter(lesson_id=lesson_id).first()
    if recording is None:
        return
    if not (recording.video_ready_at and recording.audio_finalized_at):
        return
    if not (recording.video_file_name and recording.audio_file_name):
        return
    updated = LessonRecording.objects.filter(
        pk=recording.pk, status=LessonRecording.Status.RECORDING,
    ).update(status=LessonRecording.Status.MERGING)
    if not updated:
        return  # allaqachon merge boshlangan/tugagan
    _merge_executor.submit(_run_merge_in_pool, recording.pk)


MERGE_MAX_ATTEMPTS = 3
MERGE_STUCK_AFTER = timedelta(minutes=20)  # `MERGING` shundan uzoq tursa — merge jarayoni o'lgan (masalan deploy)
FILE_IDLE_AFTER = timedelta(minutes=5)     # fayl shuncha vaqt o'zgarmagan bo'lsa — yuklash tugagan


def _usable(path) -> bool:
    return bool(path) and path.exists() and path.stat().st_size > 0


def recover_recordings(*, now=None, limit: int = 3) -> dict:
    """Qotib qolgan yoki xato bilan tugagan yozuvlarni (xom fayllari diskda bo'lsa) qayta birlashtiradi.

    Sabablar: merge jarayoni deploy/qayta ishga tushish paytida o'ldi (`MERGING`da qolib, keyin `FAILED` bo'ldi);
    o'qituvchi brauzeri "tugadi" demasdan yopilib qoldi. Qoidalar: faqat YAKUNLANGAN dars, har yozuvga ko'pi bilan
    `MERGE_MAX_ATTEMPTS` urinish, fayllar `FILE_IDLE_AFTER` dan beri o'zgarmagan bo'lishi kerak, har ishga tushishda ko'pi
    bilan `limit` ta yozuv (server yuklanmasligi uchun). Birlashtirish odatdagidek `-c copy` (qayta kodlashsiz — yengil).
    Qaytaradi: `{merged, single, repaired, skipped}`."""
    import logging

    from django.db.models import F, Q

    from apps.lessons.models import LessonRecording

    now = now or timezone.now()
    report = {'merged': 0, 'single': 0, 'repaired': 0, 'skipped': 0}
    candidates = (
        LessonRecording.objects.select_related('lesson')
        .filter(lesson__status=Lesson.Status.FINISHED, merge_attempts__lt=MERGE_MAX_ATTEMPTS)
        .filter(
            Q(status=LessonRecording.Status.MERGING, updated_at__lt=now - MERGE_STUCK_AFTER)
            | Q(status=LessonRecording.Status.FAILED)
            # Dars majburan yakunlangan, lekin birlashtirish boshlanmagan (sayt serveri fayllarga ega emas) — fayllar
            # `FILE_IDLE_AFTER` dan beri o'zgarmagan bo'lsagina olinadi (pastda)
            | Q(status=LessonRecording.Status.RECORDING, updated_at__lt=now - FILE_IDLE_AFTER)
        )
        .order_by('updated_at')[:limit * 4]
    )
    for recording in candidates:
        if sum(report[k] for k in ('merged', 'single', 'repaired')) >= limit:
            break
        root = settings.RECORDINGS_DIR
        video = root / recording.video_file_name if recording.video_file_name else None
        audio = root / recording.audio_file_name if recording.audio_file_name else None
        final = root / recording.file_name if recording.file_name else None
        # Yakuniy fayl bor, faqat holat noto'g'ri qolgan — shunchaki to'g'rilaymiz
        if _usable(final):
            LessonRecording.objects.filter(pk=recording.pk).update(status=LessonRecording.Status.COMPLETED, error='')
            report['repaired'] += 1
            continue
        has_video, has_audio = _usable(video), _usable(audio)
        if not (has_video or has_audio):
            report['skipped'] += 1
            continue
        idle_cutoff = now.timestamp() - FILE_IDLE_AFTER.total_seconds()
        if any(p.stat().st_mtime > idle_cutoff for p in (video, audio) if _usable(p)):
            report['skipped'] += 1  # fayl hali yangilanyapti — o'qituvchi hamon yuklayotgan bo'lishi mumkin
            continue
        claimed = LessonRecording.objects.filter(pk=recording.pk, status=recording.status, merge_attempts=recording.merge_attempts).update(
            merge_attempts=F('merge_attempts') + 1, error='',
        )
        if not claimed:
            continue  # boshqa jarayon allaqachon oldi
        logging.getLogger('apps').warning(
            'recording %s qayta tiklanmoqda (urinish %d, holat %s)', recording.pk, recording.merge_attempts + 1, recording.status,
        )
        if has_video and has_audio:
            LessonRecording.objects.filter(pk=recording.pk).update(
                status=LessonRecording.Status.MERGING,
                video_ready_at=recording.video_ready_at or now, audio_finalized_at=recording.audio_finalized_at or now,
            )
            _merge_recording(recording.pk)
            report['merged'] += 1
        else:
            # Faqat bitta tomon fayli bor: yo'q tomonning nomini tozalab, mavjudi bilan yakunlaymiz
            LessonRecording.objects.filter(pk=recording.pk).update(
                status=LessonRecording.Status.RECORDING,
                **({'audio_file_name': ''} if not has_audio else {'video_file_name': ''}),
            )
            finalize_single_side(recording.lesson_id)
            report['single'] += 1
    return report


def finalize_single_side(lesson_id) -> None:
    """Video YOKI audiodan faqat BITTASI keladi, ikkinchisi HECH QACHON
    kelmaydi (brauzer qulab qolgan, ruxsat berilmagan va h.k.) — mavjud
    bo'lgan tomon bilan yakunlaydi, butunlay yo'qotmaydi. Ikkala
    yo'nalish uchun ham ishlaydi (faqat video, yoki faqat audio).
    `maybe_start_merge`ga o'xshab, atomik DB guard ikki marta ishlashning
    oldini oladi. Chaqiruvchi (`apps.lessons.services.recording_info`)
    qancha kutish kerakligini o'zi hisoblaydi."""
    import logging

    from apps.lessons.models import LessonRecording

    recording = LessonRecording.objects.filter(lesson_id=lesson_id).first()
    if recording is None:
        return
    if recording.video_file_name and not recording.audio_file_name:
        source, label, kind, sessions = recording.video_file_name, "video-only (audio yo'q)", 'video', recording.video_sessions
    elif recording.audio_file_name and not recording.video_file_name:
        source, label, kind, sessions = recording.audio_file_name, "audio-only (video yo'q)", 'audio', recording.audio_sessions
    else:
        return
    path = settings.RECORDINGS_DIR / source
    if not path.exists():
        return
    # Merge bo'lmasa ham (yagona tomon) ko'p-segmentli fayl bo'lishi mumkin
    # — u qidirish/pauzada qotib qolmasin deb shu yerda ham to'g'rilanadi.
    normalized_path = _normalize_webm(path, sessions, kind)
    file_name = normalized_path.name
    updated = LessonRecording.objects.filter(
        pk=recording.pk, status=LessonRecording.Status.RECORDING,
    ).update(file_name=file_name, status=LessonRecording.Status.COMPLETED)
    if updated:
        logging.getLogger('apps').info('recording %s finalized %s', recording.pk, label)
        recording.refresh_from_db()
        _announce_recording_ready(recording)


_EBML_MAGIC = b'\x1a\x45\xdf\xa3'
_SCAN_BLOCK = 4 * 1024 * 1024
GAP_MIN_SECONDS = 0.5      # bundan qisqa tanaffus ahamiyatsiz (soat/kodlash farqi)
TAIL_MIN_SECONDS = 1.0     # video va ovoz oxiri orasidagi farq shundan oshsa, qisqasi to'ldiriladi
GAP_MAX_SECONDS = 4 * 3600  # bundan katta "tanaffus" — soat xatosi, to'ldirilmaydi


def _scan_ebml_offsets(path) -> list[int]:
    """Faylda nechta mustaqil EBML (WebM) hujjat borligini bayt offsetlari bo'yicha topadi. Fayl bo'laklab o'qiladi
    (butun fayl xotiraga yuklanmaydi: 90 daqiqalik dars ~800 MB). Odatda faqat bitta (0-offsetda)."""
    offsets, tail, position = [], b'', 0
    with open(path, 'rb') as handle:
        while True:
            block = handle.read(_SCAN_BLOCK)
            if not block:
                break
            data = tail + block
            base = position - len(tail)
            start = 0
            while True:
                idx = data.find(_EBML_MAGIC, start)
                if idx == -1:
                    break
                offsets.append(base + idx)
                start = idx + 1
            tail = data[-(len(_EBML_MAGIC) - 1):]  # chegaradan o'tgan sarlavhani ham topish uchun
            position += len(block)
    return offsets


def _copy_range(source, target, start: int, end: int) -> None:
    with open(source, 'rb') as src, open(target, 'wb') as dst:
        src.seek(start)
        remaining = end - start
        while remaining > 0:
            block = src.read(min(_SCAN_BLOCK, remaining))
            if not block:
                break
            dst.write(block)
            remaining -= len(block)


def _has_ebml_at(path, offset: int) -> bool:
    with open(path, 'rb') as handle:
        handle.seek(offset)
        return handle.read(len(_EBML_MAGIC)) == _EBML_MAGIC


def _is_standalone_webm(path) -> bool:
    import subprocess

    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=format_name',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        capture_output=True, text=True, timeout=30,
    )
    return probe.returncode == 0 and 'matroska' in probe.stdout.lower()


def _media_duration(path) -> float | None:
    """Fayl davomiyligi (soniya). Brauzer (MediaRecorder) yozgan WebM'da davomiylik sarlavhasi bo'lmaydi (`ffprobe`
    `N/A` beradi) — shunda paketlar `-c copy` bilan o'qilib, oxirgi vaqt belgisi olinadi (qayta kodlanmaydi)."""
    import re
    import subprocess

    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
         str(path)], capture_output=True, text=True, timeout=60,
    )
    try:
        value = float(probe.stdout.strip())
        if value > 0:
            return value
    except ValueError:
        pass
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-c', 'copy', '-f', 'null', '-', '-progress', 'pipe:1'],
        capture_output=True, text=True, timeout=600,
    )
    times = re.findall(r'out_time_us=(\d+)', result.stdout)
    if result.returncode == 0 and times:
        return int(times[-1]) / 1_000_000
    return None


def _stream_info(path, kind: str) -> dict | None:
    import json
    import subprocess

    selector = 'v:0' if kind == 'video' else 'a:0'
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', selector, '-show_entries',
         'stream=codec_name,width,height,sample_rate,channels', '-of', 'json', str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if probe.returncode != 0:
        return None
    streams = json.loads(probe.stdout or '{}').get('streams') or []
    return streams[0] if streams else None


def _make_filler(kind: str, seconds: float, like, output) -> bool:
    """`like` faylga o'xshash (kodek, o'lcham/kanallar) `seconds` soniyalik to'ldiruvchi WebM yasaydi:
    video uchun — oxirgi kadrning qotib turgan nusxasi (ekran ulashish o'chiq turgan payt; kadr topilmasa qora ekran),
    ovoz uchun — jimlik. Faqat shu qism qayta kodlanadi (juda arzon: kam kadr/past bitreyt). True — tayyor."""
    import subprocess
    import tempfile
    from pathlib import Path

    info = _stream_info(like, kind)
    if not info:
        return False
    seconds = f'{seconds:.3f}'
    if kind == 'video':
        codec = {'vp8': ['-c:v', 'libvpx'], 'vp9': ['-c:v', 'libvpx-vp9', '-row-mt', '1']}.get(info.get('codec_name'))
        width, height = info.get('width'), info.get('height')
        if not (codec and width and height):
            return False
        with tempfile.TemporaryDirectory(dir=settings.RECORDINGS_DIR) as tmp:
            frame = Path(tmp) / 'last.png'
            subprocess.run(
                ['ffmpeg', '-y', '-loglevel', 'error', '-sseof', '-2', '-i', str(like), '-an', '-update', '1', str(frame)],
                capture_output=True, timeout=300,
            )
            source = (['-loop', '1', '-framerate', '2', '-i', str(frame)] if frame.exists() and frame.stat().st_size
                      else ['-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:r=2'])
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', *source, '-t', seconds, '-an', *codec,
                   '-b:v', '60k', '-g', '20', '-deadline', 'realtime', '-cpu-used', '8', '-pix_fmt', 'yuv420p',
                   '-vf', f'scale={width}:{height}', str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    else:
        rate, channels = info.get('sample_rate') or '48000', int(info.get('channels') or 1)
        layout = 'mono' if channels == 1 else 'stereo'
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'anullsrc=r={rate}:cl={layout}',
               '-t', seconds, '-c:a', 'libopus', '-b:a', '16k', str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return result.returncode == 0 and Path(output).exists() and Path(output).stat().st_size > 0


def _mkv_append(parts, output) -> bool:
    import subprocess

    cmd = ['mkvmerge', '-q', '-o', str(output), str(parts[0])]
    for part in parts[1:]:
        cmd += ['+', str(part)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    # mkvmerge chiqish kodlari: 0 — xatosiz, 1 — ogohlantirish bilan (muvaffaqiyatli), 2 — xato.
    return result.returncode in (0, 1) and output.exists()


def _segment_offsets(path, sessions) -> tuple[list[int], bool]:
    """Fayldagi mustaqil WebM hujjatlarining boshlanish offsetlari. Brauzer yuborgan sessiya ma'lumoti bo'lsa (aniq,
    tekshirilgan) — shu; bo'lmasa (eski mijoz) — fayldan qidiriladi va har nomzod `ffprobe` bilan tasdiqlanadi.
    Ikkinchi qiymat: offsetlar sessiya ma'lumotidan olindimi (u holda vaqt belgilari ham bor)."""
    import tempfile
    from pathlib import Path

    size = path.stat().st_size
    if sessions and len(sessions) > 1:
        offsets = [s.get('offset') for s in sessions]
        if (all(isinstance(o, int) for o in offsets) and offsets[0] == 0
                and offsets == sorted(set(offsets)) and offsets[-1] < size
                and all(_has_ebml_at(path, o) for o in offsets)):
            return offsets, True
    raw = _scan_ebml_offsets(path)
    if len(raw) <= 1:
        return raw[:1], False
    bounds = raw + [size]
    offsets = [raw[0]]
    with tempfile.TemporaryDirectory(dir=settings.RECORDINGS_DIR) as tmp:
        for i in range(1, len(raw)):
            candidate = Path(tmp) / f'candidate-{i}.webm'
            _copy_range(path, candidate, raw[i], bounds[i + 1])
            if _is_standalone_webm(candidate):
                offsets.append(raw[i])
            candidate.unlink()
    return offsets, False


def _session_start(sessions, index: int):
    from datetime import timezone as dt_timezone

    from django.utils.dateparse import parse_datetime

    try:
        value = sessions[index].get('started_at')
    except (IndexError, AttributeError, TypeError):
        return None
    parsed = parse_datetime(value) if value else None
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def _normalize_webm(path, sessions=None, kind=None):
    """Brauzer tarmoq uzilib-ulanganda, ekran ulashish o'chirib-yoqilganda yoki sahifa yangilanganda MediaRecorder
    sessiyasi qayta boshlanadi — natijada bir nechta MUSTAQIL WebM hujjati serverda xom baytlarda ketma-ket ulanib
    qoladi (`upload_recording_*_chunk` shunchaki 'ab' bilan qo'shib boradi). Oddiy demuxer/muxerlar BITTA Segment
    kutadi: ikkinchi hujjatdan keyingi qism vaqt belgisi buzilgan holda o'qiladi (production'da topilgan xato:
    6 daqiqalik yozuvdan atigi ~30 soniyasi tiklangan, qidirish/pauza umuman ishlamagan).

    `mkvmerge --append` (MKVToolNix) ishlatiladi — u bir xil kodekli segmentlarni QAYTA KODLAMASDAN, vaqt belgilarini
    to'g'irlab ulaydi (lossless append). (Avval ffmpeg `-f concat` DEMUXERI sinalgan — ishonchsiz chiqdi, Cues'siz
    bo'laklarning o'z ichidagi davomiyligiga ishonib keyingi segmentni jimgina tashlab yuborgan edi, 2026-09-01.)
    Bitta hujjatli (normal) fayllarga tegilmaydi — o'zgarishsiz qaytariladi.

    DIQQAT (production'da topilgan, 2026-09-01): `1A45DFA3` baytlari siqilgan video ma'lumotlari ICHIDA ham
    TASODIFAN uchrashi mumkin. Sessiya ma'lumoti bo'lmasa har nomzod ffprobe bilan haqiqatan mustaqil WebM sifatida
    tasdiqlanadi; soxtasi oldingi segmentga qo'shib yuboriladi.

    TANAFFUS (2026-10-29): `mkvmerge` segmentlarni orasidagi real vaqt tanaffusisiz ulaydi. Ovoz esa uzluksiz yozilib
    ketsa, video undan tanaffus uzunligicha oldinga siljib qolardi va `-shortest` darsning oxirini kesardi (lokal
    tajribada: 10 soniyalik tanaffus -> 10 soniya siljish). `sessions` (har sessiyaning brauzer soatidagi boshlanishi)
    va `kind` ('video'|'audio') berilsa, har tanaffus o'sha uzunlikdagi to'ldiruvchi bilan (`_make_filler`) to'ldiriladi
    va vaqt chizig'i haqiqiy dars bilan mos qoladi."""
    import logging
    import tempfile
    from pathlib import Path

    if not path.exists():
        return path
    offsets, from_sessions = _segment_offsets(path, sessions)
    if len(offsets) <= 1:
        return path

    size = path.stat().st_size
    bounds = offsets + [size]
    normalized_path = path.with_name(f'{path.stem}-normalized{path.suffix}')
    starts = [_session_start(sessions, i) for i in range(len(offsets))] if from_sessions else []
    fill = bool(kind and from_sessions and all(starts))
    with tempfile.TemporaryDirectory(dir=settings.RECORDINGS_DIR) as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        segment_paths = []
        for i in range(len(offsets)):
            segment_path = tmp_dir_path / f'segment-{i}.webm'
            _copy_range(path, segment_path, bounds[i], bounds[i + 1])
            segment_paths.append(segment_path)

        parts = [segment_paths[0]]
        if fill:
            elapsed = _media_duration(segment_paths[0])
            for i in range(1, len(segment_paths)):
                if elapsed is None:
                    break
                gap = (starts[i] - starts[0]).total_seconds() - elapsed
                if GAP_MIN_SECONDS <= gap <= GAP_MAX_SECONDS:
                    filler = tmp_dir_path / f'gap-{i}.webm'
                    if _make_filler(kind, gap, segment_paths[i - 1], filler):
                        parts.append(filler)
                        elapsed += gap
                        logging.getLogger('apps').info('%s: %.1f s tanaffus to\'ldirildi (%s, sessiya %d)',
                                                       path.name, gap, kind, i)
                    else:
                        logging.getLogger('apps').warning('%s: tanaffusni to\'ldirib bo\'lmadi (%s, sessiya %d)',
                                                          path.name, kind, i)
                duration = _media_duration(segment_paths[i])
                elapsed = None if duration is None else elapsed + duration
                parts.append(segment_paths[i])
        else:
            parts += segment_paths[1:]
        ok = _mkv_append(parts, normalized_path)
        if not ok and len(parts) > len(segment_paths):
            # To'ldiruvchi bilan ulanmadi (kodek parametrlari mos kelmadi): avvalgidek tanaffussiz, lekin ulaymiz —
            # yozuv butunlay yo'qolmasin
            logging.getLogger('apps').warning("%s: to'ldiruvchi bilan ulanmadi, tanaffussiz ulanmoqda", path.name)
            normalized_path.unlink(missing_ok=True)
            ok = _mkv_append(segment_paths, normalized_path)

    if not ok:
        logging.getLogger('apps').error('webm normalize failed for %s (%d segments)', path.name, len(offsets))
        normalized_path.unlink(missing_ok=True)
        return path
    return normalized_path


def _pad_tail(path, kind: str, seconds: float):
    """Fayl oxiriga `seconds` soniyalik to'ldiruvchi (oxirgi kadr yoki jimlik) ulaydi; yangi fayl yo'lini qaytaradi
    (bajarilmasa — o'zgarishsiz `path`)."""
    import tempfile
    from pathlib import Path

    output = path.with_name(f'{path.stem}-padded{path.suffix}')
    with tempfile.TemporaryDirectory(dir=settings.RECORDINGS_DIR) as tmp:
        filler = Path(tmp) / 'tail.webm'
        if not _make_filler(kind, seconds, path, filler) or not _mkv_append([path, filler], output):
            output.unlink(missing_ok=True)
            return path
    return output


def _equalize_ends(video_path, audio_path, recording, created: list):
    """Video va ovoz fayllarining OXIRI ham real soatga mos bo'lsin: biri ikkinchisidan qisqa bo'lsa (masalan o'qituvchi
    brauzerning "Ulashishni to'xtatish" tugmasini bosgan, dars esa davom etgan), qisqasining oxiriga oxirgi kadr/jimlik
    ulanadi. Aks holda `-shortest` darsning oxirgi qismini (ovozni!) kesib tashlardi. `created` — vaqtinchalik fayllar."""
    if not (recording.video_started_at and recording.audio_started_at):
        return video_path, audio_path
    video_duration, audio_duration = _media_duration(video_path), _media_duration(audio_path)
    if video_duration is None or audio_duration is None:
        return video_path, audio_path
    video_end = recording.video_started_at.timestamp() + video_duration
    audio_end = recording.audio_started_at.timestamp() + audio_duration
    end = max(video_end, audio_end)
    for label, current, missing in (('video', video_path, end - video_end), ('audio', audio_path, end - audio_end)):
        if TAIL_MIN_SECONDS <= missing <= GAP_MAX_SECONDS:
            padded = _pad_tail(current, label, missing)
            if padded != current:
                created.append(padded)
                if label == 'video':
                    video_path = padded
                else:
                    audio_path = padded
    return video_path, audio_path


def _merge_recording(recording_pk) -> None:
    """Video+audio fayllarini vaqt farqiga moslab (`-itsoffset`) bitta WebM faylga birlashtiradi. Ikkalasi ham
    qayta kodlanmaydi (`-c copy`) — brauzer kamerasi VP8/VP9, mikrofon-mix esa Opus kodlaydi, ikkalasi ham WebM
    konteynerida TABIIY qo'llab-quvvatlanadi (production'da topilgan xato: MP4 konteynerga VP8'ni yozib bo'lmaydi —
    "codec not currently supported in container", chiqish fayli umuman yaratilmagan edi).

    Har ikkala kirish avval `_normalize_webm` orqali o'tkaziladi — ko'p-segmentli (qayta ulangan sessiya) fayllarni
    to'g'rilaydi va oradagi tanaffusni to'ldiradi; keyin `_equalize_ends` ikkalasining oxirini tenglashtiradi.

    `-fflags +genpts` qo'shimcha himoya — kichik, segment ichidagi vaqt tebranishlarini silliqlaydi.
    `-cues_to_front 1` chiqish faylini boshidanoq qidirish mumkin (seekable) qiladi."""
    import logging
    import subprocess
    import uuid as _uuid

    from django.db import close_old_connections

    from apps.lessons.models import LessonRecording

    normalized_paths = []
    try:
        recording = LessonRecording.objects.select_related('lesson').get(pk=recording_pk)
        raw_video_path = settings.RECORDINGS_DIR / recording.video_file_name
        raw_audio_path = settings.RECORDINGS_DIR / recording.audio_file_name
        video_path = _normalize_webm(raw_video_path, recording.video_sessions, 'video')
        audio_path = _normalize_webm(raw_audio_path, recording.audio_sessions, 'audio')
        if video_path != raw_video_path:
            normalized_paths.append(video_path)
        if audio_path != raw_audio_path:
            normalized_paths.append(audio_path)
        video_path, audio_path = _equalize_ends(video_path, audio_path, recording, normalized_paths)
        # .webm, .mp4 EMAS — brauzer kamerasi VP8 (yoki VP9) kodlaydi, va VP8/VP9 MP4 konteynerida UMUMAN
        # qo'llab-quvvatlanmaydi (production'da topilgan xato: "Could not find tag for codec vp8 in stream").
        output_name = f'{recording.lesson.room_name}-{_uuid.uuid4().hex[:6]}-final.webm'
        output_path = settings.RECORDINGS_DIR / output_name

        if recording.video_started_at and recording.audio_started_at:
            delta = (recording.video_started_at - recording.audio_started_at).total_seconds()
        else:
            delta = 0.0
        video_offset = max(delta, 0.0)
        audio_offset = max(-delta, 0.0)

        cmd = [
            'ffmpeg', '-y',
            '-itsoffset', f'{video_offset:.3f}', '-fflags', '+genpts', '-i', str(video_path),
            '-itsoffset', f'{audio_offset:.3f}', '-fflags', '+genpts', '-i', str(audio_path),
            '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'copy', '-c:a', 'copy',
            '-cues_to_front', '1',
            '-shortest', str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not output_path.exists():
            LessonRecording.objects.filter(pk=recording_pk).update(
                status=LessonRecording.Status.FAILED,
                error=f'Birlashtirish xatosi: {result.stderr[-500:]}',
            )
            return
        LessonRecording.objects.filter(pk=recording_pk).update(
            file_name=output_name, status=LessonRecording.Status.COMPLETED,
        )
        recording.refresh_from_db()
        _announce_recording_ready(recording)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger('apps').exception('recording merge failed: %s', exc)
        LessonRecording.objects.filter(pk=recording_pk).update(
            status=LessonRecording.Status.FAILED, error=str(exc)[:500],
        )
    finally:
        for normalized_path in normalized_paths:
            normalized_path.unlink(missing_ok=True)
        close_old_connections()


def _announce_recording_ready(recording) -> None:
    """Yozuv (video+audio birlashgan, yoki faqat bittasi) tayyor bo'lganda
    guruh chatga e'lon qiladi. Bu — endi `finish_lesson` ichida EMAS,
    chunki brauzer video/audio yuklashni finish tugmasi bosilgandan KEYIN
    ham davom ettirishi mumkin (chunked upload asinxron); e'lon faqat
    fayl HAQIQATAN tayyor bo'lganda yuboriladi."""
    import logging

    try:
        from apps.lessons.services import publish_recording_message
        title = recording.title or recording.lesson.title or recording.lesson.course.title
        publish_recording_message(recording.lesson, title)
    except Exception:  # noqa: BLE001
        logging.getLogger('apps').exception('recording announce failed')
