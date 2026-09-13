"""Lessons views — yupqa qatlam: HTTP <-> service/selector."""
from django.db.models import Q
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.core.permissions import RequirePerm

from . import selectors, services
from .models import Course, Enrollment
from .serializers import (
    AttendanceSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    LessonRatingSerializer,
    LessonSerializer,
    RateLessonSerializer,
    ScheduleLessonsSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    search_fields = ['title', 'subject']
    ordering_fields = ['created_at', 'title']

    def get_permissions(self):
        if self.action == 'create':
            return [RequirePerm('course.create')()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [RequirePerm('course.edit')()]
        if self.action in ('enroll', 'unenroll', 'catalog'):
            return [RequirePerm('course.enroll')()]
        if self.action in ('requests', 'respond_request'):
            return [RequirePerm('course.edit')()]  # faqat o'qituvchi (o'z kurslari service'da tekshiriladi)
        if self.action == 'schedule':
            return [RequirePerm('lesson.schedule')()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.action == 'catalog':
            return Course.objects.filter(is_active=True).select_related('teacher').order_by('title')
        return selectors.courses_for(self.request.user)

    @action(detail=False)
    def catalog(self, request):
        """Yozilish uchun ochiq kurslar — o'quvchi/ota-ona ko'radi (courses_for faqat yozilganlarni beradi)."""
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def perform_create(self, serializer):
        serializer.instance = services.create_course(
            teacher=self.request.user, request=self.request, **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        services.delete_course(teacher=self.request.user, course=instance, request=self.request)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        enrollment, created = services.enroll(
            course_id=pk, by_user=request.user,
            student_id=request.data.get('student_id'),
            student_ref=request.data.get('student'),
            request=request,
        )
        return Response(
            EnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def unenroll(self, request, pk=None):
        removed = services.unenroll(
            course_id=pk, by_user=request.user,
            student_id=request.data.get('student_id'), request=request,
        )
        return Response({'removed': removed})

    @action(detail=False)
    def requests(self, request):
        """O'qituvchi kurslariga kelgan kutilayotgan yozilish so'rovlari — panel xabarnomasi."""
        qs = (
            Enrollment.objects
            .filter(course__teacher=request.user, status=Enrollment.Status.PENDING)
            .select_related('student', 'course')
            .order_by('created_at')
        )
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(EnrollmentSerializer(page, many=True).data)

    @action(detail=False, methods=['post'], url_path='requests/respond')
    def respond_request(self, request):
        enrollment = services.respond_enrollment(
            teacher=request.user,
            enrollment_id=request.data.get('enrollment_id'),
            action=request.data.get('action'),
            request=request,
        )
        return Response(EnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        """Haftalik jadval asosida ko'plab darslarni avtomatik yaratadi."""
        course = self.get_object()
        ser = ScheduleLessonsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        lessons = services.schedule_recurring(
            teacher=request.user, course=course, request=request,
            **ser.validated_data,
        )
        return Response(
            {'count': len(lessons), 'lessons': LessonSerializer(lessons, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, url_path='search-students')
    def search_students(self, request, pk=None):
        """Jonli qidiruv (EduTech.docx: username orqali bazadan search) —
        o'qituvchi yozgan matnga mos o'quvchilar, kursdagi holati bilan."""
        course = self.get_object()
        if course.teacher_id != request.user.id and request.user.role not in ('admin', 'super_admin'):
            self.permission_denied(request, message="Faqat kurs o'qituvchisi qidiradi.")
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response([])
        students = User.objects.filter(role=User.Role.STUDENT).filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(invite_code__iexact=q)
        ).order_by('username')[:10]
        statuses = dict(
            course.enrollments.filter(student__in=students).values_list('student_id', 'status')
        )
        return Response([
            {**UserSerializer(s).data, 'enroll_status': statuses.get(s.id)}
            for s in students
        ])

    @action(detail=True)
    def students(self, request, pk=None):
        """Kursga yozilgan o'quvchilar — faqat kurs o'qituvchisi (va admin) ko'radi."""
        course = self.get_object()
        if course.teacher_id != request.user.id and request.user.role not in ('admin', 'super_admin'):
            self.permission_denied(request, message="Faqat kurs o'qituvchisi o'quvchilar ro'yxatini ko'radi.")
        qs = course.enrollments.select_related('student').order_by('student__first_name')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(EnrollmentSerializer(page, many=True).data)


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    filterset_fields = ['course', 'status']
    ordering_fields = ['starts_at']

    def get_permissions(self):
        if self.action == 'create':
            return [RequirePerm('lesson.schedule')()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [RequirePerm('lesson.edit')()]
        if self.action == 'finish':
            return [RequirePerm('lesson.finish')()]
        if self.action == 'rate':
            return [RequirePerm('lesson.rate')()]
        if self.action == 'recording_stream':
            # Video oqimi imzolangan muddatli token bilan himoyalangan —
            # <video src> Authorization header yubora olmaydi
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return selectors.lessons_for(self.request.user)

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        course = data.pop('course')
        serializer.instance = services.schedule_lesson(
            teacher=self.request.user, course=course, request=self.request, **data,
        )

    def perform_update(self, serializer):
        # `quiz` Lesson modelining o'z maydoni emas (Quiz'ning `lesson` FK'si
        # orqali teskari bog'lanadi) — shuning uchun `serializer.save()`dan
        # OLDIN chiqarib olib, alohida service orqali qo'llaymiz.
        has_quiz = 'quiz' in serializer.validated_data
        quiz = serializer.validated_data.pop('quiz', None)
        lesson = serializer.save()
        if has_quiz:
            services.update_lesson_quiz(
                teacher=self.request.user, lesson=lesson, quiz=quiz, request=self.request,
            )

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """Darsni yakunlash. `recording_title` — video yozuvga o'qituvchi
        beradigan nom (bo'sh bo'lsa dars nomi olinadi); yozuv guruh chatga tushadi."""
        lesson = self.get_object()
        lesson = services.finish_lesson(
            teacher=request.user, lesson=lesson,
            recording_title=request.data.get('recording_title') or '',
            request=request,
        )
        return Response(LessonSerializer(lesson).data)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        lesson = self.get_object()
        if lesson.status != 'finished':
            raise ValidationError(_('Faqat tugagan darsga baho berish mumkin.'))
        if not lesson.course.enrollments.filter(
            student=request.user, status=Enrollment.Status.APPROVED,
        ).exists():
            raise PermissionDenied(_("Siz bu kursga yozilmagansiz."))
        ser = RateLessonSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from .models import LessonRating
        rating, created = LessonRating.objects.update_or_create(
            lesson=lesson, student=request.user,
            defaults=ser.validated_data,
        )
        return Response(
            LessonRatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True)
    def ratings(self, request, pk=None):
        lesson = self.get_object()
        qs = lesson.ratings.select_related('student').order_by('-created_at')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(LessonRatingSerializer(page, many=True).data)

    @action(detail=True, methods=['get', 'delete'], url_path='recording')
    def recording(self, request, pk=None):
        """GET — yozuv holati + muddatli stream havolasi; DELETE — o'qituvchi o'chiradi."""
        lesson = self.get_object()
        if request.method == 'DELETE':
            services.delete_recording(teacher=request.user, lesson=lesson)
            return Response(status=204)
        return Response(services.recording_info(user=request.user, lesson=lesson))

    @action(
        detail=True, methods=['post'], url_path='recording/audio',
        parser_classes=[MultiPartParser, FormParser],
    )
    def recording_audio_chunk(self, request, pk=None):
        """O'qituvchi brauzeridan audio bo'lagi (chunk) — dars davomida
        ketma-ket, har 30-60 soniyada yuboriladi. Brauzer barcha
        ishtirokchilar ovozini ichkarida (Web Audio API) aralashtirib
        yuboradi — server faqat diskka yozadi, CPU sarflamaydi."""
        lesson = self.get_object()
        chunk = request.FILES.get('chunk')
        if not chunk:
            raise ValidationError({'chunk': _("Fayl bo'lagi yuborilmadi.")})
        services.upload_recording_audio_chunk(
            teacher=request.user, lesson=lesson, chunk=chunk,
            started_at=request.data.get('started_at') or None,
        )
        return Response(status=204)

    @action(detail=True, methods=['post'], url_path='recording/audio/finalize')
    def recording_audio_finalize(self, request, pk=None):
        """O'qituvchi audio yuklashni tugatdi — video ham tayyor bo'lsa,
        fon jarayonida birlashtirish boshlanadi."""
        lesson = self.get_object()
        services.finalize_recording_audio(teacher=request.user, lesson=lesson)
        return Response(status=204)

    @action(
        detail=True, methods=['post'], url_path='recording/video',
        parser_classes=[MultiPartParser, FormParser],
    )
    def recording_video_chunk(self, request, pk=None):
        """O'qituvchi brauzeridan video bo'lagi (chunk) — ekranning o'zi
        (`getDisplayMedia`), audio bilan bir xil naqshda."""
        lesson = self.get_object()
        chunk = request.FILES.get('chunk')
        if not chunk:
            raise ValidationError({'chunk': _("Fayl bo'lagi yuborilmadi.")})
        services.upload_recording_video_chunk(
            teacher=request.user, lesson=lesson, chunk=chunk,
            started_at=request.data.get('started_at') or None,
        )
        return Response(status=204)

    @action(detail=True, methods=['post'], url_path='recording/video/finalize')
    def recording_video_finalize(self, request, pk=None):
        """O'qituvchi video yuklashni tugatdi — audio ham tayyor bo'lsa,
        fon jarayonida birlashtirish boshlanadi."""
        lesson = self.get_object()
        services.finalize_recording_video(teacher=request.user, lesson=lesson)
        return Response(status=204)

    @action(
        detail=True, methods=['get'], url_path='recording/stream',
        permission_classes=[AllowAny], authentication_classes=[],
    )
    def recording_stream(self, request, pk=None):
        """Video oqimi — faqat imzolangan MUDDATLI token bilan (recording_info
        beradi). Auth header kerak emas (<video src> uchun); doimiy URL yo'q,
        Content-Disposition: inline — brauzer pleerda ochadi."""
        from .models import Lesson as LessonModel

        try:
            lesson = LessonModel.objects.get(pk=pk)
        except (LessonModel.DoesNotExist, ValueError, TypeError):
            raise NotFound(_('Dars topilmadi.'))
        path = services.recording_stream_path(
            lesson=lesson, token=request.query_params.get('t') or '',
        )
        return _ranged_video_response(request, path)


class _FileSlice:
    """Range so'rov uchun chegaralangan fayl oqimi (xotiraga yuklamasdan)."""

    def __init__(self, fileobj, length):
        self._f = fileobj
        self._remaining = length

    def read(self, size=8192):
        if self._remaining <= 0:
            return b''
        chunk = self._f.read(min(size, self._remaining))
        self._remaining -= len(chunk)
        return chunk

    def close(self):
        self._f.close()


_VIDEO_CONTENT_TYPES = {'.mp4': 'video/mp4', '.webm': 'video/webm'}


def _ranged_video_response(request, path):
    """Videoni HTTP Range bilan beradi — pleer o'tkazib ko'ra oladi (seek).
    inline: brauzer "saqlash" emas, pleerda ochadi.

    Content-Type fayl kengaytmasiga qarab tanlanadi — Track Egress+ffmpeg
    birlashtirish endi `.webm` (VP8+Opus, qayta kodlashsiz) chiqaradi,
    eski/fallback yozuvlar `.mp4` bo'lishi ham mumkin."""
    import re

    content_type = _VIDEO_CONTENT_TYPES.get(path.suffix.lower(), 'video/mp4')
    size = path.stat().st_size
    range_header = request.META.get('HTTP_RANGE', '')
    match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if match:
        start = int(match.group(1))
        end = min(int(match.group(2)) if match.group(2) else size - 1, size - 1)
        start = min(start, size - 1)
        length = end - start + 1
        f = open(path, 'rb')
        f.seek(start)
        response = FileResponse(_FileSlice(f, length), status=206, content_type=content_type)
        response['Content-Range'] = f'bytes {start}-{end}/{size}'
        response['Content-Length'] = str(length)
    else:
        response = FileResponse(open(path, 'rb'), content_type=content_type)
        response['Content-Length'] = str(size)
    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'
    response['Cache-Control'] = 'private, no-store'
    return response


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Davomat hisoboti: o'qituvchi -> o'z darslari, o'quvchi -> o'zi, ota-ona -> tasdiqlangan bolalari."""

    serializer_class = AttendanceSerializer
    filterset_fields = ['lesson', 'student']

    def get_permissions(self):
        return [RequirePerm('attendance.view')()]

    def get_queryset(self):
        return selectors.attendance_for(self.request.user)
