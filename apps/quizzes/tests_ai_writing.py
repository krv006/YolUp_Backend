"""AI bilan IELTS Writing testi: reja insho (essay) bloklarini saqlaydi, zaxira yozilmaydi, savol min_words bilan yaratiladi."""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from . import ai_exam

TASK1 = ('The table below shows the percentage of households with internet access in four countries.\n\n'
         'Country | 2010 | 2020\nA | 40 | 90\nB | 25 | 70\n\nSummarise the information. Write at least 150 words.')
TASK2 = 'Some people think technology isolates us. Discuss both views and give your opinion. Write at least 250 words.'

PLAN = {
    'exam_name': 'IELTS Writing', 'language': 'en', 'rules': [],
    'sections': [{'title': 'Writing', 'passage': None, 'audio': None, 'focus': '', 'blocks': [
        {'type': 'essay', 'count': 1, 'instruction': '', 'options': 4, 'points': 9, 'min_words': 150},
        {'type': 'essay', 'count': 1, 'instruction': '', 'options': 4, 'points': 9, 'min_words': 250},
    ]}],
}


class EssayPlanTests(SimpleTestCase):
    def test_the_planner_keeps_essay_blocks_and_their_word_minimum(self):
        raw = {'exam_name': 'IELTS Writing', 'sections': [{'title': 'Writing', 'passage': None, 'blocks': [
            {'type': 'essay', 'count': 1, 'points': 9, 'min_words': 150},
            {'type': 'essay', 'count': 1, 'points': 9, 'min_words': 250}]}]}
        plan = ai_exam.normalize_plan(raw, fallback_count=20)
        self.assertEqual([(b['type'], b['min_words']) for b in plan['sections'][0]['blocks']],
                         [('essay', 150), ('essay', 250)])

    def test_the_planner_prompt_allows_writing_but_not_speaking(self):
        self.assertIn('WRITING section only when the exam or the rules call for it', ai_exam._PLANNER_SYSTEM)
        self.assertIn('never plan Speaking', ai_exam._PLANNER_SYSTEM)
        self.assertIn('plain-text table', ai_exam._WRITER_SYSTEM)  # Task 1 ma'lumoti rasm emas, matn jadvali
        self.assertIn('at least 150 words', ai_exam._WRITER_SYSTEM)

    def test_an_essay_converts_to_a_question_with_the_blocks_minimum(self):
        question = ai_exam._to_question({'kind': 'essay', 'text': TASK2}, points=9, min_words=250)
        self.assertEqual((question['type'], question['min_words'], question['points']), ('essay', 250, 9))
        own = ai_exam._to_question({'kind': 'essay', 'text': TASK1, 'min_words': 150}, points=9, min_words=250)
        self.assertEqual(own['min_words'], 150)  # modelning o'z qiymati ustun
        self.assertIsNone(ai_exam._to_question({'kind': 'essay', 'text': '  '}, points=9))

    def test_an_essay_passes_the_real_question_validation_without_any_answer_key(self):
        question = ai_exam._to_question({'kind': 'essay', 'text': TASK2}, points=9, min_words=250)
        self.assertIsNotNone(ai_exam._validated(question))


@override_settings(AI_EXAM_JUDGE=True)
class EssaySectionTests(SimpleTestCase):
    def write(self, questions):
        calls = []

        def fake(system, user, **kwargs):
            calls.append(system)
            return {'passage': '', 'questions': questions}

        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            result = ai_exam.generate_section(PLAN, 0, '', avoid_topics=[])
        return result, calls

    def test_two_tasks_become_two_essay_questions_in_order_with_no_spares_and_no_judge_call(self):
        result, calls = self.write([
            {'kind': 'essay', 'text': TASK1, 'min_words': 150, 'block': 0},
            {'kind': 'essay', 'text': TASK2, 'min_words': 250, 'block': 1},
            {'kind': 'essay', 'text': 'extra spare', 'block': 1},
        ])
        self.assertEqual([(q['type'], q['min_words'], q['block']) for q in result['questions']],
                         [('essay', 150, 0), ('essay', 250, 1)])
        self.assertEqual((result['dropped'], result['missing']), (0, 0))
        self.assertEqual(len(calls), 1)  # insholar uchun AI tekshiruvchi chaqirilmaydi

    def test_the_writer_is_told_not_to_write_spares_for_essays(self):
        sent = {}

        def fake(system, user, **kwargs):
            sent.update(json.loads(user))
            return {'passage': '', 'questions': []}

        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            ai_exam.generate_section(PLAN, 0, '', avoid_topics=[])
        self.assertEqual([b['spare'] for b in sent['section_spec']['blocks']], [0, 0])

    def test_a_missing_essay_is_reported(self):
        result, _ = self.write([{'kind': 'essay', 'text': TASK1, 'block': 0}])
        self.assertEqual(result['missing'], 1)
