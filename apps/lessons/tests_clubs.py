"""Speaking club (2026-11-10): o'qituvchi turli guruhlaridan o'quvchilarni qo'shadi, ular darhol a'zo bo'ladi va xabar oladi."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.chat.models import ChatRoom
from apps.lessons.models import Course, Enrollment, Lesson
from apps.notifications.models import NotificationRecipient


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class ClubTests(APITestCase):
    def setUp(self):
        self.teacher = make('cl_t', User.Role.TEACHER)
        self.other_teacher = make('cl_t2', User.Role.TEACHER)
        self.a1, self.a2, self.b1 = (make(n, User.Role.STUDENT) for n in ('cl_a1', 'cl_a2', 'cl_b1'))
        self.group_a = Course.objects.create(teacher=self.teacher, title='A guruh')
        self.group_b = Course.objects.create(teacher=self.teacher, title='B guruh')
        for course, student in ((self.group_a, self.a1), (self.group_a, self.a2), (self.group_b, self.b1)):
            Enrollment.objects.create(course=course, student=student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def create(self, **body):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(self.teacher).post('/api/v1/clubs/', {'title': 'Speaking club', 'subject': 'english', **body}, format='json')

    def test_create_with_students_from_different_groups_adds_them_at_once_and_notifies(self):
        r = self.create(course_ids=[str(self.group_a.id)], student_ids=[str(self.b1.id)])
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual((body['kind'], body['title'], body['members_count']), ('club', 'Speaking club', 3))
        self.assertTrue(body['chat_room_id'])
        members = Enrollment.objects.filter(course_id=body['id'], status='approved').values_list('student__username', flat=True)
        self.assertEqual(set(members), {'cl_a1', 'cl_a2', 'cl_b1'})
        for student in (self.a1, self.a2, self.b1):
            self.assertEqual(NotificationRecipient.objects.filter(user=student, notification__kind='club_added').count(), 1)
        # klubning o'z chati bor, a'zolar ko'radi
        rooms = self.api(self.a1).get('/api/v1/chat/rooms/').json()['results']
        self.assertIn(body['chat_room_id'], [x['id'] for x in rooms])

    def test_clubs_are_separate_from_group_lists(self):
        club = self.create(course_ids=[str(self.group_a.id)]).json()
        groups = self.api(self.teacher).get('/api/v1/courses/').json()
        rows = groups['results'] if isinstance(groups, dict) else groups
        self.assertEqual({r['id'] for r in rows}, {str(self.group_a.id), str(self.group_b.id)})
        as_clubs = self.api(self.teacher).get('/api/v1/courses/', {'kind': 'club'}).json()
        rows = as_clubs['results'] if isinstance(as_clubs, dict) else as_clubs
        self.assertEqual([r['id'] for r in rows], [club['id']])
        self.assertEqual([c['id'] for c in self.api(self.teacher).get('/api/v1/clubs/').json()], [club['id']])
        # a'zo o'quvchi o'z clubini ko'radi; a'zo bo'lmagani — yo'q
        self.assertEqual([c['id'] for c in self.api(self.a1).get('/api/v1/clubs/').json()], [club['id']])
        self.assertEqual(self.api(self.b1).get('/api/v1/clubs/').json(), [])

    def test_rules_only_own_teacher_own_students(self):
        self.assertEqual(self.api(self.a1).post('/api/v1/clubs/', {'title': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.create(title=' ').status_code, 400)
        stranger = make('cl_stranger', User.Role.STUDENT)
        self.assertEqual(self.create(student_ids=[str(stranger.id)]).status_code, 403)
        foreign_group = Course.objects.create(teacher=self.other_teacher, title='X')
        self.assertEqual(self.create(course_ids=[str(foreign_group.id)]).status_code, 403)

    def test_add_remove_members_update_and_delete(self):
        club = self.create(student_ids=[str(self.a1.id)]).json()
        with self.captureOnCommitCallbacks(execute=True):
            added = self.api(self.teacher).post(f'/api/v1/clubs/{club["id"]}/members/', {'course_ids': [str(self.group_a.id)]}, format='json')
        self.assertEqual(added.json(), {'added': 1})  # a1 allaqachon a'zo, faqat a2 yangi
        listing = self.api(self.teacher).get(f'/api/v1/clubs/{club["id"]}/members/').json()
        self.assertEqual({m['username'] for m in listing}, {'cl_a1', 'cl_a2'})
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/clubs/{club["id"]}/members/{self.a2.id}/').status_code, 204)
        self.assertEqual(self.api(self.other_teacher).delete(f'/api/v1/clubs/{club["id"]}/members/{self.a1.id}/').status_code, 403)
        renamed = self.api(self.teacher).patch(f'/api/v1/clubs/{club["id"]}/', {'title': 'IELTS club'}, format='json')
        self.assertEqual(renamed.json()['title'], 'IELTS club')
        self.assertEqual(self.api(self.teacher).delete(f'/api/v1/clubs/{club["id"]}/').status_code, 204)
        self.assertEqual(self.api(self.teacher).get('/api/v1/clubs/').json(), [])

    def test_live_sessions_use_regular_lessons_of_the_club(self):
        club = self.create(student_ids=[str(self.a1.id)]).json()
        starts = (timezone.now() + timedelta(days=1)).isoformat()
        r = self.api(self.teacher).post('/api/v1/lessons/', {'course': club['id'], 'title': 'Speaking 1', 'starts_at': starts, 'duration_min': 60}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(Lesson.objects.filter(course_id=club['id']).exists())
        self.assertTrue(ChatRoom.objects.filter(course_id=club['id'], kind='course').exists())
