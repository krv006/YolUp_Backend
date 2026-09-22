"""Voice (guruh ichidagi ovozli suhbat) service qatlami."""
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from livekit.api import AccessToken, VideoGrants
from livekit.protocol.models import TrackSource
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.lessons.models import Course, Enrollment

from .models import VoiceRoom, VoiceRoomJoinRequest, VoiceRoomParticipant

_ENROLLED = Enrollment.Status.APPROVED


def _is_enrolled(course: Course, user: User) -> bool:
    return Enrollment.objects.filter(course=course, student=user, status=_ENROLLED).exists()


def _is_member(course: Course, user: User) -> bool:
    return course.teacher_id == user.id or _is_enrolled(course, user)


def _is_owner_or_teacher(room: VoiceRoom, user: User) -> bool:
    return user.id == room.created_by_id or user.id == room.course.teacher_id


def _get_room(room_id) -> VoiceRoom:
    try:
        return VoiceRoom.objects.select_related('course').get(pk=room_id)
    except (VoiceRoom.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Xona topilmadi.'))


@transaction.atomic
def create_room(
    *, user: User, course: Course, title: str = '',
    access_mode: str = VoiceRoom.AccessMode.OPEN, scheduled_at=None,
) -> VoiceRoom:
    if not _is_member(course, user):
        raise PermissionDenied(_("Siz bu guruh a'zosi emassiz."))
    is_scheduled = bool(scheduled_at and scheduled_at > timezone.now())
    status = VoiceRoom.Status.SCHEDULED if is_scheduled else VoiceRoom.Status.LIVE
    # `select_for_update` + DB constraint (`unique_active_voice_room_per_course`)
    # — ikkalasi ham: birinchisi tushunarli xato xabari uchun, ikkinchisi
    # poyga holati (race condition)dan haqiqiy himoya sifatida.
    active_exists = (
        VoiceRoom.objects.select_for_update()
        .filter(course=course, status__in=[VoiceRoom.Status.SCHEDULED, VoiceRoom.Status.LIVE])
        .exists()
    )
    if active_exists:
        raise ValidationError(_('Bu guruhda allaqachon faol ovozli xona bor.'))
    try:
        room = VoiceRoom.objects.create(
            course=course, created_by=user, title=title, access_mode=access_mode,
            status=status, scheduled_at=scheduled_at,
            started_at=None if is_scheduled else timezone.now(),
        )
    except IntegrityError:
        raise ValidationError(_('Bu guruhda allaqachon faol ovozli xona bor.'))
    audit.record(action='voice.create', actor=user, target=room)
    return room


def _token_payload(room: VoiceRoom, user: User) -> dict:
    is_moderator = _is_owner_or_teacher(room, user)
    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(f'user-{user.id}')
        .with_name(user.get_full_name() or user.username)
        .with_ttl(timedelta(hours=4))
        .with_grants(VideoGrants(
            room_join=True,
            room=room.room_name,
            room_admin=is_moderator,
            can_publish=True,
            can_subscribe=True,
            # Ovozli suhbat — faqat mikrofon; kamera/ekran ulashish yo'q
            # (darslardagi video-xonadan farqli, bu shunchaki ovozli kanal).
            can_publish_sources=[TrackSource.MICROPHONE],
        ))
    )
    return {
        'token': token.to_jwt(), 'url': settings.LIVEKIT_URL, 'room': room.room_name,
        'is_moderator': is_moderator,
    }


