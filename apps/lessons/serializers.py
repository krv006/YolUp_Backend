from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.quizzes.models import Quiz

from . import selectors
from .models import Attendance, Course, Enrollment, Lesson, LessonRating


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
        ]
        read_only_fields = ['is_active']

    def get_student_count(self, obj) -> int:
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

    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'course_title', 'starts_at',
            'duration_min', 'status', 'room_name', 'created_at',
            'avg_rating', 'rating_count', 'quiz', 'quiz_id',
        ]
        read_only_fields = ['room_name', 'status']

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
        result = obj.ratings.aggregate(avg=Avg('stars'))['avg']
        return round(result, 1) if result else None

    def get_quiz_id(self, obj) -> str | None:
        quiz = obj.quizzes.first()
        return str(quiz.id) if quiz else None

    def get_rating_count(self, obj) -> int:
        return obj.ratings.count()


class LessonRatingSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = LessonRating
        fields = ['id', 'lesson', 'student', 'stars', 'description', 'created_at']
        read_only_fields = ['lesson']


class RateLessonSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    description = serializers.CharField(required=False, allow_blank=True, default='')


class ScheduleLessonsSerializer(serializers.Serializer):
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
    lesson_title = serializers.CharField(source='lesson.course.title', read_only=True)
    minutes = serializers.IntegerField(read_only=True)
    attention_total = serializers.SerializerMethodField()
    attention_answered = serializers.SerializerMethodField()
    focus_exits = serializers.SerializerMethodField()
    focus = serializers.SerializerMethodField()
    focus_alert = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'lesson', 'lesson_title', 'student', 'joined_at', 'left_at', 'minutes',
            'attention_total', 'attention_answered', 'focus_exits', 'focus', 'focus_alert',
        ]

    def get_attention_total(self, obj) -> int:
        return obj.lesson.attention_checks.filter(student=obj.student).count()

    def get_attention_answered(self, obj) -> int:
        return obj.lesson.attention_checks.filter(
            student=obj.student, answered_at__isnull=False,
        ).count()

    def get_focus_exits(self, obj) -> int:
        """O'quvchi dars davomida necha marta oynadan chiqib ketgani (anti-cheat)."""
        return obj.lesson.focus_events.filter(student=obj.student, kind='exit').count()

    def get_focus(self, obj) -> dict:
        """Chiqish-qaytish tahlili: jami/eng uzun yo'qlik + taymlayn
        (qachon chiqdi, qachon qaytdi, necha sekund turdi)."""
        return selectors.focus_summary(obj.lesson, obj.student)

    def get_focus_alert(self, obj) -> bool:
        """Chegaradan oshib, ota-onaga signal yaratilganmi (FOCUS_PARENT_ALERT_THRESHOLD)."""
        return obj.lesson.focus_alerts.filter(student=obj.student).exists()
