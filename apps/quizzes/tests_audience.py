"""Test: guruh/fan majburiy emas; testni guruhdagi faqat ba'zi o'quvchilarga berish (2026-11-10 Trello kartalari)."""
from apps.accounts.models import User
from apps.homework.tests import make
from apps.homework.tests_hardening import HomeworkBase
from apps.lessons.models import Enrollment
from apps.notifications.models import NotificationRecipient

from . import services
from .models import Quiz

QUESTIONS = [{
    'text': '2 + 2 = ?', 'type': 'single', 'points': 1,
    'options': [{'text': '3', 'is_correct': False, 'order': 0}, {'text': '4', 'is_correct': True, 'order': 1}],
}]


class OptionalGroupTests(HomeworkBase):
    def test_a_quiz_can_be_created_without_group_and_without_subject(self):
        resp = self.api(self.teacher).post('/api/v1/quizzes/', {
            'topic': 'Umumiy test', 'questions': QUESTIONS,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        quiz = Quiz.objects.get(pk=resp.data['id'])
        self.assertEqual((quiz.course_id, quiz.subject, quiz.author_id), (None, '', self.teacher.id))

    def test_students_do_not_see_a_groupless_quiz(self):
        self.api(self.teacher).post('/api/v1/quizzes/', {'topic': 'Umumiy', 'questions': QUESTIONS}, format='json')
        listed = self.api(self.student).get('/api/v1/quizzes/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data.get('results', listed.data)), 0)


class QuizAudienceTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.second = make('s2', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=self.second, status=Enrollment.Status.APPROVED)
        self.quiz = services.create_quiz(
            teacher=self.teacher, topic="Qo'shish", course=self.course, questions=QUESTIONS,
            status=Quiz.Status.PUBLISHED,
        )

    def sees(self, user) -> bool:
        listed = self.api(user).get('/api/v1/quizzes/')
        self.assertEqual(listed.status_code, 200)
        return str(self.quiz.id) in [str(i['id']) for i in listed.data.get('results', listed.data)]

    def put(self, ids, user=None):
        return self.api(user or self.teacher).put(
            f'/api/v1/quizzes/{self.quiz.id}/audience/', {'student_ids': [str(i) for i in ids]}, format='json')

    def attempt(self, user):
        question = self.quiz.questions.first()
        option = question.options.filter(is_correct=True).first()
        return self.api(user).post(f'/api/v1/quizzes/{self.quiz.id}/attempts/', {
            'answers': [{'question': str(question.id), 'selected_option': str(option.id)}],
        }, format='json')

    def test_by_default_everyone_in_the_group_gets_the_quiz(self):
        data = self.api(self.teacher).get(f'/api/v1/quizzes/{self.quiz.id}/audience/').data
        self.assertEqual((data['restricted'], data['total'], data['assigned_count']), (False, 2, 2))
        self.assertTrue(all(r['can_attend'] for r in data['students']))
        self.assertTrue(self.sees(self.student) and self.sees(self.second))

    def test_giving_the_quiz_to_one_student_hides_it_from_the_other(self):
        resp = self.put([self.student.id])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.data['restricted'], resp.data['assigned_count']), (True, 1))
        rows = {r['username']: r for r in resp.data['students']}
        self.assertTrue(rows[self.student.username]['can_attend'])
        self.assertFalse(rows[self.second.username]['can_attend'])
        self.assertTrue(self.sees(self.student))
        self.assertFalse(self.sees(self.second))

    def test_a_student_who_was_not_given_the_quiz_cannot_submit_it(self):
        self.put([self.student.id])
        self.assertEqual(self.attempt(self.second).status_code, 404)  # test unga umuman ko'rinmaydi
        self.assertEqual(self.attempt(self.student).status_code, 201)

    def test_service_level_guard_rejects_an_unassigned_student_too(self):
        from rest_framework.exceptions import PermissionDenied

        self.put([self.student.id])
        question = self.quiz.questions.first()
        with self.assertRaises(PermissionDenied):
            services.submit_attempt(student=self.second, quiz=self.quiz, answers=[{'question': question}])

    def test_the_parent_of_an_excluded_student_does_not_see_it(self):
        self.put([self.second.id])  # self.student (ota-onasi self.parent) tashqarida
        self.assertFalse(self.sees(self.parent))

    def test_attempted_flag_is_reported(self):
        self.attempt(self.student)
        rows = {r['username']: r for r in self.api(self.teacher).get(
            f'/api/v1/quizzes/{self.quiz.id}/audience/').data['students']}
        self.assertTrue(rows[self.student.username]['attempted'])
        self.assertFalse(rows[self.second.username]['attempted'])

    def test_selecting_everybody_or_nobody_removes_the_restriction(self):
        self.put([self.student.id])
        self.assertTrue(self.put([self.student.id, self.second.id]).data['restricted'] is False)
        self.put([self.student.id])
        self.assertTrue(self.put([]).data['restricted'] is False)
        self.assertTrue(self.sees(self.second))

    def test_cannot_pick_someone_outside_the_group_or_use_someone_elses_quiz(self):
        outsider = make('s3', User.Role.STUDENT)
        self.assertEqual(self.put([outsider.id]).status_code, 400)
        other_teacher = make('t2', User.Role.TEACHER)
        self.assertIn(self.put([self.student.id], user=other_teacher).status_code, (403, 404))

    def test_a_groupless_quiz_cannot_be_split_between_students(self):
        groupless = services.create_quiz(
            teacher=self.teacher, topic='x', questions=QUESTIONS, status=Quiz.Status.PUBLISHED)
        resp = self.api(self.teacher).put(
            f'/api/v1/quizzes/{groupless.id}/audience/', {'student_ids': [str(self.student.id)]}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_patch_with_student_ids_and_the_detail_shows_them(self):
        resp = self.api(self.teacher).patch(
            f'/api/v1/quizzes/{self.quiz.id}/', {'student_ids': [str(self.student.id)]}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data['student_ids'], [str(self.student.id)])
        detail = self.api(self.teacher).get(f'/api/v1/quizzes/{self.quiz.id}/')
        self.assertEqual(detail.data['student_ids'], [str(self.student.id)])

    def test_students_never_see_the_audience_list(self):
        detail = self.api(self.student).get(f'/api/v1/quizzes/{self.quiz.id}/')
        self.assertNotIn('student_ids', detail.data)

    def test_new_quiz_created_for_selected_students_notifies_only_them(self):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.api(self.teacher).post('/api/v1/quizzes/', {
                'course': str(self.course.id), 'topic': 'Tanlanganlar', 'questions': QUESTIONS,
                'student_ids': [str(self.second.id)],
            }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(NotificationRecipient.objects.filter(user=self.second).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student).exists())

    def test_students_added_later_get_a_notification(self):
        self.put([self.student.id])
        NotificationRecipient.objects.all().delete()
        # ikkinchi o'quvchini qo'shish: avval faqat bittasi (cheklangan), endi ikkinchi qo'shiladi
        third = make('s4', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=third, status=Enrollment.Status.APPROVED)
        with self.captureOnCommitCallbacks(execute=True):
            self.put([self.student.id, third.id])
        self.assertTrue(NotificationRecipient.objects.filter(user=third).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student).exists())