@transaction.atomic
def join_room(*, user: User, room_id, request=None) -> dict:
    try:
        room = VoiceRoom.objects.select_for_update().select_related('course').get(pk=room_id)
    except (VoiceRoom.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Xona topilmadi.'))
    if room.status == VoiceRoom.Status.ENDED:
        raise ValidationError(_('Bu xona yopilgan.'))
    if not _is_member(room.course, user):
        raise PermissionDenied(_("Siz bu guruh a'zosi emassiz."))

    is_moderator = _is_owner_or_teacher(room, user)
    if room.status == VoiceRoom.Status.SCHEDULED:
        if room.scheduled_at and timezone.now() < room.scheduled_at and not is_moderator:
            raise ValidationError(_('Xona hali boshlanmagan.'))
        room.status = VoiceRoom.Status.LIVE
        room.started_at = timezone.now()
        room.save(update_fields=['status', 'started_at'])

    if not is_moderator and room.access_mode == VoiceRoom.AccessMode.INVITE_ONLY:
        approved = VoiceRoomJoinRequest.objects.filter(
            room=room, user=user, status=VoiceRoomJoinRequest.Status.APPROVED,
        ).exists()
        if not approved:
            raise PermissionDenied(_("Bu xonaga kirish uchun avval so'rov yuboring va tasdiqlanishini kuting."))

    if not VoiceRoomParticipant.objects.filter(room=room, user=user, left_at__isnull=True).exists():
        VoiceRoomParticipant.objects.create(room=room, user=user)

    audit.record(action='voice.join', actor=user, target=room, request=request)
    return _token_payload(room, user)


def _maybe_close_if_empty(room_id) -> None:
    still_inside = VoiceRoomParticipant.objects.filter(room_id=room_id, left_at__isnull=True).exists()
    if still_inside:
        return
    VoiceRoom.objects.filter(pk=room_id, status=VoiceRoom.Status.LIVE).update(
        status=VoiceRoom.Status.ENDED, ended_at=timezone.now(),
    )


@transaction.atomic
def leave_room(*, user: User, room_id, request=None) -> bool:
    updated = VoiceRoomParticipant.objects.filter(
        room_id=room_id, user=user, left_at__isnull=True,
    ).update(left_at=timezone.now())
    if updated:
        audit.record(action='voice.leave', actor=user, meta={'room_id': str(room_id)}, request=request)
        _maybe_close_if_empty(room_id)
    return bool(updated)


def close_room(*, user: User, room_id, request=None) -> VoiceRoom:
    room = _get_room(room_id)
    if not _is_owner_or_teacher(room, user):
        raise PermissionDenied(_('Faqat xona egasi yoki kurs o\'qituvchisi yopa oladi.'))
    if room.status != VoiceRoom.Status.ENDED:
        room.status = VoiceRoom.Status.ENDED
        room.ended_at = timezone.now()
        room.save(update_fields=['status', 'ended_at'])
        VoiceRoomParticipant.objects.filter(room=room, left_at__isnull=True).update(left_at=timezone.now())
        audit.record(action='voice.close', actor=user, target=room, request=request)
    return room


@transaction.atomic
def request_join(*, user: User, room_id, request=None) -> VoiceRoomJoinRequest:
    room = _get_room(room_id)
    if room.access_mode != VoiceRoom.AccessMode.INVITE_ONLY:
        raise ValidationError(_("Bu xona ochiq — so'rov shart emas, to'g'ridan-to'g'ri kiring."))
    if room.status == VoiceRoom.Status.ENDED:
        raise ValidationError(_('Bu xona yopilgan.'))
    if not _is_member(room.course, user):
        raise PermissionDenied(_("Siz bu guruh a'zosi emassiz."))
    if _is_owner_or_teacher(room, user):
        raise ValidationError(_("Xona egasi/o'qituvchiga so'rov kerak emas."))

    join_request, created = VoiceRoomJoinRequest.objects.get_or_create(
        room=room, user=user, defaults={'status': VoiceRoomJoinRequest.Status.PENDING},
    )
    if not created and join_request.status == VoiceRoomJoinRequest.Status.DENIED:
        join_request.status = VoiceRoomJoinRequest.Status.PENDING
        join_request.save(update_fields=['status'])
    audit.record(action='voice.request_join', actor=user, target=room, request=request)
    return join_request


def list_join_requests(*, user: User, room_id):
    """Faqat xona egasi yoki kurs o'qituvchisi so'rovlar ro'yxatini ko'radi
    (boshqa a'zolar kimning so'raganini bilmasligi kerak)."""
    room = _get_room(room_id)
    if not _is_owner_or_teacher(room, user):
        raise PermissionDenied(_('Faqat xona egasi yoki kurs o\'qituvchisi so\'rovlarni ko\'ra oladi.'))
    return room.join_requests.select_related('user').order_by('created_at')


def _respond_request(*, user: User, room_id, request_id, new_status: str, request=None) -> VoiceRoomJoinRequest:
    try:
        join_request = VoiceRoomJoinRequest.objects.select_related('room', 'room__course').get(
            pk=request_id, room_id=room_id,
        )
    except (VoiceRoomJoinRequest.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("So'rov topilmadi."))
    if not _is_owner_or_teacher(join_request.room, user):
        raise PermissionDenied(_('Faqat xona egasi yoki kurs o\'qituvchisi javob bera oladi.'))
    join_request.status = new_status
    join_request.save(update_fields=['status'])
    audit.record(action=f'voice.request_{new_status}', actor=user, target=join_request, request=request)
    return join_request


def approve_request(*, user: User, room_id, request_id, request=None) -> VoiceRoomJoinRequest:
    return _respond_request(
        user=user, room_id=room_id, request_id=request_id,
        new_status=VoiceRoomJoinRequest.Status.APPROVED, request=request,
    )


def deny_request(*, user: User, room_id, request_id, request=None) -> VoiceRoomJoinRequest:
    return _respond_request(
        user=user, room_id=room_id, request_id=request_id,
        new_status=VoiceRoomJoinRequest.Status.DENIED, request=request,
    )
