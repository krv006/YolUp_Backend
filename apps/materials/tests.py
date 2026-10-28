import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment


def upload(name='darslik.pdf', size=100):
    return SimpleUploadedFile(name, b'x' * size, content_type='application/octet-stream')


def make(name, role, **extra):
    return User.objects.create_user(username=name, password='x', role=role, **extra)


class MaterialTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = make('m_t', 'teacher', is_approved=True)
        self.other_teacher = make('m_t2', 'teacher', is_approved=True)
        self.student = make('m_s', 'student')
        self.outsider = make('m_o', 'student')
        self.parent = make('m_p', 'parent')
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject='math')
        Enrollment.objects.create(course=self.course, student=self.student, status='approved')
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status='approved')

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def post(self, user=None, **extra):
        data = {'course': str(self.course.id), 'file': upload(), **extra}
        return self.api(user or self.teacher).post('/api/v1/materials/', data, format='multipart')

    def test_teacher_uploads_and_title_defaults_to_file_name(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual((data['title'], data['kind'], data['size'], data['name']), ('darslik', 'pdf', 100, 'darslik.pdf'))
        self.assertEqual(data['url'], f"/api/v1/materials/{data['id']}/file/")

    def test_only_course_teacher_can_upload(self):
        self.assertEqual(self.post(self.other_teacher).status_code, 403)
        self.assertEqual(self.post(self.student).status_code, 403)

    def test_bad_extension_and_big_file_rejected(self):
        self.assertEqual(self.post(file=upload('virus.exe')).status_code, 400)
        from apps.materials import services

        old = services.MAX_SIZE_MB
        services.MAX_SIZE_MB = 0
        try:
            self.assertEqual(self.post(file=upload('big.pdf', 10)).status_code, 400)
        finally:
            services.MAX_SIZE_MB = old

    def test_visibility_student_parent_teacher_yes_outsider_no(self):
        self.post(title='Algebra 1')
        self.post(file=upload('a.mp3'), title='Audio')
        for user, count in ((self.teacher, 2), (self.student, 2), (self.parent, 2), (self.outsider, 0)):
            data = self.api(user).get('/api/v1/materials/').json()
            self.assertEqual(len(data['results']), count, user.username)

    def test_filters(self):
        self.post(title='Algebra 1')
        self.post(file=upload('a.mp3'), title='Audio')
        api = self.api(self.student)
        self.assertEqual(len(api.get(f'/api/v1/materials/?course={self.course.id}&kind=audio').json()['results']), 1)
        self.assertEqual(len(api.get('/api/v1/materials/?search=algebra').json()['results']), 1)

    def test_download_permissions(self):
        material_id = self.post().json()['id']
        self.assertEqual(self.api(self.student).get(f'/api/v1/materials/{material_id}/file/').status_code, 200)
        self.assertEqual(self.api(self.outsider).get(f'/api/v1/materials/{material_id}/file/').status_code, 403)

    def test_delete_only_by_teacher(self):
        material_id = self.post().json()['id']
        self.assertEqual(self.api(self.student).delete(f'/api/v1/materials/{material_id}/').status_code, 403)
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/materials/{material_id}/').status_code, 204)
        self.assertEqual(self.api(self.teacher).get('/api/v1/materials/').json()['count'], 0)
