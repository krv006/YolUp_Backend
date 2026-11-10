"""Kanallar (2026-11-10): faqat o'qituvchi post yozadi, a'zolar o'qiydi va izoh qoldiradi."""
from apps.accounts.models import ParentChildLink, User
from apps.chat import services
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


class ChannelAutoMembershipTests(BaseChatRules):
    """2026-11-10: guruhga keyin qo'shilgan o'quvchi kanalga avtomatik a'zo; guruhdan chiqqani chiqadi (alohida tanlanmagan bo'lsa)."""

    def setUp(self):
        super().setUp()
        self.newbie = make('c_new', User.Role.STUDENT)
        self.newbie_parent = make('c_newp', User.Role.PARENT)
        ParentChildLink.objects.create(parent=self.newbie_parent, student=self.newbie, status=ParentChildLink.Status.APPROVED)
        self.channel = self.api(self.teacher).post(
            '/api/v1/chat/channels/', {'title': 'K', 'course_ids': [str(self.course.id)], 'student_ids': [str(self.student.id)]}, format='json',
        ).json()

    def members(self):
        return set(RoomMember.objects.filter(room_id=self.channel['id']).values_list('user__username', flat=True))

    def test_channel_reports_its_linked_courses(self):
        self.assertEqual(self.channel['course_ids'], [str(self.course.id)])
        self.assertEqual(self.channel['courses'], [{'id': str(self.course.id), 'title': 'A'}])
        room = next(r for r in self.api(self.teacher).get('/api/v1/chat/rooms/').json()['results'] if r['id'] == self.channel['id'])
        self.assertEqual(room['courses'][0]['title'], 'A')
        group = next(r for r in self.api(self.teacher).get('/api/v1/chat/rooms/').json()['results'] if r['kind'] == 'course')
        self.assertIsNone(group['course_ids'])

    def test_a_student_who_joins_the_group_later_is_added_with_his_parents(self):
        Enrollment.objects.create(course=self.course, student=self.newbie, status=Enrollment.Status.PENDING)
        self.assertNotIn('c_new', self.members())  # hali tasdiqlanmagan
        Enrollment.objects.filter(student=self.newbie).first().save()  # no-op
        enrollment = Enrollment.objects.get(student=self.newbie)
        enrollment.status = Enrollment.Status.APPROVED
        enrollment.save()
        self.assertTrue({'c_new', 'c_newp'} <= self.members())
        # kanalda o'qiy oladi
        self.assertEqual(self.api(self.newbie).get(f'/api/v1/chat/rooms/{self.channel["id"]}/messages/').status_code, 200)

    def test_approved_on_creation_path_also_adds(self):
        Enrollment.objects.create(course=self.course, student=self.newbie, status=Enrollment.Status.APPROVED)
        self.assertTrue({'c_new', 'c_newp'} <= self.members())

    def test_leaving_the_group_removes_course_members_but_keeps_hand_picked_ones(self):
        Enrollment.objects.create(course=self.course, student=self.newbie, status=Enrollment.Status.APPROVED)
        Enrollment.objects.filter(student=self.newbie).delete()
        self.assertFalse({'c_new', 'c_newp'} & self.members())
        # c_s alohida tanlangan (student_ids): guruhdan chiqsa ham qoladi, ota-onasi ham
        Enrollment.objects.filter(student=self.student).delete()
        self.assertTrue({'c_s', 'c_p'} <= self.members())
        # c_s2 faqat guruh orqali edi
        Enrollment.objects.filter(student=self.classmate).delete()
        self.assertNotIn('c_s2', self.members())

    def test_student_in_another_linked_group_stays(self):
        other = Course.objects.create(teacher=self.teacher, title='B')
        self.api(self.teacher).post(f'/api/v1/chat/channels/{self.channel["id"]}/members/', {'course_ids': [str(other.id)]}, format='json')
        Enrollment.objects.create(course=other, student=self.classmate, status=Enrollment.Status.APPROVED)
        Enrollment.objects.filter(course=self.course, student=self.classmate).delete()
        self.assertIn('c_s2', self.members())  # boshqa bog'langan guruhda hamon bor

    def test_parent_approved_later_joins_and_removed_parent_link_leaves(self):
        late_parent = make('c_late', User.Role.PARENT)
        link = ParentChildLink.objects.create(parent=late_parent, student=self.classmate, status=ParentChildLink.Status.PENDING)
        self.assertNotIn('c_late', self.members())
        link.status = ParentChildLink.Status.APPROVED
        link.save()
        self.assertIn('c_late', self.members())
        link.delete()
        self.assertNotIn('c_late', self.members())

    def test_unlinking_a_course_removes_only_its_members(self):
        r = self.api(self.teacher).delete(f'/api/v1/chat/channels/{self.channel["id"]}/courses/{self.course.id}/')
        self.assertEqual((r.status_code, r.json()), (200, {'removed': 1}))  # c_s2; c_s (alohida) va ota-onasi qoladi
        self.assertEqual(self.members(), {'c_s', 'c_p'})
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/chat/channels/{self.channel["id"]}/courses/{self.course.id}/').status_code, 404)
        self.assertEqual(self.api(self.student).delete(f'/api/v1/chat/channels/{self.channel["id"]}/courses/{self.course.id}/').status_code, 403)


