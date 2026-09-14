"""Demo ma'lumot: o'qituvchi + ota-ona + bola + kurs + dars.

    python manage.py seed_demo
Parollar: Demo1234!
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.lessons import services as lesson_services

PASSWORD = 'Demo1234!'


class Command(BaseCommand):
    help = 'Demo foydalanuvchilar va dars yaratadi (idempotent emas — bir marta ishlating).'

    def handle(self, *args, **options):
        if User.objects.filter(username='demo_teacher').exists():
            self.stdout.write(self.style.WARNING('Demo ma\'lumot allaqachon mavjud.'))
            return

        teacher = account_services.register_user(
            username='demo_teacher', password=PASSWORD, role=User.Role.TEACHER,
            first_name='Malika', last_name='Karimova', phone='+998900000001',
        )
        parent = account_services.register_user(
            username='demo_parent', password=PASSWORD, role=User.Role.PARENT,
            first_name='Aziz', last_name='Aliyev', phone='+998900000002',
        )
        child = account_services.create_child(
            creator=parent, username='demo_child', password=PASSWORD, first_name='Sardor',
        )
        course = lesson_services.create_course(
            teacher=teacher, title='Algebra · 7-sinf', subject='math',
            description='Kvadrat tenglamalar moduli',
        )
        lesson_services.enroll(course_id=course.id, by_user=parent, student_id=child.id)
        lesson = lesson_services.schedule_lesson(
            teacher=teacher, course=course, title='Kvadrat tenglamalar — 1-dars',
            starts_at=timezone.now() + timezone.timedelta(hours=1), duration_min=45,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Demo tayyor:\n'
            f'  o\'qituvchi: demo_teacher / {PASSWORD}\n'
            f'  ota-ona:    demo_parent / {PASSWORD}\n'
            f'  o\'quvchi:   demo_child / {PASSWORD} (taklif kodi: {child.invite_code})\n'
            f'  dars xonasi: {lesson.room_name}'
        ))
