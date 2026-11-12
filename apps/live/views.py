"""Live views — yupqa qatlam: HTTP <-> live services."""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import services


class RoomTokenView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        payload = services.issue_room_token(
            user=request.user, lesson_id=request.data.get('lesson_id'), request=request,
        )
        return Response(payload)


class RoomLeaveView(APIView):
    permission_classes = [RequirePerm('room.leave')]

    def post(self, request):
        updated = services.leave_room(
            user=request.user, lesson_id=request.data.get('lesson_id'), request=request,
        )
        return Response({'updated': updated})


class AttentionView(APIView):
    """GET: hozir ko'rsatiladigan "Siz shu yerdamisiz?" tekshiruvi (polling).
    POST: javob berish."""

    permission_classes = [RequirePerm('room.token')]

    def get(self, request):
        check = services.pending_attention(
            user=request.user, lesson_id=request.query_params.get('lesson_id'),
        )
        if not check:
            return Response({'check': None})
        return Response({'check': {'id': str(check.id), 'due_at': check.due_at}})

    def post(self, request):
        check = services.answer_attention(user=request.user, check_id=request.data.get('check_id'))
        return Response({'answered_at': check.answered_at})


class FocusEventView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        result = services.record_focus(
            user=request.user,
            lesson_id=request.data.get('lesson_id'),
            kind=request.data.get('kind'),
        )
        return Response({'ok': True, **result})


class AllowShareView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        services.grant_screen_share(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            identity=request.data.get('identity'),
            request=request,
        )
        return Response({'ok': True})


class CancelMicRequestView(APIView):
    """O'quvchi: o'z mikrofon so'rovini bekor qilish — `DELETE /live/lesson/<id>/mic-request/` (idempotent, 204)."""

    permission_classes = [RequirePerm('room.token')]

    def delete(self, request, lesson_id):
        services.cancel_mic_request(user=request.user, lesson_id=lesson_id, request=request)
        return Response(status=204)


class CancelCameraRequestView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def delete(self, request, lesson_id):
        services.cancel_camera_request(user=request.user, lesson_id=lesson_id, request=request)
        return Response(status=204)


class RequestMicView(APIView):
    """O'quvchi: mikrofon so'rash ("qo'l ko'tarish")."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        services.request_mic(
            user=request.user, lesson_id=request.data.get('lesson_id'), request=request,
        )
        return Response({'ok': True})


class MuteAllView(APIView):
    """O'qituvchi: hammaning mikrofonini (yoki `kind: "video"` bo'lsa kamerasini) o'chiradi va RUXSATINI qaytarib oladi —
    `{lesson_id, kind?: "audio"|"video", except?: [user_id]}` -> `{muted: n}` (video: `{camera_off: n}`).
    O'quvchilar interfeysi `mic_revoked` / `camera_revoked` hodisasi bilan "So'rash" holatiga qaytadi."""

    permission_classes = [RequirePerm('room.moderate')]
    kind_default = 'audio'

    def post(self, request):
        except_ids = request.data.get('except') or []
        kind = services._media_kind(request.data.get('kind') or self.kind_default)
        count = services.restrict_media(
            teacher=request.user, lesson_id=request.data.get('lesson_id') or request.data.get('lesson'),
            kind=kind, except_ids=except_ids if isinstance(except_ids, list) else [], request=request,
        )
        return Response({'muted': count} if kind == 'audio' else {'camera_off': count})


class CameraOffAllView(MuteAllView):
    """`POST /live/camera-off-all/ {lesson_id, except?}` — `mute-all` ning `kind: "video"` varianti."""

    kind_default = 'video'


