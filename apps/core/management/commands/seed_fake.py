"""To'liq fake ma'lumot — demo/sinov uchun.

    python manage.py seed_fake

Hisoblar (parol hammasiga: 1):
  teacher  — O'qituvchi (Malika Karimova)
  data     — O'qituvchi (Informatika · Python kursi)
  perents  — Ota-ona (Aziz Aliyev)
  student  — O'quvchi (Sardor, perents'ga bog'langan)
  + qo'shimcha o'quvchilar: nilufar, dilnoza, madina, jasur
  + data o'qituvchining o'quvchilari: Xusinboy, Kamron, Jaloliddin, Yokub

Qayta ishga tushirsa eski fake ma'lumotni o'chirib, yangidan yaratadi (idempotent).
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Consent, ParentChildLink, User
from apps.chat import services as chat_services
from apps.chat.models import ChatRoom, Message
from apps.lessons.models import Attendance, AttentionCheck, Course, Enrollment, FocusEvent, Lesson

PASSWORD = '1'
USERNAMES = [
    'teacher', 'perents', 'student', 'nilufar', 'dilnoza', 'madina', 'jasur',
    'data', 'Xusinboy', 'Kamron', 'Jaloliddin', 'Yokub',
]


def make_user(username, role, first_name='', last_name='', phone=None):
    user = User(username=username, role=role, first_name=first_name, last_name=last_name, phone=phone)
    user.set_password(PASSWORD)  # to'g'ridan-to'g'ri saqlash — parol validatsiyasi API'da, bu yerda emas
    user.save()
    return user


class Command(BaseCommand):
    help = "Fake foydalanuvchilar va to'liq demo ma'lumot yaratadi (teacher/perents/student, parol: 1)."

    def handle(self, *args, **options):
        # eski fake/demo ma'lumotni tozalash
        User.objects.filter(username__in=USERNAMES).delete()
        User.objects.filter(username__startswith='demo_').delete()
        Course.all_objects.filter(teacher__isnull=True).delete()

        now = timezone.now()

        # ── foydalanuvchilar ──
        teacher = make_user('teacher', User.Role.TEACHER, 'Malika', 'Karimova', '+998901234567')
        parent = make_user('perents', User.Role.PARENT, 'Aziz', 'Aliyev', '+998907654321')
        student = make_user('student', User.Role.STUDENT, 'Sardor', 'Aliyev')
        others = [
            make_user('nilufar', User.Role.STUDENT, 'Nilufar', 'Rahimova'),
            make_user('dilnoza', User.Role.STUDENT, 'Dilnoza', 'Karimova'),
            make_user('madina', User.Role.STUDENT, 'Madina', 'Tosheva'),
            make_user('jasur', User.Role.STUDENT, 'Jasur', 'Bekov'),
        ]

        # ── ota-ona ↔ bola (tasdiqlangan — rozilik oqimi o'tilgan) ──
        ParentChildLink.objects.create(
            parent=parent, student=student,
            status=ParentChildLink.Status.APPROVED, responded_at=now,
        )
        for kind in (Consent.Kind.ANALYTICS, Consent.Kind.RECORDING):
            Consent.objects.create(student=student, granted_by=parent, kind=kind, granted=True)

        # ── kurslar ──
        algebra = Course.objects.create(
            teacher=teacher, title='Algebra · 7-sinf', subject=Course.Subject.MATH,
            description='Kvadrat tenglamalar, funksiyalar va grafiklar',
        )
        english = Course.objects.create(
            teacher=teacher, title="Ingliz tili · Boshlang'ich", subject=Course.Subject.ENGLISH,
            description='Grammatika va so\'zlashuv asoslari',
        )

        all_students = [student] + others
        for s in all_students:
            Enrollment.objects.create(course=algebra, student=s)
        for s in all_students[:3]:
            Enrollment.objects.create(course=english, student=s)

        # ── o'tgan hafta darslari (tugagan, davomat bilan) ──
        topics = [
            'Kvadrat tenglamalar — kirish',
            'Diskriminant va ildizlar',
            'Vieta teoremasi',
            'Funksiya grafigi',
            'Takrorlash va test',
        ]
        for i, topic in enumerate(topics):
            starts = now - timedelta(days=len(topics) - i, hours=2)
            lesson = Lesson.objects.create(
                course=algebra, title=topic, starts_at=starts,
                duration_min=45, status=Lesson.Status.FINISHED,
            )
            for j, s in enumerate(all_students):
                if s.username == 'jasur' and i % 2 == 0:
                    continue  # Jasur ba'zi darslarni qoldirgan — hisobotda ko'rinsin
                joined = starts + timedelta(minutes=2 + j)
                left = starts + timedelta(minutes=40 + (j % 5))
                Attendance.objects.create(lesson=lesson, student=s, joined_at=joined, left_at=left)
                # Diqqat tekshiruvi tarixi: Sardor hammasiga javob bergan,
                # Jasur yarmini o'tkazib yuborgan — hisobotda farq ko'rinsin
                for k in range(random.randint(3, 5)):
                    due = joined + timedelta(minutes=5 + k * 8)
                    missed = s.username == 'jasur' and k % 2 == 0
                    AttentionCheck.objects.create(
                        lesson=lesson, student=s, due_at=due,
                        answered_at=None if missed else due + timedelta(seconds=random.randint(2, 12)),
                    )
            # Jasur dars oynasidan chiqib-kirib yurgan (anti-cheat jurnali)
            jasur = next(s for s in all_students if s.username == 'jasur')
            for k in range(3):
                FocusEvent.objects.create(lesson=lesson, student=jasur, kind=FocusEvent.Kind.EXIT)
                FocusEvent.objects.create(lesson=lesson, student=jasur, kind=FocusEvent.Kind.RETURN)

        # ── hozir jonli dars ──
        live = Lesson.objects.create(
            course=algebra, title='Kvadrat tenglamalar — amaliyot',
            starts_at=now - timedelta(minutes=15), duration_min=45, status=Lesson.Status.LIVE,
        )
        Attendance.objects.create(
            lesson=live, student=student, joined_at=now - timedelta(minutes=12),
        )

        # ── ikkinchi o'qituvchi: data — o'z kursi va o'quvchilari bilan ──
        data_teacher = make_user('data', User.Role.TEACHER, 'Data', "O'qituvchi")
        data_students = [
            make_user('Xusinboy', User.Role.STUDENT, 'Xusinboy', ''),
            make_user('Kamron', User.Role.STUDENT, 'Kamron', ''),
            make_user('Jaloliddin', User.Role.STUDENT, 'Jaloliddin', ''),
            make_user('Yokub', User.Role.STUDENT, 'Yokub', ''),
        ]
        informatika = Course.objects.create(
            teacher=data_teacher, title='Informatika · Python', subject=Course.Subject.COMPUTER_SCIENCE,
            description="Python asoslari — o'zgaruvchilar, sikllar, funksiyalar",
        )
        for s in data_students:
            Enrollment.objects.create(course=informatika, student=s)

        # o'tgan darslar (davomat bilan) va kelgusi dars
        for i, topic in enumerate(['Python — kirish', "O'zgaruvchilar va turlar"]):
            starts = now - timedelta(days=2 - i, hours=1)
            lesson = Lesson.objects.create(
                course=informatika, title=topic, starts_at=starts,
                duration_min=45, status=Lesson.Status.FINISHED,
            )
            for j, s in enumerate(data_students):
                Attendance.objects.create(
                    lesson=lesson, student=s,
                    joined_at=starts + timedelta(minutes=1 + j),
                    left_at=starts + timedelta(minutes=42),
                )
        Lesson.objects.create(
            course=informatika, title='Shart operatorlari (if/else)',
            starts_at=now + timedelta(days=1, hours=2), duration_min=45,
        )

        # ── kelgusi darslar ──
        for days, (course, topic) in enumerate([
            (algebra, "Chiziqli tenglamalar tizimi"),
            (english, 'Present Simple — amaliyot'),
            (algebra, 'Nazorat ishi'),
        ], start=1):
            Lesson.objects.create(
                course=course, title=topic,
                starts_at=now + timedelta(days=days, hours=3), duration_min=45,
            )

        # ── chat: guruhlar + direct (Telegram uslubi) ──
        for course in (algebra, english, informatika):
            chat_services.ensure_course_room(course)
        algebra_room = algebra.chat_room
        for sender, text in [
            (teacher, "Assalomu alaykum! Ertaga nazorat ishi bo'ladi, tayyorlaning 📚"),
            (student, 'Vaalaykum assalom, qaysi mavzulardan?'),
            (teacher, "Kvadrat tenglamalar va Vieta teoremasi. Doska PDF'larini ko'rib chiqing."),
            (others[0], 'Rahmat, tushunarli!'),
        ]:
            Message.objects.create(room=algebra_room, sender=sender, text=text)
        info_room = informatika.chat_room
        for sender, text in [
            (data_teacher, "Salom! Keyingi darsda if/else mavzusini o'tamiz 🐍"),
            (data_students[0], 'Zo\'r, kutamiz!'),
        ]:
            Message.objects.create(room=info_room, sender=sender, text=text)
        # direct: Sardor <-> Malika (ochiq), Nilufar so'rovi kutilmoqda
        direct = ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=teacher, student=student,
            direct_status=ChatRoom.DirectStatus.ACTIVE,
        )
        for sender, text in [
            (student, "Ustoz, uy vazifasining 3-misolini tushunmadim."),
            (teacher, "Ertaga darsdan keyin 10 daqiqa qolsang, birga ko'ramiz."),
            (student, 'Xo\'p, rahmat!'),
        ]:
            Message.objects.create(room=direct, sender=sender, text=text)
        ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=teacher, student=others[0],
            direct_status=ChatRoom.DirectStatus.PENDING,
        )

        self.stdout.write(self.style.SUCCESS(
            'Fake ma\'lumot tayyor (parol hammasiga: 1):\n'
            '  teacher  — O\'qituvchi (Malika Karimova)\n'
            '  data     — O\'qituvchi (Informatika · Python kursi)\n'
            '  perents  — Ota-ona (Aziz Aliyev)\n'
            f'  student  — O\'quvchi Sardor (taklif kodi: {student.invite_code})\n'
            '  nilufar / dilnoza / madina / jasur — qo\'shimcha o\'quvchilar\n'
            '  Xusinboy / Kamron / Jaloliddin / Yokub — data o\'qituvchining o\'quvchilari\n'
            f'Kurslar: {Course.objects.count()} · Darslar: {Lesson.objects.count()} · '
            f'Davomat: {Attendance.objects.count()} · '
            f'Chat xonalari: {ChatRoom.objects.count()} · Xabarlar: {Message.objects.count()} · '
            f'Diqqat tekshiruvlari: {AttentionCheck.objects.count()}'
        ))
