import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson


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


class MaterialLessonFolderTests(MaterialTests):
    """2026-11-10: Guruh -> darslar -> fayllar tuzilmasi; video yozuv va doska PDF'i dars papkasida alohida elementlar."""

    def setUp(self):
        super().setUp()
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        self.lesson1 = Lesson.objects.create(course=self.course, title='1-dars', starts_at=now - timedelta(days=2), status='finished')
        self.lesson2 = Lesson.objects.create(course=self.course, title='2-dars', starts_at=now - timedelta(days=1), status='finished')
        self.empty_lesson = Lesson.objects.create(course=self.course, title='3-dars', starts_at=now + timedelta(days=1), status='scheduled')

    def test_upload_into_a_lesson_and_general_folder(self):
        inside = self.post(lesson=str(self.lesson1.id)).json()
        general = self.post(title='Umumiy fayl').json()
        self.assertEqual((inside['lesson_id'], general['lesson_id']), (str(self.lesson1.id), None))
        api = self.api(self.student)
        self.assertEqual([m['id'] for m in api.get(f'/api/v1/materials/?lesson={self.lesson1.id}').json()['results']], [inside['id']])
        self.assertEqual([m['id'] for m in api.get('/api/v1/materials/?lesson=general').json()['results']], [general['id']])

    def test_lesson_must_belong_to_the_course(self):
        other = Course.objects.create(teacher=self.teacher, title='Boshqa')
        foreign = Lesson.objects.create(course=other, title='x', starts_at=self.lesson1.starts_at)
        self.assertEqual(self.post(lesson=str(foreign.id)).status_code, 400)
        self.assertEqual(self.post(lesson='not-a-uuid').status_code, 400)

    def test_course_and_lesson_listings_with_counts(self):
        from apps.board.models import BoardSheet
        from apps.lessons.models import LessonRecording

        self.post(lesson=str(self.lesson1.id))
        self.post(lesson=str(self.lesson1.id), file=upload('b.mp3'))
        self.post()  # umumiy
        BoardSheet.objects.create(lesson=self.lesson2, index=0, strokes=[{'id': 's', 'points': [[1, 1]], 'color': '#000', 'width': 2}])
        LessonRecording.objects.create(lesson=self.lesson2, status='completed')
        courses = self.api(self.student).get('/api/v1/materials/courses/').json()
        self.assertEqual([(c['title'], c['file_count']) for c in courses], [('Algebra', 3)])
        body = self.api(self.student).get(f'/api/v1/materials/courses/{self.course.id}/lessons/').json()
        self.assertEqual(body['general'], {'file_count': 1})
        rows = {r['title']: r for r in body['lessons']}
        self.assertEqual(set(rows), {'1-dars', '2-dars'})  # bo'sh dars o'quvchiga ko'rinmaydi
        self.assertEqual((rows['1-dars']['file_count'], rows['1-dars']['has_recording'], rows['1-dars']['has_board']), (2, False, False))
        self.assertEqual((rows['2-dars']['file_count'], rows['2-dars']['has_recording'], rows['2-dars']['has_board']), (0, True, True))
        # o'qituvchi hamma darsni ko'radi (yuklash uchun), ota-ona ham o'quvchi kabi
        teacher_rows = self.api(self.teacher).get(f'/api/v1/materials/courses/{self.course.id}/lessons/').json()['lessons']
        self.assertEqual({r['title'] for r in teacher_rows}, {'1-dars', '2-dars', '3-dars'})
        self.assertEqual(len(self.api(self.parent).get(f'/api/v1/materials/courses/{self.course.id}/lessons/').json()['lessons']), 2)
        self.assertEqual(self.api(self.outsider).get(f'/api/v1/materials/courses/{self.course.id}/lessons/').status_code, 403)

    def test_unfinished_recording_is_hidden_from_students_but_visible_to_teacher(self):
        from apps.lessons.models import LessonRecording

        LessonRecording.objects.create(lesson=self.lesson1, status='merging')
        student = self.api(self.student).get(f'/api/v1/materials/lessons/{self.lesson1.id}/').json()
        teacher = self.api(self.teacher).get(f'/api/v1/materials/lessons/{self.lesson1.id}/').json()
        self.assertIsNone(student['recording'])
        self.assertEqual(teacher['recording']['status'], 'merging')

    def test_lesson_folder_lists_files_recording_and_board_links(self):
        from apps.board.models import BoardSheet
        from apps.lessons.models import LessonRecording

        material = self.post(lesson=str(self.lesson2.id)).json()
        BoardSheet.objects.create(lesson=self.lesson2, index=0, strokes=[{'id': 's', 'points': [[1, 1], [9, 9]], 'color': '#000', 'width': 2}])
        LessonRecording.objects.create(lesson=self.lesson2, status='completed')
        body = self.api(self.parent).get(f'/api/v1/materials/lessons/{self.lesson2.id}/').json()
        self.assertEqual([f['id'] for f in body['files']], [material['id']])
        self.assertEqual(body['recording'], {'status': 'completed', 'info_url': f'/api/v1/lessons/{self.lesson2.id}/recording/'})
        self.assertEqual(body['board'], {'pdf_url': f'/api/v1/materials/lessons/{self.lesson2.id}/board.pdf'})
        self.assertEqual(self.api(self.outsider).get(f'/api/v1/materials/lessons/{self.lesson2.id}/').status_code, 403)
        pdf = self.api(self.parent).get(body['board']['pdf_url'])
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
