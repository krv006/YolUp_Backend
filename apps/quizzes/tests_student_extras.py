"""Testlar: o'quvchiga savol-savol natija va guruh statistikasi, guruh o'rtachasi, qoralama, natijalarni ulashish."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.chat.models import Message
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

from .models import AnswerResponse, Question, Quiz, QuizAttempt, QuizDraft


class QuizExtrasTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='qe_t', password='x', role='teacher', is_approved=True)
        self.s1 = User.objects.create_user(username='qe_s1', password='x', role='student', first_name='Ali')
        self.s2 = User.objects.create_user(username='qe_s2', password='x', role='student', first_name='Vali')
        self.parent = User.objects.create_user(username='qe_p', password='x', role='parent')
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        for user in (self.s1, self.s2):
            Enrollment.objects.create(course=self.course, student=user, status='approved')
        ParentChildLink.objects.create(parent=self.parent, student=self.s1, status='approved')
        self.quiz = Quiz.objects.create(course=self.course, author=self.teacher, title='Algebra testi', status='published')
        self.q1 = Question.objects.create(quiz=self.quiz, type='single', text='Birinchi savol', order=1, points=1)
        self.q2 = Question.objects.create(quiz=self.quiz, type='single', text='Ikkinchi savol', order=2, points=1)
        self.a1 = self.attempt(self.s1, 1, 2, [(self.q1, True), (self.q2, True)])
        self.attempt(self.s2, 1, 2, [(self.q1, True), (self.q2, False)])

    def attempt(self, student, score, max_score, answers):
        attempt = QuizAttempt.objects.create(quiz=self.quiz, student=student, score=score, max_score=max_score)
        for question, correct in answers:
            AnswerResponse.objects.create(attempt=attempt, question=question, is_correct=correct, earned_points=1 if correct else 0,
                                          given_display='javob')
        return attempt

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_student_attempts_have_answers_and_only_own(self):
        rows = self.api(self.s2).get(f'/api/v1/quizzes/{self.quiz.id}/attempts/').json()
        rows = rows['results'] if isinstance(rows, dict) else rows
        self.assertEqual(len(rows), 1)
        answers = rows[0]['answers']
        self.assertEqual([(a['order'], a['is_correct']) for a in answers], [(1, True), (2, False)])
        self.assertEqual(answers[1]['label'], 'Ikkinchi savol')

    def test_teacher_gets_answers_only_on_request(self):
        plain = self.api(self.teacher).get(f'/api/v1/quizzes/{self.quiz.id}/attempts/').json()
        plain = plain['results'] if isinstance(plain, dict) else plain
        self.assertIsNone(plain[0]['answers'])
        full = self.api(self.teacher).get(f'/api/v1/quizzes/{self.quiz.id}/attempts/?include=answers').json()
        full = full['results'] if isinstance(full, dict) else full
        self.assertEqual(len(full[0]['answers']), 2)

    def test_student_can_read_group_stats_parent_cannot(self):
        rows = self.api(self.s1).get(f'/api/v1/quizzes/{self.quiz.id}/stats/').json()
        self.assertEqual({r['order']: r['wrong_rate'] for r in rows}, {1: 0, 2: 50})
        self.assertEqual(self.api(self.parent).get(f'/api/v1/quizzes/{self.quiz.id}/stats/').status_code, 403)

    def test_group_average_in_detail(self):
        for user in (self.teacher, self.s1):
            data = self.api(user).get(f'/api/v1/quizzes/{self.quiz.id}/').json()
            self.assertEqual(data['group_avg_percentage'], 50.0)

    def test_group_average_none_without_attempts(self):
        QuizAttempt.objects.all().delete()
        self.assertIsNone(self.api(self.teacher).get(f'/api/v1/quizzes/{self.quiz.id}/').json()['group_avg_percentage'])

    def test_draft_roundtrip_is_per_student(self):
        url = f'/api/v1/quizzes/{self.quiz.id}/draft/'
        self.assertEqual(self.api(self.s1).get(url).json()['answers'], [])
        saved = self.api(self.s1).put(url, {'answers': [{'question_id': str(self.q1.id), 'option': 'a'}], 'elapsed_seconds': 42}, format='json')
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.api(self.s1).get(url).json()['elapsed_seconds'], 42)
        self.assertEqual(self.api(self.s2).get(url).json()['answers'], [])
        self.assertEqual(self.api(self.s1).put(url, {'answers': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.api(self.s1).delete(url).status_code, 204)
        self.assertFalse(QuizDraft.objects.exists())

    def test_share_results_posts_ranked_table_to_group_chat(self):
        response = self.api(self.teacher).post(f'/api/v1/quizzes/{self.quiz.id}/share-results/', {'parents': True}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()['students'], response.json()['parents_notified']), (2, 1))
        text = Message.objects.get(pk=response.json()['message_id']).text
        self.assertIn('Algebra testi', text)
        self.assertLess(text.index('Ali'), text.index('Vali'))  # yuqori ball birinchi
        self.assertTrue(NotificationRecipient.objects.filter(user=self.parent, notification__kind='quiz_result').exists())

    def test_share_results_rules(self):
        self.assertEqual(self.api(self.s1).post(f'/api/v1/quizzes/{self.quiz.id}/share-results/', {}, format='json').status_code, 403)
        QuizAttempt.objects.all().delete()
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/quizzes/{self.quiz.id}/share-results/', {}, format='json').status_code, 400)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/quizzes/{self.quiz.id}/share-results/', {'to': 'x'}, format='json').status_code, 400)
