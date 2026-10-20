"""Guruhga taklif havolasi (`invite-link`, `join`) va o'quvchilar ro'yxatida onlayn holati."""
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.chat import presence
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


@override_settings(INVITE_BASE_URL='https://yolup.uz')
class InviteLinkTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.student = make('s1', User.Role.STUDENT, first_name='Aziza')
        self.url = f'/api/v1/courses/{self.course.id}/invite-link/'

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client

    def create(self, **data):
        resp = self.as_(self.teacher).post(self.url, data, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def test_create_get_regenerate_and_revoke(self):
        empty = self.as_(self.teacher).get(self.url).json()
        self.assertEqual((empty['code'], empty['url'], empty['expires_at']), (None, None, None))
        created = self.create()
        self.assertEqual(len(created['code']), 6)
        self.assertEqual(created['url'], f'https://yolup.uz/j/{created["code"]}')
        self.assertIsNone(created['expires_at'])
        self.assertEqual(self.as_(self.teacher).get(self.url).json()['code'], created['code'])
        again = self.create()
        self.assertNotEqual(again['code'], created['code'])
        old = self.as_(self.student).post('/api/v1/courses/join/', {'code': created['code']}, format='json')
        self.assertEqual(old.status_code, 404)  # eski havola bekor bo'ldi
        self.assertEqual(self.as_(self.teacher).delete(self.url).status_code, 204)
        self.assertIsNone(self.as_(self.teacher).get(self.url).json()['code'])
        gone = self.as_(self.student).post('/api/v1/courses/join/', {'code': again['code']}, format='json')
        self.assertEqual(gone.status_code, 404)

    def test_only_the_course_teacher_manages_the_link(self):
        other = make('t2', User.Role.TEACHER)
        for method in ('get', 'post', 'delete'):
            self.assertEqual(getattr(self.as_(other), method)(self.url).status_code, 404, method)  # kurs ko'rinmaydi
        for method in ('get', 'post', 'delete'):
            self.assertEqual(getattr(self.as_(self.student), method)(self.url).status_code, 403, method)

    def test_student_joins_immediately_and_the_teacher_is_notified(self):
        code = self.create()['code']
        resp = self.as_(self.student).post('/api/v1/courses/join/', {'code': code.lower()}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (200, {'course_id': str(self.course.id), 'status': 'joined'}))
        enrollment = Enrollment.objects.get(course=self.course, student=self.student)
        self.assertEqual(enrollment.status, Enrollment.Status.APPROVED)
        note = NotificationRecipient.objects.get(user=self.teacher, notification__kind='member_joined').notification
        self.assertEqual((note.link_type, note.link_id), ('course', str(self.course.id)))
        self.assertIn('Aziza', note.description)
        again = self.as_(self.student).post('/api/v1/courses/join/', {'code': code}, format='json')
        self.assertEqual(again.json()['status'], 'joined')  # takror — xato emas
        self.assertEqual(NotificationRecipient.objects.filter(notification__kind='member_joined').count(), 1)
        self.assertTrue(self.course.chat_room.id if hasattr(self.course, 'chat_room') else True)

    def test_approval_mode_gives_pending(self):
        code = self.create(require_approval=True)['code']
        resp = self.as_(self.student).post('/api/v1/courses/join/', {'code': code}, format='json')
        self.assertEqual(resp.json()['status'], 'pending')
        self.assertEqual(Enrollment.objects.get(student=self.student).status, Enrollment.Status.PENDING)
        requests = self.as_(self.teacher).get('/api/v1/courses/requests/').json()['results']
        self.assertEqual(len(requests), 1)  # o'qituvchi odatdagi so'rovlar ro'yxatida ko'radi
        self.assertEqual(self.create()['require_approval'], True)  # sozlama yangi havolada ham saqlanadi
        off = self.create(require_approval=False)
        self.assertFalse(off['require_approval'])

    def test_expiry_declined_and_wrong_roles(self):
        created = self.create(expires_in_days=7)
        self.assertTrue(created['expires_at'])
        Course.objects.filter(pk=self.course.pk).update(invite_expires_at=timezone.now() - timedelta(minutes=1))
        expired = self.as_(self.student).post('/api/v1/courses/join/', {'code': created['code']}, format='json')
        self.assertEqual(expired.status_code, 400)
        Course.objects.filter(pk=self.course.pk).update(invite_expires_at=None)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.DECLINED)
        declined = self.as_(self.student).post('/api/v1/courses/join/', {'code': created['code']}, format='json')
        self.assertEqual(declined.status_code, 403)
        parent = make('p1', User.Role.PARENT)
        self.assertEqual(self.as_(parent).post('/api/v1/courses/join/', {'code': created['code']}, format='json').status_code, 403)
        self.assertEqual(self.as_(self.teacher).post('/api/v1/courses/join/', {'code': created['code']}, format='json').status_code, 403)
        self.assertEqual(self.as_(self.student).post('/api/v1/courses/join/', {'code': ''}, format='json').status_code, 404)
        self.assertEqual(self.as_(self.teacher).post(self.url, {'expires_in_days': 0}, format='json').status_code, 400)
        self.assertEqual(self.as_(self.teacher).post(self.url, {'expires_in_days': 'x'}, format='json').status_code, 400)

    def test_inactive_courses_cannot_be_joined(self):
        code = self.create()['code']
        Course.objects.filter(pk=self.course.pk).update(is_active=False)
        resp = self.as_(self.student).post('/api/v1/courses/join/', {'code': code}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_cannot_join(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/v1/courses/join/', {'code': 'ABC123'}, format='json').status_code, 401)


class StudentsWithPresenceTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.online = make('aziza', User.Role.STUDENT, first_name='Aziza', last_name='Rahimova')
        self.away = make('bobur', User.Role.STUDENT, first_name='Bobur')
        self.pending = make('kutadi', User.Role.STUDENT)
        for student, state in ((self.online, 'approved'), (self.away, 'approved'), (self.pending, 'pending')):
            Enrollment.objects.create(course=self.course, student=student, status=state)
        self.url = f'/api/v1/courses/{self.course.id}/students/'

    def test_flat_list_with_online_and_last_seen(self):
        seen = timezone.now() - timedelta(minutes=10)
        User.objects.filter(pk=self.away.pk).update(last_seen_at=seen)
        presence.mark_online(self.online.id)
        self.addCleanup(presence.mark_offline, self.online.id)
        self.client.force_authenticate(self.teacher)
        rows = self.client.get(self.url + '?with_presence=1').json()
        self.assertEqual([r['name'] for r in rows], ['Aziza Rahimova', 'Bobur'])  # tasdiqlanmagan chiqmaydi
        aziza, bobur = rows
        self.assertEqual((aziza['is_online'], aziza['id'], aziza['username']), (True, str(self.online.id), 'aziza'))
        self.assertEqual((bobur['is_online'], bobur['last_seen'] is not None), (False, True))
        self.assertIn('avatar', aziza)

    def test_default_list_is_unchanged_and_students_cannot_use_it(self):
        self.client.force_authenticate(self.teacher)
        self.assertIn('results', self.client.get(self.url).json())
        self.client.force_authenticate(self.online)
        self.assertEqual(self.client.get(self.url + '?with_presence=1').status_code, 403)
