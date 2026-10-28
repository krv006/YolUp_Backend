"""Yangi dizayn: o'qituvchi bosh sahifasi (ko'rsatkichlar, so'nggi faollik), o'qituvchi tahlili, bildirishnoma sarlavhasi,
odamlarni qidirish, guruh rasmi va ovozli xona egasi."""
from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.accounts.models import ParentChildLink, User
from apps.chat.models import ChatRoom
from apps.homework.models import Assignment, Submission
from apps.lessons.models import Attendance, Enrollment, Lesson
from apps.lessons.tests_schedule_extras import ScheduleBase, make
from apps.notifications.models import Notification
from apps.notifications.services import send_notification
from apps.quizzes.models import Quiz, QuizAttempt
from apps.voice.models import VoiceRoom


class TeacherDashboardTests(ScheduleBase):
    def today(self, hour, **extra):
        local = timezone.localtime().replace(hour=hour, minute=0, second=0, microsecond=0)
        return Lesson.objects.create(course=self.course, starts_at=local, **extra)

    def overview(self, user=None):
        resp = self.api(user or self.teacher).get('/api/v1/dashboard/teacher/')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def pending(self, assignment, student):
        return Submission.objects.create(
            assignment=assignment, student=student, file='x.pdf', original_name='x.pdf',
            status=Submission.Status.PENDING_REVIEW,
        )

    def test_empty_teacher(self):
        lonely = make('t9', User.Role.TEACHER)
        self.assertEqual(self.overview(lonely), {
            'lessons_today': 0, 'lessons_today_finished': 0, 'submissions_pending': 0, 'assignments_pending': 0,
            'students_total': 0, 'courses_total': 0, 'attendance_rate_week': None,
        })

    def test_counts(self):
        self.today(9, status=Lesson.Status.FINISHED)
        self.today(11, status=Lesson.Status.LIVE)
        self.today(13, status=Lesson.Status.CANCELLED)  # bekor qilingan sanalmaydi
        tomorrow = self.lesson()  # ertangi dars bugunga kirmaydi
        self.assertIsNotNone(tomorrow)
        first = Assignment.objects.create(course=self.course, title='A')
        second = Assignment.objects.create(course=self.course, title='B')
        Assignment.objects.create(course=self.course, title='C')  # topshiriq yo'q
        self.pending(first, self.student)
        self.pending(first, self.student2)
        self.pending(second, self.student)
        other_course = Course = type(self.course).objects.create(teacher=self.teacher, title='Geometriya')
        Enrollment.objects.create(course=other_course, student=self.student, status=Enrollment.Status.APPROVED)  # takror o'quvchi
        body = self.overview()
        self.assertEqual((body['lessons_today'], body['lessons_today_finished']), (2, 1))
        self.assertEqual((body['submissions_pending'], body['assignments_pending']), (3, 2))
        self.assertEqual((body['students_total'], body['courses_total']), (2, 2))

    def test_weekly_attendance_uses_only_the_last_seven_days(self):
        recent = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() - timedelta(days=2), status=Lesson.Status.FINISHED)
        old = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() - timedelta(days=20), status=Lesson.Status.FINISHED)
        Attendance.objects.create(lesson=recent, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=old, student=self.student, joined_at=timezone.now())
        Attendance.objects.create(lesson=old, student=self.student2, joined_at=timezone.now())
        self.assertEqual(self.overview()['attendance_rate_week'], 50)  # 1 / 2 — eski dars hisobga olinmaydi

    def test_only_teachers(self):
        self.assertEqual(self.api(self.student).get('/api/v1/dashboard/teacher/').status_code, 403)


