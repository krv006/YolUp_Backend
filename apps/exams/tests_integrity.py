"""Halollik jurnali: imtihon davomida oynadan chiqish / tashqaridan nusxa qo'yish qayd etiladi, faqat o'qituvchiga ko'rinadi."""
from .models import ExamAttempt
from .services import MAX_FOCUS_EVENTS
from .tests import ExamTestBase


class IntegrityLogTests(ExamTestBase):
    def running_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])  # urinish yaratiladi
        return exam

    def focus(self, exam_id, kind, token=None):
        self.auth(token or self.child_token)
        return self.client.post(f'/api/v1/exams/{exam_id}/focus/', {'kind': kind}, format='json')

    def test_events_are_recorded_during_the_exam_and_counted_for_the_teacher_only(self):
        exam = self.running_exam()
        for kind in ('blur', 'blur', 'paste'):
            self.assertEqual(self.focus(exam['id'], kind).status_code, 200)
        self.assertEqual(ExamAttempt.objects.get(exam_id=exam['id']).focus_events.__len__(), 3)
        row = self.results(exam['id'], self.teacher_token).json()['results'][0]
        self.assertEqual((row['integrity']['away'], row['integrity']['paste']), (2, 1))
        self.assertEqual([e['kind'] for e in row['integrity']['events']], ['blur', 'blur', 'paste'])
        self.shift(exam['id'], 40)  # imtihon tugadi: o'quvchi o'z natijasini ko'radi, jurnalsiz
        own = self.results(exam['id'], self.child_token).json()['results'][0]
        self.assertNotIn('integrity', own)

    def test_the_student_detail_for_the_teacher_has_it_too(self):
        exam = self.running_exam()
        self.focus(exam['id'], 'blur')
        from apps.accounts.models import User

        sid = User.objects.get(username='s1').id
        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/exams/{exam["id"]}/results/{sid}/').json()
        self.assertEqual(detail['integrity']['away'], 1)

    def test_nothing_is_recorded_before_the_start_after_finishing_or_after_the_end(self):
        exam = self.make_exam(starts_in=60)
        self.assertEqual(self.focus(exam['id'], 'blur').json()['recorded'], 0)  # boshlanmagan
        self.shift(exam['id'], 3)
        self.save(exam['id'], [self.answers_for(self.qa)[0]])
        self.auth(self.child_token)
        self.client.post(f'/api/v1/exams/{exam["id"]}/finish/')
        self.assertEqual(self.focus(exam['id'], 'blur').json()['recorded'], 0)  # yakunlagan
        self.assertEqual(ExamAttempt.objects.get(exam_id=exam['id']).focus_events, [])

    def test_no_attempt_no_record(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)  # o'quvchi hali hech narsa saqlamagan -> urinish yo'q
        self.assertEqual(self.focus(exam['id'], 'blur').json()['recorded'], 0)

    def test_bad_kinds_are_refused_and_teachers_cannot_post(self):
        exam = self.running_exam()
        self.assertEqual(self.focus(exam['id'], 'hack').status_code, 400)
        self.assertEqual(self.focus(exam['id'], 'blur', token=self.teacher_token).status_code, 403)

    def test_the_log_is_capped(self):
        exam = self.running_exam()
        attempt = ExamAttempt.objects.get(exam_id=exam['id'])
        attempt.focus_events = [{'t': 'x', 'kind': 'blur'}] * MAX_FOCUS_EVENTS
        attempt.save()
        self.assertEqual(self.focus(exam['id'], 'blur').json()['recorded'], MAX_FOCUS_EVENTS)
        self.assertEqual(len(ExamAttempt.objects.get(pk=attempt.pk).focus_events), MAX_FOCUS_EVENTS)
