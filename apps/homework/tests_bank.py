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

    def test_bank_detail_lists_the_copies_with_their_groups(self):
        aid = self.api(self.teacher).post('/api/v1/homework/assignments/', {'title': 'Savolsiz'}, format='json').data['id']
        self.assign(aid, course_ids=[str(self.course.id)])
        self.assign(aid, student_ids=[str(self.s3.id)])
        detail = self.api(self.teacher).get(f'/api/v1/homework/assignments/{aid}/').data
        self.assertEqual(detail['copies_count'], 2)
        by_course = {c['course_id']: c for c in detail['copies']}
        self.assertEqual(set(by_course), {str(self.course.id), str(self.course2.id)})
        self.assertEqual(by_course[str(self.course.id)]['submissions_count'], 0)
        self.assertIsNone(by_course[str(self.course.id)]['student_ids'])
        self.assertEqual(by_course[str(self.course2.id)]['student_ids'], [str(self.s3.id)])
        self.assertTrue(by_course[str(self.course.id)]['id'] and by_course[str(self.course.id)]['due_at'])
        self.api(self.student).post(f'/api/v1/homework/assignments/{by_course[str(self.course.id)]["id"]}/submit/', {'comment': 'x'}, format='multipart')
        again = self.api(self.teacher).get(f'/api/v1/homework/assignments/{aid}/').data
        self.assertEqual({c['course_id']: c['submissions_count'] for c in again['copies']}[str(self.course.id)], 1)

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


