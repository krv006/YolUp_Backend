"""`target_type: "course"` — o'qituvchi guruhning barcha o'quvchilariga (+ ixtiyoriy ota-onalariga) xabar yuboradi."""
from rest_framework.test import APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import Notification, NotificationRecipient


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class CourseTargetTests(APITestCase):
    def setUp(self):
        self.teacher = make('ct_t', User.Role.TEACHER)
        self.other_teacher = make('ct_t2', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='A')
        self.other_course = Course.objects.create(teacher=self.other_teacher, title='B')
        self.s1, self.s2, self.s3 = (make(f'ct_s{i}', User.Role.STUDENT) for i in range(3))
        self.parent = make('ct_p', User.Role.PARENT)
        self.pending_parent = make('ct_pp', User.Role.PARENT)
        Enrollment.objects.create(course=self.course, student=self.s1, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.s2, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.s3, status=Enrollment.Status.PENDING)
        ParentChildLink.objects.create(parent=self.parent, student=self.s1, status=ParentChildLink.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.pending_parent, student=self.s2, status=ParentChildLink.Status.PENDING)

    def send(self, user, **body):
        self.client.force_authenticate(user)
        return self.client.post('/api/v1/notifications/send/', {'description': 'Eslatma', 'target_type': 'course', **body}, format='json')

    def recipients(self, response):
        return set(NotificationRecipient.objects.filter(notification_id=response.json()['id']).values_list('user__username', flat=True))

    def test_teacher_reaches_all_approved_students_of_the_course(self):
        response = self.send(self.teacher, course_id=str(self.course.id))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.recipients(response), {'ct_s0', 'ct_s1'})  # kutayotgan (s3) va ota-onalar yo'q
        self.assertEqual(Notification.objects.get(pk=response.json()['id']).target_type, 'course')

    def test_include_parents_adds_only_approved_parents(self):
        response = self.send(self.teacher, course_id=str(self.course.id), include_parents=True)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.recipients(response), {'ct_s0', 'ct_s1', 'ct_p'})

    def test_teacher_cannot_send_to_someone_elses_course(self):
        self.assertEqual(self.send(self.teacher, course_id=str(self.other_course.id)).status_code, 403)

    def test_course_id_is_required_for_teacher_and_unknown_course_is_404_for_admin(self):
        self.assertEqual(self.send(self.teacher).status_code, 403)
        admin = make('ct_admin', User.Role.ADMIN)
        self.assertEqual(self.send(admin, course_id='00000000-0000-0000-0000-000000000000').status_code, 404)
        self.assertEqual(self.send(admin, course_id=str(self.course.id)).status_code, 201)


class TeacherNotificationTitleTests(CourseTargetTests):
    """O'qituvchi yozgan xabar: sarlavha "O'qituvchi ismi · Guruh nomi", matn — o'qituvchi yozgan xabar (2026-11-12)."""

    def test_in_app_title_and_data_carry_the_teacher_and_the_group(self):
        self.teacher.first_name, self.teacher.last_name = 'Ali', 'Valiyev'
        self.teacher.save()
        r = self.send(self.teacher, course_id=str(self.course.id), description='<p>Ertaga dars soat 18:00 da</p>')
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body['title'], 'Ali Valiyev · A')
        self.assertEqual(body['body'], 'Ertaga dars soat 18:00 da')  # o'qituvchi yozgan matnning o'zi
        self.assertEqual((body['data']['teacher_name'], body['data']['course_title'], body['data']['course_id']),
                         ('Ali Valiyev', 'A', str(self.course.id)))

    def test_name_falls_back_to_the_username_and_inbox_uses_the_same_title(self):
        r = self.send(self.teacher, course_id=str(self.course.id))
        self.assertEqual(r.json()['title'], 'ct_t · A')
        self.client.force_authenticate(self.s1)
        inbox = self.client.get('/api/v1/notifications/')
        row = (inbox.json().get('results') or inbox.json())[0]
        self.assertEqual((row.get('notification') or row)['title'], 'ct_t · A')

    def test_system_notifications_keep_their_titles_and_admin_messages_are_unchanged(self):
        from apps.notifications.services import send_notification

        n = send_notification(sender=self.teacher, description='Dars bekor', target_type='user', user_id=self.s1.id, kind='lesson_cancelled')
        self.assertEqual(n.data, {})
        self.client.force_authenticate(self.s1)
        inbox = self.client.get('/api/v1/notifications/').json()
        titles = [(r.get('notification') or r)['title'] for r in (inbox.get('results') or inbox)]
        self.assertIn('Dars bekor qilindi', titles)

    def test_direct_message_without_a_group_shows_only_the_teacher(self):
        r = self.send(self.teacher, target_type='users', user_ids=[str(self.s1.id)])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['title'], 'ct_t')

    def test_push_uses_the_same_title(self):
        from unittest import mock

        from apps.notifications.models import PushSubscription

        PushSubscription.objects.create(user=self.s1, endpoint='https://push.example/1', p256dh='k', auth='a')
        with mock.patch('pywebpush.webpush') as webpush, self.captureOnCommitCallbacks(execute=True):
            self.send(self.teacher, course_id=str(self.course.id), description='Salom')
        import json
        payload = json.loads(webpush.call_args.kwargs['data'])
        self.assertEqual((payload['title'], payload['body']), ('ct_t · A', 'Salom'))
