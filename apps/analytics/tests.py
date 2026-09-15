from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import PASSWORD, login, register
from apps.lessons.models import Attendance, Course, Enrollment, Lesson, LessonRating
from apps.quizzes.models import Quiz, QuizAttempt

from .selectors import PERIOD_BUCKET_COUNTS


def make_admin(username='admin1') -> User:
    return User.objects.create_user(username=username, password=PASSWORD, role=User.Role.ADMIN)


def make_lesson(course, *, status, starts_at) -> Lesson:
    return Lesson.objects.create(course=course, starts_at=starts_at, status=status)


class AnalyticsPermissionTests(APITestCase):
    def setUp(self):
        register(self.client, 't1', 'teacher')
        self.teacher_token = login(self.client, 't1')
        register(self.client, 's1', 'student')
        self.student_token = login(self.client, 's1')
        register(self.client, 'p1', 'parent')
        self.parent_token = login(self.client, 'p1')
        make_admin('a1')
        self.admin_token = login(self.client, 'a1')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_non_admin_roles_forbidden(self):
        for token in (self.teacher_token, self.student_token, self.parent_token):
            self.auth(token)
            self.assertEqual(self.client.get('/api/v1/analytics/dashboard/summary/').status_code, 403)
            self.assertEqual(self.client.get('/api/v1/analytics/dashboard/trends/').status_code, 403)

    def test_admin_allowed(self):
        self.auth(self.admin_token)
        self.assertEqual(self.client.get('/api/v1/analytics/dashboard/summary/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/analytics/dashboard/trends/').status_code, 200)

    def test_invalid_period_rejected(self):
        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/analytics/dashboard/trends/?period=decade')
        self.assertEqual(resp.status_code, 400)


