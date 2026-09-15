from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import PASSWORD, login, register

from .models import Attendance, Course


class CourseLessonFlowTests(APITestCase):
    def setUp(self):
        register(self.client, 't1', 'teacher')
        self.teacher_token = login(self.client, 't1')

        register(self.client, 'p1', 'parent')
        self.parent_token = login(self.client, 'p1')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        resp = self.client.post('/api/v1/auth/children/', {'username': 's1', 'password': PASSWORD})
        self.child_id = resp.json()['id']
        self.child_token = login(self.client, 's1')

        # teacher creates course + lesson
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')
        self.course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Algebra', 'subject': 'math'}
        ).json()['id']
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        self.lesson_id = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 1',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()['id']

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def approve_all_requests(self):
        """O'qituvchi sifatida barcha kutilayotgan yozilish so'rovlarini tasdiqlaydi."""
        self.auth(self.teacher_token)
        for req in self.client.get('/api/v1/courses/requests/').json()['results']:
            self.client.post('/api/v1/courses/requests/respond/', {
                'enrollment_id': req['id'], 'action': 'approve',
            })

    def test_student_cannot_create_course(self):
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/courses/', {'title': 'Hack'})
        self.assertEqual(resp.status_code, 403)

    def test_parent_enrolls_linked_child_only(self):
        self.auth(self.parent_token)
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['status'], 'pending')  # o'qituvchi tasdig'ini kutadi

        # another parent with no link cannot enroll this child
        register(self.client, 'p2', 'parent')
        p2 = login(self.client, 'p2')
        self.auth(p2)
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.assertEqual(resp.status_code, 403)

    def test_pending_enrollment_gives_no_access_until_approved(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})

        # tasdiqlanmagan — token yo'q, darslar ko'rinmaydi
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(len(self.client.get('/api/v1/lessons/').json()['results']), 0)

        # o'qituvchi tasdiqladi — endi kiradi
        self.approve_all_requests()
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})
        self.assertEqual(resp.status_code, 200)

    def test_teacher_direct_enroll_is_approved(self):
        self.auth(self.teacher_token)
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student': 's1'})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['status'], 'approved')

    def test_room_token_flow_and_attendance(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()

        # student joins -> attendance stamped
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['token'])
        self.assertFalse(resp.json()['is_teacher'])
        attendance = Attendance.objects.get(lesson_id=self.lesson_id, student_id=self.child_id)
        self.assertIsNotNone(attendance.joined_at)

        # teacher joins -> lesson goes live
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})
        self.assertTrue(resp.json()['is_teacher'])

        # teacher finishes -> open attendance closed
        resp = self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.assertEqual(resp.json()['status'], 'finished')
        attendance.refresh_from_db()
        self.assertIsNotNone(attendance.left_at)

    def test_unenrolled_student_cannot_get_token(self):
        register(self.client, 'p3', 'parent')
        p3 = login(self.client, 'p3')
        self.auth(p3)
        outsider = self.client.post('/api/v1/auth/children/', {'username': 's2', 'password': PASSWORD})
        outsider_token = login(self.client, 's2')
        self.auth(outsider_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})
        self.assertEqual(resp.status_code, 403)

    def test_scheduled_lesson_from_past_day_cannot_be_joined(self):
        """2026-09-05 topilgan xato: eski (kuni allaqachon o'tib ketgan,
        hech qachon boshlanmagan) SCHEDULED darsga token so'ralganda
        ABADIY ruxsat berilardi — aslida teskari bo'lishi kerak edi
        (kelajakdagi darsga muammosiz kirish mumkin edi, eskisiga esa
        cheklov yo'q edi). Endi faqat kuni o'tib ketgan darslar
        bloklanadi."""
        from .models import Course, Lesson

        course = Course.objects.get(id=self.course_id)
        stale = Lesson.objects.create(
            course=course, starts_at=timezone.now() - timedelta(days=2),
            duration_min=45, status=Lesson.Status.SCHEDULED,
        )
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': str(stale.id)})
        self.assertEqual(resp.status_code, 400)

    def test_scheduled_lesson_today_can_be_joined_before_its_exact_time(self):
        """Bugunga rejalashtirilgan darsga aniq soatini kutmasdan
        kirish mumkin bo'lishi kerak (o'qituvchi xonani oldindan
        tayyorlab qo'yishi uchun)."""
        from .models import Course, Lesson

        course = Course.objects.get(id=self.course_id)
        now = timezone.localtime(timezone.now())
        end_of_day = now.replace(hour=23, minute=59, second=0, microsecond=0)
        later_today = Lesson.objects.create(
            course=course, starts_at=min(now + timedelta(hours=1), end_of_day),
            duration_min=45, status=Lesson.Status.SCHEDULED,
        )
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/live/token/', {'lesson_id': str(later_today.id)})
        self.assertEqual(resp.status_code, 200)

    def test_parent_sees_only_linked_child_attendance(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.child_token)
        self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})

        self.auth(self.parent_token)
        resp = self.client.get('/api/v1/attendance/')
        self.assertEqual(len(resp.json()['results']), 1)

        register(self.client, 'p4', 'parent')
        p4 = login(self.client, 'p4')
        self.auth(p4)
        resp = self.client.get('/api/v1/attendance/')
        self.assertEqual(len(resp.json()['results']), 0)

    def test_soft_delete_course(self):
        self.auth(self.teacher_token)
        resp = self.client.delete(f'/api/v1/courses/{self.course_id}/')
        self.assertEqual(resp.status_code, 204)
        from .models import Course
        self.assertFalse(Course.objects.filter(pk=self.course_id).exists())
        self.assertTrue(Course.all_objects.filter(pk=self.course_id).exists())

    def test_cannot_create_lesson_in_past(self):
        self.auth(self.teacher_token)
        past = (timezone.now() - timedelta(days=1)).isoformat()
        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': "O'tgan dars",
            'starts_at': past, 'duration_min': 45,
        })
        self.assertEqual(resp.status_code, 400)

    def test_can_edit_other_fields_of_existing_lesson(self):
        """starts_at o'zgarmasa (allaqachon kelajakda bo'lsa ham), boshqa
        maydonni tahrirlash bloklanmasligini tekshiradi."""
        self.auth(self.teacher_token)
        resp = self.client.patch(f'/api/v1/lessons/{self.lesson_id}/', {'title': 'Yangi nom'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], 'Yangi nom')

    def test_create_single_lesson_allows_blank_title(self):
        """Mavzu bo'sh qoldirilishi mumkin — o'qituvchi keyin tahrirlab yozadi."""
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': '',
            'starts_at': (timezone.now() + timedelta(days=1)).isoformat(), 'duration_min': 45,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['title'], '')

    def test_schedule_recurring_rejects_past_start_date(self):
        self.auth(self.teacher_token)
        past_date = (timezone.now().date() - timedelta(days=7)).isoformat()
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/schedule/', {
            'title': "O'tgan hafta",
            'days': [0],
            'start_time': '10:00',
            'end_time': '11:00',
            'weeks': 1,
            'start_date': past_date,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    @staticmethod
    def _next_monday() -> str:
        """Har doim "bugun"dan keyingi eng yaqin dushanba, kamida 1 kun oldinda
        (bugun dushanba bo'lsa — bir hafta keyingisi) — qattiq yozilgan sana
        (masalan '2026-09-07') vaqt o'tishi bilan o'tmishga aylanib, testni
        o'zi buzib qo'yishining oldini oladi. Dushanbaga tekislash muhim:
        days=[0,2,4] hammasi shu haftaning ICHIDA hisoblanishi uchun
        (aks holda start_date hafta o'rtasiga to'g'ri kelsa, o'sha haftaning
        boshidagi kunlar "o'tmishda" deb chetlab o'tiladi va son kamayadi)."""
        today = timezone.now().date()
        days_ahead = (7 - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_ahead)).isoformat()

    def test_schedule_recurring_creates_lessons(self):
        self.auth(self.teacher_token)
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/schedule/', {
            'title': 'Haftalik dars',
            'days': [0, 2, 4],
            'start_time': '10:00',
            'end_time': '11:00',
            'weeks': 2,
            'start_date': self._next_monday(),
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['count'], 6)

    def test_schedule_recurring_allows_blank_title(self):
        """Bitta mavzu ko'p darsga bir xil yozilib ketmasligi uchun —
        o'qituvchi keyin har birini alohida tahrirlab yozadi."""
        self.auth(self.teacher_token)
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/schedule/', {
            'title': '',
            'days': [0, 2],
            'start_time': '10:00',
            'end_time': '11:00',
            'weeks': 1,
            'start_date': self._next_monday(),
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['count'], 2)
        self.assertTrue(all(lesson['title'] == '' for lesson in resp.json()['lessons']))

    def test_schedule_recurring_detects_overlap(self):
        self.auth(self.teacher_token)
        start_date = self._next_monday()
        self.client.post(f'/api/v1/courses/{self.course_id}/schedule/', {
            'title': 'Dars A',
            'days': [0],
            'start_time': '14:00',
            'end_time': '15:00',
            'weeks': 1,
            'start_date': start_date,
        }, format='json')
        resp = self.client.post(f'/api/v1/courses/{self.course_id}/schedule/', {
            'title': 'Dars B',
            'days': [0],
            'start_time': '14:30',
            'end_time': '15:30',
            'weeks': 1,
            'start_date': start_date,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rate_finished_lesson(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')

        self.auth(self.child_token)
        resp = self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 5, 'description': 'Zo\'r!'})
        self.assertEqual(resp.status_code, 201)

        resp = self.client.get(f'/api/v1/lessons/{self.lesson_id}/')
        self.assertEqual(resp.json()['avg_rating'], 5.0)
        self.assertEqual(resp.json()['rating_count'], 1)

    def test_cannot_rate_unfinished_lesson(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.child_token)
        resp = self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 4})
        self.assertEqual(resp.status_code, 400)

    def test_delete_course_wipes_group_data_keeps_history(self):
        from apps.board.models import BoardSheet
        from apps.chat.models import ChatRoom, Message

        from .models import Course, LessonRating

        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()

        self.auth(self.child_token)
        self.client.post('/api/v1/live/token/', {'lesson_id': self.lesson_id})

        BoardSheet.objects.create(
            lesson_id=self.lesson_id, index=0,
            strokes=[{'id': 'x', 'points': [[0, 0], [1, 1]], 'color': '#000', 'width': 2}],
        )
        room = ChatRoom.objects.get(kind=ChatRoom.Kind.COURSE, course_id=self.course_id)
        teacher = User.objects.get(username='t1')
        Message.objects.create(room=room, sender=teacher, text='Salom guruh!')

        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')

        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 5})

        self.assertTrue(Attendance.objects.filter(lesson_id=self.lesson_id).exists())
        self.assertTrue(LessonRating.objects.filter(lesson_id=self.lesson_id).exists())

        self.auth(self.teacher_token)
        resp = self.client.delete(f'/api/v1/courses/{self.course_id}/')
        self.assertEqual(resp.status_code, 204)

        # guruh ma'lumotlari butunlay o'chadi
        self.assertFalse(ChatRoom.objects.filter(course_id=self.course_id).exists())
        self.assertFalse(BoardSheet.objects.filter(lesson_id=self.lesson_id).exists())
        self.assertFalse(self.client.get(f'/api/v1/courses/{self.course_id}/').json().get('id'))

        # kurs/dars yashiriladi (soft-delete), lekin bazadan o'chmaydi
        self.assertFalse(Course.objects.filter(pk=self.course_id).exists())
        self.assertTrue(Course.all_objects.filter(pk=self.course_id).exists())

        # Davomat va baho TARIXI saqlanib qoladi
        self.assertTrue(Attendance.objects.filter(lesson_id=self.lesson_id).exists())
        self.assertTrue(LessonRating.objects.filter(lesson_id=self.lesson_id).exists())

    def test_other_teacher_cannot_delete_foreign_course(self):
        register(self.client, 't2', 'teacher')
        t2_token = login(self.client, 't2')
        self.auth(t2_token)
        resp = self.client.delete(f'/api/v1/courses/{self.course_id}/')
        self.assertEqual(resp.status_code, 404)  # boshqa oquvchining kursi korinmaydi (queryset scoped)

    def test_teacher_has_no_rating_before_any_lesson_rated(self):
        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertIsNone(resp.json()['avg_rating'])
        self.assertEqual(resp.json()['rating_count'], 0)

    def test_teacher_sees_own_average_rating_across_lessons(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()

        starts_at = (timezone.now() + timedelta(days=2)).isoformat()
        self.auth(self.teacher_token)
        lesson2_id = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 2',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()['id']
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.client.post(f'/api/v1/lessons/{lesson2_id}/finish/')

        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 5})
        self.client.post(f'/api/v1/lessons/{lesson2_id}/rate/', {'stars': 3})

        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.json()['avg_rating'], 4.0)
        self.assertEqual(resp.json()['rating_count'], 2)

    def test_student_rating_field_is_null_not_teacher(self):
        self.auth(self.child_token)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertIsNone(resp.json()['avg_rating'])
        self.assertIsNone(resp.json()['rating_count'])

    def test_admin_teacher_list_shows_rating_stats(self):
        from apps.accounts.models import User

        User.objects.create_user(username='admin1', password=PASSWORD, role=User.Role.ADMIN)
        admin_token = login(self.client, 'admin1')

        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()

        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 5})

        self.auth(admin_token)
        resp = self.client.get('/api/v1/auth/teachers/')
        self.assertEqual(resp.status_code, 200)
        results = resp.json()['results'] if isinstance(resp.json(), dict) else resp.json()
        teacher_row = next(r for r in results if r['username'] == 't1')
        self.assertEqual(teacher_row['avg_rating'], 5.0)
        self.assertEqual(teacher_row['rating_count'], 1)

    def test_non_admin_cannot_list_teachers(self):
        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/auth/teachers/')
        self.assertEqual(resp.status_code, 403)

    def test_teacher_sees_own_ratings_with_student_feedback(self):
        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 4, 'description': 'Yaxshi dars edi'})

        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/auth/me/ratings/')
        self.assertEqual(resp.status_code, 200)
        results = resp.json()['results'] if isinstance(resp.json(), dict) else resp.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['stars'], 4)
        self.assertEqual(results[0]['description'], 'Yaxshi dars edi')
        self.assertEqual(results[0]['student']['username'], 's1')

    def test_student_and_parent_cannot_view_own_ratings_endpoint(self):
        """`/auth/me/ratings/` faqat o'qituvchiga tegishli — talaba/ota-ona
        uchun ma'nosiz (ular baho qo'yadi, olmaydi)."""
        self.auth(self.child_token)
        self.assertEqual(self.client.get('/api/v1/auth/me/ratings/').status_code, 403)
        self.auth(self.parent_token)
        self.assertEqual(self.client.get('/api/v1/auth/me/ratings/').status_code, 403)

    def test_admin_sees_teacher_detail_stats(self):
        from apps.accounts.models import User

        User.objects.create_user(username='admin2', password=PASSWORD, role=User.Role.ADMIN)
        admin_token = login(self.client, 'admin2')

        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 5})

        teacher_id = User.objects.get(username='t1').id
        self.auth(admin_token)
        resp = self.client.get(f'/api/v1/auth/teachers/{teacher_id}/stats/')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['avg_rating'], 5.0)
        self.assertEqual(body['rating_count'], 1)
        self.assertEqual(body['rating_breakdown'], {'1': 0, '2': 0, '3': 0, '4': 0, '5': 1})
        self.assertEqual(body['course_count'], 1)
        self.assertEqual(body['student_count'], 1)
        self.assertEqual(body['lessons_finished'], 1)
        self.assertEqual(body['lessons_cancelled'], 0)
        self.assertEqual(body['reliability'], 100.0)

    def test_admin_sees_teacher_ratings_list(self):
        from apps.accounts.models import User

        User.objects.create_user(username='admin3', password=PASSWORD, role=User.Role.ADMIN)
        admin_token = login(self.client, 'admin3')

        self.auth(self.parent_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {'student_id': self.child_id})
        self.approve_all_requests()
        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/finish/')
        self.auth(self.child_token)
        self.client.post(f'/api/v1/lessons/{self.lesson_id}/rate/', {'stars': 2, 'description': "Zerikarli o'tdi"})

        teacher_id = User.objects.get(username='t1').id
        self.auth(admin_token)
        resp = self.client.get(f'/api/v1/auth/teachers/{teacher_id}/ratings/')
        self.assertEqual(resp.status_code, 200)
        results = resp.json()['results'] if isinstance(resp.json(), dict) else resp.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['stars'], 2)
        self.assertEqual(results[0]['description'], "Zerikarli o'tdi")
        self.assertEqual(results[0]['student']['username'], 's1')

    def test_non_admin_cannot_view_other_teacher_stats_or_ratings(self):
        from apps.accounts.models import User

        teacher_id = User.objects.get(username='t1').id
        self.auth(self.child_token)
        self.assertEqual(self.client.get(f'/api/v1/auth/teachers/{teacher_id}/stats/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/v1/auth/teachers/{teacher_id}/ratings/').status_code, 403)

    def test_teacher_stats_404_for_non_teacher_id(self):
        from apps.accounts.models import User

        User.objects.create_user(username='admin4', password=PASSWORD, role=User.Role.ADMIN)
        admin_token = login(self.client, 'admin4')
        self.auth(admin_token)
        resp = self.client.get(f'/api/v1/auth/teachers/{self.child_id}/stats/')
        self.assertEqual(resp.status_code, 404)


