"""IELTS ball og'irligi: har bo'shliq, har juft va har to'g'ri javob alohida 1 ball (Reading/Listening jami 40)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.exams import scoring

from . import ai_exam


def convert(raw, points=1):
    question = ai_exam._to_question(raw, points=points)
    return ai_exam._validated(question) if question else None


class MarksTests(SimpleTestCase):
    def test_every_gap_is_one_mark(self):
        question = convert({'kind': 'fill_blank', 'text': 'a {{1}} b {{2}} c {{3}}', 'blanks': [['x'], ['y'], ['z']]})
        self.assertEqual(question['points'], 3)

    def test_every_matched_pair_is_one_mark(self):
        pairs = [{'left': f'L{i}', 'right': f'R{i}'} for i in range(5)]
        self.assertEqual(convert({'kind': 'matching', 'text': 'm', 'pairs': pairs})['points'], 5)

    def test_choose_two_is_two_marks_and_choose_one_is_one(self):
        multi = convert({'kind': 'mcq_multiple', 'text': 'q', 'options': ['a', 'b', 'c', 'd', 'e'], 'answers': [0, 3]})
        single = convert({'kind': 'mcq', 'text': 'q', 'options': ['a', 'b', 'c'], 'answer': 1})
        self.assertEqual((multi['points'], single['points']), (2, 1))

    def test_other_types_stay_one_mark(self):
        for raw in ({'kind': 'true_false_not_given', 'text': 's', 'answer': 'true'},
                    {'kind': 'short_answer', 'text': 'q', 'answers': ['x']},
                    {'kind': 'numeric', 'text': 'q', 'answers': ['4']},
                    {'kind': 'ordering', 'text': 'q', 'items': ['a', 'b', 'c']}):
            self.assertEqual(convert(raw)['points'], 1, raw['kind'])

    def test_the_block_points_multiply_the_marks(self):
        question = convert({'kind': 'fill_blank', 'text': 'a {{1}} b {{2}}', 'blanks': [['x'], ['y']]}, points=2)
        self.assertEqual(question['points'], 4)

    def test_points_never_exceed_the_serializer_limit(self):
        text = ' '.join('{{%d}}' % i for i in range(1, 31))
        question = convert({'kind': 'fill_blank', 'text': text, 'blanks': [['x']] * 30}, points=10)
        self.assertEqual(question['points'], 100)

    def test_a_forty_mark_section_gives_the_real_band_not_a_skewed_one(self):
        """13 bo'shliq + 27 oddiy savol = 40 ball. Eskisi: 13 bo'shliq 1-2 ball turardi va band buzilardi."""
        gaps = convert({'kind': 'fill_blank', 'text': ' '.join('{{%d}}' % i for i in range(1, 14)), 'blanks': [['x']] * 13})
        self.assertEqual(gaps['points'], 13)
        total = gaps['points'] + 27
        self.assertEqual(total, 40)
        # 13 bo'shliqdan 0 tasi, 27 savolning hammasi to'g'ri: 27/40 -> band 6.5 (avval 27/28 ~ 38.6/40 -> 8.5)
        row = [{'key': 'reading', 'title': 'R', 'group': '', 'weight': 1, 'manual': False, 'earned': 27, 'max': total,
                'manual_score': None}]
        self.assertEqual(scoring.compute({'type': 'ielts'}, row)['sections'][0]['score'], 6.5)

    def test_partial_credit_follows_the_gaps(self):
        from .grading import grade

        class Q:
            type = 'fill_blank'
            points = 5
            answer_key = {'blanks': [{'answers': ['a']}, {'answers': ['b']}, {'answers': ['c']}, {'answers': ['d']}, {'answers': ['e']}]}

        graded = grade(Q(), {'blanks': ['a', 'b', 'c', 'x', 'y']})
        self.assertEqual(graded.earned, 3)  # 3 to'g'ri bo'shliq = 3 ball

    def test_generate_section_keeps_the_scaled_points(self):
        plan = {'exam_name': 'X', 'language': 'en', 'rules': [], 'sections': [{'title': 'S', 'passage': None, 'blocks': [
            {'type': 'fill_blank', 'count': 4, 'instruction': 'Complete the notes.', 'options': 4, 'points': 1}]}]}
        reply = {'passage': '', 'questions': [{'kind': 'fill_blank', 'text': 'a {{1}} b {{2}} c {{3}} d {{4}}',
                                               'blanks': [['x'], ['y'], ['z'], ['w']], 'block': 0}]}
        with patch('apps.quizzes.llm.chat_json', return_value=reply):
            result = ai_exam.generate_section(plan, 0, '', avoid_topics=[])
        self.assertEqual([q['points'] for q in result['questions']], [4])
