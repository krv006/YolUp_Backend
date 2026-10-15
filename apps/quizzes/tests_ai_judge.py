"""Bo'limdan keyin AI tekshiruvi (judge): manbaga zid/noaniq savollar tashlanadi, zaxira o'rniga keladi, xato bo'lsa jim o'tadi."""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from . import ai_exam, llm

PASSAGE = 'Honeybees are social insects that live in large colonies with one queen. ' * 4


def mcq(text, block=0, answer=0):
    return {'kind': 'mcq', 'text': text, 'options': ['a', 'b', 'c'], 'answer': answer, 'block': block}


PLAN = {
    'exam_name': 'X', 'language': 'en', 'rules': [],
    'sections': [{'title': 'S1', 'passage': {'min_words': 10, 'max_words': 400}, 'focus': '', 'blocks': [
        {'type': 'mcq', 'count': 2, 'instruction': '', 'options': 3, 'points': 1}]}],
}


class FakeChat:
    """Birinchi chaqiruv - yozuvchi, ikkinchisi - tekshiruvchi."""

    def __init__(self, questions, verdicts=None, judge_error=None):
        self.questions, self.verdicts, self.judge_error = questions, verdicts, judge_error
        self.calls = []

    def __call__(self, system, user, **kwargs):
        self.calls.append((system, json.loads(user)))
        if system is ai_exam._JUDGE_SYSTEM:
            if self.judge_error:
                raise self.judge_error
            return {'verdicts': self.verdicts or []}
        return {'passage': PASSAGE, 'questions': self.questions}


def ok(*ids):
    return [{'id': i, 'ok': True, 'problem': ''} for i in ids]


def bad(i, problem='answer not in passage'):
    return {'id': i, 'ok': False, 'problem': problem}


@override_settings(AI_EXAM_JUDGE=True)
class JudgeTests(SimpleTestCase):
    def run_section(self, fake):
        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            return ai_exam.generate_section(PLAN, 0, 'material', avoid_topics=[])

    def texts(self, result):
        return [q['text'] for q in result['questions']]

    def test_a_rejected_question_is_replaced_by_a_spare(self):
        fake = FakeChat([mcq('q1'), mcq('q2'), mcq('spare1')], verdicts=[bad(0), *ok(1, 2)])
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q2', 'spare1'])
        self.assertEqual((result['dropped'], result['missing']), (1, 0))

    def test_spares_are_judged_too_and_unused_ones_are_ignored(self):
        fake = FakeChat([mcq('q1'), mcq('q2'), mcq('spare1'), mcq('spare2')], verdicts=ok(0, 1, 2, 3))
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q1', 'q2'])
        judged = [c for c in fake.calls if c[0] is ai_exam._JUDGE_SYSTEM][0][1]['questions']
        self.assertEqual(len(judged), 3)  # 2 savol + 1 zaxira (2 talik blok uchun bitta zaxira)

    def test_without_enough_good_questions_the_block_is_short_and_reported(self):
        fake = FakeChat([mcq('q1'), mcq('q2')], verdicts=[bad(0), *ok(1)])
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q2'])
        self.assertEqual(result['missing'], 1)

    def test_the_judge_sees_the_passage_and_the_marked_answers(self):
        fake = FakeChat([mcq('q1', answer=2), mcq('q2')], verdicts=ok(0, 1))
        self.run_section(fake)
        sent = [c for c in fake.calls if c[0] is ai_exam._JUDGE_SYSTEM][0][1]
        self.assertEqual(sent['source'], PASSAGE.strip())
        self.assertEqual(sent['questions'][0]['correct'], ['c'])

    def test_a_judge_failure_never_blocks_generation(self):
        fake = FakeChat([mcq('q1'), mcq('q2')], judge_error=llm.LLMError('boom'))
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q1', 'q2'])
        self.assertEqual(result['dropped'], 0)

    def test_a_judge_that_rejects_almost_everything_is_ignored(self):
        fake = FakeChat([mcq('q1'), mcq('q2'), mcq('s1')], verdicts=[bad(0), bad(1), bad(2)])
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q1', 'q2'])

    def test_garbage_verdicts_are_ignored(self):
        fake = FakeChat([mcq('q1'), mcq('q2')], verdicts=['x', {'id': 'zz', 'ok': False}, {'id': 99, 'ok': False}, None])
        result = self.run_section(fake)
        self.assertEqual(self.texts(result), ['q1', 'q2'])

    @override_settings(AI_EXAM_JUDGE=False)
    def test_it_can_be_switched_off(self):
        fake = FakeChat([mcq('q1'), mcq('q2'), mcq('spare')])
        result = self.run_section(fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(self.texts(result), ['q1', 'q2'])

    def test_fill_blank_gaps_are_counted_for_the_block(self):
        plan = {**PLAN, 'sections': [{**PLAN['sections'][0], 'blocks': [
            {'type': 'fill_blank', 'count': 2, 'instruction': '', 'options': 0, 'points': 1}]}]}
        gap = {'kind': 'fill_blank', 'text': 'Bees: {{1}} and {{2}}', 'blanks': [['queen'], ['workers']], 'block': 0}
        fake = FakeChat([gap], verdicts=ok(0))
        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            result = ai_exam.generate_section(plan, 0, 'material', avoid_topics=[])
        self.assertEqual((len(result['questions']), result['missing']), (1, 0))

    def test_blocks_stay_separate_when_the_model_sends_no_block_markers(self):
        plan = {**PLAN, 'sections': [{**PLAN['sections'][0], 'blocks': [
            {'type': 'mcq', 'count': 1, 'instruction': 'A', 'options': 3, 'points': 1},
            {'type': 'mcq', 'count': 1, 'instruction': 'B', 'options': 3, 'points': 1}]}]}
        questions = [{k: v for k, v in mcq(name).items() if k != 'block'} for name in ('one', 'two')]
        fake = FakeChat(questions, verdicts=ok(0, 1))
        with patch('apps.quizzes.llm.chat_json', side_effect=fake):
            result = ai_exam.generate_section(plan, 0, 'material', avoid_topics=[])
        self.assertEqual([q['block'] for q in result['questions']], [0, 1])

    def test_every_question_type_can_be_shown_to_the_judge(self):
        samples = [
            {'type': 'multiple', 'text': 't', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
            {'type': 'true_false', 'text': 't', 'correct_bool': True},
            {'type': 'matching', 'text': 't', 'pairs': [{'left': 'l', 'right': 'r'}]},
            {'type': 'fill_blank', 'text': 't {{1}}', 'blanks': [{'answers': ['x']}]},
            {'type': 'text', 'text': 't', 'accepted_answers': ['x']},
            {'type': 'numeric', 'text': 't', 'accepted_answers': ['1']},
            {'type': 'ordering', 'text': 't', 'items': ['a', 'b']},
        ]
        for number, question in enumerate(samples):
            view = ai_exam._judge_view(number, question)
            self.assertEqual(view['id'], number)
            self.assertGreater(len(view), 3, question['type'])