class ActivityTests(ScheduleBase):
    def notify(self, **extra):
        data = {'sender': self.student, 'description': "<p>Aziza <b>A2</b> guruhiga qo'shilmoqchi</p>",
                'target_type': Notification.Target.USER, 'user_id': self.teacher.id, 'kind': 'member_joined',
                'link_type': 'course', 'link_id': str(self.course.id), **extra}
        return send_notification(**data)

    def test_feed_shape_and_order(self):
        self.notify()
        self.notify(description='Yangi vazifa berildi', kind='new_assignment', link_type='assignment', link_id='1')
        rows = self.api(self.teacher).get('/api/v1/dashboard/activity/').json()
        self.assertEqual([r['category'] for r in rows], ['assignment', 'member_joined'])  # yangisi birinchi
        joined = rows[1]
        self.assertEqual((joined['title'], joined['body']), ("Qo'shilish so'rovi", "Aziza A2 guruhiga qo'shilmoqchi"))
        self.assertEqual((joined['link_type'], joined['link_id'], joined['is_read']), ('course', str(self.course.id), False))
        self.assertTrue(joined['id'] and joined['created_at'])

    def test_limit_and_privacy(self):
        for _ in range(4):
            self.notify()
        self.assertEqual(len(self.api(self.teacher).get('/api/v1/dashboard/activity/?limit=2').json()), 2)
        self.assertEqual(len(self.api(self.teacher).get('/api/v1/dashboard/activity/?limit=abc').json()), 4)
        self.assertEqual(self.api(self.student).get('/api/v1/dashboard/activity/').json(), [])  # boshqaning xabari ko'rinmaydi

    def test_inbox_items_have_title_and_plain_body(self):
        self.notify()
        body = self.api(self.teacher).get('/api/v1/notifications/').json()
        item = (body['results'] if isinstance(body, dict) else body)[0]['notification']
        self.assertEqual((item['title'], item['body']), ("Qo'shilish so'rovi", "Aziza A2 guruhiga qo'shilmoqchi"))
        self.assertIn('<b>', item['description'])  # eski maydon o'zgarmagan


class TeacherAnalyticsTests(ScheduleBase):
    def test_trends_cover_only_my_courses(self):
        quiz = Quiz.objects.create(course=self.course, title='T')
        QuizAttempt.objects.create(quiz=quiz, student=self.student, score=8, max_score=10)
        stranger_course = type(self.course).objects.create(teacher=make('t2', User.Role.TEACHER), title='Boshqa')
        other = Quiz.objects.create(course=stranger_course, title='O')
        QuizAttempt.objects.create(quiz=other, student=self.student, score=1, max_score=10)
        Lesson.objects.create(course=self.course, starts_at=timezone.now() - timedelta(hours=1), status=Lesson.Status.FINISHED)
        body = self.api(self.teacher).get('/api/v1/analytics/me/trends/?period=week').json()
        self.assertEqual(body['period'], 'week')
        self.assertEqual(len(body['labels']), 8)
        self.assertEqual(body['quiz_avg_score'][-1], 80.0)  # faqat o'zimning testim: 8/10
        self.assertEqual(body['lessons_completed'][-1], 1)
        self.assertEqual(body['quiz_avg_score'][:-1], [None] * 7)

    def test_validation_and_roles(self):
        self.assertEqual(self.api(self.teacher).get('/api/v1/analytics/me/trends/?period=hour').status_code, 400)
        self.assertEqual(self.api(self.teacher).get('/api/v1/analytics/me/trends/').json()['period'], 'week')  # standart
        self.assertEqual(self.api(self.student).get('/api/v1/analytics/me/trends/').status_code, 200)  # o'quvchi ham o'z trendini ko'radi (yangi dizayn)

    def test_overall_attendance_rate_in_my_analytics(self):
        lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now() - timedelta(days=1), status=Lesson.Status.FINISHED)
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=timezone.now())
        body = self.api(self.teacher).get('/api/v1/analytics/me/').json()
        self.assertEqual(body['attendance_rate'], 50.0)
        self.assertEqual(body['overall']['attendance_rate'], 50.0)


