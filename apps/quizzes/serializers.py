from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.lessons.models import Course

from .models import AnswerResponse, MockTest, MockTestAttempt, MockTestSection, Option, Question, Quiz, QuizAttempt

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


# ─── Mock Test (imtihon-simulyatsiyasi) ────────────────────────────────────


class MockTestCreateSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    time_limit_minutes = serializers.IntegerField(min_value=1)
    quizzes = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all(), many=True)

    def validate_quizzes(self, quizzes):
        if not quizzes:
            raise serializers.ValidationError(_("Kamida 1 ta test tanlanishi kerak."))
        return quizzes


class MockTestSectionSerializer(serializers.ModelSerializer):
    quiz_id = serializers.UUIDField(source='quiz.id', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    question_count = serializers.IntegerField(source='quiz.questions.count', read_only=True)

    class Meta:
        model = MockTestSection
        fields = ['order', 'quiz_id', 'quiz_title', 'question_count']


class MockTestListSerializer(serializers.ModelSerializer):
    section_count = serializers.IntegerField(source='sections.count', read_only=True)

    class Meta:
        model = MockTest
        fields = [
            'id', 'course', 'title', 'description', 'time_limit_minutes',
            'section_count', 'created_at',
        ]


class MockTestDetailSerializer(serializers.ModelSerializer):
    """O'qituvchi/admin uchun — tarkibidagi bo'limlar (testlar) ro'yxati bilan."""

    sections = MockTestSectionSerializer(many=True, read_only=True)

    class Meta:
        model = MockTest
        fields = ['id', 'course', 'title', 'description', 'time_limit_minutes', 'sections', 'created_at']


class MockTestTakeSerializer(serializers.ModelSerializer):
    """O'quvchi `start` qilishdan OLDIN ko'radigan preview — savollar yo'q,
    faqat bo'lim sarlavhalari (nechta savol) va vaqt chegarasi."""

    sections = MockTestSectionSerializer(many=True, read_only=True)

    class Meta:
        model = MockTest
        fields = ['id', 'course', 'title', 'description', 'time_limit_minutes', 'sections']


class MockTestAttemptStartSerializer(serializers.ModelSerializer):
    """`start` javobi — endi vaqt ketyapti: barcha bo'lim savollari (to'g'ri
    javobsiz, `QuizTakeSerializer` bilan bir xil) va topshirish muddati birga
    qaytadi."""

    deadline = serializers.DateTimeField(read_only=True)
    sections = serializers.SerializerMethodField()

    class Meta:
        model = MockTestAttempt
        fields = ['id', 'mock_test', 'started_at', 'deadline', 'sections']

    def get_sections(self, attempt):
        sections = attempt.mock_test.sections.select_related('quiz').prefetch_related('quiz__questions__options')
        return [
            {'order': section.order, 'quiz': QuizTakeSerializer(section.quiz).data}
            for section in sections
        ]


class MockTestSectionAnswersSerializer(serializers.Serializer):
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())
    answers = AnswerSubmitSerializer(many=True)


class MockTestSubmitSerializer(serializers.Serializer):
    sections = MockTestSectionAnswersSerializer(many=True)

    def validate_sections(self, sections):
        if not sections:
            raise serializers.ValidationError(_("Kamida 1 ta bo'lim javobi yuborilishi kerak."))
        return sections


class MockTestAttemptResultSerializer(serializers.ModelSerializer):
    """Topshirgandan keyingi yakuniy natija — jami ball + har bir bo'lim
    (test) bo'yicha batafsil natija (`AttemptResultSerializer` bilan bir xil)."""

    total_score = serializers.IntegerField(read_only=True)
    total_max_score = serializers.IntegerField(read_only=True)
    quiz_results = AttemptResultSerializer(source='quiz_attempts', many=True, read_only=True)

    class Meta:
        model = MockTestAttempt
        fields = [
            'id', 'mock_test', 'started_at', 'submitted_at',
            'total_score', 'total_max_score', 'quiz_results',
        ]


class MockTestAttemptListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    total_score = serializers.IntegerField(read_only=True)
    total_max_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = MockTestAttempt
        fields = [
            'id', 'mock_test', 'student', 'student_name',
            'started_at', 'submitted_at', 'total_score', 'total_max_score',
        ]
