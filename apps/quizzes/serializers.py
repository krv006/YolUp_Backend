import math
import random
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from . import grading
from .models import AnswerResponse, Option, Question, Quiz, QuizAttempt

T = Question.Type
_BLANK_RE = re.compile(r'\{\{(\d+)\}\}')

# ─── Yaratish (o'qituvchi yozadi) ──────────────────────────────────────────


class OptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['text', 'is_correct', 'order']


class PairWriteSerializer(serializers.Serializer):
    left = serializers.CharField(max_length=500)
    right = serializers.CharField(max_length=500)


class BlankWriteSerializer(serializers.Serializer):
    answers = serializers.ListField(
        child=serializers.CharField(max_length=500), allow_empty=False,
    )


class QuestionWriteSerializer(serializers.Serializer):
    """Savol turiga qarab maydonlar `validate()`da tekshiriladi (frontend kontrakti:
    BACKEND_QUIZ_TYPES.md). `type` kelmasa — `single` (eski format)."""

    type = serializers.ChoiceField(choices=Question.Type.choices, default=T.SINGLE)
    text = serializers.CharField()
    points = serializers.IntegerField(min_value=1, max_value=100, default=2)
    order = serializers.IntegerField(min_value=0, required=False)
    options = OptionWriteSerializer(many=True, required=False)
    correct_bool = serializers.BooleanField(required=False)
    accepted_answers = serializers.ListField(
        child=serializers.CharField(max_length=500), required=False,
    )
    tolerance = serializers.FloatField(min_value=0, default=0)
    case_sensitive = serializers.BooleanField(default=False)
    pairs = PairWriteSerializer(many=True, required=False)
    items = serializers.ListField(child=serializers.CharField(max_length=500), required=False)
    blanks = BlankWriteSerializer(many=True, required=False)

    def validate(self, attrs):
        getattr(self, f'_check_{attrs["type"]}')(attrs)
        return attrs

    @staticmethod
    def _fail(field, message):
        raise serializers.ValidationError({field: message})

    def _check_single(self, attrs):
        options = attrs.get('options') or []
        if len(options) < 2:
            self._fail('options', _("Har bir savolda kamida 2 ta variant bo'lishi kerak."))
        if sum(1 for o in options if o.get('is_correct')) != 1:
            self._fail('options', _("Har bir savolda aynan 1 ta to'g'ri variant belgilanishi kerak."))

    def _check_multiple(self, attrs):
        options = attrs.get('options') or []
        if len(options) < 2:
            self._fail('options', _("Har bir savolda kamida 2 ta variant bo'lishi kerak."))
        if not any(o.get('is_correct') for o in options):
            self._fail('options', _("Kamida 1 ta to'g'ri variant belgilanishi kerak."))

    def _check_true_false(self, attrs):
        if 'correct_bool' not in attrs:
            self._fail('correct_bool', _("To'g'ri javob (correct_bool) majburiy."))

    def _check_numeric(self, attrs):
        answers = attrs.get('accepted_answers') or []
        if not answers:
            self._fail('accepted_answers', _('Kamida 1 ta qabul qilinadigan javob kerak.'))
        if any(grading.parse_number(a) is None for a in answers):
            self._fail('accepted_answers', _("Javoblar son ko'rinishida bo'lishi kerak (masalan 3.14)."))
        if not math.isfinite(attrs['tolerance']):
            self._fail('tolerance', _("Tolerantlik chekli son bo'lishi kerak."))

    def _check_text(self, attrs):
        answers = attrs.get('accepted_answers') or []
        if not answers or any(not a.strip() for a in answers):
            self._fail('accepted_answers', _("Kamida 1 ta bo'sh bo'lmagan javob kerak."))

    def _check_matching(self, attrs):
        pairs = attrs.get('pairs') or []
        if len(pairs) < 2:
            self._fail('pairs', _('Kamida 2 ta juft kerak.'))
        lefts = [grading.normalize_text(p['left']) for p in pairs]
        rights = [grading.normalize_text(p['right']) for p in pairs]
        if '' in lefts or '' in rights:
            self._fail('pairs', _("Juft qiymatlari bo'sh bo'lmasligi kerak."))
        if len(set(lefts)) != len(lefts) or len(set(rights)) != len(rights):
            self._fail('pairs', _('Chap va o\'ng qiymatlar takrorlanmasligi kerak.'))

    def _check_ordering(self, attrs):
        items = attrs.get('items') or []
        if len(items) < 2 or any(not i.strip() for i in items):
            self._fail('items', _("Kamida 2 ta bo'sh bo'lmagan element kerak."))

    def _check_fill_blank(self, attrs):
        blanks = attrs.get('blanks') or []
        numbers = sorted(int(n) for n in _BLANK_RE.findall(attrs['text']))
        if not blanks or numbers != list(range(1, len(blanks) + 1)):
            self._fail('blanks', _(
                "Matndagi {{1}}, {{2}}... joylar soni blanks uzunligiga teng bo'lishi kerak.",
            ))
        if any(not a.strip() for b in blanks for a in b['answers']):
            self._fail('blanks', _("Javoblar bo'sh bo'lmasligi kerak."))


