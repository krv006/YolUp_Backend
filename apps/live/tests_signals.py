"""O'qituvchi signallari: doskani yuklamasdan kichik javob (oynadan chiqqanlar, mikrofon/kamera so'rovlari)."""
from apps.accounts.models import User
from apps.lessons.models import CameraRequest, FocusEvent, Lesson, MicRequest
from apps.lessons.tests_schedule_extras import ScheduleBase, make


class LessonSignalsTests(ScheduleBase):
    def setUp(self):
        super().setUp()
        self.live = self.lesson(status=Lesson.Status.LIVE)

    def signals(self, user, lesson=None):
        return self.api(user).get(f'/api/v1/live/lesson/{(lesson or self.live).id}/signals/')

    def test_empty_and_filled(self):
        self.assertEqual(self.signals(self.teacher).json(), {
            'away_students': [], 'pending_mic_requests': [], 'pending_camera_requests': [],
        })
        FocusEvent.objects.create(lesson=self.live, student=self.student, kind='exit')
        MicRequest.objects.create(lesson=self.live, student=self.student2)
        CameraRequest.objects.create(lesson=self.live, student=self.student2)
        body = self.signals(self.teacher).json()
        self.assertEqual([r['name'] for r in body['away_students']], ['Aziza'])
        self.assertEqual([r['student_id'] for r in body['pending_mic_requests']], [str(self.student2.id)])
        self.assertEqual([r['student_id'] for r in body['pending_camera_requests']], [str(self.student2.id)])

    def test_returned_student_is_not_away(self):
        FocusEvent.objects.create(lesson=self.live, student=self.student, kind='exit')
        FocusEvent.objects.create(lesson=self.live, student=self.student, kind='return')
        self.assertEqual(self.signals(self.teacher).json()['away_students'], [])

    def test_only_the_lessons_teacher(self):
        self.assertEqual(self.signals(self.student).status_code, 403)
        self.assertEqual(self.signals(make('t2', User.Role.TEACHER)).status_code, 403)
        self.assertEqual(self.api(self.teacher).get('/api/v1/live/lesson/00000000-0000-0000-0000-000000000000/signals/').status_code, 404)

    def test_payload_is_tiny_compared_to_the_board(self):
        from apps.board.models import BoardSheet

        stroke = {'id': 'x', 'color': '#000000', 'width': 3, 'points': [[i, i] for i in range(40)], 'by': 't'}
        BoardSheet.objects.create(lesson=self.live, index=0, strokes=[stroke] * 300)
        board = len(self.api(self.teacher).get(f'/api/v1/board/{self.live.id}/').content)
        small = len(self.signals(self.teacher).content)
        self.assertGreater(board, 50_000)
        self.assertLess(small, 200)
