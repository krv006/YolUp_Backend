"""Profil maydonlari, parolni o'zgartirish, profil ko'rsatkichlari va o'qituvchining o'quvchi hisobi yaratishi."""
from datetime import date

from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


class ProfileFieldsTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.client.force_authenticate(self.teacher)

    def patch(self, **data):
        return self.client.patch('/api/v1/auth/me/', data, format='json')

    def test_new_profile_fields_are_saved_and_returned(self):
        resp = self.patch(
            middle_name='Alisher o‘g‘li', birth_date='1990-05-14', email='  Mirkamol@YolUp.uz ', subject='math',
            city='Toshkent', bio='8 yillik tajriba', experience_years=8,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = self.client.get('/api/v1/auth/me/').json()
        self.assertEqual(
            (body['middle_name'], body['birth_date'], body['email'], body['subject'], body['city'], body['bio'], body['experience_years']),
            ('Alisher o‘g‘li', '1990-05-14', 'mirkamol@yolup.uz', 'math', 'Toshkent', '8 yillik tajriba', 8),
        )

    def test_invalid_values_are_refused(self):
        for bad in (
            {'subject': 'nonsense'}, {'birth_date': '1850-01-01'}, {'birth_date': '2999-01-01'},
            {'experience_years': 99}, {'experience_years': -1}, {'email': 'not-an-email'}, {'bio': 'x' * 1001},
        ):
            self.assertEqual(self.patch(**bad).status_code, 400, bad)

    def test_fields_can_be_cleared(self):
        self.patch(city='Toshkent', experience_years=5, email='a@b.uz', subject='math')
        resp = self.patch(city='', experience_years=None, email='', subject='')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['city'], body['experience_years'], body['email'], body['subject']), ('', None, '', ''))

    def test_read_only_and_old_fields_keep_working(self):
        resp = self.patch(parent_phone='+998900000000', password_changed_at='2020-01-01T00:00:00Z', first_name='Ali', phone='+998901112233')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['parent_phone'], body['password_changed_at'], body['first_name'], body['phone']), ('', None, 'Ali', '+998901112233'))

    def test_private_fields_are_not_in_the_public_user_serializer(self):
        from apps.accounts.serializers import UserSerializer

        self.patch(email='a@b.uz', bio='maxfiy', city='Toshkent')
        data = UserSerializer(User.objects.get(username='t1')).data
        for key in ('email', 'bio', 'city', 'birth_date', 'middle_name', 'parent_phone'):
            self.assertNotIn(key, data)


class PasswordChangeTests(APITestCase):
    def setUp(self):
        self.user = make('u1', User.Role.STUDENT)
        self.client.force_authenticate(self.user)

    def change(self, current=PASSWORD, new='NewStrongPass456!'):
        return self.client.post('/api/v1/auth/password/change/', {'current_password': current, 'new_password': new}, format='json')

    def test_password_is_changed_and_the_time_is_returned(self):
        resp = self.change()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['password_changed_at'])
        self.assertEqual(self.client.get('/api/v1/auth/me/').json()['password_changed_at'], resp.json()['password_changed_at'])
        fresh = APITestCaseClient()
        self.assertEqual(fresh.post('/api/v1/auth/login/', {'username': 'u1', 'password': 'NewStrongPass456!'}).status_code, 200)
        self.assertEqual(fresh.post('/api/v1/auth/login/', {'username': 'u1', 'password': PASSWORD}).status_code, 401)

    def test_wrong_current_password_weak_or_same_new_password(self):
        wrong = self.change(current='wrong')
        self.assertEqual(wrong.status_code, 400)
        self.assertIn("Joriy parol noto'g'ri", wrong.content.decode())
        self.assertEqual(self.change(new='123').status_code, 400)
        self.assertEqual(self.change(new=PASSWORD).status_code, 400)
        self.assertIsNone(User.objects.get(username='u1').password_changed_at)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.change().status_code, 401)


