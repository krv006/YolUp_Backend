"""Bo'limni muddatidan oldin tugatib keyingisiga o'tish (har o'quvchi uchun alohida)."""
from datetime import timedelta

from django.utils import timezone

from .models import Exam, ExamAttempt
from .tests import ExamTestBase


class NextSectionTests(ExamTestBase):
    def go(self, exam_id, token=None):
        self.auth(token or self.child_token)
        return self.client.post(f'/api/v1/exams/{exam_id}/next-section/')

    def running_exam(self, minutes_ago=3):
        exam = self.make_exam()
        self.shift(exam['id'], minutes_ago)
        return exam

    def test_student_moves_to_the_next_section_and_it_starts_now(self):
        exam = self.running_exam()
        self.assertEqual(self.current(exam['id']).json()['item']['key'], 'a')
        body = self.go(exam['id']).json()
        self.assertEqual(body['item']['kind'], 'break')
        self.assertEqual(body['item']['key'], 'rest')

    def test_only_this_student_is_moved(self):
        exam = self.running_exam()
        self.go(exam['id'])
        from django.contrib.auth import get_user_model

        from . import services

        other = get_user_model().objects.get(username='s2')  # boshqa o'quvchining jadvali o'zgarmaydi
        payload = services.current_payload(student=other, exam=Exam.objects.get(pk=exam['id']))
        self.assertEqual(payload['item']['key'], 'a')

    def test_the_old_section_is_closed_and_the_new_one_opens_for_answers(self):
        exam = self.running_exam()
        self.go(exam['id'])  # a -> tanaffus
        self.go(exam['id'])  # tanaffus -> b
        self.assertEqual(self.current(exam['id']).json()['item']['key'], 'b')
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qb)).status_code, 200)
        # a bo'limi endi yopiq (GRACE dan keyin)
        attempt = ExamAttempt.objects.get(exam_id=exam['id'])
        attempt.advances['a'] = (timezone.now() - timedelta(minutes=1)).isoformat()
        attempt.save()
        self.assertEqual(self.save(exam['id'], self.answers_for(self.qa)).status_code, 403)

    def test_the_last_section_cannot_be_skipped(self):
        exam = self.running_exam(minutes_ago=17)  # a(10) + tanaffus(5) -> hozir b da
        self.assertEqual(self.current(exam['id']).json()['item']['key'], 'b')
        self.assertEqual(self.go(exam['id']).status_code, 400)

    def test_not_possible_before_the_start_after_the_end_or_after_finishing(self):
        upcoming = self.make_exam(starts_in=60)
        self.assertEqual(self.go(upcoming['id']).status_code, 403)
        exam = self.running_exam()
        self.save(exam['id'], [self.answers_for(self.qa)[0]])
        self.auth(self.child_token)
        self.client.post(f'/api/v1/exams/{exam["id"]}/finish/')
        self.assertEqual(self.go(exam['id']).status_code, 403)
        self.shift(exam['id'], 60)
        self.assertEqual(self.go(exam['id']).status_code, 403)

    def test_teachers_cannot_use_it(self):
        exam = self.running_exam()
        self.assertEqual(self.go(exam['id'], self.teacher_token).status_code, 403)

    def test_a_student_who_rushed_through_is_done_before_the_exam_ends(self):
        from django.contrib.auth import get_user_model

        from . import services

        exam_id = self.running_exam(minutes_ago=0)['id']
        exam = Exam.objects.get(pk=exam_id)
        student = get_user_model().objects.get(username='s1')
        t0 = exam.starts_at + timedelta(minutes=1)
        services.next_section(student=student, exam=exam, now=t0)  # a -> tanaffus
        services.next_section(student=student, exam=exam, now=t0 + timedelta(minutes=1))  # tanaffus -> b
        mid = services.current_payload(student=student, exam=exam, now=t0 + timedelta(minutes=5))
        self.assertEqual(mid['item']['key'], 'b')
        late = services.current_payload(student=student, exam=exam, now=t0 + timedelta(minutes=15))
        self.assertEqual((late['state'], late['item']), ('submitted', None))  # exam hali tugamagan (umumiy 25 daq)
