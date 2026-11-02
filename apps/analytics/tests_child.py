"""Ota-ona uchun farzand statistikasi: summary / children summary / rank (BACKEND_OTA_ONA.md 2, 9, 17-bandlar).

Hamma hisob aniq bir `now` (2026-11-11 chorshanba 12:00 Toshkent) atrofida — oy/hafta chegaralarida tasodifiy yiqilmasligi uchun."""
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User
from apps.analytics import child
from apps.homework.models import Assignment, Submission
from apps.lessons.models import Attendance, Course, Enrollment, Lesson

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def at(day, hour=12, minute=0, month=11):
    return timezone.make_aware(datetime(2026, month, day, hour, minute))


NOW = at(11)  # chorshanba; hafta 9-15 noyabr, oy 1-30 noyabr


class ChildAnalyticsBase(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.other_parent = make('p2', User.Role.PARENT)
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT, first_name='Toshmat')
        self.rival = make('s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Ingliz tili A1')
        for student in (self.student, self.rival):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

        # darslar: shu oyda 5 ta (3 tasiga qatnashgan), o'tgan oyda 2 ta (1 tasiga)
        self.lessons = {}
        for key, (month, day, hour) in {
            'n2': (11, 2, 10), 'n3': (11, 3, 10), 'n5': (11, 5, 10), 'n9': (11, 9, 10), 'n10': (11, 10, 9),
            'o5': (10, 5, 10), 'o6': (10, 6, 10),
        }.items():
            self.lessons[key] = Lesson.objects.create(
                course=self.course, starts_at=at(day, hour, month=month), duration_min=60, status=Lesson.Status.FINISHED,
            )
        self.attend('n2', 10, 0, 10, 50)
        self.attend('n9', 10, 5, 10, 50)    # 45 daqiqa (shu hafta)
        self.attend('n10', 9, 0, 9, 30)     # 30 daqiqa (shu hafta)
        self.attend('o5', 10, 0, 10, 50, month=10)

        # vazifalar va tasdiqlangan ballar
        self.a1 = self.assignment('A1', due=at(4))
        self.a2 = self.assignment('A2', due=at(12, 9))
        self.a3 = self.assignment('A3', due=at(18, month=10))
        self.a4 = self.assignment('A4', due=at(12, 8))  # topshirilmagan, 24 soat ichida
        self.score(self.student, self.a1, 80, at(3))
        self.score(self.student, self.a2, 90, at(10))
        self.score(self.student, self.a3, 70, at(20, month=10))
        self.score(self.rival, self.a1, 90, at(3))
        self.score(self.rival, self.a2, 70, at(10))

    def attend(self, key, h1, m1, h2, m2, month=11):
        lesson = self.lessons[key]
        day = timezone.localtime(lesson.starts_at).day
        Attendance.objects.create(lesson=lesson, student=self.student, joined_at=at(day, h1, m1, month), left_at=at(day, h2, m2, month))

    def assignment(self, title, due):
        a = Assignment.objects.create(course=self.course, title=title, due_at=due, status=Assignment.Status.ACTIVE)
        Assignment.objects.filter(pk=a.pk).update(created_at=due - timedelta(days=5))
        return a

    def score(self, student, assignment, value, reviewed_at):
        return Submission.objects.create(
            assignment=assignment, student=student, file='x.pdf', original_name='x.pdf',
            status=Submission.Status.DONE, overall_score=value, reviewed_at=reviewed_at,
        )


