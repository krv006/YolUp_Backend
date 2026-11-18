"""AI sarfi: har baholashda tokenlar yoziladi (narxni o'lchash uchun) va `homework_ai_usage` hisoboti."""
import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings

from apps.quizzes import llm
from apps.quizzes.tests_ai_exam import completion, reply

from . import services
from .models import Submission
from .tests_ai_engine import GRADE, LLM_ON, FakeGrader, text_pdf
from .tests_hardening import HomeworkBase


def broken_json():
    return reply(200, {'choices': [{'message': {'content': 'not json'}, 'finish_reason': 'stop'}], 'usage': {'total_tokens': 123}})


@override_settings(**LLM_ON)
class UsageBase(HomeworkBase):
    def graded(self, fake):
        with patch('apps.quizzes.llm.requests.post', side_effect=fake):
            resp = self.submit(self.assignment(), text_pdf())
            self.assertEqual(resp.status_code, 201, resp.content)
            services.sync_ai_results()
        return Submission.objects.get(pk=resp.data['id'])


class UsageTests(UsageBase):
    def test_the_tokens_of_a_grading_are_recorded_on_the_ai_result(self):
        submission = self.graded(FakeGrader())
        usage = submission.ai_result['usage']
        self.assertEqual((usage['calls'], usage['total_tokens'], usage['model']), (1, 123, 'gpt-test'))

    def test_usage_stays_out_of_the_final_result_the_student_sees(self):
        submission = self.graded(FakeGrader())
        self.assertNotIn('usage', submission.result)
        self.assertIn('overall_score', submission.result)

    def test_retries_after_a_broken_json_are_counted_too(self):
        replies = [broken_json(), completion(GRADE)]

        def fake(url, json=None, **kwargs):
            return replies.pop(0)

        submission = self.graded(fake)
        self.assertEqual(submission.ai_result['usage']['calls'], 2)
        self.assertEqual(submission.ai_result['usage']['total_tokens'], 246)

    def test_tracking_is_scoped_and_does_not_leak_between_gradings(self):
        first = self.graded(FakeGrader())
        second = self.graded(FakeGrader())
        self.assertEqual(first.ai_result['usage']['total_tokens'], second.ai_result['usage']['total_tokens'])

    def test_a_call_outside_tracking_records_nothing_and_does_not_fail(self):
        with patch('apps.quizzes.llm.requests.post', side_effect=FakeGrader()):
            self.assertEqual(llm.chat_json('sys', 'user')['overall_score'], 78)


class UsageReportTests(UsageBase):
    def report(self, *args):
        out = StringIO()
        call_command('homework_ai_usage', *args, stdout=out)
        return out.getvalue()

    def test_the_report_before_any_usage_says_so(self):
        self.assertIn("yozilmagan", self.report())

    def test_the_report_sums_tokens_and_shows_the_average(self):
        self.graded(FakeGrader())
        self.graded(FakeGrader())
        text = self.report()
        self.assertIn('2 ta', text)
        self.assertIn('Jami: 246 token', text)
        self.assertIn("o'rtacha: 123 token", text)
        self.assertIn('Narxni', text)  # tarif berilmagan: narx taxmin qilinmaydi

    def test_the_price_is_shown_only_when_the_tariff_is_given(self):
        submission = self.graded(FakeGrader())
        submission.ai_result['usage'].update(prompt_tokens=1_000_000, completion_tokens=500_000, total_tokens=1_500_000)
        submission.save()
        text = self.report('--price-in', '1', '--price-out', '2')
        self.assertIn('Taxminiy narx: $2.0000', text)  # 1M * $1 + 0.5M * $2
        self.assertNotIn('Narxni ko', text)
        self.assertIn('Narxni ko', self.report())
