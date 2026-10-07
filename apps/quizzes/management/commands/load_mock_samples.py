"""Mock test (IELTS) ni sinash uchun ORIGINAL demo testlarni yuklaydi.

    python manage.py load_mock_samples --teacher <login> [--course <uuid>] [--exam-in <daqiqa>]
    python manage.py load_mock_samples --teacher <login> [--course <uuid>] --remove

Nima yaratadi (o'qituvchining guruhida, E'LON QILINGAN holda, nomi `[DEMO] ...`):
  * `[DEMO] IELTS Reading`  — 2 matn parchasi guruhi, 20 savol;
  * `[DEMO] IELTS Listening (matn skripti)` — audio o'rniga matn, 10 savol;
  * `[DEMO] IELTS Writing`  — Task 1 va Task 2 (insho).
`--exam-in N` — shu testlardan IELTS imtihonini ham yaratadi (N daqiqadan keyin
boshlanadi; yozilgan o'quvchilarga bildirishnoma boradi). Buyruq IDEMPOTENT:
qayta ishga tushirilsa mavjud demo testlarni takrorlamaydi. `--remove` demo
testlarni o'chiradi (imtihonga biriktirilganlari bundan mustasno).

Matnlar original (rasmiy IELTS materiali EMAS) — faqat tizimni sinash uchun.
Yaratishda o'quvchilarga "yangi test" bildirishnomasi yuborilmaydi.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Course
from apps.quizzes import demo_content, services
from apps.quizzes.models import Quiz
from apps.quizzes.serializers import QuestionWriteSerializer


class Command(BaseCommand):
    help = "IELTS mock test uchun original demo testlarni yuklaydi (yoki o'chiradi)."

    def add_arguments(self, parser):
        parser.add_argument('--teacher', required=True, help="O'qituvchi logini (username)")
        parser.add_argument('--course', help="Guruh (kurs) ID — o'qituvchida bitta guruh bo'lsa shart emas")
        parser.add_argument('--exam-in', type=int, help="IELTS imtihonini N daqiqadan keyin boshlanadigan qilib yaratish")
        parser.add_argument('--remove', action='store_true', help="Demo testlarni o'chirish")

    def handle(self, *args, **options):
        teacher = self._teacher(options['teacher'])
        course = self._course(teacher, options.get('course'))
        if options['remove']:
            return self._remove(teacher, course)

        quizzes = {}
        for key, data in demo_content.SECTION_KEYS.items():
            quizzes[key], created = self._ensure_quiz(teacher, course, data)
            self.stdout.write(f"{'Yaratildi' if created else 'Mavjud'}: {quizzes[key].title}")

        if options.get('exam_in') is not None:
            self._create_exam(teacher, course, quizzes, options['exam_in'])
        self.stdout.write(self.style.SUCCESS('Tayyor.'))

    # ------------------------------------------------------------------
    def _teacher(self, username: str) -> User:
        teacher = User.objects.filter(username=username, role=User.Role.TEACHER).first()
        if teacher is None:
            raise CommandError(f"O'qituvchi topilmadi: {username}")
        return teacher

    def _course(self, teacher: User, course_id) -> Course:
        courses = Course.objects.filter(teacher=teacher)
        if course_id:
            course = courses.filter(pk=course_id).first()
            if course is None:
                raise CommandError("Bu ID dagi guruh shu o'qituvchiga tegishli emas.")
            return course
        found = list(courses[:6])
        if not found:
            raise CommandError("O'qituvchida guruh yo'q — avval guruh yarating.")
        if len(found) > 1:
            listing = '\n'.join(f'  {c.id}  {c.title}' for c in found)
            raise CommandError(f"O'qituvchida bir nechta guruh bor — --course bilan tanlang:\n{listing}")
        return found[0]

    def _ensure_quiz(self, teacher: User, course: Course, data: dict):
        existing = Quiz.objects.filter(course=course, author=teacher, title=data['title']).first()
        if existing is not None:
            return existing, False
        serializer = QuestionWriteSerializer(data=data['questions'], many=True)
        if not serializer.is_valid():
            raise CommandError(f"Demo savollar noto'g'ri ({data['title']}): {serializer.errors}")
        # QORALAMA sifatida yaratib, keyin e'lon qilamiz — shunda `create_quiz` kurs
        # o'quvchilariga "yangi test" bildirishnomasini yubormaydi.
        quiz = services.create_quiz(
            teacher=teacher, course=course, topic=data['topic'], title=data['title'],
            questions=serializer.validated_data, groups=data['groups'], status=Quiz.Status.DRAFT,
        )
        Quiz.objects.filter(pk=quiz.pk).update(status=Quiz.Status.PUBLISHED)
        quiz.refresh_from_db()
        return quiz, True

    def _create_exam(self, teacher: User, course: Course, quizzes: dict, minutes: int) -> None:
        from apps.exams import services as exam_services

        exam = exam_services.create_exam(
            teacher=teacher, course=course, template_ref='ielts', title=demo_content.TITLE_PREFIX + 'IELTS mock',
            starts_at=timezone.now() + timedelta(minutes=max(minutes, 2)),
            sections=[{'key': key, 'quiz': quiz} for key, quiz in quizzes.items()],
        )
        self.stdout.write(f'Imtihon yaratildi: {exam.id} (boshlanishi: {exam.starts_at:%d.%m.%Y %H:%M})')

    def _remove(self, teacher: User, course: Course) -> None:
        removed = skipped = 0
        for quiz in Quiz.objects.filter(
            course=course, author=teacher, title__startswith=demo_content.TITLE_PREFIX,
        ):
            if quiz.exam_sections.exists():
                self.stdout.write(f"Imtihonga biriktirilgan — o'tkazib yuborildi: {quiz.title}")
                skipped += 1
                continue
            quiz.delete()
            removed += 1
        self.stdout.write(f"O'chirildi: {removed}, o'tkazib yuborildi: {skipped}")
