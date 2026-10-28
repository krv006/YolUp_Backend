"""Sertifikatni tekshirish: yuklash (issuer/yil), admin tasdiqlash/rad etish, bildirishnoma, ko'rinish qoidalari."""
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

from apps.notifications.models import NotificationRecipient

from .models import TeacherCertificate, User
from .tests_sms_flows import make


def pdf(name='c.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')


class CertificateReviewTests(APITestCase):
    def setUp(self):
        self.teacher = make('cert_t', role=User.Role.TEACHER)
        self.admin = make('cert_admin', role=User.Role.ADMIN)
        self.student = make('cert_s')
        self.t = APIClient()
        self.t.force_authenticate(self.teacher)
        self.a = APIClient()
        self.a.force_authenticate(self.admin)

    def upload(self, **extra):
        return self.t.post('/api/v1/auth/me/certificates/', {'file': pdf(), 'title': 'IELTS 6.5', **extra}, format='multipart')

    def test_upload_stores_issuer_year_and_starts_pending(self):
        response = self.upload(issuer='British Council', issued_year=2026)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual((data['status'], data['verified'], data['issuer'], data['issued_year']), ('pending', False, 'British Council', 2026))
        self.assertEqual(data['reject_reason'], '')

    def test_bad_year_rejected(self):
        self.assertEqual(self.upload(issued_year=1800).status_code, 400)

    def test_teacher_cannot_self_verify(self):
        response = self.upload(status='verified', verified=True)
        self.assertEqual(response.json()['status'], 'pending')

    def test_admin_notified_of_new_certificate(self):
        self.upload()
        self.assertTrue(NotificationRecipient.objects.filter(user=self.admin, notification__kind='certificate_pending').exists())

    def test_admin_lists_pending_with_owner(self):
        self.upload()
        data = self.a.get('/api/v1/admin/certificates/?status=pending').json()
        rows = data['results'] if isinstance(data, dict) else data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['owner']['username'], 'cert_t')

    def test_verify_flow_and_notification(self):
        cert_id = self.upload().json()['id']
        with self.captureOnCommitCallbacks(execute=True):
            response = self.a.post(f'/api/v1/admin/certificates/{cert_id}/verify/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['status'], response.json()['verified']), ('verified', True))
        self.assertIsNotNone(TeacherCertificate.objects.get(pk=cert_id).verified_at)
        note = NotificationRecipient.objects.get(user=self.teacher, notification__kind='certificate_verified').notification
        self.assertEqual((note.link_type, note.link_id), ('certificate', cert_id))

    def test_reject_requires_reason_and_notifies(self):
        cert_id = self.upload().json()['id']
        self.assertEqual(self.a.post(f'/api/v1/admin/certificates/{cert_id}/reject/', {}).status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.a.post(f'/api/v1/admin/certificates/{cert_id}/reject/', {'reason': 'Fayl o‘qilmaydi'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['status'], response.json()['reject_reason']), ('rejected', 'Fayl o‘qilmaydi'))
        self.assertTrue(NotificationRecipient.objects.filter(user=self.teacher, notification__kind='certificate_rejected').exists())

    def test_only_admin_can_review(self):
        cert_id = self.upload().json()['id']
        self.assertEqual(self.t.post(f'/api/v1/admin/certificates/{cert_id}/verify/').status_code, 403)
        self.assertEqual(self.t.get('/api/v1/admin/certificates/').status_code, 403)

    def test_students_see_only_verified_owner_sees_all(self):
        first = self.upload().json()['id']
        self.upload()
        self.a.post(f'/api/v1/admin/certificates/{first}/verify/')
        own = self.t.get('/api/v1/auth/me/').json()['certificates']
        self.assertEqual(len(own), 2)
        viewer = APIClient()
        viewer.force_authenticate(self.student)
        from .serializers import UserSerializer
        from rest_framework.test import APIRequestFactory

        request = APIRequestFactory().get('/')
        request.user = self.student
        shown = UserSerializer(self.teacher, context={'request': request}).data['certificates']
        self.assertEqual([c['id'] for c in shown], [first])
