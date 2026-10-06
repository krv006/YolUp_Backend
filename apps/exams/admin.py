from django.contrib import admin

from .models import Exam, ExamAttempt, ExamSection, ExamTemplate


class ExamSectionInline(admin.TabularInline):
    model = ExamSection
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'template_key', 'starts_at', 'ends_at']
    list_filter = ['template_key']
    search_fields = ['title', 'course__title']
    inlines = [ExamSectionInline]


@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student', 'finished_at', 'created_at']
