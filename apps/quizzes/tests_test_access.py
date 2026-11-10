"""Test yaratish (pullik xizmat) — admin foydalanuvchi bo'yicha yoqadi/o'chiradi; hozircha hammada yoqilgan (2026-11-10)."""
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.lessons.models import Course


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


QUIZ = {
    'topic': 'Algebra', 'title': 'T',
    'questions': [{'type': 'single', 'text': '2+2?', 'options': [{'text': '4', 'is_correct': True}, {'text': '5', 'is_correct': False}]}],
}


class TestAccessTests(APITestCase):
    def setUp(self):
        self.teacher = make('ta_t', User.Role.TEACHER)
        self.other = make('ta_t2', User.Role.TEACHER)
        self.admin = make('ta_admin', User.Role.ADMIN)
        self.student = make('ta_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='A')
        self.other_course = Course.objects.create(teacher=self.other, title='B')

    def api(self, user):
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=user.pk))  # har so'rovda bazadan (JWT'dagidek)
        return client

    def toggle(self, user, enabled, as_user=None):
        return self.api(as_user or self.admin).patch(f'/api/v1/admin/users/{user.id}/test-access/', {'enabled': enabled}, format='json')

    def create(self, user):
        course = self.course if user == self.teacher else self.other_course
        return self.api(user).post('/api/v1/quizzes/', {**QUIZ, 'course': str(course.id)}, format='json')

    def test_open_for_everyone_by_default(self):
        self.assertTrue(self.api(self.teacher).get('/api/v1/auth/me/').json()['can_create_tests'])
        self.assertNotEqual(self.create(self.teacher).status_code, 403)

    def test_admin_closes_and_reopens_creation_for_one_teacher(self):
        resp = self.toggle(self.teacher, False)
        self.assertEqual((resp.status_code, resp.json()['can_create_tests']), (200, False))
        locked = self.create(self.teacher)
        self.assertEqual(locked.status_code, 403)
        self.assertIn('yoqilmagan', str(locked.json()))
        # boshqa o'qituvchiga ta'sir qilmaydi
        self.assertNotEqual(self.create(self.other).status_code, 403)
        # hamma yaratish yo'llari yopiladi, o'qish (GET) — yo'q
        for path in ('import/', 'ai-generate/', 'ai-generate/mini/', 'ai-generate/bank/', 'import-google-doc/', 'import-google-form/'):
            self.assertEqual(self.api(self.teacher).post(f'/api/v1/quizzes/{path}', {}, format='json').status_code, 403, path)
        self.assertEqual(self.api(self.teacher).get('/api/v1/quizzes/').status_code, 200)
        self.assertEqual(self.api(self.teacher).get('/api/v1/quizzes/ai-generate/').status_code, 200)
        self.assertFalse(self.api(self.teacher).get('/api/v1/auth/me/').json()['can_create_tests'])
        self.assertTrue(self.toggle(self.teacher, True).json()['can_create_tests'])
        self.assertNotEqual(self.create(self.teacher).status_code, 403)

    def test_only_admin_can_toggle_and_input_is_validated(self):
        self.assertEqual(self.toggle(self.other, False, as_user=self.teacher).status_code, 403)
        self.assertEqual(self.toggle(self.other, False, as_user=self.student).status_code, 403)
        self.assertEqual(self.api(self.admin).patch(f'/api/v1/admin/users/{self.other.id}/test-access/', {'enabled': 'no'}, format='json').status_code, 400)
        self.assertEqual(self.api(self.admin).patch(f'/api/v1/admin/users/{self.student.id}/test-access/', {'enabled': False}, format='json').status_code, 404)
        self.assertEqual(self.api(self.admin).patch('/api/v1/admin/users/00000000-0000-0000-0000-000000000000/test-access/', {'enabled': False}, format='json').status_code, 404)

    def test_admin_teacher_list_shows_the_flag(self):
        self.toggle(self.other, False)
        rows = self.api(self.admin).get('/api/v1/auth/teachers/').json()
        rows = rows['results'] if isinstance(rows, dict) else rows
        by_name = {r['username']: r['can_create_tests'] for r in rows}
        self.assertEqual((by_name['ta_t'], by_name['ta_t2']), (True, False))