class CourseKindOnRoomTests(BaseChatRules):
    def test_course_rooms_carry_the_group_or_club_kind(self):
        club = Course.objects.create(teacher=self.teacher, title='Club', kind=Course.Kind.CLUB)
        services.ensure_course_room(club)
        Enrollment.objects.create(course=club, student=self.student, status=Enrollment.Status.APPROVED)
        rooms = self.api(self.student).get('/api/v1/chat/rooms/').json()['results']
        kinds = {r['title']: r['course_kind'] for r in rooms}
        self.assertEqual(kinds, {'A': 'group', 'Club': 'club'})
        one = self.api(self.student).get(f'/api/v1/chat/rooms/{club.chat_room.id}/').json()
        self.assertEqual(one['course_kind'], 'club')


class ChannelImageTests(BaseChatRules):
    def make_image(self):
        from apps.chat.tests import make_image

        return make_image()

    def channel(self):
        r = self.api(self.teacher).post('/api/v1/chat/channels/', {'title': 'Rasmli', 'course_ids': [str(self.course.id)]}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        return r.data['id']

    def test_owner_sets_and_removes_the_channel_image(self):
        cid = self.channel()
        r = self.api(self.teacher).post(f'/api/v1/chat/channels/{cid}/image/', {'image': self.make_image()}, format='multipart')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('/media/group_images/', r.data['image'])
        listed = self.api(self.student).get(f'/api/v1/chat/rooms/{cid}/')
        self.assertIn('/media/group_images/', listed.data['image'])  # a'zolar ham ko'radi
        gone = self.api(self.teacher).delete(f'/api/v1/chat/channels/{cid}/image/')
        self.assertEqual(gone.status_code, 200, gone.content)
        self.assertFalse(gone.data['image'])

    def test_the_generic_rooms_endpoint_works_for_channels_too(self):
        cid = self.channel()
        r = self.api(self.teacher).post(f'/api/v1/chat/rooms/{cid}/image/', {'image': self.make_image()}, format='multipart')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('/media/group_images/', r.data['image'])

    def test_members_and_other_teachers_cannot_change_it(self):
        cid = self.channel()
        for user in (self.student, make('c_t_other', User.Role.TEACHER)):
            r = self.api(user).post(f'/api/v1/chat/channels/{cid}/image/', {'image': self.make_image()}, format='multipart')
            self.assertIn(r.status_code, (403, 404))

    def test_an_image_file_is_required(self):
        cid = self.channel()
        r = self.api(self.teacher).post(f'/api/v1/chat/channels/{cid}/image/', {}, format='multipart')
        self.assertEqual(r.status_code, 400)
