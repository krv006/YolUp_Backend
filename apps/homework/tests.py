"""Uy vazifasi oqimi testlari — AI chaqiruvi mock qilinadi.

Qamrov: vazifa berish (faqat o'z kursiga), topshirish (yozilganlar, fayl
validatsiyasi), AI natijaning saqlanishi, xatoda status=error, ko'rish
huquqlari (o'quvchi/o'qituvchi/ota-ona/begona), qayta tekshirish, fan
aniqlash va JSON validatsiya birliklari.
"""
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson

from . import ai
from .models import Submission

FAKE_RESULT = {
    'overall_score': 78,
    'grade': 'Yaxshi',
    'questions': [{
        'question_number': 1,
        'question': '2x + 3 = 7 tenglamani yeching',
        'student_answer': 'x = 2',
        'expected_solution': 'x = 2',
        'analysis': "To'g'ri yechilgan.",
        'mistakes': [],
        'error_categories': [],
        'correct_answer': 'x = 2',
        'suggestions': [],
        'difficulty': 'Easy',
        'score': 100,
    }],
    'summary': {
        'strengths': ['Tenglama yechish'],
        'weaknesses': [],
        'topics_to_review': [],
        'recommendations': [],
    },
}


def make(username, role):
    u = User(username=username, role=role)
    u.set_password('x')
    u.save()
    return u


def pdf_upload(name='vazifa.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake homework', content_type='application/pdf')


