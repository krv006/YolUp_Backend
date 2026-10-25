"""Dars jadvali: bekor qilish (`cancel`), takrorlanish/seriya (`recurrence`, `scope`), izoh (`note`), yozuv statistikasi,
jonli dars (`mute-all`, `presence`), doska ruxsati (`revoke`, ommaviy `grant`, `send-to-chat`), imtihon natijasini ulashish va
chat Fayllar ro'yxatidagi `cursor`."""
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from livekit.protocol.models import TrackType
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.board.models import BoardGrant, BoardSheet
from apps.chat import services as chat_services
from apps.chat.models import Message
from apps.lessons.models import Attendance, Course, Enrollment, Lesson, LessonRecording
from apps.notifications.models import NotificationRecipient

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


class ScheduleBase(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT, first_name='Aziza')
        self.student2 = make('s2', User.Role.STUDENT, first_name='Bobur')
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.room = chat_services.ensure_course_room(self.course)
        for student in (self.student, self.student2):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def tomorrow(self, hour=10):
        day = timezone.localtime() + timedelta(days=1)
        return day.replace(hour=hour, minute=0, second=0, microsecond=0)

    def lesson(self, **extra):
        return Lesson.objects.create(course=self.course, starts_at=extra.pop('starts_at', self.tomorrow()), **extra)

    def series(self, count=3, **extra):
        series_id = __import__('uuid').uuid4()
        return [
            self.lesson(starts_at=self.tomorrow() + timedelta(days=7 * i), recurrence_id=series_id,
                        recurrence={'freq': 'weekly', 'weeks': count, 'weekdays': [0]}, **extra)
            for i in range(count)
        ]


class CancelLessonTests(ScheduleBase):
    def test_cancel_one_keeps_the_lesson_and_notifies_students(self):
        lesson = self.lesson(title='Kasrlar')
        resp = self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/cancel/')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['status'], body['cancelled_count']), ('cancelled', 1))
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, Lesson.Status.CANCELLED)
        self.assertTrue(Lesson.objects.filter(pk=lesson.pk).exists())  # o'chmadi
        for student in (self.student, self.student2):
            note = NotificationRecipient.objects.get(user=student, notification__kind='lesson_cancelled').notification
            self.assertEqual((note.link_type, note.link_id), ('lesson', str(lesson.id)))
            self.assertIn('Kasrlar', note.description)
        listing = self.api(self.student).get(f'/api/v1/lessons/?course={self.course.id}').json()
        self.assertEqual([item['status'] for item in listing['results']], ['cancelled'])  # jadvalda chizilgan holda

    def test_only_scheduled_lessons_and_only_the_teacher(self):
        live = self.lesson(status=Lesson.Status.LIVE)
        done = self.lesson(status=Lesson.Status.FINISHED)
        for lesson in (live, done):
            self.assertEqual(self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/cancel/').status_code, 400)
        scheduled = self.lesson()
        self.assertEqual(self.api(self.student).post(f'/api/v1/lessons/{scheduled.id}/cancel/').status_code, 403)
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.api(other).post(f'/api/v1/lessons/{scheduled.id}/cancel/').status_code, 404)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/lessons/{scheduled.id}/cancel/?scope=bad').status_code, 400)
        self.api(self.teacher).post(f'/api/v1/lessons/{scheduled.id}/cancel/')
        again = self.api(self.teacher).post(f'/api/v1/lessons/{scheduled.id}/cancel/')
        self.assertEqual(again.status_code, 400)  # allaqachon bekor

    def test_cancel_series_only_touches_scheduled_lessons_of_that_series(self):
        first, second, third = self.series(3)
        Lesson.objects.filter(pk=first.pk).update(status=Lesson.Status.FINISHED)
        outsider = self.lesson(starts_at=self.tomorrow(15))
        resp = self.api(self.teacher).post(f'/api/v1/lessons/{second.id}/cancel/?scope=series')
        self.assertEqual(resp.json()['cancelled_count'], 2)
        statuses = {lesson.pk: Lesson.objects.get(pk=lesson.pk).status for lesson in (first, second, third, outsider)}
        self.assertEqual(statuses[first.pk], 'finished')
        self.assertEqual((statuses[second.pk], statuses[third.pk]), ('cancelled', 'cancelled'))
        self.assertEqual(statuses[outsider.pk], 'scheduled')
        self.assertEqual(NotificationRecipient.objects.filter(user=self.student, notification__kind='lesson_cancelled').count(), 1)

    def test_scope_series_without_a_series_cancels_just_that_lesson(self):
        lesson = self.lesson()
        resp = self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/cancel/?scope=series')
        self.assertEqual(resp.json()['cancelled_count'], 1)

    def test_cancelled_lessons_cannot_be_joined(self):
        lesson = self.lesson()
        self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/cancel/')
        resp = self.api(self.student).post('/api/v1/live/token/', {'lesson_id': str(lesson.id)}, format='json')
        self.assertGreaterEqual(resp.status_code, 400)


