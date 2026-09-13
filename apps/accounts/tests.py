import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from .models import ParentChildLink, User

PASSWORD = 'StrongPass123!'


def register(client, username, role, **extra):
    """Testlar uchun umumiy yordamchi — o'qituvchi darhol tasdiqlanadi,
    aks holda deyarli barcha testlar (register -> course.create va h.k.) buziladi.
    Tasdiqlash oqimining o'zi alohida testda tekshiriladi (TeacherActivationTests)."""
    resp = client.post('/api/v1/auth/register/', {
        'username': username, 'password': PASSWORD, 'role': role, **extra,
    })
    if resp.status_code == 201 and role == 'teacher':
        User.objects.filter(username=username).update(is_approved=True)
    return resp


def login(client, username):
    resp = client.post('/api/v1/auth/login/', {'username': username, 'password': PASSWORD})
    return resp.json()['access']


class AuthTests(APITestCase):
    def test_register_and_login_teacher(self):
        resp = register(self.client, 'teacher1', 'teacher')
        self.assertEqual(resp.status_code, 201)
        token = login(self.client, 'teacher1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.json()['role'], 'teacher')

    def test_student_can_register_publicly(self):
        resp = register(self.client, 'student1', 'student')
        self.assertEqual(resp.status_code, 201)
        token = login(self.client, 'student1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.json()['role'], 'student')
        # ota-ona keyin bog'lanishi uchun invite_code hali ham beriladi
        self.assertTrue(me.json()['invite_code'])

    def test_register_returns_tokens_for_immediate_auto_login(self):
        """Ro'yxatdan o'tish javobida access/refresh bo'lishi kerak — alohida
        `/login/` chaqirmasdan darhol autentifikatsiyalash mumkin bo'lishi uchun."""
        resp = register(self.client, 'autologin1', 'teacher')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn('access', body)
        self.assertIn('refresh', body)

        me = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f"Bearer {body['access']}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['username'], 'autologin1')

    def test_unknown_role_cannot_register_publicly(self):
        resp = register(self.client, 'weird1', 'admin')
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertFalse(body['success'])
        self.assertIn('error', body)

    def test_error_envelope_shape(self):
        resp = self.client.post('/api/v1/auth/login/', {'username': 'nobody', 'password': 'x'})
        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertFalse(body['success'])
        self.assertIn('code', body['error'])
        self.assertIn('message', body['error'])

    def test_update_avatar(self):
        register(self.client, 'teacher2', 'teacher')
        token = login(self.client, 'teacher2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        buf = io.BytesIO()
        Image.new('RGB', (10, 10), 'red').save(buf, format='PNG')
        avatar = SimpleUploadedFile('avatar.png', buf.getvalue(), content_type='image/png')
        resp = self.client.patch(
            '/api/v1/auth/me/', {'avatar': avatar}, format='multipart',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['avatar'])
        self.assertIn('/media/avatars/', resp.json()['avatar'])

    def test_preferred_language_defaults_to_uz_and_is_updatable(self):
        register(self.client, 'lang1', 'student')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "lang1")}')

        self.assertEqual(self.client.get('/api/v1/auth/me/').json()['preferred_language'], 'uz')

        resp = self.client.patch('/api/v1/auth/me/', {'preferred_language': 'ru'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['preferred_language'], 'ru')
        # Boshqa "qurilma"dan (yangi so'rov) ham saqlangan qiymat qaytishi kerak.
        self.assertEqual(self.client.get('/api/v1/auth/me/').json()['preferred_language'], 'ru')

    def test_preferred_language_rejects_unsupported_code(self):
        register(self.client, 'lang2', 'student')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "lang2")}')

        resp = self.client.patch('/api/v1/auth/me/', {'preferred_language': 'fr'})
        self.assertEqual(resp.status_code, 400)

    def test_role_and_invite_code_stay_read_only_when_updating_language(self):
        register(self.client, 'lang3', 'student')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "lang3")}')
        original_invite_code = self.client.get('/api/v1/auth/me/').json()['invite_code']

        resp = self.client.patch('/api/v1/auth/me/', {
            'preferred_language': 'en', 'role': 'admin', 'invite_code': 'HACKED',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['role'], 'student')
        self.assertEqual(resp.json()['invite_code'], original_invite_code)


class CertificateTests(APITestCase):
    def upload(self, filename='cert.png'):
        buf = io.BytesIO()
        Image.new('RGB', (10, 10), 'blue').save(buf, format='PNG')
        return SimpleUploadedFile(filename, buf.getvalue(), content_type='image/png')

    def test_teacher_uploads_certificate_and_sees_it_on_profile(self):
        register(self.client, 'teacher3', 'teacher')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "teacher3")}')

        resp = self.client.post('/api/v1/auth/me/certificates/', {
            'file': self.upload(), 'title': "IELTS 8.0",
        }, format='multipart')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['title'], 'IELTS 8.0')

        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(len(me.json()['certificates']), 1)
        self.assertEqual(me.json()['certificates'][0]['title'], 'IELTS 8.0')

    def test_non_teacher_cannot_upload_certificate(self):
        register(self.client, 'parent5', 'parent')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "parent5")}')
        resp = self.client.post('/api/v1/auth/me/certificates/', {'file': self.upload()}, format='multipart')
        self.assertEqual(resp.status_code, 403)

    def test_teacher_deletes_own_certificate(self):
        register(self.client, 'teacher4', 'teacher')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "teacher4")}')
        cert_id = self.client.post(
            '/api/v1/auth/me/certificates/', {'file': self.upload()}, format='multipart',
        ).json()['id']

        resp = self.client.delete(f'/api/v1/auth/me/certificates/{cert_id}/')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(len(self.client.get('/api/v1/auth/me/').json()['certificates']), 0)

    def test_teacher_cannot_delete_foreign_certificate(self):
        register(self.client, 'teacher5', 'teacher')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "teacher5")}')
        cert_id = self.client.post(
            '/api/v1/auth/me/certificates/', {'file': self.upload()}, format='multipart',
        ).json()['id']

        register(self.client, 'teacher6', 'teacher')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "teacher6")}')
        resp = self.client.delete(f'/api/v1/auth/me/certificates/{cert_id}/')
        self.assertEqual(resp.status_code, 404)


