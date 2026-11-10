"""Chat ruxsatlari (3), qidiruv (4), spam/shikoyat (5) va rollar yorlig'i (6) — 2026-11-10 qoidalari."""
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.chat import services
from apps.chat.models import ChatRoom, Message, SpamReport
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient


def make(username, role, **extra):
    user = User(username=username, role=role, is_approved=True, **extra)
    user.set_password('x')
    user.save()
    return user


class BaseChatRules(APITestCase):
    def setUp(self):
        self.teacher = make('c_t', User.Role.TEACHER, first_name='Ustoz')
        self.other_teacher = make('c_t2', User.Role.TEACHER, first_name='Boshqa')
        self.student = make('c_s', User.Role.STUDENT, first_name='Aziz', phone='+998901112233')
        self.classmate = make('c_s2', User.Role.STUDENT, first_name='Aziza')
        self.parent = make('c_p', User.Role.PARENT, first_name='Ota')
        self.stranger_parent = make('c_p2', User.Role.PARENT, first_name='Begona')
        self.admin = make('c_admin', User.Role.ADMIN)
        self.course = Course.objects.create(teacher=self.teacher, title='A')
        services.ensure_course_room(self.course)
        for s in (self.student, self.classmate):
            Enrollment.objects.create(course=self.course, student=s, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client


class DirectRulesTests(BaseChatRules):
    def test_teacher_opens_chat_with_own_student_without_request(self):
        r = self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(self.student.id)}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['direct_status'], 'active')
        self.assertTrue(r.data['can_write'])
        # qayta chaqirilsa shu xonaning o'zi
        again = self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(self.student.id)}, format='json')
        self.assertEqual(again.data['id'], r.data['id'])

    def test_teacher_opens_chat_with_approved_parent_of_own_student(self):
        r = self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(self.parent.id)}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['direct_status'], 'active')
        # ota-ona o'z ro'yxatida uni ko'radi va yoza oladi
        rooms = self.api(self.parent).get('/api/v1/chat/rooms/').json()['results']
        self.assertEqual([x['id'] for x in rooms], [r.data['id']])
        self.assertTrue(rooms[0]['can_write'])
        self.assertEqual(rooms[0]['other_user']['role'], 'teacher')
        sent = self.api(self.parent).post(f'/api/v1/chat/rooms/{r.data["id"]}/messages/', {'text': 'Salom'}, format='json')
        self.assertEqual(sent.status_code, 201, sent.content)

    def test_teacher_cannot_open_chat_with_strangers(self):
        for other in (self.stranger_parent, self.other_teacher, self.admin):
            r = self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(other.id)}, format='json')
            self.assertEqual(r.status_code, 403, other.username)
        outsider = make('c_out', User.Role.STUDENT)  # guruhda emas
        self.assertEqual(
            self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(outsider.id)}, format='json').status_code, 403,
        )

    def test_student_request_goes_pending_and_teacher_accepts(self):
        r = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': str(self.other_teacher.id)}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['direct_status'], 'pending')
        self.assertFalse(r.data['can_write'])
        ok = self.api(self.other_teacher).post(
            '/api/v1/chat/rooms/direct/respond/', {'room_id': r.data['id'], 'action': 'accept'}, format='json',
        )
        self.assertEqual(ok.data['direct_status'], 'active')

    def test_parent_requests_only_childs_teachers(self):
        ok = self.api(self.parent).post('/api/v1/chat/rooms/direct/request/', {'teacher': str(self.teacher.id)}, format='json')
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.data['direct_status'], 'pending')
        no = self.api(self.parent).post('/api/v1/chat/rooms/direct/request/', {'teacher': str(self.other_teacher.id)}, format='json')
        self.assertEqual(no.status_code, 403)
        teachers = self.api(self.parent).get('/api/v1/chat/rooms/teachers/').json()
        self.assertEqual([t['username'] for t in teachers], ['c_t'])

    def test_student_cannot_write_to_student_or_parent(self):
        # so'rov faqat o'qituvchiga mavjud
        r = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': 'c_s2'}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_group_chats_stay_closed_to_parents(self):
        room = self.course.chat_room
        self.assertEqual(self.api(self.parent).get(f'/api/v1/chat/rooms/{room.id}/messages/').status_code, 404)  # ota-onaga ko'rinmaydi


