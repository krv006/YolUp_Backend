"""Guruh rasmi kursda va chat xonasida bir xil; yozuv tayyor bildirishnomasi."""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.chat.models import ChatRoom
from apps.lessons import services
from apps.lessons.models import Course, Enrollment, Lesson
from apps.notifications.models import NotificationRecipient


def png(name='g.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (30, 30), 'blue').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class GroupImageSyncTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = User.objects.create_user(username='av_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        self.room = chat_services.ensure_course_room(self.course)
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def test_chat_image_shows_up_as_course_avatar(self):
        response = self.client.post(f'/api/v1/chat/rooms/{self.room.id}/image/', {'image': png()}, format='multipart')
        self.assertEqual(response.status_code, 200)
        listing = self.client.get('/api/v1/courses/').json()
        rows = listing['results'] if isinstance(listing, dict) else listing
        self.assertTrue(rows[0]['avatar'])

    def test_course_avatar_shows_up_in_chat_room(self):
        self.course.avatar = png('c.png')
        self.course.save()
        self.room.refresh_from_db()
        self.assertTrue(self.room.image)
        self.assertEqual(self.room.image.name, self.course.avatar.name)

    def test_removing_course_avatar_clears_room_image(self):
        self.course.avatar = png('c.png')
        self.course.save()
        self.course.avatar = None
        self.course.save()
        self.room.refresh_from_db()
        self.assertFalse(self.room.image)

    def test_unrelated_save_does_not_touch_room(self):
        self.course.avatar = png('c.png')
        self.course.save()
        name = ChatRoom.objects.get(pk=self.room.pk).image.name
        self.course.title = 'Yangi nom'
        self.course.save(update_fields=['title'])
        self.assertEqual(ChatRoom.objects.get(pk=self.room.pk).image.name, name)


class RecordingReadyNotificationTests(TestCase):
    def test_enrolled_students_get_a_recording_notification(self):
        teacher = User.objects.create_user(username='rr_t', password='x', role=User.Role.TEACHER, is_approved=True)
        student = User.objects.create_user(username='rr_s', password='x', role=User.Role.STUDENT)
        outsider = User.objects.create_user(username='rr_o', password='x', role=User.Role.STUDENT)
        course = Course.objects.create(teacher=teacher, title='K', subject='math')
        Enrollment.objects.create(course=course, student=student, status=Enrollment.Status.APPROVED)
        lesson = Lesson.objects.create(course=course, title='D', starts_at=timezone.now(), status=Lesson.Status.FINISHED)
        with self.captureOnCommitCallbacks(execute=False):
            services.publish_recording_message(lesson, 'Dars 1')
        note = NotificationRecipient.objects.get(user=student).notification
        self.assertEqual((note.kind, note.link_type, note.link_id), ('recording_ready', 'recording', str(lesson.id)))
        self.assertFalse(NotificationRecipient.objects.filter(user=outsider).exists())
