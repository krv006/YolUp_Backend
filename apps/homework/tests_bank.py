"""Uy vazifasi: Google Form havolasi, vazifalar bazasi, guruh(lar)ga/o'quvchilarga biriktirish (2026-11-11)."""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

from .models import Assignment
from .tests import make
from .tests_hardening import HomeworkBase

FORM = 'https://docs.google.com/forms/d/e/1FAIpQLSabc/viewform'


class GoogleFormUrlTests(HomeworkBase):
    def create(self, url=None, **extra):
        body = {'course_id': str(self.course.id), 'title': 'Forma', **extra}
        if url is not None:
            body['google_form_url'] = url
        return self.api(self.teacher).post('/api/v1/homework/assignments/', body, format='json')

    def test_a_google_form_link_is_saved_and_everyone_sees_it(self):
        r = self.create(FORM)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['google_form_url'], FORM)
        aid = r.data['id']
        for user in (self.teacher, self.student, self.parent):
            got = self.api(user).get(f'/api/v1/homework/assignments/{aid}/')
            self.assertEqual(got.status_code, 200)
            self.assertEqual(got.data['google_form_url'], FORM)
        listed = self.api(self.student).get(f'/api/v1/homework/assignments/?course={self.course.id}')
        self.assertEqual(listed.data[0]['google_form_url'], FORM)

    def test_short_forms_gle_links_work_and_foreign_links_are_rejected(self):
        self.assertEqual(self.create('https://forms.gle/AbCd123').status_code, 201)
        for bad in ('http://docs.google.com/forms/d/x', 'https://evil.example.com/forms', 'https://docs.google.com/document/d/x', 'javascript:alert(1)'):
            r = self.create(bad)
            self.assertEqual(r.status_code, 400, bad)

    def test_patch_changes_and_clears_it(self):
        aid = self.create(FORM).data['id']
        r = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{aid}/', {'google_form_url': 'https://forms.gle/Zz9'}, format='json')
        self.assertEqual(r.data['google_form_url'], 'https://forms.gle/Zz9')
        r = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{aid}/', {'google_form_url': ''}, format='json')
        self.assertEqual(r.data['google_form_url'], '')

    def test_a_form_only_assignment_can_be_submitted_with_a_comment(self):
        aid = self.create(FORM).data['id']
        r = self.api(self.student).post(f'/api/v1/homework/assignments/{aid}/submit/', {'comment': "Formani to'ldirdim"}, format='multipart')
        self.assertEqual(r.status_code, 201, r.content)


class BankBase(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.s2 = make('s2', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=self.s2, status=Enrollment.Status.APPROVED)
        self.course2 = Course.objects.create(teacher=self.teacher, title='Geometriya', subject=Course.Subject.MATH)
        self.s3 = make('s3', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course2, student=self.s3, status=Enrollment.Status.APPROVED)

    def bank(self, **extra):
        r = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'title': 'Bazadagi vazifa', 'body': '<p>Hal qiling</p>', 'questions': [
                {'type': 'single', 'text': '2+2', 'options': ['3', '4'], 'correct': [1], 'points': 2}], **extra}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        return r.data['id']

    def assign(self, aid, user=None, **body):
        due = (timezone.now() + timedelta(days=3)).isoformat()
        return self.api(user or self.teacher).post(f'/api/v1/homework/assignments/{aid}/assign/', {'due_at': due, **body}, format='json')


