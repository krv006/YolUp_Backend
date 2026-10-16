"""IELTS Writing AI tahlili: 4 mezon, band hisobi, uzunlik cheklovi, mock imtihondagi navbat va ko'rinish qoidalari."""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.accounts.models import User
from apps.quizzes import ielts_writing, llm

from . import services
from .models import Exam, ExamAttempt
from .tests import ExamTestBase

ESSAY_2 = 'Some people think technology isolates us. ' + 'Technology helps people to stay connected today. ' * 40


def reply(task=2, bands=(6.0, 6.5, 6.0, 5.5), words=0):
    names = ('task', 'coherence', 'lexical', 'grammar')
    return {
        'task': task, 'word_count': words,
        'criteria': {n: {'band': b, 'comment': f'{n} ok', 'evidence': 'quote'} for n, b in zip(names, bands)},
        'errors': [{'quote': 'people is', 'issue': 'agreement', 'correction': 'people are'}],
        'strengths': ['clear position'], 'improvements': ['vary structures'], 'upgraded_paragraph': 'Better text.',
    }


class ModuleTests(SimpleTestCase):
    def test_overall_is_the_mean_rounded_to_half_a_band(self):
        result = ielts_writing.clean_result(reply(bands=(6.0, 6.5, 6.0, 5.5)), task=2, words=260)
        self.assertEqual(result['overall_band'], 6.0)  # 6.0 o'rtacha
        result = ielts_writing.clean_result(reply(bands=(7.0, 7.0, 6.5, 6.5)), task=2, words=260)
        self.assertEqual(result['overall_band'], 7.0)  # 6.75 -> 7.0
        self.assertEqual([c['title'] for c in result['criteria']][0], 'Task Response')
        self.assertEqual(ielts_writing.clean_result(reply(1), task=1, words=160)['criteria'][0]['title'], 'Task Achievement')

    def test_a_response_that_is_too_short_caps_the_task_band(self):
        result = ielts_writing.clean_result(reply(bands=(7.5, 7.0, 7.0, 7.0)), task=2, words=180)  # 72% of 250
        self.assertEqual((result['criteria'][0]['band'], result['criteria'][0]['capped'], result['too_short']), (5.0, True, True))
        self.assertEqual(result['criteria'][1]['band'], 7.0)  # boshqa mezonlar o'zgarmaydi
        near = ielts_writing.clean_result(reply(bands=(7.5, 7.0, 7.0, 7.0)), task=2, words=230)  # 92%
        self.assertEqual((near['criteria'][0]['band'], near['too_short']), (7.5, False))
        tiny = ielts_writing.clean_result(reply(bands=(8, 8, 8, 8)), task=2, words=90)
        self.assertEqual(tiny['criteria'][0]['band'], 4.0)

    def test_incomplete_or_invalid_bands_are_refused(self):
        broken = reply()
        del broken['criteria']['lexical']
        with self.assertRaises(ielts_writing.IeltsWritingError):
            ielts_writing.clean_result(broken, task=2, words=260)
        with self.assertRaises(ielts_writing.IeltsWritingError):
            ielts_writing.clean_result(reply(bands=(10, 6, 6, 6)), task=2, words=260)

    def test_odd_bands_are_snapped_to_half_steps(self):
        result = ielts_writing.clean_result(reply(bands=(6.2, 6.3, 6.8, 5.9)), task=2, words=260)
        self.assertEqual([c['band'] for c in result['criteria']], [6.0, 6.5, 7.0, 6.0])

    def test_task_detection(self):
        self.assertEqual(ielts_writing.detect_task('', minimum=150), 1)
        self.assertEqual(ielts_writing.detect_task('', minimum=250), 2)
        self.assertEqual(ielts_writing.detect_task('WRITING TASK 1: the graph shows...'), 1)
        self.assertEqual(ielts_writing.detect_task('The chart below shows exports'), 1)
        self.assertEqual(ielts_writing.detect_task('Discuss both views and give your opinion'), 2)
        self.assertEqual(ielts_writing.detect_task('something else'), 2)

    def test_writing_band_weights_task_two_double(self):
        t1 = {'task': 1, 'overall_band': 6.0}
        t2 = {'task': 2, 'overall_band': 7.0}
        self.assertEqual(ielts_writing.writing_band([t1, t2]), 6.5)  # (6 + 14) / 3 = 6.67 -> 6.5
        self.assertEqual(ielts_writing.writing_band([t2]), 7.0)
        self.assertIsNone(ielts_writing.writing_band([]))

    def test_word_count(self):
        self.assertEqual(ielts_writing.count_words("It's a well-known fact, isn't it?"), 6)
        self.assertEqual(ielts_writing.count_words(''), 0)

    def test_homework_shape_has_a_question_per_criterion_and_percent_scores(self):
        result = ielts_writing.clean_result(reply(bands=(9, 9, 9, 9)), task=2, words=300)
        shaped = ielts_writing.to_homework_result(result, model='m')
        self.assertEqual(shaped['overall_score'], 100.0)
        self.assertEqual(len(shaped['questions']), 5)  # 4 mezon + xatolar
        self.assertEqual(shaped['questions'][0]['score'], 100.0)
        self.assertIn('Band 9', shaped['questions'][0]['question'])
        self.assertTrue(shaped['questions'][4]['mistakes'])

    def test_empty_response_is_refused_before_any_ai_call(self):
        with patch('apps.quizzes.llm.chat_json') as chat:
            with self.assertRaises(ielts_writing.IeltsWritingError):
                ielts_writing.evaluate('   ')
        chat.assert_not_called()

    def test_the_prompt_is_strict_and_treats_the_essay_as_data(self):
        for phrase in ('LOWER one', 'DATA', 'public IELTS Writing', 'Band 5-6.5'):
            self.assertIn(phrase, ielts_writing._SYSTEM)


