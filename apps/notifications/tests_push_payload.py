"""Push mazmuni: sarlavha ("Fokus" emas), HTML'siz matn, fonda yuborish."""
import json
from unittest import mock

from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.core import background

from . import services
from .models import Notification


def make(username, role=User.Role.STUDENT):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class PushTitleTests(TestCase):
    def setUp(self):
        self.sender = make('sender', User.Role.ADMIN)

    def note(self, **extra):
        return Notification.objects.create(sender=self.sender, description='x', target_type='user', **extra)

    def test_a_system_notification_uses_its_kind_title(self):
        self.assertEqual(services.push_title(self.note(kind='recording_ready')), 'Dars yozuvi tayyor')
        self.assertEqual(services.push_title(self.note(kind='homework_reviewed')), 'Yangi baho')

    def test_an_unknown_kind_falls_back_to_the_inbox_category_title(self):
        self.assertEqual(services.push_title(self.note(kind='something_new')), "E'lon")

    def test_a_teacher_message_shows_the_teacher_and_the_group(self):
        title = services.push_title(self.note(data={'teacher_name': 'Ali Valiyev', 'course_title': 'Algebra'}))
        self.assertEqual(title, 'Ali Valiyev · Algebra')

    def test_the_old_brand_name_is_gone(self):
        for kind in ('', 'recording_ready', 'payment_reminder', 'something_new'):
            self.assertNotEqual(services.push_title(self.note(kind=kind)), 'Fokus')


class PushDeliveryTests(TestCase):
    def setUp(self):
        self.admin = make('adm', User.Role.ADMIN)
        self.student = make('stu')
        services.save_push_subscription(user=self.student, endpoint='https://push.example/abc', p256dh='p', auth='a')

    def send(self, description, **extra):
        with mock.patch('pywebpush.webpush') as webpush, self.captureOnCommitCallbacks(execute=True):
            services.send_notification(
                sender=self.admin, description=description, target_type='user', user_id=self.student.id, **extra,
            )
        return json.loads(webpush.call_args.kwargs['data'])

    def test_web_push_body_has_no_html_tags(self):
        payload = self.send('<p>Salom <b>dunyo</b></p>')
        self.assertEqual(payload['body'], 'Salom dunyo')

    def test_web_push_title_is_the_kind_title(self):
        payload = self.send('Yozuv tayyor', kind='recording_ready', link_type='lesson', link_id='abc')
        self.assertEqual(payload['title'], 'Dars yozuvi tayyor')
        self.assertEqual((payload['link_type'], payload['link_id'], payload['kind']), ('lesson', 'abc', 'recording_ready'))

    def test_mobile_push_title_and_plain_body(self):
        from .services import register_push_device

        register_push_device(user=self.student, token='tok', platform='android', device_id='d1')
        fake = mock.MagicMock()
        fake.UnregisteredError = type('UnregisteredError', (Exception,), {})
        fake.SenderIdMismatchError = type('SenderIdMismatchError', (Exception,), {})
        with mock.patch('apps.notifications.services._firebase_messaging', return_value=fake), \
                mock.patch('pywebpush.webpush'), self.captureOnCommitCallbacks(execute=True):
            services.send_notification(
                sender=self.admin, description='<b>Baho</b> qo\'yildi', target_type='user', user_id=self.student.id, kind='homework_reviewed',
            )
        kwargs = fake.Notification.call_args.kwargs
        self.assertEqual((kwargs['title'], kwargs['body']), ('Yangi baho', "Baho qo'yildi"))

    def test_push_is_handed_to_the_background_not_sent_inside_the_request(self):
        with mock.patch('apps.notifications.services.background.run') as run, self.captureOnCommitCallbacks(execute=True):
            services.send_notification(sender=self.admin, description='Salom', target_type='user', user_id=self.student.id)
        names = {call.args[0].__name__ for call in run.call_args_list}
        self.assertTrue({'send_web_push', 'send_mobile_push'} <= names, names)

    @override_settings(BACKGROUND_ASYNC=True)
    def test_a_slow_push_does_not_block_the_sender(self):
        import threading

        started, release = threading.Event(), threading.Event()

        def slow(*args, **kwargs):
            started.set()
            release.wait(5)

        with mock.patch('apps.notifications.services.send_web_push', side_effect=slow), \
                mock.patch('apps.notifications.services.send_mobile_push'), self.captureOnCommitCallbacks(execute=True):
            services.send_notification(sender=self.admin, description='Salom', target_type='user', user_id=self.student.id)
            # send_notification qaytdi, push esa hali tugamagan — so'rov kutmadi
            self.assertFalse(release.is_set())
        self.assertTrue(started.wait(5))
        release.set()
        self.assertIsNotNone(background)