class HomeworkBankTests(BankBase):
    def test_a_groupless_assignment_goes_to_the_bank_and_only_the_author_sees_it(self):
        aid = self.bank()
        a = Assignment.objects.get(pk=aid)
        self.assertEqual((a.course_id, a.status, a.author_id), (None, Assignment.Status.BANK, self.teacher.id))
        listed = self.api(self.teacher).get('/api/v1/homework/assignments/?bank=1')
        self.assertEqual([r['id'] for r in listed.data], [aid])
        self.assertTrue(listed.data[0]['is_bank'])
        self.assertEqual(self.api(self.student).get(f'/api/v1/homework/assignments/{aid}/').status_code, 404)
        self.assertEqual(self.api(self.student).get('/api/v1/homework/assignments/?bank=1').status_code, 403)
        other = make('t_other', User.Role.TEACHER)
        self.assertEqual(self.api(other).get(f'/api/v1/homework/assignments/{aid}/').status_code, 404)
        self.assertEqual(self.api(other).get('/api/v1/homework/assignments/?bank=1').data, [])

    def test_nobody_can_submit_to_a_bank_assignment(self):
        aid = self.bank()
        r = self.api(self.student).post(f'/api/v1/homework/assignments/{aid}/submit/', {'comment': 'x'}, format='multipart')
        self.assertEqual(r.status_code, 404)

    def test_bank_assignment_can_be_edited_and_deleted_by_the_author(self):
        aid = self.bank()
        r = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{aid}/', {'title': 'Yangi nom'}, format='json')
        self.assertEqual((r.status_code, r.data['title']), (200, 'Yangi nom'))
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/homework/assignments/{aid}/').status_code, 204)

    def test_assign_to_one_group_makes_a_copy_with_questions_and_notifies_the_students(self):
        aid = self.bank(google_form_url=FORM)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.assign(aid, course_ids=[str(self.course.id)])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['count'], 1)
        copy = Assignment.objects.get(pk=r.data['assignments'][0]['id'])
        self.assertEqual((copy.course_id, copy.status, copy.source_id, copy.google_form_url), (self.course.id, 'active', uuid_of(aid), FORM))
        self.assertEqual(copy.questions.count(), 1)
        self.assertTrue(copy.due_at)
        self.assertTrue(NotificationRecipient.objects.filter(user=self.student).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.s3).exists())  # boshqa guruh
        listed = self.api(self.student).get(f'/api/v1/homework/assignments/?course={self.course.id}')
        self.assertEqual([r['id'] for r in listed.data], [str(copy.id)])
        # bankdagi asl vazifa saqlanib qoladi va qayta berish mumkin
        again = self.assign(aid, course_ids=[str(self.course2.id)])
        self.assertEqual(again.status_code, 201)
        self.assertEqual(Assignment.objects.filter(source_id=uuid_of(aid)).count(), 2)

    def test_assign_to_several_groups_creates_a_copy_for_each(self):
        aid = self.bank()
        r = self.assign(aid, course_ids=[str(self.course.id), str(self.course2.id)])
        self.assertEqual((r.status_code, r.data['count']), (201, 2))
        self.assertEqual({a['course_id'] for a in r.data['assignments']}, {str(self.course.id), str(self.course2.id)})

    def test_assign_to_selected_students_only(self):
        aid = self.bank()
        r = self.assign(aid, student_ids=[str(self.student.id)])  # guruh o'zi aniqlanadi
        self.assertEqual(r.status_code, 201, r.content)
        copy = Assignment.objects.get(pk=r.data['assignments'][0]['id'])
        self.assertEqual(copy.course_id, self.course.id)
        self.assertEqual(list(copy.assigned_students.values_list('pk', flat=True)), [self.student.pk])
        self.assertTrue(self.api(self.student).get(f'/api/v1/homework/assignments/{copy.id}/').status_code == 200)
        self.assertEqual(self.api(self.s2).get(f'/api/v1/homework/assignments/{copy.id}/').status_code, 404)
        self.assertEqual(self.api(self.s2).get(f'/api/v1/homework/assignments/?course={self.course.id}').data, [])
        self.assertEqual(self.api(self.parent).get(f'/api/v1/homework/assignments/{copy.id}/').status_code, 200)  # o'quvchining ota-onasi

    def test_students_from_two_groups_get_a_copy_per_group(self):
        aid = self.bank()
        r = self.assign(aid, student_ids=[str(self.student.id), str(self.s3.id)])
        self.assertEqual((r.status_code, r.data['count']), (201, 2))

    def test_group_plus_extra_student_from_another_group(self):
        aid = self.bank()
        r = self.assign(aid, course_ids=[str(self.course.id)], student_ids=[str(self.s2.id), str(self.s3.id)])
        self.assertEqual((r.status_code, r.data['count']), (201, 2))  # s2 — tanlangan guruhda (allaqachon), s3 — o'z guruhiga
        by_course = {a['course_id']: Assignment.objects.get(pk=a['id']) for a in r.data['assignments']}
        self.assertFalse(by_course[str(self.course.id)].assigned_students.exists())  # butun guruh
        self.assertEqual(list(by_course[str(self.course2.id)].assigned_students.values_list('pk', flat=True)), [self.s3.pk])

    def test_validation(self):
        aid = self.bank()
        self.assertEqual(self.assign(aid).status_code, 400)  # kimga ekani yo'q
        other = make('t_other2', User.Role.TEACHER)
        foreign = Course.objects.create(teacher=other, title='Boshqa')
        self.assertEqual(self.assign(aid, course_ids=[str(foreign.id)]).status_code, 403)
        outsider = make('s_out', User.Role.STUDENT)
        self.assertEqual(self.assign(aid, student_ids=[str(outsider.id)]).status_code, 400)
        self.assertEqual(self.assign(aid, user=other, course_ids=[str(self.course.id)]).status_code, 404)  # boshqa o'qituvchining bazasi
        self.assertEqual(self.assign(aid, user=self.student, course_ids=[str(self.course.id)]).status_code, 403)
        self.assertEqual(self.assign(aid, course_ids=['nope']).status_code, 400)

    def test_a_student_in_two_groups_needs_the_group_to_be_named(self):
        Enrollment.objects.create(course=self.course2, student=self.student, status=Enrollment.Status.APPROVED)
        aid = self.bank()
        self.assertEqual(self.assign(aid, student_ids=[str(self.student.id)]).status_code, 400)
        ok = self.assign(aid, course_ids=[str(self.course2.id)], student_ids=[str(self.student.id)])
        self.assertEqual(ok.status_code, 201, ok.content)

    def test_a_normal_assignment_cannot_be_assigned_again(self):
        normal = self.assignment()
        self.assertEqual(self.assign(normal, course_ids=[str(self.course2.id)]).status_code, 404)