@override_settings(OPENAI_API_KEY='sk-test')
class ExamWritingAiTests(ExamTestBase):
    def setUp(self):
        super().setUp()
        self.auth(self.teacher_token)
        essay = {'type': 'essay', 'text': 'Some people think technology isolates us. Discuss both views.',
                 'points': 9, 'min_words': 250}
        self.writing_quiz = self.make_quiz([essay]).json()['id']
        listening, reading = self.quiz(count=1), self.quiz(count=1)
        sections = [{'key': 'listening', 'quiz': listening}, {'key': 'reading', 'quiz': reading},
                    {'key': 'writing', 'quiz': self.writing_quiz}]
        self.exam = self.create_exam('ielts', sections).json()
        self.shift(self.exam['id'], 100)  # Writing davri
        detail = self.client.get(f'/api/v1/quizzes/{self.writing_quiz}/').json()
        self.essay_id = detail['questions'][0]['id']
        self.student_id = User.objects.get(username='s1').id

    def write(self, text=ESSAY_2):
        self.save(self.exam['id'], [{'question': self.essay_id, 'value_text': text}])
        self.shift(self.exam['id'], 200)

    def ask(self, token=None):
        self.auth(token or self.teacher_token)
        return self.client.post(f'/api/v1/exams/{self.exam["id"]}/results/{self.student_id}/writing-ai/')

    def detail(self, token):
        self.auth(token)
        return self.client.get(f'/api/v1/exams/{self.exam["id"]}/results/{self.student_id}/').json()

    def run_queue(self, **kwargs):
        with patch('apps.quizzes.llm.chat_json', return_value=reply(**kwargs)) as chat:
            result = services.sync_writing_ai()
        return result, chat

    def test_the_teacher_asks_the_queue_runs_and_a_suggestion_appears(self):
        self.write()
        resp = self.ask()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['writing_ai']['status'], 'queued')
        result, chat = self.run_queue()
        self.assertEqual(result, {'done': 1, 'failed': 0})
        self.assertEqual(chat.call_count, 1)
        ai = self.detail(self.teacher_token)['writing_ai']
        self.assertEqual(ai['status'], 'done')
        self.assertEqual(ai['suggested_band'], 6.0)
        item = ai['items'][0]
        self.assertEqual((item['task'], item['min_words']), (2, 250))  # savol min_words=250 -> Task 2
        self.assertEqual(len(item['criteria']), 4)

    def test_asking_twice_does_not_queue_two_jobs(self):
        self.write()
        self.ask()
        self.ask()
        self.assertEqual(self.run_queue()[0]['done'], 1)
        self.assertEqual(self.run_queue()[0], {'done': 0, 'failed': 0})  # navbat bo'sh

    def test_the_student_sees_nothing_until_the_teacher_sets_the_writing_band(self):
        self.write()
        self.ask()
        self.run_queue()
        self.assertIsNone(self.detail(self.child_token)['writing_ai'])
        self.auth(self.teacher_token)
        self.client.put(f'/api/v1/exams/{self.exam["id"]}/results/{self.student_id}/manual/',
                        {'scores': {'writing': 6.5}}, format='json')
        own = self.detail(self.child_token)['writing_ai']
        self.assertEqual(own['status'], 'done')
        self.assertNotIn('suggested_band', own)  # taklif bandi o'quvchiga ko'rsatilmaydi, faqat tahlil
        self.assertTrue(own['items'][0]['errors'])

    def test_only_the_exam_teacher_can_ask(self):
        self.write()
        self.assertEqual(self.ask(self.child_token).status_code, 403)
        self.assertEqual(self.ask(self.teacher2_token).status_code, 404)

    def test_nothing_is_asked_when_the_student_wrote_nothing(self):
        self.shift(self.exam['id'], 200)
        self.assertEqual(self.ask().status_code, 404)  # urinish yo'q
        self.shift(self.exam['id'], 100)
        self.save(self.exam['id'], [{'question': self.essay_id, 'value_text': '  '}])
        self.shift(self.exam['id'], 200)
        self.assertIn(self.ask().status_code, (400, 404))

    def test_an_ai_failure_is_recorded_and_the_teacher_can_retry(self):
        self.write()
        self.ask()
        with patch('apps.quizzes.llm.chat_json', side_effect=llm.LLMError('boom')):
            self.assertEqual(services.sync_writing_ai(), {'done': 0, 'failed': 1})
        self.assertEqual(self.detail(self.teacher_token)['writing_ai']['status'], 'failed')
        self.ask()
        self.assertEqual(self.run_queue()[0]['done'], 1)

    def test_a_short_essay_is_marked_down_on_task_response(self):
        self.write('Technology is good. ' * 20)  # ~60 so'z
        self.ask()
        self.run_queue(bands=(8, 8, 8, 8))
        item = self.detail(self.teacher_token)['writing_ai']['items'][0]
        self.assertTrue(item['too_short'])
        self.assertEqual(item['criteria'][0]['band'], 4.0)

    def test_the_cron_command_runs(self):
        from django.core.management import call_command
        import io

        self.write()
        self.ask()
        out = io.StringIO()
        with patch('apps.quizzes.llm.chat_json', return_value=reply()):
            call_command('sync_exam_writing_ai', stdout=out)
        self.assertIn('tayyor 1', out.getvalue())
        self.assertEqual(ExamAttempt.objects.get(exam_id=self.exam['id']).ai_results['writing']['status'], 'done')
        self.assertTrue(Exam.objects.filter(pk=self.exam['id']).exists())