class ReleaseMediaView(APIView):
    """O'quvchi ruxsat berilgan mikrofon/kamera/ekran ulashishni o'zi to'xtatgach chaqiradi:
    `{lesson_id, kind: "microphone"|"camera"|"screen"}` -> `{revoked, open}`. Ruxsat olinadi (qayta yoqish uchun yana so'rov kerak;
    hodisalar: `mic_revoked` / `camera_revoked` / `screen_revoked`); ochiq rejim yoqilgan bo'lsa mikrofon/kamera ruxsati olinmaydi."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        return Response(services.release_media(
            user=request.user, lesson_id=request.data.get('lesson_id') or request.data.get('lesson'),
            kind=request.data.get('kind'), request=request,
        ))


class LessonMediaModeView(APIView):
    """`GET` — holat (`{open_mic, open_camera}`); `PATCH {open_mic?, open_camera?}` — o'qituvchi almashtirgichlari."""

    def get_permissions(self):
        return [RequirePerm('room.moderate' if self.request.method == 'PATCH' else 'room.token')()]

    def get(self, request, lesson_id):
        from apps.lessons import selectors as lesson_selectors

        lesson = lesson_selectors.lessons_for(request.user).filter(pk=lesson_id).first()
        if lesson is None:
            raise NotFound(_('Dars topilmadi.'))
        return Response(services.media_mode(lesson=lesson))

    def patch(self, request, lesson_id):
        return Response(services.set_media_mode(
            teacher=request.user, lesson_id=lesson_id, open_mic=request.data.get('open_mic'),
            open_camera=request.data.get('open_camera'), request=request,
        ))


class LessonPresenceView(APIView):
    """Pre-join ekrani: `{count, avatars}` — hozir darsda nechta kishi bor."""

    permission_classes = [RequirePerm('room.token')]

    def get(self, request, lesson_id):
        return Response(services.lesson_presence(user=request.user, lesson_id=lesson_id))


class ClientHealthView(APIView):
    """Brauzer jonli darsda har ~30 s da yuboradi: `{cpu_constrained?, hardware_concurrency?, device_memory?, connection_quality?,
    page_visible?, events?: [str], tracks: [{source, fps?, width?, height?, target_bitrate?, bitrate?, quality_limitation_reason?,
    packets_lost?, jitter?, rtt?}]}` -> `201 {id}`. Faqat dars o'qituvchisi/yozilgan o'quvchisi; chastota cheklovi 12/min."""

    permission_classes = [RequirePerm('room.token')]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'client_health'

    def post(self, request, lesson_id):
        from apps.monitoring import client_health

        report = client_health.record(
            user=request.user, lesson_id=lesson_id, data=request.data, user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return Response({'id': str(report.id)}, status=201)


class LessonSignalsView(APIView):
    """O'qituvchi: `{away_students, pending_mic_requests, pending_camera_requests}` — doskani yuklamasdan, kichik javob."""

    permission_classes = [RequirePerm('room.moderate')]

    def get(self, request, lesson_id):
        return Response(services.lesson_signals(teacher=request.user, lesson_id=lesson_id))


class GrantMicView(APIView):
    """O'qituvchi: o'quvchiga mikrofon ruxsatini beradi."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        services.grant_mic(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'ok': True})


class DenyMicView(APIView):
    """O'qituvchi: mikrofon so'rovini rad etadi (ruxsat bermasdan navbatdan chiqaradi)."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        denied = services.deny_mic(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'denied': denied})


class RequestCameraView(APIView):
    """O'quvchi: kamera so'rash (2026-09-04: mikrofon bilan bir xil naqsh)."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        services.request_camera(
            user=request.user, lesson_id=request.data.get('lesson_id'), request=request,
        )
        return Response({'ok': True})


class GrantCameraView(APIView):
    """O'qituvchi: o'quvchiga kamera ruxsatini beradi."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        services.grant_camera(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'ok': True})


class DenyCameraView(APIView):
    """O'qituvchi: kamera so'rovini rad etadi."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        denied = services.deny_camera(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'denied': denied})


class InviteView(APIView):
    """O'qituvchi: darsga taklif bildirishnomasi. `student_id` bo'lmasa — hammaga."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        count = services.invite_to_lesson(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'invited': count})


class BanView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        services.ban_participant(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'ok': True})


class UnbanView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        unbanned = services.unban_participant(
            teacher=request.user,
            lesson_id=request.data.get('lesson_id'),
            student_id=request.data.get('student_id'),
            request=request,
        )
        return Response({'unbanned': unbanned})