class PeopleSearchRulesTests(BaseChatRules):
    def search(self, user, q):
        r = self.api(user).get('/api/v1/auth/users/search/', {'q': q})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_student_finds_teachers_students_and_parents_with_can_message(self):
        by_name = {row['username']: row for row in self.search(self.student, 'c_')}
        self.assertEqual(by_name['c_t']['can_message'], 'request')
        self.assertEqual(by_name['c_t2']['can_message'], 'request')  # begona o'qituvchi ham
        self.assertEqual(by_name['c_s2']['can_message'], 'none')
        self.assertEqual(by_name['c_p']['can_message'], 'none')
        self.assertNotIn('c_admin', by_name)
        self.assertNotIn('c_s', by_name)  # o'zi chiqmaydi
        self.assertEqual({row['role'] for row in by_name.values()}, {'teacher', 'student', 'parent'})

    def test_strangers_expose_only_name_username_avatar_role(self):
        row = next(r for r in self.search(self.classmate, 'Aziz') if r['username'] == 'c_s')
        self.assertEqual(set(row), {'id', 'name', 'username', 'role', 'avatar', 'room_id', 'direct_status', 'can_message'})
        self.assertNotIn('phone', row)
        # telefon bo'yicha begona topilmaydi
        self.assertEqual(self.search(self.classmate, '901112233'), [])

    def test_room_id_and_status_follow_the_room(self):
        room = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.student, direct_status=ChatRoom.DirectStatus.ACTIVE,
        )
        row = next(r for r in self.search(self.student, 'c_t') if r['username'] == 'c_t')
        self.assertEqual((row['room_id'], row['direct_status'], row['can_message']), (str(room.id), 'active', 'write'))
        ChatRoom.objects.filter(pk=room.pk).update(direct_status=ChatRoom.DirectStatus.PENDING)
        row = next(r for r in self.search(self.student, 'c_t') if r['username'] == 'c_t')
        self.assertEqual((row['direct_status'], row['can_message']), ('pending', 'request'))

    def test_teacher_sees_own_people_with_write_and_parent_rows_with_room(self):
        room = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.parent, direct_status=ChatRoom.DirectStatus.ACTIVE,
        )
        rows = {r['username']: r for r in self.search(self.teacher, 'c_')}
        self.assertEqual(set(rows), {'c_s', 'c_s2', 'c_p'})  # begona ota-ona va o'qituvchilar ko'rinmaydi
        self.assertEqual(rows['c_s']['can_message'], 'write')
        self.assertEqual(rows['c_p']['room_id'], str(room.id))  # ota-onada ham room_id

    def test_parent_search_is_limited_to_childs_teachers(self):
        rows = self.search(self.parent, 'c_')
        self.assertEqual([r['username'] for r in rows], ['c_t'])
        self.assertEqual(rows[0]['can_message'], 'request')

    def test_global_search_people_carries_the_same_fields(self):
        r = self.api(self.student).get('/api/v1/search/', {'q': 'c_t', 'type': 'people'}).json()
        row = next(x for x in r['results'] if x['id'] == str(self.teacher.id))
        self.assertEqual((row['role'], row['can_message'], row['direct_status']), ('teacher', 'request', None))


