"""Uy vazifasi: qoralama, chat/muddat/baholash sozlamalari, ota-onaga ko'rsatish, qayta topshirish, eslatma, AI xulosa;
bildirishnoma `users`/`parents_of` nishonlari."""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.chat.models import Message
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

from .models import Assignment, Submission


def make(username, role):
    user = User(username=username, role=role)
    user.set_password('x')
    user.save()
    return user


def upload(name='a.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


class WorkflowBase(TestCase):
    def setUp(self):
        cache.clear()
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.student2 = make('s2', User.Role.STUDENT)
        self.parent = make('p1', User.Role.PARENT)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject=Course.Subject.MATH)
        for student in (self.student, self.student2):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def create(self, **extra):
        data = {'course_id': str(self.course.id), 'title': 'Kasrlar', **extra}
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', data, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def submit(self, student, assignment_id, name='a.pdf'):
        return self.api(student).post(
            f'/api/v1/homework/assignments/{assignment_id}/submit/', {'file': upload(name)}, format='multipart',
        )

    def make_submission(self, student, assignment_id, status=Submission.Status.PENDING_REVIEW):
        return Submission.objects.create(
            assignment_id=assignment_id, student=student, file=upload(), original_name='a.pdf', status=status,
        )

    def cards(self, user=None):
        return Message.objects.filter(room__course=self.course, message_type=Message.Type.ASSIGNMENT)


