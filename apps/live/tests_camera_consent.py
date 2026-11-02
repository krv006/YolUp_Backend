"""Ota-ona kamerani o'chirgan bo'lsa (Consent camera=false): o'quvchi kamera so'ray olmaydi, o'qituvchi ham ocha olmaydi (13-band)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.consent import ConsentRequired
from apps.accounts.models import Consent, ParentChildLink, User
from apps.lessons.models import CameraRequest, Course, Enrollment, Lesson
from apps.live import services


def make(username, role):
    user = User(username=username, role=role)
    user.set_password('StrongPass123!')
    user.save()
    return user


class CameraConsentTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.parent = make('p1', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='English')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() - timedelta(minutes=5), duration_min=60, status=Lesson.Status.LIVE,
        )

    def deny(self):
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.CAMERA, granted=False)

    def test_denied_camera_blocks_the_students_request(self):
        self.deny()
        with self.assertRaises(ConsentRequired) as ctx:
            services.request_camera(user=self.student, lesson_id=self.lesson.id)
        self.assertEqual(ctx.exception.default_code, 'consent_required')
        self.assertEqual(ctx.exception.detail['kind'], 'camera')
        self.assertFalse(CameraRequest.objects.filter(lesson=self.lesson, student=self.student).exists())

    def test_denied_camera_blocks_the_teacher_grant_before_livekit_is_touched(self):
        self.deny()
        with self.assertRaises(ConsentRequired):
            services.grant_camera(teacher=self.teacher, lesson_id=self.lesson.id, student_id=self.student.id)

    def test_allowed_or_unset_consent_does_not_block_the_request(self):
        services.request_camera(user=self.student, lesson_id=self.lesson.id)  # rozilik yozuvi yo'q: ruxsat
        self.assertTrue(CameraRequest.objects.filter(lesson=self.lesson, student=self.student).exists())
        CameraRequest.objects.all().delete()
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.CAMERA, granted=True)
        services.request_camera(user=self.student, lesson_id=self.lesson.id)
        self.assertTrue(CameraRequest.objects.filter(lesson=self.lesson, student=self.student).exists())

    def test_other_consent_kinds_do_not_affect_the_camera(self):
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.RECORDING, granted=False)
        services.request_camera(user=self.student, lesson_id=self.lesson.id)
        self.assertTrue(CameraRequest.objects.filter(lesson=self.lesson, student=self.student).exists())
