"""Import qilingan (to'g'ri javobsiz) test uchun AI javob taklifi: hech narsa saqlanmaydi, faqat egasi, ishonchsiz savolga taklif yo'q."""
from unittest.mock import patch

from django.test import override_settings

from apps.accounts.tests import login, register
from apps.quizzes.models import Option, Quiz
from apps.quizzes.tests_ai_exam import LLM_ON
from apps.quizzes.tests_question_types import QuizTestBase


def mcq(text, correct=None, qtype='single', options=('A', 'B', 'C')):
    return {'type': qtype, 'text': text, 'options': [
        {'text': o, 'is_correct': correct is not None and i in correct} for i, o in enumerate(options)]}


@override_settings(**LLM_ON)
class SuggestAnswersTests(QuizTestBase):
    def draft(self, questions):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/', {
            'topic': 'Import', 'title': 'Forma', 'status': 'draft', 'questions': questions}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()['id']

    def suggest(self, quiz_id, token=None):
        self.auth(token or self.teacher_token)
        return self.client.post(f'/api/v1/quizzes/{quiz_id}/suggest-answers/')

    @staticmethod
    def reply(quiz_id, answers):
        """`question id` -> javob; id'larni DB'dan olamiz."""
        ids = [str(q.id) for q in Quiz.objects.get(pk=quiz_id).questions.all()]
        return {'answers': [{'id': ids[i], **payload} for i, payload in answers]}

    def test_suggests_only_for_questions_without_a_correct_option(self):
        quiz_id = self.draft([mcq('Poytaxt?'), mcq('Tayyor', correct=[1]), mcq('Tub sonlar?', qtype='multiple')])
        with patch('apps.quizzes.ai_answers.llm.chat_json') as chat:
            chat.return_value = self.reply(quiz_id, [(0, {'correct': [0], 'confidence': 'high'}),
                                                     (2, {'correct': [0, 2], 'confidence': 'medium'})])
            resp = self.suggest(quiz_id)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['asked'], body['skipped']), (2, 0))
        self.assertEqual([(s['number'], s['correct'], s['confidence']) for s in body['suggestions']],
                         [(1, [0], 'high'), (3, [0, 2], 'medium')])
        sent = chat.call_args.args[1]
        self.assertIn('Poytaxt?', sent)
        self.assertNotIn('Tayyor', sent)  # javobi bor savol AI'ga yuborilmaydi

    def test_nothing_is_saved(self):
        quiz_id = self.draft([mcq('Poytaxt?')])
        with patch('apps.quizzes.ai_answers.llm.chat_json') as chat:
            chat.return_value = self.reply(quiz_id, [(0, {'correct': [1], 'confidence': 'high'})])
            self.suggest(quiz_id)
        self.assertFalse(Option.objects.filter(question__quiz_id=quiz_id, is_correct=True).exists())

    def test_uncertain_and_invalid_suggestions_are_dropped(self):
        quiz_id = self.draft([mcq('Matnga tayanadi?'), mcq('Ikkita deb xato?'), mcq('Chegaradan tashqari?'),
                              mcq('Noma\'lum ishonch?'), mcq('Javob yo\'q?')])
        with patch('apps.quizzes.ai_answers.llm.chat_json') as chat:
            chat.return_value = self.reply(quiz_id, [
                (0, {'correct': [], 'confidence': 'low'}),            # AI ishonchsiz — taklif yo'q
                (1, {'correct': [0, 1], 'confidence': 'high'}),       # single uchun ikkita — yaroqsiz
                (2, {'correct': [7], 'confidence': 'high'}),          # chegaradan tashqari
                (3, {'correct': [2], 'confidence': 'zzz'}),           # ishonch noma'lum -> low
            ])                                                        # 5-savol umuman javobsiz
            body = self.suggest(quiz_id).json()
        self.assertEqual((body['asked'], body['skipped']), (5, 4))
        self.assertEqual(body['suggestions'], [{'number': 4, 'question': body['suggestions'][0]['question'],
                                                'correct': [2], 'confidence': 'low'}])

    def test_questions_are_sent_in_chunks(self):
        quiz_id = self.draft([mcq(f'Savol {i}') for i in range(20)])
        with patch('apps.quizzes.ai_answers.llm.chat_json', return_value={'answers': []}) as chat:
            body = self.suggest(quiz_id).json()
        self.assertEqual(chat.call_count, 2)  # 15 + 5
        self.assertEqual((body['asked'], body['skipped']), (20, 20))

    def test_nothing_to_suggest_does_not_call_the_ai(self):
        quiz_id = self.draft([mcq('Tayyor', correct=[0])])
        with patch('apps.quizzes.ai_answers.llm.chat_json') as chat:
            body = self.suggest(quiz_id).json()
        chat.assert_not_called()
        self.assertEqual(body, {'asked': 0, 'suggestions': [], 'skipped': 0})

    @override_settings(OPENAI_API_KEY='')
    def test_disabled_ai_gives_a_clear_error(self):
        quiz_id = self.draft([mcq('Poytaxt?')])
        resp = self.suggest(quiz_id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("AI hozir o'chirilgan", resp.json()['error']['details']['detail'])

    def test_only_the_owner_can_ask(self):
        quiz_id = self.draft([mcq('Poytaxt?')])
        register(self.client, 'other_teacher', 'teacher')
        other = login(self.client, 'other_teacher')
        self.assertIn(self.suggest(quiz_id, other).status_code, (403, 404))
        self.assertEqual(self.suggest(quiz_id, self.child_token).status_code, 403)
