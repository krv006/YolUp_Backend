"""Ota-ona yangi dizayni: imtihonlar ro'yxatida farzandning natijasi (`child_result`) va o'qituvchi izohi (8, 17-bandlar)."""
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User

from .models import ExamAttempt
from .serializers import ManualScoresSerializer
from .tests import ExamTestBase


class ExamChildResultTests(ExamTestBase):
    def exams(self, query='', token=None):
        self.auth(token or self.parent_token)
        return self.client.get(f'/api/v1/exams/{query}')

    def finished_exam(self):
        exam = self.make_exam()
        self.shift(exam['id'], 3)
        self.save(exam['id'], self.answers_for(self.qa))
        self.shift(exam['id'], 18)  # tanaffusdan keyingi B bo'limi
        self.save(exam['id'], self.answers_for(self.qb))
        self.shift(exam['id'], 60)  # imtihon tugagan: natija ko'rinadi
        return exam

    def test_child_result_in_the_list_for_a_finished_exam(self):
        exam = self.finished_exam()
        rows = self.exams(f'?student={self.child_id}').json()
        row = next(r for r in rows if r['id'] == exam['id'])
        result = row['child_result']
        self.assertTrue(result['participated'])
        self.assertIsNotNone(result['score'])
        self.assertIsNotNone(result['max'])
        self.assertIsNone(result['band'])  # IELTS emas: band yo'q
        self.assertEqual(result['teacher_comment'], '')

    def test_no_child_result_without_the_student_param_or_before_the_end(self):
        exam = self.finished_exam()
        plain = next(r for r in self.exams().json() if r['id'] == exam['id'])
        self.assertNotIn('child_result', plain)
        running = self.make_exam(title='Boshqa')
        self.shift(running['id'], 3)
        row = next(r for r in self.exams(f'?student={self.child_id}').json() if r['id'] == running['id'])
        self.assertIsNone(row['child_result'])  # tugamagan imtihon natijasi yashirin

    def test_not_participating_child_gets_participated_false(self):
        exam = self.make_exam()
        self.shift(exam['id'], 60)  # hech kim qatnashmagan, imtihon tugagan
        row = next(r for r in self.exams(f'?student={self.child_id}').json() if r['id'] == exam['id'])
        self.assertEqual(row['child_result']['participated'], False)
        self.assertIsNone(row['child_result']['score'])

    def test_teacher_comment_is_part_of_the_childs_result(self):
        exam = self.finished_exam()
        ExamAttempt.objects.filter(exam_id=exam['id']).update(teacher_comment='Writing Task 2 da argumentlar kuchli.')
        row = next(r for r in self.exams(f'?student={self.child_id}').json() if r['id'] == exam['id'])
        self.assertEqual(row['child_result']['teacher_comment'], 'Writing Task 2 da argumentlar kuchli.')
        self.auth(self.child_token)
        own = self.client.get(f"/api/v1/exams/{exam['id']}/results/").json()['results'][0]
        self.assertEqual(own['teacher_comment'], 'Writing Task 2 da argumentlar kuchli.')

    def test_other_parent_and_unlinked_children_are_forbidden(self):
        outsider = User.objects.get(username='s2')
        self.assertEqual(self.exams(f'?student={outsider.pk}').status_code, 403)
        other_parent = User(username='p9', role=User.Role.PARENT)
        other_parent.set_password('StrongPass123!')
        other_parent.save()
        client = APIClient()
        client.force_authenticate(other_parent)
        self.assertEqual(client.get(f'/api/v1/exams/?student={self.child_id}').status_code, 403)

    def test_manual_score_payload_accepts_a_comment(self):
        serializer = ManualScoresSerializer(data={'scores': {'writing': 6.5}, 'comment': 'Yaxshi'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['comment'], 'Yaxshi')
        self.assertTrue(ManualScoresSerializer(data={'scores': {'writing': 6.5}}).is_valid())
        self.assertFalse(ManualScoresSerializer(data={'scores': {'writing': 6.5}, 'comment': 'x' * 2001}).is_valid())
