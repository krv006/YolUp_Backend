"""Kanallar (2026-11-10): faqat o'qituvchi post yozadi, a'zolar o'qiydi va izoh qoldiradi."""
from apps.accounts.models import ParentChildLink, User
from apps.chat.models import ChatRoom, Message, RoomMember
from apps.chat.tests_contacts import BaseChatRules, make
from apps.lessons.models import Course, Enrollment


class ChannelTests(BaseChatRules):
    def setUp(self):
        super().setUp()
        self.s3 = make('c_s3', User.Role.STUDENT)  # teacher.course ga yozilmagan
        self.course2 = Course.objects.create(teacher=self.teacher, title='B')
        Enrollment.objects.create(course=self.course2, student=self.s3, status=Enrollment.Status.APPROVED)
        self.parent3 = make('c_p3', User.Role.PARENT)
        ParentChildLink.objects.create(parent=self.parent3, student=self.s3, status=ParentChildLink.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.stranger_parent, student=self.classmate, status=ParentChildLink.Status.PENDING)

    def create(self, user=None, **body):
        body = {'title': 'Yangiliklar', 'description': 'Kunlik xabarlar', **body}
        return self.api(user or self.teacher).post('/api/v1/chat/channels/', body, format='json')

    def members(self, room_id):
        return set(RoomMember.objects.filter(room_id=room_id).values_list('user__username', flat=True))

    def test_create_from_a_course_adds_students_and_approved_parents(self):
        r = self.create(course_ids=[str(self.course.id)])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['kind'], 'channel')
        self.assertEqual(r.data['title'], 'Yangiliklar')
        # c_s, c_s2 + c_s ning tasdiqlangan ota-onasi (c_p); kutayotgan ota-ona (c_p2) yo'q
        self.assertEqual(self.members(r.data['id']), {'c_s', 'c_s2', 'c_p'})
        self.assertEqual(r.data['members_count'], 4)  # + egasi
        self.assertTrue(r.data['can_write'])

    def test_create_from_individual_students_only_own_students(self):
        r = self.create(student_ids=[str(self.student.id), str(self.s3.id)])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.members(r.data['id']), {'c_s', 'c_s3', 'c_p', 'c_p3'})
        stranger = make('c_foreign', User.Role.STUDENT)
        self.assertEqual(self.create(student_ids=[str(stranger.id)]).status_code, 403)
        other_course = Course.objects.create(teacher=self.other_teacher, title='X')
        self.assertEqual(self.create(course_ids=[str(other_course.id)]).status_code, 403)

    def test_only_teachers_create_and_title_is_required(self):
        self.assertEqual(self.create(user=self.student).status_code, 403)
        self.assertEqual(self.create(title='  ').status_code, 400)

    def test_only_owner_posts_members_comment_and_comments_stay_out_of_the_feed(self):
        room_id = self.create(course_ids=[str(self.course.id)]).data['id']
        # a'zo (o'quvchi) post yoza olmaydi
        no = self.api(self.student).post(f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'salom'}, format='json')
        self.assertEqual(no.status_code, 403)
        post = self.api(self.teacher).post(f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'Yangi post'}, format='json')
        self.assertEqual(post.status_code, 201, post.content)
        self.assertEqual(post.data['comment_count'], 0)
        # o'quvchi ham, ota-ona ham izoh yoza oladi
        for user in (self.student, self.parent):
            c = self.api(user).post(
                f'/api/v1/chat/rooms/{room_id}/messages/', {'text': f'izoh {user.username}', 'thread_root_id': post.data['id']}, format='json',
            )
            self.assertEqual(c.status_code, 201, c.content)
            self.assertEqual(str(c.data['thread_root']), post.data['id'])
        # asosiy lentada faqat post, comment_count bilan
        feed = self.api(self.student).get(f'/api/v1/chat/rooms/{room_id}/messages/').json()
        self.assertEqual([(m['text'], m['comment_count']) for m in feed], [('Yangi post', 2)])
        # izohlar alohida
        thread = self.api(self.student).get(f'/api/v1/chat/rooms/{room_id}/messages/', {'thread': post.data['id']}).json()
        self.assertEqual([m['text'] for m in thread], ['izoh c_s', 'izoh c_p'])
        self.assertTrue(all(m['comment_count'] is None for m in thread))

    def test_non_members_cannot_read_or_comment(self):
        room_id = self.create(course_ids=[str(self.course.id)]).data['id']
        post = self.api(self.teacher).post(f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'P'}, format='json').data
        for outsider in (self.s3, self.stranger_parent, self.other_teacher):
            self.assertEqual(self.api(outsider).get(f'/api/v1/chat/rooms/{room_id}/messages/').status_code, 404, outsider.username)
            self.assertIn(self.api(outsider).post(
                f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'x', 'thread_root_id': post['id']}, format='json',
            ).status_code, (403, 404))

    def test_comment_must_target_a_real_post_of_a_channel(self):
        room_id = self.create(course_ids=[str(self.course.id)]).data['id']
        bad = self.api(self.student).post(
            f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'x', 'thread_root_id': '00000000-0000-0000-0000-000000000000'}, format='json',
        )
        self.assertEqual(bad.status_code, 404)
        group_msg = Message.objects.create(room=self.course.chat_room, sender=self.teacher, text='g')
        wrong = self.api(self.student).post(
            f'/api/v1/chat/rooms/{self.course.chat_room.id}/messages/', {'text': 'x', 'thread_root_id': str(group_msg.id)}, format='json',
        )
        self.assertEqual(wrong.status_code, 400)  # guruhda izoh yo'q

    def test_channels_are_listed_with_other_chats_and_comments_do_not_count_as_unread(self):
        room_id = self.create(course_ids=[str(self.course.id)]).data['id']
        post = self.api(self.teacher).post(f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'P'}, format='json').data
        self.api(self.classmate).post(
            f'/api/v1/chat/rooms/{room_id}/messages/', {'text': 'izoh', 'thread_root_id': post['id']}, format='json',
        )
        rooms = {r['id']: r for r in self.api(self.student).get('/api/v1/chat/rooms/').json()['results']}
        row = rooms[room_id]
        self.assertEqual((row['kind'], row['title'], row['unread_count']), ('channel', 'Yangiliklar', 1))  # faqat post
        self.assertEqual(row['last_message']['text'], 'P')
        self.assertFalse(row['can_write'])
        self.assertTrue(row['can_comment'])
        # ota-ona ham ro'yxatda ko'radi (faqat kanalni)
        parent_rooms = self.api(self.parent).get('/api/v1/chat/rooms/').json()['results']
        self.assertEqual([r['id'] for r in parent_rooms], [room_id])

    def test_owner_manages_members_update_and_delete(self):
        room_id = self.create(student_ids=[str(self.student.id)]).data['id']
        self.assertEqual(self.members(room_id), {'c_s', 'c_p'})
        added = self.api(self.teacher).post(f'/api/v1/chat/channels/{room_id}/members/', {'student_ids': [str(self.s3.id)]}, format='json')
        self.assertEqual(added.json(), {'added': 2})  # o'quvchi + ota-onasi
        self.assertEqual(self.members(room_id), {'c_s', 'c_p', 'c_s3', 'c_p3'})
        listing = self.api(self.teacher).get(f'/api/v1/chat/channels/{room_id}/members/').json()
        self.assertEqual({m['role'] for m in listing}, {'teacher', 'student', 'parent'})
        # o'quvchi chiqarilsa, farzandi qolmagan ota-ona ham chiqadi
        gone = self.api(self.teacher).delete(f'/api/v1/chat/channels/{room_id}/members/{self.s3.id}/')
        self.assertEqual(gone.status_code, 204)
        self.assertEqual(self.members(room_id), {'c_s', 'c_p'})
        renamed = self.api(self.teacher).patch(f'/api/v1/chat/channels/{room_id}/', {'title': 'Yangi nom'}, format='json')
        self.assertEqual(renamed.json()['title'], 'Yangi nom')
        # boshqa o'qituvchi/o'quvchi boshqara olmaydi
        self.assertEqual(self.api(self.other_teacher).patch(f'/api/v1/chat/channels/{room_id}/', {'title': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.api(self.student).post(f'/api/v1/chat/channels/{room_id}/members/', {'student_ids': []}, format='json').status_code, 403)
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/chat/channels/{room_id}/').status_code, 204)
        self.assertFalse(ChatRoom.objects.filter(pk=room_id).exists())