class ChildSummaryTests(ChildAnalyticsBase):
    def test_cards_trend_and_deltas(self):
        data = child.child_summary(viewer=self.parent, student_id=self.student.pk, now=NOW)
        self.assertEqual(data['attendance'], {'month_percent': 60, 'attended': 3, 'total': 5, 'delta_percent': 10})
        self.assertEqual(data['score'], {'average': 8.5, 'scale': 10, 'delta': 1.5})
        self.assertEqual(data['homework'], {'total': 3, 'submitted': 2, 'due_soon': 1})
        self.assertEqual(data['week_minutes'], 75)
        trend = {row['week_start']: row['average'] for row in data['score_trend']}
        self.assertEqual(list(trend), ['2026-10-05', '2026-10-12', '2026-10-19', '2026-10-26', '2026-11-02', '2026-11-09'])
        self.assertEqual(trend['2026-10-19'], 7.0)
        self.assertEqual(trend['2026-11-02'], 8.0)
        self.assertEqual(trend['2026-11-09'], 9.0)
        self.assertIsNone(trend['2026-10-05'])

    def test_unapproved_scores_do_not_count(self):
        Submission.objects.filter(student=self.student, assignment=self.a2).update(status=Submission.Status.PENDING_REVIEW)
        data = child.child_summary(viewer=self.parent, student_id=self.student.pk, now=NOW)
        self.assertEqual(data['score']['average'], 8.0)  # faqat A1 (80); A2 hali tasdiqlanmagan

    def test_only_the_latest_submission_per_assignment_counts(self):
        newer = self.score(self.student, self.a1, 50, at(10))  # qayta topshirilgan: eng so'nggisi 50
        Submission.objects.filter(pk=newer.pk).update(created_at=at(10))
        data = child.child_summary(viewer=self.parent, student_id=self.student.pk, now=NOW)
        self.assertEqual(data['score']['average'], 7.0)  # (50 + 90) / 2

    def test_no_data_gives_nulls_not_errors(self):
        newbie = make('s9', User.Role.STUDENT)
        ParentChildLink.objects.create(parent=self.parent, student=newbie, status=ParentChildLink.Status.APPROVED)
        data = child.child_summary(viewer=self.parent, student_id=newbie.pk, now=NOW)
        self.assertEqual(data['attendance'], {'month_percent': None, 'attended': 0, 'total': 0, 'delta_percent': None})
        self.assertIsNone(data['score']['average'])
        self.assertEqual(data['homework'], {'total': 0, 'submitted': 0, 'due_soon': 0})
        self.assertEqual(data['week_minutes'], 0)

    def test_http_permissions_and_consent(self):
        url = f'/api/v1/analytics/child/{self.student.pk}/summary/'

        def get(user):
            client = APIClient()
            if user:
                client.force_authenticate(user)
            return client.get(url)

        self.assertEqual(get(None).status_code, 401)
        self.assertEqual(get(self.other_parent).status_code, 403)  # bog'lanmagan ota-ona
        self.assertEqual(get(self.teacher).status_code, 403)
        self.assertEqual(get(self.parent).status_code, 200)
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        denied = get(self.parent)
        self.assertEqual(denied.status_code, 403)
        error = denied.json()['error']
        self.assertEqual(error['code'], 'consent_required')
        self.assertEqual(error['details']['kind'], 'analytics')
        Consent.objects.filter(student=self.student).update(granted=True)
        self.assertEqual(get(self.parent).status_code, 200)

    def test_pending_link_is_not_enough(self):
        ParentChildLink.objects.filter(parent=self.parent).update(status=ParentChildLink.Status.PENDING)
        client = APIClient()
        client.force_authenticate(self.parent)
        self.assertEqual(client.get(f'/api/v1/analytics/child/{self.student.pk}/summary/').status_code, 403)