class DraftTests(WorkflowBase):
    def test_draft_is_hidden_silent_and_publishable(self):
        draft = self.create(status='draft')
        self.assertEqual((draft['status'], draft['published']), ('draft', False))
        self.assertEqual(self.cards().count(), 0)
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student).exists())
        url = f'/api/v1/homework/assignments/{draft["id"]}/'
        self.assertEqual(self.api(self.student).get(url).status_code, 404)
        self.assertEqual(self.api(self.teacher).get(url).status_code, 200)
        listing = self.api(self.student).get(f'/api/v1/homework/assignments/?course={self.course.id}').json()
        self.assertEqual(listing, [])
        self.assertEqual(self.submit(self.student, draft['id']).status_code, 404)
        self.assertEqual(self.api(self.parent).get(url).status_code, 404)
        published = self.api(self.teacher).patch(url, {'status': 'active'}, format='json')
        self.assertEqual(published.status_code, 200, published.content)
        self.assertEqual((published.json()['status'], published.json()['published']), ('active', True))
        self.assertEqual(self.cards().count(), 1)  # e'lon qilingach chatga karta tushdi
        self.assertEqual(NotificationRecipient.objects.filter(user=self.student).count(), 1)
        self.assertEqual(self.api(self.student).get(url).status_code, 200)
        again = self.api(self.teacher).patch(url, {'status': 'active'}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self.cards().count(), 1)  # takror e'lon qilinmaydi

    def test_status_filter_published_alias_and_no_way_back(self):
        draft = self.create(status='draft')
        active = self.create(title='Faol', status='published')  # ikkinchi hujjat nomi
        self.assertEqual(active['status'], 'active')
        base = f'/api/v1/homework/assignments/?course={self.course.id}'
        self.assertEqual({a['id'] for a in self.api(self.teacher).get(base).json()}, {draft['id'], active['id']})
        self.assertEqual([a['id'] for a in self.api(self.teacher).get(base + '&status=draft').json()], [draft['id']])
        self.assertEqual([a['id'] for a in self.api(self.teacher).get(base + '&status=active').json()], [active['id']])
        self.assertEqual([a['id'] for a in self.api(self.student).get(base + '&status=draft').json()], [active['id']])
        back = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{active["id"]}/', {'status': 'draft'}, format='json')
        self.assertEqual(back.status_code, 400)
        bad = self.api(self.teacher).post('/api/v1/homework/assignments/', {'course_id': str(self.course.id), 'title': 'x', 'status': 'zzz'}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_drafts_get_no_deadline_reminders(self):
        from . import services

        due = timezone.now() + timedelta(minutes=30)
        draft = self.create(status='draft', due_at=due.isoformat())
        Assignment.objects.filter(pk=draft['id']).update(created_at=timezone.now() - timedelta(hours=5))
        self.assertEqual(services.send_deadline_reminders(), {'halfway': 0, '1h': 0})


class AnnounceAndLateTests(WorkflowBase):
    def test_announce_in_chat_switch(self):
        quiet = self.create(announce_in_chat=False)
        self.assertFalse(quiet['announce_in_chat'])
        self.assertEqual(self.cards().count(), 0)
        self.assertEqual(NotificationRecipient.objects.filter(user=self.student).count(), 1)  # bildirishnoma baribir ketadi
        loud = self.create(title='Ovozli', announce_in_chat='true')
        self.assertTrue(loud['announce_in_chat'])
        self.assertEqual(self.cards().count(), 1)
        self.assertEqual(self.create(title='Standart')['announce_in_chat'], True)

    def test_allow_late_false_closes_submissions_after_the_deadline(self):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        strict = self.create(due_at=past, allow_late=False)
        self.assertFalse(strict['allow_late'])
        closed = self.submit(self.student, strict['id'])
        self.assertEqual(closed.status_code, 400, closed.content)
        lenient = self.create(title='Yumshoq', due_at=past, allow_late=True)
        ok = self.submit(self.student, lenient['id'])
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertTrue(ok.json()['is_late'])
        self.api(self.teacher).patch(f'/api/v1/homework/assignments/{strict["id"]}/', {'allow_late': 'true'}, format='multipart')
        self.assertEqual(self.submit(self.student, strict['id'], name='b.pdf').status_code, 201)

    def test_default_keeps_old_behaviour(self):
        data = self.create()
        self.assertEqual((data['allow_late'], data['grading'], data['max_score'], data['status']), (True, 'five', 5, 'active'))


class GradingTests(WorkflowBase):
    def review(self, submission, **data):
        return self.api(self.teacher).post(f'/api/v1/homework/submissions/{submission.id}/review/', data, format='json')

    def test_five_point_scale(self):
        a = self.create()
        sub = self.make_submission(self.student, a['id'])
        resp = self.review(sub, grade=4)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['grade_value'], body['overall_score'], body['grading'], body['max_score']), (4.0, 80.0, 'five', 5))
        self.assertTrue(body['grade'])
        self.assertEqual(self.review(sub, grade=6).status_code, 400)
        self.assertEqual(self.review(sub, grade=0).status_code, 400)
        old = self.review(sub, overall_score=60)  # eski usul ishlaydi
        self.assertEqual((old.json()['overall_score'], old.json()['grade_value']), (60.0, 3.0))

    def test_hundred_point_scale_with_a_custom_maximum(self):
        a = self.create(grading='hundred')
        self.assertEqual((a['grading'], a['max_score']), ('hundred', 100))
        sub = self.make_submission(self.student, a['id'])
        body = self.review(sub, grade=87).json()
        self.assertEqual((body['grade_value'], body['overall_score']), (87.0, 87.0))
        self.assertEqual(self.review(sub, grade=101).status_code, 400)
        small = self.create(title='20 ballik', grading='hundred', max_score=20)
        sub2 = self.make_submission(self.student2, small['id'])
        body = self.review(sub2, grade=15).json()
        self.assertEqual((body['grade_value'], body['overall_score'], body['max_score']), (15.0, 75.0, 20))
        self.assertEqual(self.review(sub2, grade=21).status_code, 400)
        self.assertEqual(self.api(self.teacher).post('/api/v1/homework/assignments/', {'course_id': str(self.course.id), 'title': 'x', 'grading': 'hundred', 'max_score': 5000}, format='json').status_code, 400)

    def test_no_grade_assignment_is_confirmed_with_a_comment_only(self):
        a = self.create(grading='none')
        self.assertEqual((a['grading'], a['max_score']), ('none', 0))
        sub = self.make_submission(self.student, a['id'])
        resp = self.review(sub, result={'comment': 'Yaxshi ish'})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['status'], body['overall_score'], body['grade'], body['grade_value']), ('done', None, '', None))
        seen = self.api(self.student).get(f'/api/v1/homework/submissions/{sub.id}/').json()
        self.assertEqual(seen['result'], {'comment': 'Yaxshi ish'})

    def test_grading_cannot_change_after_a_review_and_bad_values_are_refused(self):
        a = self.create()
        sub = self.make_submission(self.student, a['id'])
        self.review(sub, grade=5)
        resp = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{a["id"]}/', {'grading': 'hundred'}, format='json')
        self.assertEqual(resp.status_code, 400)
        fresh = self.create(title='Boshqa')
        ok = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{fresh["id"]}/', {'grading': 'hundred', 'max_score': 50}, format='json')
        self.assertEqual((ok.status_code, ok.json()['max_score']), (200, 50))
        wrong = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{fresh["id"]}/', {'grading': 'ten'}, format='json')
        self.assertEqual(wrong.status_code, 400)
        missing = self.review(self.make_submission(self.student2, fresh['id']))
        self.assertEqual(missing.status_code, 400)


