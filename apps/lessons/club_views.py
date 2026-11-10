"""`/clubs/` — speaking clublar (apps.lessons.clubs). Jonli mashg'ulotlar: oddiy `/lessons/` (`course=<club id>`)."""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.serializers import UserSerializer
from apps.core.permissions import RequirePerm

from . import clubs, selectors
from .models import Course, Enrollment
from .serializers import CourseSerializer


class ClubSerializer(CourseSerializer):
    members_count = serializers.SerializerMethodField()
    chat_room_id = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = [*CourseSerializer.Meta.fields, 'members_count', 'chat_room_id']

    def get_members_count(self, obj) -> int:
        return getattr(obj, 'list_student_count', None) if getattr(obj, 'list_student_count', None) is not None else \
            Enrollment.objects.filter(course=obj, status=Enrollment.Status.APPROVED).count()

    def get_chat_room_id(self, obj):
        room = getattr(obj, 'chat_room', None)
        return str(room.id) if room else None


class ClubViewSet(viewsets.ViewSet):
    """Teacher: o'z clublari; o'quvchi — a'zo bo'lgan clublari; ota-ona — farzandining clublari."""

    permission_classes = [RequirePerm('course.view')]

    def _queryset(self, request):
        qs = selectors.courses_for(request.user).filter(kind=Course.Kind.CLUB)
        return selectors.with_course_stats(qs, request.user).select_related('chat_room')

    def _data(self, request, club, many=False):
        return ClubSerializer(club, many=many, context={'request': request}).data

    def list(self, request):
        return Response(self._data(request, self._queryset(request).order_by('title'), many=True))

    def retrieve(self, request, pk=None):
        club = self._queryset(request).filter(pk=pk).first()
        if club is None:
            return Response({'detail': 'Klub topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._data(request, club))

    def create(self, request):
        """`{title, description?, subject?, course_ids?: [], student_ids?: []}` — a'zolar darhol qo'shiladi va xabar oladi."""
        club = clubs.create_club(
            teacher=request.user, title=request.data.get('title'), description=request.data.get('description', ''),
            subject=request.data.get('subject', ''), course_ids=request.data.get('course_ids'),
            student_ids=request.data.get('student_ids'), request=request,
        )
        return Response(self._data(request, self._queryset(request).get(pk=club.pk)), status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        club = clubs.update_club(
            teacher=request.user, club_id=pk, title=request.data.get('title'), description=request.data.get('description'),
            request=request,
        )
        return Response(self._data(request, self._queryset(request).get(pk=club.pk)))

    def destroy(self, request, pk=None):
        clubs.delete_club(teacher=request.user, club_id=pk, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        """GET — a'zolar; POST `{course_ids?, student_ids?}` — qo'shish (darhol a'zo, bildirishnoma boradi)."""
        if request.method == 'POST':
            return Response(clubs.add_members(
                teacher=request.user, club_id=pk, course_ids=request.data.get('course_ids'),
                student_ids=request.data.get('student_ids'), request=request,
            ))
        club = self._queryset(request).filter(pk=pk).first()
        if club is None:
            return Response({'detail': 'Klub topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        rows = Enrollment.objects.filter(course=club, status=Enrollment.Status.APPROVED).select_related('student').order_by('student__first_name')
        return Response([UserSerializer(e.student).data for e in rows])

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<student_id>[^/.]+)')
    def remove_member(self, request, pk=None, student_id=None):
        clubs.remove_member(teacher=request.user, club_id=pk, student_id=student_id, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