class LessonQuizLinkTests(APITestCase):
    """Dars yaratish/tahrirlashning o'zidan mavjud testni biriktirish."""

    def setUp(self):
        register(self.client, 'lq_teacher', 'teacher')
        self.teacher_token = login(self.client, 'lq_teacher')
        self.auth(self.teacher_token)
        self.course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Fizika', 'subject': 'physics'}
        ).json()['id']

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def create_quiz(self, course_id=None, lesson_id=None):
        payload = {
            'course': course_id or self.course_id,
            'title': 'Bob 1 testi',
            'questions': [{
                'text': '2+2=?', 'points': 1,
                'options': [{'text': '4', 'is_correct': True}, {'text': '5', 'is_correct': False}],
            }],
        }
        if lesson_id:
            payload['lesson'] = lesson_id
        return self.client.post('/api/v1/quizzes/', payload, format='json').json()

    def test_create_lesson_with_existing_unlinked_quiz(self):
        quiz = self.create_quiz()
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 1',
            'starts_at': starts_at, 'duration_min': 45, 'quiz': quiz['id'],
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['quiz_id'], quiz['id'])

        from apps.quizzes.models import Quiz
        self.assertEqual(str(Quiz.objects.get(pk=quiz['id']).lesson_id), resp.json()['id'])

    def test_create_lesson_without_quiz_leaves_quiz_id_null(self):
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 2',
            'starts_at': starts_at, 'duration_min': 45,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.json()['quiz_id'])

    def test_cannot_attach_quiz_already_linked_to_another_lesson(self):
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        lesson1 = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars A',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()
        quiz = self.create_quiz(lesson_id=lesson1['id'])  # allaqachon Dars A ga bog'langan

        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars B',
            'starts_at': starts_at, 'duration_min': 45, 'quiz': quiz['id'],
        })
        self.assertEqual(resp.status_code, 400)

    def test_cannot_attach_quiz_from_another_course(self):
        other_course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Kimyo', 'subject': 'chemistry'}
        ).json()['id']
        quiz = self.create_quiz(course_id=other_course_id)

        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 3',
            'starts_at': starts_at, 'duration_min': 45, 'quiz': quiz['id'],
        })
        self.assertEqual(resp.status_code, 400)

    def test_attach_quiz_to_existing_lesson_via_update(self):
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        lesson = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 4',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()
        quiz = self.create_quiz()

        resp = self.client.patch(f'/api/v1/lessons/{lesson["id"]}/', {'quiz': quiz['id']})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['quiz_id'], quiz['id'])

    def test_detach_quiz_from_lesson_via_update(self):
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        lesson = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars 5',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()
        quiz = self.create_quiz(lesson_id=lesson['id'])
        self.assertEqual(
            self.client.get(f'/api/v1/lessons/{lesson["id"]}/').json()['quiz_id'], quiz['id'],
        )

        resp = self.client.patch(f'/api/v1/lessons/{lesson["id"]}/', {'quiz': None}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()['quiz_id'])

        from apps.quizzes.models import Quiz
        self.assertIsNone(Quiz.objects.get(pk=quiz['id']).lesson_id)

    def test_reattaching_quiz_moves_it_from_previous_lesson(self):
        """Bitta test faqat bitta darsga tegishli bo'lishi mumkin — mos
        yozuvlarni tozalash uchun avval o'zi biriktirilgan darsdan ajratiladi,
        keyin yangisiga qo'shiladi (bir xil dars uchun update orqali)."""
        starts_at = (timezone.now() + timedelta(days=1)).isoformat()
        lesson1 = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars X',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()
        lesson2 = self.client.post('/api/v1/lessons/', {
            'course': self.course_id, 'title': 'Dars Y',
            'starts_at': starts_at, 'duration_min': 45,
        }).json()
        quiz = self.create_quiz(lesson_id=lesson1['id'])

        # lesson1'dan ajratib, lesson2'ga biriktiramiz.
        resp = self.client.patch(f'/api/v1/lessons/{lesson1["id"]}/', {'quiz': None}, format='json')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.patch(f'/api/v1/lessons/{lesson2["id"]}/', {'quiz': quiz['id']})
        self.assertEqual(resp.status_code, 200)

        self.assertIsNone(self.client.get(f'/api/v1/lessons/{lesson1["id"]}/').json()['quiz_id'])
        self.assertEqual(self.client.get(f'/api/v1/lessons/{lesson2["id"]}/').json()['quiz_id'], quiz['id'])


