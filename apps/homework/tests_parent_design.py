"""Ota-ona yangi dizayni: farzand vazifalari ro'yxati, guruh statistikasi, eslatma, ichki xato yashirilishi, muddat xabari (16, 18-bandlar)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.homework import services
from apps.homework.models import Assignment, Submission
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import Notification, NotificationRecipient

PASSWORD = 'StrongPass123!'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class Fixture(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.parent = make('p1', User.Role.PARENT)
        self.other_parent = make('p2', User.Role.PARENT)
        self.toshmat = make('s1', User.Role.STUDENT, first_name='Toshmat')
        self.aziza = make('s2', User.Role.STUDENT, first_name='Aziza')
        self.rival = make('s3', User.Role.STUDENT)
        self.english = Course.objects.create(teacher=self.teacher, title='Ingliz tili')
        self.math = Course.objects.create(teacher=self.teacher, title='Matematika')
        for course, students in ((self.english, (self.toshmat, self.aziza, self.rival)), (self.math, (self.toshmat,))):
            for student in students:
                Enrollment.objects.create(course=course, student=student, status=Enrollment.Status.APPROVED)
        for child in (self.toshmat, self.aziza):
            ParentChildLink.objects.create(parent=self.parent, student=child, status=ParentChildLink.Status.APPROVED)
        self.hw_en = Assignment.objects.create(course=self.english, title='Essay', status=Assignment.Status.ACTIVE)
        self.hw_math = Assignment.objects.create(course=self.math, title='Tenglamalar', status=Assignment.Status.ACTIVE)
        self.draft = Assignment.objects.create(course=self.english, title='Qoralama', status=Assignment.Status.DRAFT)

    def sub(self, student, assignment, status=Submission.Status.DONE, score=None, **extra):
        return Submission.objects.create(
            assignment=assignment, student=student, file='x.pdf', original_name='x.pdf', status=status, overall_score=score, **extra,
        )

    def child_list(self, child, query='', user=None):
        return client_for(user or self.parent).get(f'/api/v1/homework/assignments/?student={child.pk}{query}')


class ChildAssignmentListTests(Fixture):
    def test_lists_active_assignments_of_all_the_childs_courses(self):
        body = self.child_list(self.toshmat).json()
        self.assertEqual({row['title'] for row in body}, {'Essay', 'Tenglamalar'})  # qoralama yo'q
        self.assertEqual({row['course_title'] for row in body}, {'Ingliz tili', 'Matematika'})
        self.assertTrue(all(row['student_id'] == str(self.toshmat.pk) for row in body))
        only_math = self.child_list(self.toshmat, f'&course={self.math.pk}').json()
        self.assertEqual([row['title'] for row in only_math], ['Tenglamalar'])
        azizas = self.child_list(self.aziza).json()
        self.assertEqual([row['title'] for row in azizas], ['Essay'])  # Aziza faqat ingliz tilida

    def test_my_submission_belongs_to_the_requested_child_even_in_a_shared_course(self):
        self.sub(self.aziza, self.hw_en, score=95)
        toshmat_rows = {row['title']: row for row in self.child_list(self.toshmat).json()}
        self.assertIsNone(toshmat_rows['Essay']['my_submission'])  # opasining topshirig'i emas
        aziza_rows = {row['title']: row for row in self.child_list(self.aziza).json()}
        self.assertEqual(aziza_rows['Essay']['my_submission']['student_id'], str(self.aziza.pk))

    def test_group_stats_only_for_a_confirmed_and_shared_result(self):
        self.sub(self.toshmat, self.hw_en, score=80)
        self.sub(self.aziza, self.hw_en, score=90)
        self.sub(self.rival, self.hw_en, score=60)
        row = next(r for r in self.child_list(self.toshmat).json() if r['title'] == 'Essay')
        self.assertEqual(row['group_stats'], {'average': 7.7, 'rank': 2, 'total': 3})  # (80+90+60)/3/10
        self.assertEqual(next(r for r in self.child_list(self.aziza).json() if r['title'] == 'Essay')['group_stats']['rank'], 1)
        Submission.objects.filter(student=self.toshmat, assignment=self.hw_en).update(share_with_parent=False)
        hidden = next(r for r in self.child_list(self.toshmat).json() if r['title'] == 'Essay')
        self.assertIsNone(hidden['group_stats'])
        self.assertIsNone(hidden['my_submission']['overall_score'])
        pending = self.sub(self.toshmat, self.hw_math, status=Submission.Status.PENDING_REVIEW, score=99)
        math_row = next(r for r in self.child_list(self.toshmat).json() if r['title'] == 'Tenglamalar')
        self.assertIsNone(math_row['group_stats'])  # tasdiqlanmagan AI taklifi ko'rinmaydi
        self.assertIsNone(math_row['my_submission']['overall_score'])
        self.assertIsNotNone(pending)

    def test_internal_error_text_is_not_shown_to_parents_but_students_still_see_it(self):
        self.sub(self.toshmat, self.hw_en, status=Submission.Status.ERROR, error="AI baholay olmadi — o'zingiz baholang")
        row = next(r for r in self.child_list(self.toshmat).json() if r['title'] == 'Essay')
        self.assertEqual(row['my_submission']['error'], '')
        student_rows = client_for(self.toshmat).get(f'/api/v1/homework/assignments/?course={self.english.pk}').json()
        mine = next(r for r in student_rows if r['title'] == 'Essay')['my_submission']
        self.assertIn('AI baholay olmadi', mine['error'])
        parent_course_rows = client_for(self.parent).get(f'/api/v1/homework/assignments/?course={self.english.pk}').json()
        self.assertEqual(next(r for r in parent_course_rows if r['title'] == 'Essay')['my_submission']['error'], '')

    def test_access_rules(self):
        self.assertEqual(self.child_list(self.toshmat, user=self.other_parent).status_code, 403)
        ParentChildLink.objects.filter(student=self.toshmat).update(status=ParentChildLink.Status.PENDING)
        self.assertEqual(self.child_list(self.toshmat).status_code, 403)
        self.assertEqual(APIClient().get(f'/api/v1/homework/assignments/?student={self.toshmat.pk}').status_code, 401)


class RemindChildTests(Fixture):
    def url(self, assignment=None):
        return f'/api/v1/homework/assignments/{(assignment or self.hw_en).pk}/remind-child/'

    def post(self, student=None, user=None, assignment=None):
        return client_for(user or self.parent).post(self.url(assignment), {'student': str((student or self.toshmat).pk)}, format='json')

    def test_reminder_reaches_the_child_once_per_hour(self):
        first = self.post()
        self.assertEqual(first.status_code, 200, first.content)
        self.assertTrue(first.json()['sent'])
        (item,) = NotificationRecipient.objects.filter(user=self.toshmat, notification__kind='homework_reminder').select_related('notification')
        self.assertEqual(item.notification.link_type, 'assignment')
        self.assertEqual(item.notification.link_id, str(self.hw_en.pk))
        self.assertTrue(item.notification.data['from_parent'])
        second = self.post()
        self.assertEqual(second.status_code, 429)
        self.assertGreater(second.json()['error']['retry_after'], 0)
        Notification.objects.filter(pk=item.notification.pk).update(created_at=timezone.now() - timedelta(minutes=61))
        self.assertEqual(self.post().status_code, 200)

    def test_per_child_and_per_assignment_limits_are_independent(self):
        self.post()
        self.assertEqual(self.post(student=self.aziza).status_code, 200)
        self.assertEqual(self.post(assignment=self.hw_math).status_code, 200)

    def test_cannot_remind_about_a_submitted_or_foreign_assignment(self):
        self.sub(self.toshmat, self.hw_en, status=Submission.Status.PENDING_REVIEW)
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.post(student=self.aziza, assignment=self.hw_math).status_code, 404)  # Aziza matematikada emas
        self.assertEqual(self.post(assignment=self.draft).status_code, 404)  # qoralama

    def test_permissions(self):
        self.assertEqual(self.post(user=self.other_parent).status_code, 403)
        self.assertEqual(self.post(user=self.teacher).status_code, 403)
        self.assertEqual(self.post(user=self.toshmat).status_code, 403)
        self.assertEqual(client_for(self.parent).post(self.url(), {}, format='json').status_code, 400)

    def test_resubmit_requested_child_can_still_be_reminded(self):
        self.sub(self.toshmat, self.hw_en, status=Submission.Status.RESUBMIT_REQUESTED)
        self.assertEqual(self.post().status_code, 200)


class ParentDueSoonTests(Fixture):
    def setUp(self):
        super().setUp()
        self.quiet_parent = make('p3', User.Role.PARENT, notify_homework_due=False)
        ParentChildLink.objects.create(parent=self.quiet_parent, student=self.toshmat, status=ParentChildLink.Status.APPROVED)
        now = timezone.now()
        self.hw_en.due_at = now + timedelta(hours=20)
        self.hw_en.save(update_fields=['due_at'])
        Assignment.objects.filter(pk=self.hw_en.pk).update(created_at=now - timedelta(days=1))
        self.now = now

    def sent(self, user):
        return list(NotificationRecipient.objects.filter(user=user, notification__kind='homework_due_soon').select_related('notification'))

    def test_parents_of_pending_students_are_told_a_day_before(self):
        result = services.send_deadline_reminders(now=self.now)
        self.assertEqual(result['parents'], 2)  # Toshmat va Aziza uchun bittadan xabar; Rivalning ota-onasi yo'q
        (item,) = [i for i in self.sent(self.parent) if i.notification.data['student_id'] == str(self.toshmat.pk)]
        self.assertEqual(item.notification.data['assignment_id'], str(self.hw_en.pk))
        self.assertEqual(item.notification.link_type, 'assignment')
        self.assertEqual(len(self.sent(self.parent)), 2)  # ikki farzand uchun alohida
        self.assertEqual(self.sent(self.quiet_parent), [])  # notify_homework_due o'chirilgan

    def test_parent_who_disabled_it_gets_nothing_and_it_is_sent_only_once(self):
        services.send_deadline_reminders(now=self.now)
        self.assertEqual(self.sent(self.quiet_parent), [])
        again = services.send_deadline_reminders(now=self.now + timedelta(minutes=5))
        self.assertEqual(again['parents'], 0)
        self.assertEqual(len(self.sent(self.parent)), 2)

    def test_submitted_students_are_skipped_and_far_deadlines_wait(self):
        self.sub(self.toshmat, self.hw_en, status=Submission.Status.PENDING_REVIEW)
        services.send_deadline_reminders(now=self.now)
        rows = self.sent(self.parent)
        self.assertEqual([r.notification.data['student_id'] for r in rows], [str(self.aziza.pk)])
        Assignment.objects.filter(pk=self.hw_en.pk).update(reminder_parents_sent_at=None, due_at=self.now + timedelta(days=3))
        NotificationRecipient.objects.all().delete()
        self.assertEqual(services.send_deadline_reminders(now=self.now)['parents'], 0)  # hali 24 soatdan ko'p
