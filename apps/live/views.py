"""Live views — yupqa qatlam: HTTP <-> live services."""
from rest_framework.response import Response
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


class RequestMicView(APIView):
    """O'quvchi: mikrofon so'rash ("qo'l ko'tarish")."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request):
        services.request_mic(
            user=request.user, lesson_id=request.data.get('lesson_id'), request=request,
        )
        return Response({'ok': True})


class MuteAllView(APIView):
    """O'qituvchi: hammani ovozsiz qiladi — `{lesson_id, except?: [user_id]}` -> `{muted: n}`."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request):
        except_ids = request.data.get('except') or []
        muted = services.mute_all(
            teacher=request.user, lesson_id=request.data.get('lesson_id'),
            except_ids=except_ids if isinstance(except_ids, list) else [], request=request,
        )
        return Response({'muted': muted})


class LessonPresenceView(APIView):
    """Pre-join ekrani: `{count, avatars}` — hozir darsda nechta kishi bor."""

    permission_classes = [RequirePerm('room.token')]

    def get(self, request, lesson_id):
        return Response(services.lesson_presence(user=request.user, lesson_id=lesson_id))


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
