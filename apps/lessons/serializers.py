from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.quizzes.models import Quiz

from . import selectors
from .models import Attendance, Course, Enrollment, Lesson, LessonRating


ATTENDANCE_OPENS_MINUTES = 10


class CourseSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student_count = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()
    is_language_subject = serializers.SerializerMethodField()
    subject_label = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'teacher', 'title', 'subject', 'subject_label', 'description',
            'is_active', 'student_count', 'my_status', 'is_language_subject', 'created_at',
            'lessons_per_week', 'monthly_fee', 'avatar',
        ]
        read_only_fields = ['is_active']
        extra_kwargs = {
            'lessons_per_week': {'min_value': 1, 'max_value': 14},
            'monthly_fee': {'min_value': 0, 'max_value': 1_000_000_000},
        }

    def validate_avatar(self, value):
        """Rasm: JPEG/PNG/WebP, ko'pi bilan 5 MB (bo'sh qiymat — rasmni o'chiradi)."""
        if not value:
            return value
        from PIL import Image

        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(_('Rasm 5 MB dan katta.'))
        try:
            value.seek(0)
            fmt = Image.open(value).format
        except Exception:  # noqa: BLE001
            raise serializers.ValidationError(_('Rasm fayli buzilgan.')) from None
        finally:
            value.seek(0)
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            raise serializers.ValidationError(_('Faqat JPEG, PNG yoki WebP rasm.'))
        return value

    def get_student_count(self, obj) -> int:
        if hasattr(obj, 'list_student_count'):
            return obj.list_student_count
        return obj.enrollments.filter(status=Enrollment.Status.APPROVED).count()

    def get_subject_label(self, obj) -> str:
        """`subject` — barqaror kod (masalan `'chemistry'`), frontend uchun
        emas. `subject_label` esa so'rovning `Accept-Language`iga (uz/ru/en)
        mos tarjima qilingan ko'rsatiladigan nom."""
        return obj.get_subject_display()

    def get_is_language_subject(self, obj) -> bool:
        """Til fani (ingliz/rus/turk) bo'lsa true — frontend vazifa
        yaratishda "tekshiruv turi" (writing/reading/listening/speaking)
        maydonini faqat shu holatda ko'rsatishi kerak."""
        return obj.subject in (
            Course.Subject.ENGLISH, Course.Subject.RUSSIAN, Course.Subject.TURKISH,
            Course.Subject.GERMAN, Course.Subject.FRENCH, Course.Subject.ARABIC,
            Course.Subject.CHINESE, Course.Subject.KOREAN, Course.Subject.JAPANESE,
        )

    def get_my_status(self, obj) -> str | None:
        """So'rov yuborgan foydalanuvchining shu kursdagi yozilish holati (katalog uchun)."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if hasattr(obj, 'my_enrollments'):
            return obj.my_enrollments[0].status if obj.my_enrollments else None
        enrollment = obj.enrollments.filter(student=request.user).first()
        return enrollment.status if enrollment else None


class LessonSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    avg_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    # Mavjud testni shu darsga biriktirish — yozish uchun (Quiz'ning o'zida
    # `lesson` FK bor, Lesson'da emas, shuning uchun bu maydon Lesson modelida
    # yo'q — `views.perform_create`/`perform_update` uni alohida qo'llaydi).
    quiz = serializers.PrimaryKeyRelatedField(
        queryset=Quiz.objects.all(), required=False, allow_null=True, write_only=True,
    )
    # O'qish uchun — hozir shu darsga biriktirilgan test (bo'lsa) id'si.
    quiz_id = serializers.SerializerMethodField()
    # Darslar ro'yxati kartalari uchun (qo'shimcha so'rovsiz): kursdagi o'quvchilar soni; tugagan darsda ishtirokchilar
    # soni va davomat foizi; jonli darsda hozir qo'shilganlar soni; darsga biriktirilgan vazifa
    students_count = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()
    joined_count = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    # O'quvchi uchun (boshqa rollarda null): o'zi qo'ygan baho va qatnashgani (faqat tugagan darsda true/false)
    my_rating = serializers.SerializerMethodField()
    attended = serializers.SerializerMethodField()
    # Jonli darsda yozuv haqiqatan ketyaptimi (REC belgisi shunga qarab); `recording_started_at` — boshlangan vaqt
    recording_active = serializers.SerializerMethodField()
    recording_started_at = serializers.SerializerMethodField()
    # "Davomat ochiq" kartasi chiqadigan vaqt: dars boshlanishidan ATTENDANCE_OPENS_MINUTES oldin
    attendance_opens_at = serializers.SerializerMethodField()
    # Men qo'ygan shaxsiy eslatma (bo'lmasa false/null)
    has_reminder = serializers.SerializerMethodField()
    reminder_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'course_title', 'title', 'note', 'starts_at',
            'duration_min', 'status', 'room_name', 'created_at',
            'avg_rating', 'rating_count', 'quiz', 'quiz_id', 'recurrence', 'recurrence_id',
            'students_count', 'participants_count', 'attendance_rate', 'joined_count', 'assignment',
            'my_rating', 'attended', 'recording_active', 'recording_started_at',
            'attendance_opens_at', 'has_reminder', 'reminder_minutes',
        ]
        read_only_fields = ['room_name', 'status', 'recurrence_id']

    def validate_recurrence(self, value):
        """`{freq: 'weekly', weeks: 1..52, weekdays: [0..6]}` — faqat dars YARATILGANDA (seriya ochish) ma'noli."""
        if value in (None, {}):
            return None
        if self.instance is not None:
            return self.instance.recurrence  # mavjud darsning takrorlanishi tahrirlanmaydi
        if not isinstance(value, dict) or value.get('freq', 'weekly') != 'weekly':
            raise serializers.ValidationError(_("Hozircha faqat haftalik takrorlanish (freq=weekly) bor."))
        weeks, weekdays = value.get('weeks'), value.get('weekdays')
        if not isinstance(weeks, int) or isinstance(weeks, bool) or not 1 <= weeks <= 52:
            raise serializers.ValidationError(_("`weeks` 1 dan 52 gacha butun son bo'lishi kerak."))
        if (
            not isinstance(weekdays, list) or not 1 <= len(weekdays) <= 7
            or any(not isinstance(d, int) or isinstance(d, bool) or not 0 <= d <= 6 for d in weekdays)
        ):
            raise serializers.ValidationError(_("`weekdays` — hafta kunlari ro'yxati (0=dushanba … 6=yakshanba)."))
        return {'freq': 'weekly', 'weeks': weeks, 'weekdays': sorted(set(weekdays))}

    def validate_starts_at(self, value):
        # Faqat YANGI dars yaratishda tekshiramiz — mavjud (o'tgan) darsni
        # boshqa maydon bo'yicha tahrirlash bloklanib qolmasin.
        if self.instance is None and value < timezone.now():
            raise serializers.ValidationError(_("Dars boshlanish vaqti o'tgan bo'lishi mumkin emas."))
        return value

    def validate(self, attrs):
        quiz = attrs.get('quiz')
        if quiz is not None:
            course = attrs.get('course') or (self.instance.course if self.instance else None)
            if course is not None and quiz.course_id != course.id:
                raise serializers.ValidationError({'quiz': _("Bu test boshqa kursga tegishli.")})
            target_lesson_id = self.instance.id if self.instance else None
            if quiz.lesson_id is not None and quiz.lesson_id != target_lesson_id:
                raise serializers.ValidationError(
                    {'quiz': _('Bu test allaqachon boshqa darsga biriktirilgan.')},
                )
        return attrs

    def get_avg_rating(self, obj) -> float | None:
        from django.db.models import Avg
        result = obj.card_avg_rating if hasattr(obj, 'card_avg_rating') else obj.ratings.aggregate(avg=Avg('stars'))['avg']
        return round(result, 1) if result else None

    def _recording(self, obj):
        if obj.status != Lesson.Status.LIVE:
            return None
        if hasattr(obj, 'card_recording_started'):  # ro'yxat so'rovi oldindan hisoblagan
            return obj.card_recording_started
        recording = getattr(obj, 'recording', None) if obj.pk else None
        return recording.video_started_at or recording.audio_started_at if recording and recording.status == 'recording' else None

    def get_has_reminder(self, obj) -> bool:
        return getattr(obj, 'my_reminder_minutes', None) is not None

    def get_reminder_minutes(self, obj):
        return getattr(obj, 'my_reminder_minutes', None)

    def get_attendance_opens_at(self, obj):
        from datetime import timedelta

        return obj.starts_at - timedelta(minutes=ATTENDANCE_OPENS_MINUTES) if obj.starts_at else None

    def get_recording_active(self, obj) -> bool:
        return self._recording(obj) is not None

    def get_recording_started_at(self, obj):
        return self._recording(obj)

    def get_my_rating(self, obj) -> int | None:
        return getattr(obj, 'my_rating_value', None)

    def get_attended(self, obj) -> bool | None:
        return getattr(obj, 'my_attended', None)

    def get_quiz_id(self, obj) -> str | None:
        if hasattr(obj, 'card_quiz_id'):  # ro'yxat so'rovi oldindan hisoblagan
            return str(obj.card_quiz_id) if obj.card_quiz_id else None
        quiz = obj.quizzes.first()
        return str(quiz.id) if quiz else None

    # Ro'yxat so'rovi `annotate` qilgan qiymatlarni (`_students` va h.k.) ishlatadi; yakka dars/boshqa joylarda
    # (annotatsiya yo'q) o'zi hisoblaydi — shu tufayli ro'yxatda har dars uchun qo'shimcha so'rov ketmaydi.
    def _students(self, obj) -> int:
        value = getattr(obj, 'card_students', None)
        if value is None:
            value = Enrollment.objects.filter(course_id=obj.course_id, status=Enrollment.Status.APPROVED).count()
        return value or 0

    def _attended(self, obj) -> int:
        value = getattr(obj, 'card_attended', None)
        if value is None:
            value = Attendance.objects.filter(lesson=obj, joined_at__isnull=False).count()
        return value or 0

    def get_students_count(self, obj) -> int:
        return self._students(obj)

    def get_participants_count(self, obj) -> int | None:
        return self._attended(obj) if obj.status == Lesson.Status.FINISHED else None

    def get_attendance_rate(self, obj) -> int | None:
        if obj.status != Lesson.Status.FINISHED:
            return None
        students = self._students(obj)
        return round(self._attended(obj) * 100 / students) if students else 0

    def get_joined_count(self, obj) -> int | None:
        """Jonli darsda hozir xonada turgan o'quvchilar soni (kirgan, hali chiqmagan)."""
        if obj.status != Lesson.Status.LIVE:
            return None
        value = getattr(obj, 'card_present', None)
        if value is None:
            value = Attendance.objects.filter(lesson=obj, joined_at__isnull=False, left_at__isnull=True).count()
        return value or 0

    def get_assignment(self, obj) -> dict | None:
        """Darsga biriktirilgan (qoralama bo'lmagan) birinchi vazifa: `{id, title}`."""
        rows = getattr(obj, 'card_assignments', None)
        if rows is None:
            from apps.homework.models import Assignment

            rows = list(Assignment.objects.filter(lesson=obj).exclude(status=Assignment.Status.DRAFT).order_by('created_at')[:1])
        return {'id': str(rows[0].id), 'title': rows[0].title} if rows else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        recurrence = data.get('recurrence')
        if isinstance(recurrence, dict) and instance.recurrence_id:
            # Seriya qachon tugaydi: oxirgi darsning sanasi
            last = getattr(instance, 'card_series_end', None)
            if last is None:
                last = Lesson.objects.filter(recurrence_id=instance.recurrence_id).order_by('-starts_at').values_list(
                    'starts_at', flat=True).first()
            data['recurrence'] = {**recurrence, 'ends_on': timezone.localtime(last).date().isoformat() if last else None}
        return data

    def get_rating_count(self, obj) -> int:
        return obj.card_rating_count if hasattr(obj, 'card_rating_count') else obj.ratings.count()


class LessonRatingSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    # "Mening baholarim" ro'yxati: izoh ostida guruh va dars nomi
    lesson_title = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='lesson.course.title', read_only=True)
    course_id = serializers.UUIDField(source='lesson.course_id', read_only=True)

    class Meta:
        model = LessonRating
        fields = [
            'id', 'lesson', 'lesson_title', 'course_id', 'course_title', 'student', 'stars', 'description', 'created_at',
        ]
        read_only_fields = ['lesson']

    def get_lesson_title(self, obj) -> str:
        return obj.lesson.title or obj.lesson.course.title


class RateLessonSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    description = serializers.CharField(required=False, allow_blank=True, default='')


class ScheduleLessonsSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        min_length=1, max_length=7,
    )
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    weeks = serializers.IntegerField(min_value=1, max_value=52)
    start_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError(
                {'end_time': _("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak.")},
            )
        if data['start_date'] < timezone.now().date():
            raise serializers.ValidationError(
                {'start_date': _("Boshlanish sanasi o'tgan bo'lishi mumkin emas.")},
            )
        return data


class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'student', 'status', 'created_at']


class AttendanceSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    lesson_title = serializers.SerializerMethodField()
    minutes = serializers.IntegerField(read_only=True)
    attention_total = serializers.SerializerMethodField()
    attention_answered = serializers.SerializerMethodField()
    focus_exits = serializers.SerializerMethodField()
    focus = serializers.SerializerMethodField()
    focus_alert = serializers.SerializerMethodField()
    focus_percent = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'lesson', 'lesson_title', 'student', 'joined_at', 'left_at', 'minutes',
            'attention_total', 'attention_answered', 'focus_exits', 'focus', 'focus_alert', 'focus_percent',
        ]

    def get_lesson_title(self, obj) -> str:
        return obj.lesson.title or obj.lesson.course.title

    # Ro'yxat ko'rinishi `extras` ni (selectors.attendance_extras) kontekstga beradi — shunda har qator uchun alohida so'rov
    # ketmaydi; yakka qator (extras yo'q) eskicha hisoblanadi.
    def _extras(self):
        return self.context.get('extras')

    def get_attention_total(self, obj) -> int:
        extras = self._extras()
        if extras is not None:
            return extras['checks'].get((obj.lesson_id, obj.student_id), (0, 0))[0]
        return obj.lesson.attention_checks.filter(student=obj.student).count()

    def get_attention_answered(self, obj) -> int:
        extras = self._extras()
        if extras is not None:
            return extras['checks'].get((obj.lesson_id, obj.student_id), (0, 0))[1]
        return obj.lesson.attention_checks.filter(
            student=obj.student, answered_at__isnull=False,
        ).count()

    def _focus(self, obj) -> dict:
        cached = obj.__dict__.get('_focus_summary')
        if cached is None:
            extras = self._extras()
            if extras is not None:
                cached = selectors.focus_summary_from(extras['events'].get((obj.lesson_id, obj.student_id), []), obj.left_at)
            else:
                cached = selectors.focus_summary(obj.lesson, obj.student)
            obj.__dict__['_focus_summary'] = cached
        return cached

    def get_focus_exits(self, obj) -> int:
        """O'quvchi dars davomida necha marta oynadan chiqib ketgani (anti-cheat)."""
        return self._focus(obj)['exits']

    def get_focus(self, obj) -> dict:
        """Chiqish-qaytish tahlili: jami/eng uzun yo'qlik + taymlayn
        (qachon chiqdi, qachon qaytdi, necha sekund turdi)."""
        return self._focus(obj)

    def get_focus_percent(self, obj) -> int | None:
        """Darsda necha foiz vaqt e'tibor bilan o'tirgani: 100 − (oynadan tashqarida bo'lgan vaqt / darsda turgan vaqt).
        Hisoblab bo'lmasa (kirgan/chiqqan vaqt yo'q) — `null`."""
        if not obj.joined_at or not obj.left_at:
            return None
        total = (obj.left_at - obj.joined_at).total_seconds()
        if total <= 0:
            return None
        away = self._focus(obj).get('away_seconds') or 0
        return max(0, min(100, round(100 - away * 100 / total)))

    def get_focus_alert(self, obj) -> bool:
        """Chegaradan oshib, ota-onaga signal yaratilganmi (FOCUS_PARENT_ALERT_THRESHOLD)."""
        extras = self._extras()
        if extras is not None:
            return (obj.lesson_id, obj.student_id) in extras['alerts']
        return obj.lesson.focus_alerts.filter(student=obj.student).exists()