class FocusSummaryTests(APITestCase):
    """Chiqish-qaytish tahlili: juftlash, jami/eng uzun vaqt, taymlayn."""

    def setUp(self):
        from apps.accounts.models import User

        self.teacher = User(username='fs_t', role=User.Role.TEACHER)
        self.teacher.set_password('x')
        self.teacher.save()
        self.student = User(username='fs_s', role=User.Role.STUDENT)
        self.student.set_password('x')
        self.student.save()
        from django.utils import timezone

        from .models import Course, Lesson

        course = Course.objects.create(teacher=self.teacher, title='F')
        self.lesson = Lesson.objects.create(
            course=course, starts_at=timezone.now(), duration_min=45,
        )

    def _event(self, kind, at):
        from .models import FocusEvent

        e = FocusEvent.objects.create(lesson=self.lesson, student=self.student, kind=kind)
        # auto_now_add ni chetlab, vaqtni aniq boshqaramiz
        FocusEvent.objects.filter(pk=e.pk).update(created_at=at)

    def test_pairs_and_totals(self):
        from datetime import timedelta

        from django.utils import timezone

        from . import selectors

        t0 = timezone.now()
        self._event('exit', t0)                                  # 1-chiqish: 30s
        self._event('return', t0 + timedelta(seconds=30))
        self._event('exit', t0 + timedelta(seconds=100))         # 2-chiqish: 120s
        self._event('return', t0 + timedelta(seconds=220))
        s = selectors.focus_summary(self.lesson, self.student)
        self.assertEqual(s['exits'], 2)
        self.assertEqual(s['away_seconds'], 150)
        self.assertEqual(s['longest_seconds'], 120)
        self.assertEqual(len(s['timeline']), 2)
        self.assertEqual(s['timeline'][0]['seconds'], 30)
        self.assertEqual(s['timeline'][1]['seconds'], 120)

    def test_unreturned_exit_capped_by_left_at(self):
        from datetime import timedelta

        from django.utils import timezone

        from . import selectors
        from .models import Attendance

        t0 = timezone.now()
        self._event('exit', t0)
        Attendance.objects.create(
            lesson=self.lesson, student=self.student,
            joined_at=t0 - timedelta(minutes=10), left_at=t0 + timedelta(seconds=60),
        )
        s = selectors.focus_summary(self.lesson, self.student)
        self.assertEqual(s['exits'], 1)
        self.assertEqual(s['away_seconds'], 60)
        self.assertIsNone(s['timeline'][0]['returned_at'])

    def test_empty(self):
        from . import selectors

        s = selectors.focus_summary(self.lesson, self.student)
        self.assertEqual(s, {'exits': 0, 'away_seconds': 0, 'longest_seconds': 0, 'timeline': []})


class ParentSeesFocusTests(APITestCase):
    """Fokus tahlili (chiqish-qaytish taymlayn) aynan o'sha bolaning
    OTA-ONASIGA ko'rinadi; begona ota-onaga ko'rinmaydi."""

    def setUp(self):
        register(self.client, 'pf_t', 'teacher')
        self.teacher_token = login(self.client, 'pf_t')

        register(self.client, 'pf_p', 'parent')
        self.parent_token = login(self.client, 'pf_p')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        self.child_id = self.client.post(
            '/api/v1/auth/children/', {'username': 'pf_s', 'password': PASSWORD},
        ).json()['id']

        from datetime import timedelta

        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, FocusEvent, Lesson

        teacher = User.objects.get(username='pf_t')
        self.studentu = User.objects.get(username='pf_s')
        course = Course.objects.create(teacher=teacher, title='PF')
        Enrollment.objects.create(
            course=course, student=self.studentu, status=Enrollment.Status.APPROVED,
        )
        lesson = Lesson.objects.create(
            course=course, starts_at=timezone.now(), duration_min=45,
        )
        Attendance.objects.create(lesson=lesson, student=self.studentu, joined_at=timezone.now())
        t0 = timezone.now()
        for kind, at in [('exit', t0), ('return', t0 + timedelta(seconds=45))]:
            e = FocusEvent.objects.create(lesson=lesson, student=self.studentu, kind=kind)
            FocusEvent.objects.filter(pk=e.pk).update(created_at=at)

    def test_parent_sees_child_focus_timeline(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.parent_token}')
        rows = self.client.get('/api/v1/attendance/').json()['results']
        self.assertEqual(len(rows), 1)
        focus = rows[0]['focus']
        self.assertEqual(focus['exits'], 1)
        self.assertEqual(focus['away_seconds'], 45)
        self.assertEqual(len(focus['timeline']), 1)
        self.assertIsNotNone(focus['timeline'][0]['returned_at'])

    def test_other_parent_sees_nothing(self):
        register(self.client, 'pf_p2', 'parent')
        p2 = login(self.client, 'pf_p2')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {p2}')
        rows = self.client.get('/api/v1/attendance/').json()['results']
        self.assertEqual(len(rows), 0)


class RecordingTests(APITestCase):
    """Dars video yozuvi: nom berish + chat e'loni, faqat-platforma stream,
    ruxsatlar, o'chirish."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings
        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson, LessonRecording

        self.tmp = tempfile.mkdtemp()
        self._override = override_settings(RECORDINGS_DIR=Path(self.tmp))
        self._override.enable()
        self.addCleanup(self._override.disable)

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('rc_t', User.Role.TEACHER)
        self.student = mk('rc_s', User.Role.STUDENT)
        self.stranger = mk('rc_x', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='RC')
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )
        # Egress yozgan faylni imitatsiya qilamiz (egress tasdiqlagan holat)
        self.recording = LessonRecording.objects.create(
            lesson=self.lesson, file_name=f'{self.lesson.room_name}.mp4',
            egress_id='EG_test', status=LessonRecording.Status.RECORDING,
        )
        (Path(self.tmp) / self.recording.file_name).write_bytes(b'\x00' * 2048)

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_finish_saves_title_without_posting_yet(self):
        """finish_lesson endi darhol chatga e'lon qilmaydi — brauzer video/
        audio yuklashni finish tugmasidan KEYIN ham davom ettirishi mumkin
        (asinxron chunked upload). Faqat nomni saqlab qo'yadi."""
        from apps.chat.models import Message

        from . import services as lesson_services
        before = Message.objects.count()
        lesson_services.finish_lesson(
            teacher=self.teacher, lesson=self.lesson,
            recording_title='Kvadrat tenglamalar (video)',
        )
        self.recording.refresh_from_db()
        self.assertEqual(self.recording.title, 'Kvadrat tenglamalar (video)')
        self.assertIsNotNone(self.recording.ended_at)
        self.assertEqual(Message.objects.count(), before)

    def test_announce_recording_ready_posts_saved_title_to_chat(self):
        """Yozuv (birlashtirish/finalize) haqiqatan tayyor bo'lganda —
        finish_lesson orqali saqlangan nom bilan guruh chatga e'lon
        qilinadi."""
        from unittest.mock import patch

        from apps.chat.models import Message

        from . import services as lesson_services
        from apps.live.services import _announce_recording_ready

        lesson_services.finish_lesson(
            teacher=self.teacher, lesson=self.lesson,
            recording_title='Kvadrat tenglamalar (video)',
        )
        self.recording.refresh_from_db()
        with patch('apps.chat.realtime.broadcast_message') as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                _announce_recording_ready(self.recording)
        msg = Message.objects.filter(text__contains='/recordings/').latest('created_at')
        self.assertIn('Kvadrat tenglamalar (video)', msg.text)
        self.assertIn(str(self.lesson.id), msg.text)
        # WebSocket'ga darhol tarqatilishi kerak (2026-09-03: shu bug tuzatildi).
        broadcast.assert_called_once_with(msg)

    def test_info_gives_stream_url_to_member_only(self):
        r = self.api(self.student).get(f'/api/v1/lessons/{self.lesson.id}/recording/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['ready'])
        self.assertIn('/recording/stream/?t=', r.data['stream_url'])
        # begona: dars queryset'ida yo'q — 404 (mavjudligi ham oshkor bo'lmaydi)
        r = self.api(self.stranger).get(f'/api/v1/lessons/{self.lesson.id}/recording/')
        self.assertEqual(r.status_code, 404)

    def test_stream_requires_valid_token(self):
        info = self.api(self.student).get(f'/api/v1/lessons/{self.lesson.id}/recording/')
        url = info.data['stream_url']
        from rest_framework.test import APIClient

        anon = APIClient()  # token URLda — auth header kerak emas
        r = anon.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Disposition'], 'inline')
        # Range (seek) ishlaydi
        r = anon.get(url, HTTP_RANGE='bytes=100-199')
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r['Content-Length'], '100')
        # buzilgan token — yo'q
        r = anon.get(f'/api/v1/lessons/{self.lesson.id}/recording/stream/?t=soxta')
        self.assertEqual(r.status_code, 403)

    def test_delete_teacher_only(self):
        r = self.api(self.student).delete(f'/api/v1/lessons/{self.lesson.id}/recording/')
        self.assertEqual(r.status_code, 403)
        r = self.api(self.teacher).delete(f'/api/v1/lessons/{self.lesson.id}/recording/')
        self.assertEqual(r.status_code, 204)
        from pathlib import Path

        self.assertFalse((Path(self.tmp) / f'{self.lesson.room_name}.mp4').exists())


class FocusEscalationTests(APITestCase):
    """EPAM imtihon uslubi: 1-2 marta oynadan chiqish — o'ziga ogohlantirish,
    3-chisida (FOCUS_PARENT_ALERT_THRESHOLD) — ota-onaga FocusAlert signali."""

    def setUp(self):
        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('fe_t', User.Role.TEACHER)
        self.student = mk('fe_s', User.Role.STUDENT)
        course = Course.objects.create(teacher=self.teacher, title='FE')
        Enrollment.objects.create(course=course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def _exit(self):
        return self.api(self.student).post('/api/v1/live/focus/', {
            'lesson_id': str(self.lesson.id), 'kind': 'exit',
        })

    def test_first_two_exits_only_warn_student(self):
        for expected_count in (1, 2):
            resp = self._exit()
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body['exit_count'], expected_count)
            self.assertEqual(body['threshold'], 3)
            self.assertFalse(body['parent_notified'])
        from .models import FocusAlert
        self.assertFalse(FocusAlert.objects.filter(lesson=self.lesson, student=self.student).exists())

    def test_third_exit_notifies_parent_and_creates_alert(self):
        from .models import FocusAlert

        self._exit()
        self._exit()
        resp = self._exit()
        body = resp.json()
        self.assertEqual(body['exit_count'], 3)
        self.assertTrue(body['parent_notified'])
        alert = FocusAlert.objects.get(lesson=self.lesson, student=self.student)
        self.assertEqual(alert.exit_count, 3)

    def test_alert_created_only_once_despite_further_exits(self):
        from .models import FocusAlert

        for _ in range(5):
            self._exit()
        self.assertEqual(
            FocusAlert.objects.filter(lesson=self.lesson, student=self.student).count(), 1,
        )

    def test_attendance_serializer_exposes_focus_alert(self):
        from django.utils import timezone

        from .models import Attendance

        Attendance.objects.create(lesson=self.lesson, student=self.student, joined_at=timezone.now())
        for _ in range(3):
            self._exit()
        rows = self.api(self.teacher).get('/api/v1/attendance/').json()['results']
        row = next(r for r in rows if r['student']['username'] == 'fe_s')
        self.assertTrue(row['focus_alert'])

    def test_return_event_does_not_affect_counter(self):
        r = self.api(self.student).post('/api/v1/live/focus/', {
            'lesson_id': str(self.lesson.id), 'kind': 'return',
        })
        body = r.json()
        self.assertIsNone(body['exit_count'])
        self.assertFalse(body['parent_notified'])