class ChildrenSummaryTests(ChildAnalyticsBase):
    def test_week_and_month_rows(self):
        (row,) = child.children_summary(viewer=self.parent, period='week', now=NOW)
        self.assertEqual(row['student_id'], str(self.student.pk))
        self.assertEqual(row['groups_count'], 1)
        self.assertFalse(row['restricted'])
        self.assertEqual(row['attendance'], {'month_percent': 60, 'period_percent': 100, 'attended_total': 4})
        self.assertEqual(row['homework'], {'period_submitted': 1, 'period_total': 2})  # A2 (topshirilgan) va A4 shu haftada
        self.assertEqual(row['score'], {'average': 8.0, 'period_average': 9.0, 'scale': 10})
        self.assertEqual(row['last_visit']['lesson_id'], str(self.lessons['n10'].pk))
        self.assertEqual(row['last_visit']['course_title'], 'Ingliz tili A1')
        (month,) = child.children_summary(viewer=self.parent, period='month', now=NOW)
        self.assertEqual(month['attendance']['period_percent'], 60)
        self.assertEqual(month['homework'], {'period_submitted': 2, 'period_total': 3})

    def test_denied_analytics_hides_activity_but_keeps_the_child(self):
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        (row,) = child.children_summary(viewer=self.parent, period='week', now=NOW)
        self.assertTrue(row['restricted'])
        self.assertIsNone(row['attendance'])
        self.assertIsNone(row['last_visit'])
        self.assertEqual(row['homework']['period_total'], 2)  # vazifa ma'lumoti faollik emas: qoladi

    def test_only_this_parents_approved_children(self):
        outsider = make('s5', User.Role.STUDENT)
        ParentChildLink.objects.create(parent=self.other_parent, student=outsider, status=ParentChildLink.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.rival, status=ParentChildLink.Status.PENDING)
        rows = child.children_summary(viewer=self.parent, period='month', now=NOW)
        self.assertEqual([r['student_id'] for r in rows], [str(self.student.pk)])

    def test_http_validates_period(self):
        client = APIClient()
        client.force_authenticate(self.parent)
        self.assertEqual(client.get('/api/v1/analytics/children/summary/').status_code, 200)
        self.assertEqual(client.get('/api/v1/analytics/children/summary/?period=week').status_code, 200)
        self.assertEqual(client.get('/api/v1/analytics/children/summary/?period=year').status_code, 400)


class ChildRankTests(ChildAnalyticsBase):
    def test_rank_percentile_and_delta(self):
        data = child.child_rank(viewer=self.parent, student_id=self.student.pk, course_id=self.course.pk, month='2026-11', now=NOW)
        self.assertEqual((data['rank'], data['total']), (1, 2))  # 8.5 > 8.0
        self.assertEqual(data['top_percent'], 50)
        self.assertEqual(data['percentile'], 50)
        self.assertEqual(data['delta'], 0)  # o'tgan oyda yagona ballga ega: 1-o'rin edi
        self.assertEqual(data['month'], '2026-11')

    def test_lower_rank_and_ties(self):
        self.score(self.rival, self.a4, 100, at(11))  # raqib ballari: 90, 70, 100 -> 86.7 -> 8.7 > 8.5 (o'quvchi)
        data = child.child_rank(viewer=self.parent, student_id=self.student.pk, course_id=self.course.pk, month='2026-11', now=NOW)
        self.assertEqual(data['rank'], 2)
        self.assertEqual(data['top_percent'], 100)
        self.assertEqual(data['percentile'], 0)

    def test_child_without_scores_has_no_rank(self):
        Submission.objects.filter(student=self.student).delete()
        data = child.child_rank(viewer=self.parent, student_id=self.student.pk, course_id=self.course.pk, month='2026-11', now=NOW)
        self.assertIsNone(data['rank'])
        self.assertIsNone(data['top_percent'])

    def test_http_requires_course_and_membership(self):
        client = APIClient()
        client.force_authenticate(self.parent)
        base = f'/api/v1/analytics/child/{self.student.pk}/rank/'
        self.assertEqual(client.get(base).status_code, 400)
        other_course = Course.objects.create(teacher=self.teacher, title='Boshqa')
        self.assertEqual(client.get(f'{base}?course={other_course.pk}').status_code, 404)
        self.assertEqual(client.get(f'{base}?course={self.course.pk}&month=bad').status_code, 400)
        self.assertEqual(client.get(f'{base}?course={self.course.pk}').status_code, 200)
        other = APIClient()
        other.force_authenticate(self.other_parent)
        self.assertEqual(other.get(f'{base}?course={self.course.pk}').status_code, 403)
