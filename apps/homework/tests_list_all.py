"""`GET /homework/assignments/` kurs ko'rsatilmasa — hamma kurslarning vazifalari bitta so'rovda (web 6 ta so'rov yubormasin)."""
from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

from .tests_hardening import HomeworkBase, make


class ListAllAssignmentsTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.course2 = Course.objects.create(teacher=self.teacher, title='Algebra · 8-sinf', subject=Course.Subject.MATH)
        self.first = self.assignment(title='Birinchi')
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course2.id), 'title': 'Ikkinchi'}, format='json')
        self.second = resp.data['id']

    def ids(self, user, query=''):
        data = self.api(user).get(f'/api/v1/homework/assignments/{query}')
        self.assertEqual(data.status_code, 200, data.content)
        return [row['id'] for row in data.json()]

    def test_teacher_gets_all_courses_in_one_list_newest_first(self):
        self.assertEqual(self.ids(self.teacher), [self.second, self.first])

    def test_course_filter_is_unchanged(self):
        self.assertEqual(self.ids(self.teacher, f'?course={self.course.id}'), [self.first])
        self.assertEqual(self.ids(self.teacher, f'?course={self.course2.id}'), [self.second])

    def test_rows_carry_the_course_and_teacher_stats(self):
        rows = {row['id']: row for row in self.api(self.teacher).get('/api/v1/homework/assignments/').json()}
        self.assertEqual((rows[self.first]['course_id'], rows[self.second]['course_title']), (str(self.course.id), 'Algebra · 8-sinf'))
        self.assertIn('submissions_count', rows[self.first])

    def test_student_sees_only_his_own_courses_and_active_ones(self):
        self.assertEqual(self.ids(self.student), [self.first])  # course2 ga yozilmagan
        Enrollment.objects.create(course=self.course2, student=self.student, status=Enrollment.Status.APPROVED)
        self.assertEqual(self.ids(self.student), [self.second, self.first])
        draft = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Qoralama', 'status': 'draft'}, format='json').data['id']
        self.assertNotIn(draft, self.ids(self.student))  # qoralama o'quvchiga ko'rinmaydi
        self.assertIn(draft, self.ids(self.teacher))

    def test_parent_sees_the_childs_courses(self):
        self.assertEqual(self.ids(self.parent), [self.first])

    def test_other_teacher_gets_nothing_and_admin_stays_forbidden(self):
        stranger = make('t2', User.Role.TEACHER)
        self.assertEqual(self.ids(stranger), [])
        admin = make('adm1', User.Role.ADMIN)
        self.assertEqual(self.api(admin).get('/api/v1/homework/assignments/').status_code, 403)  # admin'ga bu bo'lim yopiq (avvalgidek)

    def test_unknown_or_forbidden_single_course_still_errors(self):
        stranger = make('t3', User.Role.TEACHER)
        self.assertEqual(self.api(stranger).get(f'/api/v1/homework/assignments/?course={self.course.id}').status_code, 403)
