from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import AnswerResponse, Option, Question, Quiz, QuizAttempt

# ─── Yaratish (o'qituvchi yozadi) ──────────────────────────────────────────


class OptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['text', 'is_correct', 'order']


class QuestionWriteSerializer(serializers.ModelSerializer):
    options = OptionWriteSerializer(many=True)

    class Meta:
        model = Question
        fields = ['text', 'points', 'order', 'options']

    def validate_options(self, options):
        if len(options) < 2:
            raise serializers.ValidationError(_("Har bir savolda kamida 2 ta variant bo'lishi kerak."))
        if sum(1 for o in options if o.get('is_correct')) != 1:
            raise serializers.ValidationError(_("Har bir savolda aynan 1 ta to'g'ri variant belgilanishi kerak."))
        return options


class QuizCreateSerializer(serializers.ModelSerializer):
    """Faqat kirish validatsiyasi uchun — obyekt yaratish services.create_quiz'da."""

    questions = QuestionWriteSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ['course', 'lesson', 'title', 'description', 'due_at', 'opens_at', 'questions']

    def validate_questions(self, questions):
        if not questions:
            raise serializers.ValidationError(_("Kamida 1 ta savol bo'lishi kerak."))
        return questions


# ─── O'qish (ro'yxat / batafsil) ───────────────────────────────────────────


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'lesson', 'title', 'description', 'due_at', 'opens_at',
            'question_count', 'created_at',
        ]


class OptionTakeSerializer(serializers.ModelSerializer):
    """O'quvchi/ota-ona ko'radi — `is_correct` YO'Q (javob oldindan ko'rinmasin)."""

    class Meta:
        model = Option
        fields = ['id', 'text', 'order']


class QuestionTakeSerializer(serializers.ModelSerializer):
    options = OptionTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'points', 'order', 'options']


class QuizTakeSerializer(serializers.ModelSerializer):
    questions = QuestionTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'course', 'lesson', 'title', 'description', 'due_at', 'opens_at', 'questions']


class OptionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionDetailSerializer(serializers.ModelSerializer):
    options = OptionDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'points', 'order', 'options']


class QuizDetailSerializer(serializers.ModelSerializer):
    """Faqat o'qituvchi/admin uchun — to'g'ri javoblar bilan (javob kaliti)."""

    questions = QuestionDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'lesson', 'title', 'description', 'due_at', 'opens_at',
            'questions', 'created_at',
        ]


# ─── Topshirish (o'quvchi) ─────────────────────────────────────────────────


class AnswerSubmitSerializer(serializers.Serializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    selected_option = serializers.PrimaryKeyRelatedField(queryset=Option.objects.all())


class AttemptSubmitSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)

    def validate_answers(self, answers):
        if not answers:
            raise serializers.ValidationError(_("Kamida 1 ta javob yuborilishi kerak."))
        return answers


class AnswerResultSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_option_text = serializers.CharField(
        source='selected_option.text', read_only=True, default=None,
    )
    correct_option = serializers.SerializerMethodField()

    class Meta:
        model = AnswerResponse
        fields = [
            'question', 'question_text', 'selected_option', 'selected_option_text',
            'is_correct', 'correct_option',
        ]

    def get_correct_option(self, obj):
        correct = next((o for o in obj.question.options.all() if o.is_correct), None)
        return {'id': correct.id, 'text': correct.text} if correct else None


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