class RecordingLifecycleTests(APITestCase):
    """Yozuv hayotiy tsikli: yolg'on holatlar yo'q — pending/failed halol,
    e'lon faqat haqiqiy yozuvda, qotib qolganlar avtomatik yakunlanadi."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings
        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        self._override = override_settings(RECORDINGS_DIR=Path(tempfile.mkdtemp()))
        self._override.enable()
        self.addCleanup(self._override.disable)

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('rl_t', User.Role.TEACHER)
        self.student = mk('rl_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='RL')
        from apps.chat import services as chat_services
        chat_services.ensure_course_room(self.course)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(),
            duration_min=45, status=Lesson.Status.LIVE,
        )

    def test_stale_pending_marked_failed_on_info(self):
        """Dars tugagan, fayl 3+ daqiqa yo'q — info so'ralganda halol failed."""
        from datetime import timedelta

        from django.utils import timezone

        from .models import Lesson, LessonRecording

        recording = LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x', file_name='yoq.mp4',
        )
        self.lesson.status = Lesson.Status.FINISHED
        self.lesson.save(update_fields=['status'])
        LessonRecording.objects.filter(pk=recording.pk).update(
            updated_at=timezone.now() - timedelta(minutes=5),
        )

        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(self.teacher)
        r = client.get(f'/api/v1/lessons/{self.lesson.id}/recording/')
        self.assertEqual(r.data['status'], 'failed')
        self.assertIn('yaratilmadi', r.data['error'])


class AudioChunkUploadTests(APITestCase):
    """Brauzerdan chunked video+audio upload va ularni birlashtirish
    (2026-08-27/28 CPU optimallashtirish: video HAM, audio HAM endi
    to'liq o'qituvchi brauzeridan, server-tomon Egress yo'q)."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson, LessonRecording

        self.tmp = tempfile.mkdtemp()
        self._override = override_settings(RECORDINGS_DIR=Path(self.tmp))
        self._override.enable()
        self.addCleanup(self._override.disable)

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('ac_t', User.Role.TEACHER)
        self.student = mk('ac_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='AC')
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(),
            duration_min=45, status=Lesson.Status.LIVE,
        )
        self.LessonRecording = LessonRecording
        self.SimpleUploadedFile = SimpleUploadedFile

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_only_teacher_can_upload_chunk(self):
        chunk = self.SimpleUploadedFile('c.webm', b'\x00' * 100, content_type='audio/webm')
        r = self.api(self.student).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {'chunk': chunk}, format='multipart',
        )
        self.assertEqual(r.status_code, 403)

    def test_missing_chunk_is_rejected(self):
        r = self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {}, format='multipart',
        )
        self.assertEqual(r.status_code, 400)

    def test_oversized_chunk_is_rejected(self):
        from . import services

        big = self.SimpleUploadedFile('c.webm', b'\x00' * (services.AUDIO_CHUNK_MAX_MB * 1024 * 1024 + 1))
        r = self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {'chunk': big}, format='multipart',
        )
        self.assertEqual(r.status_code, 400)

    def test_chunks_append_in_order_and_started_at_set_once(self):
        from pathlib import Path

        c1 = self.SimpleUploadedFile('c.webm', b'AAAA', content_type='audio/webm')
        r = self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/',
            {'chunk': c1, 'started_at': '2026-08-27T10:00:00Z'}, format='multipart',
        )
        self.assertEqual(r.status_code, 204)
        recording = self.LessonRecording.objects.get(lesson=self.lesson)
        self.assertTrue(recording.audio_file_name)
        self.assertEqual(recording.audio_started_at.isoformat(), '2026-08-27T10:00:00+00:00')

        c2 = self.SimpleUploadedFile('c.webm', b'BBBB', content_type='audio/webm')
        r = self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/',
            # ikkinchi chunk'da started_at yuborilsa ham — birinchisi saqlanadi
            {'chunk': c2, 'started_at': '2099-01-01T00:00:00Z'}, format='multipart',
        )
        self.assertEqual(r.status_code, 204)
        recording.refresh_from_db()
        self.assertEqual(recording.audio_started_at.isoformat(), '2026-08-27T10:00:00+00:00')
        content = (Path(self.tmp) / recording.audio_file_name).read_bytes()
        self.assertEqual(content, b'AAAABBBB')

    def test_finalize_without_upload_fails(self):
        r = self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/recording/audio/finalize/')
        self.assertEqual(r.status_code, 400)

    def test_finalize_before_video_ready_does_not_merge(self):
        c1 = self.SimpleUploadedFile('c.webm', b'AAAA')
        self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {'chunk': c1}, format='multipart',
        )
        r = self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/recording/audio/finalize/')
        self.assertEqual(r.status_code, 204)
        recording = self.LessonRecording.objects.get(lesson=self.lesson)
        self.assertIsNotNone(recording.audio_finalized_at)
        self.assertEqual(recording.status, self.LessonRecording.Status.RECORDING)

    def test_finalize_after_video_ready_triggers_merge_thread(self):
        """2026-09-05: merge endi xom `threading.Thread` emas, cheklangan
        `live_services._merge_executor` pool'iga (`ThreadPoolExecutor`)
        yuboriladi — shuning uchun `submit()`ni tekshiramiz, `threading.
        Thread`ni emas."""
        from unittest.mock import patch

        from apps.live import services as live_services

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='video.mp4', video_ready_at=timezone.now(),
            status=self.LessonRecording.Status.RECORDING,
        )
        c1 = self.SimpleUploadedFile('c.webm', b'AAAA')
        self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {'chunk': c1}, format='multipart',
        )
        with patch.object(live_services._merge_executor, 'submit') as submit:
            r = self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/recording/audio/finalize/')
        self.assertEqual(r.status_code, 204)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.MERGING)
        submit.assert_called_once_with(live_services._run_merge_in_pool, recording.pk)

    def test_maybe_start_merge_is_idempotent(self):
        """Video va audio ikkalasi tayyor bo'lganda ikki marta chaqirilsa
        ham (video finalize HAM, audio finalize HAM chaqirishi mumkin) —
        faqat BIR marta merge navbatga qo'yiladi."""
        from unittest.mock import patch

        from apps.live import services as live_services

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='video.mp4', video_ready_at=timezone.now(),
            audio_file_name='audio.webm', audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.RECORDING,
        )
        with patch.object(live_services._merge_executor, 'submit') as submit:
            live_services.maybe_start_merge(self.lesson.id)
            live_services.maybe_start_merge(self.lesson.id)
        submit.assert_called_once()
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.MERGING)

    def test_merge_recording_success_with_offset(self):
        """Haqiqiy ffmpeg bilan: video 0.5s audio'dan keyin boshlangan bo'lsa
        ham, chiqish fayli video+audio bilan yaratiladi."""
        from pathlib import Path

        from apps.live.services import _merge_recording

        video_path = Path(self.tmp) / 'video.webm'
        audio_path = Path(self.tmp) / 'audio.webm'
        self._make_test_video(video_path)
        self._make_test_audio(audio_path)

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='video.webm', video_started_at=timezone.now(),
            audio_file_name='audio.webm',
            audio_started_at=timezone.now() - timedelta(seconds=1),
            audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.MERGING,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED, recording.error)
        self.assertTrue(recording.file_name)
        self.assertTrue((Path(self.tmp) / recording.file_name).exists())
        self.assertGreater((Path(self.tmp) / recording.file_name).stat().st_size, 0)

    def test_merge_recording_survives_concatenated_audio_segments(self):
        """Production'da topilgan xato (2026-08-28): brauzer audio faylini
        bir nechta ALOHIDA yozib olish seansidan (har biri o'z vaqtini
        noldan boshlaydigan) qo'shib yuborsa, ulanish nuqtasida vaqt
        belgisi orqaga qaytadi ("non monotonically increasing dts") va
        `-c:a aac` buni QATTIQ xato deb hisoblab, chiqish faylini umuman
        yaratmay qo'yadi. `-fflags +genpts` buni silliqlab, birlashtirish
        baribir muvaffaqiyatli tugashini ta'minlashi kerak."""
        from pathlib import Path

        from apps.live.services import _merge_recording

        video_path = Path(self.tmp) / 'video.webm'
        self._make_test_video(video_path)

        # Ikkita ALOHIDA audio segment (har biri o'z sarlavhasi/vaqti
        # bilan) — xom baytlarda ulab, "ko'p seansli chunked upload"ni
        # taqlid qilamiz.
        seg1 = Path(self.tmp) / 'seg1.webm'
        seg2 = Path(self.tmp) / 'seg2.webm'
        self._make_test_audio(seg1)
        self._make_test_audio(seg2)
        audio_path = Path(self.tmp) / 'audio.webm'
        audio_path.write_bytes(seg1.read_bytes() + seg2.read_bytes())

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='video.webm', video_started_at=timezone.now(),
            audio_file_name='audio.webm',
            audio_started_at=timezone.now() - timedelta(seconds=1),
            audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.MERGING,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED, recording.error)
        self.assertTrue((Path(self.tmp) / recording.file_name).exists())
        self.assertGreater((Path(self.tmp) / recording.file_name).stat().st_size, 0)

    def test_merge_recording_survives_concatenated_video_segments(self):
        """Production'da topilgan xato (2026-09-01): audio kabi, video
        tomonida ham brauzer sessiyasi tarmoq uzilib-ulanganda yoki
        ekran ulashish o'chirib-yoqilganda qayta boshlanishi mumkin —
        natijada bir nechta mustaqil WebM hujjati xom ulanib qoladi.
        Bunday faylda ikkinchi segmentdan keyingi joyga o'tish umuman
        ishlamas edi ("Output file is empty") — `_normalize_webm` orqali
        to'g'ri ulanishi va yakuniy faylda butun davomiylik bo'ylab
        qidirish ishlashi kerak."""
        from pathlib import Path

        from apps.live.services import _merge_recording

        seg1 = Path(self.tmp) / 'vseg1.webm'
        seg2 = Path(self.tmp) / 'vseg2.webm'
        self._make_test_video(seg1)
        self._make_test_video(seg2)
        video_path = Path(self.tmp) / 'video.webm'
        video_path.write_bytes(seg1.read_bytes() + seg2.read_bytes())
        # Audio ham ~2s bo'lsin — aks holda `-shortest` 1s'li audioga qarab
        # video tomonidagi (2-segment saqlanganmi) tekshiruvni yashirib qo'yardi.
        aseg1 = Path(self.tmp) / 'aseg1.webm'
        aseg2 = Path(self.tmp) / 'aseg2.webm'
        self._make_test_audio(aseg1)
        self._make_test_audio(aseg2)
        audio_path = Path(self.tmp) / 'audio.webm'
        audio_path.write_bytes(aseg1.read_bytes() + aseg2.read_bytes())

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='video.webm', video_started_at=timezone.now(),
            audio_file_name='audio.webm',
            audio_started_at=timezone.now(),
            audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.MERGING,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED, recording.error)
        output_path = Path(self.tmp) / recording.file_name
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

        import subprocess
        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path),
        ], capture_output=True, text=True, timeout=30)
        # Ikkala ~1s video segment ham saqlanishi kerak — faqat birinchisi
        # qolsa (production regressiyasi) ~1s chiqardi.
        self.assertGreater(float(probe.stdout.strip()), 1.5, probe.stdout)
        # Vaqtinchalik normalizatsiya fayli o'chirilgan bo'lishi kerak.
        self.assertFalse((Path(self.tmp) / 'video-normalized.webm').exists())

    def test_normalize_webm_ignores_false_positive_ebml_magic_in_payload(self):
        """Production'da topilgan xato (2026-09-01): `1A45DFA3` baytlari
        siqilgan video ma'lumotlari ICHIDA tasodifan ham uchrashi mumkin.
        Bunday soxta moslikni haqiqiy segment chegarasi deb bo'lib
        yuborilsa, ffmpeg uni EBML sifatida ochaolmay ("EBML header
        parsing failed") butun normalizatsiyani ishdan chiqargan edi.
        Har nomzod ffprobe bilan tasdiqlanishi kerak — yaroqsizi
        e'tiborga olinmasligi kerak."""
        from pathlib import Path

        from apps.live.services import _EBML_MAGIC, _normalize_webm

        video_path = Path(self.tmp) / 'video.webm'
        self._make_test_video(video_path)
        real_bytes = video_path.read_bytes()
        mid = len(real_bytes) // 2
        # Haqiqiy oqim o'rtasiga EBML "sarlavhasi"ga o'xshab boshlanadigan,
        # lekin aslida yaroqsiz baytlar qo'shamiz — soxta moslik taqlidi.
        video_path.write_bytes(real_bytes[:mid] + _EBML_MAGIC + b'\xff' * 200 + real_bytes[mid:])

        result = _normalize_webm(video_path)
        self.assertEqual(result, video_path)

    def test_normalize_webm_single_segment_returns_same_path(self):
        """Oddiy (bitta uzluksiz sessiya) fayl — o'zgarishsiz qaytadi,
        keraksiz ffmpeg ishlov berilmaydi."""
        from pathlib import Path

        from apps.live.services import _normalize_webm

        video_path = Path(self.tmp) / 'video.webm'
        self._make_test_video(video_path)
        result = _normalize_webm(video_path)
        self.assertEqual(result, video_path)

    def test_normalize_webm_multi_segment_keeps_full_duration_and_seeks(self):
        """`_normalize_webm`ni to'g'ridan-to'g'ri sinash: ikkita mustaqil
        WebM segmentini xom ulagandan keyin, IKKALASI ham chiqishda
        saqlanishi va ikkinchi segment ichiga qidirish (seek)
        muvaffaqiyatli bo'lishi kerak.

        Production'da topilgan xato (2026-09-01): `concat` DEMUXERI
        (`-c copy`) bilan ishlaganda, ikkinchi (kattaroq) segment
        ffmpeg tomonidan XATOSIZ, lekin JIMGINA tashlab yuborilgan
        edi — 5:43 daqiqalik yozuvdan atigi 37 soniyasi qolgan.
        Endi `mkvmerge --append` ishlatiladi (qayta kodlamasdan, CPU
        tejash rejasiga mos). Bu yerda nafaqat seek, balki YAKUNIY
        DAVOMIYLIK ham (ikkala segment yig'indisiga yaqin) tekshiriladi
        — aks holda xuddi shu regressiya sezilmasdan qolardi."""
        import subprocess
        from pathlib import Path

        from apps.live.services import _normalize_webm

        seg1 = Path(self.tmp) / 'seg1.webm'
        seg2 = Path(self.tmp) / 'seg2.webm'
        self._make_test_video(seg1)
        self._make_test_video(seg2)
        video_path = Path(self.tmp) / 'video.webm'
        video_path.write_bytes(seg1.read_bytes() + seg2.read_bytes())

        result = _normalize_webm(video_path)
        self.assertNotEqual(result, video_path)
        self.assertTrue(result.exists())

        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(result),
        ], capture_output=True, text=True, timeout=30)
        duration = float(probe.stdout.strip())
        # Har segment ~1s — ikkalasi ham saqlangan bo'lsa jami ~2s bo'lishi
        # kerak. Faqat birinchisi qolsa (production regressiyasi) ~1s chiqardi.
        self.assertGreater(duration, 1.5, probe.stdout)

        # Ikkinchi segment ichiga (~1.5s) qidirish muvaffaqiyatli, bo'sh
        # bo'lmagan natija berishi kerak.
        seek_output = Path(self.tmp) / 'seek_check.webm'
        seek_result = subprocess.run([
            'ffmpeg', '-y', '-ss', '1.5', '-i', str(result), '-t', '0.3',
            '-c', 'copy', str(seek_output),
        ], capture_output=True, timeout=30)
        self.assertEqual(seek_result.returncode, 0, seek_result.stderr)
        self.assertTrue(seek_output.exists())
        self.assertGreater(seek_output.stat().st_size, 0)

    def test_merge_recording_failure_marks_failed(self):
        recording = self.LessonRecording.objects.create(
            lesson=self.lesson, egress_id='EG_x',
            video_file_name='yoq-video.mp4', video_started_at=timezone.now(),
            audio_file_name='yoq-audio.webm', audio_started_at=timezone.now(),
            audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.MERGING,
        )
        from apps.live.services import _merge_recording
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.FAILED)
        self.assertIn('Birlashtirish xatosi', recording.error)

    def test_finalize_single_side_video_only_fallback(self):
        """Audio (brauzerdan) hech qachon kelmasa — video bilan (ovozsiz)
        yakunlanadi, yo'qotilmaydi."""
        from pathlib import Path

        from apps.live.services import finalize_single_side

        video_path = Path(self.tmp) / 'video.webm'
        video_path.write_bytes(b'\x00' * 1024)
        recording = self.LessonRecording.objects.create(
            lesson=self.lesson,
            video_file_name='video.webm', video_ready_at=timezone.now(),
            status=self.LessonRecording.Status.RECORDING,
        )
        finalize_single_side(self.lesson.id)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED)
        self.assertEqual(recording.file_name, 'video.webm')

    def test_finalize_single_side_audio_only_fallback(self):
        """Video (brauzerdan — ekran ulashish ruxsati berilmagan va h.k.)
        hech qachon kelmasa — audio bilan yakunlanadi, yo'qotilmaydi.
        Video Track Egress orqali server-tomon KAFOLATLANMASdi (2026-08-28,
        2-bosqich: video ham brauzerdan) — shuning uchun bu holat endi
        haqiqiy imkoniyat."""
        from pathlib import Path

        from apps.live.services import finalize_single_side

        audio_path = Path(self.tmp) / 'audio.webm'
        audio_path.write_bytes(b'\x00' * 1024)
        recording = self.LessonRecording.objects.create(
            lesson=self.lesson,
            audio_file_name='audio.webm', audio_finalized_at=timezone.now(),
            status=self.LessonRecording.Status.RECORDING,
        )
        finalize_single_side(self.lesson.id)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED)
        self.assertEqual(recording.file_name, 'audio.webm')

    def test_finalize_single_side_normalizes_multi_segment_video(self):
        """Merge bo'lmasa ham (ikkinchi tomon umuman kelmagan) yagona
        tomon ko'p-segmentli bo'lishi mumkin — shu yerda ham to'g'rilanishi
        kerak, aks holda qidirish/pauza qotib qolardi."""
        from pathlib import Path

        from apps.live.services import finalize_single_side

        seg1 = Path(self.tmp) / 'vseg1.webm'
        seg2 = Path(self.tmp) / 'vseg2.webm'
        self._make_test_video(seg1)
        self._make_test_video(seg2)
        video_path = Path(self.tmp) / 'video.webm'
        video_path.write_bytes(seg1.read_bytes() + seg2.read_bytes())

        recording = self.LessonRecording.objects.create(
            lesson=self.lesson,
            video_file_name='video.webm', video_ready_at=timezone.now(),
            status=self.LessonRecording.Status.RECORDING,
        )
        finalize_single_side(self.lesson.id)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.COMPLETED)
        self.assertEqual(recording.file_name, 'video-normalized.webm')
        output_path = Path(self.tmp) / recording.file_name
        self.assertTrue(output_path.exists())

        import subprocess
        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path),
        ], capture_output=True, text=True, timeout=30)
        # Ikkala ~1s segment ham saqlanishi kerak — faqat birinchisi
        # qolsa (production regressiyasi) ~1s chiqardi.
        self.assertGreater(float(probe.stdout.strip()), 1.5, probe.stdout)

    def test_only_teacher_can_upload_video_chunk(self):
        chunk = self.SimpleUploadedFile('c.webm', b'\x00' * 100, content_type='video/webm')
        r = self.api(self.student).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/video/', {'chunk': chunk}, format='multipart',
        )
        self.assertEqual(r.status_code, 403)

    def test_video_chunks_append_and_finalize_triggers_merge_with_audio(self):
        from unittest.mock import patch

        from apps.live import services as live_services

        c1 = self.SimpleUploadedFile('c.webm', b'VVVV', content_type='video/webm')
        r = self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/video/',
            {'chunk': c1, 'started_at': '2026-08-28T10:00:00Z'}, format='multipart',
        )
        self.assertEqual(r.status_code, 204)
        recording = self.LessonRecording.objects.get(lesson=self.lesson)
        self.assertTrue(recording.video_file_name)
        self.assertEqual(recording.status, self.LessonRecording.Status.RECORDING)

        a1 = self.SimpleUploadedFile('c.webm', b'AAAA')
        self.api(self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/audio/', {'chunk': a1}, format='multipart',
        )
        self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/recording/video/finalize/')
        with patch.object(live_services._merge_executor, 'submit') as submit:
            r = self.api(self.teacher).post(f'/api/v1/lessons/{self.lesson.id}/recording/audio/finalize/')
        self.assertEqual(r.status_code, 204)
        recording.refresh_from_db()
        self.assertEqual(recording.status, self.LessonRecording.Status.MERGING)
        submit.assert_called_once()

    @staticmethod
    def _make_test_video(path):
        import subprocess
        # libvpx (VP8) + webm — brauzer kamerasi haqiqatda shu kodeklarni
        # yuboradi (Track Egress xom nusxa ko'chirgani uchun). libx264/mp4
        # bilan test qilish production'dagi "VP8 MP4'ga sig'maydi" xatosini
        # yashirib qo'yardi (2026-08-28 real incident).
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=1',
            '-c:v', 'libvpx', '-t', '1', str(path),
        ], capture_output=True, check=True)

    @staticmethod
    def _make_test_audio(path):
        import subprocess
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
            '-c:a', 'libopus', str(path),
        ], capture_output=True, check=True)