class AssignTargetsTests(BankBase):
    """`targets: [{course_id, student_ids?}]` — har guruh uchun aniq ro'yxat (2026-11-12)."""

    def setUp(self):
        super().setUp()
        self.club = Course.objects.create(teacher=self.teacher, title='Club', subject=Course.Subject.MATH, kind='club')
        Enrollment.objects.create(course=self.club, student=self.student, status=Enrollment.Status.APPROVED)  # guruh + club
        self.aid = self.bank()

    def assign_targets(self, targets, **extra):
        return self.assign(self.aid, targets=targets, **extra)

    def test_a_student_in_two_groups_can_be_chosen_inside_one_of_them(self):
        r = self.assign_targets([{'course_id': str(self.course.id), 'student_ids': [str(self.student.id)]}])
        self.assertEqual((r.status_code, r.data['count']), (201, 1), r.content)
        copy = Assignment.objects.get(pk=r.data['assignments'][0]['id'])
        self.assertEqual(copy.course_id, self.course.id)
        self.assertEqual(list(copy.assigned_students.values_list('pk', flat=True)), [self.student.pk])
        self.assertFalse(copy.announce_in_chat)  # chat butun guruhga ko'rinadi — karta yuborilmaydi

    def test_notification_goes_only_to_the_chosen_students_and_nothing_leaks_to_the_rest(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.assign_targets([{'course_id': str(self.course.id), 'student_ids': [str(self.student.id)]}])
        copy_id = r.data['assignments'][0]['id']
        self.assertTrue(NotificationRecipient.objects.filter(user=self.student).exists())
        self.assertFalse(NotificationRecipient.objects.filter(user=self.s2).exists())
        self.assertEqual(self.api(self.s2).get(f'/api/v1/homework/assignments/{copy_id}/').status_code, 404)
        from apps.chat.models import Message
        self.assertFalse(Message.objects.filter(message_type='assignment').exists())

    def test_whole_group_and_chosen_students_of_another_group_in_one_request(self):
        r = self.assign_targets([
            {'course_id': str(self.course.id)},
            {'course_id': str(self.club.id), 'student_ids': [str(self.student.id)]},
        ])
        self.assertEqual((r.status_code, r.data['count']), (201, 2), r.content)
        by_course = {a['course_id']: Assignment.objects.get(pk=a['id']) for a in r.data['assignments']}
        self.assertFalse(by_course[str(self.course.id)].assigned_students.exists())
        self.assertTrue(by_course[str(self.course.id)].announce_in_chat)
        self.assertEqual(by_course[str(self.club.id)].assigned_students.count(), 0)  # club'da faqat shu o'quvchi bor = butun guruh

    def test_all_students_chosen_is_the_same_as_the_whole_group(self):
        r = self.assign_targets([{'course_id': str(self.course.id), 'student_ids': [str(self.student.id), str(self.s2.id)]}])
        copy = Assignment.objects.get(pk=r.data['assignments'][0]['id'])
        self.assertFalse(copy.assigned_students.exists())
        self.assertTrue(copy.announce_in_chat)

    def test_an_empty_student_list_means_the_whole_group(self):
        r = self.assign_targets([{'course_id': str(self.course.id), 'student_ids': []}])
        self.assertFalse(Assignment.objects.get(pk=r.data['assignments'][0]['id']).assigned_students.exists())

    def test_validation_errors_name_the_target(self):
        outsider = str(self.s3.id)  # course2 da, course da emas
        r = self.assign_targets([{'course_id': str(self.course.id)}, {'course_id': str(self.course.id), 'student_ids': [outsider]}])
        self.assertEqual(r.status_code, 400)
        self.assertIn('1', r.data['error']['details']['targets'])  # ikki marta kiritilgan guruh
        r = self.assign_targets([{'course_id': str(self.course.id), 'student_ids': [outsider]}])
        self.assertEqual(r.status_code, 400)
        self.assertIn('student_ids', r.data['error']['details']['targets']['0'])
        self.assertEqual(self.assign_targets([]).status_code, 400)
        self.assertEqual(self.assign_targets([{'student_ids': []}]).status_code, 400)
        foreign = Course.objects.create(teacher=make('t_x', User.Role.TEACHER), title='X')
        self.assertEqual(self.assign_targets([{'course_id': str(foreign.id)}]).status_code, 403)
        self.assertEqual(Assignment.objects.filter(source_id=uuid_of(self.aid)).count(), 0)  # hech narsa yaratilmadi

    def test_the_old_course_ids_and_student_ids_still_work(self):
        r = self.assign(self.aid, course_ids=[str(self.course.id)])
        self.assertEqual((r.status_code, r.data['count']), (201, 1))


def uuid_of(value):
    import uuid

    return uuid.UUID(str(value))


class HomeworkCountsTests(BankBase):
    """Ro'yxatdagi "N / M topshirdi" hisoblari (Trello "Count qism larni ko'rib to'g'irlash", 2026-11-12)."""

    def row(self, aid):
        listed = self.api(self.teacher).get(f'/api/v1/homework/assignments/?course={self.course.id}')
        return next(r for r in listed.data if r['id'] == str(aid))

    def test_counts_are_students_not_submissions(self):
        aid = self.api(self.teacher).post('/api/v1/homework/assignments/', {'course_id': str(self.course.id), 'title': 'Hisob'}, format='json').data['id']
        row = self.row(aid)
        self.assertEqual((row['students_count'], row['submitted_count'], row['pending_review_count'], row['graded_count']), (2, 0, 0, 0))
        for _i in range(2):  # bitta o'quvchi ikki marta topshirsa ham 1 ta
            self.api(self.student).post(f'/api/v1/homework/assignments/{aid}/submit/', {'comment': 'javob'}, format='multipart')
        row = self.row(aid)
        self.assertEqual((row['students_count'], row['submitted_count'], row['pending_review_count'], row['submissions_count']), (2, 1, 1, 2))
        sub_id = self.api(self.teacher).get(f'/api/v1/homework/assignments/{aid}/').data['submissions'][0]['id']
        self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub_id}/review/', {'overall_score': 90}, format='json')
        row = self.row(aid)
        self.assertEqual(row['graded_count'], 1)

    def test_students_count_follows_the_audience(self):
        aid = self.api(self.teacher).post('/api/v1/homework/assignments/', {'course_id': str(self.course.id), 'title': 'Tanlangan'}, format='json').data['id']
        self.api(self.teacher).put(f'/api/v1/homework/assignments/{aid}/audience/', {'student_ids': [str(self.student.id)]}, format='json')
        self.assertEqual(self.row(aid)['students_count'], 1)


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