class QuizCreateSerializer(serializers.ModelSerializer):
    """Faqat kirish validatsiyasi uchun — obyekt yaratish services.create_quiz'da."""

    questions = QuestionWriteSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ['course', 'subject', 'lesson', 'title', 'description', 'due_at', 'opens_at', 'questions']

    def validate_questions(self, questions):
        if not questions:
            raise serializers.ValidationError(_("Kamida 1 ta savol bo'lishi kerak."))
        return questions

    def validate(self, attrs):
        if attrs.get('course') is None and not attrs.get('subject'):
            raise serializers.ValidationError({'subject': _('Guruh yoki fan tanlanishi shart.')})
        return attrs


# ─── O'qish (ro'yxat / batafsil) ───────────────────────────────────────────


class SubjectLabelMixin(serializers.Serializer):
    subject_label = serializers.CharField(source='get_subject_display', read_only=True)


class QuizListSerializer(SubjectLabelMixin, serializers.ModelSerializer):
    question_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'subject', 'subject_label', 'lesson', 'title', 'description',
            'due_at', 'opens_at', 'question_count', 'created_at',
        ]


class OptionTakeSerializer(serializers.ModelSerializer):
    """O'quvchi/ota-ona ko'radi — `is_correct` YO'Q (javob oldindan ko'rinmasin)."""

    class Meta:
        model = Option
        fields = ['id', 'text', 'order']


class QuestionTakeSerializer(serializers.Serializer):
    """O'quvchi ko'rinishi: javob kaliti YO'Q; matching o'ng tomoni va ordering
    elementlari har so'rovda aralashtiriladi."""

    def to_representation(self, question):
        data = {
            'id': question.id, 'type': question.type, 'text': question.text,
            'points': question.points, 'order': question.order, 'options': [],
        }
        key = question.answer_key or {}
        options = list(question.options.all())
        if question.type in (T.SINGLE, T.MULTIPLE):
            data['options'] = OptionTakeSerializer(options, many=True).data
        elif question.type == T.ORDERING:
            shuffled = options[:]
            random.shuffle(shuffled)
            data['options'] = [{'id': o.id, 'text': o.text} for o in shuffled]
        elif question.type == T.MATCHING:
            pairs = key.get('pairs', [])
            right = [{'id': p['right_id'], 'text': p['right']} for p in pairs]
            random.shuffle(right)
            data['pairs_left'] = [{'id': p['left_id'], 'text': p['left']} for p in pairs]
            data['pairs_right'] = right
        elif question.type == T.FILL_BLANK:
            data['blank_count'] = len(key.get('blanks', []))
        return data


class QuizTakeSerializer(SubjectLabelMixin, serializers.ModelSerializer):
    questions = QuestionTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'subject', 'subject_label', 'lesson', 'title', 'description',
            'due_at', 'opens_at', 'questions',
        ]


class OptionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionDetailSerializer(serializers.Serializer):
    """Faqat o'qituvchi/admin uchun — javob kaliti bilan (yaratishdagi shakl)."""

    def to_representation(self, question):
        data = {
            'id': question.id, 'type': question.type, 'text': question.text,
            'points': question.points, 'order': question.order, 'options': [],
        }
        key = question.answer_key or {}
        options = list(question.options.all())
        qtype = question.type
        if qtype in (T.SINGLE, T.MULTIPLE):
            data['options'] = OptionDetailSerializer(options, many=True).data
        elif qtype == T.TRUE_FALSE:
            data['correct_bool'] = key.get('correct_bool')
        elif qtype == T.NUMERIC:
            data['accepted_answers'] = key.get('accepted_answers', [])
            data['tolerance'] = key.get('tolerance', 0)
        elif qtype == T.TEXT:
            data['accepted_answers'] = key.get('accepted_answers', [])
            data['case_sensitive'] = key.get('case_sensitive', False)
        elif qtype == T.MATCHING:
            data['pairs'] = [{'left': p['left'], 'right': p['right']} for p in key.get('pairs', [])]
        elif qtype == T.ORDERING:
            data['items'] = [o.text for o in options]
        elif qtype == T.FILL_BLANK:
            data['blanks'] = key.get('blanks', [])
        return data


class QuizDetailSerializer(SubjectLabelMixin, serializers.ModelSerializer):
    """Faqat o'qituvchi/admin uchun — to'g'ri javoblar bilan (javob kaliti)."""

    questions = QuestionDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'subject', 'subject_label', 'lesson', 'title', 'description',
            'due_at', 'opens_at', 'questions', 'created_at',
        ]


# ─── Topshirish (o'quvchi) ─────────────────────────────────────────────────


class PairAnswerSerializer(serializers.Serializer):
    left = serializers.CharField()
    right = serializers.CharField()


class AnswerSubmitSerializer(serializers.Serializer):
    """Bitta savolga javob — faqat savol turiga mos maydon o'qiladi
    (eski format `selected_option` `single` bilan bir xil)."""

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_option = serializers.PrimaryKeyRelatedField(
        queryset=Option.objects.all(), required=False, allow_null=True,
    )
    selected_options = serializers.PrimaryKeyRelatedField(
        queryset=Option.objects.all(), many=True, required=False,
    )
    value_bool = serializers.BooleanField(required=False, allow_null=True)
    value_text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, trim_whitespace=False,
    )
    pairs = PairAnswerSerializer(many=True, required=False)
    order = serializers.ListField(child=serializers.CharField(), required=False)
    blanks = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False)


class AttemptSubmitSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)

    def validate_answers(self, answers):
        if not answers:
            raise serializers.ValidationError(_("Kamida 1 ta javob yuborilishi kerak."))
        return answers


class AnswerResultSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.type', read_only=True)
    points = serializers.IntegerField(source='question.points', read_only=True)
    selected_option_text = serializers.CharField(
        source='selected_option.text', read_only=True, default=None,
    )
    correct_option = serializers.SerializerMethodField()
    given_display = serializers.SerializerMethodField()
    correct_display = serializers.SerializerMethodField()

    class Meta:
        model = AnswerResponse
        fields = [
            'question', 'question_text', 'question_type', 'points', 'earned_points',
            'is_correct', 'given_display', 'correct_display',
            'selected_option', 'selected_option_text', 'correct_option',
        ]

    def get_correct_option(self, obj):
        if obj.question.type != T.SINGLE:
            return None
        correct = next((o for o in obj.question.options.all() if o.is_correct), None)
        return {'id': correct.id, 'text': correct.text} if correct else None

    def get_given_display(self, obj):
        if obj.given_display is not None:
            return obj.given_display
        return obj.selected_option.text if obj.selected_option_id else None

    def get_correct_display(self, obj):
        return grading.correct_display(obj.question)


class AttemptResultSerializer(serializers.ModelSerializer):
    """Topshirgandan keyingi natija — har bir savol bo'yicha to'g'ri/xato va
    to'g'ri javob ochiladi (qayta urinishda yaxshilash uchun o'rganish)."""

    answers = AnswerResultSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'student', 'score', 'max_score', 'created_at', 'answers']


class AttemptListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'student', 'student_name', 'score', 'max_score', 'created_at']
