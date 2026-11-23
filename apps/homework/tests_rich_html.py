"""Vazifa matni (rich HTML) tozalovchisi va matnga rasm yuklash (2026-11-23)."""
import os
import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

from . import services
from .models import AssignmentImage
from .tests import make

_MEDIA = tempfile.mkdtemp(prefix='hw-img-tests-')


def tearDownModule():
    shutil.rmtree(_MEDIA, ignore_errors=True)


def image_file(fmt='PNG', name='rasm.png', size=(40, 30)):
    buffer = BytesIO()
    Image.new('RGB', size, (69, 103, 245)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


class SanitizeRichHtmlTests(SimpleTestCase):
    def clean(self, html):
        return services.sanitize_html(html)

    def test_empty(self):
        self.assertEqual(self.clean(''), '')
        self.assertEqual(self.clean(None), '')

    def test_keeps_editor_output(self):
        html = (
            '<h1 style="text-align: center;">Sarlavha</h1>'
            '<p>Matn <strong>qalin</strong> <em>qiyshiq</em> <u>u</u> <s>s</s> H<sub>2</sub>O x<sup>2</sup></p>'
            '<p><span style="color: rgb(229, 72, 77); font-family: Georgia, serif; font-size: 20px;">rangli</span> '
            '<mark data-color="#fdefcf" style="background-color: #fdefcf;">belgilangan</mark></p>'
            '<div class="callout"><p>izoh</p></div>'
            '<pre><code class="language-python">print(1)</code></pre>'
            '<p>Formula: <span data-type="inline-math" data-latex="x^2+\\sqrt{x+1}"></span></p>'
            '<div class="tableWrapper"><table style="min-width: 75px;"><colgroup><col style="min-width: 25px;"></colgroup>'
            '<tbody><tr><th colspan="2">A</th></tr><tr><td style="background-color: #cdebdf;">1</td><td>2</td></tr></tbody></table></div>'
            '<ul><li><p>bir</p></li></ul><ol start="3"><li><p>uch</p></li></ol><blockquote><p>q</p></blockquote><hr>'
        )
        out = self.clean(html)
        for piece in (
            '<h1 style="text-align: center;">', '<strong>', '<sub>2</sub>', '<sup>2</sup>',
            'color: rgb(229, 72, 77); font-family: Georgia, serif; font-size: 20px;',
            '<mark data-color="#fdefcf"', '<div class="callout">', '<code class="language-python">',
            'data-type="inline-math"', 'data-latex="x^2+\\sqrt{x+1}"', '<div class="tableWrapper">', 'colspan="2"',
            'background-color: #cdebdf;', '<ol start="3">', '<blockquote>', '<hr>',
        ):
            self.assertIn(piece, out, piece)

    def test_removes_scripts_and_events(self):
        out = self.clean(
            '<p onclick="x()">a</p><script>alert(1)</script><img src="/media/homework_images/a.png" onerror="alert(2)">'
            '<iframe src="https://evil.example"></iframe><style>body{display:none}</style><object data="x"></object>'
            '<a href="javascript:alert(3)">l</a><svg onload="alert(4)"></svg><!-- izoh -->'
        )
        for bad in ('script', 'alert', 'onclick', 'onerror', 'iframe', '<style', 'object', 'javascript:', 'svg', 'onload', '<!--'):
            self.assertNotIn(bad, out, bad)
        self.assertIn('<img src="/media/homework_images/a.png">', out)

    def test_image_sources(self):
        own = '<img src="https://api.example.uz/media/homework_images/abc.png" alt="rasm">'
        self.assertIn('src="https://api.example.uz/media/homework_images/abc.png"', self.clean(own))
        self.assertIn('src="/media/homework_images/abc.png"', self.clean('<img src="/media/homework_images/abc.png">'))
        for bad in (
            '<img src="https://evil.example/pixel.gif">',
            '<img src="data:image/png;base64,AAAA">',
            '<img src="/media/quiz_images/x.png">',
            '<img src="/media/homework_images/../secret.png">',
            '<img src="javascript:alert(1)">',
            '<img alt="yo\'q">',
        ):
            self.assertNotIn('<img', self.clean(bad), bad)

    def test_links(self):
        out = self.clean('<a href="https://example.com" target="_blank" onclick="x()">ok</a>')
        self.assertIn('href="https://example.com"', out)
        self.assertIn('rel="noopener noreferrer nofollow"', out)
        self.assertNotIn('onclick', out)
        self.assertNotIn('href', self.clean('<a href="data:text/html,x">x</a>'))

    def test_dangerous_styles_and_classes_are_dropped(self):
        out = self.clean(
            '<p style="position: fixed; top: 0; width: 100vw; color: red; background-image: url(http://evil/x.png)">a</p>'
            '<p style="color: expression(alert(1))">b</p><p style="width: 500px; color: #fff">c</p>'
            '<div class="fixed inset-0 callout">d</div><code class="language-python x">e</code><p class="x">f</p>'
        )
        self.assertNotIn('position', out)
        self.assertNotIn('url(', out)
        self.assertNotIn('expression', out)
        self.assertNotIn('100vw', out)
        self.assertIn('style="color: red;"', out)
        self.assertIn('style="width: 500px; color: #fff;"', out)
        self.assertIn('<div class="callout">', out)
        self.assertNotIn('inset-0', out)
        self.assertNotIn('class="x"', out)
        self.assertNotIn('language-python x', out)

    def test_formula_latex_limits(self):
        self.assertNotIn('data-latex', self.clean('<span data-type="inline-math" data-latex="%s"></span>' % ('x' * 2001)))
        self.assertNotIn('data-type', self.clean('<span data-type="evil" data-latex="x"></span>'))

    def test_formula_latex_may_contain_colons_and_backslashes(self):
        out = self.clean('<span data-type="inline-math" data-latex="f: A \\to B"></span>')
        self.assertIn('data-latex="f: A \\to B"', out)

    def test_too_large_body_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.clean('<p>' + 'a' * (services.MAX_BODY_CHARS + 1) + '</p>')

    def test_plain_old_bodies_are_unchanged(self):
        html = '<p>Yeching: <b>x²+1</b></p><ul><li>bir</li></ul>'
        self.assertEqual(self.clean(html), html)


@override_settings(MEDIA_ROOT=_MEDIA)
class AssignmentImageApiTests(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject=Course.Subject.MATH)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)

    def api(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def upload(self, upload=None, user='teacher'):
        who = self.teacher if user == 'teacher' else self.student if user == 'student' else None
        return self.api(who).post('/api/v1/homework/images/', {'file': upload or image_file()}, format='multipart')

    def test_teacher_uploads_and_gets_url(self):
        resp = self.upload()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIn('/media/homework_images/', resp.json()['url'])
        self.assertTrue(resp.json()['url'].endswith('.png'))
        self.assertEqual(AssignmentImage.objects.filter(owner=self.teacher).count(), 1)

    def test_formats_are_named_by_real_format(self):
        for fmt, ext in (('JPEG', '.jpg'), ('GIF', '.gif'), ('WEBP', '.webp')):
            resp = self.upload(image_file(fmt, 'x.png'))
            self.assertEqual(resp.status_code, 201, (fmt, resp.content))
            self.assertTrue(resp.json()['url'].endswith(ext), resp.json()['url'])

    def test_rejects_non_images_big_files_and_missing_file(self):
        self.assertEqual(self.upload(SimpleUploadedFile('virus.png', b'<?php echo 1; ?>', content_type='image/png')).status_code, 400)
        self.assertEqual(self.upload(image_file('BMP', 'x.bmp')).status_code, 400)
        self.assertEqual(self.upload(SimpleUploadedFile('big.png', b'0' * (5 * 1024 * 1024 + 1), content_type='image/png')).status_code, 400)
        missing = self.api(self.teacher).post('/api/v1/homework/images/', {}, format='multipart')
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(AssignmentImage.objects.count(), 0)

    def test_student_and_anonymous_cannot_upload(self):
        self.assertEqual(self.upload(user='student').status_code, 403)
        self.assertIn(self.upload(user=None).status_code, (401, 403))

    def test_hourly_cap(self):
        with mock.patch.object(services, 'MAX_IMAGES_PER_HOUR', 2):
            self.assertEqual(self.upload().status_code, 201)
            self.assertEqual(self.upload().status_code, 201)
            self.assertEqual(self.upload().status_code, 400)

    def test_deleting_row_removes_file(self):
        image = AssignmentImage.objects.get(pk=self.upload().json()['id'])
        path = image.file.path
        self.assertTrue(os.path.exists(path))
        image.delete()
        self.assertFalse(os.path.exists(path))

    def test_uploaded_image_survives_in_assignment_body_and_bad_markup_does_not(self):
        url = self.upload().json()['url']
        body = (
            f'<p>Rasmga qarang:</p><img src="{url}" style="width: 60%;" alt="rasm">'
            '<img src="https://evil.example/x.gif"><script>alert(1)</script>'
            '<p>Formula <span data-type="inline-math" data-latex="x^2"></span></p>'
            '<table><tbody><tr><td>1</td></tr></tbody></table>'
        )
        created = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Matnli vazifa', 'body': body,
        }, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        saved = created.data['body']
        self.assertIn(f'src="{url}"', saved)
        self.assertIn('style="width: 60%;"', saved)
        self.assertIn('data-latex="x^2"', saved)
        self.assertIn('<table>', saved)
        self.assertNotIn('evil.example', saved)
        self.assertNotIn('script', saved)

        patched = self.api(self.teacher).patch(
            f"/api/v1/homework/assignments/{created.data['id']}/", {'body': '<p onclick="x()">yangi</p><iframe></iframe>'}, format='json',
        )
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertEqual(patched.data['body'], '<p>yangi</p>')

        # o'quvchi ham aynan shu tozalangan matnni ko'radi
        got = self.api(self.student).get(f"/api/v1/homework/assignments/{created.data['id']}/")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.data['body'], '<p>yangi</p>')

    def test_huge_body_is_rejected_on_create(self):
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Katta', 'body': '<p>' + 'a' * 300_001 + '</p>',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('body', resp.json()['error']['details'])
