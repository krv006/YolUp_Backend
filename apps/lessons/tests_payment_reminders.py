"""To'lov muddati: sozlash, eslatmalar (o'quvchi + ota-ona, faqat to'lanmagan, bir martadan), to'lamaganlar soni (2026-11-10)."""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.chat import services as chat_services
from apps.lessons import payments
from apps.lessons.models import Course, CoursePayment, Enrollment, PaymentReminderLog
from apps.notifications.models import Notification, NotificationRecipient


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


def at(day: date):
    return datetime(day.year, day.month, day.day, 8, 0, tzinfo=dt_timezone.utc)


class PaymentSetupTests(APITestCase):
    def setUp(self):
        self.teacher = make('pay_t', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='A', monthly_fee=300000)
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def patch(self, **body):
        return self.client.patch(f'/api/v1/courses/{self.course.id}/', body, format='json')

    def test_teacher_sets_day_and_multiple_reminder_days(self):
        r = self.patch(payment_day=5, payment_reminder_days=[3, 7, 7])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['payment_day'], r.json()['payment_reminder_days']), (5, [7, 3]))
        self.course.refresh_from_db()
        self.assertEqual((self.course.payment_day, self.course.payment_reminder_days), (5, [7, 3]))

    def test_validation(self):
        self.assertEqual(self.patch(payment_day=29).status_code, 400)
        self.assertEqual(self.patch(payment_day=0).status_code, 400)
        self.assertEqual(self.patch(payment_day=5, payment_reminder_days=[4]).status_code, 400)
        self.assertEqual(self.patch(payment_reminder_days=[3]).status_code, 400)  # kun belgilanmagan


class PaymentReminderTests(APITestCase):
    def setUp(self):
        self.teacher = make('pr_t', User.Role.TEACHER)
        self.s_unpaid, self.s_paid, self.s_pending = (make(f'pr_s{i}', User.Role.STUDENT) for i in range(3))
        self.parent = make('pr_p', User.Role.PARENT)
        self.course = Course.objects.create(
            teacher=self.teacher, title='Algebra', monthly_fee=300000, payment_day=10, payment_reminder_days=[3, 7],
        )
        for student, status in ((self.s_unpaid, 'approved'), (self.s_paid, 'approved'), (self.s_pending, 'pending')):
            Enrollment.objects.create(course=self.course, student=student, status=status)
        ParentChildLink.objects.create(parent=self.parent, student=self.s_unpaid, status=ParentChildLink.Status.APPROVED)
        CoursePayment.objects.create(course=self.course, student=self.s_paid, period=date(2026, 11, 1), paid_at=at(date(2026, 11, 1)))

    def recipients(self, kind='payment_reminder'):
        return sorted(NotificationRecipient.objects.filter(notification__kind=kind).values_list('user__username', flat=True))

    def test_reminds_only_unpaid_students_and_their_parents_on_the_chosen_days(self):
        # 10-noyabr muddat: 7 kun oldin = 3-noyabr
        out = payments.send_reminders(now=at(date(2026, 11, 3)))
        self.assertEqual(out, {'students': 1, 'parents': 1})
        self.assertEqual(self.recipients(), ['pr_p', 'pr_s0'])  # to'lagan va kutayotgan o'quvchi yo'q
        text = Notification.objects.filter(kind='payment_reminder').first().description
        self.assertIn('Algebra', text)
        # tanlanmagan kun (masalan 5-noyabr = 5 kun oldin) — xabar yo'q
        self.assertEqual(payments.send_reminders(now=at(date(2026, 11, 5))), {'students': 0, 'parents': 0})
        # 7-noyabr = 3 kun oldin — yana bir eslatma
        self.assertEqual(payments.send_reminders(now=at(date(2026, 11, 7))), {'students': 1, 'parents': 1})

    def test_each_reminder_is_sent_once_even_if_the_job_runs_many_times(self):
        for _ in range(3):
            payments.send_reminders(now=at(date(2026, 11, 3)))
        self.assertEqual(NotificationRecipient.objects.filter(notification__kind='payment_reminder').count(), 2)
        self.assertEqual(PaymentReminderLog.objects.count(), 1)

    def test_paid_students_are_not_reminded_and_next_month_due_date_is_covered(self):
        CoursePayment.objects.create(course=self.course, student=self.s_unpaid, period=date(2026, 11, 1), paid_at=at(date(2026, 11, 2)))
        self.assertEqual(payments.send_reminders(now=at(date(2026, 11, 3))), {'students': 0, 'parents': 0})
        # dekabr to'lovi uchun: 10-dekabr, 7 kun oldin = 3-dekabr; 3 kun oldin = 7-dekabr
        self.assertEqual(payments.send_reminders(now=at(date(2026, 12, 3))), {'students': 2, 'parents': 1})
        # oy chegarasi: 10-yanvardan 7 kun oldin = 3-yanvar; 3-noyabr bilan adashmaydi
        self.assertEqual(payments.send_reminders(now=at(date(2026, 12, 29))), {'students': 0, 'parents': 0})

    def test_management_command_runs(self):
        from django.core.management import call_command

        with mock.patch('apps.lessons.payments.local_today', return_value=date(2026, 11, 3)):
            call_command('send_payment_reminders', verbosity=0)
        self.assertEqual(self.recipients(), ['pr_p', 'pr_s0'])


class UnpaidCountTests(PaymentReminderTests):
    def test_unpaid_and_overdue_counts_in_courses_and_chat_rooms_for_the_teacher_only(self):
        chat_services.ensure_course_room(self.course)
        client = APIClient()
        client.force_authenticate(self.teacher)
        today = payments.local_today()
        CoursePayment.objects.filter(course=self.course).delete()
        self.course.payment_day = 1  # bugun 1-kundan keyin bo'lsa muddat o'tgan
        self.course.save(update_fields=['payment_day'])
        rows = client.get('/api/v1/courses/').json()
        rows = rows['results'] if isinstance(rows, dict) else rows
        row = next(r for r in rows if r['id'] == str(self.course.id))
        self.assertEqual(row['unpaid_count'], 2)  # approved: s_unpaid, s_paid (to'lov o'chirildi)
        self.assertEqual(row['overdue_count'], 2 if today.day > 1 else 0)
        rooms = client.get('/api/v1/chat/rooms/').json()['results']
        room = next(r for r in rooms if r['kind'] == 'course')
        self.assertEqual(room['unpaid_count'], 2)
        # o'quvchi ko'rmaydi
        student_client = APIClient()
        student_client.force_authenticate(self.s_unpaid)
        srows = student_client.get('/api/v1/courses/').json()
        srows = srows['results'] if isinstance(srows, dict) else srows
        self.assertIsNone(next(r for r in srows if r['id'] == str(self.course.id))['unpaid_count'])

    def test_unconfigured_courses_do_not_count(self):
        plain = Course.objects.create(teacher=self.teacher, title='Bepul')
        Enrollment.objects.create(course=plain, student=self.s_unpaid, status='approved')
        self.assertNotIn(plain.id, payments.unpaid_counts_for_teacher(self.teacher))

    def test_progress_marks_overdue_for_past_months(self):
        client = APIClient()
        client.force_authenticate(self.teacher)
        body = client.get(f'/api/v1/courses/{self.course.id}/students/{self.s_unpaid.id}/progress/').json()
        statuses = {p['period']: (p['status'], p['overdue']) for p in body['payments']}
        current = f'{payments.local_today():%Y-%m}'
        for period, (status, overdue) in statuses.items():
            self.assertEqual(status, 'unpaid')
            if period < current:
                self.assertTrue(overdue, period)
