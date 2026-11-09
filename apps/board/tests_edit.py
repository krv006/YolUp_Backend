"""Doska: kod bloki (Notepad++ uslubi) va mavjud elementni tahrirlash/ko'chirish (Zoom uslubi)."""
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.lessons.models import Course, Enrollment, Lesson

from . import code_highlight, render, services
from .models import SHEET_H, SHEET_W


def make(username, role):
    user = User(username=username, role=role)
    user.set_password('x')
    user.save()
    return user


SQL = "SELECT name, COUNT(*)\nFROM students\n    WHERE age > 18 -- adults\nGROUP BY name;"


class EditBase(TestCase):
    subject = Course.Subject.COMPUTER_SCIENCE

    def setUp(self):
        self.teacher = make('ed_t', User.Role.TEACHER)
        self.student = make('ed_s', User.Role.STUDENT)
        self.other = make('ed_o', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Dasturlash', subject=self.subject)
        chat_services.ensure_course_room(self.course)
        for student in (self.student, self.other):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now(), duration_min=45)
        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def url(self, tail=''):
        return f'/api/v1/board/{self.lesson.id}/{tail}'

    def draw(self, user, stroke):
        response = self.as_user(user).post(self.url('stroke/'), {'sheet': 0, 'stroke': stroke}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.data

    def patch(self, user, stroke_id, **body):
        return self.as_user(user).patch(self.url(f'stroke/{stroke_id}/'), {'sheet': 0, **body}, format='json')

    def grant(self, *students):
        for student in students:
            self.as_user(self.teacher).post(self.url('grant/'), {'student_id': str(student.id)}, format='json')


class CodeBlockTests(EditBase):
    def test_code_is_stored_with_indentation_and_language(self):
        element = self.draw(self.teacher, {'type': 'code', 'text': SQL, 'language': 'SQL', 'x': 80, 'y': 120, 'size': 20})
        self.assertEqual(element['type'], 'code')
        self.assertEqual(element['language'], 'sql')
        self.assertIn('\n    WHERE', element['text'])
        board = self.as_user(self.student).get(self.url()).data
        self.assertEqual(board['sheets'][0]['strokes'][0]['text'], SQL)

    def test_leading_indent_is_preserved(self):
        element = self.draw(self.teacher, {'type': 'code', 'text': '    return 1', 'language': 'python'})
        self.assertEqual(element['text'], '    return 1')

    def test_language_defaults_to_auto_and_unknown_is_rejected(self):
        self.assertEqual(self.draw(self.teacher, {'type': 'code', 'text': 'x = 1'})['language'], 'auto')
        response = self.as_user(self.teacher).post(
            self.url('stroke/'), {'sheet': 0, 'stroke': {'type': 'code', 'text': 'x', 'language': 'klingon'}}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_empty_code_is_rejected(self):
        response = self.as_user(self.teacher).post(
            self.url('stroke/'), {'sheet': 0, 'stroke': {'type': 'code', 'text': '  \n '}}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_board_exposes_languages_and_flag(self):
        board = self.as_user(self.teacher).get(self.url()).data
        self.assertTrue(board['code_enabled'])
        ids = [item['id'] for item in board['code_languages']]
        self.assertIn('sql', ids)
        self.assertIn('auto', ids)
        self.assertEqual(set(ids), code_highlight.CODE_LANGUAGE_IDS)

    def test_code_flag_off_for_other_subjects_but_element_still_allowed(self):
        math = Course.objects.create(teacher=self.teacher, title='Algebra', subject=Course.Subject.MATH)
        lesson = Lesson.objects.create(course=math, starts_at=timezone.now(), duration_min=45)
        client = self.as_user(self.teacher)
        self.assertFalse(client.get(f'/api/v1/board/{lesson.id}/').data['code_enabled'])
        response = client.post(f'/api/v1/board/{lesson.id}/stroke/', {'sheet': 0, 'stroke': {'type': 'code', 'text': 'a'}}, format='json')
        self.assertEqual(response.status_code, 201)

    def test_text_accepts_box_width(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'Salom', 'w': 300})
        self.assertEqual(element['w'], 300)

    def test_bad_size_is_400_not_500(self):
        response = self.as_user(self.teacher).post(
            self.url('stroke/'), {'sheet': 0, 'stroke': {'type': 'text', 'text': 'a', 'size': 'katta'}}, format='json')
        self.assertEqual(response.status_code, 400)


class HighlightRenderTests(EditBase):
    def test_highlight_colors_sql_keywords_and_comments(self):
        lines = code_highlight.highlight_lines(SQL, 'sql')
        self.assertEqual(len(lines), 4)
        colors = {part.strip(): color for line in lines for part, color in line if part.strip()}
        self.assertEqual(colors['SELECT'], code_highlight.COLORS['keyword'])
        self.assertEqual(colors['-- adults'], code_highlight.COLORS['comment'])

    def test_auto_detects_common_languages(self):
        samples = {
            'sql': 'select * from t', 'python': 'def f(x):\n    return x', 'javascript': 'const a = 5;\nconsole.log(a)',
            'html': '<div class="a">hi</div>', 'java': 'public class A { }', 'cpp': '#include <iostream>',
            'json': '{"a": 1}', 'plaintext': 'oddiy matn',
        }
        for expected, code in samples.items():
            self.assertEqual(code_highlight.detect_language(code), expected, code)

    def test_auto_colors_python_keywords(self):
        lines = code_highlight.highlight_lines('def f(x):\n    return x', 'auto')
        colors = {part.strip(): color for line in lines for part, color in line if part.strip()}
        self.assertEqual(colors['def'], code_highlight.COLORS['keyword'])

    def test_auto_and_plaintext_never_raise(self):
        for language in ('auto', 'plaintext', 'python', 'nope'):
            self.assertTrue(code_highlight.highlight_lines('def f(x):\n    return x', language))

    def test_pdf_and_image_render_code(self):
        self.draw(self.teacher, {'type': 'code', 'text': SQL, 'language': 'sql', 'x': 80, 'y': 120})
        self.draw(self.teacher, {'type': 'code', 'text': 'print("salom — ўзбек")', 'language': 'python', 'x': 80, 'y': 400, 'w': 500})
        path = services.generate_pdf(self.lesson)
        self.assertIsNotNone(path)
        self.assertGreater(path.stat().st_size, 1000)
        path.unlink()
        strokes = self.lesson.board_sheets.get(index=0).strokes
        image = render.render_sheet(strokes)
        self.assertEqual(image.size, (SHEET_W, SHEET_H))
        self.assertIsNotNone(render.sheets_to_pdf([strokes]))


class UpdateStrokeTests(EditBase):
    def test_teacher_edits_text_and_keeps_identity(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'Salom', 'x': 100, 'y': 100})
        response = self.patch(self.teacher, element['id'], changes={'text': 'Salom dunyo', 'color': '#ff0000', 'size': 30})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['text'], 'Salom dunyo')
        self.assertEqual(response.data['color'], '#ff0000')
        self.assertEqual(response.data['size'], 30)
        self.assertEqual(response.data['id'], element['id'])
        self.assertEqual(response.data['by_id'], str(self.teacher.id))
        stored = self.lesson.board_sheets.get(index=0).strokes
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]['text'], 'Salom dunyo')

    def test_edit_code_changes_language_and_text(self):
        element = self.draw(self.teacher, {'type': 'code', 'text': 'x = 1', 'language': 'auto'})
        response = self.patch(self.teacher, element['id'], changes={'text': 'SELECT 1;', 'language': 'sql'})
        self.assertEqual((response.data['text'], response.data['language']), ('SELECT 1;', 'sql'))

    def test_validation_still_applies_on_edit(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'Salom'})
        self.assertEqual(self.patch(self.teacher, element['id'], changes={'text': '   '}).status_code, 400)
        code = self.draw(self.teacher, {'type': 'code', 'text': 'a', 'language': 'sql'})
        self.assertEqual(self.patch(self.teacher, code['id'], changes={'language': 'klingon'}).status_code, 400)

    def test_cannot_change_type_id_or_author(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'Salom'})
        self.assertEqual(self.patch(self.teacher, element['id'], changes={'type': 'code'}).status_code, 400)
        response = self.patch(self.teacher, element['id'], changes={'text': 'Yangi', 'id': 'hack', 'by_id': 'x', 'by': 'Kimdir'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], element['id'])
        self.assertEqual(response.data['by_id'], str(self.teacher.id))

    def test_move_text_and_clamp_anchor(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'A', 'x': 100, 'y': 100})
        moved = self.patch(self.teacher, element['id'], move=[50, -30]).data
        self.assertEqual((moved['x'], moved['y']), (150, 70))
        far = self.patch(self.teacher, element['id'], move=[99999, 99999]).data
        self.assertLessEqual(far['x'], SHEET_W)
        self.assertLessEqual(far['y'], SHEET_H)

    def test_move_shapes_keeps_shape_inside_sheet(self):
        rect = self.draw(self.teacher, {'type': 'rect', 'x': 100, 'y': 100, 'w': 200, 'h': 100})
        moved = self.patch(self.teacher, rect['id'], move=[10, 20]).data
        self.assertEqual((moved['x'], moved['y'], moved['w'], moved['h']), (110, 120, 200, 100))
        clipped = self.patch(self.teacher, rect['id'], move=[99999, -99999]).data
        self.assertEqual((clipped['w'], clipped['h']), (200, 100))  # shakl buzilmaydi
        self.assertEqual(clipped['x'] + clipped['w'], SHEET_W)
        self.assertEqual(clipped['y'], 0)

    def test_move_line_and_freehand(self):
        line = self.draw(self.teacher, {'type': 'line', 'x1': 10, 'y1': 10, 'x2': 110, 'y2': 60, 'arrow': True})
        moved = self.patch(self.teacher, line['id'], move=[5, 5]).data
        self.assertEqual((moved['x1'], moved['y1'], moved['x2'], moved['y2']), (15, 15, 115, 65))
        self.assertTrue(moved['arrow'])
        free = self.draw(self.teacher, {'points': [[10, 10], [20, 30], [40, 20]], 'color': '#00ff00', 'width': 5, 'opacity': 0.4})
        moved = self.patch(self.teacher, free['id'], move=[-100, 100]).data
        self.assertEqual(moved['points'], [[0, 110], [10, 130], [30, 120]])  # dx -100 -> -10 ga kesildi (shakl sheetdan chiqmaydi)
        self.assertEqual(moved['opacity'], 0.4)

    def test_nothing_to_change_and_bad_payload(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'A'})
        self.assertEqual(self.patch(self.teacher, element['id']).status_code, 400)
        self.assertEqual(self.patch(self.teacher, element['id'], move=[1]).status_code, 400)
        self.assertEqual(self.patch(self.teacher, element['id'], move=['a', 'b']).status_code, 400)
        self.assertEqual(self.patch(self.teacher, element['id'], changes=['x']).status_code, 400)

    def test_unknown_element_is_404(self):
        self.draw(self.teacher, {'type': 'text', 'text': 'A'})
        self.assertEqual(self.patch(self.teacher, 'yoq', changes={'text': 'B'}).status_code, 404)

    def test_student_needs_grant(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'A'})
        self.assertEqual(self.patch(self.student, element['id'], changes={'text': 'B'}).status_code, 403)

    def test_granted_student_edits_only_own(self):
        self.grant(self.student, self.other)
        teachers = self.draw(self.teacher, {'type': 'text', 'text': "O'qituvchi"})
        mine = self.draw(self.student, {'type': 'text', 'text': 'Meniki'})
        theirs = self.draw(self.other, {'type': 'text', 'text': 'Boshqaniki'})
        self.assertEqual(self.patch(self.student, mine['id'], changes={'text': 'Tuzatdim'}).status_code, 200)
        self.assertEqual(self.patch(self.student, theirs['id'], changes={'text': 'Buzdim'}).status_code, 403)
        self.assertEqual(self.patch(self.student, teachers['id'], move=[5, 5]).status_code, 403)
        # o'qituvchi hammasini tahrirlay oladi
        self.assertEqual(self.patch(self.teacher, theirs['id'], changes={'text': "O'qituvchi tuzatdi"}).status_code, 200)

    def test_legacy_element_without_author_is_teacher_only(self):
        self.grant(self.student)
        sheet = self.lesson.board_sheets.create(index=0, strokes=[{'id': 'old1', 'type': 'text', 'text': 'Eski', 'x': 10, 'y': 10, 'size': 24, 'color': '#000000', 'by': 'ed_s'}])
        self.assertEqual(sheet.index, 0)
        self.assertEqual(self.patch(self.student, 'old1', changes={'text': 'X'}).status_code, 403)
        self.assertEqual(self.patch(self.teacher, 'old1', changes={'text': 'Yangi'}).status_code, 200)

    def test_edit_broadcasts_full_element_and_is_audited(self):
        from apps.core.models import AuditLog

        element = self.draw(self.teacher, {'type': 'text', 'text': 'A'})
        with patch('apps.board.realtime.broadcast_update') as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.patch(self.teacher, element['id'], changes={'text': 'B'})
        broadcast.assert_called_once()
        lesson_id, sheet_index, payload = broadcast.call_args.args
        self.assertEqual((str(lesson_id), sheet_index, payload['text']), (str(self.lesson.id), 0, 'B'))
        self.assertTrue(AuditLog.objects.filter(action='board.edit').exists())

    def test_erase_still_works_after_edit(self):
        element = self.draw(self.teacher, {'type': 'text', 'text': 'A'})
        self.patch(self.teacher, element['id'], changes={'text': 'B'})
        response = self.as_user(self.teacher).post(
            self.url('erase/'), {'sheet': 0, 'stroke_ids': [element['id']], 'reason': 'xato'}, format='json')
        self.assertEqual(response.data['removed'], 1)


class UpdateWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.teacher = make('edw_t', User.Role.TEACHER)
        self.student = make('edw_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='W', subject=Course.Subject.COMPUTER_SCIENCE)
        chat_services.ensure_course_room(self.course)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now(), duration_min=45)

    def ws(self, user):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        return WebsocketCommunicator(application, f'/ws/board/{self.lesson.id}/?token={AccessToken.for_user(user)}')

    async def test_ws_update_is_broadcast_as_stroke_updated(self):
        from channels.db import database_sync_to_async

        element = await database_sync_to_async(services.add_stroke)(
            user=self.teacher, lesson_id=self.lesson.id, sheet_index=0, stroke={'type': 'code', 'text': 'a', 'language': 'sql'})
        teacher_comm, student_comm = self.ws(self.teacher), self.ws(self.student)
        await teacher_comm.connect()
        await student_comm.connect()
        await teacher_comm.send_json_to({'type': 'update', 'sheet': 0, 'stroke_id': element['id'], 'changes': {'text': 'SELECT 1;'}})
        event = await student_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'stroke_updated')
        self.assertEqual(event['stroke']['text'], 'SELECT 1;')
        self.assertEqual(event['stroke']['id'], element['id'])
        await teacher_comm.disconnect()
        await student_comm.disconnect()

    async def test_student_without_grant_gets_error_on_update(self):
        from channels.db import database_sync_to_async

        element = await database_sync_to_async(services.add_stroke)(
            user=self.teacher, lesson_id=self.lesson.id, sheet_index=0, stroke={'type': 'text', 'text': 'a'})
        comm = self.ws(self.student)
        await comm.connect()
        await comm.send_json_to({'type': 'update', 'sheet': 0, 'stroke_id': element['id'], 'changes': {'text': 'b'}})
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'error')
        await comm.disconnect()
