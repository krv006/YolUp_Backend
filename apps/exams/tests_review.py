"""Imtihon natijasida savol-savol tahlil: o'quvchi javobi, to'g'ri javob, ball. Imtihon tugamaguncha o'quvchiga yopiq."""
from .tests import ExamTestBase


class ExamReviewTests(ExamTestBase):
    def finished_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])  # A bo'lim: 1 ta to'g'ri, 2-savol javobsiz
        self.shift(exam['id'], 18)
        self.save(exam['id'], self.answers_for(self.qb, correct=False))  # B bo'lim: hammasi xato
        return exam

    def ielts_exam(self):
        quizzes = {k: self.quiz(count=1) for k in ('listening', 'reading', 'writing')}
        exam = self.create_exam('ielts', [{'key': k, 'quiz': q} for k, q in quizzes.items()]).json()
        self.shift(exam['id'], 5)
        self.save(exam['id'], self.answers_for(quizzes['listening']))
        self.shift(exam['id'], 35)
        self.save(exam['id'], self.answers_for(quizzes['reading']))
        self.shift(exam['id'], 100)
        return exam, quizzes

    def detail(self, exam_id, token):
        self.auth(token)
        resp = self.client.get(f'/api/v1/exams/{exam_id}/results/{self.child_id}/')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_the_student_gets_no_review_while_the_exam_is_still_running(self):
        exam = self.finished_exam()
        self.assertNotIn('review', self.detail(exam['id'], self.child_token))

    def test_after_the_exam_the_student_sees_every_question_with_the_right_answer(self):
        exam = self.finished_exam()
        self.shift(exam['id'], 40)
        review = self.detail(exam['id'], self.child_token)['review']
        self.assertEqual(len(review), 4)
        first = review[0]
        self.assertEqual((first['section'], first['number'], first['is_correct']), ('a', 1, True))
        self.assertEqual(first['correct_answer'], "to'g'ri")
        unanswered = review[1]
        self.assertEqual((unanswered['given'], unanswered['is_correct'], unanswered['earned']), (None, False, 0.0))
        self.assertEqual(unanswered['correct_answer'], "to'g'ri")  # javob bermagan bo'lsa ham to'g'risi ko'rsatiladi
        wrong = review[2]
        self.assertEqual((wrong['given'], wrong['is_correct']), ('xato', False))

    def test_the_teacher_sees_the_review_at_any_time(self):
        exam = self.finished_exam()
        self.assertEqual(len(self.detail(exam['id'], self.teacher_token)['review']), 4)

    def test_a_student_cannot_open_a_classmates_review(self):
        exam = self.finished_exam()
        self.shift(exam['id'], 40)
        self.auth(self.outsider_token)
        resp = self.client.get(f'/api/v1/exams/{exam["id"]}/results/{self.child_id}/')
        self.assertIn(resp.status_code, (403, 404))

    def test_manual_sections_and_essays_are_not_part_of_the_review(self):
        exam, quizzes = self.ielts_exam()
        self.shift(exam['id'], 200)
        review = self.detail(exam['id'], self.teacher_token)['review']
        self.assertNotIn('writing', {row['section'] for row in review})