class ShareWithParentTests(WorkflowBase):
    def test_parent_sees_the_result_unless_the_teacher_hides_it(self):
        a = self.create()
        sub = self.make_submission(self.student, a['id'])
        self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub.id}/review/', {'grade': 5, 'result': {'comment': 'Zo\'r'}}, format='json')
        url = f'/api/v1/homework/submissions/{sub.id}/'
        shown = self.api(self.parent).get(url).json()
        self.assertEqual((shown['overall_score'], shown['grade_value'], shown['share_with_parent']), (100.0, 5.0, True))
        self.assertEqual(shown['result'], {'comment': "Zo'r"})
        hide = self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub.id}/review/', {'grade': 5, 'share_with_parent': False}, format='json')
        self.assertFalse(hide.json()['share_with_parent'])
        hidden = self.api(self.parent).get(url).json()
        self.assertEqual((hidden['overall_score'], hidden['grade'], hidden['grade_value'], hidden['result']), (None, '', None, None))
        self.assertEqual(hidden['status'], 'done')
        own = self.api(self.student).get(url).json()
        self.assertEqual(own['overall_score'], 100.0)  # o'quvchining o'ziga ta'sir qilmaydi
        listing = self.api(self.parent).get(f'/api/v1/homework/assignments/?course={self.course.id}').json()
        self.assertIsNone(listing[0]['my_submission']['overall_score'])
        self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub.id}/review/', {'grade': 5, 'share_with_parent': 'true'}, format='json')
        self.assertEqual(self.api(self.parent).get(url).json()['overall_score'], 100.0)


