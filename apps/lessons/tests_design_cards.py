"""Yangi dizayn (desktop) uchun: darslar ro'yxati kartalari, vaqt to'qnashuvi, "kutayotganlar", davomatda fokus foizi,
yozuv sahifasi (bo'limlar, doska rasmlari, PDF, chatga yuborish) va doska (ruxsat rejimi, sahifa nomlari)."""
from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.board.models import BoardGrant, BoardSheet
from apps.chat.models import Message
from apps.homework.models import Assignment
from apps.lessons.models import Attendance, Enrollment, FocusEvent, Lesson, LessonRecording

from .tests_schedule_extras import ScheduleBase, make
from apps.accounts.models import User

STROKE = {'id': 'a', 'color': '#000000', 'width': 3, 'points': [[10, 10], [200, 120]], 'by': 't1'}


class LessonCardTests(ScheduleBase):
    def listing(self, user=None):
        resp = self.api(user or self.teacher).get('/api/v1/lessons/')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        return {row['id']: row for row in (body['results'] if isinstance(body, dict) else body)}

    def test_finished_live_and_scheduled_cards(self):
        finished = self.lesson(status=Lesson.Status.FINISHED)
        live = self.lesson(status=Lesson.Status.LIVE, starts_at=self.tomorrow(12))
        planned = self.lesson(starts_at=self.tomorrow(14))
        Attendance.objects.create(lesson=finished, student=self.student, joined_at=timezone.now(), left_at=timezone.now())
        Attendance.objects.create(lesson=live, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=live, student=self.student2, joined_at=timezone.now(), left_at=timezone.now())
        rows = self.listing()
        done, now, later = rows[str(finished.id)], rows[str(live.id)], rows[str(planned.id)]
        self.assertEqual((done['students_count'], done['participants_count'], done['attendance_rate']), (2, 1, 50))
        self.assertEqual((done['joined_count'], now['joined_count']), (None, 1))  # jonli: hozir xonadagilar
        self.assertEqual((now['participants_count'], now['attendance_rate']), (None, None))
        self.assertEqual((later['students_count'], later['participants_count'], later['joined_count']), (2, None, None))

    def test_assignment_is_attached_but_drafts_are_hidden(self):
        lesson = self.lesson()
        Assignment.objects.create(course=self.course, lesson=lesson, title='Qoralama', status=Assignment.Status.DRAFT)
        self.assertIsNone(self.listing()[str(lesson.id)]['assignment'])
        active = Assignment.objects.create(course=self.course, lesson=lesson, title='Kvadrat tenglamalar')
        self.assertEqual(self.listing()[str(lesson.id)]['assignment'], {'id': str(active.id), 'title': 'Kvadrat tenglamalar'})

    def test_recurrence_carries_the_series_end_date(self):
        lessons = self.series(3)
        row = self.listing()[str(lessons[0].id)]
        expected = timezone.localtime(lessons[-1].starts_at).date().isoformat()
        self.assertEqual(row['recurrence']['ends_on'], expected)
        self.assertEqual(row['recurrence']['weekdays'], [0])
        single = self.lesson(starts_at=self.tomorrow(16))
        self.assertIsNone(self.listing()[str(single.id)]['recurrence'])

    def test_list_does_not_run_extra_queries_per_lesson(self):
        def count(n):
            Lesson.objects.all().delete()
            for i in range(n):
                self.lesson(starts_at=self.tomorrow(8) + timedelta(days=i), status=Lesson.Status.FINISHED)
            with CaptureQueriesContext(connection) as ctx:
                self.listing()
            return len(ctx)

        few = count(2)
        many = count(8)
        # `quiz_id` va baholar eskidan har dars uchun so'rov qiladi; yangi maydonlar (soni/davomat/vazifa) qo'shmasligi shart
        self.assertLessEqual(many - few, 6 * 3, (few, many))

    def test_student_sees_the_same_counts(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED)
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        row = self.listing(self.student)[str(lesson.id)]
        self.assertEqual((row['students_count'], row['participants_count']), (2, 1))


class ConflictTests(ScheduleBase):
    def conflicts(self, start, duration=60, user=None, **extra):
        return self.api(user or self.teacher).get('/api/v1/lessons/conflicts/', {'start': start.isoformat(), 'duration': duration, **extra})

    def test_overlap_adjacent_and_cancelled(self):
        base = self.tomorrow(10)
        lesson = self.lesson(starts_at=base, duration_min=60, title='Reading')
        self.lesson(starts_at=base + timedelta(hours=3), duration_min=60, status=Lesson.Status.CANCELLED)
        hit = self.conflicts(base + timedelta(minutes=30), 60).json()
        self.assertEqual((hit['has_conflict'], [row['id'] for row in hit['lessons']]), (True, [str(lesson.id)]))
        self.assertEqual(hit['lessons'][0]['title'], 'Reading')
        self.assertFalse(self.conflicts(base + timedelta(minutes=60), 30).json()['has_conflict'])  # keyingi daqiqada boshlanadi
        self.assertFalse(self.conflicts(base - timedelta(minutes=60), 60).json()['has_conflict'])  # oldin tugaydi
        self.assertFalse(self.conflicts(base + timedelta(hours=3), 60).json()['has_conflict'])  # bekor qilingan
        self.assertFalse(self.conflicts(base, 60, exclude=str(lesson.id)).json()['has_conflict'])  # tahrirlanayotgan dars

    def test_validation_and_permissions(self):
        base = self.tomorrow(10)
        self.assertEqual(self.api(self.teacher).get('/api/v1/lessons/conflicts/', {'start': 'abc'}).status_code, 400)
        self.assertEqual(self.conflicts(base, 0).status_code, 400)
        self.assertEqual(self.conflicts(base, 'x').status_code, 400)
        self.assertEqual(self.conflicts(base, user=self.student).status_code, 403)
        other = make('t2', User.Role.TEACHER)
        self.lesson(starts_at=base)
        self.assertFalse(self.conflicts(base, user=other).json()['has_conflict'])  # boshqa o'qituvchining darsi ko'rinmaydi