class InviteBanTests(APITestCase):
    """Zoom uslubidagi dars moderatsiyasi: o'qituvchi taklif yuboradi va
    o'quvchini chetlashtiradi (ban qilingan qayta token ololmaydi)."""

    def setUp(self):
        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('ib_t', User.Role.TEACHER)
        self.student = mk('ib_s', User.Role.STUDENT)
        self.other_student = mk('ib_s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='IB')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.other_student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_invite_single_student_sends_notification(self):
        resp = self.api(self.teacher).post('/api/v1/live/invite/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['invited'], 1)

        inbox = self.api(self.student).get('/api/v1/notifications/').json()['results']
        self.assertEqual(len(inbox), 1)
        self.assertIn(self.lesson.course.title, inbox[0]['notification']['description'])
        self.assertEqual(
            len(self.api(self.other_student).get('/api/v1/notifications/').json()['results']), 0,
        )

    def test_invite_without_student_id_notifies_everyone_enrolled(self):
        resp = self.api(self.teacher).post('/api/v1/live/invite/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.data['invited'], 2)
        self.assertEqual(
            len(self.api(self.student).get('/api/v1/notifications/').json()['results']), 1,
        )
        self.assertEqual(
            len(self.api(self.other_student).get('/api/v1/notifications/').json()['results']), 1,
        )

    def test_non_owner_teacher_cannot_invite(self):
        from apps.accounts.models import User

        other_teacher = User(username='ib_t2', role=User.Role.TEACHER)
        other_teacher.set_password('x')
        other_teacher.save()
        resp = self.api(other_teacher).post('/api/v1/live/invite/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_invite(self):
        resp = self.api(self.student).post('/api/v1/live/invite/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 403)

    def test_ban_blocks_future_token_requests(self):
        # ban'dan oldin — o'quvchi kira oladi
        resp = self.api(self.student).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)

        ban_resp = self.api(self.teacher).post('/api/v1/live/ban/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(ban_resp.status_code, 200)

        resp = self.api(self.student).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 403)

        # boshqa o'quvchiga ta'sir qilmaydi
        resp = self.api(self.other_student).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)

    def test_ban_does_not_block_teacher(self):
        from .models import LessonBan

        LessonBan.objects.create(lesson=self.lesson, student=self.teacher, banned_by=self.teacher)
        resp = self.api(self.teacher).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)

    def test_unban_restores_access(self):
        self.api(self.teacher).post('/api/v1/live/ban/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        unban_resp = self.api(self.teacher).post('/api/v1/live/unban/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(unban_resp.data['unbanned'], True)

        resp = self.api(self.student).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_teacher_cannot_ban(self):
        from apps.accounts.models import User

        other_teacher = User(username='ib_t3', role=User.Role.TEACHER)
        other_teacher.set_password('x')
        other_teacher.save()
        resp = self.api(other_teacher).post('/api/v1/live/ban/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(resp.status_code, 403)

    def test_ban_unknown_student_returns_404(self):
        import uuid

        resp = self.api(self.teacher).post('/api/v1/live/ban/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(uuid.uuid4()),
        })
        self.assertEqual(resp.status_code, 404)


class JoinQueueTests(APITestCase):
    """Ulanish navbati (FIFO, cheklangan parallellik) — production'da
    o'lchangan (2026-09-02): bir darsga qisqa vaqt ichida ko'p o'quvchi
    ulansa, LiveKit'da CPU 5-8x portlaydi. Server har o'quvchiga
    `join_delay_ms` qaytaradi — frontend shuncha kutib, keyin ulanadi."""

    def setUp(self):
        from django.core.cache import cache
        from django.utils import timezone

        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        cache.clear()

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('jq_t', User.Role.TEACHER)
        self.students = [mk(f'jq_s{i}', User.Role.STUDENT) for i in range(8)]
        self.course = Course.objects.create(teacher=self.teacher, title='JQ')
        for s in self.students:
            Enrollment.objects.create(course=self.course, student=s, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_teacher_never_delayed(self):
        resp = self.api(self.teacher).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.data['join_delay_ms'], 0)

    def test_first_batch_of_students_not_delayed(self):
        # _JOIN_QUEUE_BATCH_SIZE = 6 — birinchi 6 o'quvchi darhol kiradi.
        for s in self.students[:6]:
            resp = self.api(s).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
            self.assertEqual(resp.data['join_delay_ms'], 0)

    def test_next_batch_is_delayed_by_one_interval(self):
        for s in self.students[:6]:
            self.api(s).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        # 7-o'quvchi — keyingi partiya, +1 interval kutadi.
        resp = self.api(self.students[6]).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.data['join_delay_ms'], 1200)
        # 8-o'quvchi ham xuddi shu (hali ikkinchi partiya) partiyada.
        resp = self.api(self.students[7]).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.data['join_delay_ms'], 1200)

    def test_different_lessons_share_one_global_queue(self):
        """Navbat DARS bo'yicha emas — butun server uchun BITTA (global).
        Sabab: 150 ta turli dars bir vaqtda boshlansa ham, jami parallel
        ulanish sonini cheklash kerak, dars qaysi bo'lishidan qat'iy
        nazar (izohga qarang, `_compute_join_delay_ms`)."""
        from django.utils import timezone

        from .models import Course, Enrollment, Lesson

        other_course = Course.objects.create(teacher=self.teacher, title='JQ2')
        Enrollment.objects.create(
            course=other_course, student=self.students[0], status=Enrollment.Status.APPROVED,
        )
        other_lesson = Lesson.objects.create(
            course=other_course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )
        # Birinchi darsda navbatni to'ldiramiz (global hisoblagich 6ga yetadi).
        for s in self.students[:6]:
            self.api(s).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        # BOSHQA darsga kiruvchi ham xuddi shu global navbatda — kechikadi.
        resp = self.api(self.students[0]).post('/api/v1/live/token/', {'lesson_id': str(other_lesson.id)})
        self.assertEqual(resp.data['join_delay_ms'], 1200)

    def test_delay_grows_unbounded_for_extreme_burst_no_pileup_at_cap(self):
        """2026-09-04 tuzatildi: avval qat'iy chegara (20s) bor edi — chegaraga
        yetgan HAMMASI o'sha nuqtaning o'zida zichlashib qolib, aynan oldini
        olishga harakat qilingan portlashning o'zini qayta yaratardi (faqat
        kechiktirilgan holda). Endi chegara YO'Q — xavfsiz tezlik (6/1.2s)
        N qancha katta bo'lmasin, HECH QACHON buzilmaydi, kechikish shunchaki
        chiziqli o'sib boradi (`AWS full-jitter` singari tasodifiy taxminlash
        emas — bu yerda markazlashgan, aniq hisoblagich borligi uchun
        qat'iy tezlik cheklovi ustunroq)."""
        from apps.live.services import (
            _JOIN_QUEUE_BATCH_INTERVAL_MS,
            _JOIN_QUEUE_BATCH_SIZE,
            _compute_join_delay_ms,
        )

        delays = [_compute_join_delay_ms() for _ in range(600)]
        # 500-pozitsiyaga yaqin kishi eski (20s) chegaradan SEZILARLI uzoqroq
        # kutadi — bu ATAYLAB shunday (pastga qarang), pileup emas.
        self.assertGreater(delays[499], 20_000)
        # Hech ikkita KETMA-KET PARTIYA bir xil kechikishga ega emas — ya'ni
        # hech qanday nuqtada "tekislanib" cheklanmayapti, chiziqli davom etadi.
        expected_last = ((600 - 1) // _JOIN_QUEUE_BATCH_SIZE) * _JOIN_QUEUE_BATCH_INTERVAL_MS
        self.assertEqual(delays[-1], expected_last)


class MicPermissionTests(APITestCase):
    """Mikrofon so'rov/ruxsat: o'quvchi standart holatda mikrofonsiz kiradi,
    so'raydi ("qo'l ko'tarish"), o'qituvchi ruxsat beradi."""

    def setUp(self):
        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('mic_t', User.Role.TEACHER)
        self.student = mk('mic_s', User.Role.STUDENT)
        self.stranger = mk('mic_s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='MIC')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45,
            status=Lesson.Status.LIVE,
        )

    def api(self, user):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user)
        return c

    def _decode(self, token):
        import jwt
        from django.conf import settings

        return jwt.decode(token, settings.LIVEKIT_API_SECRET, algorithms=['HS256'])

    def test_student_token_excludes_camera_and_microphone_by_default(self):
        """2026-09-04: kamera ham endi ruxsat bilan ochiladi (avval erkin edi).

        KRITIK REGRESSIYA TEKSHIRUVI (2026-09-05, ikki ishtirokchi bilan
        haqiqiy sinovda topilgan): bo'sh `canPublishSources` ro'yxati LiveKit
        protokolida "cheklov YO'Q, hamma manba OCHIQ" degani — "hech narsa
        mumkin emas" EMAS (https://docs.livekit.io/frontends/reference/
        tokens-grants/). Shuning uchun faqat `canPublishSources`ning bo'sh
        ekanini tekshirish YETARLI EMAS — bu eski test xuddi shu sababdan
        soxta xotirjamlik bergan edi (bo'sh ro'yxatda "camera"/"microphone"
        bo'lishi mumkin emas, lekin bu hech narsani cheklamasdi!). Haqiqiy
        kafolat — `canPublish: False` bo'lishi kerak (LiveKit'ning "bosh
        kalit"i, faqat shu chindan bloklaydi)."""
        resp = self.api(self.student).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)
        video_claim = self._decode(resp.data['token'])['video']
        self.assertFalse(video_claim.get('canPublish'))
        sources = video_claim.get('canPublishSources', [])
        self.assertNotIn('camera', sources)
        self.assertNotIn('microphone', sources)

    def test_teacher_token_unrestricted(self):
        resp = self.api(self.teacher).post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(resp.status_code, 200)
        video_claim = self._decode(resp.data['token'])['video']
        self.assertTrue(video_claim.get('canPublish'))
        self.assertNotIn('canPublishSources', video_claim)

    def test_request_mic_requires_enrollment(self):
        resp = self.api(self.stranger).post(
            '/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)},
        )
        self.assertEqual(resp.status_code, 403)

    def test_request_mic_ok_for_enrolled_student(self):
        resp = self.api(self.student).post(
            '/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)},
        )
        self.assertEqual(resp.status_code, 200)

    def test_request_mic_persists_for_late_joining_teacher(self):
        """So'rov faqat WebSocket'da emas, bazada ham qoladi — o'qituvchi
        so'rovdan keyin kirsa ham (yangi WS ulanish emas, oddiy funksiya
        chaqiruvi bilan tekshiramiz) ko'rinishi kerak."""
        from apps.live.services import pending_mic_requests

        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})
        pending = pending_mic_requests(self.lesson)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['student_id'], str(self.student.id))

    def test_grant_mic_clears_pending_request(self):
        from unittest.mock import AsyncMock, patch

        from livekit.protocol.models import ParticipantInfo, ParticipantPermission, TrackSource

        from apps.live.services import pending_mic_requests

        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(len(pending_mic_requests(self.lesson)), 1)

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_client = mock_livekit_cls.return_value
            mock_client.room.get_participant = AsyncMock(return_value=ParticipantInfo(
                permission=ParticipantPermission(can_publish_sources=[TrackSource.CAMERA]),
            ))
            mock_client.room.update_participant = AsyncMock()
            mock_client.aclose = AsyncMock()

            self.api(self.teacher).post('/api/v1/live/grant-mic/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })

        self.assertEqual(pending_mic_requests(self.lesson), [])

    def test_duplicate_request_does_not_spam_queue(self):
        """Bitta o'quvchi bir vaqtda faqat bitta faol so'rovga ega bo'ladi —
        qayta so'rasa dublikat qo'shilmaydi."""
        from apps.live.services import pending_mic_requests

        for _ in range(3):
            resp = self.api(self.student).post(
                '/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)},
            )
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(pending_mic_requests(self.lesson)), 1)

    def test_pending_requests_are_fifo_ordered(self):
        from apps.accounts.models import User

        from .models import Enrollment

        second = User(username='mic_s3', role=User.Role.STUDENT)
        second.set_password('x')
        second.save()
        Enrollment.objects.create(course=self.course, student=second, status=Enrollment.Status.APPROVED)

        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})
        self.api(second).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})

        from apps.live.services import pending_mic_requests
        pending = pending_mic_requests(self.lesson)
        self.assertEqual([p['student_id'] for p in pending], [str(self.student.id), str(second.id)])

    def test_deny_mic_removes_request_without_granting_permission(self):
        from unittest.mock import patch

        from apps.live.services import pending_mic_requests

        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            resp = self.api(self.teacher).post('/api/v1/live/deny-mic/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.data['denied'])
            # LiveKit'ga umuman murojaat qilinmadi — faqat navbatdan olib tashlandi
            mock_livekit_cls.assert_not_called()

        self.assertEqual(pending_mic_requests(self.lesson), [])

    def test_request_camera_requires_enrollment(self):
        resp = self.api(self.stranger).post(
            '/api/v1/live/request-camera/', {'lesson_id': str(self.lesson.id)},
        )
        self.assertEqual(resp.status_code, 403)

    def test_grant_camera_adds_camera_source_and_clears_pending(self):
        from unittest.mock import AsyncMock, patch

        from livekit.protocol.models import ParticipantInfo, ParticipantPermission, TrackSource

        from apps.live.services import pending_camera_requests

        self.api(self.student).post('/api/v1/live/request-camera/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(len(pending_camera_requests(self.lesson)), 1)

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_client = mock_livekit_cls.return_value
            mock_client.room.get_participant = AsyncMock(return_value=ParticipantInfo(
                permission=ParticipantPermission(can_publish_sources=[]),
            ))
            mock_client.room.update_participant = AsyncMock()
            mock_client.aclose = AsyncMock()

            resp = self.api(self.teacher).post('/api/v1/live/grant-camera/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })
            self.assertEqual(resp.status_code, 200)
            call = mock_client.room.update_participant.call_args
            sent_request = call.args[0]
            self.assertIn(TrackSource.CAMERA, sent_request.permission.can_publish_sources)

        self.assertEqual(pending_camera_requests(self.lesson), [])

    def test_deny_camera_removes_request_without_granting_permission(self):
        from unittest.mock import patch

        from apps.live.services import pending_camera_requests

        self.api(self.student).post('/api/v1/live/request-camera/', {'lesson_id': str(self.lesson.id)})

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            resp = self.api(self.teacher).post('/api/v1/live/deny-camera/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.data['denied'])
            mock_livekit_cls.assert_not_called()

        self.assertEqual(pending_camera_requests(self.lesson), [])

    def test_deny_unknown_request_returns_false(self):
        resp = self.api(self.teacher).post('/api/v1/live/deny-mic/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['denied'])

    def test_deny_mic_requires_owner_teacher(self):
        from apps.accounts.models import User

        other_teacher = User(username='mic_t4', role=User.Role.TEACHER)
        other_teacher.set_password('x')
        other_teacher.save()
        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})
        resp = self.api(other_teacher).post('/api/v1/live/deny-mic/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(resp.status_code, 403)

    def test_can_request_again_after_denied(self):
        from apps.live.services import pending_mic_requests

        self.api(self.student).post('/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)})
        self.api(self.teacher).post('/api/v1/live/deny-mic/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(pending_mic_requests(self.lesson), [])

        resp = self.api(self.student).post(
            '/api/v1/live/request-mic/', {'lesson_id': str(self.lesson.id)},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(pending_mic_requests(self.lesson)), 1)

    def test_grant_mic_requires_owner_teacher(self):
        from apps.accounts.models import User

        other_teacher = User(username='mic_t2', role=User.Role.TEACHER)
        other_teacher.set_password('x')
        other_teacher.save()
        resp = self.api(other_teacher).post('/api/v1/live/grant-mic/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
        })
        self.assertEqual(resp.status_code, 403)

    def test_grant_mic_unknown_student_404(self):
        import uuid

        resp = self.api(self.teacher).post('/api/v1/live/grant-mic/', {
            'lesson_id': str(self.lesson.id), 'student_id': str(uuid.uuid4()),
        })
        self.assertEqual(resp.status_code, 404)

    def test_grant_mic_adds_microphone_to_publish_sources(self):
        from unittest.mock import AsyncMock, patch

        from livekit.protocol.models import ParticipantInfo, ParticipantPermission, TrackSource

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_client = mock_livekit_cls.return_value
            mock_client.room.get_participant = AsyncMock(return_value=ParticipantInfo(
                permission=ParticipantPermission(can_publish_sources=[TrackSource.CAMERA]),
            ))
            mock_client.room.update_participant = AsyncMock()
            mock_client.aclose = AsyncMock()

            resp = self.api(self.teacher).post('/api/v1/live/grant-mic/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })
            self.assertEqual(resp.status_code, 200)

            sent = mock_client.room.update_participant.call_args.args[0]
            sources = set(sent.permission.can_publish_sources)
            self.assertIn(TrackSource.MICROPHONE, sources)
            self.assertIn(TrackSource.CAMERA, sources)

    def test_grant_mic_preserves_existing_screen_share_permission(self):
        """update_participant butun ro'yxatni ALMASHTIRADI — shuning uchun
        grant_mic joriy ruxsatlarni o'qib, ustiga qo'shishi kerak, aks holda
        avval berilgan ekran ulashish ruxsati tasodifan yo'qolib qolardi."""
        from unittest.mock import AsyncMock, patch

        from livekit.protocol.models import ParticipantInfo, ParticipantPermission, TrackSource

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_client = mock_livekit_cls.return_value
            mock_client.room.get_participant = AsyncMock(return_value=ParticipantInfo(
                permission=ParticipantPermission(
                    can_publish_sources=[TrackSource.CAMERA, TrackSource.SCREEN_SHARE],
                ),
            ))
            mock_client.room.update_participant = AsyncMock()
            mock_client.aclose = AsyncMock()

            self.api(self.teacher).post('/api/v1/live/grant-mic/', {
                'lesson_id': str(self.lesson.id), 'student_id': str(self.student.id),
            })

            sent = mock_client.room.update_participant.call_args.args[0]
            sources = set(sent.permission.can_publish_sources)
            self.assertIn(TrackSource.SCREEN_SHARE, sources)
            self.assertIn(TrackSource.MICROPHONE, sources)

    def test_grant_screen_share_preserves_existing_mic_permission(self):
        """2026-09-05 topilgan xato: `grant_screen_share` avval butun
        ro'yxatni [CAMERA, MICROPHONE, SCREEN_SHARE, SCREEN_SHARE_AUDIO]
        bilan QATTIQ ALMASHTIRARDI — o'qituvchi FAQAT ekran ulashishga
        ruxsat bermoqchi bo'lsa ham, kamera/mikrofonni BEXOSDAN ochib
        yuborardi, yoki avval FAQAT mikrofon berilgan bo'lsa, uni yo'qotib
        qo'yardi. Endi `grant_mic`/`grant_camera` bilan bir xil — mavjudini
        saqlab, faqat ekran ulashishni qo'shadi."""
        from unittest.mock import AsyncMock, patch

        from livekit.protocol.models import ParticipantInfo, ParticipantPermission, TrackSource

        identity = f'user-{self.student.id}'
        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_client = mock_livekit_cls.return_value
            mock_client.room.get_participant = AsyncMock(return_value=ParticipantInfo(
                permission=ParticipantPermission(can_publish_sources=[TrackSource.MICROPHONE]),
            ))
            mock_client.room.update_participant = AsyncMock()
            mock_client.aclose = AsyncMock()

            resp = self.api(self.teacher).post('/api/v1/live/allow-share/', {
                'lesson_id': str(self.lesson.id), 'identity': identity,
            })
            self.assertEqual(resp.status_code, 200)

            sent = mock_client.room.update_participant.call_args.args[0]
            sources = set(sent.permission.can_publish_sources)
            self.assertIn(TrackSource.MICROPHONE, sources)
            self.assertIn(TrackSource.SCREEN_SHARE, sources)
            self.assertIn(TrackSource.SCREEN_SHARE_AUDIO, sources)
            # Kamera ATAYLAB so'ralmagan — shuning uchun bexosdan ochilmasligi kerak.
            self.assertNotIn(TrackSource.CAMERA, sources)


class AutoFinishExpiredLessonsTests(APITestCase):
    """Vaqti tugagan, lekin hali LIVE qolib ketgan darslarni avtomatik
    yakunlash — o'qituvchi 'tugatish'ni bosmagan/brauzeri yiqilgan holatlar."""

    def setUp(self):
        from apps.accounts.models import User

        from .models import Course, Lesson

        def mk(username, role):
            u = User(username=username, role=role)
            u.set_password('x')
            u.save()
            return u

        self.teacher = mk('af_t', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='AF')

        now = timezone.now()
        # Vaqti allaqachon tugagan (45 daqiqa oldin boshlangan, 30 daqiqalik dars)
        self.expired = Lesson.objects.create(
            course=self.course, starts_at=now - timedelta(minutes=45),
            duration_min=30, status=Lesson.Status.LIVE,
        )
        # Hali davom etayotgan (10 daqiqa oldin boshlangan, 45 daqiqalik dars)
        self.still_live = Lesson.objects.create(
            course=self.course, starts_at=now - timedelta(minutes=10),
            duration_min=45, status=Lesson.Status.LIVE,
        )
        # SCHEDULED holatda, vaqti tugagan bo'lsa ham — tegilmasligi kerak
        self.never_started = Lesson.objects.create(
            course=self.course, starts_at=now - timedelta(hours=2),
            duration_min=30, status=Lesson.Status.SCHEDULED,
        )

    def test_only_expired_live_lessons_are_finished(self):
        from .models import Lesson
        from . import services

        count = services.auto_finish_expired_lessons()
        self.assertEqual(count, 1)

        self.expired.refresh_from_db()
        self.still_live.refresh_from_db()
        self.never_started.refresh_from_db()
        self.assertEqual(self.expired.status, Lesson.Status.FINISHED)
        self.assertEqual(self.still_live.status, Lesson.Status.LIVE)
        self.assertEqual(self.never_started.status, Lesson.Status.SCHEDULED)

    def test_open_attendance_is_closed(self):
        from .models import Attendance
        from . import services

        Attendance.objects.create(lesson=self.expired, student=self.teacher, joined_at=timezone.now())
        services.auto_finish_expired_lessons()
        att = Attendance.objects.get(lesson=self.expired, student=self.teacher)
        self.assertIsNotNone(att.left_at)

    def test_idempotent_second_run_finishes_nothing_new(self):
        from . import services

        services.auto_finish_expired_lessons()
        count2 = services.auto_finish_expired_lessons()
        self.assertEqual(count2, 0)

    def test_late_started_lesson_not_finished_by_scheduled_time(self):
        """2026-09-04 bug: rejalashtirilgan (starts_at) vaqti allaqachon
        o'tgan bo'lsa ham, o'qituvchi KECH kirib darsni HOZIRGINA boshlagan
        bo'lsa — hali davom etayotgan safar uzilmasligi kerak."""
        from . import services
        from .models import Lesson

        now = timezone.now()
        late = Lesson.objects.create(
            course=self.course, starts_at=now - timedelta(hours=2), duration_min=30,
            status=Lesson.Status.LIVE, live_started_at=now - timedelta(minutes=5),
        )
        count = services.auto_finish_expired_lessons()
        late.refresh_from_db()
        self.assertEqual(late.status, Lesson.Status.LIVE)
        self.assertNotIn(late.id, [self.expired.id])
        self.assertEqual(count, 1)  # faqat self.expired (live_started_at yo'q, eski hisob)

    def test_lesson_finished_after_live_started_plus_grace(self):
        from . import services
        from .models import Lesson

        now = timezone.now()
        stuck = Lesson.objects.create(
            course=self.course, starts_at=now - timedelta(hours=3),
            duration_min=30, status=Lesson.Status.LIVE,
            live_started_at=now - timedelta(minutes=61),  # 30 + 30 grace = 60 dan o'tgan
        )
        services.auto_finish_expired_lessons()
        stuck.refresh_from_db()
        self.assertEqual(stuck.status, Lesson.Status.FINISHED)

    def test_teacher_rejoining_stale_live_lesson_refreshes_clock(self):
        """2026-09-04 tuzatildi: `live_started_at` avval FAQAT birinchi marta
        LIVE'ga o'tganda yozilardi. O'qituvchi darsni tashlab ketib (masalan
        sahifani yopib), SOATLAR o'tib — allaqachon "muddati o'tgan" holatga
        yetgan bir paytda — qaytadan kirsa, eski soat hamon o'sha-o'sha
        qolgani uchun auto-finish uni deyarli DARHOL (keyingi cron
        aylanishida) yopib qo'yardi. Endi qayta kirish soatni yangilaydi."""
        from rest_framework.test import APIClient

        from . import services
        from .models import Lesson

        stale = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() - timedelta(hours=3),
            duration_min=45, status=Lesson.Status.LIVE,
            live_started_at=timezone.now() - timedelta(hours=2),  # 45+30=75 daqiqadan ancha o'tgan
        )

        client = APIClient()
        client.force_authenticate(self.teacher)
        resp = client.post('/api/v1/live/token/', {'lesson_id': str(stale.id)})
        self.assertEqual(resp.status_code, 200)

        # Qayta kirgan zahoti fon vazifasi ishga tushsa ham — endi yopilmasligi kerak.
        services.auto_finish_expired_lessons()
        stale.refresh_from_db()
        self.assertEqual(stale.status, Lesson.Status.LIVE)

    def test_auto_finish_triggers_merge_when_teacher_never_clicked_finish(self):
        """2026-09-05 topilgan production xato: o'qituvchi darsni ekrandan
        shunchaki tashlab ketadi (jonli dars ekranida "Yakunlash" tugmasi
        yo'q — buni alohida sahifadan qidirib topish kerak), frontend
        `finalize_recording_video`/`finalize_recording_audio`ni HECH QACHON
        chaqirmaydi. Auto-finish darsni "finished" qilgandan keyin ham,
        video+audio bo'laklari mavjud bo'lsa — backend o'zi ularni finalize
        qilib, birlashtirishni ishga tushirishi kerak."""
        from unittest.mock import AsyncMock, patch

        from . import services
        from .models import Lesson, LessonRecording

        recording = LessonRecording.objects.create(
            lesson=self.expired,
            video_file_name='video.webm', audio_file_name='audio.webm',
            status=LessonRecording.Status.RECORDING,
        )
        from apps.live import services as live_services

        with patch.object(live_services._merge_executor, 'submit') as submit, \
                patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_livekit_cls.return_value.room.delete_room = AsyncMock()
            mock_livekit_cls.return_value.aclose = AsyncMock()
            services.auto_finish_expired_lessons()
        self.expired.refresh_from_db()
        self.assertEqual(self.expired.status, Lesson.Status.FINISHED)
        recording.refresh_from_db()
        self.assertIsNotNone(recording.video_ready_at)
        self.assertIsNotNone(recording.audio_finalized_at)
        self.assertEqual(recording.status, LessonRecording.Status.MERGING)
        submit.assert_called_once()

    def test_auto_finish_completes_video_only_recording_with_no_audio(self):
        """O'qituvchi hech qachon mikrofon/ovoz yubormagan (yoki audio
        umuman kelmagan) holatda ham — abandon qilingan yagona tomon
        (video) yo'qotilmasligi, avtomatik yakunlanishi kerak."""
        import tempfile
        from pathlib import Path
        from unittest.mock import AsyncMock, patch

        from django.test import override_settings

        from . import services
        from .models import LessonRecording

        recording = LessonRecording.objects.create(
            lesson=self.expired, video_file_name='video.webm',
            status=LessonRecording.Status.RECORDING,
        )
        tmp = tempfile.mkdtemp()
        with override_settings(RECORDINGS_DIR=Path(tmp)), \
                patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_livekit_cls.return_value.room.delete_room = AsyncMock()
            mock_livekit_cls.return_value.aclose = AsyncMock()
            (Path(tmp) / 'video.webm').write_bytes(b'\x00' * 10)
            services.auto_finish_expired_lessons()
        recording.refresh_from_db()
        self.assertEqual(recording.status, LessonRecording.Status.COMPLETED)
        self.assertEqual(recording.file_name, 'video.webm')

    def test_auto_finish_without_any_recording_does_not_crash(self):
        """Bu darsda umuman video/audio yozuvi bo'lmasa (LessonRecording
        yaratilmagan) — auto-finish xatosiz o'tishi kerak."""
        from unittest.mock import AsyncMock, patch

        from . import services
        from .models import Lesson

        with patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_livekit_cls.return_value.room.delete_room = AsyncMock()
            mock_livekit_cls.return_value.aclose = AsyncMock()
            count = services.auto_finish_expired_lessons()
        self.expired.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(self.expired.status, Lesson.Status.FINISHED)

    def test_auto_finish_does_not_reset_already_finalized_side(self):
        """Bitta tomon allaqachon finalize qilingan bo'lsa (masalan
        o'qituvchi audio finalize'ni bosgan, keyin brauzeri qulab tushgan)
        — auto-finish uning vaqtini QAYTA yozib yubormasligi kerak, faqat
        yetishmayotgan tomonni to'ldirishi kerak."""
        from unittest.mock import AsyncMock, patch

        from . import services
        from .models import LessonRecording

        original_audio_ts = timezone.now() - timedelta(hours=1)
        recording = LessonRecording.objects.create(
            lesson=self.expired,
            video_file_name='video.webm', audio_file_name='audio.webm',
            audio_finalized_at=original_audio_ts,
            status=LessonRecording.Status.RECORDING,
        )
        from apps.live import services as live_services

        with patch.object(live_services._merge_executor, 'submit'), \
                patch('apps.live.services.LiveKitAPI') as mock_livekit_cls:
            mock_livekit_cls.return_value.room.delete_room = AsyncMock()
            mock_livekit_cls.return_value.aclose = AsyncMock()
            services.auto_finish_expired_lessons()
        recording.refresh_from_db()
        self.assertEqual(recording.audio_finalized_at, original_audio_ts)
        self.assertIsNotNone(recording.video_ready_at)


class LessonReminderTests(APITestCase):
    """"Dars N daqiqadan keyin boshlanadi" — har foydalanuvchining o'z
    `lesson_reminder_minutes` sozlamasiga ko'ra, har juftlikka bir marta."""

    def setUp(self):
        from apps.accounts.models import User

        from .models import Course, Enrollment, Lesson

        def mk(username, role, reminder_minutes=15):
            u = User(username=username, role=role, lesson_reminder_minutes=reminder_minutes)
            u.set_password('x')
            u.save()
            return u

        self.mk = mk
        self.teacher = mk('lr_t', User.Role.TEACHER)
        self.student = mk('lr_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='LR')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)

    def inbox_texts(self, user):
        from apps.notifications.models import NotificationRecipient

        return [
            r.notification.description
            for r in NotificationRecipient.objects.filter(user=user).select_related('notification')
        ]

    def test_reminder_sent_when_window_reached(self):
        from .models import Lesson
        from . import services

        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() + timedelta(minutes=15), duration_min=45,
        )
        sent = services.send_lesson_reminders()
        self.assertEqual(sent, 2)  # o'qituvchi + o'quvchi
        self.assertTrue(any('15 daqiqadan keyin' in t for t in self.inbox_texts(self.student)))
        self.assertTrue(any(lesson.course.title in t for t in self.inbox_texts(self.teacher)))

    def test_reminder_prefers_lesson_title_over_course_title(self):
        from .models import Lesson
        from . import services

        lesson = Lesson.objects.create(
            course=self.course, title="Present Simple — amaliyot",
            starts_at=timezone.now() + timedelta(minutes=15), duration_min=45,
        )
        services.send_lesson_reminders()
        self.assertTrue(any(lesson.title in t for t in self.inbox_texts(self.teacher)))
        self.assertFalse(any(self.course.title in t for t in self.inbox_texts(self.teacher)))

    def test_not_sent_before_window(self):
        from .models import Lesson
        from . import services

        Lesson.objects.create(
            course=self.course, starts_at=timezone.now() + timedelta(minutes=30), duration_min=45,
        )
        sent = services.send_lesson_reminders()
        self.assertEqual(sent, 0)

    def test_sent_only_once_per_user(self):
        from .models import Lesson
        from . import services

        Lesson.objects.create(
            course=self.course, starts_at=timezone.now() + timedelta(minutes=10), duration_min=45,
        )
        first = services.send_lesson_reminders()
        second = services.send_lesson_reminders()
        self.assertEqual(first, 2)
        self.assertEqual(second, 0)

    def test_respects_per_user_custom_minutes(self):
        """O'quvchi 5 daqiqa, o'qituvchi standart 15 daqiqa — 10 daqiqa
        qolganda faqat o'qituvchiga (15 >= 10) eslatma boradi, o'quvchiga
        (5 < 10) hali emas."""
        from .models import Lesson
        from . import services

        quick_student = self.mk('lr_s2', 'student', reminder_minutes=5)
        from .models import Enrollment
        Enrollment.objects.create(course=self.course, student=quick_student, status=Enrollment.Status.APPROVED)

        Lesson.objects.create(
            course=self.course, starts_at=timezone.now() + timedelta(minutes=10), duration_min=45,
        )
        services.send_lesson_reminders()
        self.assertEqual(self.inbox_texts(self.teacher).__len__(), 1)
        self.assertEqual(self.inbox_texts(quick_student).__len__(), 0)


class CourseSubjectI18nTests(APITestCase):
    """Fanlar ro'yxati tayin (erkin matn emas) va 3 tilda (uz/ru/en) —
    `Accept-Language` sarlavhasiga qarab tarjima qilinadi."""

    def setUp(self):
        register(self.client, 'subj_teacher', 'teacher')
        self.token = login(self.client, 'subj_teacher')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_subjects_list_default_uzbek(self):
        r = self.client.get('/api/v1/courses/subjects/')
        self.assertEqual(r.status_code, 200)
        values = {item['value'] for item in r.json()}
        self.assertEqual(values, {v for v, _ in Course.Subject.choices})
        chemistry = next(item for item in r.json() if item['value'] == 'chemistry')
        self.assertEqual(chemistry['label'], 'Kimyo')
        chess = next(item for item in r.json() if item['value'] == 'chess')
        self.assertEqual(chess['label'], 'Shaxmat')

    def test_all_subject_labels_translated_in_all_3_languages(self):
        """Har bir fan kodi uchun ru/en labeli uz labelidan farqli bo'lishi
        kerak — aks holda tarjima yozilmagan (source matn qaytgan) bo'ladi."""
        uz = {item['value']: item['label'] for item in self.client.get('/api/v1/courses/subjects/').json()}
        for lang in ('ru', 'en'):
            translated = {
                item['value']: item['label']
                for item in self.client.get('/api/v1/courses/subjects/', HTTP_ACCEPT_LANGUAGE=lang).json()
            }
            for value, uz_label in uz.items():
                self.assertNotEqual(
                    translated[value], uz_label,
                    f"'{value}' fani {lang} tiliga tarjima qilinmagan",
                )

    def test_subjects_list_russian(self):
        r = self.client.get('/api/v1/courses/subjects/', HTTP_ACCEPT_LANGUAGE='ru')
        chemistry = next(item for item in r.json() if item['value'] == 'chemistry')
        self.assertEqual(chemistry['label'], 'Химия')

    def test_subjects_list_english(self):
        r = self.client.get('/api/v1/courses/subjects/', HTTP_ACCEPT_LANGUAGE='en')
        chemistry = next(item for item in r.json() if item['value'] == 'chemistry')
        self.assertEqual(chemistry['label'], 'Chemistry')

    def test_course_creation_rejects_free_text_subject(self):
        r = self.client.post('/api/v1/courses/', {'title': 'X', 'subject': 'Ximiya'})
        self.assertEqual(r.status_code, 400)

    def test_course_subject_label_follows_accept_language(self):
        course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Kimyo 9', 'subject': 'chemistry'},
        ).json()['id']
        r = self.client.get(f'/api/v1/courses/{course_id}/', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(r.json()['subject'], 'chemistry')
        self.assertEqual(r.json()['subject_label'], 'Химия')
