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
        self.assertEqual(own['min_words'], 250)  # blokdagi minimum ustun (model adashmasin)
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


class TaskOneNeedsDataTests(SimpleTestCase):
    """IELTS Writing: Task 1 da ma'lumot jadvali bo'lishi shart, tartib Task 1 -> Task 2."""

    TABLE = ('The table shows internet access in four countries.\n\nCountry | 2010 | 2020\nA | 40 | 90\nB | 25 | 70\n'
             'C | 10 | 55\n\nSummarise the information by selecting and reporting the main features. Write at least 150 words.')

    def plan(self):
        return ai_exam.ielts_writing_plan()

    def run_section(self, replies):
        calls = []

        def fake(system, user, **kwargs):
            calls.append(json.loads(user))
            return replies[min(len(calls), len(replies)) - 1]

        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            result = ai_exam.generate_section(self.plan(), 0, '', avoid_topics=[])
        return result, calls

    def test_the_fixed_plan_tells_the_writer_which_block_is_which_task(self):
        blocks = self.plan()['sections'][0]['blocks']
        self.assertIn('TASK 1', blocks[0]['instruction'])
        self.assertIn('TASK 2', blocks[1]['instruction'])
        self.assertTrue(blocks[0]['data_table'] and not blocks[1].get('data_table'))

    def test_a_task_one_without_a_table_is_asked_again_and_the_order_is_kept(self):
        no_table = {'passage': '', 'questions': [
            {'kind': 'essay', 'text': TASK2 + ' ' + TASK2, 'block': 0}, {'kind': 'essay', 'text': TASK2, 'block': 1}]}
        good = {'passage': '', 'questions': [
            {'kind': 'essay', 'text': self.TABLE, 'block': 0}, {'kind': 'essay', 'text': TASK2, 'block': 1}]}
        result, calls = self.run_section([no_table, good])
        self.assertEqual(len(calls), 2)
        self.assertIn('table rows', calls[1]['problem'])
        self.assertEqual([(q['min_words'], '|' in q['text']) for q in result['questions']], [(150, True), (250, False)])

    def test_a_good_answer_needs_no_retry(self):
        good = {'passage': '', 'questions': [
            {'kind': 'essay', 'text': self.TABLE, 'block': 0}, {'kind': 'essay', 'text': TASK2, 'block': 1}]}
        result, calls = self.run_section([good])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result['questions']), 2)

    def test_markers_missing_falls_back_to_order(self):
        good = {'passage': '', 'questions': [{'kind': 'essay', 'text': self.TABLE}, {'kind': 'essay', 'text': TASK2}]}
        _result, calls = self.run_section([good])
        self.assertEqual(len(calls), 1)


class WritingModelTests(SimpleTestCase):
    def test_a_separate_writing_model_is_used_when_configured(self):
        from django.test import override_settings

        from . import ielts_writing

        criteria = {k: {'band': 6, 'comment': 'c', 'evidence': ''} for k in ('task', 'coherence', 'lexical', 'grammar')}
        reply = {'task': 2, 'criteria': criteria}
        for configured, expected in (('', ''), ('gpt-strong', 'gpt-strong')):
            with override_settings(OPENAI_WRITING_MODEL=configured), \
                    patch('apps.quizzes.llm.chat_json', return_value=reply) as chat:
                ielts_writing.evaluate('word ' * 260, prompt='x', minimum=250)
            self.assertEqual(chat.call_args.kwargs['model'], expected)

    def test_the_post_uses_the_given_model_else_the_default(self):
        from django.test import override_settings

        from . import llm

        class Ok:
            status_code = 200
            text = '{}'
            headers = {}

            def json(self):
                return {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}

        with override_settings(OPENAI_API_KEY='k', OPENAI_MODEL='default-model'), \
                patch('apps.quizzes.llm.requests.post', return_value=Ok()) as post:
            llm._post([{'role': 'user', 'content': 'x'}], 10)
            llm._post([{'role': 'user', 'content': 'x'}], 10, 'other-model')
        self.assertEqual([c.kwargs['json']['model'] for c in post.call_args_list], ['default-model', 'other-model'])

    def test_the_grader_prompt_forbids_false_corrections(self):
        from . import ielts_writing

        for phrase in ('List ONLY mistakes you are certain about', 'correction is itself correct', 'an empty list is fine'):
            self.assertIn(phrase, ielts_writing._SYSTEM)
