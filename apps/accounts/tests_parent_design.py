"""Ota-ona yangi dizayni (BACKEND_OTA_ONA.md): bog'lanish boshqaruvi, bildirishnomalar, login bandligi, rozilik xabarlari."""
from datetime import timedelta

from django.core import management
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def inbox(user, kind=None):
    qs = NotificationRecipient.objects.filter(user=user).select_related('notification')
    if kind:
        qs = qs.filter(notification__kind=kind)
    return list(qs)


class LinkListExtrasTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT, grade='7-sinf', first_name='Toshmat')
        self.teacher = make('t1', User.Role.TEACHER)
        for i in range(2):
            course = Course.objects.create(teacher=self.teacher, title=f'C{i}')
            Enrollment.objects.create(course=course, student=self.student, status=Enrollment.Status.APPROVED)
        self.link = ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

    def row(self, viewer):
        response = client_for(viewer).get('/api/v1/auth/links/')
        self.assertEqual(response.status_code, 200)
        return (response.json().get('results') or response.json())[0]

    def test_parent_sees_grade_course_count_and_online_state(self):
        User.objects.filter(pk=self.student.pk).update(last_seen_at=timezone.now())
        row = self.row(self.parent)
        self.assertEqual(row['grade'], '7-sinf')
        self.assertEqual(row['courses_count'], 2)
        self.assertTrue(row['is_online'])
        self.assertIsNotNone(row['last_seen_at'])
        self.assertIsNone(row['expires_at'])

    def test_offline_when_last_seen_is_old(self):
        User.objects.filter(pk=self.student.pk).update(last_seen_at=timezone.now() - timedelta(minutes=30))
        self.assertFalse(self.row(self.parent)['is_online'])

    def test_online_state_is_hidden_from_the_student_and_while_pending(self):
        User.objects.filter(pk=self.student.pk).update(last_seen_at=timezone.now())
        student_view = self.row(self.student)
        self.assertIsNone(student_view['last_seen_at'])
        self.assertIsNone(student_view['is_online'])
        ParentChildLink.objects.filter(pk=self.link.pk).update(status=ParentChildLink.Status.PENDING)
        row = self.row(self.parent)
        self.assertIsNone(row['last_seen_at'])
        self.assertIsNone(row['is_online'])
        self.assertIsNone(row['courses_count'])
        self.assertIsNotNone(row['expires_at'])


class LinkActionsTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT, first_name='Ota')
        self.other_parent = make('p2', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT, first_name='Toshmat')
        self.pending = ParentChildLink.objects.create(parent=self.parent, student=self.student)

    def test_cancel_deletes_only_own_pending_link(self):
        self.assertEqual(client_for(self.other_parent).post(f'/api/v1/auth/links/{self.pending.pk}/cancel/').status_code, 404)
        self.assertEqual(client_for(self.parent).post(f'/api/v1/auth/links/{self.pending.pk}/cancel/').status_code, 204)
        self.assertFalse(ParentChildLink.objects.filter(pk=self.pending.pk).exists())

    def test_cancel_refuses_an_approved_link(self):
        ParentChildLink.objects.filter(pk=self.pending.pk).update(status=ParentChildLink.Status.APPROVED)
        self.assertEqual(client_for(self.parent).post(f'/api/v1/auth/links/{self.pending.pk}/cancel/').status_code, 400)

    def test_student_cannot_cancel(self):
        self.assertEqual(client_for(self.student).post(f'/api/v1/auth/links/{self.pending.pk}/cancel/').status_code, 403)

    def test_remind_notifies_the_student_and_is_limited_to_once_a_day(self):
        url = f'/api/v1/auth/links/{self.pending.pk}/remind/'
        first = client_for(self.parent).post(url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(inbox(self.student, 'link.remind')), 1)
        second = client_for(self.parent).post(url)
        self.assertEqual(second.status_code, 429)
        body = second.json()
        self.assertGreater(body['error']['retry_after'], 0)
        self.assertLessEqual(body['error']['retry_after'], 24 * 3600)
        self.assertEqual(len(inbox(self.student, 'link.remind')), 1)

    def test_remind_works_again_after_a_day(self):
        client = client_for(self.parent)
        client.post(f'/api/v1/auth/links/{self.pending.pk}/remind/')
        ParentChildLink.objects.filter(pk=self.pending.pk).update(reminded_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(client.post(f'/api/v1/auth/links/{self.pending.pk}/remind/').status_code, 200)

    def test_unlink_removes_link_and_this_parents_consents_and_tells_the_student(self):
        ParentChildLink.objects.filter(pk=self.pending.pk).update(status=ParentChildLink.Status.APPROVED)
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.CAMERA, granted=True)
        response = client_for(self.parent).post(f'/api/v1/auth/links/{self.pending.pk}/unlink/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ParentChildLink.objects.filter(pk=self.pending.pk).exists())
        self.assertFalse(Consent.objects.filter(student=self.student).exists())
        self.assertEqual(len(inbox(self.student, 'link.revoked')), 1)

    def test_unlink_with_delete_verb_and_foreign_parent_is_not_found(self):
        ParentChildLink.objects.filter(pk=self.pending.pk).update(status=ParentChildLink.Status.APPROVED)
        self.assertEqual(client_for(self.other_parent).delete(f'/api/v1/auth/links/{self.pending.pk}/').status_code, 404)
        self.assertEqual(client_for(self.parent).delete(f'/api/v1/auth/links/{self.pending.pk}/').status_code, 204)

    def test_student_decline_notifies_the_parent_with_structured_data(self):
        response = client_for(self.student).post(f'/api/v1/auth/links/{self.pending.pk}/respond/', {'action': 'decline'})
        self.assertEqual(response.status_code, 200)
        (item,) = inbox(self.parent, 'link.revoked')
        self.assertEqual(item.notification.data['student_id'], str(self.student.pk))
        self.assertEqual(item.notification.data['previous_status'], 'pending')

    def test_parent_can_mute_the_kind_so_it_is_not_created(self):
        User.objects.filter(pk=self.parent.pk).update(muted_kinds=['link.revoked'])
        client_for(self.student).post(f'/api/v1/auth/links/{self.pending.pk}/respond/', {'action': 'decline'})
        self.assertEqual(inbox(self.parent, 'link.revoked'), [])

    def test_expire_command_removes_only_old_pending_requests(self):
        old = ParentChildLink.objects.create(parent=self.other_parent, student=self.student)
        ParentChildLink.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=8))
        approved_parent = make('p3', User.Role.PARENT)
        approved = ParentChildLink.objects.create(parent=approved_parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        ParentChildLink.objects.filter(pk=approved.pk).update(created_at=timezone.now() - timedelta(days=30))
        management.call_command('expire_link_requests', verbosity=0)
        self.assertFalse(ParentChildLink.objects.filter(pk=old.pk).exists())
        self.assertTrue(ParentChildLink.objects.filter(pk=self.pending.pk).exists())  # fresh pending stays
        self.assertTrue(ParentChildLink.objects.filter(pk=approved.pk).exists())  # approved never expires


class UsernameAndPasswordTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        make('toshmat_b', User.Role.STUDENT)

    def test_free_username_is_available_without_suggestions(self):
        body = client_for(self.parent).get('/api/v1/auth/username-available/?username=newkid').json()
        self.assertTrue(body['available'])
        self.assertEqual(body['suggestions'], [])

    def test_taken_username_gets_free_suggestions(self):
        make('toshmat_b2', User.Role.STUDENT)
        body = client_for(self.parent).get('/api/v1/auth/username-available/?username=Toshmat_B').json()  # case-insensitive
        self.assertFalse(body['available'])
        self.assertEqual(len(body['suggestions']), 3)
        self.assertNotIn('toshmat_b2', [s.lower() for s in body['suggestions']])
        for suggestion in body['suggestions']:
            self.assertFalse(User.objects.filter(username__iexact=suggestion).exists())

    def test_invalid_username_is_not_available(self):
        body = client_for(self.parent).get('/api/v1/auth/username-available/?username=a%20b').json()
        self.assertFalse(body['available'])
        self.assertFalse(body['valid'])

    def test_requires_login_and_a_value(self):
        self.assertEqual(APIClient().get('/api/v1/auth/username-available/?username=x').status_code, 401)
        self.assertEqual(client_for(self.parent).get('/api/v1/auth/username-available/').status_code, 400)

    def test_parent_created_child_must_change_password_until_it_does(self):
        response = client_for(self.parent).post(
            '/api/v1/auth/children/', {'username': 'kid1', 'password': PASSWORD, 'first_name': 'Kid', 'grade': '5-sinf'},
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['must_change_password'])
        kid = User.objects.get(username='kid1')
        self.assertEqual(kid.grade, '5-sinf')
        login = APIClient().post('/api/v1/auth/login/', {'username': 'kid1', 'password': PASSWORD})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()['must_change_password'])
        me = client_for(kid).get('/api/v1/auth/me/').json()
        self.assertTrue(me['must_change_password'])
        changed = client_for(kid).post('/api/v1/auth/password/change/', {'current_password': PASSWORD, 'new_password': 'Another#Pass456'})
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertFalse(client_for(kid).get('/api/v1/auth/me/').json()['must_change_password'])

    def test_teacher_created_child_does_not_need_a_password_change(self):
        teacher = make('t1', User.Role.TEACHER)
        response = client_for(teacher).post('/api/v1/auth/children/', {'username': 'kid2', 'password': PASSWORD})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(response.json()['must_change_password'])

    def test_notification_preferences_and_muted_kinds_are_editable_on_me(self):
        client = client_for(self.parent)
        response = client.patch('/api/v1/auth/me/', {
            'notify_child_absent': False, 'notify_child_new_device': False, 'notify_homework_due': False,
            'muted_kinds': ['attendance.joined', 'attendance.joined', 'security.new_device'],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertFalse(body['notify_child_absent'])
        self.assertEqual(body['muted_kinds'], ['attendance.joined', 'security.new_device'])
        self.assertEqual(client.patch('/api/v1/auth/me/', {'muted_kinds': 'nope'}, format='json').status_code, 400)
        self.assertEqual(client.patch('/api/v1/auth/me/', {'must_change_password': True}, format='json').status_code, 200)
        self.assertFalse(User.objects.get(pk=self.parent.pk).must_change_password)  # read-only


class SecurityAndConsentNotificationTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.quiet_parent = make('p2', User.Role.PARENT, notify_child_new_device=False)
        self.student = make('s1', User.Role.STUDENT, first_name='Toshmat')
        self.teacher = make('t1', User.Role.TEACHER)
        for parent in (self.parent, self.quiet_parent):
            ParentChildLink.objects.create(parent=parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        course = Course.objects.create(teacher=self.teacher, title='English')
        Enrollment.objects.create(course=course, student=self.student, status=Enrollment.Status.APPROVED)

    def login(self, agent):
        return APIClient().post('/api/v1/auth/login/', {'username': 's1', 'password': PASSWORD}, HTTP_USER_AGENT=agent,
                                HTTP_X_FORWARDED_FOR='1.2.3.4')

    def test_new_device_login_notifies_parents_who_did_not_mute_it(self):
        self.assertEqual(self.login('Mozilla/5.0 (Windows NT 10.0) Chrome/130').status_code, 200)
        self.assertEqual(inbox(self.parent, 'security.new_device'), [])  # first login is not a "new device"
        self.assertEqual(self.login('Mozilla/5.0 (Linux; Android 14; SM-A546B) Chrome/130 Mobile').status_code, 200)
        (item,) = inbox(self.parent, 'security.new_device')
        data = item.notification.data
        self.assertEqual(data['student_id'], str(self.student.pk))
        self.assertEqual(data['ip'], '1.2.3.4')
        self.assertIn('SM-A546B', data['device'])
        self.assertIn('at', data)
        self.assertEqual(item.notification.link_type, 'login')
        self.assertEqual(inbox(self.quiet_parent, 'security.new_device'), [])

    def test_same_device_does_not_notify(self):
        agent = 'Mozilla/5.0 (Windows NT 10.0) Chrome/130'
        self.login(agent)
        self.login(agent)
        self.assertEqual(inbox(self.parent, 'security.new_device'), [])

    def test_consent_change_notifies_the_childs_teachers_once_per_change(self):
        client = client_for(self.parent)
        body = {'student': str(self.student.pk), 'kind': 'camera', 'granted': False}
        self.assertEqual(client.post('/api/v1/auth/consents/', body, format='json').status_code, 201)
        (item,) = inbox(self.teacher, 'consent.changed')
        self.assertEqual(item.notification.data['kind'], 'camera')
        self.assertFalse(item.notification.data['granted'])
        client.post('/api/v1/auth/consents/', body, format='json')  # same value again: no new notification
        self.assertEqual(len(inbox(self.teacher, 'consent.changed')), 1)
        client.post('/api/v1/auth/consents/', {**body, 'granted': True}, format='json')
        self.assertEqual(len(inbox(self.teacher, 'consent.changed')), 2)


class NotificationManagementTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

    def send(self, kind='attendance.joined', n=1):
        from apps.notifications import services

        return [services.send_event(sender=self.student, recipients=[self.parent], kind=kind, description=f'x{i}',
                                    data={'student_id': str(self.student.pk)}, link_type='lesson', link_id=str(i)) for i in range(n)]

    def test_event_exposes_data_and_link_in_the_inbox(self):
        self.send()
        row = client_for(self.parent).get('/api/v1/notifications/').json()
        item = (row.get('results') or row)[0]['notification']
        self.assertEqual(item['kind'], 'attendance.joined')
        self.assertEqual(item['data']['student_id'], str(self.student.pk))
        self.assertEqual(item['link'], {'kind': 'lesson', 'id': '0'})

    def test_delete_removes_only_my_inbox_row(self):
        (n,) = self.send()
        other = make('p2', User.Role.PARENT)
        NotificationRecipient.objects.create(notification=n, user=other)
        self.assertEqual(client_for(self.parent).delete(f'/api/v1/notifications/{n.pk}/').status_code, 204)
        self.assertEqual(inbox(self.parent), [])
        self.assertEqual(len(inbox(other)), 1)
        self.assertEqual(client_for(self.parent).delete(f'/api/v1/notifications/{n.pk}/').status_code, 404)

    def test_mark_unread_undoes_read_all(self):
        notifications = self.send(n=3)
        client = client_for(self.parent)
        client.post('/api/v1/notifications/read-all/')
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').json()['count'], 0)
        response = client.post('/api/v1/notifications/mark-unread/', {'ids': [str(n.pk) for n in notifications[:2]]}, format='json')
        self.assertEqual(response.json()['updated'], 2)
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').json()['count'], 2)
        self.assertEqual(client.post('/api/v1/notifications/mark-unread/', {'ids': []}, format='json').status_code, 400)

    def test_muted_kind_is_not_created_for_the_muter_only(self):
        other = make('p2', User.Role.PARENT)
        User.objects.filter(pk=self.parent.pk).update(muted_kinds=['attendance.joined'])
        self.parent.refresh_from_db()
        from apps.notifications import services

        services.send_event(sender=self.student, recipients=[self.parent, other], kind='attendance.joined', description='x')
        self.assertEqual(inbox(self.parent), [])
        self.assertEqual(len(inbox(other)), 1)
        self.assertIsNone(services.send_event(sender=self.student, recipients=[self.parent], kind='attendance.joined', description='y'))
