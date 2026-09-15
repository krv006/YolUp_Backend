from django.contrib import admin

from .models import (
    Attendance,
    AttentionCheck,
    Course,
    Enrollment,
    FocusAlert,
    FocusEvent,
    Lesson,
    LessonBan,
    LessonRating,
    LessonRecording,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'subject', 'is_active', 'created_at']
    list_filter = ['is_active', 'subject']
    search_fields = ['title', 'teacher__username']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['course', 'starts_at', 'duration_min', 'status', 'room_name']
    list_filter = ['status']
    search_fields = ['course__title']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['student__username', 'course__title']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'joined_at', 'left_at', 'minutes']
    search_fields = ['student__username', 'lesson__course__title']
    date_hierarchy = 'created_at'


@admin.register(AttentionCheck)
class AttentionCheckAdmin(admin.ModelAdmin):
    """Diqqat tekshiruvi: kimga, qachon yuborilgan va javob berilganmi."""

    list_display = ['student', 'lesson', 'due_at', 'answered_at', 'answered']
    list_filter = [('answered_at', admin.EmptyFieldListFilter)]
    search_fields = ['student__username', 'lesson__course__title']
    date_hierarchy = 'due_at'

    @admin.display(boolean=True, description='Javob berdi')
    def answered(self, obj):
        return obj.answered_at is not None


@admin.register(LessonRating)
class LessonRatingAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'student', 'stars', 'created_at']
    list_filter = ['stars']
    search_fields = ['lesson__course__title', 'student__username']


@admin.register(LessonRecording)
class LessonRecordingAdmin(admin.ModelAdmin):
    """Dars video yozuvlari — holat, fayl, egress ID."""

    list_display = ['lesson', 'title', 'status', 'file_name', 'created_at', 'ended_at']
    list_filter = ['status']
    search_fields = ['lesson__course__title', 'title']


@admin.register(FocusEvent)
class FocusEventAdmin(admin.ModelAdmin):
    """Anti-cheat jurnali: o'quvchi dars oynasidan chiqib-kirishlari."""

    list_display = ['student', 'lesson', 'kind', 'created_at']
    list_filter = ['kind']
    search_fields = ['student__username', 'lesson__course__title']
    date_hierarchy = 'created_at'


@admin.register(FocusAlert)
class FocusAlertAdmin(admin.ModelAdmin):
    """Ota-onaga ko'rinadigan signal — o'quvchi chegaradan ko'p chiqqan darslar."""

    list_display = ['student', 'lesson', 'exit_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['student__username', 'lesson__course__title']


@admin.register(LessonBan)
class LessonBanAdmin(admin.ModelAdmin):
    """O'qituvchi darsdan chetlashtirgan o'quvchilar."""

    list_display = ['student', 'lesson', 'banned_by', 'created_at']
    search_fields = ['student__username', 'lesson__course__title']
