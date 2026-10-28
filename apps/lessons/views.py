"""Lessons views — yupqa qatlam: HTTP <-> service/selector."""
from django.db.models import Q
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.core.permissions import RequirePerm

from . import attendance_summary, selectors, services
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
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # `avatar` rasmi multipart bilan yuklanadi

    @property
    def throttle_scope(self):
        """Taklif kodini taxmin qilib ko'rishdan himoya: `join` auth chegarasi (30/daq) bilan."""
        return 'auth' if getattr(self, 'action', None) == 'join' else None
    search_fields = ['title', 'subject']
    ordering_fields = ['created_at', 'title']

    def get_permissions(self):
        if self.action == 'create':
            return [RequirePerm('course.create')()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [RequirePerm('course.edit')()]
        if self.action in ('enroll', 'unenroll', 'catalog'):
            return [RequirePerm('course.enroll')()]
        if self.action == 'attendance_summary':
            return [RequirePerm('attendance.view')()]
        if self.action in ('invite_link',):
            return [RequirePerm('course.edit')()]  # faqat o'qituvchi (kurs egaligi service'da tekshiriladi)
        if self.action == 'join':
            return [RequirePerm('course.enroll')()]
        if self.action in ('requests', 'respond_request'):
            return [RequirePerm('course.edit')()]  # faqat o'qituvchi (o'z kurslari service'da tekshiriladi)
        if self.action == 'schedule':
            return [RequirePerm('lesson.schedule')()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.action == 'catalog':
            return selectors.with_course_stats(Course.objects.filter(is_active=True), self.request.user).order_by('title')
        qs = selectors.courses_for(self.request.user)
        # ro'yxat/ko'rish uchun statistika oldindan yuklanadi; yozish amallarida (update/destroy...) kerak emas
        return selectors.with_course_stats(qs, self.request.user) if self.action in ('list', 'retrieve') else qs

    @action(detail=False)
    def catalog(self, request):
        """Yozilish uchun ochiq kurslar — o'quvchi/ota-ona ko'radi (courses_for faqat yozilganlarni beradi)."""
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=True, url_path='attendance/summary')
    def attendance_summary(self, request, pk=None):
        """Davomat va fokus foizi: `?range=all|30d|month`. O'qituvchi — hamma o'quvchi; o'quvchi — faqat o'zi;
        ota-ona — tasdiqlangan bolalari."""
        range_key = request.query_params.get('range', 'all')
        if range_key not in attendance_summary.RANGES:
            raise ValidationError({'range': _("all, 30d yoki month bo'lishi kerak.")})
        return Response(attendance_summary.course_summary(
            course=self.get_object(), viewer=request.user, range_key=range_key,
        ))

    @action(detail=True, methods=['get', 'post', 'delete'], url_path='invite-link')
    def invite_link(self, request, pk=None):
        """Taklif havolasi. GET — mavjudi (yo'q bo'lsa maydonlar `null`); POST — yangisini yaratadi (eskisi bekor)
        `{require_approval?, expires_in_days?}`; DELETE — bekor qiladi."""
        course = self.get_object()
        if request.method == 'DELETE':
            services.revoke_invite_link(teacher=request.user, course=course, request=request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.method == 'POST':
            approval = request.data.get('require_approval')
            if isinstance(approval, str):
                approval = approval.lower() in ('1', 'true', 'yes')
            data = services.create_invite_link(
                teacher=request.user, course=course, require_approval=approval,
                expires_in_days=request.data.get('expires_in_days'), request=request,
            )
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(services.get_invite_link(teacher=request.user, course=course))

    @action(detail=False, methods=['post'])
    def join(self, request):
        """O'quvchi taklif kodi bilan guruhga qo'shiladi: `{code}` -> `{course_id, status: joined | pending}`."""
        return Response(services.join_by_code(student=request.user, code=request.data.get('code'), request=request))

    @action(detail=False)
    def subjects(self, request):
        """Kurs yaratishda tanlanadigan tayin fanlar ro'yxati — o'qituvchi
        o'zi fan nomini yozmaydi, shu ro'yxatdan tanlaydi. `label` so'rovning
        `Accept-Language`iga (uz/ru/en) mos tarjima qilingan."""
        return Response([
            {'value': value, 'label': str(label)} for value, label in Course.Subject.choices
        ])

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
        if request.query_params.get('with_presence'):
            return Response(_students_with_presence_rows(request, course))
        qs = course.enrollments.select_related('student').order_by('student__first_name')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(EnrollmentSerializer(page, many=True).data)


def _students_with_presence_rows(request, course) -> list:
    """Tasdiqlangan o'quvchilar + onlayn holati va oxirgi faolligi ("Onlayn", "10 daqiqa oldin")."""
    from apps.chat import presence

    students = list(
        User.objects.filter(
            enrollments__course=course, enrollments__status=Enrollment.Status.APPROVED,
        ).distinct().order_by('first_name', 'last_name', 'username')[:500]
    )
    online = presence.online_ids([s.id for s in students])
    rows = []
    for student in students:
        avatar = request.build_absolute_uri(student.avatar.url) if student.avatar else None
        rows.append({
            'id': str(student.id), 'name': student.get_full_name() or student.username,
            'username': student.username, 'avatar': avatar,
            'is_online': str(student.id) in online, 'last_seen': student.last_seen_at,
        })
    return rows


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
        if self.action == 'cancel':
            return [RequirePerm('lesson.cancel')()]
        if self.action == 'rate':
            return [RequirePerm('lesson.rate')()]
        if self.action in ('recording_stream', 'board_preview'):
            # Video oqimi / doska rasmi imzolangan muddatli token bilan himoyalangan —
            # <video src> Authorization header yubora olmaydi
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = selectors.lessons_for(self.request.user)
        if self.action in ('list', 'retrieve'):
            qs = selectors.with_card_stats(qs)
            if self.request.user.role == 'student':
                qs = selectors.with_student_marks(qs, self.request.user)
        return qs

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        course = data.pop('course')
        recurrence = data.pop('recurrence', None)
        if recurrence:
            # `recurrence` bilan: shu dars va uning haftalik takrorlari bitta seriya sifatida yaratiladi
            lessons = services.schedule_series_from(
                teacher=self.request.user, course=course, starts_at=data['starts_at'],
                duration_min=data.get('duration_min') or 45, recurrence=recurrence,
                title=data.get('title', ''), note=data.get('note', ''), request=self.request,
            )
            quiz = data.get('quiz')
            if quiz is not None:
                services.update_lesson_quiz(teacher=self.request.user, lesson=lessons[0], quiz=quiz, request=self.request)
            serializer.instance = lessons[0]
            return
        serializer.instance = services.schedule_lesson(
            teacher=self.request.user, course=course, request=self.request, **data,
        )

    def perform_update(self, serializer):
        # `quiz` Lesson modelining o'z maydoni emas (Quiz'ning `lesson` FK'si
        # orqali teskari bog'lanadi) — shuning uchun `serializer.save()`dan
        # OLDIN chiqarib olib, alohida service orqali qo'llaymiz.
        has_quiz = 'quiz' in serializer.validated_data
        quiz = serializer.validated_data.pop('quiz', None)
        scope = self.request.query_params.get('scope', 'one')
        if scope not in ('one', 'series'):
            raise ValidationError({'scope': _("'one' yoki 'series' bo'lishi kerak.")})
        old_start = serializer.instance.starts_at
        lesson = serializer.save()
        if scope == 'series' and lesson.recurrence_id:
            changes = {
                field: getattr(lesson, field) for field in ('title', 'note', 'duration_min')
                if field in serializer.validated_data
            }
            services.apply_to_series(lesson=lesson, changes=changes, shift=lesson.starts_at - old_start)
        if has_quiz:
            services.update_lesson_quiz(
                teacher=self.request.user, lesson=lesson, quiz=quiz, request=self.request,
            )

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """Vaqt to'qnashuvi: `?start=<ISO vaqt>&duration=<daqiqa>[&exclude=<dars id>]` — o'qituvchining shu vaqtga to'g'ri
        keladigan boshqa darslari. Javob: `{has_conflict, lessons: [...]}`."""
        if request.user.role != User.Role.TEACHER:
            raise PermissionDenied(_("Faqat o'qituvchi uchun."))
        return Response(services.lesson_conflicts(
            teacher=request.user, start=request.query_params.get('start'),
            duration=request.query_params.get('duration'), exclude=request.query_params.get('exclude'),
        ))

    @action(detail=True, methods=['get'])
    def waiting(self, request, pk=None):
        """Darsga kirish ekrani: hozir xonada kutayotgan o'quvchilar. `{waiting_count, total_count, students}`
        (`students` ro'yxati — faqat o'qituvchiga)."""
        from apps.live import services as live_services

        return Response(live_services.lesson_waiting(user=request.user, lesson_id=pk))

    @action(detail=True, methods=['get'], url_path='board')
    def board(self, request, pk=None):
        """`GET /board/{id}/` bilan bir xil (yozuv sahifasi uchun qulay manzil)."""
        from apps.board import services as board_services

        return Response(board_services.get_board(user=request.user, lesson_id=pk))

    @action(detail=True, methods=['get'], url_path='board/pdf')
    def board_pdf(self, request, pk=None):
        """Doska PDF — dars tugagandan keyin ham ishlaydi."""
        from apps.board import services as board_services

        path = board_services.pdf_file(user=request.user, lesson_id=pk)
        response = FileResponse(open(path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="doska.pdf"'
        response['Cache-Control'] = 'no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @action(
        detail=True, methods=['get'], url_path=r'board/preview/(?P<index>\d+)',
        permission_classes=[AllowAny], authentication_classes=[],
    )
    def board_preview(self, request, pk=None, index=None):
        """Doska sahifasining kichik rasmi (PNG) — imzolangan muddatli havola bilan (`recording` javobidagi
        `board_page_previews[].image_url`); `<img src>` Authorization sarlavhasi yubora olmaydi."""
        from django.http import HttpResponse

        from .models import Lesson as LessonModel

        try:
            lesson = LessonModel.objects.get(pk=pk)
        except (LessonModel.DoesNotExist, ValueError, TypeError):
            raise NotFound(_('Dars topilmadi.'))
        png = services.board_preview_png(lesson=lesson, index=int(index), token=request.query_params.get('t') or '')
        response = HttpResponse(png, content_type='image/png')
        response['Cache-Control'] = 'private, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

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
    def cancel(self, request, pk=None):
        """Darsni bekor qilish (o'chirmasdan): `?scope=one|series`. Jadvalda `cancelled` holatida qoladi, o'quvchilarga
        bildirishnoma boradi."""
        lesson = self.get_object()
        targets = services.cancel_lesson(
            teacher=request.user, lesson=lesson, scope=request.query_params.get('scope', 'one'), request=request,
        )
        lesson.refresh_from_db()
        return Response({**LessonSerializer(lesson).data, 'cancelled_count': len(targets)})

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

    @action(detail=True, methods=['post'], url_path='recording/share')
    def recording_share(self, request, pk=None):
        """O'qituvchi tayyor yozuvni guruh chatiga yuboradi (havola bilan xabar). Javob: `{ok, message_id}`."""
        lesson = self.get_object()
        message = services.share_recording(teacher=request.user, lesson=lesson)
        return Response({'ok': True, 'message_id': str(message.id)}, status=status.HTTP_201_CREATED)

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
            session=request.data.get('session'), index=request.data.get('index'),
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
            session=request.data.get('session'), index=request.data.get('index'),
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


_VIDEO_CONTENT_TYPES = {'.mp4': 'video/mp4', '.webm': 'video/webm', '.m4a': 'audio/mp4'}


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

    def list(self, request, *args, **kwargs):
        """Sahifadagi qatorlar uchun e'tibor/fokus ma'lumotlari bitta guruhli yuklash bilan (har qatorga alohida so'rov emas)."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = list(page if page is not None else queryset)
        context = {**self.get_serializer_context(), 'extras': selectors.attendance_extras(rows)}
        data = self.get_serializer(rows, many=True, context=context).data
        return self.get_paginated_response(data) if page is not None else Response(data)
