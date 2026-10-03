import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.accounts.tests import login, register
from apps.lessons.models import Course
from apps.quizzes.models import Quiz


class WipeDataKeepAccountsTests(APITestCase):
    def setUp(self):
        register(self.client, 't1', 'teacher')
        teacher_token = login(self.client, 't1')
        register(self.client, 'p1', 'parent')
        parent_token = login(self.client, 'p1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {parent_token}')
        self.client.post('/api/v1/auth/children/', {'username': 's1', 'password': 'StrongPass123!'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_token}')
        course_id = self.client.post('/api/v1/courses/', {'title': 'C', 'subject': 'math'}).json()['id']
        quiz = self.client.post('/api/v1/quizzes/', {
            'course': course_id, 'topic': 'T', 'title': 'Q', 'questions': [
                {'text': 'q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]}]}, format='json')
        assert quiz.status_code == 201, quiz.content

    def run_cmd(self, *args):
        out = StringIO()
        call_command('wipe_data_keep_accounts', *args, stdout=out)
        return out.getvalue()

    def counts(self):
        return (User.objects.count(), ParentChildLink.objects.count(),
                Course.objects.count(), Quiz.objects.count())

    def test_dry_run_deletes_nothing(self):
        before = self.counts()
        self.assertGreater(before[2], 0)
        output = self.run_cmd()
        self.assertIn('DRY-RUN', output)
        self.assertEqual(self.counts(), before)

    def test_confirm_requires_nonempty_backup_file(self):
        before = self.counts()
        with self.assertRaises(CommandError):
            self.run_cmd('--confirm')
        with tempfile.NamedTemporaryFile(delete=False) as empty:
            pass
        try:
            with self.assertRaises(CommandError):
                self.run_cmd('--confirm', '--backup-file', empty.name)
        finally:
            os.unlink(empty.name)
        self.assertEqual(self.counts(), before)

    def test_confirm_wipes_everything_but_accounts_and_links(self):
        users, links, courses, quizzes = self.counts()
        self.assertGreater(links, 0)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as backup:
            backup.write(b'-- dump')
        try:
            self.run_cmd('--confirm', '--backup-file', backup.name)
        finally:
            os.unlink(backup.name)
        self.assertEqual(self.counts(), (users, links, 0, 0))

    def test_soft_deleted_courses_and_lessons_are_counted_and_physically_removed(self):
        """`Course`/`Lesson` yumshoq o'chiriladi (`is_deleted=True`) — `objects`
        ularni ko'rsatmaydi va `.delete()` qatorni o'chirmaydi. Oldin buyruq
        shu sababli ularni qoldirib ketgan edi (production'da topilgan)."""
        Course.objects.all().delete()  # yumshoq o'chirish: qator bazada qoladi
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Course.all_objects.count(), 1)

        self.assertIn('lessons.course: 1', self.run_cmd())  # dry-run yashirinni ham sanaydi

        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as backup:
            backup.write(b'-- dump')
        try:
            self.run_cmd('--confirm', '--backup-file', backup.name)
        finally:
            os.unlink(backup.name)
        self.assertEqual(Course.all_objects.count(), 0)