class PeopleSearchTests(ScheduleBase):
    def search(self, q, user=None):
        resp = self.api(user or self.teacher).get('/api/v1/auth/users/search/', {'q': q})
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_teacher_finds_own_students_and_parents_only(self):
        parent = make('p1', User.Role.PARENT, first_name='Aziza')
        ParentChildLink.objects.create(parent=parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        stranger = make('s9', User.Role.STUDENT, first_name='Aziza')  # boshqa guruh o'quvchisi
        rows = self.search('Aziza')
        self.assertEqual({r['username'] for r in rows}, {'s1', 'p1'})
        self.assertNotIn(str(stranger.id), {r['id'] for r in rows})
        student = next(r for r in rows if r['username'] == 's1')
        self.assertEqual((student['role'], student['name'], student['room_id']), ('student', 'Aziza', None))
        self.assertIn('avatar', student)

    def test_existing_direct_room_is_returned_and_blocked_one_is_not(self):
        room = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.student, direct_status=ChatRoom.DirectStatus.ACTIVE)
        row = next(r for r in self.search('s1') if r['username'] == 's1')
        self.assertEqual(row['room_id'], str(room.id))
        ChatRoom.objects.filter(pk=room.pk).update(direct_status=ChatRoom.DirectStatus.BLOCKED)
        self.assertIsNone(next(r for r in self.search('s1') if r['username'] == 's1')['room_id'])

    def test_short_query_and_other_roles(self):
        self.assertEqual(self.search('a'), [])
        self.assertEqual(self.api(self.student).get('/api/v1/auth/users/search/', {'q': 'ab'}).status_code, 403)
        admin = make('adm', User.Role.ADMIN)
        rows = self.api(admin).get('/api/v1/auth/users/search/', {'q': 's1'}).json()
        self.assertEqual([r['username'] for r in rows], ['s1'])  # admin eski xatti-harakat (to'liq foydalanuvchi)

    def test_pending_students_are_searchable_too(self):
        pending = make('s8', User.Role.STUDENT, first_name='Kutuvchi')
        Enrollment.objects.create(course=self.course, student=pending, status=Enrollment.Status.PENDING)
        self.assertEqual([r['username'] for r in self.search('Kutuvchi')], ['s8'])


def png(color='red', size=(40, 40)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, format='PNG')
    return SimpleUploadedFile('guruh.png', buffer.getvalue(), content_type='image/png')


class CourseAvatarTests(ScheduleBase):
    def url(self):
        return f'/api/v1/courses/{self.course.id}/'

    def test_upload_show_replace_and_clear(self):
        resp = self.api(self.teacher).patch(self.url(), {'avatar': png()}, format='multipart')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['avatar'].startswith('http') and 'course_avatars/' in resp.json()['avatar'])
        listed = self.api(self.student).get('/api/v1/courses/').json()
        rows = listed['results'] if isinstance(listed, dict) else listed
        self.assertIn('course_avatars/', rows[0]['avatar'])
        cleared = self.api(self.teacher).patch(self.url(), {'avatar': ''}, format='multipart')
        self.assertIsNone(cleared.json()['avatar'])

    def test_validation(self):
        text = SimpleUploadedFile('x.png', b'bu rasm emas', content_type='image/png')
        self.assertEqual(self.api(self.teacher).patch(self.url(), {'avatar': text}, format='multipart').status_code, 400)
        buffer = BytesIO()
        Image.new('RGB', (20, 20)).save(buffer, format='GIF')
        gif = SimpleUploadedFile('x.gif', buffer.getvalue(), content_type='image/gif')
        self.assertEqual(self.api(self.teacher).patch(self.url(), {'avatar': gif}, format='multipart').status_code, 400)
        self.assertEqual(self.api(self.student).patch(self.url(), {'avatar': png()}, format='multipart').status_code, 403)
        self.assertEqual(self.api(self.teacher).patch(self.url(), {'title': 'Yangi nom'}, format='json').status_code, 200)

    def test_group_chat_falls_back_to_the_course_avatar(self):
        self.assertIsNone(self.api(self.student).get(f'/api/v1/chat/rooms/{self.room.id}/').json()['image'])
        self.api(self.teacher).patch(self.url(), {'avatar': png()}, format='multipart')
        image = self.api(self.student).get(f'/api/v1/chat/rooms/{self.room.id}/').json()['image']
        self.assertIn('course_avatars/', image)


class VoiceHostTests(ScheduleBase):
    def test_host_id_matches_the_livekit_identity(self):
        room = VoiceRoom.objects.create(course=self.course, created_by=self.teacher, title='Suhbat')
        resp = self.api(self.student).get(f'/api/v1/voice-rooms/{room.id}/')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['host_id'], body['host_identity']), (str(self.teacher.id), f'user-{self.teacher.id}'))
