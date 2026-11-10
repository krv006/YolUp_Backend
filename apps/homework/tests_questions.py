"""Uy vazifasi ichidagi savollar (2026-11-10): testlar avtomatik baholanadi, ochiq javoblarni AI yoki o'qituvchi baholaydi."""
from unittest.mock import patch

from django.test import override_settings

from apps.quizzes.tests_ai_exam import completion

from . import services
from .models import AssignmentQuestion, Submission, SubmissionAnswer
from .tests_hardening import HomeworkBase
from .tests_speaking_ai import LLM_ON

SINGLE = {'type': 'single', 'text': '2 + 2 = ?', 'options': ['3', '4', '5'], 'correct': [1], 'points': 2}
MULTIPLE = {'type': 'multiple', 'text': 'Tub sonlar?', 'options': ['2', '4', '5', '9'], 'correct': [0, 2], 'points': 3}
SHORT = {'type': 'short', 'text': 'Kvadrat tenglama nima?', 'points': 5}
LONG = {'type': 'long', 'text': "Diskriminant haqida yozing", 'points': 10}


class QuestionBase(HomeworkBase):
    def make(self, questions, **extra):
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Savollar', 'questions': questions, **extra}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.data

    def answer(self, assignment_id, answers, user=None):
        return self.api(user or self.student).post(
            f'/api/v1/homework/assignments/{assignment_id}/submit/', {'answers': answers}, format='json')

    def ids(self, assignment):
        return {q['type']: q['id'] for q in assignment['questions']}


class QuestionSetupTests(QuestionBase):
    def test_teacher_creates_questions_and_students_do_not_see_correct_answers(self):
        data = self.make([SINGLE, MULTIPLE, SHORT])
        self.assertEqual((data['has_questions'], data['questions_points']), (True, 10))
        self.assertEqual(data['questions'][0]['correct'], [1])
        student_view = self.api(self.student).get(f'/api/v1/homework/assignments/{data["id"]}/').json()
        self.assertTrue(all('correct' not in q for q in student_view['questions']))
        self.assertEqual([q['type'] for q in student_view['questions']], ['single', 'multiple', 'short'])
        teacher_view = self.api(self.teacher).get(f'/api/v1/homework/assignments/{data["id"]}/').json()
        self.assertEqual(teacher_view['questions'][1]['correct'], [0, 2])

    def test_validation(self):
        bad = [
            {'type': 'single', 'text': 'x', 'options': ['a'], 'correct': [0]},               # kam variant
            {'type': 'single', 'text': 'x', 'options': ['a', 'b'], 'correct': [0, 1]},       # bitta emas
            {'type': 'multiple', 'text': 'x', 'options': ['a', 'b'], 'correct': []},         # to'g'ri javob yo'q
            {'type': 'single', 'text': 'x', 'options': ['a', 'b'], 'correct': [5]},          # indeks chegaradan tashqari
            {'type': 'essay', 'text': 'x'},                                                  # noma'lum tur
            {'type': 'short', 'text': '  '},                                                 # bo'sh matn
            {'type': 'short', 'text': 'x', 'points': 0},
        ]
        for question in bad:
            resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
                'course_id': str(self.course.id), 'title': 'X', 'questions': [question]}, format='json')
            self.assertEqual(resp.status_code, 400, question)

    def test_questions_can_be_edited_until_the_first_submission(self):
        data = self.make([SHORT])
        url = f'/api/v1/homework/assignments/{data["id"]}/'
        ok = self.api(self.teacher).patch(url, {'questions': [SINGLE, SHORT]}, format='json')
        self.assertEqual((ok.status_code, len(ok.json()['questions'])), (200, 2))
        self.answer(data['id'], [{'question_id': ok.json()['questions'][1]['id'], 'answer': 'javob'}])
        self.assertEqual(self.api(self.teacher).patch(url, {'questions': [SHORT]}, format='json').status_code, 400)


