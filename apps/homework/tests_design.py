"""Yangi dizayn: AI guruh xulosasi vazifada saqlanadi, kunlik AI statistikasi, eslatma matni va ota-onaga ham."""
from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import NotificationRecipient

from .models import Submission
from .tests_workflow import WorkflowBase, make


class GroupSummaryStoredTests(WorkflowBase):
    URL = '/api/v1/homework/assignments/{}/ai-summary/'
    REPLY = {'summary': "Ko'pchilik 115-misolda xato qildi.", 'topics': ['Kasrlar'], 'recommendations': ['Takrorlang']}

    def test_assignment_shows_the_ready_summary_without_calling_ai(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        before = self.api(self.teacher).get(f'/api/v1/homework/assignments/{a["id"]}/').json()
        self.assertIsNone(before['ai_group_summary'])
        with override_settings(OPENAI_API_KEY='sk-test'), mock.patch('apps.quizzes.llm.chat_json', return_value=self.REPLY) as llm:
            made = self.api(self.teacher).post(self.URL.format(a['id'])).json()
            shown = self.api(self.teacher).get(f'/api/v1/homework/assignments/{a["id"]}/').json()['ai_group_summary']
        self.assertEqual(llm.call_count, 1)
        self.assertEqual((shown['text'], shown['topics'], shown['recommendations']), (self.REPLY['summary'], ['Kasrlar'], ['Takrorlang']))
        self.assertEqual(shown['created_at'], made['created_at'])
        self.assertEqual(made['text'], made['summary'])  # eski `summary` ham joyida

    def test_summary_is_hidden_from_students_and_parents(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        with override_settings(OPENAI_API_KEY='sk-test'), mock.patch('apps.quizzes.llm.chat_json', return_value=self.REPLY):
            self.api(self.teacher).post(self.URL.format(a['id']))
        for user in (self.student, self.parent):
            body = self.api(user).get(f'/api/v1/homework/assignments/{a["id"]}/').json()
            self.assertNotIn('ai_group_summary', body)


class AiStatsTests(WorkflowBase):
    URL = '/api/v1/homework/assignments/ai-stats/'

    def test_today_week_and_pending(self):
        a = self.create()
        today = self.make_submission(self.student, a['id'])
        older = self.make_submission(self.student2, a['id'], status=Submission.Status.DONE)
        Submission.objects.filter(pk=today.pk).update(checked_at=timezone.now())
        Submission.objects.filter(pk=older.pk).update(checked_at=timezone.now() - timedelta(days=3))
        self.assertEqual(self.api(self.teacher).get(self.URL).json(), {'period': 'today', 'checked': 1, 'pending_confirm': 1})
        week = self.api(self.teacher).get(self.URL, {'period': 'week'}).json()
        self.assertEqual((week['checked'], week['pending_confirm']), (2, 1))

    def test_other_teachers_and_roles(self):
        a = self.create()
        Submission.objects.filter(pk=self.make_submission(self.student, a['id']).pk).update(checked_at=timezone.now())
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.api(other).get(self.URL).json()['checked'], 0)
        self.assertEqual(self.api(self.teacher).get(self.URL, {'period': 'year'}).status_code, 400)
        self.assertEqual(self.api(self.student).get(self.URL).status_code, 403)


class RemindMessageTests(WorkflowBase):
    def remind(self, a, **data):
        return self.api(self.teacher).post(f'/api/v1/homework/assignments/{a["id"]}/remind/', data, format='json')

    def test_custom_message_reaches_the_missing_students(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        resp = self.remind(a, message="Ertagacha topshiring, iltimos!")
        self.assertEqual((resp.status_code, resp.json()), (200, {'notified': 1}))
        note = NotificationRecipient.objects.get(user=self.student2, notification__kind='homework_reminder').notification
        self.assertIn('Ertagacha topshiring', note.description)

    def test_parents_of_missing_students_can_be_notified_too(self):
        a = self.create()  # s1 ning ota-onasi bor, s2 niki yo'q; ikkalasi ham topshirmagan
        resp = self.remind(a, notify_parents=True)
        self.assertEqual(resp.json(), {'notified': 2, 'parents_notified': 1})
        self.assertTrue(NotificationRecipient.objects.filter(user=self.parent, notification__kind='homework_reminder').exists())

    def test_parents_are_skipped_when_every_child_submitted(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        self.make_submission(self.student2, a['id'])
        self.assertEqual(self.remind(a, notify_parents=True).json(), {'notified': 0, 'parents_notified': 0})

    def test_message_validation(self):
        a = self.create()
        self.assertEqual(self.remind(a, message=['x']).status_code, 400)
        self.assertEqual(self.remind(a, message='a' * 501).status_code, 400)
        self.assertEqual(self.remind(a, message='   ').status_code, 200)  # bo'sh matn — standart matn
