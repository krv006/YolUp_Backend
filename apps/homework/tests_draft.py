"""Uy vazifasi topshirish qoralamasi."""
from .models import SubmissionDraft
from .tests_hardening import HomeworkBase


class SubmissionDraftTests(HomeworkBase):
    def url(self, assignment_id):
        return f'/api/v1/homework/assignments/{assignment_id}/draft/'

    def test_roundtrip_per_student(self):
        assignment_id = self.assignment()
        api = self.api(self.student)
        self.assertEqual(api.get(self.url(assignment_id)).json()['comment'], '')
        self.assertEqual(api.put(self.url(assignment_id), {'comment': 'Yarmi tayyor'}, format='json').status_code, 200)
        self.assertEqual(api.get(self.url(assignment_id)).json()['comment'], 'Yarmi tayyor')
        self.assertEqual(api.put(self.url(assignment_id), {'comment': 'Yangilandi'}, format='json').json()['comment'], 'Yangilandi')
        self.assertEqual(SubmissionDraft.objects.count(), 1)
        self.assertEqual(api.delete(self.url(assignment_id)).status_code, 204)
        self.assertEqual(api.delete(self.url(assignment_id)).status_code, 204)  # takroriy chaqiruv xato emas
        self.assertFalse(SubmissionDraft.objects.exists())

    def test_teacher_has_no_draft_endpoint(self):
        assignment_id = self.assignment()
        self.assertEqual(self.api(self.teacher).put(self.url(assignment_id), {'comment': 'x'}, format='json').status_code, 403)

    def test_unknown_assignment_is_404(self):
        self.assertEqual(self.api(self.student).get(self.url('00000000-0000-0000-0000-000000000000')).status_code, 404)
