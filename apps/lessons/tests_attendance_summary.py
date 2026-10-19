"""Guruh davomat hisoboti (`/courses/{id}/attendance/summary/`) va kursning yangi maydonlari (haftasiga darslar, oylik to'lov)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Attendance, Course, Enrollment, FocusEvent, Lesson

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


class AttendanceSummaryTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.aziza = make('aziza', User.Role.STUDENT, first_name='Aziza', last_name='Rahimova')
        self.bobur = make('bobur', User.Role.STUDENT, first_name='Bobur')
        self.pending = make('kutadi', User.Role.STUDENT)
        for student, state in ((self.aziza, 'approved'), (self.bobur, 'approved'), (self.pending, 'pending')):
            Enrollment.objects.create(course=self.course, student=student, status=state)
        self.now = timezone.now()
        # 3 ta tugagan dars (bittasi 40 kun oldin), 1 ta rejalashtirilgan
        self.old = self.lesson(days_ago=40)
        self.recent_a = self.lesson(days_ago=3)
        self.recent_b = self.lesson(days_ago=2)
        Lesson.objects.create(course=self.course, starts_at=self.now + timedelta(days=1), status=Lesson.Status.SCHEDULED)
        self.url = f'/api/v1/courses/{self.course.id}/attendance/summary/'

    def lesson(self, days_ago):
        return Lesson.objects.create(
            course=self.course, starts_at=self.now - timedelta(days=days_ago), duration_min=60, status=Lesson.Status.FINISHED,
        )

    def attend(self, student, lesson, minutes_in=0, minutes=60):
        start = lesson.starts_at + timedelta(minutes=minutes_in)
        return Attendance.objects.create(
            lesson=lesson, student=student, joined_at=start, left_at=start + timedelta(minutes=minutes),
        )

    def focus(self, student, lesson, exit_min, return_min=None):
        for kind, minute in ((FocusEvent.Kind.EXIT, exit_min), (FocusEvent.Kind.RETURN, return_min)):
            if minute is None:
                continue
            event = FocusEvent.objects.create(lesson=lesson, student=student, kind=kind)
            FocusEvent.objects.filter(pk=event.pk).update(created_at=lesson.starts_at + timedelta(minutes=minute))

    def get(self, user, query=''):
        self.client.force_authenticate(user)
        return self.client.get(self.url + query)

    def row(self, body, username):
        return next(r for r in body['students'] if r['name'] == username)

    def test_percentages_per_student_and_overall(self):
        for lesson in (self.old, self.recent_a, self.recent_b):
            self.attend(self.aziza, lesson)
        self.attend(self.bobur, self.recent_a)
        self.focus(self.aziza, self.recent_a, exit_min=10, return_min=25)  # 15 daqiqa chetda: 45/60 = 75%
        body = self.get(self.teacher).json()
        self.assertEqual(body['lesson_count'], 3)
        aziza, bobur = self.row(body, 'Aziza Rahimova'), self.row(body, 'Bobur')
        self.assertEqual((aziza['attendance_percent'], aziza['attended_count']), (100, 3))
        self.assertEqual(aziza['focus_percent'], round((180 - 15) * 100 / 180))
        self.assertEqual((bobur['attendance_percent'], bobur['focus_percent']), (33, 100))
        self.assertEqual(body['attendance_percent'], round(4 * 100 / 6))
        self.assertEqual(body['focus_percent'], round((240 - 15) * 100 / 240))
        self.assertEqual(len(body['students']), 2)  # tasdiqlanmagan o'quvchi kirmaydi

    def test_unreturned_exit_counts_until_the_end(self):
        self.attend(self.aziza, self.recent_a)
        self.focus(self.aziza, self.recent_a, exit_min=30)  # qaytmagan: 30 daqiqa chetda
        body = self.get(self.teacher, '?range=30d').json()
        self.assertEqual(self.row(body, 'Aziza Rahimova')['focus_percent'], 50)

    def test_ranges(self):
        self.attend(self.aziza, self.old)
        self.assertEqual(self.get(self.teacher, '?range=all').json()['lesson_count'], 3)
        thirty = self.get(self.teacher, '?range=30d').json()
        self.assertEqual((thirty['lesson_count'], self.row(thirty, 'Aziza Rahimova')['attendance_percent']), (2, 0))
        month = self.get(self.teacher, '?range=month').json()
        self.assertLessEqual(month['lesson_count'], 2)
        self.assertEqual(self.get(self.teacher, '?range=year').status_code, 400)

    def test_no_attendance_means_no_focus_and_no_lessons_is_safe(self):
        body = self.get(self.teacher, '?range=30d').json()
        self.assertEqual((body['attendance_percent'], body['focus_percent']), (0, None))
        empty = Course.objects.create(teacher=self.teacher, title='Bo\'sh')
        self.client.force_authenticate(self.teacher)
        body = self.client.get(f'/api/v1/courses/{empty.id}/attendance/summary/').json()
        self.assertEqual((body['lesson_count'], body['attendance_percent'], body['students']), (0, 0, []))

    def test_who_sees_what(self):
        self.attend(self.aziza, self.recent_a)
        own = self.get(self.aziza).json()
        self.assertEqual([r['name'] for r in own['students']], ['Aziza Rahimova'])
        parent = make('p1', User.Role.PARENT)
        ParentChildLink.objects.create(parent=parent, student=self.bobur, status=ParentChildLink.Status.APPROVED)
        self.assertEqual([r['name'] for r in self.get(parent).json()['students']], ['Bobur'])
        outsider = make('s9', User.Role.STUDENT)
        self.assertEqual(self.get(outsider).status_code, 404)
        stranger = make('t2', User.Role.TEACHER)
        self.assertEqual(self.get(stranger).status_code, 404)


class CourseFeeFieldsTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.client.force_authenticate(self.teacher)

    def test_create_and_read_the_new_fields(self):
        resp = self.client.post('/api/v1/courses/', {
            'title': 'Matematika', 'subject': 'math', 'lessons_per_week': 3, 'monthly_fee': 450000,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['lessons_per_week'], body['monthly_fee']), (3, 450000))
        course = Course.objects.get(pk=body['id'])
        self.assertEqual((course.lessons_per_week, course.monthly_fee), (3, 450000))
        patched = self.client.patch(f'/api/v1/courses/{course.id}/', {'monthly_fee': 500000}, format='json')
        self.assertEqual(patched.json()['monthly_fee'], 500000)

    def test_fields_are_optional_and_validated(self):
        resp = self.client.post('/api/v1/courses/', {'title': 'Fizika', 'subject': 'physics'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual((resp.json()['lessons_per_week'], resp.json()['monthly_fee']), (None, None))
        for bad in ({'lessons_per_week': 0}, {'lessons_per_week': 15}, {'monthly_fee': -1}):
            r = self.client.post('/api/v1/courses/', {'title': 'X', **bad}, format='json')
            self.assertEqual(r.status_code, 400, bad)
