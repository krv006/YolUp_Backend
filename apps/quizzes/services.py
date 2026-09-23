"""Quizzes service qatlami — barcha yozuvchi biznes-logika shu yerda."""
import uuid
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment, Lesson

from . import docx_import, google_docs_import, google_forms_scrape, grading, template_export, xlsx_import
from .models import AnswerResponse, Option, Question, Quiz, QuizAttempt

_IMPORT_PARSERS = {
    '.docx': docx_import.parse_docx_questions,
    '.xlsx': xlsx_import.parse_xlsx_questions,
}

_ENROLLED = Enrollment.Status.APPROVED


def _enrolled_students(course: Course):
    return User.objects.filter(enrollments__course=course, enrollments__status=_ENROLLED)


def _is_owner(quiz: Quiz, teacher: User) -> bool:
    if quiz.author_id == teacher.id:
        return True
    return quiz.course_id is not None and quiz.course.teacher_id == teacher.id


def _notify_new_quiz(quiz: Quiz) -> None:
    """apps.homework._notify_new_assignment bilan bir xil naqsh — real-time
    push (WebSocket) send_notification ichida avtomatik bo'ladi."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    description = f'«{quiz.course.title}»: yangi test qo\'shildi — «{quiz.title or quiz.topic}».'
    for student in _enrolled_students(quiz.course):
        send_notification(
            sender=quiz.course.teacher, description=description,
            target_type=Notification.Target.USER, user_id=student.id,
            link_type='quiz', link_id=str(quiz.id),
        )


T = Question.Type


def _build_answer_key(q_data: dict) -> dict:
    qtype = q_data.get('type', T.SINGLE)
    if qtype == T.TRUE_FALSE:
        return {'correct_bool': bool(q_data['correct_bool'])}
    if qtype == T.NUMERIC:
        return {
            'accepted_answers': [a.strip() for a in q_data['accepted_answers']],
            'tolerance': float(q_data.get('tolerance') or 0),
        }
    if qtype == T.TEXT:
        return {
            'accepted_answers': [a.strip() for a in q_data['accepted_answers']],
            'case_sensitive': bool(q_data.get('case_sensitive')),
        }
    if qtype == T.MATCHING:
        # Chap/o'ng elementlarga alohida ID — aks holda o'quvchi ko'rinishida
        # ID'lar juftni oshkor qilib qo'yadi.
        return {'pairs': [
            {'left_id': uuid.uuid4().hex, 'right_id': uuid.uuid4().hex,
             'left': p['left'].strip(), 'right': p['right'].strip()}
            for p in q_data['pairs']
        ]}
    if qtype == T.FILL_BLANK:
        return {'blanks': [
            {'answers': [a.strip() for a in b['answers']]} for b in q_data['blanks']
        ]}
    return {}


def _create_question(quiz: Quiz, index: int, q_data: dict) -> Question:
    qtype = q_data.get('type', T.SINGLE)
    question = Question.objects.create(
        quiz=quiz, type=qtype, text=q_data['text'], points=q_data.get('points', 2),
        order=q_data.get('order', index), answer_key=_build_answer_key(q_data),
    )
    if qtype in (T.SINGLE, T.MULTIPLE):
        for o_index, o_data in enumerate(q_data['options']):
            Option.objects.create(
                question=question, text=o_data['text'],
                is_correct=o_data.get('is_correct', False), order=o_data.get('order', o_index),
            )
    elif qtype == T.ORDERING:
        # Option.order — TO'G'RI tartib.
        for o_index, item in enumerate(q_data['items']):
            Option.objects.create(question=question, text=item.strip(), order=o_index)
    return question


@transaction.atomic
def create_quiz(
    *, teacher: User, topic: str, questions: list, course: Course | None = None,
    subject: str = '', lesson: Lesson | None = None, title: str = '', description: str = '',
    due_at=None, opens_at=None,
) -> Quiz:
    if not topic.strip():
        raise ValidationError({'topic': _('Mavzu bo\'sh bo\'lishi mumkin emas.')})
    if course is None:
        if not subject:
            raise ValidationError({'subject': _('Guruh yoki fan tanlanishi shart.')})
        if lesson is not None:
            raise ValidationError({'lesson': _("Guruhsiz testni darsga biriktirib bo'lmaydi.")})
    else:
        if course.teacher_id != teacher.id:
            raise PermissionDenied(_('Bu kurs sizga tegishli emas.'))
        if lesson is not None and lesson.course_id != course.id:
            raise ValidationError({'lesson': _('Bu dars ushbu kursga tegishli emas.')})
        subject = course.subject  # guruh testi fanini kursdan oladi

    quiz = Quiz.objects.create(
        course=course, author=teacher, subject=subject, lesson=lesson, topic=topic, title=title,
        description=description, due_at=due_at, opens_at=opens_at,
    )
    for q_index, q_data in enumerate(questions):
        _create_question(quiz, q_index, q_data)

    # Faqat DARHOL ochiq test uchun bildirishnoma yuboriladi — kelajakdagi
    # "ochilish kuni"si bo'lgan testda hali ko'ra olmaydigan havolaga
    # bildirishnoma yuborish chalkashlik keltirib chiqaradi (buzuq link).
    if course is not None and (opens_at is None or opens_at <= timezone.now()):
        transaction.on_commit(lambda: _notify_new_quiz(quiz))
    return quiz


def import_quiz_file(*, upload) -> dict:
    """`.docx` yoki `.xlsx` faylni parse qilib preview qaytaradi — HECH NARSA
    DB'ga yozilmaydi. O'qituvchi preview'ni ko'rib (kerak bo'lsa tahrirlab)
    `create_quiz`'ga (yuqoridagi, mavjud endpoint) yuboradi."""
    if upload is None:
        raise ValidationError({'file': _('Fayl majburiy.')})
    ext = Path(upload.name or '').suffix.lower()
    parser = _IMPORT_PARSERS.get(ext)
    if parser is None:
        raise ValidationError({'file': _("Faqat .docx yoki .xlsx fayl qo'llab-quvvatlanadi.")})
    if upload.size > docx_import.MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError({'file': _('Fayl %(size).1f MB; chegara %(max_mb)s MB.') % {
            'size': upload.size / 1024 / 1024, 'max_mb': docx_import.MAX_IMPORT_FILE_SIZE_MB,
        }})

    try:
        result = parser(upload)
    except Exception as exc:
        raise ValidationError({'file': _("Faylni o'qib bo'lmadi: %(error)s") % {'error': str(exc)}}) from exc
    if not result['questions']:
        raise ValidationError({'file': _('Fayldan birorta ham savol topilmadi.')})
    return result


def import_google_doc(*, url: str) -> dict:
    """Ochiq (public) Google Docs havolasidan preview qaytaradi — `.docx`
    import bilan bir xil format, HECH NARSA DB'ga yozilmaydi."""
    if not url or not url.strip():
        raise ValidationError({'url': _('Havola majburiy.')})
    result = google_docs_import.parse_google_doc(url=url)
    if not result['questions']:
        raise ValidationError({'url': _('Hujjatdan birorta ham savol topilmadi.')})
    return result


def import_google_form(*, url: str) -> dict:
    """Ochiq (public) Google Forms havolasidan preview qaytaradi — TO'G'RI
    JAVOBLAR ANIQLANMAYDI (Google buni ochiq sahifaga yubormaydi), barcha
    savol `warnings`da belgilanadi. HECH NARSA DB'ga yozilmaydi."""
    if not url or not url.strip():
        raise ValidationError({'url': _('Havola majburiy.')})
    result = google_forms_scrape.parse_google_form(url=url)
    if not result['questions']:
        raise ValidationError({'url': _('Formadan birorta ham qo\'llab-quvvatlanadigan savol topilmadi.')})
    return result


def build_quiz_template(*, fmt: str, count) -> bytes:
    """Bo'sh shablon fayl (.docx / .xlsx) — `count` ta bo'sh savol bloki bilan,
    import parserlariga mos formatda (`template_export.py`)."""
    clamped = template_export.clamp_count(count)
    if fmt == 'docx':
        return template_export.build_docx_template(clamped)
    if fmt == 'xlsx':
        return template_export.build_xlsx_template(clamped)
    raise ValidationError({'format': _("Format faqat 'docx' yoki 'xlsx' bo'lishi mumkin.")})


_EDITABLE_FIELDS = ('topic', 'title', 'description', 'due_at', 'opens_at', 'questions')


@transaction.atomic
def update_quiz(*, teacher: User, quiz: Quiz, **fields) -> Quiz:
    """Metadata (mavzu/nom/tavsif/muddat/ochilish vaqti) va ixtiyoriy
    `questions` (berilsa — to'liq almashtiriladi, yaratishdagi bilan bir
    xil validatsiya/saqlash). Testda allaqachon urinish(lar) bo'lsa,
    savollarni o'zgartirish RAD ETILADI — aks holda o'quvchining natijasi
    (AnswerResponse) endi mavjud bo'lmagan savolga ishora qilib qolardi
    (Question CASCADE — savol o'chsa, unga tegishli javoblar ham o'chadi)."""
    if not _is_owner(quiz, teacher):
        raise PermissionDenied(_('Bu test sizga tegishli emas.'))
    unknown = set(fields) - set(_EDITABLE_FIELDS)
    if unknown:
        raise ValidationError({f: _("Bu maydonni o'zgartirib bo'lmaydi.") for f in unknown})
    if 'topic' in fields and not fields['topic'].strip():
        raise ValidationError({'topic': _('Mavzu bo\'sh bo\'lishi mumkin emas.')})

    questions = fields.pop('questions', None)
    if questions is not None:
        if QuizAttempt.objects.filter(quiz=quiz).exists():
            raise ValidationError({
                'questions': _("Bu testda allaqachon urinish(lar) bor — savollarni o'zgartirib bo'lmaydi."),
            })
        quiz.questions.all().delete()
        for q_index, q_data in enumerate(questions):
            _create_question(quiz, q_index, q_data)

    for field, value in fields.items():
        setattr(quiz, field, value)
    if fields:
        quiz.save(update_fields=list(fields))
    return quiz


def delete_quiz(*, teacher: User, quiz: Quiz) -> None:
    if not _is_owner(quiz, teacher):
        raise PermissionDenied(_('Bu test sizga tegishli emas.'))
    quiz.delete()


@transaction.atomic
def submit_attempt(*, student: User, quiz: Quiz, answers: list) -> QuizAttempt:
    is_enrolled = Enrollment.objects.filter(
        course=quiz.course, student=student, status=_ENROLLED,
    ).exists()
    if not is_enrolled:
        raise PermissionDenied(_('Siz bu kursga yozilmagansiz.'))

    questions = list(quiz.questions.prefetch_related('options'))
    given_by_question = {}
    for answer in answers:
        question = answer['question']
        if question.quiz_id != quiz.id:
            raise ValidationError({'answers': _('Savol ushbu testga tegishli emas.')})
        if question.id in given_by_question:
            raise ValidationError({'answers': _("Bir savolga faqat bitta javob yuborilishi mumkin.")})
        given_by_question[question.id] = answer

    attempt = QuizAttempt.objects.create(quiz=quiz, student=student)
    score = 0.0
    for question in questions:
        graded = grading.grade(question, given_by_question.get(question.id, {}))
        AnswerResponse.objects.create(
            attempt=attempt, question=question,
            selected_option=(given_by_question.get(question.id, {}).get('selected_option')
                             if question.type == T.SINGLE else None),
            answer=graded.answer, given_display=graded.given_display,
            earned_points=graded.earned, is_correct=graded.earned == question.points,
        )
        score += graded.earned

    # Javobsiz qolgan savollar ham maksimal ballga qo'shiladi (adolatli ball).
    attempt.score = grading.round_points(score)
    attempt.max_score = sum(q.points for q in questions)
    attempt.save(update_fields=['score', 'max_score'])
    return attempt
