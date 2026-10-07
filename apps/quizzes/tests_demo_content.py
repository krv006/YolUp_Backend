"""IELTS demo testlarini yuklovchi buyruq (`load_mock_samples`)."""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import Notification

from . import demo_content
from .models import Question, QuestionGroup, Quiz
from .serializers import QuestionWriteSerializer


def run(*args):
    out = StringIO()
    call_command('load_mock_samples', *args, stdout=out)
    return out.getvalue()


class DemoContentTests(TestCase):
    def test_every_demo_question_passes_the_real_validation(self):
        for data in demo_content.QUIZZES:
            serializer = QuestionWriteSerializer(data=data['questions'], many=True)
            self.assertTrue(serializer.is_valid(), (data['title'], serializer.errors))
            for question in data['questions']:
                group = question.get('group')
                self.assertTrue(group is None or group < len(data['groups']), data['title'])

    def test_sizes(self):
        self.assertEqual(len(demo_content.READING['questions']), 20)
        self.assertEqual(len(demo_content.READING['groups']), 2)
        self.assertEqual(len(demo_content.LISTENING['questions']), 10)
        self.assertEqual(len(demo_content.WRITING['questions']), 2)
        # Reading'dagi har guruhga 10 tadan savol
        by_group = [sum(1 for q in demo_content.READING['questions'] if q['group'] == g) for g in (0, 1)]
        self.assertEqual(by_group, [10, 10])


class LoadMockSamplesTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='ielts_teacher', password='x', role='teacher')
        self.course = Course.objects.create(teacher=self.teacher, title='IELTS 7.0', subject='english')
        self.student = User.objects.create_user(username='ielts_student', password='x', role='student')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)

    def test_creates_three_published_quizzes_with_groups(self):
        output = run('--teacher', 'ielts_teacher')
        self.assertEqual(output.count('Yaratildi'), 3)
        quizzes = {q.title: q for q in Quiz.objects.filter(author=self.teacher)}
        self.assertEqual(len(quizzes), 3)
        self.assertTrue(all(q.status == Quiz.Status.PUBLISHED for q in quizzes.values()))
        self.assertTrue(all(q.course_id == self.course.id for q in quizzes.values()))
        reading = quizzes['[DEMO] IELTS Reading']
        self.assertEqual(reading.groups.count(), 2)
        self.assertEqual(reading.questions.count(), 20)
        self.assertTrue(all(q.group_id for q in reading.questions.all()))
        self.assertIn('Honeybees', reading.groups.first().passage + reading.groups.last().passage)
        writing = quizzes['[DEMO] IELTS Writing']
        self.assertEqual(list(writing.questions.values_list('type', flat=True)), ['text', 'text'])

    def test_students_are_not_spammed_with_new_quiz_notifications(self):
        run('--teacher', 'ielts_teacher')
        self.assertFalse(Notification.objects.exists())

    def test_idempotent(self):
        run('--teacher', 'ielts_teacher')
        second = run('--teacher', 'ielts_teacher')
        self.assertEqual(second.count('Mavjud'), 3)
        self.assertEqual(Quiz.objects.count(), 3)
        self.assertEqual(QuestionGroup.objects.count(), 4)

    def test_creates_an_ielts_exam_on_request(self):
        from apps.exams.models import Exam

        with self.captureOnCommitCallbacks(execute=True):
            output = run('--teacher', 'ielts_teacher', '--exam-in', '15')
        self.assertIn('Imtihon yaratildi', output)
        exam = Exam.objects.get()
        self.assertEqual(exam.template_key, 'ielts')
        self.assertEqual(exam.course_id, self.course.id)
        self.assertGreater(exam.starts_at, timezone.now() + timedelta(minutes=10))
        self.assertEqual(
            sorted(s.key for s in exam.sections.exclude(kind='offline').exclude(kind='break')),
            ['listening', 'reading', 'writing'],
        )

    def test_remove_deletes_demo_quizzes_but_keeps_those_in_exams(self):
        run('--teacher', 'ielts_teacher', '--exam-in', '15')
        output = run('--teacher', 'ielts_teacher', '--remove')
        self.assertIn("o'tkazib yuborildi: 3", output)
        self.assertEqual(Quiz.objects.count(), 3)
        from apps.exams.models import Exam

        Exam.objects.all().delete()
        output = run('--teacher', 'ielts_teacher', '--remove')
        self.assertIn("O'chirildi: 3", output)
        self.assertEqual(Quiz.objects.count(), 0)

    def test_remove_never_touches_other_quizzes(self):
        other = Quiz.objects.create(course=self.course, author=self.teacher, topic='Mening testim', title='Mening testim')
        Question.objects.create(quiz=other, text='Q')
        run('--teacher', 'ielts_teacher')
        run('--teacher', 'ielts_teacher', '--remove')
        self.assertEqual(list(Quiz.objects.values_list('title', flat=True)), ['Mening testim'])

    def test_clear_errors(self):
        with self.assertRaises(CommandError):
            run('--teacher', 'yoq_odam')
        with self.assertRaises(CommandError):
            run('--teacher', 'ielts_student')  # o'quvchi — o'qituvchi emas
        Course.objects.create(teacher=self.teacher, title='Ikkinchi guruh', subject='english')
        with self.assertRaises(CommandError) as ctx:
            run('--teacher', 'ielts_teacher')
        self.assertIn('--course', str(ctx.exception))
        self.assertIn(str(self.course.id), str(ctx.exception))  # guruhlar ro'yxati ko'rsatiladi
        run('--teacher', 'ielts_teacher', '--course', str(self.course.id))
        self.assertEqual(Quiz.objects.count(), 3)
