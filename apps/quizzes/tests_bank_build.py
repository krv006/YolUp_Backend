"""Savollar bankidan test yig'ish (AI'siz) va uy vazifasi qoralamasi."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

from .models import BankQuestion, Quiz


def payload(text, correct=0):
    return {'type': 'single', 'text': text, 'points': 2, 'options': [
        {'text': 'A', 'is_correct': correct == 0}, {'text': 'B', 'is_correct': correct == 1}]}


class BankBuildTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='bb_t', password='x', role='teacher', is_approved=True)
        self.other = User.objects.create_user(username='bb_o', password='x', role='teacher', is_approved=True)
        self.student = User.objects.create_user(username='bb_s', password='x', role='student')
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject='math')
        Enrollment.objects.create(course=self.course, student=self.student, status='approved')
        for i in range(6):
            BankQuestion.objects.create(teacher=self.teacher, exam_key='ielts', subject='english', text=f'Present Perfect savol {i}',
                                        digest=f'd{i}', payload=payload(f'Present Perfect savol {i}'))
        BankQuestion.objects.create(teacher=self.teacher, exam_key='sat', subject='math', text='Kvadrat tenglama', digest='x',
                                    payload=payload('Kvadrat tenglama'))
        BankQuestion.objects.create(teacher=self.other, exam_key='ielts', subject='english', text='Present Perfect begona', digest='y',
                                    payload=payload('Present Perfect begona'))
        self.api = APIClient()
        self.api.force_authenticate(self.teacher)

    def post(self, **data):
        return self.api.post('/api/v1/quizzes/ai-generate/bank/', data, format='json')

    def test_builds_draft_quiz_from_matching_bank_questions(self):
        response = self.post(topic='present perfect', count=4, course=str(self.course.id))
        self.assertEqual(response.status_code, 201, response.content)
        quiz = Quiz.objects.get(pk=response.json()['id'])
        self.assertEqual((quiz.status, quiz.course_id, quiz.questions.count()), ('draft', self.course.id, 4))
        self.assertFalse(quiz.questions.filter(text__icontains='begona').exists())  # boshqa o'qituvchi banki ishlatilmaydi
        self.assertTrue(all(q.options.count() == 2 for q in quiz.questions.all()))

    def test_count_is_capped_by_available_questions(self):
        response = self.post(topic='present perfect', count=50)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Quiz.objects.get(pk=response.json()['id']).questions.count(), 6)

    def test_no_match_and_validation(self):
        self.assertEqual(self.post(topic='astronomiya').status_code, 400)
        self.assertEqual(self.post(topic=' ').status_code, 400)
        self.assertEqual(self.post(topic='kvadrat', count='x').status_code, 400)

    def test_cannot_use_someone_elses_course_and_students_cannot_build(self):
        self.assertEqual(self.post(topic='kvadrat', course=str(Course.objects.create(teacher=self.other, title='X', subject='math').id)).status_code, 404)
        student = APIClient()
        student.force_authenticate(self.student)
        self.assertEqual(student.post('/api/v1/quizzes/ai-generate/bank/', {'topic': 'kvadrat'}, format='json').status_code, 403)
