"""O'qituvchi uchun o'quvchilar progressi (`/courses/{id}/progress/`, `/students/{sid}/progress/`, to'lov belgisi) +
frontend topgan uchta xato: UUID bo'lmagan id (500 -> 400), login tarixi sahifalash filtrlari, remind-child xato formati."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.homework.models import Assignment, Submission
from apps.lessons import progress
from apps.lessons.models import Attendance, Course, CoursePayment, Enrollment, Lesson

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


class ProgressTests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.teacher = make('t1', User.Role.TEACHER)
        self.other_teacher = make('t2', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', monthly_fee=450000)
        self.aziza = make('aziza', User.Role.STUDENT, first_name='Aziza')
        self.bobur = make('bobur', User.Role.STUDENT, first_name='Bobur')
        self.pending = make('kutadi', User.Role.STUDENT)
        for student, state in ((self.aziza, 'approved'), (self.bobur, 'approved'), (self.pending, 'pending')):
            Enrollment.objects.create(course=self.course, student=student, status=state)
        # Bobur yaqinda qo'shilgan, Aziza ancha oldin
        Enrollment.objects.filter(student=self.aziza).update(created_at=self.now - timedelta(days=100))
        Enrollment.objects.filter(student=self.bobur).update(created_at=self.now - timedelta(days=5))
        self.l1 = self.lesson(3)
        self.l2 = self.lesson(2)
        Attendance.objects.create(lesson=self.l1, student=self.aziza, joined_at=self.l1.starts_at, left_at=self.l1.starts_at + timedelta(minutes=50))
        Attendance.objects.create(lesson=self.l2, student=self.aziza, joined_at=self.l2.starts_at)
        Attendance.objects.create(lesson=self.l1, student=self.bobur, joined_at=self.l1.starts_at)
        # Vazifalar: bittasi Bobur qo'shilgunga qadar bo'lgan (muddati o'tgan), biri o'tgan, biri kelajakda
        self.old_hw = Assignment.objects.create(course=self.course, title='Eski', due_at=self.now - timedelta(days=30), status=Assignment.Status.ACTIVE)
        self.past_hw = Assignment.objects.create(course=self.course, title="Muddati o'tdi", due_at=self.now - timedelta(days=1), status=Assignment.Status.ACTIVE)
        self.future_hw = Assignment.objects.create(course=self.course, title='Kelgusi', due_at=self.now + timedelta(days=2), status=Assignment.Status.ACTIVE)
        Assignment.objects.create(course=self.course, title='Qoralama', status=Assignment.Status.DRAFT)
        self.sub(self.aziza, self.old_hw, Submission.Status.DONE, 90)
        self.sub(self.aziza, self.past_hw, Submission.Status.DONE, 70)
        self.sub(self.aziza, self.future_hw, Submission.Status.PENDING_REVIEW, 80)
        self.url = f'/api/v1/courses/{self.course.id}/progress/'

    def lesson(self, days_ago):
        return Lesson.objects.create(
            course=self.course, starts_at=self.now - timedelta(days=days_ago), duration_min=60, status=Lesson.Status.FINISHED,
        )

    def sub(self, student, assignment, status, score=None):
        return Submission.objects.create(
            assignment=assignment, student=student, file='x.pdf', original_name='x.pdf', status=status, overall_score=score,
        )

    def rows(self, **query):
        body = client_for(self.teacher).get(self.url, query).json()
        return body, {row['name']: row for row in body['students']}

    def test_lists_approved_students_with_join_date_and_summary(self):
        body, rows = self.rows()
        self.assertEqual(set(rows), {'Aziza', 'Bobur'})  # kutayotgani yo'q
        self.assertEqual(body['summary']['students'], 2)
        self.assertEqual(body['lesson_count'], 2)
        self.assertEqual(body['monthly_fee'], 450000)
        self.assertLess(rows['Aziza']['joined_at'], rows['Bobur']['joined_at'])

    def test_attendance_matches_course_summary(self):
        _body, rows = self.rows()
        self.assertEqual(rows['Aziza']['attendance'], {'percent': 100, 'attended': 2, 'total': 2, 'focus_percent': 100})
        self.assertEqual(rows['Bobur']['attendance']['percent'], 50)
        self.assertIsNotNone(rows['Aziza']['last_visit_at'])

    def test_homework_counts_and_average(self):
        _body, rows = self.rows()
        aziza = rows['Aziza']['homework']
        self.assertEqual((aziza['total'], aziza['submitted'], aziza['checked'], aziza['awaiting_review']), (3, 3, 2, 1))
        self.assertEqual(aziza['average'], 8.0)  # (9 + 7) / 2, kutayotgani kirmaydi
        self.assertEqual(aziza['completion_percent'], 100)
        bobur = rows['Bobur']['homework']
        # Bobur "Eski" vazifa muddatidan keyin qo'shilgan -> hisobga kirmaydi; muddati o'tgani - qilmagan, kelgusi - hali emas
        self.assertEqual((bobur['total'], bobur['submitted'], bobur['missed']), (2, 0, 1))
        self.assertEqual(bobur['completion_percent'], 0)
        self.assertIsNone(bobur['average'])

    def test_resubmit_requested_counts_as_not_submitted(self):
        self.sub(self.bobur, self.past_hw, Submission.Status.RESUBMIT_REQUESTED)
        _body, rows = self.rows()
        self.assertEqual((rows['Bobur']['homework']['submitted'], rows['Bobur']['homework']['resubmit_requested']), (0, 1))

    def test_payment_mark_and_unmark(self):
        url = f'/api/v1/courses/{self.course.id}/students/{self.aziza.pk}/payments/{progress.current_period():%Y-%m}/'
        _body, rows = self.rows()
        self.assertEqual(rows['Aziza']['payment']['status'], 'unpaid')
        self.assertGreaterEqual(rows['Aziza']['payment']['unpaid_months'], 4)  # 100 kun oldin qo'shilgan
        marked = client_for(self.teacher).put(url, {'note': 'Naqd'}, format='json')
        self.assertEqual(marked.status_code, 200, marked.content)
        self.assertEqual((marked.json()['status'], marked.json()['amount'], marked.json()['note']), ('paid', 450000, 'Naqd'))
        again = client_for(self.teacher).put(url, {'amount': 300000}, format='json')  # qayta chaqirish yangilaydi
        self.assertEqual(again.json()['amount'], 300000)
        self.assertEqual(CoursePayment.objects.count(), 1)
        body, rows = self.rows()
        self.assertEqual((rows['Aziza']['payment']['status'], body['summary']['paid'], body['summary']['unpaid']), ('paid', 1, 1))
        self.assertEqual(client_for(self.teacher).delete(url).status_code, 204)
        self.assertEqual(client_for(self.teacher).delete(url).status_code, 204)  # ikkinchi marta ham xato emas
        self.assertEqual(CoursePayment.objects.count(), 0)

    def test_month_filter_shows_that_months_payment(self):
        CoursePayment.objects.create(
            course=self.course, student=self.aziza, period=progress.current_period().replace(year=2026, month=1), paid_at=self.now,
        )
        _body, rows = self.rows(month='2026-01')
        self.assertEqual(rows['Aziza']['payment']['status'], 'paid')
        self.assertEqual(rows['Bobur']['payment']['status'], 'unpaid')

    def test_payment_validation(self):
        base = f'/api/v1/courses/{self.course.id}/students/{self.aziza.pk}/payments'
        client = client_for(self.teacher)
        self.assertEqual(client.put(f'{base}/2026-13/', {}, format='json').status_code, 400)
        self.assertEqual(client.put(f'{base}/1999-01/', {}, format='json').status_code, 400)
        self.assertEqual(client.put(f'{base}/2026-01/', {'amount': 'abc'}, format='json').status_code, 400)
        self.assertEqual(client.put(f'{base}/2026-01/', {'amount': -5}, format='json').status_code, 400)
        outsider = f'/api/v1/courses/{self.course.id}/students/{self.pending.pk}/payments/2026-01/'
        self.assertEqual(client.put(outsider, {}, format='json').status_code, 404)  # tasdiqlanmagan o'quvchi

    def test_bad_query_params_are_400(self):
        client = client_for(self.teacher)
        self.assertEqual(client.get(self.url, {'range': 'zzz'}).status_code, 400)
        self.assertEqual(client.get(self.url, {'month': 'abc'}).status_code, 400)

    def test_student_detail(self):
        CoursePayment.objects.create(course=self.course, student=self.aziza, period=progress.current_period(), paid_at=self.now)
        body = client_for(self.teacher).get(f'/api/v1/courses/{self.course.id}/students/{self.aziza.pk}/progress/').json()
        self.assertEqual(body['name'], 'Aziza')
        self.assertEqual(len(body['lessons']), 2)
        self.assertTrue(all(row['attended'] for row in body['lessons']))
        states = {row['title']: row['state'] for row in body['assignments']}
        self.assertEqual(states, {'Eski': 'done', "Muddati o'tdi": 'done', 'Kelgusi': 'awaiting_review'})
        self.assertEqual(body['payments'][0]['status'], 'paid')  # eng yangi oy birinchi
        self.assertEqual(body['payments'][1]['status'], 'unpaid')
        bobur = client_for(self.teacher).get(f'/api/v1/courses/{self.course.id}/students/{self.bobur.pk}/progress/').json()
        self.assertEqual({row['title']: row['state'] for row in bobur['assignments']}, {"Muddati o'tdi": 'missed', 'Kelgusi': 'not_submitted'})
        self.assertEqual([row['attended'] for row in bobur['lessons']], [False, True])  # yangi dars birinchi

    def test_student_detail_unknown_student_404(self):
        outsider = make('boshqa', User.Role.STUDENT)
        url = f'/api/v1/courses/{self.course.id}/students/{outsider.pk}/progress/'
        self.assertEqual(client_for(self.teacher).get(url).status_code, 404)
        self.assertEqual(client_for(self.teacher).get(f'/api/v1/courses/{self.course.id}/students/not-a-uuid/progress/').status_code, 404)

    def test_only_the_courses_teacher(self):
        for user in (self.other_teacher, self.aziza, make('p1', User.Role.PARENT)):
            self.assertIn(client_for(user).get(self.url).status_code, (403, 404), user.username)
        mark = f'/api/v1/courses/{self.course.id}/students/{self.aziza.pk}/payments/2026-01/'
        self.assertIn(client_for(self.aziza).put(mark, {}, format='json').status_code, (403, 404))
        self.assertEqual(CoursePayment.objects.count(), 0)

    def test_constant_number_of_queries(self):
        for index in range(8):
            student = make(f'extra{index}', User.Role.STUDENT)
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        client = client_for(self.teacher)
        client.get(self.url)  # isitish
        with self.assertNumQueries(10):
            self.assertEqual(client.get(self.url).status_code, 200)


class ReportedBugsTests(APITestCase):
    """Frontend topgan xatolar: noto'g'ri UUID 500 emas 400; filtrlar sahifalashda yo'qolmasin; remind-child xato formati."""

    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.child = make('c1', User.Role.STUDENT)
        ParentChildLink.objects.create(parent=self.parent, student=self.child, status=ParentChildLink.Status.APPROVED)
        self.teacher = make('t1', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Ingliz')
        Enrollment.objects.create(course=self.course, student=self.child, status=Enrollment.Status.APPROVED)
        self.hw = Assignment.objects.create(course=self.course, title='Essay', status=Assignment.Status.ACTIVE)

    def test_rank_with_garbage_course_is_400(self):
        response = client_for(self.parent).get(f'/api/v1/analytics/child/{self.child.pk}/rank/', {'course': 'abc'})
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(response.json()['success'])

    def test_rank_with_valid_uuid_still_works(self):
        response = client_for(self.parent).get(f'/api/v1/analytics/child/{self.child.pk}/rank/', {'course': str(self.course.pk)})
        self.assertEqual(response.status_code, 200, response.content)

    def test_remind_child_garbage_student_is_400(self):
        response = client_for(self.parent).post(f'/api/v1/homework/assignments/{self.hw.pk}/remind-child/', {'student': 'abc'}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()['error']['code'], 'invalid')

    def test_logins_with_garbage_student_is_400(self):
        response = client_for(self.parent).get('/api/v1/auth/logins/', {'student': 'abc'})
        self.assertEqual(response.status_code, 400, response.content)

    def test_remind_child_missing_student_uses_standard_error_format(self):
        response = client_for(self.parent).post(f'/api/v1/homework/assignments/{self.hw.pk}/remind-child/', {}, format='json')
        body = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual((body['success'], body['error']['code']), (False, 'invalid'))
        self.assertIn('student', body['error']['details'])

    def test_login_pagination_links_keep_filters(self):
        from apps.core.models import AuditLog

        chrome = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        for _index in range(3):
            AuditLog.objects.create(actor=self.parent, action='auth.login', ip_address='10.0.0.1', meta={'user_agent': chrome})
        client = client_for(self.parent)
        first = client.get('/api/v1/auth/logins/', {'page': 1, 'page_size': 1, 'from': '2020-01-01', 'device': 'computer'}).json()
        self.assertEqual(first['count'], 3)
        for filter_part in ('from=2020-01-01', 'device=computer', 'page=2', 'page_size=1'):
            self.assertIn(filter_part, first['next'])
        self.assertIsNone(first['previous'])
        second = client.get(first['next'].replace('http://testserver', '')).json()
        self.assertIn('device=computer', second['previous'])
        self.assertIn('page=1', second['previous'])
        self.assertEqual(len(second['results']), 1)