class TeacherActivationTests(APITestCase):
    """O'qituvchi ro'yxatdan o'tgach kira oladi, lekin admin tasdiqlamaguncha
    kurs ochish kabi amallarga ruxsati yo'q (real oqim, `register()`
    yordamchisidagi avto-tasdiqni chetlab o'tib)."""

    def test_teacher_actions_blocked_until_admin_approves(self):
        resp = self.client.post('/api/v1/auth/register/', {
            'username': 'newteacher', 'password': PASSWORD, 'role': 'teacher',
        })
        self.assertFalse(resp.json()['is_approved'])

        token = login(self.client, 'newteacher')  # kira oladi
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.post('/api/v1/courses/', {'title': 'Hack'}).status_code, 403)

        User.objects.create_user(username='admin1', password=PASSWORD, role=User.Role.ADMIN)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "admin1")}')
        teacher_id = User.objects.get(username='newteacher').id
        resp = self.client.post(f'/api/v1/auth/teachers/{teacher_id}/approve/')
        self.assertTrue(resp.json()['is_approved'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(
            self.client.post('/api/v1/courses/', {'title': 'Algebra'}).status_code, 201,
        )

    def test_admin_is_notified_when_teacher_registers(self):
        from apps.notifications.models import NotificationRecipient

        admin = User.objects.create_user(username='admin_notif', password=PASSWORD, role=User.Role.ADMIN)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post('/api/v1/auth/register/', {
                'username': 'notifteacher', 'password': PASSWORD, 'role': 'teacher',
            })
        self.assertEqual(resp.status_code, 201)
        recipients = NotificationRecipient.objects.filter(user=admin).select_related('notification')
        self.assertEqual(len(recipients), 1)
        self.assertIn('notifteacher', recipients[0].notification.description)
        self.assertEqual(recipients[0].notification.kind, 'teacher_pending_approval')

    def test_all_admins_notified_but_not_other_teachers(self):
        from apps.notifications.models import NotificationRecipient

        admin1 = User.objects.create_user(username='admin_a', password=PASSWORD, role=User.Role.ADMIN)
        admin2 = User.objects.create_user(username='admin_b', password=PASSWORD, role=User.Role.SUPER_ADMIN)
        register(self.client, 'bystander_teacher', 'teacher')
        bystander = User.objects.get(username='bystander_teacher')

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post('/api/v1/auth/register/', {
                'username': 'scopeteacher', 'password': PASSWORD, 'role': 'teacher',
            })

        self.assertTrue(NotificationRecipient.objects.filter(user=admin1).exists())
        self.assertTrue(NotificationRecipient.objects.filter(user=admin2).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=bystander).exists())

    def test_student_and_parent_registration_do_not_notify_admins(self):
        from apps.notifications.models import NotificationRecipient

        admin = User.objects.create_user(username='admin_noteach', password=PASSWORD, role=User.Role.ADMIN)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post('/api/v1/auth/register/', {
                'username': 'juststudent', 'password': PASSWORD, 'role': 'student',
            })
            self.client.post('/api/v1/auth/register/', {
                'username': 'justparent', 'password': PASSWORD, 'role': 'parent',
            })
        self.assertFalse(NotificationRecipient.objects.filter(user=admin).exists())

    def test_teacher_is_notified_when_approved(self):
        from apps.notifications.models import NotificationRecipient

        self.client.post('/api/v1/auth/register/', {
            'username': 'approveteacher', 'password': PASSWORD, 'role': 'teacher',
        })
        teacher = User.objects.get(username='approveteacher')
        User.objects.create_user(username='admin_approve', password=PASSWORD, role=User.Role.ADMIN)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "admin_approve")}')

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f'/api/v1/auth/teachers/{teacher.id}/approve/')
        self.assertEqual(resp.status_code, 200)

        recipients = NotificationRecipient.objects.filter(user=teacher).select_related('notification')
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0].notification.kind, 'teacher_approved')