class WaitingTests(ScheduleBase):
    def test_teacher_sees_names_student_sees_counts_only(self):
        lesson = self.lesson()
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=lesson, student=self.student2, joined_at=timezone.now(), left_at=timezone.now())
        teacher_view = self.api(self.teacher).get(f'/api/v1/lessons/{lesson.id}/waiting/').json()
        self.assertEqual((teacher_view['waiting_count'], teacher_view['total_count']), (1, 2))
        self.assertEqual([s['name'] for s in teacher_view['students']], ['Aziza'])
        self.assertIn('avatar', teacher_view['students'][0])
        student_view = self.api(self.student).get(f'/api/v1/lessons/{lesson.id}/waiting/').json()
        self.assertEqual((student_view['waiting_count'], student_view['students']), (1, []))

    def test_unrelated_user_and_unknown_lesson(self):
        lesson = self.lesson()
        stranger = make('s9', User.Role.STUDENT)
        self.assertEqual(self.api(stranger).get(f'/api/v1/lessons/{lesson.id}/waiting/').status_code, 404)
        self.assertEqual(self.api(self.teacher).get('/api/v1/lessons/00000000-0000-0000-0000-000000000000/waiting/').status_code, 404)


class FocusPercentTests(ScheduleBase):
    def test_focus_percent_from_time_away(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED)
        start = timezone.now() - timedelta(hours=2)
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=start, left_at=start + timedelta(minutes=60))
        for kind, offset in (('exit', 10), ('return', 16)):
            event = FocusEvent.objects.create(lesson=lesson, student=self.student, kind=kind)
            FocusEvent.objects.filter(pk=event.pk).update(created_at=start + timedelta(minutes=offset))
        rows = self.api(self.teacher).get('/api/v1/attendance/', {'lesson': str(lesson.id)}).json()
        rows = rows['results'] if isinstance(rows, dict) else rows
        self.assertEqual((len(rows), rows[0]['focus_percent'], rows[0]['minutes']), (1, 90, 60))

    def test_no_percent_without_leave_time_and_filter_by_lesson(self):
        lesson, other = self.lesson(), self.lesson(starts_at=self.tomorrow(15))
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=other, student=self.student2, joined_at=timezone.now(), left_at=timezone.now())
        rows = self.api(self.teacher).get('/api/v1/attendance/', {'lesson': str(lesson.id)}).json()
        rows = rows['results'] if isinstance(rows, dict) else rows
        self.assertEqual([r['focus_percent'] for r in rows], [None])
        self.assertEqual({r['lesson'] for r in rows}, {str(lesson.id)})