class ResubmitTests(WorkflowBase):
    def test_request_resubmit_flow(self):
        a = self.create()
        sub = self.make_submission(self.student, a['id'])
        url = f'/api/v1/homework/submissions/{sub.id}/request-resubmit/'
        self.assertEqual(self.api(self.student).post(url, {'comment': 'x'}, format='json').status_code, 403)
        resp = self.api(self.teacher).post(url, {'comment': '115-misolni qayta yuboring'}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (200, {'ok': True}))
        shown = self.api(self.student).get(f'/api/v1/homework/submissions/{sub.id}/').json()
        self.assertEqual((shown['status'], shown['resubmit_comment']), ('resubmit_requested', '115-misolni qayta yuboring'))
        note = NotificationRecipient.objects.get(user=self.student, notification__kind='homework_resubmit').notification
        self.assertIn('115-misolni', note.description)
        self.assertEqual((note.link_type, note.link_id), ('assignment', a['id']))
        again = self.api(self.teacher).post(url, {}, format='json')
        self.assertEqual(again.status_code, 400)  # allaqachon so'ralgan
        fresh = self.submit(self.student, a['id'], name='yangi.pdf')
        self.assertEqual(fresh.status_code, 201, fresh.content)  # o'quvchi yangi fayl yuklay oladi
        listing = self.api(self.student).get(f'/api/v1/homework/assignments/?course={self.course.id}').json()
        self.assertEqual(listing[0]['my_submission']['file_name'], 'yangi.pdf')

    def test_checking_submissions_and_foreign_teachers_are_refused(self):
        a = self.create()
        checking = self.make_submission(self.student, a['id'], status=Submission.Status.CHECKING)
        done = self.make_submission(self.student2, a['id'], status=Submission.Status.DONE)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/homework/submissions/{checking.id}/request-resubmit/', {}, format='json').status_code, 400)
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/homework/submissions/{done.id}/request-resubmit/', {}, format='json').status_code, 200)
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.api(other).post(f'/api/v1/homework/submissions/{done.id}/request-resubmit/', {}, format='json').status_code, 403)


class RemindTests(WorkflowBase):
    def test_only_students_without_a_submission_are_reminded(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        resp = self.api(self.teacher).post(f'/api/v1/homework/assignments/{a["id"]}/remind/')
        self.assertEqual((resp.status_code, resp.json()), (200, {'notified': 1}))
        reminder = NotificationRecipient.objects.get(user=self.student2, notification__kind='homework_reminder')
        self.assertEqual(reminder.notification.link_id, a['id'])
        self.assertFalse(NotificationRecipient.objects.filter(user=self.student, notification__kind='homework_reminder').exists())
        again = self.api(self.teacher).post(f'/api/v1/homework/assignments/{a["id"]}/remind/')
        self.assertEqual(again.status_code, 400)  # 10 daqiqada bir marta

    def test_permissions_and_drafts(self):
        a = self.create()
        self.assertEqual(self.api(self.student).post(f'/api/v1/homework/assignments/{a["id"]}/remind/').status_code, 403)
        other = make('t2', User.Role.TEACHER)
        self.assertEqual(self.api(other).post(f'/api/v1/homework/assignments/{a["id"]}/remind/').status_code, 403)
        draft = self.create(title='Qoralama', status='draft')
        self.assertEqual(self.api(self.teacher).post(f'/api/v1/homework/assignments/{draft["id"]}/remind/').status_code, 400)

    def test_nobody_to_remind(self):
        a = self.create()
        self.make_submission(self.student, a['id'])
        self.make_submission(self.student2, a['id'])
        resp = self.api(self.teacher).post(f'/api/v1/homework/assignments/{a["id"]}/remind/')
        self.assertEqual(resp.json(), {'notified': 0})


class AiSummaryTests(WorkflowBase):
    URL = '/api/v1/homework/assignments/{}/ai-summary/'

    def test_summary_from_the_llm_with_caching(self):
        a = self.create()
        sub = self.make_submission(self.student, a['id'])
        Submission.objects.filter(pk=sub.pk).update(overall_score=55, result={'weaknesses': ['kasrlarni qisqartirish']})
        reply = {'summary': "Ko'pchilik 115-misolda xato qildi.", 'topics': ['Kasrlarni qisqartirish', ' '], 'recommendations': ['Takrorlang']}
        with override_settings(OPENAI_API_KEY='sk-test'), mock.patch('apps.quizzes.llm.chat_json', return_value=reply) as llm:
            resp = self.api(self.teacher).post(self.URL.format(a['id']))
            again = self.api(self.teacher).post(self.URL.format(a['id']))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['topics'], ['Kasrlarni qisqartirish'])
        self.assertEqual((body['summary'], body['recommendations'], body['submissions_count']), (reply['summary'], ['Takrorlang'], 1))
        self.assertEqual(again.json(), body)
        self.assertEqual(llm.call_count, 1)  # ikkinchi marta keshdan
        prompt = llm.call_args.args[1]
        self.assertNotIn('s1', prompt)  # o'quvchilar anonim yuboriladi
        self.assertIn('kasrlarni qisqartirish', prompt)

    def test_no_key_no_submissions_and_wrong_user(self):
        a = self.create()
        with override_settings(OPENAI_API_KEY=''):
            self.assertEqual(self.api(self.teacher).post(self.URL.format(a['id'])).status_code, 503)
        with override_settings(OPENAI_API_KEY='sk-test'):
            self.assertEqual(self.api(self.teacher).post(self.URL.format(a['id'])).status_code, 400)  # hali topshiriq yo'q
            self.assertEqual(self.api(self.student).post(self.URL.format(a['id'])).status_code, 403)
            self.make_submission(self.student, a['id'])
            from apps.quizzes.llm import LLMError

            with mock.patch('apps.quizzes.llm.chat_json', side_effect=LLMError('limit')):
                self.assertEqual(self.api(self.teacher).post(self.URL.format(a['id'])).status_code, 503)


