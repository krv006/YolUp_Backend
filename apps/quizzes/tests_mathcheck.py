"""AI yozgan hisob-kitob savollarini mustaqil tekshirish: noto'g'ri javobli savol tushib qoladi, ifoda xavfsiz hisoblanadi."""
import json
from fractions import Fraction
from unittest.mock import patch

from django.test import SimpleTestCase

from . import ai_exam, mathcheck


class EvaluateTests(SimpleTestCase):
    def test_arithmetic(self):
        self.assertEqual(mathcheck.evaluate('3*(4+5)'), 27)
        self.assertEqual(mathcheck.evaluate('2^10'), 1024)
        self.assertEqual(mathcheck.evaluate('1/3 + 1/6'), Fraction(1, 2))
        self.assertEqual(mathcheck.evaluate('12 × 3 ÷ 4 − 1'), 8)
        self.assertEqual(mathcheck.evaluate('1,5 * 2'), 3)
        self.assertEqual(mathcheck.evaluate('-(2+3)'), -5)

    def test_square_roots(self):
        self.assertEqual(mathcheck.evaluate('sqrt(144)'), 12)
        self.assertEqual(mathcheck.evaluate('√(9/4)'), Fraction(3, 2))
        self.assertAlmostEqual(float(mathcheck.evaluate('sqrt(2)')), 1.41421356, places=6)

    def test_anything_else_is_refused(self):
        for bad in ('__import__("os").system("x")', 'open("f")', 'x + 1', '2 ** 99999', '9**9**9', '1/0', 'sqrt(-4)',
                    '', 'a' * 500, '2 + ', '[1,2]', '1 if 1 else 2', 'lambda: 1', '(1).real', '10**15**2', 'sin(1)'):
            with self.assertRaises(mathcheck.Unsafe, msg=bad):
                mathcheck.evaluate(bad)


class NumberTests(SimpleTestCase):
    def test_first_number_in_text(self):
        self.assertEqual(mathcheck.number_in('27 cm'), 27)
        self.assertEqual(mathcheck.number_in('-3,5'), Fraction(-7, 2))
        self.assertEqual(mathcheck.number_in('3/4 of it'), Fraction(3, 4))
        self.assertIsNone(mathcheck.number_in('none of the above'))


class ContradictionTests(SimpleTestCase):
    @staticmethod
    def numeric(answers, check, **extra):
        return {'kind': 'numeric', 'text': '3 x (4+5)?', 'answers': answers, 'check': check, **extra}

    def test_a_correct_numeric_answer_passes(self):
        self.assertFalse(mathcheck.contradicts(self.numeric(['27'], '3*(4+5)')))
        self.assertFalse(mathcheck.contradicts(self.numeric(['27 cm'], '3*(4+5)')))
        self.assertFalse(mathcheck.contradicts(self.numeric(['26', '27'], '3*(4+5)')))  # biri mos kelsa yetadi

    def test_a_wrong_numeric_answer_is_caught(self):
        self.assertTrue(mathcheck.contradicts(self.numeric(['28'], '3*(4+5)')))

    def test_tolerance_and_rounding_are_respected(self):
        self.assertFalse(mathcheck.contradicts(self.numeric(['3.33'], '10/3', tolerance=0.01)))
        self.assertTrue(mathcheck.contradicts(self.numeric(['3.33'], '10/3')))
        self.assertFalse(mathcheck.contradicts(self.numeric(['1.414213'], 'sqrt(2)', tolerance=0.001)))

    def test_mcq_is_checked_against_its_correct_option(self):
        good = {'kind': 'mcq', 'text': 'q', 'options': ['26', '27', '28'], 'answer': 1, 'check': '3*9'}
        bad = {**good, 'answer': 0}
        self.assertFalse(mathcheck.contradicts(good))
        self.assertTrue(mathcheck.contradicts(bad))

    def test_unverifiable_questions_are_left_alone(self):
        self.assertFalse(mathcheck.contradicts(self.numeric(['27'], '')))  # ifoda yo'q
        self.assertFalse(mathcheck.contradicts(self.numeric(['28'], 'abc')))  # ifoda yaroqsiz
        self.assertFalse(mathcheck.contradicts({'kind': 'mcq', 'text': 'q', 'options': ['red', 'blue'], 'answer': 0,
                                                'check': '1+1'}))  # javob son emas
        self.assertFalse(mathcheck.contradicts({'kind': 'short_answer', 'text': 'q', 'answers': ['5'], 'check': '1+1'}))
        self.assertFalse(mathcheck.contradicts('not a dict'))


class SectionIntegrationTests(SimpleTestCase):
    PLAN = {
        'exam_name': 'Math', 'language': 'en', 'rules': [],
        'sections': [{'title': 'S1', 'passage': None, 'focus': '', 'blocks': [
            {'type': 'numeric', 'count': 2, 'instruction': '', 'options': 0, 'points': 1}]}],
    }

    @staticmethod
    def numeric(text, answer, check):
        return {'kind': 'numeric', 'text': text, 'answers': [answer], 'check': check, 'block': 0}

    def write(self, questions):
        with patch('apps.quizzes.llm.chat_json', return_value={'passage': '', 'questions': questions}) as chat:
            result = ai_exam.generate_section(self.PLAN, 0, '', avoid_topics=[])
        return result, json.loads(chat.call_args.args[1])

    def test_a_question_with_a_wrong_answer_is_dropped_and_a_spare_takes_its_place(self):
        result, _ = self.write([
            self.numeric('wrong', '30', '3*9'),   # 27 bo'lishi kerak edi
            self.numeric('ok1', '27', '3*9'), self.numeric('ok2', '16', '2^4'), self.numeric('spare', '5', '2+3'),
        ])
        self.assertEqual([q['text'] for q in result['questions']], ['ok1', 'ok2'])
        self.assertEqual((result['dropped'], result['missing']), (1, 0))

    def test_the_check_field_never_reaches_the_stored_question(self):
        result, _ = self.write([self.numeric('ok1', '27', '3*9'), self.numeric('ok2', '16', '2^4')])
        self.assertTrue(all('check' not in q for q in result['questions']))

    def test_the_writer_is_told_to_send_a_check_expression(self):
        self.assertIn('"check"', ai_exam._WRITER_SYSTEM)


