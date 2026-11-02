"""Ota-ona yangi dizayni: darslar filtri, davomat filtr/izoh/rozilik, jonli diqqat foizi, davomat bildirishnomalari."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User
from apps.lessons import services
from apps.lessons.models import Attendance, Course, Enrollment, FocusEvent, Lesson
from apps.notifications.models import NotificationRecipient

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def rows(response):
    body = response.json()
    return body['results'] if isinstance(body, dict) and 'results' in body else body


def inbox(user, kind):
    return list(NotificationRecipient.objects.filter(user=user, notification__kind=kind).select_related('notification'))


class ParentFixture(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.parent = make('p1', User.Role.PARENT)
        self.toshmat = make('s1', User.Role.STUDENT, first_name='Toshmat')
        self.aziza = make('s2', User.Role.STUDENT, first_name='Aziza')
        self.english = Course.objects.create(teacher=self.teacher, title='Ingliz tili')
        self.math = Course.objects.create(teacher=self.teacher, title='Matematika')
        Enrollment.objects.create(course=self.english, student=self.toshmat, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.math, student=self.aziza, status=Enrollment.Status.APPROVED)
        for child in (self.toshmat, self.aziza):
            ParentChildLink.objects.create(parent=self.parent, student=child, status=ParentChildLink.Status.APPROVED)
        self.now = timezone.now()

    def lesson(self, course, days_ago=1, status=Lesson.Status.FINISHED, **extra):
        return Lesson.objects.create(course=course, starts_at=self.now - timedelta(days=days_ago), duration_min=60, status=status, **extra)

    def attend(self, student, lesson, minutes=50):
        return Attendance.objects.create(lesson=lesson, student=student, joined_at=lesson.starts_at, left_at=lesson.starts_at + timedelta(minutes=minutes))


class LessonFilterTests(ParentFixture):
    def setUp(self):
        super().setUp()
        self.l_en = self.lesson(self.english, days_ago=5)
        self.l_en2 = self.lesson(self.english, days_ago=1)
        self.l_math = self.lesson(self.math, days_ago=3)

    def ids(self, query, user=None):
        response = client_for(user or self.parent).get('/api/v1/lessons/' + query)
        self.assertEqual(response.status_code, 200, response.content)
        return {row['id'] for row in rows(response)}

    def test_parent_sees_all_children_without_the_filter(self):
        self.assertEqual(self.ids(''), {str(self.l_en.id), str(self.l_en2.id), str(self.l_math.id)})

    def test_student_filter_limits_to_that_childs_courses(self):
        self.assertEqual(self.ids(f'?student={self.toshmat.pk}'), {str(self.l_en.id), str(self.l_en2.id)})
        self.assertEqual(self.ids(f'?student={self.aziza.pk}'), {str(self.l_math.id)})

    def test_foreign_or_unapproved_student_is_forbidden(self):
        stranger = make('s9', User.Role.STUDENT)
        self.assertEqual(client_for(self.parent).get(f'/api/v1/lessons/?student={stranger.pk}').status_code, 403)
        ParentChildLink.objects.filter(student=self.toshmat).update(status=ParentChildLink.Status.PENDING)
        self.assertEqual(client_for(self.parent).get(f'/api/v1/lessons/?student={self.toshmat.pk}').status_code, 403)

    def test_student_may_only_filter_by_himself(self):
        self.assertEqual(client_for(self.toshmat).get(f'/api/v1/lessons/?student={self.aziza.pk}').status_code, 403)
        self.assertEqual(self.ids(f'?student={self.toshmat.pk}', user=self.toshmat), {str(self.l_en.id), str(self.l_en2.id)})

    def test_date_range_accepts_plain_dates_and_iso_datetimes(self):
        day = timezone.localtime(self.l_math.starts_at).date()
        self.assertEqual(self.ids(f'?starts_at__gte={day}&starts_at__lte={day}'), {str(self.l_math.id)})  # kun boshidan oxirigacha
        iso = (self.l_en.starts_at + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        self.assertEqual(self.ids(f'?starts_at__lte={iso}'), {str(self.l_en.id)})
        self.assertEqual(self.ids(f'?student={self.toshmat.pk}&starts_at__gte={day}'), {str(self.l_en2.id)})

    def test_bad_date_is_a_400(self):
        self.assertEqual(client_for(self.parent).get('/api/v1/lessons/?starts_at__gte=zzz').status_code, 400)

    def test_old_filters_still_work(self):
        self.assertEqual(self.ids(f'?course={self.english.pk}'), {str(self.l_en.id), str(self.l_en2.id)})
        self.assertEqual(self.ids('?status=scheduled'), set())


class AttendanceParentTests(ParentFixture):
    def setUp(self):
        super().setUp()
        self.l1 = self.lesson(self.english, days_ago=10)
        self.l2 = self.lesson(self.english, days_ago=2)
        self.l3 = self.lesson(self.math, days_ago=4)
        self.a1, self.a2 = self.attend(self.toshmat, self.l1), self.attend(self.toshmat, self.l2)
        self.a3 = self.attend(self.aziza, self.l3)

    def list(self, query='', user=None):
        return client_for(user or self.parent).get('/api/v1/attendance/' + query)

    def test_course_and_date_filters(self):
        self.assertEqual({r['id'] for r in rows(self.list(f'?course={self.math.pk}'))}, {str(self.a3.id)})
        day = timezone.localtime(self.l2.starts_at).date()
        self.assertEqual({r['id'] for r in rows(self.list(f'?from={day}'))}, {str(self.a2.id)})  # l3 (4 kun oldin) undan oldin
        self.assertEqual({r['id'] for r in rows(self.list(f'?to={timezone.localtime(self.l1.starts_at).date()}'))}, {str(self.a1.id)})
        both = self.list(f'?student={self.toshmat.pk}&from={day}')
        self.assertEqual({r['id'] for r in rows(both)}, {str(self.a2.id)})

    def test_teacher_note_and_late_reason_are_visible_to_parent(self):
        response = client_for(self.teacher).patch(f'/api/v1/attendance/{self.a2.id}/', {'teacher_note': 'Faol qatnashdi', 'late_reason': 'Transport'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        row = next(r for r in rows(self.list()) if r['id'] == str(self.a2.id))
        self.assertEqual((row['teacher_note'], row['late_reason']), ('Faol qatnashdi', 'Transport'))

    def test_only_the_lessons_teacher_may_write_notes(self):
        url = f'/api/v1/attendance/{self.a2.id}/'
        self.assertEqual(client_for(self.parent).patch(url, {'teacher_note': 'x'}, format='json').status_code, 403)
        self.assertEqual(client_for(self.toshmat).patch(url, {'teacher_note': 'x'}, format='json').status_code, 403)
        other_teacher = make('t2', User.Role.TEACHER)
        self.assertEqual(client_for(other_teacher).patch(url, {'teacher_note': 'x'}, format='json').status_code, 404)  # ko'rinmaydi
        self.assertEqual(client_for(self.teacher).patch(url, {'joined_at': '2020-01-01T00:00:00Z'}, format='json').status_code, 400)
        self.assertEqual(client_for(self.teacher).patch(url, {'teacher_note': 'x' * 3000}, format='json').status_code, 200)
        self.a2.refresh_from_db()
        self.assertEqual(len(self.a2.teacher_note), 2000)

    def test_analytics_consent_hides_the_child_from_the_list(self):
        Consent.objects.create(student=self.toshmat, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        own = rows(self.list())
        self.assertEqual({r['id'] for r in own}, {str(self.a3.id)})  # Toshmatning qatorlari yo'q, Aziza qoladi
        denied = self.list(f'?student={self.toshmat.pk}')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()['error']['code'], 'consent_required')
        self.assertEqual(self.list(f'?student={self.aziza.pk}').status_code, 200)
        # o'qituvchi va o'quvchining o'zi cheklanmaydi
        self.assertEqual(len(rows(self.list(user=self.teacher))), 3)
        self.assertEqual(len(rows(self.list(user=self.toshmat))), 2)

    def test_course_summary_hides_a_denied_child_from_the_parent(self):
        Enrollment.objects.create(course=self.math, student=self.toshmat, status=Enrollment.Status.APPROVED)
        Consent.objects.create(student=self.toshmat, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        response = client_for(self.parent).get(f'/api/v1/courses/{self.math.pk}/attendance/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({s['id'] for s in response.json()['students']}, {str(self.aziza.pk)})


class LiveFocusPercentTests(ParentFixture):
    def test_focus_percent_is_computed_while_the_lesson_is_live(self):
        lesson = self.lesson(self.english, days_ago=0, status=Lesson.Status.LIVE)
        lesson.live_started_at = self.now - timedelta(minutes=20)
        lesson.save(update_fields=['live_started_at'])
        joined = self.now - timedelta(minutes=10)
        attendance = Attendance.objects.create(lesson=lesson, student=self.toshmat, joined_at=joined)  # hali chiqmagan
        event = FocusEvent.objects.create(lesson=lesson, student=self.toshmat, kind=FocusEvent.Kind.EXIT)
        FocusEvent.objects.filter(pk=event.pk).update(created_at=self.now - timedelta(minutes=5))  # 5 daqiqadan beri tashqarida
        row = next(r for r in rows(client_for(self.parent).get(f'/api/v1/attendance/?student={self.toshmat.pk}')) if r['id'] == str(attendance.id))
        self.assertIsNotNone(row['focus_percent'])
        self.assertTrue(45 <= row['focus_percent'] <= 55, row['focus_percent'])  # 10 daqiqadan 5 tasi tashqarida
        self.assertIsNone(row['left_at'])

    def test_finished_lessons_keep_the_old_calculation_and_unjoined_is_null(self):
        lesson = self.lesson(self.english)
        attendance = Attendance.objects.create(lesson=lesson, student=self.toshmat)  # hech qachon kirmagan
        row = next(r for r in rows(client_for(self.parent).get('/api/v1/attendance/')) if r['id'] == str(attendance.id))
        self.assertIsNone(row['focus_percent'])


class AttendanceNotificationTests(ParentFixture):
    def setUp(self):
        super().setUp()
        self.quiet_parent = make('p2', User.Role.PARENT, notify_child_absent=False)
        ParentChildLink.objects.create(parent=self.quiet_parent, student=self.toshmat, status=ParentChildLink.Status.APPROVED)
        self.live = self.lesson(self.english, days_ago=0, status=Lesson.Status.LIVE)

    def join(self, student, minutes_after_start=None):
        if minutes_after_start is not None:
            Lesson.objects.filter(pk=self.live.pk).update(live_started_at=timezone.now() - timedelta(minutes=minutes_after_start))
            self.live.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            return services.mark_joined(lesson=self.live, student=student)

    def test_joined_notification_has_structured_data(self):
        self.join(self.toshmat, minutes_after_start=1)
        (item,) = inbox(self.parent, 'attendance.joined')
        notification = item.notification
        self.assertEqual(notification.link_type, 'lesson')
        self.assertEqual(notification.link_id, str(self.live.pk))
        self.assertEqual(notification.data['student_id'], str(self.toshmat.pk))
        self.assertEqual(notification.data['course_title'], 'Ingliz tili')
        self.assertIn('darsga kirdi', notification.description)
        self.assertEqual(len(inbox(self.quiet_parent, 'attendance.joined')), 1)  # "kirdi" notify_child_absent ga bog'liq emas

    def test_late_join_notifies_only_parents_who_want_absence_alerts(self):
        self.join(self.toshmat, minutes_after_start=12)
        (item,) = inbox(self.parent, 'attendance.late')
        self.assertEqual(item.notification.data['late_minutes'], 12)
        self.assertEqual(inbox(self.parent, 'attendance.joined'), [])
        self.assertEqual(inbox(self.quiet_parent, 'attendance.late'), [])

    def test_second_join_does_not_notify_again(self):
        self.join(self.toshmat, minutes_after_start=1)
        self.join(self.toshmat)
        self.assertEqual(len(inbox(self.parent, 'attendance.joined')), 1)

    def test_analytics_consent_denied_means_no_attendance_messages(self):
        Consent.objects.create(student=self.toshmat, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        self.join(self.toshmat, minutes_after_start=1)
        self.assertEqual(inbox(self.parent, 'attendance.joined'), [])

    def test_absent_alert_after_ten_minutes_once_and_only_for_absent_students(self):
        Lesson.objects.filter(pk=self.live.pk).update(live_started_at=timezone.now() - timedelta(minutes=11))
        classmate = make('s3', User.Role.STUDENT)
        Enrollment.objects.create(course=self.english, student=classmate, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=classmate, status=ParentChildLink.Status.APPROVED)
        self.join(classmate)  # u kirgan
        self.assertEqual(services.send_absence_alerts(), 1)
        (item,) = inbox(self.parent, 'attendance.missed')
        self.assertEqual(item.notification.data['student_id'], str(self.toshmat.pk))
        self.assertEqual(inbox(self.quiet_parent, 'attendance.missed'), [])  # u o'chirib qo'ygan
        self.assertEqual(services.send_absence_alerts(), 0)  # takrorlanmaydi
        self.assertEqual(len(inbox(self.parent, 'attendance.missed')), 1)

    def test_no_absent_alert_before_ten_minutes(self):
        Lesson.objects.filter(pk=self.live.pk).update(live_started_at=timezone.now() - timedelta(minutes=5))
        self.assertEqual(services.send_absence_alerts(), 0)

    def test_finishing_the_lesson_alerts_students_who_never_came_without_duplicates(self):
        Lesson.objects.filter(pk=self.live.pk).update(live_started_at=timezone.now() - timedelta(minutes=30))
        self.live.refresh_from_db()
        services.send_absence_alerts()
        self.assertEqual(len(inbox(self.parent, 'attendance.missed')), 1)
        services.finish_lesson(teacher=self.teacher, lesson=self.live)
        self.assertEqual(len(inbox(self.parent, 'attendance.missed')), 1)  # allaqachon yuborilgan

    def test_finish_alerts_if_nothing_was_sent_before(self):
        Lesson.objects.filter(pk=self.live.pk).update(live_started_at=timezone.now() - timedelta(minutes=3))
        self.live.refresh_from_db()
        services.finish_lesson(teacher=self.teacher, lesson=self.live)
        self.assertEqual(len(inbox(self.parent, 'attendance.missed')), 1)
