"""O'quvchi tahlili: o'rtacha baho, oxirgi 30 kun davomati, vazifani o'z vaqtida topshirish, kurslar kesimi, haftalik trend."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.homework.models import Assignment, Submission
from apps.lessons.models import Attendance, Course, Enrollment, Lesson
from apps.quizzes.models import Quiz, QuizAttempt


class StudentAnalyticsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='sa_t', password='x', role='teacher', is_approved=True)
        self.student = User.objects.create_user(username='sa_s', password='x', role='student')
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject='math')
        Enrollment.objects.create(course=self.course, student=self.student, status='approved')
        now = timezone.now()
        lessons = [
            Lesson.objects.create(course=self.course, title=f'D{i}', starts_at=now - timedelta(days=i + 1), status='finished')
            for i in range(4)
        ]
        Lesson.objects.create(course=self.course, title='Eski', starts_at=now - timedelta(days=90), status='finished')
        for lesson in lessons[:3]:
            Attendance.objects.create(lesson=lesson, student=self.student, joined_at=now)
        quiz = Quiz.objects.create(course=self.course, author=self.teacher, title='T', status='published')
        QuizAttempt.objects.create(quiz=quiz, student=self.student, score=8, max_score=10)
        QuizAttempt.objects.create(quiz=quiz, student=self.student, score=6, max_score=10)
        for grade, late in ((5, False), (4, False), (3, True)):
            assignment = Assignment.objects.create(
                course=self.course, title='V', grading='five', due_at=now - timedelta(hours=1), status='active',
            )
            submission = Submission.objects.create(
                assignment=assignment, student=self.student, original_name='a.pdf', status=Submission.Status.DONE, grade_value=grade,
            )
            created = now if late else now - timedelta(hours=2)
            Submission.objects.filter(pk=submission.pk).update(created_at=created)
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def test_overview_numbers(self):
        data = self.api.get('/api/v1/analytics/me/').json()
        self.assertEqual((data['avg_grade'], data['grades_count']), (4.0, 3))
        self.assertEqual((data['lessons_attended'], data['lessons_missed'], data['attendance_rate_month']), (3, 1, 75))
        self.assertEqual(data['homework_on_time_rate'], 67)
        self.assertEqual(data['courses'][0]['course_title'], 'Algebra')
        self.assertEqual((data['courses'][0]['test_avg'], data['courses'][0]['grade_avg']), (70.0, 4.0))
        self.assertIn('recent_attempts', data)  # eski maydonlar saqlanadi

    def test_empty_student_has_nulls_not_errors(self):
        newbie = User.objects.create_user(username='sa_n', password='x', role='student')
        client = APIClient()
        client.force_authenticate(newbie)
        data = client.get('/api/v1/analytics/me/').json()
        self.assertEqual((data['avg_grade'], data['attendance_rate_month'], data['homework_on_time_rate'], data['courses']), (None, None, None, []))

    def test_student_trends(self):
        data = self.api.get('/api/v1/analytics/me/trends/?period=week').json()
        self.assertEqual(len(data['labels']), len(data['quiz_avg_score']))
        self.assertIn(70.0, data['quiz_avg_score'])

    def test_trends_bad_period_and_other_roles(self):
        self.assertEqual(self.api.get('/api/v1/analytics/me/trends/?period=decade').status_code, 400)
        parent = User.objects.create_user(username='sa_p', password='x', role='parent')
        client = APIClient()
        client.force_authenticate(parent)
        self.assertIn(client.get('/api/v1/analytics/me/trends/').status_code, (403,))
