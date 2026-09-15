"""Doska oqimi testlari — chizish ruxsati, o'chirish sababi, PDF -> chat, WebSocket."""
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.chat.models import Message
from apps.lessons.models import Course, Enrollment, Lesson

from . import services


def make(username, role):
    u = User(username=username, role=role)
    u.set_password('x')
    u.save()
    return u


STROKE = {'points': [[10, 10], [100, 100], [200, 150]], 'color': '#ff0000', 'width': 4}


class PeriodicTableTests(TestCase):
    def setUp(self):
        self.student = make('pt_s', User.Role.STUDENT)
        self.client = APIClient()

    def test_requires_auth(self):
        resp = self.client.get('/api/v1/board/periodic-table/')
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_user_gets_full_table(self):
        self.client.force_authenticate(self.student)
        resp = self.client.get('/api/v1/board/periodic-table/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 118)  # H dan Og gacha (barcha elementlar)
        hydrogen = next(el for el in data if el['symbol'] == 'H')
        self.assertEqual(hydrogen['z'], 1)
        self.assertEqual(hydrogen['shells'], [1])
        self.assertEqual(hydrogen['valence'], [1])
        self.assertIn('appearance', hydrogen)
        for el in data:
            if el['shells'] is not None:
                self.assertEqual(sum(el['shells']), el['z'])

    def test_no_lesson_or_room_permission_needed(self):
        """Bu — umumiy ma'lumot, biror darsga/xonaga bog'liq emas — shuning
        uchun `room.token` kabi ruxsat emas, oddiy autentifikatsiya yetarli."""
        self.client.force_authenticate(self.student)
        resp = self.client.get('/api/v1/board/periodic-table/')
        self.assertEqual(resp.status_code, 200)


class BoardTests(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.course = Course.objects.create(
            teacher=self.teacher, title='Algebra', subject=Course.Subject.MATH,
        )
        chat_services.ensure_course_room(self.course)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title='Dars', starts_at=timezone.now(), duration_min=45,
        )
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def url(self, tail=''):
        return f'/api/v1/board/{self.lesson.id}/{tail}'

    def test_teacher_draws_student_views(self):
        r = self.api(self.teacher).post(self.url('stroke/'), {'sheet': 0, 'stroke': STROKE}, format='json')
        self.assertEqual(r.status_code, 201)
        r = self.api(self.student).get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['sheets'][0]['strokes']), 1)
        self.assertFalse(r.data['can_draw'])

    def test_student_needs_grant_to_draw(self):
        r = self.api(self.student).post(self.url('stroke/'), {'sheet': 0, 'stroke': STROKE}, format='json')
        self.assertEqual(r.status_code, 403)
        self.api(self.teacher).post(self.url('grant/'), {'student_id': str(self.student.id)}, format='json')
        r = self.api(self.student).post(self.url('stroke/'), {'sheet': 0, 'stroke': STROKE}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_grant_broadcasts_to_websocket_immediately(self):
        """2026-09-04 bug: ruxsat berilgach sahifa yangilanmaguncha ko'rinmasdi."""
        from unittest.mock import patch

        with patch('apps.board.realtime.broadcast_board_granted') as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.api(self.teacher).post(
                    self.url('grant/'), {'student_id': str(self.student.id)}, format='json',
                )
        broadcast.assert_called_once_with(self.lesson.id, str(self.student.id))

    def test_away_students_shown_only_to_teacher(self):
        from apps.live import services as live_services

        live_services.record_focus(user=self.student, lesson_id=self.lesson.id, kind='exit')

        r = self.api(self.teacher).get(self.url())
        self.assertEqual(len(r.data['away_students']), 1)
        self.assertEqual(r.data['away_students'][0]['student_id'], str(self.student.id))

        r = self.api(self.student).get(self.url())
        self.assertNotIn('away_students', r.data)

        live_services.record_focus(user=self.student, lesson_id=self.lesson.id, kind='return')
        r = self.api(self.teacher).get(self.url())
        self.assertEqual(r.data['away_students'], [])

    def test_pending_mic_requests_shown_only_to_teacher_and_survives_reconnect(self):
        """So'rov WebSocket ulanishidan MUSTAQIL saqlanishi kerak — o'qituvchi
        so'rovdan keyin kirsa yoki sahifani yangilasa ham (qayta GET /board/
        chaqirsa) joriy so'rovlar yo'qolib qolmasin."""
        from apps.live import services as live_services

        live_services.request_mic(user=self.student, lesson_id=self.lesson.id)

        # "Sahifa yangilanishi" — yangi GET so'rovi, hech qanday WS ulanishi
        # bo'lmasa ham (bu test WS ishlatmaydi) so'rov ko'rinishi kerak
        r = self.api(self.teacher).get(self.url())
        self.assertEqual(len(r.data['pending_mic_requests']), 1)
        self.assertEqual(r.data['pending_mic_requests'][0]['student_id'], str(self.student.id))

        r = self.api(self.student).get(self.url())
        self.assertNotIn('pending_mic_requests', r.data)

        # Qayta so'rasa — dublikat yaratilmaydi
        live_services.request_mic(user=self.student, lesson_id=self.lesson.id)
        r = self.api(self.teacher).get(self.url())
        self.assertEqual(len(r.data['pending_mic_requests']), 1)

    def test_erase_requires_reason(self):
        r = self.api(self.teacher).post(self.url('stroke/'), {'sheet': 0, 'stroke': STROKE}, format='json')
        sid = r.data['id']
        r = self.api(self.teacher).post(
            self.url('erase/'), {'sheet': 0, 'stroke_ids': [sid], 'reason': ''}, format='json',
        )
        self.assertEqual(r.status_code, 400)
        r = self.api(self.teacher).post(
            self.url('erase/'), {'sheet': 0, 'stroke_ids': [sid], 'reason': "Xato chizildi"}, format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['removed'], 1)

    def test_finish_publishes_pdf_message(self):
        from unittest.mock import patch

        services.add_stroke(user=self.teacher, lesson_id=self.lesson.id, sheet_index=0, stroke=STROKE)
        with patch('apps.chat.realtime.broadcast_message') as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/finish/')
        msg = Message.objects.filter(room=self.course.chat_room).last()
        self.assertIsNotNone(msg)
        self.assertTrue(msg.file)
        # WebSocket'ga darhol tarqatilishi kerak — aks holda chat qayta
        # ochilmaguncha ko'rinmaydi (2026-09-03: shu bug tuzatildi).
        broadcast.assert_called_once_with(msg)
        # PDF autentifikatsiya bilan yuklab olinadi
        r = self.api(self.student).get(self.url('pdf/'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_solve_and_place_formula(self):
        # Photomath uslubi: yechish
        r = self.api(self.teacher).post(self.url('solve/'), {'expr': 'x^2 - 5x + 6 = 0'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('x = 2', r.data['result'])
        self.assertTrue(any('Diskriminant' in s for s in r.data['steps']))
        # yaroqsiz formula
        r = self.api(self.teacher).post(self.url('solve/'), {'expr': '???'}, format='json')
        self.assertEqual(r.status_code, 400)
        # matn elementini doskaga qo'yish
        r = self.api(self.teacher).post(self.url('stroke/'), {
            'sheet': 0,
            'stroke': {'type': 'text', 'text': 'x = 2, x = 3', 'x': 60, 'y': 50, 'size': 22},
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['type'], 'text')

    def test_multiple_sheets(self):
        r = self.api(self.teacher).post(self.url('sheet/'))
        self.assertEqual(r.data['index'], 0)
        self.api(self.teacher).post(self.url('stroke/'), {'sheet': 0, 'stroke': STROKE}, format='json')
        r = self.api(self.teacher).post(self.url('sheet/'))
        self.assertEqual(r.data['index'], 1)


class MathBoardTests(TestCase):
    """MathLive kontrakti: formula bloklari va SymPy yechuvchi FAQAT
    matematika kurslarida; PDF LaTeX'ni render qiladi."""

    MATH_STROKE = {
        'type': 'math', 'latex': r'\frac{x^2-9}{x-3}', 'x': 80, 'y': 90, 'size': 24,
    }

    def setUp(self):
        self.teacher = make('mb_t', User.Role.TEACHER)
        self.math_course = Course.objects.create(
            teacher=self.teacher, title='Algebra 7', subject=Course.Subject.MATH,
        )
        self.eng_course = Course.objects.create(
            teacher=self.teacher, title='English', subject=Course.Subject.ENGLISH,
        )
        self.chem_course = Course.objects.create(
            teacher=self.teacher, title='Kimyo 8', subject=Course.Subject.CHEMISTRY,
        )
        chat_services.ensure_course_room(self.math_course)
        chat_services.ensure_course_room(self.eng_course)
        chat_services.ensure_course_room(self.chem_course)
        self.math_lesson = Lesson.objects.create(
            course=self.math_course, title='M', starts_at=timezone.now(), duration_min=45,
        )
        self.eng_lesson = Lesson.objects.create(
            course=self.eng_course, title='E', starts_at=timezone.now(), duration_min=45,
        )
        self.chem_lesson = Lesson.objects.create(
            course=self.chem_course, title='K', starts_at=timezone.now(), duration_min=45,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def test_math_enabled_flag_math_only(self):
        r = self.client.get(f'/api/v1/board/{self.math_lesson.id}/')
        self.assertTrue(r.data['math_enabled'])
        r = self.client.get(f'/api/v1/board/{self.eng_lesson.id}/')
        self.assertFalse(r.data['math_enabled'])

    def test_chemistry_enabled_flag_chemistry_only(self):
        r = self.client.get(f'/api/v1/board/{self.chem_lesson.id}/')
        self.assertTrue(r.data['chemistry_enabled'])
        self.assertFalse(r.data['math_enabled'])
        r = self.client.get(f'/api/v1/board/{self.math_lesson.id}/')
        self.assertFalse(r.data['chemistry_enabled'])
        r = self.client.get(f'/api/v1/board/{self.eng_lesson.id}/')
        self.assertFalse(r.data['chemistry_enabled'])

    def test_math_stroke_only_on_math_course(self):
        r = self.client.post(
            f'/api/v1/board/{self.math_lesson.id}/stroke/',
            {'sheet': 0, 'stroke': self.MATH_STROKE}, format='json',
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['type'], 'math')
        self.assertEqual(r.data['latex'], r'\frac{x^2-9}{x-3}')

        r = self.client.post(
            f'/api/v1/board/{self.eng_lesson.id}/stroke/',
            {'sheet': 0, 'stroke': self.MATH_STROKE}, format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_solver_only_on_math_course(self):
        r = self.client.post(
            f'/api/v1/board/{self.math_lesson.id}/solve/', {'expr': 'x^2 - 9 = 0'}, format='json',
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.post(
            f'/api/v1/board/{self.eng_lesson.id}/solve/', {'expr': 'x^2 - 9 = 0'}, format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_pdf_renders_math_stroke(self):
        self.client.post(
            f'/api/v1/board/{self.math_lesson.id}/stroke/',
            {'sheet': 0, 'stroke': self.MATH_STROKE}, format='json',
        )
        path = services.generate_pdf(self.math_lesson)
        self.assertIsNotNone(path)
        self.assertGreater(path.stat().st_size, 1000)
        path.unlink()


class ShapeStrokeTests(TestCase):
    """To'liq asboblar paneli: chiziq/strelka, to'rtburchak, ellips, marker —
    hammasi saqlanadi va PDF'ga tushadi (front -> back -> PDF shartnomasi)."""

    def setUp(self):
        self.teacher = make('sh_t', User.Role.TEACHER)
        course = Course.objects.create(teacher=self.teacher, title='SH', subject=Course.Subject.MATH)
        chat_services.ensure_course_room(course)
        self.lesson = Lesson.objects.create(
            course=course, title='D', starts_at=timezone.now(), duration_min=45,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def post_stroke(self, stroke):
        return self.client.post(
            f'/api/v1/board/{self.lesson.id}/stroke/',
            {'sheet': 0, 'stroke': stroke}, format='json',
        )

    def test_all_shape_types_accepted_and_pdf(self):
        shapes = [
            {'type': 'line', 'x1': 10, 'y1': 10, 'x2': 300, 'y2': 200, 'arrow': True, 'width': 4},
            {'type': 'rect', 'x': 50, 'y': 60, 'w': 200, 'h': 120, 'color': '#2b6be4'},
            {'type': 'ellipse', 'x': 300, 'y': 300, 'w': 150, 'h': 90},
            {'points': [[0, 0], [50, 50], [90, 40]], 'opacity': 0.4, 'width': 12},  # marker
            {'type': 'text', 'text': 'Salom 123 !@#', 'x': 20, 'y': 400},
        ]
        for shape in shapes:
            r = self.post_stroke(shape)
            self.assertEqual(r.status_code, 201, shape)
        # marker shaffofligi saqlangan
        board = self.client.get(f'/api/v1/board/{self.lesson.id}/').data
        marker = [s for s in board['sheets'][0]['strokes'] if s.get('opacity')]
        self.assertEqual(marker[0]['opacity'], 0.4)
        # hammasi PDF bo'ladi
        path = services.generate_pdf(self.lesson)
        self.assertIsNotNone(path)
        self.assertGreater(path.stat().st_size, 800)
        path.unlink()

    def test_bad_shape_rejected(self):
        r = self.post_stroke({'type': 'line', 'x1': 'abc', 'y1': 0, 'x2': 5, 'y2': 5})
        self.assertEqual(r.status_code, 400)


class BoardWebSocketTests(TransactionTestCase):
    """Doska real-time: REST/WS orqali chizilgani hammaga bir zumda boradi."""

    def setUp(self):
        self.teacher = make('bw_t', User.Role.TEACHER)
        self.student = make('bw_s', User.Role.STUDENT)
        self.stranger = make('bw_x', User.Role.STUDENT)
        self.course = Course.objects.create(
            teacher=self.teacher, title='BW', subject=Course.Subject.MATH,
        )
        chat_services.ensure_course_room(self.course)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title='D', starts_at=timezone.now(), duration_min=45,
        )

    def ws(self, user):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        token = str(AccessToken.for_user(user))
        return WebsocketCommunicator(
            application, f'/ws/board/{self.lesson.id}/?token={token}',
        )

    async def test_rest_stroke_broadcast_to_ws(self):
        from channels.db import database_sync_to_async

        comm = self.ws(self.student)
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await database_sync_to_async(services.add_stroke)(
            user=self.teacher, lesson_id=self.lesson.id, sheet_index=0, stroke=STROKE,
        )
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'stroke')
        self.assertEqual(event['sheet'], 0)
        self.assertEqual(event['stroke']['color'], '#ff0000')
        await comm.disconnect()

    async def test_ws_stroke_write_and_broadcast(self):
        from channels.db import database_sync_to_async

        teacher_comm = self.ws(self.teacher)
        student_comm = self.ws(self.student)
        await teacher_comm.connect()
        await student_comm.connect()
        await teacher_comm.send_json_to({'type': 'stroke', 'sheet': 0, 'stroke': STROKE})
        event = await student_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'stroke')
        # bazaga ham yozildi (PDF uchun doimiy saqlanadi)
        count = await database_sync_to_async(
            lambda: len(self.lesson.board_sheets.get(index=0).strokes)
        )()
        self.assertEqual(count, 1)
        await teacher_comm.disconnect()
        await student_comm.disconnect()

    async def test_student_without_grant_gets_error_via_ws(self):
        comm = self.ws(self.student)
        await comm.connect()
        await comm.send_json_to({'type': 'stroke', 'sheet': 0, 'stroke': STROKE})
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'error')
        await comm.disconnect()

    async def test_stranger_rejected(self):
        comm = self.ws(self.stranger)
        connected, _ = await comm.connect()
        self.assertFalse(connected)
        await comm.disconnect()

    async def test_focus_exit_broadcast_to_teacher(self):
        from channels.db import database_sync_to_async

        from apps.live import services as live_services

        teacher_comm = self.ws(self.teacher)
        await teacher_comm.connect()

        await database_sync_to_async(live_services.record_focus)(
            user=self.student, lesson_id=self.lesson.id, kind='exit',
        )
        event = await teacher_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'focus')
        self.assertEqual(event['kind'], 'exit')
        self.assertEqual(event['student_id'], str(self.student.id))

        await database_sync_to_async(live_services.record_focus)(
            user=self.student, lesson_id=self.lesson.id, kind='return',
        )
        event = await teacher_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'focus')
        self.assertEqual(event['kind'], 'return')
        await teacher_comm.disconnect()