class TestOnlyGradingTests(QuestionBase):
    def test_tests_are_graded_at_once_and_the_result_is_final(self):
        data = self.make([SINGLE, MULTIPLE])
        ids = self.ids(data)
        resp = self.answer(data['id'], [
            {'question_id': ids['single'], 'answer': [1]},          # to'g'ri: 2/2
            {'question_id': ids['multiple'], 'answer': [0, 1]},     # noto'g'ri: 0/3
        ])
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['status'], 'done')
        self.assertEqual(body['overall_score'], 40.0)  # 2/5 = 40%
        by_type = {a['type']: a for a in body['answers']}
        self.assertEqual((by_type['single']['score'], by_type['single']['is_correct']), (2.0, True))
        self.assertEqual((by_type['multiple']['score'], by_type['multiple']['is_correct']), (0.0, False))
        self.assertEqual(by_type['multiple']['correct'], [0, 2])  # natijada to'g'ri javob ko'rinadi
        self.assertEqual(body['files'], [])
        self.assertEqual(body['file_name'], '')

    def test_multiple_choice_is_all_or_nothing_and_unanswered_scores_zero(self):
        data = self.make([SINGLE, MULTIPLE])
        ids = self.ids(data)
        body = self.answer(data['id'], [{'question_id': ids['multiple'], 'answer': [2, 0]}]).json()  # to'g'ri, tartibsiz
        self.assertEqual(body['overall_score'], 60.0)  # 3/5
        by_type = {a['type']: a for a in body['answers']}
        self.assertEqual(by_type['single']['score'], 0.0)

    def test_answer_validation(self):
        data = self.make([SINGLE, SHORT])
        ids = self.ids(data)
        for answers in (
            [{'question_id': ids['single'], 'answer': [7]}],                         # variant yo'q
            [{'question_id': ids['single'], 'answer': [0, 1]}],                      # single: bittadan ko'p
            [{'question_id': '00000000-0000-0000-0000-000000000000', 'answer': [0]}],
            [{'question_id': ids['single'], 'answer': [0]}, {'question_id': ids['single'], 'answer': [1]}],
        ):
            self.assertEqual(self.answer(data['id'], answers).status_code, 400, answers)
        self.assertEqual(self.answer(data['id'], []).status_code, 400)  # javob ham, fayl ham yo'q
        plain = self.assignment()
        self.assertEqual(self.answer(plain, [{'question_id': ids['single'], 'answer': [0]}]).status_code, 400)  # savolsiz vazifa

    def test_file_is_optional_but_still_accepted_with_questions(self):
        data = self.make([SINGLE])
        ids = self.ids(data)
        from .tests import pdf_upload

        resp = self.api(self.student).post(
            f'/api/v1/homework/assignments/{data["id"]}/submit/',
            {'file': pdf_upload(), 'answers': '[{"question_id": "%s", "answer": [1]}]' % ids['single']},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(len(resp.json()['files']), 1)
        self.assertEqual(resp.json()['overall_score'], 100.0)


class OpenAnswerTests(QuestionBase):
    def open_assignment(self, **extra):
        data = self.make([SINGLE, SHORT, LONG], **extra)
        return data, self.ids(data)

    def submit_mixed(self, data, ids):
        return self.answer(data['id'], [
            {'question_id': ids['single'], 'answer': [1]},                       # 2/2
            {'question_id': ids['short'], 'answer': 'ax^2+bx+c=0 ko\'rinishidagi tenglama'},
            {'question_id': ids['long'], 'answer': 'D = b^2 - 4ac'},
        ])

    def test_open_answers_wait_for_the_teacher_who_scores_each_answer(self):
        data, ids = self.open_assignment(ai_check=False)
        body = self.submit_mixed(data, ids).json()
        self.assertEqual(body['status'], 'pending_review')
        sub = Submission.objects.get(pk=body['id'])
        self.assertEqual(sub.overall_score, round(2 * 100 / 17, 1))  # ochiq javoblar hozircha 0
        review = self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub.id}/review/', {
            'answer_scores': {ids['short']: 4, ids['long']: 8}, 'teacher_comment': 'Yaxshi',
        }, format='json')
        self.assertEqual(review.status_code, 200, review.content)
        out = review.json()
        self.assertEqual(out['status'], 'done')
        self.assertEqual(out['overall_score'], round(14 * 100 / 17, 1))  # (2 + 4 + 8) / 17 = 82.4%
        self.assertEqual({a['type']: a['score'] for a in out['answers']}, {'single': 2.0, 'short': 4.0, 'long': 8.0})

    def test_score_above_points_is_rejected(self):
        data, ids = self.open_assignment(ai_check=False)
        sub_id = self.submit_mixed(data, ids).json()['id']
        bad = self.api(self.teacher).post(
            f'/api/v1/homework/submissions/{sub_id}/review/', {'answer_scores': {ids['short']: 99}}, format='json')
        self.assertEqual(bad.status_code, 400)

    @override_settings(**LLM_ON)
    def test_ai_grades_open_answers_and_merges_with_the_test_score(self):
        data, ids = self.open_assignment(ai_check=True)
        ai = {
            'overall_score': 60,
            'questions': [
                {'question_number': 1, 'question': 'Q1', 'student_answer': 'a', 'analysis': 'ok', 'score': 80},    # 5 ball * 0.8 = 4
                {'question_number': 2, 'question': 'Q2', 'student_answer': 'b', 'analysis': 'ok', 'score': 40},    # 10 ball * 0.4 = 4
            ],
            'summary': {'strengths': [], 'weaknesses': [], 'topics_to_review': [], 'recommendations': []},
        }
        with patch('apps.quizzes.llm.requests.post', return_value=completion(ai)) as post:
            body = self.submit_mixed(data, ids).json()
            self.assertEqual(body['status'], 'pending_review')  # AI ishlayapti: o'quvchiga "kutilmoqda"
            self.assertEqual(post.call_count, 0)  # so'rov ichida AI chaqirilmaydi
            self.assertEqual(services.sync_ai_results(), {'done': 1, 'failed': 0, 'waiting': 0})
        prompt = post.call_args[1]['json']['messages'][1]['content']
        self.assertIn('Kvadrat tenglama nima?', prompt)
        self.assertIn("D = b^2 - 4ac", prompt)
        self.assertNotIn('2 + 2', prompt)  # testlar AI'ga yuborilmaydi
        sub = Submission.objects.get(pk=body['id'])
        self.assertEqual(sub.status, 'pending_review')
        scores = {a.question.type: (a.auto_score, a.ai_score, a.final_score) for a in SubmissionAnswer.objects.filter(submission=sub)}
        self.assertEqual(scores['single'], (2.0, None, 2.0))
        self.assertEqual(scores['short'], (None, 4.0, 4.0))
        self.assertEqual(scores['long'], (None, 4.0, 4.0))
        self.assertEqual(sub.overall_score, round(10 * 100 / 17, 1))  # (2 + 4 + 4) / 17
        # o'quvchi tasdiqlanmaguncha AI ballini ko'rmaydi
        hidden = self.api(self.student).get(f'/api/v1/homework/submissions/{sub.id}/').json()
        self.assertEqual(hidden['answers'], [])
        shown = self.api(self.teacher).get(f'/api/v1/homework/submissions/{sub.id}/').json()
        self.assertEqual({a['type']: a['ai_score'] for a in shown['answers']}['short'], 4.0)

    def test_no_ai_means_the_teacher_grades_open_answers(self):
        data, ids = self.open_assignment(ai_check=True)  # AI sozlanmagan (OPENAI_API_KEY yo'q)
        body = self.submit_mixed(data, ids).json()
        self.assertEqual(body['status'], 'pending_review')
        self.assertEqual(AssignmentQuestion.objects.filter(assignment_id=data['id']).count(), 3)