class NotificationTargetsTests(WorkflowBase):
    def send(self, user, **data):
        return self.api(user).post('/api/v1/notifications/send/', {'description': 'Eslatma', **data}, format='json')

    def test_teacher_sends_to_several_of_his_students_in_one_request(self):
        resp = self.send(self.teacher, target_type='users', user_ids=[str(self.student.id), str(self.student2.id)], kind='homework_reminder')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(NotificationRecipient.objects.filter(notification_id=resp.json()['id']).count(), 2)
        self.assertEqual(resp.json()['kind'], 'homework_reminder')

    def test_parents_of_goes_to_approved_parents_only(self):
        pending_parent = make('p2', User.Role.PARENT)
        ParentChildLink.objects.create(parent=pending_parent, student=self.student, status=ParentChildLink.Status.PENDING)
        resp = self.send(self.teacher, target_type='parents_of', user_ids=[str(self.student.id), str(self.student2.id)])
        self.assertEqual(resp.status_code, 201, resp.content)
        recipients = NotificationRecipient.objects.filter(notification_id=resp.json()['id'])
        self.assertEqual([r.user_id for r in recipients], [self.parent.id])

    def test_teacher_limits(self):
        stranger = make('s9', User.Role.STUDENT)  # shu o'qituvchining o'quvchisi emas
        self.assertEqual(self.send(self.teacher, target_type='users', user_ids=[str(stranger.id)]).status_code, 403)
        self.assertEqual(self.send(self.teacher, target_type='users', user_ids=[str(self.student.id), str(stranger.id)]).status_code, 403)
        self.assertEqual(self.send(self.teacher, target_type='all').status_code, 403)
        self.assertEqual(self.send(self.teacher, target_type='user', user_id=str(self.student.id)).status_code, 403)
        self.assertEqual(self.send(self.student, target_type='users', user_ids=[str(self.student2.id)]).status_code, 403)
        spoofed = self.send(self.teacher, target_type='users', user_ids=[str(self.student.id)], kind='teacher_approved', link_type='submission', link_id='x')
        self.assertEqual((spoofed.json()['kind'], spoofed.json()['link_type'], spoofed.json()['link_id']), ('', '', ''))

    def test_admin_keeps_full_access_and_validation(self):
        admin = make('adm', User.Role.ADMIN)
        resp = self.send(admin, target_type='users', user_ids=[str(self.student.id)], kind='announcement', link_type='x')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['kind'], 'announcement')
        self.assertEqual(self.send(admin, target_type='all').status_code, 201)
        self.assertEqual(self.send(admin, target_type='users').status_code, 400)  # user_ids kerak
        self.assertEqual(self.send(admin, target_type='bogus').status_code, 400)
