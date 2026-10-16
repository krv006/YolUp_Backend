"""AI bilan IELTS Writing testi: reja insho (essay) bloklarini saqlaydi, zaxira yozilmaydi, savol min_words bilan yaratiladi."""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from . import ai_exam

TASK1 = ('The table below shows the percentage of households with internet access in four countries.\n\n'
         'Country | 2010 | 2020\nA | 40 | 90\nB | 25 | 70\n\nSummarise the information. Write at least 150 words.')
TASK2 = ('Some people think that modern technology isolates us from each other, while others believe it brings people '
         'closer together. Discuss both views and give your own opinion. Give reasons for your answer and include any '
         'relevant examples. Write at least 250 words.')

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


class FixedWritingPlanTests(SimpleTestCase):
    def test_ielts_writing_gets_the_official_two_task_plan_without_asking_the_ai(self):
        with patch('apps.quizzes.llm.chat_json') as chat:
            for name in ('IELTS Writing', 'ielts academic writing', 'Writing (IELTS)'):
                plan = ai_exam.plan_exam('', target_total=0, topic='Technology', exam_name=name)
                blocks = plan['sections'][0]['blocks']
                self.assertEqual([(b['type'], b['min_words']) for b in blocks], [('essay', 150), ('essay', 250)])
        chat.assert_not_called()

    def test_own_rules_still_go_through_the_planner(self):
        with patch('apps.quizzes.llm.chat_json', return_value={'sections': []}) as chat:
            ai_exam.plan_exam('My own writing rules', target_total=0, exam_name='IELTS Writing')
        chat.assert_called_once()

    def test_other_exams_are_not_affected(self):
        with patch('apps.quizzes.llm.chat_json', return_value={'sections': []}) as chat:
            ai_exam.plan_exam('', target_total=0, exam_name='IELTS Listening')
        chat.assert_called_once()


class EssayCompletenessTests(SimpleTestCase):
    FULL1 = TASK1 + ' The table is about internet access in four countries between 2010 and 2020.'
    SHORT = 'Summarise the information below. Write at least 150 words.'

    def run_section(self, replies):
        calls = []

        def fake(system, user, **kwargs):
            calls.append(json.loads(user))
            return replies[min(len(calls), len(replies)) - 1]

        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            result = ai_exam.generate_section(PLAN, 0, '', avoid_topics=[])
        return result, calls

    def test_a_bare_instruction_line_triggers_one_retry_and_the_full_task_is_kept(self):
        bad = {'passage': '', 'questions': [{'kind': 'essay', 'text': self.SHORT, 'block': 0},
                                            {'kind': 'essay', 'text': TASK2, 'block': 1}]}
        good = {'passage': '', 'questions': [{'kind': 'essay', 'text': self.FULL1, 'block': 0},
                                             {'kind': 'essay', 'text': TASK2 + ' ' + TASK2, 'block': 1}]}
        result, calls = self.run_section([bad, good])
        self.assertEqual(len(calls), 2)
        self.assertIn('problem', calls[1])
        self.assertIn('2010 and 2020', result['questions'][0]['text'])

    def test_complete_tasks_need_no_retry_and_the_block_instruction_is_not_glued_on(self):
        plan = json.loads(json.dumps(PLAN))
        plan['sections'][0]['blocks'][0]['instruction'] = 'Write at least 150 words.'
        good = {'passage': '', 'questions': [{'kind': 'essay', 'text': self.FULL1, 'block': 0},
                                             {'kind': 'essay', 'text': TASK2 + ' ' + TASK2, 'block': 1}]}
        with patch('apps.quizzes.llm.chat_json', return_value=good) as chat:
            result = ai_exam.generate_section(plan, 0, '', avoid_topics=[])
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(result['questions'][0]['text'], self.FULL1)
