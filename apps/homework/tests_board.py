"""Uy vazifasi doskasi: avtosaqlash, tekshiruv, PDF ga aylantirish va oddiy topshiriq sifatida yuborish."""
import io
import json

from django.test import SimpleTestCase
from PIL import Image

from apps.accounts.models import User
from apps.board import render
from apps.lessons.models import Course

from .models import HomeworkBoard, Submission
from .tests import make
from .tests_hardening import HomeworkBase

PEN = {'points': [[10, 10], [200, 120], [400, 90]], 'color': '#c0392b', 'width': 5}
TEXT = {'type': 'text', 'text': 'x = 4', 'x': 100, 'y': 200, 'size': 28, 'color': '#1c1e3a'}
MATH = {'type': 'math', 'latex': '\\frac{a}{b}+\\sqrt{2}', 'x': 120, 'y': 320, 'size': 30, 'color': '#1c1e3a'}
RECT = {'type': 'rect', 'x': 50, 'y': 50, 'w': 300, 'h': 100, 'color': '#1c1e3a', 'width': 4}
LINE = {'type': 'line', 'x1': 10, 'y1': 400, 'x2': 500, 'y2': 420, 'arrow': True, 'color': '#2563eb', 'width': 4}
ELLIPSE = {'type': 'ellipse', 'x': 600, 'y': 100, 'w': 200, 'h': 120, 'color': '#16a34a', 'width': 4}
MARKER = {'points': [[10, 600], [800, 610]], 'color': '#facc15', 'width': 20, 'opacity': 0.4}


class RendererTests(SimpleTestCase):
    def test_every_stroke_kind_is_drawn_on_the_page(self):
        blank = render.render_sheet([])
        full = render.render_sheet([PEN, TEXT, MATH, RECT, LINE, ELLIPSE, MARKER])
        self.assertEqual(blank.size, (1600, 900))
        self.assertIsNone(Image.eval(blank, lambda v: v).getbbox() and None)
        self.assertNotEqual(blank.tobytes(), full.tobytes())
        for stroke in (PEN, TEXT, MATH, RECT, LINE, ELLIPSE, MARKER):
            self.assertNotEqual(render.render_sheet([stroke]).tobytes(), blank.tobytes(), stroke.get('type'))

    def test_the_pdf_has_one_image_page_per_non_empty_sheet(self):
        from pypdf import PdfReader

        pdf = render.sheets_to_pdf([[PEN, TEXT], [], [RECT]])
        reader = PdfReader(io.BytesIO(pdf))
        self.assertEqual(len(reader.pages), 2)
        self.assertEqual(len(list(reader.pages[0].images)), 1)  # AI ko'rishi uchun har sahifa rasm
        self.assertIsNone(render.sheets_to_pdf([[], []]))

    def test_broken_latex_and_colours_never_crash_the_render(self):
        broken = {'type': 'math', 'latex': '\\frac{', 'x': 10, 'y': 100, 'size': 24, 'color': 'zzz'}
        self.assertIsNotNone(render.sheets_to_pdf([[broken, {'type': 'text', 'text': 'a\nb', 'x': 1, 'y': 50, 'color': ''}]]))


class HomeworkBoardApiTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.assignment_id = self.assignment(body='<p>x + 2 = 6 ni yeching</p>')

    def url(self, suffix=''):
        return f'/api/v1/homework/assignments/{self.assignment_id}/board/{suffix}'

    def put(self, sheets, user=None):
        return self.api(user or self.student).put(self.url(), {'sheets': sheets}, format='json')

    def test_a_fresh_board_is_one_empty_sheet_with_the_subject_tools_flags(self):
        resp = self.api(self.student).get(self.url())
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['sheets'], [{'index': 0, 'strokes': []}])
        self.assertEqual(body['size'], [1600, 900])
        self.assertTrue(body['math_enabled'])  # self.course — matematika
        self.assertFalse(body['chemistry_enabled'])
        self.assertFalse(HomeworkBoard.objects.exists())  # faqat ochish hech narsa yaratmaydi

    def test_the_board_is_saved_validated_and_comes_back_after_a_refresh(self):
        resp = self.put([{'strokes': [PEN, TEXT, MATH]}, {'strokes': [RECT]}])
        self.assertEqual(resp.status_code, 200, resp.content)
        back = self.api(self.student).get(self.url()).json()
        self.assertEqual([len(s['strokes']) for s in back['sheets']], [3, 1])
        self.assertTrue(all(stroke['id'] for sheet in back['sheets'] for stroke in sheet['strokes']))
        # qayta saqlash — ustiga yozadi, ikkinchi qator yaratilmaydi, kelgan id saqlanadi
        first_id = back['sheets'][0]['strokes'][0]['id']
        self.put([{'strokes': [{**PEN, 'id': first_id}]}])
        self.assertEqual(HomeworkBoard.objects.count(), 1)
        self.assertEqual(self.api(self.student).get(self.url()).json()['sheets'][0]['strokes'][0]['id'], first_id)

    def test_bad_data_is_rejected(self):
        for bad in (None, [], 'x', [{'strokes': 'x'}], [{'strokes': [{'points': [[1, 1]]}]}],
                    [{'strokes': [{'type': 'text', 'text': '  '}]}], [{'strokes': ['not a dict']}]):
            self.assertEqual(self.put(bad).status_code, 400, bad)
        self.assertEqual(self.put([{'strokes': []}] * 21).status_code, 400)
        self.assertEqual(self.put([{'strokes': [PEN] * 3001}]).status_code, 400)

    def test_coordinates_are_clamped_like_the_lesson_board(self):
        far = {'type': 'rect', 'x': 99999, 'y': 99999, 'w': 99999, 'h': 99999, 'color': '#000000', 'width': 99}
        saved = self.put([{'strokes': [far]}]).json()['sheets'][0]['strokes'][0]
        self.assertEqual((saved['x'], saved['y'], saved['width']), (1600, 900, 24))

    def test_only_enrolled_students_can_use_the_board(self):
        outsider = make('s2', User.Role.STUDENT)
        self.assertEqual(self.api(outsider).get(self.url()).status_code, 403)
        self.assertEqual(self.put([{'strokes': [PEN]}], user=outsider).status_code, 403)
        self.assertEqual(self.api(self.teacher).get(self.url()).status_code, 403)  # o'qituvchida homework.submit yo'q
        self.assertEqual(self.api(self.parent).get(self.url()).status_code, 403)

    def test_each_student_has_his_own_board(self):
        other = make('s3', User.Role.STUDENT)
        from apps.lessons.models import Enrollment

        Enrollment.objects.create(course=self.course, student=other, status=Enrollment.Status.APPROVED)
        self.put([{'strokes': [PEN]}])
        self.assertEqual(self.api(other).get(self.url()).json()['sheets'][0]['strokes'], [])

    def test_submitting_turns_the_board_into_an_ordinary_pdf_submission(self):
        self.put([{'strokes': [PEN, TEXT, MATH]}, {'strokes': [RECT]}])
        resp = self.api(self.student).post(self.url('submit/'), {}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        submission = Submission.objects.get(pk=resp.json()['id'])
        self.assertEqual((submission.student_id, str(submission.assignment_id)), (self.student.id, str(self.assignment_id)))
        self.assertEqual(submission.original_name, 'doska.pdf')
        self.assertTrue(submission.file.name.endswith('.pdf'))
        with submission.file.open('rb') as handle:
            self.assertTrue(handle.read(5).startswith(b'%PDF'))
        # o'qituvchi uni oddiy topshiriq sifatida ko'radi
        listed = self.api(self.teacher).get(f'/api/v1/homework/assignments/{self.assignment_id}/').json()
        self.assertEqual(len(listed['submissions']), 1)

    def test_an_empty_board_cannot_be_submitted(self):
        self.assertEqual(self.api(self.student).post(self.url('submit/'), {}, format='json').status_code, 400)
        self.put([{'strokes': []}])
        self.assertEqual(self.api(self.student).post(self.url('submit/'), {}, format='json').status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_the_hourly_submit_limit_still_applies_to_the_board(self):
        self.put([{'strokes': [PEN]}])
        codes = [self.api(self.student).post(self.url('submit/'), {}, format='json').status_code for _ in range(8)]
        self.assertEqual(codes[0], 201)
        self.assertIn(400, codes)

    def test_the_formula_solver_works_in_maths_courses_only(self):
        ok = self.api(self.student).post(self.url('solve/'), {'expr': '2*x + 3'}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)
        Course.objects.filter(pk=self.course.pk).update(subject=Course.Subject.PHYSICS)
        bad = self.api(self.student).post(self.url('solve/'), {'expr': '2*x + 3'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(self.api(self.student).get(self.url()).json()['math_enabled'])

    def test_the_ai_reads_the_board_pdf_as_page_images(self):
        from apps.homework import ai_grader

        self.put([{'strokes': [PEN, TEXT]}])
        submission = Submission.objects.get(pk=self.api(self.student).post(self.url('submit/'), {}, format='json').json()['id'])
        text, images = ai_grader.student_work(submission)
        self.assertEqual(text, '')
        self.assertEqual(len(images), 1)
        self.assertEqual(json.dumps(bool(images[0][1])), 'true')
