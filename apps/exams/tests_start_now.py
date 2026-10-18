"""Imtihonni "hozir boshlash" - yaratishda ham, boshlanmagan imtihonni tahrirlashda ham."""
from datetime import timedelta

from django.utils import timezone

from .models import Exam
from .tests import ExamTestBase


class StartNowTests(ExamTestBase):
    def sections(self):
        qa, qb = self.quiz(), self.quiz()
        return [{'key': 'a', 'quiz': qa}, {'key': 'b', 'quiz': qb}]

    def test_create_with_start_now_is_running_immediately(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/exams/', {
            'course': self.course_id, 'template': self.custom_template(), 'title': 'Hozir',
            'start_now': True, 'sections': self.sections(),
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        exam = Exam.objects.get(pk=resp.json()['id'])
        self.assertLessEqual(exam.starts_at, timezone.now())
        self.assertEqual(exam.ends_at - exam.starts_at, timedelta(minutes=25))
        self.assertEqual(self.current(exam.pk).json()['item']['key'], 'a')

    def test_a_start_time_or_start_now_is_required(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/exams/', {
            'course': self.course_id, 'template': self.custom_template(), 'title': 'X', 'sections': self.sections(),
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_upcoming_exam_can_be_started_now_but_a_running_one_cannot(self):
        exam = self.make_exam(starts_in=60)
        self.auth(self.teacher_token)
        resp = self.client.patch(f'/api/v1/exams/{exam["id"]}/', {'start_now': True}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        fresh = Exam.objects.get(pk=exam['id'])
        self.assertLessEqual(fresh.starts_at, timezone.now())
        self.assertEqual(fresh.ends_at - fresh.starts_at, timedelta(minutes=25))
        again = self.client.patch(f'/api/v1/exams/{exam["id"]}/', {'start_now': True}, format='json')
        self.assertEqual(again.status_code, 400)

    def test_past_start_time_is_still_refused(self):
        self.auth(self.teacher_token)
        past = (timezone.now() - timedelta(minutes=5)).isoformat()
        resp = self.client.post('/api/v1/exams/', {
            'course': self.course_id, 'template': self.custom_template(), 'title': 'X',
            'starts_at': past, 'sections': self.sections(),
        }, format='json')
        self.assertEqual(resp.status_code, 400)