class SpamReportTests(BaseChatRules):
    def setUp(self):
        super().setUp()
        self.room = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.student, direct_status=ChatRoom.DirectStatus.ACTIVE,
        )
        Message.objects.create(room=self.room, sender=self.student, text='reklama reklama')

    def report(self, user, **body):
        body = {'reason': 'advertising', 'comment': 'reklama yuboryapti', **body}
        return self.api(user).post(f'/api/v1/chat/rooms/{self.room.id}/report/', body, format='json')

    def test_any_side_can_report_and_chat_is_blocked_at_once(self):
        r = self.report(self.teacher)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.data['reporter']['username'], r.data['reported']['username']), ('c_t', 'c_s'))
        self.room.refresh_from_db()
        self.assertEqual(self.room.direct_status, 'spam')
        # belgilangan odam yoza olmaydi, qayta so'rov ham yubora olmaydi
        sent = self.api(self.student).post(f'/api/v1/chat/rooms/{self.room.id}/messages/', {'text': 'hoy'}, format='json')
        self.assertEqual(sent.status_code, 403)
        again = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': str(self.teacher.id)}, format='json')
        self.assertEqual(again.status_code, 403)
        # o'qituvchi ham accept/open orqali ocha olmaydi
        self.assertEqual(self.api(self.teacher).post(
            '/api/v1/chat/rooms/direct/respond/', {'room_id': str(self.room.id), 'action': 'accept'}, format='json').status_code, 403)
        self.assertEqual(self.api(self.teacher).post(
            '/api/v1/chat/rooms/direct/open/', {'user_id': str(self.student.id)}, format='json').status_code, 403)

    def test_student_and_parent_can_report_too(self):
        self.assertEqual(self.report(self.student, reason='insult').status_code, 201)
        parent_room = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.parent, direct_status=ChatRoom.DirectStatus.ACTIVE,
        )
        r = self.api(self.parent).post(f'/api/v1/chat/rooms/{parent_room.id}/report/', {'reason': 'other'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)

    def test_validation_and_access(self):
        self.assertEqual(self.report(self.teacher, reason='zzz').status_code, 400)
        self.assertEqual(self.report(self.classmate).status_code, 403)  # xona a'zosi emas
        group = self.api(self.teacher).post(f'/api/v1/chat/rooms/{self.course.chat_room.id}/report/', {'reason': 'other'}, format='json')
        self.assertEqual(group.status_code, 400)  # guruhni emas, faqat shaxsiy suhbatni

    def test_double_report_is_idempotent_and_admins_are_notified(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.report(self.teacher).data['id']
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.report(self.teacher).data['id'], first)
        self.assertEqual(SpamReport.objects.count(), 1)
        self.assertEqual(NotificationRecipient.objects.filter(user=self.admin, notification__kind='spam_report').count(), 1)

    def test_admin_list_resolve_dismiss_unblock(self):
        rid = self.report(self.teacher).data['id']
        self.assertEqual(self.api(self.teacher).get('/api/v1/admin/reports/').status_code, 403)
        listing = self.api(self.admin).get('/api/v1/admin/reports/', {'status': 'open'}).json()
        self.assertEqual([x['id'] for x in listing['results']], [rid])
        detail = self.api(self.admin).get(f'/api/v1/admin/reports/{rid}/').json()
        self.assertEqual(detail['recent_messages'][0]['text'], 'reklama reklama')
        # tasdiqlash: chat bloklangan qoladi
        self.assertEqual(self.api(self.admin).post(f'/api/v1/admin/reports/{rid}/resolve/').json()['status'], 'resolved')
        self.room.refresh_from_db()
        self.assertEqual(self.room.direct_status, 'spam')
        # admin chatni qayta ochadi
        unblocked = self.api(self.admin).post(f'/api/v1/admin/reports/{rid}/unblock/').json()
        self.assertEqual(unblocked['room_status'], 'active')
        self.room.refresh_from_db()
        self.assertEqual(self.room.direct_status, 'active')
        sent = self.api(self.student).post(f'/api/v1/chat/rooms/{self.room.id}/messages/', {'text': 'kechiring'}, format='json')
        self.assertEqual(sent.status_code, 201)

    def test_dismiss_restores_the_previous_status(self):
        ChatRoom.objects.filter(pk=self.room.pk).update(direct_status=ChatRoom.DirectStatus.PENDING)
        rid = self.report(self.student).data['id']
        body = self.api(self.admin).post(f'/api/v1/admin/reports/{rid}/dismiss/').json()
        self.assertEqual((body['status'], body['room_status']), ('dismissed', 'pending'))


class RoleLabelTests(BaseChatRules):
    def test_role_is_present_on_sender_last_message_members_and_other_user(self):
        room = self.course.chat_room
        services.send_message(user=self.student, room_id=room.id, text='Salom')
        rooms = self.api(self.teacher).get('/api/v1/chat/rooms/').json()['results']
        self.assertEqual(rooms[0]['last_message']['sender_role'], 'student')
        messages = self.api(self.teacher).get(f'/api/v1/chat/rooms/{room.id}/messages/').json()
        rows = messages['results'] if isinstance(messages, dict) else messages
        self.assertEqual(rows[-1]['sender']['role'], 'student')
        members = self.api(self.teacher).get(f'/api/v1/chat/rooms/{room.id}/members/').json()
        self.assertEqual({m['role'] for m in members}, {'teacher', 'student'})
        direct = self.api(self.teacher).post('/api/v1/chat/rooms/direct/open/', {'user_id': str(self.parent.id)}, format='json').json()
        self.assertEqual(direct['other_user']['role'], 'parent')
