"""Yangi dizayn: jonli imtihonda har o'quvchining progressi ("28 / 40 savol")."""
from .tests import ExamTestBase


class ExamProgressTests(ExamTestBase):
    def test_teacher_sees_answered_and_total_students_do_not(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])  # 4 savoldan 1 tasiga javob
        item = self.results(exam['id'], self.teacher_token).json()['results'][0]
        self.assertEqual((item['answered'], item['questions_total']), (1, 4))
        self.assertEqual(item['progress'], {'answered': 1, 'total': 4})
        self.assertIn('score', item['total'])  # ball hisobining `total` kaliti buzilmagan
        self.assertIn('away', item['integrity'])

        self.save(exam['id'], [self.answers_for(self.qa)[1]])
        again = self.results(exam['id'], self.teacher_token).json()['results'][0]
        self.assertEqual(again['progress'], {'answered': 2, 'total': 4})

        self.shift(exam['id'], 40)
        own = self.results(exam['id'], self.child_token).json()['results'][0]
        self.assertNotIn('progress', own)
        self.assertNotIn('answered', own)

    def test_participant_without_answers_has_zero_progress(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.current(exam['id'])  # urinish yaratiladi, hali javob yo'q
        results = self.results(exam['id'], self.teacher_token).json()['results']
        item = next(r for r in results if r.get('participated'))
        self.assertEqual(item['progress'], {'answered': 0, 'total': 4})