@override_settings(HOMEWORK_CHECK_ASYNC=False)
class HomeworkTests(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.other_teacher = make('t2', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.stranger = make('s2', User.Role.STUDENT)
        self.parent = make('p1', User.Role.PARENT)
        ParentChildLink.objects.create(
            parent=self.parent, student=self.student,
            status=ParentChildLink.Status.APPROVED,
        )
        self.course = Course.objects.create(
            teacher=self.teacher, title='Algebra · 7-sinf', subject=Course.Subject.MATH,
        )
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def create_assignment(self, **extra):
        payload = {'course_id': str(self.course.id), 'title': 'Kvadrat tenglamalar', **extra}
        return self.api(self.teacher).post('/api/v1/homework/assignments/', payload, format='json')

    # ── vazifa berish ──
    def test_teacher_creates_assignment(self):
        r = self.create_assignment()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['subject'], 'math')

    def test_only_own_course(self):
        r = self.api(self.other_teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'X',
        }, format='json')
        self.assertEqual(r.status_code, 403)

    def test_student_cannot_create(self):
        r = self.api(self.student).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'X',
        }, format='json')
        self.assertEqual(r.status_code, 403)

    def test_bad_skill_key_rejected(self):
        r = self.create_assignment(skill_key='talking')
        self.assertEqual(r.status_code, 400)

    def test_assignment_linked_to_finished_lesson(self):
        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(),
            duration_min=45, status='finished',
        )
        r = self.create_assignment(lesson_id=str(lesson.id))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['lesson_id'], str(lesson.id))
        self.assertEqual(r.data['lesson_title'], self.course.title)

        # bitta darsga bir nechta vazifa berish mumkin
        r2 = self.create_assignment(lesson_id=str(lesson.id), title='Ikkinchi vazifa')
        self.assertEqual(r2.status_code, 201)

    def test_teacher_edits_deadline_only(self):
        """PATCH — frontendda \"Vazifani tahrirlash\" oynasida deadline
        o'zgartirish 405 (Method not allowed) berardi, endpoint yo'q edi."""
        assignment_id = self.create_assignment().data['id']
        new_due = (timezone.now() + timedelta(days=3)).isoformat()
        r = self.api(self.teacher).patch(
            f'/api/v1/homework/assignments/{assignment_id}/', {'due_at': new_due}, format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data['due_at'])
        # boshqa maydonlarga tegilmadi
        self.assertEqual(r.data['title'], 'Kvadrat tenglamalar')

    def test_edit_clears_deadline_when_sent_empty(self):
        assignment_id = self.create_assignment(due_at=timezone.now().isoformat()).data['id']
        r = self.api(self.teacher).patch(
            f'/api/v1/homework/assignments/{assignment_id}/', {'due_at': ''}, format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data['due_at'])

    def test_edit_title_and_body(self):
        assignment_id = self.create_assignment().data['id']
        r = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{assignment_id}/', {
            'title': 'Yangilangan nom', 'body': '<p>Yangi matn</p>',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['title'], 'Yangilangan nom')
        self.assertIn('Yangi matn', r.data['body'])

    def test_edit_requires_owner_teacher(self):
        assignment_id = self.create_assignment().data['id']
        r = self.api(self.other_teacher).patch(
            f'/api/v1/homework/assignments/{assignment_id}/', {'title': 'X'}, format='json',
        )
        self.assertEqual(r.status_code, 403)

    def test_student_cannot_edit(self):
        assignment_id = self.create_assignment().data['id']
        r = self.api(self.student).patch(
            f'/api/v1/homework/assignments/{assignment_id}/', {'title': 'X'}, format='json',
        )
        self.assertEqual(r.status_code, 403)

    def test_edit_empty_title_rejected(self):
        assignment_id = self.create_assignment().data['id']
        r = self.api(self.teacher).patch(
            f'/api/v1/homework/assignments/{assignment_id}/', {'title': '  '}, format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_unfinished_lesson_rejected(self):
        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(),
            duration_min=45,
        )
        r = self.create_assignment(lesson_id=str(lesson.id))
        self.assertEqual(r.status_code, 400)

    def test_foreign_course_lesson_rejected(self):
        other_course = Course.objects.create(
            teacher=self.other_teacher, title='Boshqa kurs', subject=Course.Subject.PHYSICS,
        )
        lesson = Lesson.objects.create(
            course=other_course, starts_at=timezone.now(),
            duration_min=45, status='finished',
        )
        r = self.create_assignment(lesson_id=str(lesson.id))
        self.assertEqual(r.status_code, 404)

    def test_course_serializer_is_language_subject(self):
        eng = Course.objects.create(
            teacher=self.teacher, title='English A1', subject=Course.Subject.ENGLISH,
        )
        r = self.api(self.teacher).get('/api/v1/courses/')
        by_id = {c['id']: c for c in r.data['results']}
        self.assertTrue(by_id[str(eng.id)]['is_language_subject'])
        self.assertFalse(by_id[str(self.course.id)]['is_language_subject'])

    # ── topshirish + AI ──
    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_submit_runs_check_and_saves_result(self, mock_grade):
        a_id = self.create_assignment().data['id']
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        self.assertEqual(r.status_code, 201)
        # AI tekshirdi, lekin o'qituvchi hali tasdiqlamagan — o'quvchiga
        # ball/baho hali ko'rsatilmaydi
        self.assertEqual(r.data['status'], 'pending_review')
        self.assertIsNone(r.data['overall_score'])
        self.assertEqual(r.data['grade'], '')
        # AI'ga fan konteksti to'g'ri uzatilgan
        _, kwargs = mock_grade.call_args
        self.assertEqual(kwargs['subject_text'], 'math')
        # natija bazada (AI taklifi sifatida) to'liq saqlangan
        sub = Submission.objects.get(pk=r.data['id'])
        self.assertEqual(sub.ai_overall_score, 78)
        self.assertEqual(sub.overall_score, 78)  # dastlab AI'nikidan nusxa
        self.assertEqual(sub.result['questions'][0]['score'], 100)

    @patch('apps.homework.services.ai.grade_file', side_effect=ai.HomeworkAIError('kvota tugadi'))
    def test_ai_error_sets_error_status(self, _):
        a_id = self.create_assignment().data['id']
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['status'], 'error')
        self.assertIn('kvota', r.data['error'])

    def test_stranger_cannot_submit(self):
        a_id = self.create_assignment().data['id']
        r = self.api(self.stranger).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        self.assertEqual(r.status_code, 403)

    def test_unsupported_extension_rejected(self):
        a_id = self.create_assignment().data['id']
        bad = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': bad},
        )
        self.assertEqual(r.status_code, 400)

    def test_audio_only_for_speaking(self):
        a_id = self.create_assignment().data['id']  # skill_key yo'q — oddiy fan
        audio = SimpleUploadedFile('javob.mp3', b'ID3 fake', content_type='audio/mpeg')
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': audio},
        )
        self.assertEqual(r.status_code, 400)

    # ── ko'rish huquqlari ──
    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_view_permissions(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        # o'quvchi, o'qituvchi, ota-ona ko'ra oladi (huquq bor)
        for user in (self.student, self.teacher, self.parent):
            r = self.api(user).get(f'/api/v1/homework/submissions/{sub_id}/')
            self.assertEqual(r.status_code, 200, user.username)

        # begona o'quvchi va boshqa o'qituvchi ko'rmaydi
        for user in (self.stranger, self.other_teacher):
            r = self.api(user).get(f'/api/v1/homework/submissions/{sub_id}/')
            self.assertEqual(r.status_code, 403, user.username)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_pending_review_hidden_from_student_visible_to_teacher(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        # O'qituvchi tasdiqlamaguncha o'quvchi/ota-onaga natija ko'rsatilmaydi
        for user in (self.student, self.parent):
            r = self.api(user).get(f'/api/v1/homework/submissions/{sub_id}/')
            self.assertEqual(r.data['status'], 'pending_review')
            self.assertIsNone(r.data['overall_score'])
            self.assertIsNone(r.data['result'])

        # O'qituvchi AI'ning taklifini darhol ko'radi
        r = self.api(self.teacher).get(f'/api/v1/homework/submissions/{sub_id}/')
        self.assertEqual(r.data['overall_score'], 78)
        self.assertEqual(r.data['ai_overall_score'], 78)
        self.assertIn('focus', r.data)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_teacher_approves_ai_result_as_is(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        r = self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub_id}/review/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'done')
        self.assertEqual(r.data['overall_score'], 78)
        self.assertEqual(r.data['reviewed_by'], self.teacher.username)
        self.assertIsNotNone(r.data['reviewed_at'])

        # Endi o'quvchi ham tasdiqlangan natijani ko'radi
        r = self.api(self.student).get(f'/api/v1/homework/submissions/{sub_id}/')
        self.assertEqual(r.data['status'], 'done')
        self.assertEqual(r.data['overall_score'], 78)
        self.assertEqual(r.data['result']['overall_score'], 78)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_teacher_overrides_score_and_feedback(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        edited_result = {**FAKE_RESULT, 'summary': {
            **FAKE_RESULT['summary'], 'strengths': ["O'qituvchining o'z izohi"],
        }}
        r = self.api(self.teacher).post(
            f'/api/v1/homework/submissions/{sub_id}/review/',
            {'overall_score': 90, 'grade': "A'lo", 'result': edited_result},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['overall_score'], 90)
        self.assertEqual(r.data['grade'], "A'lo")
        # AI'ning asl (o'zgarmas) natijasi audit sifatida saqlanib qoladi
        self.assertEqual(r.data['ai_overall_score'], 78)

        sub = Submission.objects.get(pk=sub_id)
        self.assertEqual(sub.overall_score, 90)
        self.assertEqual(sub.result['summary']['strengths'], ["O'qituvchining o'z izohi"])
        self.assertEqual(sub.ai_result['summary']['strengths'], FAKE_RESULT['summary']['strengths'])

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_review_requires_own_teacher(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        r = self.api(self.student).post(f'/api/v1/homework/submissions/{sub_id}/review/')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.other_teacher).post(f'/api/v1/homework/submissions/{sub_id}/review/')
        self.assertEqual(r.status_code, 403)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_cannot_review_twice(self, _):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']

        self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub_id}/review/')
        r = self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub_id}/review/')
        self.assertEqual(r.status_code, 400)

    # ── vazifa sahifasida vaqt kuzatuvi (focus) ──
    def test_focus_tracking_exit_return(self):
        a_id = self.create_assignment().data['id']
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/focus/', {'kind': 'exit'}, format='json',
        )
        self.assertEqual(r.status_code, 200)
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/focus/', {'kind': 'return'}, format='json',
        )
        self.assertEqual(r.status_code, 200)

        from .services import focus_summary
        summary = focus_summary(assignment_id=a_id, student=self.student)
        self.assertEqual(summary['exits'], 1)
        self.assertEqual(len(summary['timeline']), 1)
        self.assertIsNotNone(summary['timeline'][0]['returned_at'])
        self.assertGreaterEqual(summary['away_seconds'], 0)

    def test_focus_bad_kind_rejected(self):
        a_id = self.create_assignment().data['id']
        r = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/focus/', {'kind': 'blah'}, format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_focus_requires_enrollment(self):
        a_id = self.create_assignment().data['id']
        r = self.api(self.stranger).post(
            f'/api/v1/homework/assignments/{a_id}/focus/', {'kind': 'exit'}, format='json',
        )
        self.assertEqual(r.status_code, 403)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_assignment_detail_scopes_submissions(self, _):
        a_id = self.create_assignment().data['id']
        self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        # o'qituvchi hamma topshiriqni ko'radi
        r = self.api(self.teacher).get(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(len(r.data['submissions']), 1)
        # o'quvchi faqat o'zinikini
        r = self.api(self.student).get(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(len(r.data['submissions']), 1)
        self.assertEqual(r.data['submissions'][0]['student_id'], str(self.student.id))

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_recheck_teacher_only(self, mock_grade):
        a_id = self.create_assignment().data['id']
        sub_id = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        ).data['id']
        r = self.api(self.student).post(f'/api/v1/homework/submissions/{sub_id}/recheck/')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.teacher).post(f'/api/v1/homework/submissions/{sub_id}/recheck/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mock_grade.call_count, 2)

    # ── v2: rich matn, biriktirilgan fayl, muddat, statistika, o'chirish ──
    def test_body_html_is_sanitized(self):
        r = self.create_assignment(body='<p>Yeching: <b>x²+1</b></p><script>alert(1)</script>')
        self.assertEqual(r.status_code, 201)
        self.assertIn('<b>', r.data['body'])
        self.assertNotIn('script', r.data['body'])
        self.assertNotIn('alert', r.data['body'])

    def test_attachment_upload_and_download(self):
        r = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id),
            'title': 'Word vazifa',
            'attachment': SimpleUploadedFile('topshiriq.docx', b'PK fake docx'),
        }, format='multipart')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data['has_attachment'])
        self.assertEqual(r.data['attachment_name'], 'topshiriq.docx')
        # o'quvchi faylni yuklab oladi
        d = self.api(self.student).get(f"/api/v1/homework/assignments/{r.data['id']}/file/")
        self.assertEqual(d.status_code, 200)
        # begona yuklab olmaydi
        d = self.api(self.stranger).get(f"/api/v1/homework/assignments/{r.data['id']}/file/")
        self.assertEqual(d.status_code, 403)

    def test_attachment_bad_ext_rejected(self):
        r = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id),
            'title': 'X',
            'attachment': SimpleUploadedFile('virus.exe', b'MZ'),
        }, format='multipart')
        self.assertEqual(r.status_code, 400)

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_late_submission_flagged(self, _):
        r = self.create_assignment(due_at='2020-01-01T10:00')
        a_id = r.data['id']
        sub = self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        self.assertTrue(sub.data['is_late'])

    @patch('apps.homework.services.ai.grade_file', return_value=FAKE_RESULT)
    def test_teacher_stats(self, _):
        a_id = self.create_assignment().data['id']
        self.api(self.student).post(
            f'/api/v1/homework/assignments/{a_id}/submit/', {'file': pdf_upload()},
        )
        r = self.api(self.teacher).get(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(r.data['stats']['students_count'], 1)
        self.assertEqual(r.data['stats']['submitted_count'], 1)
        self.assertEqual(r.data['stats']['avg_score'], 78)

    def test_delete_assignment_teacher_only(self):
        a_id = self.create_assignment().data['id']
        r = self.api(self.student).delete(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.other_teacher).delete(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.teacher).delete(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(r.status_code, 204)
        r = self.api(self.teacher).get(f'/api/v1/homework/assignments/{a_id}/')
        self.assertEqual(r.status_code, 404)

    def test_list_requires_course_access(self):
        self.create_assignment()
        r = self.api(self.stranger).get(f'/api/v1/homework/assignments/?course={self.course.id}')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.student).get(f'/api/v1/homework/assignments/?course={self.course.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertIsNone(r.data[0]['my_submission'])


@override_settings(HOMEWORK_CHECK_ASYNC=False)
class DeadlineReminderTests(TestCase):
    """Vazifa berilganda va deadline yaqinlashganda (yarim vaqt / 1 soat)
    bildirishnoma yuborilishi — faqat hali topshirmagan o'quvchilarga,
    har biri faqat bir marta."""

    def setUp(self):
        from apps.notifications.models import NotificationRecipient

        self.NotificationRecipient = NotificationRecipient
        self.teacher = make('dr_t', User.Role.TEACHER)
        self.student = make('dr_s1', User.Role.STUDENT)
        self.other_student = make('dr_s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='DR', subject=Course.Subject.MATH)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.other_student, status=Enrollment.Status.APPROVED)

    def inbox_texts(self, student):
        return [
            r.notification.description
            for r in self.NotificationRecipient.objects.filter(user=student).select_related('notification')
        ]

    def test_creating_assignment_notifies_all_enrolled_students(self):
        from . import services

        services.create_assignment(teacher=self.teacher, course_id=self.course.id, title='Uy vazifasi 1')
        self.assertTrue(any('yangi uy vazifasi' in t for t in self.inbox_texts(self.student)))
        self.assertTrue(any('yangi uy vazifasi' in t for t in self.inbox_texts(self.other_student)))

    def test_notification_carries_assignment_link(self):
        from . import services

        assignment = services.create_assignment(
            teacher=self.teacher, course_id=self.course.id, title='Havolali vazifa',
        )
        recipient = self.NotificationRecipient.objects.filter(user=self.student).latest('created_at')
        self.assertEqual(recipient.notification.link_type, 'assignment')
        self.assertEqual(recipient.notification.link_id, str(assignment['id']))

    def test_halfway_reminder_sent_once_to_pending_students_only(self):
        from .models import Assignment, Submission
        from . import services

        created = timezone.now() - timedelta(hours=2)
        due = timezone.now() + timedelta(hours=2)  # jami 4 soat -> yarmi = created+2h = hozir
        a = Assignment.objects.create(course=self.course, title='HW', due_at=due)
        Assignment.objects.filter(pk=a.pk).update(created_at=created)
        a.refresh_from_db()

        Submission.objects.create(assignment=a, student=self.other_student, file=pdf_upload(), original_name='x.pdf')

        sent = services.send_deadline_reminders()
        self.assertEqual(sent['halfway'], 1)  # faqat student (other_student topshirgan)
        self.assertTrue(any("yarmi o'tdi" in t for t in self.inbox_texts(self.student)))
        self.assertFalse(any("yarmi o'tdi" in t for t in self.inbox_texts(self.other_student)))

        # ikkinchi chaqiruv — takror yubormaydi
        sent2 = services.send_deadline_reminders()
        self.assertEqual(sent2['halfway'], 0)

    def test_1h_reminder_fires_independently_of_halfway(self):
        from .models import Assignment
        from . import services

        created = timezone.now() - timedelta(hours=10)
        due = timezone.now() + timedelta(minutes=30)
        a = Assignment.objects.create(course=self.course, title='HW2', due_at=due)
        Assignment.objects.filter(pk=a.pk).update(
            created_at=created,
            reminder_halfway_sent_at=timezone.now() - timedelta(hours=5),
        )

        sent = services.send_deadline_reminders()
        self.assertEqual(sent['halfway'], 0)
        self.assertEqual(sent['1h'], 2)
        self.assertTrue(any('1 soat qoldi' in t for t in self.inbox_texts(self.student)))

    def test_past_due_assignment_is_skipped(self):
        from .models import Assignment
        from . import services

        Assignment.objects.create(
            course=self.course, title='Old',
            due_at=timezone.now() - timedelta(hours=1),
        )
        sent = services.send_deadline_reminders()
        self.assertEqual(sent, {'halfway': 0, '1h': 0})


@override_settings(HOMEWORK_CHECK_ASYNC=False)
class ProgressReportTests(TestCase):
    """Uspevaemost: fan bo'yicha bajarilish foizi + o'rtacha ball,
    faqat DONE topshiriqlar hisoblanadi, qayta yuklansa — eng so'nggisi."""

    def setUp(self):
        from apps.accounts.models import ParentChildLink

        self.teacher = make('pr_t', User.Role.TEACHER)
        self.student = make('pr_s', User.Role.STUDENT)
        self.parent = make('pr_p', User.Role.PARENT)
        ParentChildLink.objects.create(
            parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED,
        )
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra', subject=Course.Subject.MATH)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def mk_submission(self, assignment, *, status, score=None, created_at=None):
        sub = Submission.objects.create(
            assignment=assignment, student=self.student, file=pdf_upload(),
            original_name='x.pdf', status=status, overall_score=score,
        )
        if created_at:
            Submission.objects.filter(pk=sub.pk).update(created_at=created_at)
        return sub

    def test_empty_course_has_zero_completion_and_no_avg(self):
        r = self.api(self.student).get('/api/v1/homework/report/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['overall'], {
            'assignments_total': 0, 'assignments_submitted': 0,
            'completion_pct': 0.0, 'avg_score': None,
        })

    def test_completion_and_average_count_only_done(self):
        from .models import Assignment

        a1 = Assignment.objects.create(course=self.course, title='A1')
        Assignment.objects.create(course=self.course, title='A2')  # topshirilmagan
        a3 = Assignment.objects.create(course=self.course, title='A3')

        self.mk_submission(a1, status=Submission.Status.DONE, score=80)
        self.mk_submission(a3, status=Submission.Status.PENDING_REVIEW, score=50)  # hali tasdiqlanmagan

        r = self.api(self.student).get('/api/v1/homework/report/')
        subj = r.data['subjects'][0]
        self.assertEqual(subj['assignments_total'], 3)
        self.assertEqual(subj['assignments_submitted'], 2)  # A1 va A3 topshirilgan (holatidan qat'iy nazar)
        self.assertAlmostEqual(subj['completion_pct'], 66.7, places=1)
        self.assertEqual(subj['avg_score'], 80.0)  # faqat DONE (A1) hisoblanadi

    def test_resubmission_counts_latest_only(self):
        from datetime import timedelta as td

        from .models import Assignment

        a1 = Assignment.objects.create(course=self.course, title='A1')
        old = timezone.now() - td(hours=2)
        self.mk_submission(a1, status=Submission.Status.ERROR, score=None, created_at=old)
        self.mk_submission(a1, status=Submission.Status.DONE, score=95)  # qayta yuklangan, yangisi

        r = self.api(self.student).get('/api/v1/homework/report/')
        subj = r.data['subjects'][0]
        self.assertEqual(subj['assignments_submitted'], 1)  # ikkitasi emas — bitta vazifa
        self.assertEqual(subj['avg_score'], 95.0)  # eski ERROR emas, yangi DONE hisoblanadi

    def test_student_without_student_id_sees_own_report(self):
        r = self.api(self.student).get('/api/v1/homework/report/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['student_id'], str(self.student.id))

    def test_linked_parent_can_view_with_student_id(self):
        r = self.api(self.parent).get(f'/api/v1/homework/report/?student_id={self.student.id}')
        self.assertEqual(r.status_code, 200)

    def test_unlinked_parent_forbidden(self):
        other_parent = make('pr_p2', User.Role.PARENT)
        r = self.api(other_parent).get(f'/api/v1/homework/report/?student_id={self.student.id}')
        self.assertEqual(r.status_code, 403)

    def test_teacher_cannot_use_own_report_without_student_id(self):
        r = self.api(self.teacher).get('/api/v1/homework/report/')
        self.assertEqual(r.status_code, 400)


class AiUnitTests(TestCase):
    def test_detect_profile(self):
        self.assertEqual(ai.detect_profile('math'), ('math', '', ''))
        self.assertEqual(ai.detect_profile('physics'), ('physics', '', ''))
        self.assertEqual(ai.detect_profile('english'), ('general', '', 'english'))
        self.assertEqual(ai.detect_profile('geography'), ('general', 'Geography', ''))
        self.assertEqual(ai.detect_profile('other'), ('general', '', ''))

    def test_grade_label(self):
        self.assertEqual(ai.grade_label(95), "A'lo")
        self.assertEqual(ai.grade_label(78), 'Yaxshi')
        self.assertEqual(ai.grade_label(10), 'Jiddiy yaxshilash kerak')

    def test_parse_valid_json_with_fences(self):
        import json
        raw = '```json\n' + json.dumps(FAKE_RESULT) + '\n```'
        self.assertEqual(ai.parse_and_validate_json(raw)['overall_score'], 78)

    def test_parse_rejects_missing_keys(self):
        with self.assertRaises(ai.InvalidModelResponseError):
            ai.parse_and_validate_json('{"overall_score": 5}')
        with self.assertRaises(ai.InvalidModelResponseError):
            ai.parse_and_validate_json('bu json emas')

    def test_system_prompt_modes(self):
        p = ai.build_system_prompt('math')
        self.assertIn('Mathematics teacher', p)
        self.assertIn('UZBEK', p)
        p = ai.build_system_prompt('general', language_key='english', skill_key='speaking')
        self.assertIn('AUDIO RECORDING', p)
        p = ai.build_system_prompt('general', custom_name='Geografiya')
        self.assertIn('Geografiya', p)
