"""Mock imtihon: guruh o'rtachasi, ro'yxatda o'z natijam, rasm, PDF, xatolar ustida AI mashq; maqsad ball va interfeys sozlamalari."""
from unittest import mock

from .tests import ExamTestBase


class ExamStudentExtrasTests(ExamTestBase):
    def finished_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])
        self.shift(exam['id'], 18)
        self.save(exam['id'], self.answers_for(self.qb, correct=False))
        self.shift(exam['id'], 40)
        return exam

    def test_group_average_and_student_avatar_in_results(self):
        exam = self.finished_exam()
        body = self.results(exam['id'], self.child_token).json()
        self.assertEqual(body['group_average'], 25.0)
        self.assertIn('avatar', body['results'][0]['student'])

    def test_group_average_is_none_while_exam_is_running(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.assertIsNone(self.results(exam['id'], self.teacher_token).json()['group_average'])

    def test_my_total_in_exam_list_for_students_only(self):
        exam = self.finished_exam()
        self.auth(self.child_token)
        row = next(r for r in self.client.get('/api/v1/exams/').json() if r['id'] == exam['id'])
        self.assertEqual(row['my_total']['score'], 25.0)
        self.auth(self.teacher_token)
        teacher_row = next(r for r in self.client.get('/api/v1/exams/').json() if r['id'] == exam['id'])
        self.assertNotIn('my_total', teacher_row)

    def test_result_pdf_for_student_and_teacher(self):
        exam = self.finished_exam()
        student_id = self.results(exam['id'], self.teacher_token).json()['results'][0]['student']['id']
        for token in (self.child_token, self.teacher_token):
            self.auth(token)
            response = self.client.get(f"/api/v1/exams/{exam['id']}/results/{student_id}/pdf/")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(response.content.startswith(b'%PDF'))

    def test_pdf_hidden_until_exam_ends(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])
        student_id = self.results(exam['id'], self.teacher_token).json()['results'][0]['student']['id']
        self.auth(self.child_token)
        self.assertEqual(self.client.get(f"/api/v1/exams/{exam['id']}/results/{student_id}/pdf/").status_code, 400)

    def test_mistakes_practice_uses_wrong_questions_and_ai(self):
        exam = self.finished_exam()
        fake = {'questions': [{'text': 'Yangi savol', 'options': ['a', 'b'], 'correct_index': 1, 'explanation': 'chunki'}]}
        self.auth(self.child_token)
        with mock.patch('apps.quizzes.llm.enabled', return_value=True), mock.patch('apps.quizzes.llm.chat_json', return_value=fake) as call:
            response = self.client.post(f"/api/v1/exams/{exam['id']}/mistakes-practice/", {'count': 3}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['questions'][0]['correct_index'], 1)
        self.assertIn('Material / mistakes', call.call_args.args[1])

    def test_mistakes_practice_needs_results_to_be_visible(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])
        self.auth(self.child_token)
        self.assertEqual(self.client.post(f"/api/v1/exams/{exam['id']}/mistakes-practice/", {}, format='json').status_code, 400)


class ProfilePrefsTests(ExamTestBase):
    def test_target_band_and_interface_settings(self):
        self.auth(self.child_token)
        response = self.client.patch('/api/v1/auth/me/', {'target_band': 7.5, 'theme': 'dark', 'text_size': 'large'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        me = self.client.get('/api/v1/auth/me/').json()
        self.assertEqual((me['target_band'], me['theme'], me['text_size']), (7.5, 'dark', 'large'))

    def test_validation(self):
        self.auth(self.child_token)
        self.assertEqual(self.client.patch('/api/v1/auth/me/', {'theme': 'neon'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/v1/auth/me/', {'text_size': 'huge'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/v1/auth/me/', {'target_band': 5000}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/v1/auth/me/', {'target_band': None}, format='json').status_code, 200)
