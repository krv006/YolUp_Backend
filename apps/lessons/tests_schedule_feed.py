"""`GET /schedule/` — darslar va guruhga berilgan testlar bitta jadvalda."""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.homework.tests_hardening import HomeworkBase, make
from apps.lessons.models import Course, Enrollment, Lesson
from apps.quizzes import services
from apps.quizzes.models import Quiz

Q = [{'text': '2 + 2 = ?', 'type': 'single', 'points': 1,
      'options': [{'text': '3', 'is_correct': False, 'order': 0}, {'text': '4', 'is_correct': True, 'order': 1}]}]


class ScheduleFeedTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.now = timezone.now().replace(microsecond=0)
        self.lesson = Lesson.objects.create(
            course=self.course, title='Dars', starts_at=self.now + timedelta(days=1), duration_min=60)
        bank = services.create_quiz(teacher=self.teacher, topic='Qo\'shish', title='Test 1', subject='math', questions=Q)
        self.copy = services.assign_copy(
            teacher=self.teacher, quiz=bank, course=self.course,
            opens_at=self.now + timedelta(days=2), due_at=self.now + timedelta(days=3))

    def feed(self, user, **params):
        params.setdefault('from', (self.now - timedelta(days=1)).date().isoformat())
        params.setdefault('to', (self.now + timedelta(days=10)).date().isoformat())
        return self.api(user).get('/api/v1/schedule/', params)

    def test_lessons_and_quizzes_come_in_one_time_ordered_list(self):
        body = self.feed(self.teacher).json()
        self.assertEqual([(row['type'], row['title']) for row in body['results']], [('lesson', 'Dars'), ('quiz', 'Test 1')])
        self.assertEqual(body['count'], 2)
        quiz = body['results'][1]
        self.assertEqual((quiz['id'], quiz['course']), (str(self.copy.id), str(self.course.id)))
        self.assertIsNotNone(quiz['opens_at'])
        self.assertIsNotNone(quiz['due_at'])
        lesson = body['results'][0]
        self.assertEqual(lesson['ends_at'][:16], (self.lesson.starts_at + timedelta(minutes=60)).isoformat()[:16])

    def test_the_bank_original_and_drafts_are_not_in_the_schedule(self):
        services.create_quiz(teacher=self.teacher, topic='Qoralama', subject='math', questions=Q, status=Quiz.Status.DRAFT)
        titles = [row['title'] for row in self.feed(self.teacher).json()['results']]
        self.assertEqual(titles.count('Test 1'), 1)  # faqat guruhga berilgan nusxa
        self.assertNotIn('Qoralama', titles)

    def test_range_filters_both_kinds(self):
        body = self.feed(self.teacher, **{'from': (self.now + timedelta(days=5)).date().isoformat(),
                                          'to': (self.now + timedelta(days=9)).date().isoformat()}).json()
        self.assertEqual(body['results'], [])
        # test muddati oralig'ga tushsa (ochilgan, hali tugamagan) ham ko'rinadi
        body = self.feed(self.teacher, **{'from': (self.now + timedelta(days=3)).date().isoformat(),
                                          'to': (self.now + timedelta(days=4)).date().isoformat()}).json()
        self.assertEqual([row['type'] for row in body['results']], ['quiz'])

    def test_quiz_without_dates_shows_on_the_day_it_was_given(self):
        bank = services.create_quiz(teacher=self.teacher, topic='X', title='Sanasiz', subject='math', questions=Q)
        services.assign_copy(teacher=self.teacher, quiz=bank, course=self.course)
        today = self.now.date().isoformat()
        rows = self.feed(self.teacher, **{'from': today, 'to': today}).json()['results']
        self.assertEqual([row['title'] for row in rows], ['Sanasiz'])
        self.assertIsNone(rows[0]['ends_at'])

    def test_student_does_not_see_a_quiz_that_is_not_open_yet_or_not_his(self):
        rows = self.feed(self.student).json()['results']
        self.assertEqual([row['type'] for row in rows], ['lesson'])  # opens_at kelajakda — ko'rinmaydi
        self.copy.opens_at = self.now - timedelta(hours=1)
        self.copy.save()
        self.assertEqual([row['type'] for row in self.feed(self.student).json()['results']], ['quiz', 'lesson'])
        s2 = make('s2', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=s2, status=Enrollment.Status.APPROVED)
        self.copy.assigned_students.set([s2])
        self.assertEqual([row['type'] for row in self.feed(self.student).json()['results']], ['lesson'])

    def test_another_teachers_group_is_invisible_and_parent_sees_the_child(self):
        stranger = make('t2', User.Role.TEACHER)
        Course.objects.create(teacher=stranger, title='Boshqa')
        self.assertEqual(self.feed(stranger).json()['results'], [])
        self.copy.opens_at = self.now - timedelta(hours=1)
        self.copy.save()
        self.assertEqual(len(self.feed(self.parent).json()['results']), 2)
        self.assertEqual(len(self.feed(self.parent, student=str(self.student.id)).json()['results']), 2)
        stranger_student = make('s3', User.Role.STUDENT)
        self.assertEqual(self.feed(self.parent, student=str(stranger_student.id)).status_code, 403)

    def test_course_filter(self):
        other = Course.objects.create(teacher=self.teacher, title='Algebra 8', subject=Course.Subject.MATH)
        Lesson.objects.create(course=other, title='Boshqa dars', starts_at=self.now + timedelta(days=1))
        rows = self.feed(self.teacher, course=str(other.id)).json()['results']
        self.assertEqual([row['title'] for row in rows], ['Boshqa dars'])

    def test_validation_and_auth(self):
        self.assertEqual(self.api(self.teacher).get('/api/v1/schedule/').status_code, 400)
        self.assertEqual(self.feed(self.teacher, **{'from': 'xato'}).status_code, 400)
        self.assertEqual(self.feed(self.teacher, **{'from': '2026-12-10', 'to': '2026-12-01'}).status_code, 400)
        self.assertEqual(self.feed(self.teacher, **{'from': '2026-01-01', 'to': '2026-12-31'}).status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/schedule/?from=2026-12-01&to=2026-12-02').status_code, 401)