class RecurrenceTests(ScheduleBase):
    def create(self, **extra):
        start = self.tomorrow()
        data = {
            'course': str(self.course.id), 'title': 'Algebra', 'starts_at': start.isoformat(), 'duration_min': 60,
            'note': 'Daftar olib keling', **extra,
        }
        return self.api(self.teacher).post('/api/v1/lessons/', data, format='json')

    def test_note_is_stored_and_returned(self):
        resp = self.create()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['note'], 'Daftar olib keling')
        self.assertIsNone(resp.json()['recurrence'])
        patched = self.api(self.teacher).patch(f'/api/v1/lessons/{resp.json()["id"]}/', {'note': 'Yangi izoh'}, format='json')
        self.assertEqual(patched.json()['note'], 'Yangi izoh')

    def test_recurrence_creates_a_linked_weekly_series(self):
        weekday = self.tomorrow().weekday()
        resp = self.create(recurrence={'freq': 'weekly', 'weeks': 3, 'weekdays': [weekday]})
        self.assertEqual(resp.status_code, 201, resp.content)
        first = resp.json()
        series = list(Lesson.objects.filter(recurrence_id=first['recurrence_id']).order_by('starts_at'))
        ends_on = timezone.localtime(series[-1].starts_at).date().isoformat()  # seriya oxirgi darsi sanasi
        self.assertEqual(first['recurrence'], {'freq': 'weekly', 'weeks': 3, 'weekdays': [weekday], 'ends_on': ends_on})
        self.assertEqual(len(series), 3)
        self.assertEqual(str(series[0].id), first['id'])
        self.assertEqual([(b.starts_at - a.starts_at).days for a, b in zip(series, series[1:])], [7, 7])
        self.assertTrue(all(l.note == 'Daftar olib keling' and l.duration_min == 60 for l in series))

    def test_the_first_lessons_own_weekday_is_always_in_the_series(self):
        other_day = (self.tomorrow().weekday() + 3) % 7
        resp = self.create(recurrence={'freq': 'weekly', 'weeks': 2, 'weekdays': [other_day]})
        self.assertEqual(resp.status_code, 201, resp.content)
        days = {l.starts_at.astimezone().weekday() for l in Lesson.objects.filter(recurrence_id=resp.json()['recurrence_id'])}
        self.assertIn(self.tomorrow().weekday(), days)

    def test_recurrence_validation(self):
        for bad in (
            {'freq': 'daily', 'weeks': 2, 'weekdays': [1]}, {'freq': 'weekly', 'weeks': 0, 'weekdays': [1]},
            {'freq': 'weekly', 'weeks': 99, 'weekdays': [1]}, {'freq': 'weekly', 'weeks': 2, 'weekdays': []},
            {'freq': 'weekly', 'weeks': 2, 'weekdays': [7]}, 'weekly',
        ):
            self.assertEqual(self.create(recurrence=bad).status_code, 400, bad)

    def test_schedule_endpoint_links_the_series_too(self):
        start = (timezone.localdate() + timedelta(days=1))
        resp = self.api(self.teacher).post(f'/api/v1/courses/{self.course.id}/schedule/', {
            'title': 'Seriya', 'days': [start.weekday()], 'start_time': '10:00', 'end_time': '11:00', 'weeks': 2,
            'start_date': start.isoformat(), 'note': 'Izoh',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        lessons = resp.json()['lessons']
        self.assertEqual(len({l['recurrence_id'] for l in lessons}), 1)
        self.assertTrue(lessons[0]['recurrence_id'])
        self.assertEqual({l['note'] for l in lessons}, {'Izoh'})

    def test_patch_scope_series_changes_the_following_lessons(self):
        first, second, third = self.series(3)
        resp = self.api(self.teacher).patch(
            f'/api/v1/lessons/{first.id}/?scope=series',
            {'title': 'Yangi mavzu', 'duration_min': 90, 'starts_at': (first.starts_at + timedelta(hours=2)).isoformat()},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        for lesson in (second, third):
            lesson.refresh_from_db()
            self.assertEqual((lesson.title, lesson.duration_min), ('Yangi mavzu', 90))
        second.refresh_from_db()
        self.assertEqual(second.starts_at, self.tomorrow() + timedelta(days=7, hours=2))  # hammasi 2 soatga siljidi

    def test_patch_scope_one_changes_only_that_lesson_and_bad_scope_is_refused(self):
        first, second, _third = self.series(3)
        self.api(self.teacher).patch(f'/api/v1/lessons/{first.id}/', {'title': 'Faqat bu'}, format='json')
        second.refresh_from_db()
        self.assertEqual(second.title, '')
        bad = self.api(self.teacher).patch(f'/api/v1/lessons/{first.id}/?scope=all', {'title': 'x'}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_series_patch_skips_past_and_finished_lessons(self):
        first, second, third = self.series(3)
        Lesson.objects.filter(pk=third.pk).update(status=Lesson.Status.FINISHED)
        self.api(self.teacher).patch(f'/api/v1/lessons/{first.id}/?scope=series', {'title': 'Y'}, format='json')
        second.refresh_from_db()
        third.refresh_from_db()
        self.assertEqual((second.title, third.title), ('Y', ''))

    def test_recurrence_of_an_existing_lesson_cannot_be_edited(self):
        first, *_ = self.series(2)
        resp = self.api(self.teacher).patch(
            f'/api/v1/lessons/{first.id}/', {'recurrence': {'freq': 'weekly', 'weeks': 9, 'weekdays': [1]}}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        first.refresh_from_db()
        self.assertEqual(first.recurrence['weeks'], 2)


class RecordingStatsTests(ScheduleBase):
    def test_recording_info_has_participants_attendance_and_board_pages(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED)
        LessonRecording.objects.create(lesson=lesson, status=LessonRecording.Status.COMPLETED)
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=lesson, student=self.student2)  # kirmagan (joined_at yo'q)
        BoardSheet.objects.create(lesson=lesson, index=0, strokes=[{'id': 'a'}])
        BoardSheet.objects.create(lesson=lesson, index=1, strokes=[])  # bo'sh varaq sanalmaydi
        body = self.api(self.student).get(f'/api/v1/lessons/{lesson.id}/recording/').json()
        self.assertEqual((body['participants_count'], body['attendance_rate'], body['board_pages']), (1, 50, 1))

    def test_stats_are_safe_without_students(self):
        empty_course = Course.objects.create(teacher=self.teacher, title='Bo\'sh')
        lesson = Lesson.objects.create(course=empty_course, starts_at=timezone.now(), status=Lesson.Status.FINISHED)
        LessonRecording.objects.create(lesson=lesson, status=LessonRecording.Status.FAILED)
        body = self.api(self.teacher).get(f'/api/v1/lessons/{lesson.id}/recording/').json()
        self.assertEqual((body['participants_count'], body['attendance_rate'], body['board_pages']), (0, 0, 0))


class FakeRoom:
    def __init__(self, participants):
        self.participants, self.muted = participants, []

    async def list_participants(self, _request):
        return SimpleNamespace(participants=self.participants)

    async def mute_published_track(self, request):
        self.muted.append((request.identity, request.track_sid))


def fake_livekit(room):
    class Client:
        def __init__(self, *args, **kwargs):
            self.room = room

        async def aclose(self):
            return None

    return Client


def participant(identity, *audio):
    tracks = [SimpleNamespace(type=TrackType.AUDIO, muted=muted, sid=sid) for sid, muted in audio]
    tracks.append(SimpleNamespace(type=TrackType.VIDEO, muted=False, sid='video'))
    return SimpleNamespace(identity=identity, tracks=tracks)


class MuteAllTests(ScheduleBase):
    def test_everyone_but_the_teacher_and_the_excluded_is_muted(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        room = FakeRoom([
            participant(f'user-{self.teacher.id}', ('T1', False)),
            participant(f'user-{self.student.id}', ('A1', False)),
            participant(f'user-{self.student2.id}', ('B1', False)),
            participant('user-already', ('C1', True)),
        ])
        with mock.patch('apps.live.services.LiveKitAPI', fake_livekit(room)):
            resp = self.api(self.teacher).post(
                '/api/v1/live/mute-all/', {'lesson_id': str(lesson.id), 'except': [str(self.student2.id)]}, format='json',
            )
        self.assertEqual((resp.status_code, resp.json()), (200, {'muted': 1}))
        self.assertEqual(room.muted, [(f'user-{self.student.id}', 'A1')])  # faqat audio, faqat ovozi yoniq

    def test_permissions_and_server_problems(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        body = {'lesson_id': str(lesson.id)}
        self.assertEqual(self.api(self.student).post('/api/v1/live/mute-all/', body, format='json').status_code, 403)
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.api(other).post('/api/v1/live/mute-all/', body, format='json').status_code, 403)
        failing = mock.Mock(side_effect=RuntimeError('livekit down'))
        with mock.patch('apps.live.services.LiveKitAPI', failing):
            self.assertEqual(self.api(self.teacher).post('/api/v1/live/mute-all/', body, format='json').status_code, 400)
            idle = self.lesson(status=Lesson.Status.SCHEDULED)  # dars jonli emas: xato emas, 0
            resp = self.api(self.teacher).post('/api/v1/live/mute-all/', {'lesson_id': str(idle.id)}, format='json')
            self.assertEqual(resp.json(), {'muted': 0})


class LessonPresenceTests(ScheduleBase):
    def test_count_and_avatars(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        self.student.avatar.save('a.png', SimpleUploadedFile('a.png', b'x'), save=True)
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=lesson, student=self.student2, joined_at=timezone.now(), left_at=timezone.now())
        body = self.api(self.student2).get(f'/api/v1/live/lesson/{lesson.id}/presence/').json()
        self.assertEqual(body['count'], 2)  # o'qituvchi (jonli) + hali chiqmagan 1 o'quvchi
        self.assertEqual(len(body['avatars']), 1)
        idle = self.lesson(starts_at=self.tomorrow(15))
        self.assertEqual(self.api(self.student).get(f'/api/v1/live/lesson/{idle.id}/presence/').json(), {'count': 0, 'avatars': []})

    def test_outsiders_cannot_peek(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        outsider = make('s9', User.Role.STUDENT)
        self.assertEqual(self.api(outsider).get(f'/api/v1/live/lesson/{lesson.id}/presence/').status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/v1/live/lesson/{lesson.id}/presence/').status_code, 401)


class BoardExtrasTests(ScheduleBase):
    def grant(self, user, lesson, **data):
        return self.api(user).post(f'/api/v1/board/{lesson.id}/grant/', data, format='json')

    def test_revoke_one_student(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        self.grant(self.teacher, lesson, student_id=str(self.student.id))
        with mock.patch('apps.board.realtime.broadcast_board_revoked') as event, self.captureOnCommitCallbacks(execute=True):
            resp = self.api(self.teacher).post(f'/api/v1/board/{lesson.id}/revoke/', {'student_id': str(self.student.id)}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (200, {'ok': True, 'revoked': True}))
        self.assertFalse(BoardGrant.objects.filter(lesson=lesson, student=self.student).exists())
        event.assert_called_once()
        again = self.api(self.teacher).post(f'/api/v1/board/{lesson.id}/revoke/', {'student_id': str(self.student.id)}, format='json')
        self.assertEqual(again.json()['revoked'], False)  # xato emas
        self.assertEqual(self.api(self.student).post(f'/api/v1/board/{lesson.id}/revoke/', {'student_id': str(self.student.id)}, format='json').status_code, 403)

    def test_bulk_grant_modes(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        listed = self.grant(self.teacher, lesson, student_ids=[str(self.student.id)])
        self.assertEqual((listed.json()['granted'], listed.json()['revoked']), (1, 0))
        everyone = self.grant(self.teacher, lesson, mode='all')
        self.assertEqual(everyone.json()['granted'], 1)  # birinchisi allaqachon bor edi
        self.assertEqual(BoardGrant.objects.filter(lesson=lesson).count(), 2)
        none = self.grant(self.teacher, lesson, mode='none')
        self.assertEqual((none.json()['granted'], none.json()['revoked']), (0, 2))
        self.assertEqual(BoardGrant.objects.filter(lesson=lesson).count(), 0)

    def test_bulk_grant_limits_and_the_old_single_form(self):
        lesson = self.lesson(status=Lesson.Status.LIVE)
        stranger = make('s9', User.Role.STUDENT)
        self.assertEqual(self.grant(self.teacher, lesson, student_ids=[str(stranger.id)]).status_code, 404)
        self.assertEqual(BoardGrant.objects.count(), 0)
        self.assertEqual(self.grant(self.teacher, lesson, student_ids=[]).status_code, 400)
        self.assertEqual(self.grant(self.teacher, lesson, mode='some').status_code, 400)
        self.assertEqual(self.grant(self.student, lesson, mode='all').status_code, 403)
        single = self.grant(self.teacher, lesson, student_id=str(self.student.id))
        self.assertEqual((single.status_code, single.json()), (200, {'ok': True}))

    def test_send_to_chat_posts_the_pdf_as_a_file(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED, title='Kasrlar')
        BoardSheet.objects.create(lesson=lesson, index=0, strokes=[{'id': 's1', 'color': '#000', 'width': 3, 'points': [[1, 1], [50, 50]]}])
        resp = self.api(self.teacher).post(f'/api/v1/board/{lesson.id}/send-to-chat/')
        self.assertEqual(resp.status_code, 201, resp.content)
        message = Message.objects.get(pk=resp.json()['message_id'])
        self.assertEqual((message.room_id, message.sender_id, message.message_type), (self.room.id, self.teacher.id, 'file'))
        self.assertEqual((message.file_type, message.system_key), ('application/pdf', 'board_ready'))
        self.assertEqual(message.files.count(), 1)  # chatdagi "Fayllar" ro'yxatida ko'rinadi
        listing = self.api(self.student).get(f'/api/v1/chat/rooms/{self.room.id}/attachments/?kind=file').json()
        self.assertEqual([row['name'] for row in listing['results']], [message.file_name])

    def test_send_to_chat_needs_a_non_empty_board_and_the_teacher(self):
        lesson = self.lesson(status=Lesson.Status.FINISHED)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/board/{lesson.id}/send-to-chat/').status_code, 400)
        BoardSheet.objects.create(lesson=lesson, index=0, strokes=[{'id': 's1', 'color': '#000', 'width': 3, 'points': [[1, 1], [9, 9]]}])
        self.assertEqual(self.api(self.student).post(f'/api/v1/board/{lesson.id}/send-to-chat/').status_code, 403)


class ShareExamResultsTests(ScheduleBase):
    def setUp(self):
        super().setUp()
        from apps.exams.models import Exam, ExamSection

        self.exam = Exam.objects.create(
            course=self.course, created_by=self.teacher, title='IELTS mock', template_key='custom',
            scoring={'scale': 100}, starts_at=timezone.now() - timedelta(hours=3), ends_at=timezone.now() - timedelta(hours=1),
        )
        ExamSection.objects.create(exam=self.exam, order=0, kind='section', key='a', title='A', minutes=60)

    def share(self, user, **data):
        return self.api(user).post(f'/api/v1/exams/{self.exam.id}/share-results/', data or {'to': 'group_chat'}, format='json')

    def test_results_table_goes_to_the_group_chat(self):
        resp = self.share(self.teacher)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()['ok'], resp.json()['students']), (True, 2))
        message = Message.objects.get(pk=resp.json()['message_id'])
        self.assertEqual((message.room_id, message.sender_id), (self.room.id, self.teacher.id))
        self.assertTrue(message.text.startswith('📊 «IELTS mock» natijalari'))
        self.assertIn('Aziza — qatnashmadi', message.text)
        self.assertIn('Bobur — qatnashmadi', message.text)

    def test_only_after_the_exam_and_only_for_the_teacher(self):
        self.assertEqual(self.share(self.student).status_code, 403)
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.share(other).status_code, 404)
        self.assertEqual(self.share(self.teacher, to='telegram').status_code, 400)
        self.exam.ends_at = timezone.now() + timedelta(hours=1)
        self.exam.save()
        self.assertEqual(self.share(self.teacher).status_code, 400)  # hali tugamagan


class AttachmentsCursorTests(ScheduleBase):
    def test_cursor_pagination_and_the_mime_alias(self):
        for index in range(5):
            self.api(self.student).post(
                f'/api/v1/chat/rooms/{self.room.id}/send/',
                {'files': [SimpleUploadedFile(f'f{index}.txt', b'x')]}, format='multipart',
            )
        base = f'/api/v1/chat/rooms/{self.room.id}/attachments/?kind=file'
        first = self.api(self.teacher).get(base + '&limit=2').json()
        self.assertEqual((first['count'], [r['name'] for r in first['results']]), (5, ['f4.txt', 'f3.txt']))
        self.assertEqual(first['results'][0]['mime'], 'text/plain')
        second = self.api(self.teacher).get(base + f'&limit=2&cursor={first["next_cursor"]}').json()
        self.assertEqual([r['name'] for r in second['results']], ['f2.txt', 'f1.txt'])
        last = self.api(self.teacher).get(base + f'&limit=2&cursor={second["next_cursor"]}').json()
        self.assertEqual(([r['name'] for r in last['results']], last['next_cursor']), (['f0.txt'], None))
        self.assertEqual(self.api(self.teacher).get(base + '&cursor=nope').status_code, 400)
        self.assertIn('results', self.api(self.teacher).get(base).json())  # sahifalash (page) avvalgidek