def uuid_of(value):
    import uuid

    return uuid.UUID(str(value))


class HomeworkAudienceTests(BankBase):
    def setUp(self):
        super().setUp()
        self.aid = self.assignment()

    def url(self):
        return f'/api/v1/homework/assignments/{self.aid}/audience/'

    def put(self, ids, user=None):
        return self.api(user or self.teacher).put(self.url(), {'student_ids': [str(i) for i in ids]}, format='json')

    def test_default_is_everyone(self):
        data = self.api(self.teacher).get(self.url()).data
        self.assertEqual((data['restricted'], data['total'], data['assigned_count']), (False, 2, 2))

    def test_restricting_hides_it_from_the_others_and_blocks_submission(self):
        r = self.put([self.student.id])
        self.assertEqual((r.status_code, r.data['restricted'], r.data['assigned_count']), (200, True, 1))
        self.assertEqual(self.api(self.s2).get(f'/api/v1/homework/assignments/{self.aid}/').status_code, 404)
        sub = self.api(self.s2).post(f'/api/v1/homework/assignments/{self.aid}/submit/', {'comment': 'x'}, format='multipart')
        self.assertEqual(sub.status_code, 404)
        ok = self.api(self.student).post(f'/api/v1/homework/assignments/{self.aid}/submit/', {'comment': 'x'}, format='multipart')
        self.assertEqual(ok.status_code, 201, ok.content)
        rows = {r['username']: r for r in self.api(self.teacher).get(self.url()).data['students']}
        self.assertTrue(rows['s1']['submitted'] and rows['s1']['can_submit'])
        self.assertFalse(rows['s2']['can_submit'])

    def test_everyone_or_empty_lifts_the_restriction_and_foreign_students_are_rejected(self):
        self.put([self.student.id])
        self.assertFalse(self.put([self.student.id, self.s2.id]).data['restricted'])
        self.put([self.student.id])
        self.assertFalse(self.put([]).data['restricted'])
        self.assertEqual(self.put([self.s3.id]).status_code, 400)  # boshqa guruh o'quvchisi
        self.assertEqual(self.put([self.student.id], user=self.student).status_code, 403)

    def test_detail_shows_who_it_is_for_to_the_teacher_only(self):
        self.put([self.student.id])
        self.assertEqual(self.api(self.teacher).get(f'/api/v1/homework/assignments/{self.aid}/').data['student_ids'], [str(self.student.id)])
        self.assertNotIn('student_ids', self.api(self.student).get(f'/api/v1/homework/assignments/{self.aid}/').data)

    def test_the_students_added_later_get_a_notification(self):
        self.put([self.student.id])
        NotificationRecipient.objects.all().delete()
        s4 = make('s4', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=s4, status=Enrollment.Status.APPROVED)
        with self.captureOnCommitCallbacks(execute=True):
            self.put([self.student.id, s4.id])
        self.assertTrue(NotificationRecipient.objects.filter(user=s4).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student).exists())