def APITestCaseClient():
    from rest_framework.test import APIClient

    return APIClient()


class MeStatsTests(APITestCase):
    def test_teacher_numbers(self):
        teacher = make('t1', User.Role.TEACHER, experience_years=8)
        first = Course.objects.create(teacher=teacher, title='A')
        second = Course.objects.create(teacher=teacher, title='B')
        a, b, c = (make(name, User.Role.STUDENT) for name in ('s1', 's2', 's3'))
        for course, student, state in (
            (first, a, 'approved'), (first, b, 'approved'), (second, a, 'approved'), (second, c, 'pending'),
        ):
            Enrollment.objects.create(course=course, student=student, status=state)
        self.client.force_authenticate(teacher)
        self.assertEqual(self.client.get('/api/v1/auth/me/stats/').json(), {'groups': 2, 'students': 2, 'experience_years': 8})

    def test_student_numbers_and_login_required(self):
        teacher = make('t1', User.Role.TEACHER)
        student = make('s1', User.Role.STUDENT)
        Enrollment.objects.create(course=Course.objects.create(teacher=teacher, title='A'), student=student, status='approved')
        self.client.force_authenticate(student)
        self.assertEqual(self.client.get('/api/v1/auth/me/stats/').json(), {'groups': 1, 'students': 0, 'experience_years': None})
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/auth/me/stats/').status_code, 401)


class TeacherCreatesStudentTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.other = make('t2', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.foreign = Course.objects.create(teacher=self.other, title='Boshqa')

    def create(self, user, **extra):
        self.client.force_authenticate(user)
        data = {'first_name': 'Sardor', 'last_name': 'Aliyev', 'username': 'sardor.aliyev', 'password': PASSWORD, **extra}
        return self.client.post('/api/v1/auth/children/', data, format='json')

    def test_teacher_creates_the_account_and_adds_it_to_the_course(self):
        resp = self.create(self.teacher, parent_phone='+998901234567', course_id=str(self.course.id))
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['username'], body['parent_phone'], body['course_id']), ('sardor.aliyev', '+998901234567', str(self.course.id)))
        self.assertNotIn('password', body)
        student = User.objects.get(username='sardor.aliyev')
        self.assertEqual((student.role, student.parent_phone), (User.Role.STUDENT, '+998901234567'))
        enrollment = Enrollment.objects.get(course=self.course, student=student)
        self.assertEqual(enrollment.status, Enrollment.Status.APPROVED)

    def test_without_a_course_only_the_account_is_created(self):
        resp = self.create(self.teacher)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertNotIn('course_id', resp.json())
        self.assertFalse(Enrollment.objects.exists())

    def test_someone_elses_course_is_refused_and_no_account_is_left_behind(self):
        resp = self.create(self.teacher, course_id=str(self.foreign.id))
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(User.objects.filter(username='sardor.aliyev').exists())
        resp = self.create(self.teacher, course_id='11111111-1111-1111-1111-111111111111')
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(User.objects.filter(username='sardor.aliyev').exists())

    def test_bad_phone_is_refused(self):
        self.assertEqual(self.create(self.teacher, parent_phone='abc').status_code, 400)

    def test_parent_cannot_pick_a_course_but_still_creates_children(self):
        parent = make('p1', User.Role.PARENT)
        self.assertEqual(self.create(parent, course_id=str(self.course.id)).status_code, 400)
        self.assertFalse(User.objects.filter(username='sardor.aliyev').exists())
        self.assertEqual(self.create(parent, parent_phone='+998900000001').status_code, 201)

    def test_students_and_unapproved_teachers_cannot_create(self):
        student = make('s9', User.Role.STUDENT)
        self.assertEqual(self.create(student).status_code, 403)
        pending = make('t3', User.Role.TEACHER, is_approved=False)
        self.assertEqual(self.create(pending).status_code, 403)
