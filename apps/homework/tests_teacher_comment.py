"""O'qituvchi izohi: `teacher_comment` alohida maydon — AI qayta tekshirsa ham yo'qolmaydi."""
from .models import Submission
from .tests_hardening import HomeworkBase


class TeacherCommentTests(HomeworkBase):
    def pending(self):
        return self.submit(self.assignment()).data['id']

    def test_comment_is_saved_trimmed_and_shown_to_the_student_after_approval(self):
        submission_id = self.pending()
        resp = self.review(submission_id, {'overall_score': 80, 'teacher_comment': '  Yaxshi ish, 3-misolni qayta ko\'ring.  '})
        self.assertEqual((resp.status_code, resp.data['teacher_comment']), (200, "Yaxshi ish, 3-misolni qayta ko'ring."))
        mine = self.api(self.student).get(f'/api/v1/homework/submissions/{submission_id}/').json()
        self.assertEqual(mine['teacher_comment'], "Yaxshi ish, 3-misolni qayta ko'ring.")

    def test_comment_is_hidden_while_waiting_and_from_parent_when_not_shared(self):
        submission_id = self.pending()
        self.review(submission_id, {'overall_score': 80, 'teacher_comment': 'Izoh', 'share_with_parent': False})
        self.assertEqual(self.api(self.parent).get(f'/api/v1/homework/submissions/{submission_id}/').json()['teacher_comment'], '')
        self.assertEqual(self.api(self.student).get(f'/api/v1/homework/submissions/{submission_id}/').json()['teacher_comment'], 'Izoh')
        Submission.objects.filter(pk=submission_id).update(status=Submission.Status.PENDING_REVIEW)
        self.assertEqual(self.api(self.student).get(f'/api/v1/homework/submissions/{submission_id}/').json()['teacher_comment'], '')

    def test_old_clients_can_still_send_the_comment_inside_result(self):
        submission_id = self.pending()
        resp = self.review(submission_id, {'overall_score': 70, 'result': {'summary': 'x', 'teacher_comment': 'Eski usul'}})
        self.assertEqual(resp.data['teacher_comment'], 'Eski usul')
        # alohida maydon berilsa u ustun
        resp = self.review(submission_id, {'overall_score': 70, 'result': {'teacher_comment': 'Eski'}, 'teacher_comment': 'Yangi'})
        self.assertEqual(resp.data['teacher_comment'], 'Yangi')

    def test_comment_survives_the_ai_result_being_replaced_and_can_be_cleared(self):
        submission_id = self.pending()
        self.review(submission_id, {'overall_score': 70, 'teacher_comment': 'Saqlanadi'})
        Submission.objects.filter(pk=submission_id).update(result={'summary': 'AI yangi natija'})  # qayta tekshirish `result`ni almashtiradi
        self.assertEqual(Submission.objects.get(pk=submission_id).teacher_comment, 'Saqlanadi')
        resp = self.review(submission_id, {'overall_score': 75})  # izoh berilmasa tegilmaydi
        self.assertEqual(resp.data['teacher_comment'], 'Saqlanadi')
        self.assertEqual(self.review(submission_id, {'overall_score': 75, 'teacher_comment': ''}).data['teacher_comment'], '')

    def test_comment_must_be_text_and_is_capped(self):
        submission_id = self.pending()
        self.assertEqual(self.review(submission_id, {'overall_score': 70, 'teacher_comment': ['x']}).status_code, 400)
        resp = self.review(submission_id, {'overall_score': 70, 'teacher_comment': 'a' * 5000})
        self.assertEqual(len(resp.data['teacher_comment']), 2000)
