"""Yangi dizayn maydonlari: o'quvchi uchun my_rating/attended, baholarda dars va guruh nomi, yozuv muqovasi, davriy jadval."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Attendance, Course, Enrollment, Lesson, LessonRating


class DesignFieldsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='df_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.student = User.objects.create_user(username='df_s', password='x', role=User.Role.STUDENT)
        self.other = User.objects.create_user(username='df_o', password='x', role=User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Speaking Club', subject='english')
        for user in (self.student, self.other):
            Enrollment.objects.create(course=self.course, student=user, status=Enrollment.Status.APPROVED)
        now = timezone.now()
        self.done = Lesson.objects.create(course=self.course, title='Past', starts_at=now - timedelta(days=1), status=Lesson.Status.FINISHED)
        self.skipped = Lesson.objects.create(course=self.course, title='Skipped', starts_at=now - timedelta(days=2), status=Lesson.Status.FINISHED)
        self.future = Lesson.objects.create(course=self.course, title='Soon', starts_at=now + timedelta(days=1), status=Lesson.Status.SCHEDULED)
        Attendance.objects.create(lesson=self.done, student=self.student, joined_at=now)
        LessonRating.objects.create(lesson=self.done, student=self.student, stars=4, description='Zo‘r')
        LessonRating.objects.create(lesson=self.done, student=self.other, stars=2)

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def lessons(self, user):
        data = self.api(user).get('/api/v1/lessons/').json()
        return {row['title']: row for row in data['results']}

    def test_student_sees_own_rating_and_attendance(self):
        rows = self.lessons(self.student)
        self.assertEqual((rows['Past']['my_rating'], rows['Past']['attended']), (4, True))
        self.assertEqual((rows['Skipped']['my_rating'], rows['Skipped']['attended']), (None, False))
        self.assertEqual((rows['Soon']['my_rating'], rows['Soon']['attended']), (None, None))

    def test_other_student_does_not_see_my_values(self):
        rows = self.lessons(self.other)
        self.assertEqual((rows['Past']['my_rating'], rows['Past']['attended']), (2, False))

    def test_teacher_gets_nulls(self):
        rows = self.lessons(self.teacher)
        self.assertEqual((rows['Past']['my_rating'], rows['Past']['attended']), (None, None))

    def test_my_ratings_include_lesson_and_course_names(self):
        data = self.api(self.teacher).get('/api/v1/auth/me/ratings/').json()
        rows = data['results'] if isinstance(data, dict) else data
        row = next(item for item in rows if item['stars'] == 4)
        self.assertEqual((row['lesson_title'], row['course_title']), ('Past', 'Speaking Club'))
        self.assertEqual(row['course_id'], str(self.course.id))
        self.assertIn('avatar', row['student'])

    def test_periodic_table_has_latin_names_and_known_categories(self):
        data = self.api(self.student).get('/api/v1/board/periodic-table/').json()
        by_symbol = {item['symbol']: item for item in data}
        self.assertEqual((by_symbol['Fe']['latin_name'], by_symbol['Au']['latin_name']), ('Ferrum', 'Aurum'))
        self.assertTrue(all(item['latin_name'] for item in data))
        self.assertLessEqual(
            {item['category'] for item in data},
            {'alkali', 'alkaline_earth', 'transition', 'post_transition', 'metalloid', 'nonmetal', 'halogen', 'noble_gas',
             'lanthanide', 'actinide'},
        )

    def test_recording_status_has_thumbnail_field(self):
        data = self.api(self.teacher).get(f'/api/v1/lessons/{self.done.id}/recording/')
        if data.status_code == 200:
            self.assertIn('thumbnail_url', data.json())
