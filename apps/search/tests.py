from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.chat.models import Message
from apps.lessons.models import Course, Enrollment, Lesson
from apps.quizzes.models import Quiz
from django.utils import timezone


class SearchTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='se_t', password='x', role='teacher', is_approved=True, first_name='Aziza')
        self.student = User.objects.create_user(username='se_s', password='x', role='student', first_name='Bobur')
        self.outsider = User.objects.create_user(username='se_o', password='x', role='student', first_name='Bobur')
        self.course = Course.objects.create(teacher=self.teacher, title='Ingliz tili A1', subject='english')
        Course.objects.create(teacher=self.teacher, title='Boshqa guruh', subject='math')
        Enrollment.objects.create(course=self.course, student=self.student, status='approved')
        Lesson.objects.create(course=self.course, title='Present Simple', starts_at=timezone.now(), status='scheduled')
        Quiz.objects.create(course=self.course, author=self.teacher, title='Present tenses test', status='published')
        self.room = chat_services.ensure_course_room(self.course)
        Message.objects.create(room=self.room, sender=self.teacher, text='Ertaga present simple bo‘yicha test bo‘ladi')
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def search(self, user=None, **params):
        client = APIClient()
        client.force_authenticate(user or self.student)
        return client.get('/api/v1/search/', params).json()

    def test_all_types_grouped_with_counts(self):
        data = self.search(q='present')
        types = {row['type'] for row in data['results']}
        self.assertEqual(types, {'lessons', 'quizzes', 'messages'})
        self.assertEqual(data['counts']['lessons'], 1)

    def test_message_result_has_ids_and_snippet(self):
        row = self.search(q='simple', type='messages')['results'][0]
        self.assertEqual((row['room_id'], row['subtitle']), (str(self.room.id), 'Ingliz tili A1'))
        self.assertIn('present simple', row['title'])
        self.assertTrue(row['message_id'])

    def test_outsider_sees_nothing_from_the_group(self):
        data = self.search(self.outsider, q='present')
        self.assertEqual(data['results'], [])

    def test_groups_and_people(self):
        self.assertEqual([r['title'] for r in self.search(q='ingliz', type='groups')['results']], ['Ingliz tili A1'])
        people = self.search(q='aziza', type='people')['results']
        self.assertEqual(people[0]['subtitle'], '@se_t')
        teacher_people = self.search(self.teacher, q='bobur', type='people')['results']
        self.assertEqual([p['subtitle'] for p in teacher_people], ['@se_s'])  # faqat o'z guruhidagi Bobur

    def test_short_query_and_bad_type(self):
        self.assertEqual(self.search(q='p')['results'], [])
        self.assertEqual(self.api.get('/api/v1/search/?q=present&type=zzz').status_code, 400)

    def test_pagination_for_one_type(self):
        for i in range(25):
            Lesson.objects.create(course=self.course, title=f'Present dars {i}', starts_at=timezone.now(), status='scheduled')
        page1 = self.search(q='present dars', type='lessons', page_size=10)
        self.assertEqual((page1['count'], len(page1['results'])), (25, 10))
        self.assertIsNotNone(page1['next'])
        page3 = self.search(q='present dars', type='lessons', page_size=10, page=3)
        self.assertEqual(len(page3['results']), 5)
        self.assertIsNone(page3['next'])
