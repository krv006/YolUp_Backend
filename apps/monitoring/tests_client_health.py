"""Mijoz salomatlik hisobotlari: yuborish, tekshirish, chastota, admin xulosasi, tozalash (2026-11-12)."""
from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment, Lesson

from .models import ClientHealthReport


def make(username, role, **extra):
    user = User(username=username, role=role, is_approved=True, **extra)
    user.set_password('x')
    user.save()
    return user


GOOD = {
    'cpu_constrained': True, 'hardware_concurrency': 8, 'device_memory': 8, 'connection_quality': 'good', 'page_visible': True,
    'events': ['cpu_constrained'],
    'tracks': [
        {'source': 'camera', 'fps': 9.5, 'width': 1280, 'height': 720, 'target_bitrate': 1700000, 'bitrate': 400000, 'quality_limitation_reason': 'cpu'},
        {'source': 'screen_share', 'fps': 15, 'width': 1920, 'height': 1080, 'quality_limitation_reason': 'none'},
    ],
}


class ClientHealthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.teacher = make('ch_t', User.Role.TEACHER)
        self.student = make('ch_s', User.Role.STUDENT)
        self.outsider = make('ch_o', User.Role.STUDENT)
        self.admin = make('ch_a', User.Role.SUPER_ADMIN)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=60, status=Lesson.Status.LIVE)
        self.client = APIClient()

    def post(self, user, payload=None, lesson=None, **headers):
        self.client.force_authenticate(user)
        return self.client.post(f'/api/v1/live/lesson/{(lesson or self.lesson).id}/client-health/', payload if payload is not None else GOOD,
                                format='json', **headers)

    def test_teacher_report_is_stored_with_a_summary(self):
        r = self.post(self.teacher, HTTP_USER_AGENT='Mozilla/5.0 (Windows NT 10.0) Chrome/157')
        self.assertEqual(r.status_code, 201, r.content)
        row = ClientHealthReport.objects.get(pk=r.data['id'])
        self.assertEqual((row.user_id, row.role, row.lesson_id), (self.teacher.id, 'teacher', self.lesson.id))
        self.assertEqual((row.cpu_constrained, row.limited_by, row.min_fps), (True, 'cpu', 9.5))
        self.assertEqual((row.hardware_concurrency, row.device_memory_gb, row.connection_quality), (8, 8.0, 'good'))
        self.assertIn('Windows', row.user_agent)
        self.assertEqual(len(row.tracks), 2)
        self.assertEqual(row.events, ['cpu_constrained'])

    def test_a_student_of_the_group_can_report_too(self):
        self.assertEqual(self.post(self.student, {'tracks': [{'source': 'camera', 'fps': 24, 'quality_limitation_reason': 'bandwidth'}]}).status_code, 201)
        row = ClientHealthReport.objects.get()
        self.assertEqual((row.role, row.limited_by, row.cpu_constrained), ('student', 'bandwidth', False))

    def test_cpu_flag_without_tracks_is_enough(self):
        self.assertEqual(self.post(self.teacher, {'cpu_constrained': True}).status_code, 201)
        self.assertTrue(ClientHealthReport.objects.get().cpu_constrained)

    def test_someone_outside_the_lesson_gets_404_and_nothing_is_stored(self):
        self.assertEqual(self.post(self.outsider).status_code, 404)
        self.assertEqual(ClientHealthReport.objects.count(), 0)

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(f'/api/v1/live/lesson/{self.lesson.id}/client-health/', GOOD, format='json').status_code, 401)

    def test_validation(self):
        bad = [
            {'tracks': [{'source': 'webcam'}]},
            {'tracks': [{'source': 'camera', 'quality_limitation_reason': 'magic'}]},
            {'tracks': [{'source': 'camera', 'fps': 'fast'}]},
            {'tracks': [{'source': 'camera', 'fps': 9999}]},
            {'tracks': [{'source': 'camera'}] * 9},
            {'tracks': 'x'},
            {'hardware_concurrency': 0},
            {'connection_quality': 'great'},
            {'events': [1, 2]},
            {'events': ['a'] * 11},
            {'cpu_constrained': 'yes'},
        ]
        for payload in bad:
            self.assertEqual(self.post(self.teacher, payload).status_code, 400, payload)
            cache.clear()
        self.assertEqual(ClientHealthReport.objects.count(), 0)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post(f'/api/v1/live/lesson/{self.lesson.id}/client-health/', ['x'], format='json').status_code, 400)

    def test_it_is_rate_limited(self):
        codes = [self.post(self.teacher).status_code for _ in range(14)]
        self.assertEqual(codes[:12], [201] * 12)
        self.assertIn(429, codes[12:])

    def test_unknown_extra_fields_are_ignored(self):
        self.assertEqual(self.post(self.teacher, {**GOOD, 'secret': 'x', 'tracks': [{**GOOD['tracks'][0], 'extra': 1}]}).status_code, 201)
        self.assertNotIn('extra', ClientHealthReport.objects.get().tracks[0])

    def test_admin_summary_groups_by_user_and_students_cannot_read_it(self):
        self.post(self.teacher)
        cache.clear()
        self.post(self.teacher, {'tracks': [{'source': 'camera', 'fps': 5, 'quality_limitation_reason': 'cpu'}]})
        self.post(self.student, {'tracks': [{'source': 'camera', 'fps': 30, 'quality_limitation_reason': 'none'}]})
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/v1/monitoring/client-health/?hours=24')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.data['total'], r.data['cpu_limited_total']), (3, 2))
        users = {u['username']: u for u in r.data['users']}
        self.assertEqual((users['ch_t']['reports'], users['ch_t']['cpu_limited_reports'], users['ch_t']['min_fps']), (2, 2, 5.0))
        self.assertEqual(users['ch_t']['hardware_concurrency'], None)  # eng so'nggi hisobotda yo'q edi
        self.assertEqual(users['ch_s']['cpu_limited_reports'], 0)
        self.assertEqual(r.data['users'][0]['username'], 'ch_t')  # CPU bilan zo'riqqanlar birinchi
        self.assertEqual(len(r.data['recent']), 3)
        only = self.client.get(f'/api/v1/monitoring/client-health/?user={self.student.id}')
        self.assertEqual(only.data['total'], 1)
        for who in (self.teacher, self.student):
            self.client.force_authenticate(who)
            self.assertEqual(self.client.get('/api/v1/monitoring/client-health/').status_code, 403)

    def test_prune_removes_only_old_reports(self):
        self.post(self.teacher)
        old = ClientHealthReport.objects.create(lesson=self.lesson, user=self.teacher, role='teacher')
        ClientHealthReport.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=20))
        call_command('prune_client_health')
        self.assertEqual(ClientHealthReport.objects.count(), 1)

    def test_the_prune_job_is_scheduled(self):
        from apps.core.management.commands.run_scheduler import JOBS

        self.assertIn('prune_client_health', [job[0] for job in JOBS])