class RecordingPageTests(ScheduleBase):
    def finished(self, **fields):
        lesson = self.lesson(status=Lesson.Status.FINISHED, live_started_at=timezone.now() - timedelta(hours=1))
        recording = LessonRecording.objects.create(lesson=lesson, status=LessonRecording.Status.COMPLETED, **fields)
        return lesson, recording

    def info(self, lesson, user=None):
        return self.api(user or self.student).get(f'/api/v1/lessons/{lesson.id}/recording/').json()

    def test_chapters_previews_and_pdf(self):
        lesson, recording = self.finished(video_started_at=timezone.now() - timedelta(hours=1))
        first = BoardSheet.objects.create(lesson=lesson, index=0, title='Mavzu: Present Perfect', strokes=[STROKE])
        second = BoardSheet.objects.create(lesson=lesson, index=1, strokes=[STROKE])
        BoardSheet.objects.create(lesson=lesson, index=2, strokes=[])  # bo'sh sahifa chiqmaydi
        BoardSheet.objects.filter(pk=first.pk).update(created_at=recording.video_started_at - timedelta(minutes=1))
        BoardSheet.objects.filter(pk=second.pk).update(created_at=recording.video_started_at + timedelta(minutes=12, seconds=40))
        body = self.info(lesson)
        self.assertEqual(body['chapters'], [{'seconds': 0, 'title': 'Mavzu: Present Perfect'}, {'seconds': 760, 'title': 'Doska 2'}])
        self.assertEqual([p['page'] for p in body['board_page_previews']], [1, 2])
        self.assertEqual(body['pdf_url'], f'/api/v1/board/{lesson.id}/pdf/')
        # imzolangan havola bilan PNG rasm — Authorization sarlavhasisiz
        url = body['board_page_previews'][0]['image_url']
        anonymous = self.client.__class__()
        resp = anonymous.get(url)
        self.assertEqual((resp.status_code, resp['Content-Type']), (200, 'image/png'))
        self.assertTrue(resp.content.startswith(b'\x89PNG'))
        self.assertEqual(anonymous.get(url.split('?')[0] + '?t=buzilgan').status_code, 403)
        self.assertEqual(anonymous.get(f'/api/v1/lessons/{lesson.id}/board/preview/2/?t={url.split("t=")[1]}').status_code, 404)  # bo'sh sahifa

    def test_empty_board_has_no_extras(self):
        lesson, _ = self.finished()
        body = self.info(lesson)
        self.assertEqual((body['chapters'], body['board_page_previews'], body['pdf_url']), ([], [], None))

    def test_share_to_group_chat(self):
        lesson, _ = self.finished(title='Present Perfect')
        resp = self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/recording/share/')
        self.assertEqual(resp.status_code, 201, resp.content)
        message = Message.objects.get(pk=resp.json()['message_id'])
        self.assertIn(f'/recordings/{lesson.id}', message.text)
        self.assertEqual(message.room_id, self.room.id)
        self.assertEqual(self.api(self.student).post(f'/api/v1/lessons/{lesson.id}/recording/share/').status_code, 403)

    def test_share_requires_a_ready_recording(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/recording/share/').status_code, 400)
        LessonRecording.objects.create(lesson=lesson, status=LessonRecording.Status.MERGING)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/recording/share/').status_code, 400)


class BoardDesignTests(ScheduleBase):
    def board(self, user=None):
        return self.api(user or self.teacher).get(f'/api/v1/board/{self.the_lesson.id}/').json()

    def setUp(self):
        super().setUp()
        self.the_lesson = self.lesson(status=Lesson.Status.LIVE)

    def test_permission_mode_follows_the_grants(self):
        self.assertEqual(self.board()['permission_mode'], 'teacher')
        BoardGrant.objects.create(lesson=self.the_lesson, student=self.student)
        self.assertEqual(self.board(self.student)['permission_mode'], 'selected')
        BoardGrant.objects.create(lesson=self.the_lesson, student=self.student2)
        self.assertEqual(self.board()['permission_mode'], 'everyone')
        self.api(self.teacher).post(f'/api/v1/board/{self.the_lesson.id}/grant/', {'mode': 'none'}, format='json')
        self.assertEqual(self.board()['permission_mode'], 'teacher')

    def test_sheet_titles(self):
        url = f'/api/v1/board/{self.the_lesson.id}/sheet/'
        resp = self.api(self.teacher).post(url, {'title': '  Formula va misollar '}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (201, {'index': 0, 'title': 'Formula va misollar'}))
        sheets = self.board(self.student)['sheets']
        self.assertEqual([(s['index'], s['title']) for s in sheets], [(0, 'Formula va misollar')])
        renamed = self.api(self.teacher).patch(f'{url}0/', {'title': 'Mavzu: Present Perfect'}, format='json')
        self.assertEqual(renamed.json(), {'index': 0, 'title': 'Mavzu: Present Perfect'})
        self.assertEqual(self.board()['sheets'][0]['title'], 'Mavzu: Present Perfect')
        self.assertEqual(self.api(self.teacher).patch(f'{url}0/', {'title': ''}, format='json').json()['title'], '')
        self.assertEqual(self.api(self.student).patch(f'{url}0/', {'title': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.api(self.teacher).patch(f'{url}0/', {'title': ['x']}, format='json').status_code, 400)
        self.assertEqual(self.api(self.teacher).post(url, {'title': 'a' * 500}, format='json').json()['title'], 'a' * 120)

    def test_alias_paths_and_pdf_after_the_lesson_ended(self):
        BoardSheet.objects.create(lesson=self.the_lesson, index=0, strokes=[STROKE])
        Lesson.objects.filter(pk=self.the_lesson.pk).update(status=Lesson.Status.FINISHED)
        alias = self.api(self.student).get(f'/api/v1/lessons/{self.the_lesson.id}/board/')
        self.assertEqual((alias.status_code, alias.json()['sheets'][0]['index']), (200, 0))
        for path in (f'/api/v1/lessons/{self.the_lesson.id}/board/pdf/', f'/api/v1/board/{self.the_lesson.id}/pdf/'):
            resp = self.api(self.student).get(path)
            self.assertEqual((resp.status_code, resp['Content-Type']), (200, 'application/pdf'), path)
            self.assertTrue(b''.join(resp.streaming_content).startswith(b'%PDF'))
        stranger = make('s9', User.Role.STUDENT)
        self.assertEqual(self.api(stranger).get(f'/api/v1/lessons/{self.the_lesson.id}/board/pdf/').status_code, 403)
