from django.contrib import admin

from .models import Option, Question, Quiz, QuizAttempt


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'lesson', 'created_at']
    search_fields = ['title', 'course__title']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'type', 'quiz', 'points']
    inlines = [OptionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'student', 'score', 'max_score', 'created_at']
    list_filter = ['quiz']