class DashboardSummaryTests(APITestCase):
    def setUp(self):
        make_admin()
        self.admin_token = login(self.client, 'admin1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        self.teacher1 = User.objects.create_user(username='teach1', password=PASSWORD, role=User.Role.TEACHER)
        self.teacher2 = User.objects.create_user(username='teach2', password=PASSWORD, role=User.Role.TEACHER)
        self.student1 = User.objects.create_user(username='stud1', password=PASSWORD, role=User.Role.STUDENT)
        self.student2 = User.objects.create_user(username='stud2', password=PASSWORD, role=User.Role.STUDENT)

        self.course1 = Course.objects.create(teacher=self.teacher1, title='Matematika', is_active=True)
        self.course2 = Course.objects.create(teacher=self.teacher2, title='Fizika', is_active=True)
        # Faol bo'lmagan kurs — hech qanday hisoblashga kirmasligi kerak.
        Course.objects.create(teacher=self.teacher2, title='Eski kurs', is_active=False)

        Enrollment.objects.create(course=self.course1, student=self.student1, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course1, student=self.student2, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course2, student=self.student1, status=Enrollment.Status.APPROVED)

        now = timezone.now()
        lesson1 = make_lesson(self.course1, status=Lesson.Status.FINISHED, starts_at=now - timedelta(days=2))
        make_lesson(self.course1, status=Lesson.Status.CANCELLED, starts_at=now - timedelta(days=1))

        Attendance.objects.create(lesson=lesson1, student=self.student1, joined_at=now, left_at=now)
        # student2 course1'ga yozilgan lekin darsga kirmagan — davomat 50% bo'lishi kerak.

        LessonRating.objects.create(lesson=lesson1, student=self.student1, stars=5)
        LessonRating.objects.create(lesson=lesson1, student=self.student2, stars=3)

    def test_active_counts(self):
        resp = self.client.get('/api/v1/analytics/dashboard/summary/')
        data = resp.json()
        self.assertEqual(data['active_courses'], 2)
        self.assertEqual(data['active_teachers'], 2)
        self.assertEqual(data['active_students'], 2)

    def test_rating_summary(self):
        resp = self.client.get('/api/v1/analytics/dashboard/summary/')
        data = resp.json()
        self.assertEqual(data['avg_rating'], 4.0)
        self.assertEqual(data['rating_count'], 2)
        self.assertNotIn('attendance_rate', data)  # endi faqat trends'da, davr kesimida

    def test_top_courses_and_teachers_shape(self):
        resp = self.client.get('/api/v1/analytics/dashboard/summary/')
        data = resp.json()
        top_course = next(c for c in data['top_courses'] if c['title'] == 'Matematika')
        self.assertEqual(top_course['student_count'], 2)
        self.assertEqual(top_course['avg_rating'], 4.0)
        self.assertEqual(top_course['attendance_rate'], 50.0)

        top_teacher = next(t for t in data['top_teachers'] if t['name'] == 'teach1')
        self.assertEqual(top_teacher['course_count'], 1)
        self.assertEqual(top_teacher['avg_rating'], 4.0)
        self.assertEqual(top_teacher['reliability'], 50.0)  # 1 finished / (1 finished + 1 cancelled)


class DashboardTrendsTests(APITestCase):
    def setUp(self):
        make_admin()
        self.admin_token = login(self.client, 'admin1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

    def test_bucket_counts_match_for_every_period(self):
        for period, expected_count in PERIOD_BUCKET_COUNTS.items():
            resp = self.client.get(f'/api/v1/analytics/dashboard/trends/?period={period}')
            data = resp.json()
            self.assertEqual(data['period'], period)
            self.assertEqual(len(data['labels']), expected_count)
            self.assertEqual(len(data['enrollments']), expected_count)
            self.assertEqual(len(data['lessons_completed']), expected_count)
            self.assertEqual(len(data['lessons_cancelled']), expected_count)
            self.assertEqual(len(data['quiz_avg_score']), expected_count)
            self.assertEqual(len(data['attendance_rate']), expected_count)

    def test_fresh_enrollment_lands_in_last_day_bucket(self):
        teacher = User.objects.create_user(username='teachx', password=PASSWORD, role=User.Role.TEACHER)
        student = User.objects.create_user(username='studx', password=PASSWORD, role=User.Role.STUDENT)
        course = Course.objects.create(teacher=teacher, title='Kimyo', is_active=True)
        Enrollment.objects.create(course=course, student=student, status=Enrollment.Status.APPROVED)

        resp = self.client.get('/api/v1/analytics/dashboard/trends/?period=day')
        data = resp.json()
        self.assertEqual(data['enrollments'][-1], 1)
        self.assertEqual(sum(data['enrollments'][:-1]), 0)

    def test_quiz_attempt_score_averaged_in_bucket(self):
        teacher = User.objects.create_user(username='teachy', password=PASSWORD, role=User.Role.TEACHER)
        student = User.objects.create_user(username='study', password=PASSWORD, role=User.Role.STUDENT)
        course = Course.objects.create(teacher=teacher, title='Biologiya', is_active=True)
        quiz = Quiz.objects.create(course=course, title='Test 1')
        QuizAttempt.objects.create(quiz=quiz, student=student, score=8, max_score=10)
        QuizAttempt.objects.create(quiz=quiz, student=student, score=6, max_score=10)

        resp = self.client.get('/api/v1/analytics/dashboard/trends/?period=day')
        data = resp.json()
        self.assertEqual(data['quiz_avg_score'][-1], 70.0)  # (80% + 60%) / 2

    def test_attendance_rate_lands_in_bucket(self):
        teacher = User.objects.create_user(username='teachz', password=PASSWORD, role=User.Role.TEACHER)
        student1 = User.objects.create_user(username='studz1', password=PASSWORD, role=User.Role.STUDENT)
        student2 = User.objects.create_user(username='studz2', password=PASSWORD, role=User.Role.STUDENT)
        course = Course.objects.create(teacher=teacher, title='Kimyo-2', is_active=True)
        Enrollment.objects.create(course=course, student=student1, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=course, student=student2, status=Enrollment.Status.APPROVED)

        now = timezone.now()
        lesson = make_lesson(course, status=Lesson.Status.FINISHED, starts_at=now)
        Attendance.objects.create(lesson=lesson, student=student1, joined_at=now, left_at=now)
        # student2 yozilgan, lekin kirmagan — 1/2 = 50%.

        resp = self.client.get('/api/v1/analytics/dashboard/trends/?period=day')
        data = resp.json()
        self.assertEqual(data['attendance_rate'][-1], 50.0)
        self.assertTrue(all(v is None for v in data['attendance_rate'][:-1]))


class MyAnalyticsTests(APITestCase):
    """Workspace > Tahlil — `GET /api/v1/analytics/me/` (shaxsiy statistika)."""

    def setUp(self):
        register(self.client, 'ta1', 'teacher')
        self.teacher_token = login(self.client, 'ta1')
        register(self.client, 'sa1', 'student')
        self.student_token = login(self.client, 'sa1')
        register(self.client, 'pa1', 'parent')
        self.parent_token = login(self.client, 'pa1')
        make_admin('aa1')
        self.admin_token = login(self.client, 'aa1')

        self.teacher = User.objects.get(username='ta1')
        self.student = User.objects.get(username='sa1')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_parent_and_admin_forbidden(self):
        for token in (self.parent_token, self.admin_token):
            self.auth(token)
            self.assertEqual(self.client.get('/api/v1/analytics/me/').status_code, 403)

    def test_student_sees_own_quiz_history(self):
        course = Course.objects.create(teacher=self.teacher, title='Ingliz tili', is_active=True)
        quiz = Quiz.objects.create(course=course, title='1-bob testi')
        QuizAttempt.objects.create(quiz=quiz, student=self.student, score=8, max_score=10)
        QuizAttempt.objects.create(quiz=quiz, student=self.student, score=5, max_score=10)
        # Boshqa o'quvchining urinishi — bu ro'yxatga kirmasligi kerak.
        other_student = User.objects.create_user(username='sa2', password=PASSWORD, role=User.Role.STUDENT)
        QuizAttempt.objects.create(quiz=quiz, student=other_student, score=10, max_score=10)

        self.auth(self.student_token)
        resp = self.client.get('/api/v1/analytics/me/')
        data = resp.json()
        self.assertEqual(data['attempt_count'], 2)
        self.assertEqual(data['avg_percentage'], 65.0)  # (80% + 50%) / 2
        self.assertEqual(len(data['recent_attempts']), 2)
        self.assertEqual(data['recent_attempts'][0]['course_title'], 'Ingliz tili')

    def test_teacher_sees_overall_and_course_breakdown(self):
        course1 = Course.objects.create(teacher=self.teacher, title='Matematika', is_active=True)
        course2 = Course.objects.create(teacher=self.teacher, title='Fizika', is_active=True)
        other_student = User.objects.create_user(username='sa3', password=PASSWORD, role=User.Role.STUDENT)
        Enrollment.objects.create(course=course1, student=self.student, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=course2, student=self.student, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=course2, student=other_student, status=Enrollment.Status.APPROVED)

        lesson1 = make_lesson(course1, status=Lesson.Status.FINISHED, starts_at=timezone.now())
        LessonRating.objects.create(lesson=lesson1, student=self.student, stars=4)

        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/analytics/me/')
        data = resp.json()
        self.assertIn('overall', data)
        self.assertEqual(data['overall']['course_count'], 2)
        self.assertEqual(len(data['courses']), 2)
        math_row = next(row for row in data['courses'] if row['course_title'] == 'Matematika')
        self.assertEqual(math_row['student_count'], 1)
        self.assertEqual(math_row['avg_rating'], 4.0)
