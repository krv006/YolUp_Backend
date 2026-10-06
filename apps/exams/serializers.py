"""Exams serializerlari — kiruvchi ma'lumotlarni tekshirish va chiqish ko'rinishlari."""
from django.utils import timezone
from rest_framework import serializers

from apps.lessons.models import Course
from apps.quizzes.models import Quiz
from apps.quizzes.serializers import AnswerSubmitSerializer, GroupReadSerializer, QuestionTakeSerializer

from . import services
from .models import Exam, ExamSection


class ExamSectionInputSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=50)
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())
    # Shablondagi standart vaqtni shu imtihon uchun o'zgartirish (masalan,
    # Milliy sertifikat: matematika 150, boshqa fan boshqacha)
    minutes = serializers.IntegerField(
        required=False, min_value=1, max_value=services.MAX_SECTION_MINUTES,
    )


class ExamCreateSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    template = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=200)
    starts_at = serializers.DateTimeField()
    sections = ExamSectionInputSerializer(many=True)


class ExamUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    starts_at = serializers.DateTimeField(required=False)


class TemplateWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    items = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    scoring = serializers.DictField(required=False, default=dict)


class AnswersSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)

    def validate_answers(self, answers):
        if not answers:
            raise serializers.ValidationError('Kamida 1 ta javob yuborilishi kerak.')
        return answers


class AIApproveSerializer(serializers.Serializer):
    # Berilmasa — AI taklif qilgan band tasdiqlanadi
    band = serializers.FloatField(required=False)


class ManualScoresSerializer(serializers.Serializer):
    scores = serializers.DictField(child=serializers.FloatField(), allow_empty=False)


def exam_summary(exam: Exam, now=None) -> dict:
    now = now or timezone.now()
    return {
        'id': exam.id, 'course': exam.course_id, 'course_title': exam.course.title,
        'title': exam.title, 'template_key': exam.template_key,
        'engine': exam.scoring.get('type') or 'percent',
        'starts_at': exam.starts_at, 'ends_at': exam.ends_at,
        'total_minutes': int((exam.ends_at - exam.starts_at).total_seconds() // 60),
        'state': services.exam_state(exam, now), 'server_now': now,
    }


def exam_detail(exam: Exam, user, now=None) -> dict:
    """Bo'limlar jadvali bilan. Test (`quiz`) identifikatorini faqat
    o'qituvchi/admin ko'radi."""
    data = exam_summary(exam, now)
    sections = list(exam.sections.all())
    windows = {s.id: (start, end) for s, start, end in services.timeline(exam, sections)}
    staff = user.role not in ('student', 'parent')
    items = []
    for section in sections:
        start, end = windows.get(section.id, (None, None))
        item = {
            'order': section.order, 'kind': section.kind, 'key': section.key,
            'group': section.group, 'title': section.title, 'minutes': section.minutes,
            'manual': section.manual, 'starts_at': start, 'ends_at': end,
        }
        if staff:
            item['quiz'] = section.quiz_id
        items.append(item)
    data['sections'] = items
    return data


def current_response(payload: dict, request=None) -> dict:
    item = payload.get('item')
    if item and 'questions' in item:
        context = {'request': request}
        item = {
            **item,
            'groups': GroupReadSerializer(item.get('groups', []), many=True, context=context).data,
            'questions': QuestionTakeSerializer(item['questions'], many=True).data,
        }
        payload = {**payload, 'item': item}
    return payload


__all__ = [
    'AIApproveSerializer', 'AnswersSerializer', 'ExamCreateSerializer', 'ExamSection', 'ExamUpdateSerializer',
    'ManualScoresSerializer', 'TemplateWriteSerializer', 'current_response', 'exam_detail', 'exam_summary',
]