class EquationKeyTests(SimpleTestCase):
    """Tenglama savoli: belgilangan javob tenglamani qanoatlantiradimi (haqiqiy xato: "4x-3=2x+9" uchun 5 belgilangan edi)."""

    def test_the_options_that_satisfy_the_equation_are_found(self):
        self.assertEqual(mathcheck.satisfying_options('4*x-3=2*x+9', ['2', '3', '1', '5']), [])  # to'g'ri javob (6) yo'q
        self.assertEqual(mathcheck.satisfying_options('4*x-3=2*x+9', ['2', '6', '1', '5']), [1])
        self.assertEqual(mathcheck.satisfying_options('2x+3=11', ['x = 3', 'x = 4']), [1])  # "2x" va "x = " yozuvi

    def test_fractions_negatives_and_brackets(self):
        self.assertEqual(mathcheck.satisfying_options('8-2*x=3*x+11', ['-3', '-0.6', '1']), [1])
        self.assertEqual(mathcheck.satisfying_options('5-2*x=3*x+1', ['0', '4/5', '1']), [1])
        self.assertEqual(mathcheck.satisfying_options('x+4=3*(x-2)', ['x = 8', 'x = 5']), [1])
        self.assertEqual(mathcheck.satisfying_options('6-x=2(x+2)', ['-2', '2/3']), [1])

    def test_what_cannot_be_checked_is_left_alone(self):
        self.assertIsNone(mathcheck.satisfying_options('', ['1', '2']))
        self.assertIsNone(mathcheck.satisfying_options('2*x+3', ['1', '2']))            # tenglama emas
        self.assertIsNone(mathcheck.satisfying_options('x^2=4', ['one', 'two']))        # variantlar son emas
        self.assertIsNone(mathcheck.satisfying_options('import os=x', ['1']))           # xavfli matn
        self.assertIsNone(mathcheck.satisfying_options('2*x=4', []))
        self.assertIsNone(mathcheck.satisfying_options('2*x=4=6', ['2']))               # bitta "=" bo'lishi shart

    def test_an_mcq_with_a_wrong_key_contradicts(self):
        raw = {'kind': 'mcq', 'text': '4x-3=2x+9', 'equation': '4*x-3=2*x+9', 'options': ['2', '3', '1', '5'], 'answer': 3}
        self.assertTrue(mathcheck.contradicts(raw))
        right = {**raw, 'options': ['2', '3', '6', '5'], 'answer': 2}
        self.assertFalse(mathcheck.contradicts(right))
        wrong_key_right_value_present = {**right, 'answer': 0}
        self.assertTrue(mathcheck.contradicts(wrong_key_right_value_present))

    def test_an_unverifiable_mcq_is_never_rejected(self):
        self.assertFalse(mathcheck.contradicts({'kind': 'mcq', 'equation': 'garbage', 'options': ['1', '2'], 'answer': 0}))
        self.assertFalse(mathcheck.contradicts({'kind': 'mcq', 'equation': '2*x=4', 'options': ['1', '2'], 'answer': 'x'}))

    def test_the_equation_is_taken_from_a_bare_question_text_when_the_model_omits_it(self):
        self.assertEqual(mathcheck.equation_of({'text': 'Solve for x: 4*x - 7 = 3*x + 2'}), '4*x - 7 = 3*x + 2')
        self.assertEqual(mathcheck.equation_of({'text': '2x+3=11?'}), '2x+3=11')
        self.assertEqual(mathcheck.equation_of({'text': 'x yechimi?', 'equation': ' 2*x=4 '}), '2*x=4')
        # tenglama emas yoki oddiy gap: aralashilmaydi
        self.assertEqual(mathcheck.equation_of({'text': 'If x = 3, what is 2x + 1?'}), '')
        self.assertEqual(mathcheck.equation_of({'text': 'Which number is a prime?'}), '')
        self.assertEqual(mathcheck.equation_of({'text': 'Solve: x = 3 = y'}), '')
        # to'liq gapli savollar: faqat x so'ralganda
        self.assertEqual(mathcheck.equation_of({'text': 'What is the value of x in the equation 4 * x + 2 = 2 * x + 1'}), '4 * x + 2 = 2 * x + 1')
        self.assertEqual(mathcheck.equation_of({'text': 'If 7 * x - 2 = 3 * x + 10, what is x?'}), '7 * x - 2 = 3 * x + 10')
        self.assertEqual(mathcheck.equation_of({'text': 'If x + 2 = 5, what is 2x?'}), '')      # 2x so'ralyapti: tegilmaydi
        self.assertEqual(mathcheck.equation_of({'text': 'If 2x = 6, what is 3x + 1?'}), '')
        self.assertEqual(mathcheck.equation_of(None), '')

    def test_an_mcq_whose_text_is_the_equation_is_checked_without_the_field(self):
        raw = {'kind': 'mcq', 'text': 'Solve for x: 4*x - 7 = 3*x + 2', 'options': ['3', '7', '9', '1'], 'answer': 1}
        self.assertTrue(mathcheck.contradicts(raw))
        self.assertFalse(mathcheck.contradicts({**raw, 'answer': 2}))
