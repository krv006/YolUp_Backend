"""Testni guruhga NUSXALAB berish: `POST /quizzes/{id}/assign/` — asl test o'zgarmaydi, bir testni bir nechta guruhga berish mumkin."""
from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.homework.tests_hardening import HomeworkBase, make
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

from . import services
from .models import Option, Question, QuestionGroup, Quiz

QUESTIONS = [
    {'text': '2 + 2 = ?', 'type': 'single', 'points': 2, 'group': 0,
     'options': [{'text': '3', 'is_correct': False, 'order': 0}, {'text': '4', 'is_correct': True, 'order': 1}]},
    {'text': '3 + 3 = ?', 'type': 'single', 'points': 1,
     'options': [{'text': '6', 'is_correct': True, 'order': 0}, {'text': '7', 'is_correct': False, 'order': 1}]},
]


class AssignCopyTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.course2 = Course.objects.create(teacher=self.teacher, title='Algebra · 8-sinf', subject=Course.Subject.MATH)
        self.student2 = make('s2', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course2, student=self.student2, status=Enrollment.Status.APPROVED)
        self.quiz = services.create_quiz(
            teacher=self.teacher, topic='Qo\'shish', title='1-test', subject='math', questions=QUESTIONS,
            groups=[{'title': 'Matn', 'passage': 'Hisoblang'}],
        )
        group = self.quiz.groups.get()
        group.audio.save('a.mp3', ContentFile(b'audio-bytes'))

    def assign(self, quiz, course, **extra):
        return self.api(self.teacher).post(
            f'/api/v1/quizzes/{quiz.id}/assign/', {'course': str(course.id), **extra}, format='json')

    def test_copy_goes_to_the_group_and_the_original_is_untouched(self):
        opens = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self.assign(self.quiz, self.course, opens_at=opens, max_attempts=2)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        copy = Quiz.objects.get(pk=body['id'])
        self.assertNotEqual(copy.pk, self.quiz.pk)
        self.assertEqual((copy.course_id, copy.topic, copy.title, copy.status), (self.course.id, "Qo'shish", '1-test', 'published'))
        self.assertEqual((copy.max_attempts, body['source_quiz_id']), (2, str(self.quiz.pk)))
        self.assertIsNotNone(copy.opens_at)
        self.quiz.refresh_from_db()
        self.assertIsNone(self.quiz.course_id)  # asl test bankda qoladi

    def test_questions_options_answers_and_groups_are_copied(self):
        copy = Quiz.objects.get(pk=self.assign(self.quiz, self.course).json()['id'])
        self.assertEqual(copy.questions.count(), 2)
        first = copy.questions.get(text='2 + 2 = ?')
        self.assertEqual((first.points, first.group.passage), (2, 'Hisoblang'))
        self.assertEqual(list(first.options.order_by('order').values_list('text', 'is_correct')), [('3', False), ('4', True)])
        self.assertEqual(Option.objects.filter(question__quiz=self.quiz).count(), 4)  # asl savollar joyida

    def test_group_audio_is_a_separate_file_so_deleting_one_keeps_the_other(self):
        copy = Quiz.objects.get(pk=self.assign(self.quiz, self.course).json()['id'])
        new_group = copy.groups.get()
        old_group = self.quiz.groups.get()
        self.assertNotEqual(new_group.audio.name, old_group.audio.name)
        self.assertEqual(new_group.audio.read(), b'audio-bytes')
        new_group.delete()
        old_group.refresh_from_db()
        self.assertEqual(old_group.audio.read(), b'audio-bytes')

    def test_the_same_test_can_go_to_several_groups(self):
        first = self.assign(self.quiz, self.course).json()
        second = self.assign(self.quiz, self.course2).json()
        self.assertEqual({first['source_quiz_id'], second['source_quiz_id']}, {str(self.quiz.pk)})
        self.assertEqual(Quiz.objects.filter(source_quiz=self.quiz).count(), 2)
        # nusxaning nusxasi ham asl testga ishora qiladi
        third = self.assign(Quiz.objects.get(pk=first['id']), self.course2).json()
        self.assertEqual(third['source_quiz_id'], str(self.quiz.pk))

    def test_a_test_already_in_a_group_can_still_be_copied(self):
        moved = self.api(self.teacher).patch(
            f'/api/v1/quizzes/{self.quiz.id}/', {'course': str(self.course.id)}, format='json')
        self.assertEqual(moved.status_code, 200, moved.content)
        resp = self.assign(self.quiz, self.course2)  # PATCH shu holatda 400 berardi
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_only_my_group_and_my_test(self):
        stranger = make('t2', User.Role.TEACHER)
        other_course = Course.objects.create(teacher=stranger, title='Boshqa', subject=Course.Subject.MATH)
        self.assertEqual(self.assign(self.quiz, other_course).status_code, 403)
        resp = self.api(stranger).post(
            f'/api/v1/quizzes/{self.quiz.id}/assign/', {'course': str(other_course.id)}, format='json')
        self.assertEqual(resp.status_code, 404)  # begona test ko'rinmaydi
        self.assertEqual(self.api(self.student).post(
            f'/api/v1/quizzes/{self.quiz.id}/assign/', {'course': str(self.course.id)}, format='json').status_code, 403)

    def test_students_subset_and_limits_are_validated(self):
        resp = self.assign(self.quiz, self.course, student_ids=[str(self.student2.id)])  # student2 bu guruhda emas
        self.assertEqual(resp.status_code, 400)
        resp = self.assign(self.quiz, self.course, questions_per_attempt=5)  # testda 2 ta savol
        self.assertEqual(Quiz.objects.filter(source_quiz=self.quiz).count(), 0)
        self.assertEqual(resp.status_code, 400)

    def test_students_are_notified_for_an_open_published_copy(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assign(self.quiz, self.course)
        self.assertTrue(NotificationRecipient.objects.filter(user=self.student).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student2).exists())

    def test_list_search_works_for_the_bank(self):
        self.assign(self.quiz, self.course)
        rows = self.api(self.teacher).get('/api/v1/quizzes/?search=1-test&page_size=200').json()
        rows = rows.get('results', rows)
        self.assertTrue(rows)
        self.assertTrue(all('1-test' in (r['title'] + r['topic']) for r in rows))
        self.assertIn('source_quiz_id', rows[0])

    def test_a_draft_copy_stays_a_draft_and_notifies_nobody(self):
        draft = services.create_quiz(
            teacher=self.teacher, topic='Qoralama', subject='math', questions=QUESTIONS[1:], status=Quiz.Status.DRAFT)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.assign(draft, self.course)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['status'], 'draft')
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student).exists())
