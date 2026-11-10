"""`target_type: "course"` — o'qituvchi guruhning barcha o'quvchilariga (+ ixtiyoriy ota-onalariga) xabar yuboradi."""
from rest_framework.test import APITestCase

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import Notification, NotificationRecipient


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class CourseTargetTests(APITestCase):
    def setUp(self):
        self.teacher = make('ct_t', User.Role.TEACHER)
        self.other_teacher = make('ct_t2', User.Role.TEACHER)
        self.course = Course.objects.create(teacher=self.teacher, title='A')
        self.other_course = Course.objects.create(teacher=self.other_teacher, title='B')
        self.s1, self.s2, self.s3 = (make(f'ct_s{i}', User.Role.STUDENT) for i in range(3))
        self.parent = make('ct_p', User.Role.PARENT)
        self.pending_parent = make('ct_pp', User.Role.PARENT)
        Enrollment.objects.create(course=self.course, student=self.s1, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.s2, status=Enrollment.Status.APPROVED)
        Enrollment.objects.create(course=self.course, student=self.s3, status=Enrollment.Status.PENDING)
        ParentChildLink.objects.create(parent=self.parent, student=self.s1, status=ParentChildLink.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.pending_parent, student=self.s2, status=ParentChildLink.Status.PENDING)

    def send(self, user, **body):
        self.client.force_authenticate(user)
        return self.client.post('/api/v1/notifications/send/', {'description': 'Eslatma', 'target_type': 'course', **body}, format='json')

    def recipients(self, response):
        return set(NotificationRecipient.objects.filter(notification_id=response.json()['id']).values_list('user__username', flat=True))

    def test_teacher_reaches_all_approved_students_of_the_course(self):
        response = self.send(self.teacher, course_id=str(self.course.id))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.recipients(response), {'ct_s0', 'ct_s1'})  # kutayotgan (s3) va ota-onalar yo'q
        self.assertEqual(Notification.objects.get(pk=response.json()['id']).target_type, 'course')

    def test_include_parents_adds_only_approved_parents(self):
        response = self.send(self.teacher, course_id=str(self.course.id), include_parents=True)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.recipients(response), {'ct_s0', 'ct_s1', 'ct_p'})

    def test_teacher_cannot_send_to_someone_elses_course(self):
        self.assertEqual(self.send(self.teacher, course_id=str(self.other_course.id)).status_code, 403)

    def test_course_id_is_required_for_teacher_and_unknown_course_is_404_for_admin(self):
        self.assertEqual(self.send(self.teacher).status_code, 403)
        admin = make('ct_admin', User.Role.ADMIN)
        self.assertEqual(self.send(admin, course_id='00000000-0000-0000-0000-000000000000').status_code, 404)
        self.assertEqual(self.send(admin, course_id=str(self.course.id)).status_code, 201)
