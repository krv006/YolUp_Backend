"""Guruhsiz testni (masalan, AI fan bo'yicha yaratgan) o'qituvchining guruhiga biriktirish: PATCH {course}."""
from apps.homework.tests_hardening import HomeworkBase
from apps.lessons.models import Course
from apps.notifications.models import NotificationRecipient

from . import services
from .models import Quiz

QUESTIONS = [{
    'text': '2 + 2 = ?', 'type': 'single', 'points': 1,
    'options': [{'text': '3', 'is_correct': False, 'order': 0}, {'text': '4', 'is_correct': True, 'order': 1}],
}]


class MoveQuizToGroupTests(HomeworkBase):
    def quiz(self, *, course=None, status=Quiz.Status.PUBLISHED):
        return services.create_quiz(
            teacher=self.teacher, topic="Qo'shish", course=course, subject='math', questions=QUESTIONS, status=status,
        )

    def patch(self, quiz, payload, user=None):
        return self.api(user or self.teacher).patch(f'/api/v1/quizzes/{quiz.id}/', payload, format='json')

    def student_sees(self, quiz) -> bool:
        listed = self.api(self.student).get('/api/v1/quizzes/')
        self.assertEqual(listed.status_code, 200)
        return str(quiz.id) in [str(item['id']) for item in listed.data.get('results', listed.data)]

    def test_a_groupless_quiz_can_be_given_to_my_group(self):
        quiz = self.quiz()
        self.assertFalse(self.student_sees(quiz))
        resp = self.patch(quiz, {'course': str(self.course.id)})
        self.assertEqual(resp.status_code, 200, resp.content)
        quiz.refresh_from_db()
        self.assertEqual((quiz.course_id, quiz.subject), (self.course.id, 'math'))
        self.assertTrue(self.student_sees(quiz))

    def test_students_are_notified_when_a_published_quiz_arrives(self):
        quiz = self.quiz()
        with self.captureOnCommitCallbacks(execute=True):
            self.patch(quiz, {'course': str(self.course.id)})
        self.assertTrue(NotificationRecipient.objects.filter(user=self.student).exists())

    def test_an_ai_draft_is_not_published_by_the_move(self):
        quiz = self.quiz(status=Quiz.Status.DRAFT)
        resp = self.patch(quiz, {'course': str(self.course.id)})
        self.assertEqual(resp.status_code, 200, resp.content)
        quiz.refresh_from_db()
        self.assertEqual((quiz.course_id, quiz.status), (self.course.id, Quiz.Status.DRAFT))
        self.assertFalse(self.student_sees(quiz))  # o'qituvchi tekshirib e'lon qilmaguncha ko'rinmaydi

    def test_cannot_move_into_someone_elses_group(self):
        other = Course.objects.create(teacher=self.parent, title='Boshqa', subject='math')
        self.assertEqual(self.patch(self.quiz(), {'course': str(other.id)}).status_code, 403)

    def test_only_the_author_can_move_it(self):
        quiz = self.quiz()
        self.assertEqual(self.patch(quiz, {'course': str(self.course.id)}, user=self.student).status_code, 403)

    def test_cannot_move_a_quiz_that_already_has_a_group(self):
        quiz = self.quiz(course=self.course)
        second = Course.objects.create(teacher=self.teacher, title='Geometriya', subject='math')
        self.assertEqual(self.patch(quiz, {'course': str(second.id)}).status_code, 400)

    def test_sending_the_same_group_again_is_harmless(self):
        quiz = self.quiz(course=self.course)
        self.assertEqual(self.patch(quiz, {'course': str(self.course.id)}).status_code, 200)

    def test_ordinary_edits_still_work_without_a_course(self):
        quiz = self.quiz(course=self.course)
        resp = self.patch(quiz, {'title': 'Yangi nom'})
        self.assertEqual((resp.status_code, resp.data['title']), (200, 'Yangi nom'))