class LinkFlowTests(APITestCase):
    def setUp(self):
        register(self.client, 'parent1', 'parent')
        self.parent_token = login(self.client, 'parent1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        resp = self.client.post('/api/v1/auth/children/', {
            'username': 'child1', 'password': PASSWORD, 'first_name': 'Sardor',
        })
        self.invite_code = resp.json()['invite_code']
        self.child_token = login(self.client, 'child1')

    def test_child_create_gives_approved_link(self):
        link = ParentChildLink.objects.get(parent__username='parent1', student__username='child1')
        self.assertEqual(link.status, ParentChildLink.Status.APPROVED)
        self.assertTrue(self.invite_code.startswith('FK-'))

    def test_invite_code_flow_approve_and_revoke(self):
        register(self.client, 'parent2', 'parent')
        parent2_token = login(self.client, 'parent2')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {parent2_token}')
        resp = self.client.post('/api/v1/auth/links/request/', {'invite_code': self.invite_code})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['status'], 'pending')
        link_id = resp.json()['id']

        # student approves
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.child_token}')
        resp = self.client.post(f'/api/v1/auth/links/{link_id}/respond/', {'action': 'approve'})
        self.assertEqual(resp.json()['status'], 'approved')

        # student revokes any time (consent model)
        resp = self.client.post(f'/api/v1/auth/links/{link_id}/respond/', {'action': 'decline'})
        self.assertEqual(resp.json()['status'], 'declined')

    def test_wrong_invite_code_404(self):
        register(self.client, 'parent3', 'parent')
        token = login(self.client, 'parent3')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.post('/api/v1/auth/links/request/', {'invite_code': 'FK-XXXX'})
        self.assertEqual(resp.status_code, 404)

    def test_consent_requires_approved_link(self):
        register(self.client, 'parent4', 'parent')
        token = login(self.client, 'parent4')
        child_id = User.objects.get(username='child1').id
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.post('/api/v1/auth/consents/', {
            'student': child_id, 'kind': 'analytics', 'granted': True,
        })
        self.assertEqual(resp.status_code, 403)

        # linked parent CAN set consent
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        resp = self.client.post('/api/v1/auth/consents/', {
            'student': child_id, 'kind': 'analytics', 'granted': True,
        })
        self.assertEqual(resp.status_code, 201)

    def test_student_cannot_create_child(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.child_token}')
        resp = self.client.post('/api/v1/auth/children/', {
            'username': 'child2', 'password': PASSWORD,
        })
        self.assertEqual(resp.status_code, 403)

    def test_teacher_can_create_child_without_parent_link(self):
        register(self.client, 'teacher_x', 'teacher')
        teacher_token = login(self.client, 'teacher_x')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_token}')

        resp = self.client.post('/api/v1/auth/children/', {
            'username': 'child_by_teacher', 'password': PASSWORD, 'first_name': 'Nodira',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()['invite_code'].startswith('FK-'))

        # o'qituvchi ota-ona emas — bog'lanish yaratilmagan
        self.assertFalse(
            ParentChildLink.objects.filter(student__username='child_by_teacher').exists()
        )

        # yaratilgan o'quvchi o'zi login qila oladi
        student_token = login(self.client, 'child_by_teacher')
        self.assertTrue(student_token)


class LoginJournalTests(APITestCase):
    """Login jurnali: IP/qurilma o'zgarishi bayroqlari va tarix endpointi."""

    def setUp(self):
        register(self.client, 'lj_p', 'parent')
        self.parent_token = login(self.client, 'lj_p')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.child_id = self.client.post(
            '/api/v1/auth/children/', {'username': 'lj_s', 'password': PASSWORD},
        ).json()['id']
        self.client.credentials()

    def _login(self, username, ua, force=False):
        data = {'username': username, 'password': PASSWORD}
        if force:
            data['force'] = 'true'
        return self.client.post('/api/v1/auth/login/', data, HTTP_USER_AGENT=ua)

    def test_new_device_flagged(self):
        self._login('lj_s', 'Chrome/Telefon')
        # bitta akkaunt = bitta qurilma — qayta login qilish uchun force kerak
        self._login('lj_s', 'Chrome/Telefon', force=True)
        self._login('lj_s', 'Firefox/Kompyuter', force=True)  # qurilma o'zgardi

        token = self._login('lj_s', 'Firefox/Kompyuter', force=True).json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        rows = self.client.get('/api/v1/auth/logins/').json()
        self.assertGreaterEqual(len(rows), 4)
        # rows[1] — Firefox'ga o'tgan login (eng oxirgisi rows[0])
        self.assertTrue(rows[1]['new_device'])
        self.assertFalse(rows[2]['new_device'])  # Chrome -> Chrome

    def test_parent_sees_child_logins_stranger_not(self):
        self._login('lj_s', 'Chrome/Telefon')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        rows = self.client.get(f'/api/v1/auth/logins/?student={self.child_id}').json()
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn('user_agent', rows[0])

        register(self.client, 'lj_p2', 'parent')
        p2 = login(self.client, 'lj_p2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {p2}')
        r = self.client.get(f'/api/v1/auth/logins/?student={self.child_id}')
        self.assertEqual(r.status_code, 403)


class MultiDeviceLoginTests(APITestCase):
    """Login cheklovsiz — bitta akkaunt bir vaqtda istalgancha qurilmadan kiradi."""

    def setUp(self):
        register(self.client, 'md_t', 'teacher')

    def _login(self, ua):
        return self.client.post(
            '/api/v1/auth/login/',
            {'username': 'md_t', 'password': PASSWORD},
            HTTP_USER_AGENT=ua,
        )

    def test_multiple_devices_login_freely(self):
        responses = [
            self._login('Chrome/Windows'),
            self._login('Firefox/Mac'),
            self._login('Safari/iPhone'),
        ]
        for resp in responses:
            self.assertEqual(resp.status_code, 200)

        # hamma qurilmalarning tokenlari bir vaqtda ishlaydi
        for resp in responses:
            me = self.client.get(
                '/api/v1/auth/me/',
                HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}",
            )
            self.assertEqual(me.status_code, 200)

    def test_logout_blacklists_given_refresh_token(self):
        first = self._login('Chrome/Windows')
        access, refresh = first.json()['access'], first.json()['refresh']

        out = self.client.post(
            '/api/v1/auth/logout/', {'refresh': refresh}, HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(out.status_code, 204)

        resp = self.client.post('/api/v1/auth/token/refresh/', {'refresh': refresh})
        self.assertEqual(resp.status_code, 401)

    def test_logout_does_not_affect_other_devices(self):
        first = self._login('Chrome/Windows')
        second = self._login('Firefox/Mac')

        self.client.post(
            '/api/v1/auth/logout/',
            {'refresh': second.json()['refresh']},
            HTTP_AUTHORIZATION=f"Bearer {second.json()['access']}",
        )

        # birinchi qurilma ishlashda davom etadi
        me = self.client.get(
            '/api/v1/auth/me/', HTTP_AUTHORIZATION=f"Bearer {first.json()['access']}",
        )
        self.assertEqual(me.status_code, 200)
        resp = self.client.post('/api/v1/auth/token/refresh/', {'refresh': first.json()['refresh']})
        self.assertEqual(resp.status_code, 200)

    def test_logout_requires_auth(self):
        resp = self.client.post('/api/v1/auth/logout/', {})
        self.assertEqual(resp.status_code, 401)


class LinkedAccountsTests(APITestCase):
    """Bitta real inson bir xil telefon raqami bilan bir nechta rol-akkaunt
    (o'qituvchi/ota-ona/o'quvchi) ocha oladi — `phone` endi UNIQUE emas."""

    PHONE = '+998901234567'

    def test_same_phone_can_register_multiple_roles(self):
        r1 = register(self.client, 'multi_teacher', 'teacher', phone=self.PHONE)
        self.assertEqual(r1.status_code, 201)
        r2 = register(self.client, 'multi_parent', 'parent', phone=self.PHONE)
        self.assertEqual(r2.status_code, 201)

    def test_me_lists_linked_accounts_by_phone(self):
        register(self.client, 'lt_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'lt_parent', 'parent', phone=self.PHONE)
        access = login(self.client, 'lt_teacher')

        resp = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(resp.status_code, 200)
        linked = resp.json()['linked_accounts']
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]['username'], 'lt_parent')
        self.assertEqual(linked[0]['role'], 'parent')

    def test_no_phone_means_no_linked_accounts(self):
        register(self.client, 'np_user', 'teacher')  # phone berilmagan
        access = login(self.client, 'np_user')
        resp = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(resp.json()['linked_accounts'], [])

    def test_different_phone_not_linked(self):
        register(self.client, 'dp_a', 'teacher', phone='+998900000001')
        register(self.client, 'dp_b', 'teacher', phone='+998900000002')
        access = login(self.client, 'dp_a')
        resp = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(resp.json()['linked_accounts'], [])

    def test_linked_accounts_not_leaked_via_general_user_serializer(self):
        """Umumiy UserSerializer (boshqa foydalanuvchini ko'rsatishda ishlatiladigan
        joylarda — kurs/dars/chat va h.k.) linked_accounts maydonini chiqarmasligi
        kerak — bu faqat MeSerializer'da (/auth/me/) bor."""
        from .serializers import UserSerializer

        register(self.client, 'leak_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'leak_parent', 'parent', phone=self.PHONE)
        other = User.objects.get(username='leak_parent')

        self.assertNotIn('linked_accounts', UserSerializer(other).data)


class SwitchAccountTests(APITestCase):
    """Bir xil telefon raqamidagi rol-akkauntlar orasida parolsiz o'tish
    (`POST /auth/switch/<id>/`) — token joriy sessiyadan olinadi, parol
    qayta so'ralmaydi."""

    PHONE = '+998901234567'

    def test_switch_to_linked_account_succeeds(self):
        from rest_framework_simplejwt.tokens import AccessToken

        register(self.client, 'sw_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'sw_parent', 'parent', phone=self.PHONE)
        access = login(self.client, 'sw_teacher')
        parent = User.objects.get(username='sw_parent')

        resp = self.client.post(
            f'/api/v1/auth/switch/{parent.pk}/', HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('access', body)
        self.assertIn('refresh', body)
        self.assertEqual(body['user']['username'], 'sw_parent')
        self.assertEqual(str(AccessToken(body['access'])['user_id']), str(parent.pk))

    def test_switch_new_access_token_authenticates_as_target(self):
        register(self.client, 'sw2_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'sw2_parent', 'parent', phone=self.PHONE)
        access = login(self.client, 'sw2_teacher')
        parent = User.objects.get(username='sw2_parent')

        switch = self.client.post(
            f'/api/v1/auth/switch/{parent.pk}/', HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        new_access = switch.json()['access']
        me = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {new_access}')
        self.assertEqual(me.json()['username'], 'sw2_parent')

    def test_switch_to_unlinked_account_rejected(self):
        register(self.client, 'sw_a', 'teacher', phone='+998900000001')
        register(self.client, 'sw_b', 'teacher', phone='+998900000002')
        access = login(self.client, 'sw_a')
        other = User.objects.get(username='sw_b')

        resp = self.client.post(
            f'/api/v1/auth/switch/{other.pk}/', HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(resp.status_code, 403)

    def test_switch_to_nonexistent_account_rejected(self):
        """Mavjud bo'lmagan id ham "bog'lanmagan" sifatida rad etiladi (403) —
        404 bilan farqlash orqali akkaunt mavjudligini oshkor qilmaslik uchun."""
        import uuid

        register(self.client, 'sw_lone', 'teacher', phone=self.PHONE)
        access = login(self.client, 'sw_lone')

        resp = self.client.post(
            f'/api/v1/auth/switch/{uuid.uuid4()}/', HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(resp.status_code, 403)

    def test_switch_requires_auth(self):
        register(self.client, 'sw_noauth', 'teacher', phone=self.PHONE)
        target = User.objects.get(username='sw_noauth')
        resp = self.client.post(f'/api/v1/auth/switch/{target.pk}/')
        self.assertEqual(resp.status_code, 401)

    def test_switch_is_recorded_in_target_login_history(self):
        register(self.client, 'sw_hist_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'sw_hist_parent', 'parent', phone=self.PHONE)
        access = login(self.client, 'sw_hist_teacher')
        parent = User.objects.get(username='sw_hist_parent')

        self.client.post(f'/api/v1/auth/switch/{parent.pk}/', HTTP_AUTHORIZATION=f'Bearer {access}')

        parent_access = login(self.client, 'sw_hist_parent')
        history = self.client.get(
            '/api/v1/auth/logins/', HTTP_AUTHORIZATION=f'Bearer {parent_access}',
        )
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.json()), 1)


class SwitchRoleTests(APITestCase):
    """Ro'yxatdan o'tishsiz rolga o'tish (`POST /auth/switch-role/`) — agar
    shu telefon raqamida o'sha rol hali mavjud bo'lmasa, avtomatik yaratiladi."""

    PHONE = '+998907654321'

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def switch_role(self, role):
        return self.client.post('/api/v1/auth/switch-role/', {'role': role}, format='json')

    def test_teacher_auto_provisions_missing_parent_role(self):
        register(self.client, 'srt_teacher', 'teacher', phone=self.PHONE)
        self.auth(login(self.client, 'srt_teacher'))
        self.assertFalse(User.objects.filter(phone=self.PHONE, role='parent').exists())

        resp = self.switch_role('parent')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['user']['role'], 'parent')
        self.assertEqual(body['user']['phone'], self.PHONE)
        self.assertTrue(User.objects.filter(phone=self.PHONE, role='parent').exists())

    def test_auto_provisioned_teacher_needs_approval(self):
        register(self.client, 'srp_parent', 'parent', phone=self.PHONE)
        self.auth(login(self.client, 'srp_parent'))

        resp = self.switch_role('teacher')
        self.assertEqual(resp.status_code, 200)
        new_teacher = User.objects.get(phone=self.PHONE, role='teacher')
        self.assertFalse(new_teacher.is_approved)

    def test_switching_to_existing_role_reuses_same_account(self):
        register(self.client, 'sre_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'sre_parent', 'parent', phone=self.PHONE)
        existing_parent_id = User.objects.get(username='sre_parent').pk
        self.auth(login(self.client, 'sre_teacher'))

        resp = self.switch_role('parent')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['user']['id'], str(existing_parent_id))
        self.assertEqual(User.objects.filter(phone=self.PHONE, role='parent').count(), 1)

    def test_student_cannot_switch_role_at_all(self):
        register(self.client, 'srs_student', 'student', phone=self.PHONE)
        self.auth(login(self.client, 'srs_student'))

        resp = self.switch_role('teacher')
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(phone=self.PHONE, role='teacher').exists())

    def test_student_cannot_switch_even_if_role_already_exists(self):
        register(self.client, 'sre2_teacher', 'teacher', phone=self.PHONE)
        register(self.client, 'sre2_student', 'student', phone=self.PHONE)
        self.auth(login(self.client, 'sre2_student'))

        resp = self.switch_role('teacher')
        self.assertEqual(resp.status_code, 403)

    def test_cannot_switch_to_own_current_role(self):
        register(self.client, 'srown_teacher', 'teacher', phone=self.PHONE)
        self.auth(login(self.client, 'srown_teacher'))

        resp = self.switch_role('teacher')
        self.assertEqual(resp.status_code, 400)

    def test_rejects_invalid_role(self):
        register(self.client, 'srbad_teacher', 'teacher', phone=self.PHONE)
        self.auth(login(self.client, 'srbad_teacher'))

        resp = self.switch_role('super_admin')
        self.assertEqual(resp.status_code, 400)

    def test_requires_phone_number(self):
        register(self.client, 'srnophone_teacher', 'teacher')  # phone berilmagan
        self.auth(login(self.client, 'srnophone_teacher'))

        resp = self.switch_role('parent')
        self.assertEqual(resp.status_code, 400)

    def test_requires_auth(self):
        resp = self.client.post('/api/v1/auth/switch-role/', {'role': 'parent'}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_generated_username_is_unique_on_collision(self):
        register(self.client, 'srcol_teacher', 'teacher', phone=self.PHONE)
        # Avtomatik generatsiya qilinadigan nomni oldindan band qilib qo'yamiz.
        register(self.client, 'srcol_teacher_parent', 'parent', phone='+998900000009')
        self.auth(login(self.client, 'srcol_teacher'))

        resp = self.switch_role('parent')
        self.assertEqual(resp.status_code, 200)
        new_username = resp.json()['user']['username']
        self.assertNotEqual(new_username, 'srcol_teacher_parent')
        self.assertTrue(User.objects.filter(username=new_username, phone=self.PHONE).exists())

    def test_new_role_can_immediately_authenticate_with_returned_token(self):
        register(self.client, 'srauth_teacher', 'teacher', phone=self.PHONE)
        self.auth(login(self.client, 'srauth_teacher'))

        resp = self.switch_role('student')
        new_access = resp.json()['access']
        me = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {new_access}')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['role'], 'student')
