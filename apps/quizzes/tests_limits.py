"""Test topshirish sozlamalari: vaqt, urinishlar soni, har urinishdagi savollar, tasodifiy tartib (2026-11-11)."""
import json
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.homework.tests import make
from apps.homework.tests_hardening import HomeworkBase
from apps.lessons.models import Enrollment

from . import services
from .models import Quiz, QuizAttempt, QuizSession


def question(n, options=4):
    return {
        'text': f'Savol {n}', 'type': 'single', 'points': 1,
        'options': [{'text': f'S{n}-V{i}', 'is_correct': i == 0, 'order': i} for i in range(options)],
    }


class LimitsBase(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.s2 = make('s2', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=self.s2, status=Enrollment.Status.APPROVED)
        self.quiz = self.make_quiz()

    def make_quiz(self, count=6, **kwargs):
        return services.create_quiz(
            teacher=self.teacher, topic='Sinov', course=self.course, questions=[question(i, 8) for i in range(count)],
            status=Quiz.Status.PUBLISHED, **kwargs,
        )

    def take(self, user=None, quiz=None):
        r = self.api(user or self.student).get(f'/api/v1/quizzes/{(quiz or self.quiz).id}/')
        self.assertEqual(r.status_code, 200, r.content)
        return json.loads(json.dumps(r.data, default=str))  # UUID'lar matn bo'lib qolsin

    def start(self, user=None, quiz=None):
        return self.api(user or self.student).post(f'/api/v1/quizzes/{(quiz or self.quiz).id}/start/')

    def answers_for(self, data, correct=True):
        out = []
        for q in data['questions']:
            real = self.quiz.questions.get(pk=q['id']) if hasattr(self, 'quiz') else None
            option = real.options.filter(is_correct=correct).first()
            out.append({'question': str(q['id']), 'selected_option': str(option.id)})
        return out

    def submit(self, answers, user=None, quiz=None, **extra):
        return self.api(user or self.student).post(
            f'/api/v1/quizzes/{(quiz or self.quiz).id}/attempts/', {'answers': answers, **extra}, format='json')


class TeacherSettingsTests(LimitsBase):
    def test_settings_are_saved_on_create_and_patch_and_shown_to_the_teacher(self):
        r = self.api(self.teacher).post('/api/v1/quizzes/', {
            'course': str(self.course.id), 'topic': 'Sozlamali', 'questions': [question(i) for i in range(5)],
            'time_limit_minutes': 30, 'max_attempts': 2, 'questions_per_attempt': 3,
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        for key, value in (('time_limit_minutes', 30), ('max_attempts', 2), ('questions_per_attempt', 3)):
            self.assertEqual(r.data[key], value)
        qid = r.data['id']
        p = self.api(self.teacher).patch(f'/api/v1/quizzes/{qid}/', {'time_limit_minutes': 45, 'max_attempts': None}, format='json')
        self.assertEqual(p.status_code, 200, p.content)
        self.assertEqual((p.data['time_limit_minutes'], p.data['max_attempts'], p.data['questions_per_attempt']), (45, None, 3))
        listed = self.api(self.teacher).get('/api/v1/quizzes/')
        row = next(i for i in listed.data.get('results', listed.data) if str(i['id']) == str(qid))
        self.assertEqual(row['time_limit_minutes'], 45)

    def test_validation(self):
        base = {'course': str(self.course.id), 'topic': 'x', 'questions': [question(i) for i in range(3)]}
        post = lambda **extra: self.api(self.teacher).post('/api/v1/quizzes/', {**base, **extra}, format='json').status_code
        self.assertEqual(post(time_limit_minutes=0), 400)
        self.assertEqual(post(time_limit_minutes=601), 400)
        self.assertEqual(post(max_attempts=0), 400)
        self.assertEqual(post(max_attempts=21), 400)
        self.assertEqual(post(questions_per_attempt=4), 400)  # testda 3 ta savol bor
        self.assertEqual(post(questions_per_attempt=3), 201)

    def test_student_view_has_the_limits_and_attempt_counters(self):
        quiz = self.make_quiz(max_attempts=3)
        data = self.take(quiz=quiz)
        self.assertEqual((data['max_attempts'], data['attempts_used'], data['attempts_left'], data['needs_start']), (3, 0, 3, False))
        self.assertIsNone(data['started_at'])


class ShuffleTests(LimitsBase):
    def options_of(self, data):
        return {q['id']: [o['text'] for o in q['options']] for q in data['questions']}

    def test_order_is_stable_within_an_attempt_and_changes_on_a_new_attempt(self):
        first = self.take()
        self.assertEqual(self.take(), first)  # sahifa yangilansa ham o'zgarmaydi
        stored = {str(q.id): [o.text for o in q.options.all()] for q in self.quiz.questions.all()}
        shown = self.options_of(first)
        self.assertTrue(any(shown[str(k)] != v for k, v in stored.items()), "variantlar o'z tartibida qolgan")
        self.assertNotEqual([q['id'] for q in first['questions']], [str(q.id) for q in self.quiz.questions.all()])
        # yangi urinish
        self.assertEqual(self.submit(self.answers_for(first)).status_code, 201)
        second = self.take()
        self.assertNotEqual(self.options_of(second), self.options_of(first))

    def test_students_get_different_orders(self):
        self.assertNotEqual(self.options_of(self.take()), self.options_of(self.take(user=self.s2)))

    def test_correct_answer_does_not_always_sit_first(self):
        data = self.take()
        correct_positions = []
        for q in data['questions']:
            correct = {o.text for o in self.quiz.questions.get(pk=q['id']).options.filter(is_correct=True)}
            correct_positions.append([o['text'] in correct for o in q['options']].index(True))
        self.assertTrue(any(p != 0 for p in correct_positions))

    def test_group_quizzes_keep_the_question_order_but_shuffle_options(self):
        quiz = services.create_quiz(
            teacher=self.teacher, topic='Matnli', course=self.course, status=Quiz.Status.PUBLISHED,
            groups=[{'title': 'Reading', 'passage': 'Matn...'}],
            questions=[{**question(i, 8), 'group': 0} for i in range(5)],
        )
        data = self.take(quiz=quiz)
        stored_order = [str(q.id) for q in quiz.questions.all()]
        self.assertEqual([q['id'] for q in data['questions']], stored_order)
        stored = {str(q.id): [o.text for o in q.options.all()] for q in quiz.questions.all()}
        self.assertTrue(any([o['text'] for o in q['options']] != stored[q['id']] for q in data['questions']))

    def test_old_submissions_still_work_without_start(self):
        data = self.take()
        r = self.submit(self.answers_for(data))
        self.assertEqual(r.status_code, 201, r.content)


class QuestionsPerAttemptTests(LimitsBase):
    def test_a_subset_is_shown_and_scored_by_those_questions_only(self):
        quiz = self.make_quiz(count=6, questions_per_attempt=3)
        data = self.take(quiz=quiz)
        self.assertEqual(len(data['questions']), 3)
        self.quiz = quiz
        r = self.submit(self.answers_for(data), quiz=quiz)
        self.assertEqual(r.status_code, 201, r.content)
        attempt = QuizAttempt.objects.get(pk=r.data['id'])
        self.assertEqual((attempt.max_score, attempt.score, attempt.answers.count()), (3, 3, 3))

    def test_a_question_that_was_not_given_is_rejected(self):
        quiz = self.make_quiz(count=6, questions_per_attempt=2)
        shown = {q['id'] for q in self.take(quiz=quiz)['questions']}
        other = quiz.questions.exclude(pk__in=shown).first()
        option = other.options.first()
        r = self.submit([{'question': str(other.id), 'selected_option': str(option.id)}], quiz=quiz)
        self.assertEqual(r.status_code, 400)

    def test_the_subset_is_stable_and_differs_between_attempts_or_students(self):
        quiz = self.make_quiz(count=10, questions_per_attempt=3)
        a = [q['id'] for q in self.take(quiz=quiz)['questions']]
        self.assertEqual(a, [q['id'] for q in self.take(quiz=quiz)['questions']])
        b = [q['id'] for q in self.take(user=self.s2, quiz=quiz)['questions']]
        self.assertNotEqual(a, b)

    def test_cannot_limit_a_group_quiz(self):
        r = self.api(self.teacher).post('/api/v1/quizzes/', {
            'course': str(self.course.id), 'topic': 'G', 'groups': [{'title': 'R', 'passage': 'x'}],
            'questions': [{**question(i), 'group': 0} for i in range(4)], 'questions_per_attempt': 2,
        }, format='json')
        self.assertEqual(r.status_code, 400)


class MaxAttemptsTests(LimitsBase):
    def test_attempts_run_out(self):
        quiz = self.make_quiz(max_attempts=2)
        self.quiz = quiz
        for used in range(2):
            data = self.take(quiz=quiz)
            self.assertEqual((data['attempts_used'], data['attempts_left']), (used, 2 - used))
            self.assertEqual(self.submit(self.answers_for(data), quiz=quiz).status_code, 201)
        data = self.take(quiz=quiz)
        self.assertEqual((data['attempts_used'], data['attempts_left'], data['questions']), (2, 0, []))
        late = self.submit([{'question': str(quiz.questions.first().id), 'selected_option': str(quiz.questions.first().options.first().id)}], quiz=quiz)
        self.assertEqual(late.status_code, 400)
        self.assertEqual(self.start(quiz=quiz).status_code, 400)

    def test_other_students_have_their_own_counter(self):
        quiz = self.make_quiz(max_attempts=1)
        self.quiz = quiz
        self.assertEqual(self.submit(self.answers_for(self.take(quiz=quiz)), quiz=quiz).status_code, 201)
        data = self.take(user=self.s2, quiz=quiz)
        self.assertEqual((data['attempts_left'], len(data['questions'])), (1, 6))


class TimeLimitTests(LimitsBase):
    def setUp(self):
        super().setUp()
        self.quiz = self.make_quiz(time_limit_minutes=20, max_attempts=2)

    def test_questions_are_hidden_until_the_quiz_is_started(self):
        data = self.take()
        self.assertEqual((data['needs_start'], data['questions'], data['groups']), (True, [], []))
        self.assertIsNone(data['ends_at'])

    def test_start_sets_the_server_timer_and_reveals_the_questions(self):
        r = self.start()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.data['time_limit_minutes'], r.data['attempts_used'], r.data['attempts_left'], r.data['question_count']), (20, 0, 2, 6))
        started, ends = r.data['started_at'], r.data['ends_at']
        again = self.start()
        self.assertEqual((again.data['started_at'], again.data['ends_at']), (started, ends))  # qayta bosilsa vaqt yangilanmaydi
        self.assertEqual(QuizSession.objects.filter(student=self.student).count(), 1)
        data = self.take()
        self.assertEqual((data['needs_start'], len(data['questions']), data['ends_at'] is not None), (False, 6, True))

    def test_submit_without_start_is_rejected(self):
        any_q = self.quiz.questions.first()
        r = self.submit([{'question': str(any_q.id), 'selected_option': str(any_q.options.first().id)}])
        self.assertEqual(r.status_code, 400)

    def test_submit_in_time_works_and_records_the_duration(self):
        self.start()
        QuizSession.objects.update(started_at=timezone.now() - timedelta(minutes=5))
        r = self.submit(self.answers_for(self.take()))
        self.assertEqual(r.status_code, 201, r.content)
        attempt = QuizAttempt.objects.get(pk=r.data['id'])
        self.assertTrue(290 <= attempt.duration_seconds <= 320)  # ~5 daqiqa, serverdan
        self.assertEqual(QuizSession.objects.get().attempt_id, attempt.id)
        self.assertTrue(self.take()['needs_start'])  # yangi urinish uchun yana boshlash kerak

    def test_answers_after_the_time_is_up_are_rejected_and_the_attempt_is_spent(self):
        self.start()
        data = self.take()
        answers = self.answers_for(data)
        QuizSession.objects.update(started_at=timezone.now() - timedelta(minutes=25), ends_at=timezone.now() - timedelta(minutes=5))
        late = self.submit(answers)
        self.assertEqual(late.status_code, 400)
        self.assertEqual(QuizAttempt.objects.count(), 0)
        after = self.take()
        self.assertEqual((after['attempts_used'], after['attempts_left'], after['needs_start']), (1, 1, True))
        again = self.start()  # 1 ta urinish qoldi
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data['attempts_used'], 1)

    def test_a_short_network_delay_is_tolerated(self):
        self.start()
        answers = self.answers_for(self.take())
        QuizSession.objects.update(ends_at=timezone.now() - timedelta(seconds=10))
        self.assertEqual(self.submit(answers).status_code, 201)

    def test_start_is_only_for_students_who_can_attend(self):
        outsider = make('s_out_q', User.Role.STUDENT)
        self.assertEqual(self.start(user=outsider).status_code, 404)
        restricted = make('s_r', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=restricted, status=Enrollment.Status.APPROVED)
        services.set_audience(teacher=self.teacher, quiz=self.quiz, student_ids=[self.student.id])
        self.assertEqual(self.start(user=restricted).status_code, 404)
        self.assertEqual(self.start().status_code, 200)
