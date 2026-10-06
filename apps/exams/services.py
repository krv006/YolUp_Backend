"""Exams service qatlami — shablonlar, imtihon yaratish, sinxron taymer,
javob saqlash va natija hisoblash (HTTP'dan mustaqil)."""
import copy
import re
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.quizzes import grading
from apps.quizzes.models import Question, Quiz

from . import scoring as scoring_engines
from . import selectors
from .models import Exam, ExamAnswer, ExamAttempt, ExamSection, ExamTemplate
from .presets import SYSTEM_TEMPLATES

Kind = ExamSection.Kind

# Bo'lim tugagandan keyin ham shu soniya ichida kelgan oxirgi avtosaqlash
# qabul qilinadi (tarmoq kechikishi uchun) — undan keyin rad etiladi.
GRACE = timedelta(seconds=5)
MAX_SECTION_MINUTES = 300
MAX_BREAK_MINUTES = 60
MAX_TOTAL_MINUTES = 720

_KEY_RE = re.compile(r'^[a-z0-9_]{1,50}$')
_TYPES = {Kind.SECTION.value, Kind.BREAK.value, Kind.OFFLINE.value}


# ---------------------------------------------------------------------------
# Shablonlar
# ---------------------------------------------------------------------------
def _items_error(message: str) -> ValidationError:
    return ValidationError({'items': message})


def normalize_items(items) -> list:
    """Custom shablon elementlarini tekshirib, toza ro'yxat qaytaradi."""
    if not isinstance(items, list) or not items:
        raise _items_error(_("Kamida bitta bo'lim kerak."))
    seen, result = set(), []
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise _items_error(_("%(n)s-element noto'g'ri formatda.") % {'n': index})
        kind = raw.get('type')
        if kind not in _TYPES:
            raise _items_error(_("%(n)s-element turi 'section', 'break' yoki 'offline' bo'lishi kerak.") % {'n': index})
        key = str(raw.get('key') or '').strip()
        if not _KEY_RE.match(key):
            raise _items_error(_("%(n)s-element kaliti lotin harf, raqam yoki _ dan iborat bo'lishi kerak.") % {'n': index})
        if key in seen:
            raise _items_error(_("Kalit takrorlangan: %(key)s.") % {'key': key})
        seen.add(key)
        title = str(raw.get('title') or '').strip()[:200]
        if not title:
            raise _items_error(_("%(n)s-elementning nomi bo'sh.") % {'n': index})
        try:
            minutes = int(raw.get('minutes') or 0)
        except (TypeError, ValueError):
            raise _items_error(_("%(n)s-elementning vaqti butun son bo'lishi kerak.") % {'n': index})
        limit = {Kind.SECTION: MAX_SECTION_MINUTES, Kind.BREAK: MAX_BREAK_MINUTES}.get(kind, 0)
        if kind != Kind.OFFLINE and not 1 <= minutes <= limit:
            raise _items_error(_("%(n)s-element vaqti 1 dan %(max)s daqiqagacha bo'lishi kerak.") % {
                'n': index, 'max': limit})
        if kind == Kind.OFFLINE:
            minutes = 0
        try:
            weight = float(raw.get('weight') or 1)
        except (TypeError, ValueError):
            weight = 0
        if not 0 < weight <= 100:
            raise _items_error(_("%(n)s-element og'irligi 0 dan katta, 100 dan oshmasligi kerak.") % {'n': index})
        item = {
            'type': kind, 'key': key, 'title': title, 'minutes': minutes,
            'group': str(raw.get('group') or '')[:50],
            'manual': bool(raw.get('manual')) or kind == Kind.OFFLINE,
            'weight': weight,
        }
        if raw.get('questions') not in (None, ''):
            try:
                item['questions'] = max(0, int(raw['questions']))
            except (TypeError, ValueError):
                pass
        result.append(item)
    if not any(i['type'] == Kind.SECTION for i in result):
        raise _items_error(_("Kamida bitta vaqtli bo'lim bo'lishi kerak."))
    if result[0]['type'] == Kind.BREAK or result[-1]['type'] == Kind.BREAK:
        raise _items_error(_("Tanaffus birinchi yoki oxirgi bo'lishi mumkin emas."))
    if sum(i['minutes'] for i in result) > MAX_TOTAL_MINUTES:
        raise _items_error(_("Imtihon jami %(max)s daqiqadan oshmasligi kerak.") % {'max': MAX_TOTAL_MINUTES})
    return result


def normalize_scoring(scoring) -> dict:
    scoring = scoring or {}
    if not isinstance(scoring, dict):
        raise ValidationError({'scoring': _("Noto'g'ri format.")})
    try:
        scale = int(scoring.get('scale') or 100)
    except (TypeError, ValueError):
        raise ValidationError({'scoring': _("Shkala butun son bo'lishi kerak.")})
    if not 1 <= scale <= 1000:
        raise ValidationError({'scoring': _("Shkala 1 dan 1000 gacha bo'lishi kerak.")})
    result = {'type': 'percent', 'scale': scale}
    pass_percent = scoring.get('pass_percent')
    if pass_percent not in (None, ''):
        try:
            pass_percent = float(pass_percent)
        except (TypeError, ValueError):
            raise ValidationError({'scoring': _("O'tish foizi son bo'lishi kerak.")})
        if not 0 <= pass_percent <= 100:
            raise ValidationError({'scoring': _("O'tish foizi 0 dan 100 gacha bo'lishi kerak.")})
        result['pass_percent'] = pass_percent
    return result


def create_template(*, owner: User, name: str, description: str, items, scoring) -> ExamTemplate:
    return ExamTemplate.objects.create(
        owner=owner, name=name.strip(), description=description or '',
        items=normalize_items(items), scoring=normalize_scoring(scoring),
    )


def delete_template(*, owner: User, template_id) -> None:
    deleted, _rows = ExamTemplate.objects.filter(pk=template_id, owner=owner).delete()
    if not deleted:
        raise NotFound(_('Shablon topilmadi.'))


def list_templates(user: User) -> list:
    """Tayyor shablonlar + o'qituvchining o'z custom shablonlari."""
    result = [
        {'id': key, 'kind': 'system', 'name': data['name'], 'description': data['description'],
         'items': data['items'], 'scoring': data['scoring']}
        for key, data in SYSTEM_TEMPLATES.items()
    ]
    for template in ExamTemplate.objects.filter(owner=user):
        result.append({
            'id': str(template.id), 'kind': 'custom', 'name': template.name,
            'description': template.description, 'items': template.items, 'scoring': template.scoring,
        })
    return result


def _resolve_template(user: User, ref: str):
    if ref in SYSTEM_TEMPLATES:
        data = SYSTEM_TEMPLATES[ref]
        return ref, normalize_items(copy.deepcopy(data['items'])), copy.deepcopy(data['scoring'])
    try:
        template = ExamTemplate.objects.get(pk=ref, owner=user)
    except (ExamTemplate.DoesNotExist, DjangoValidationError, ValueError, TypeError):
        raise ValidationError({'template': _('Shablon topilmadi.')})
    return 'custom', normalize_items(copy.deepcopy(template.items)), copy.deepcopy(template.scoring)


# ---------------------------------------------------------------------------
# Imtihon yaratish / tahrirlash
# ---------------------------------------------------------------------------
def _is_owner(exam: Exam, user: User) -> bool:
    return exam.created_by_id == user.id or exam.course.teacher_id == user.id


def _notify_exam(exam: Exam) -> None:
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    when = timezone.localtime(exam.starts_at).strftime('%d.%m.%Y %H:%M')
    description = f"«{exam.course.title}»: yangi imtihon — «{exam.title}», {when}."
    for student in selectors.enrolled_students(exam):
        send_notification(
            sender=exam.course.teacher, description=description,
            target_type=Notification.Target.USER, user_id=student.id,
            link_type='exam', link_id=str(exam.id), kind='exam_scheduled',
        )


@transaction.atomic
def create_exam(*, teacher: User, course, template_ref: str, title: str, starts_at, sections: list) -> Exam:
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_('Bu kurs sizga tegishli emas.'))
    if starts_at <= timezone.now():
        raise ValidationError({'starts_at': _("Boshlanish vaqti kelajakda bo'lishi kerak.")})

    template_key, items, scoring = _resolve_template(teacher, template_ref)
    payload = {}
    for entry in sections:
        if entry['key'] in payload:
            raise ValidationError({'sections': _("Kalit takrorlangan: %(key)s.") % {'key': entry['key']}})
        payload[entry['key']] = entry

    section_keys = {i['key'] for i in items if i['type'] == Kind.SECTION}
    unknown = set(payload) - section_keys
    if unknown:
        raise ValidationError({'sections': _("Shablonda bunday bo'lim yo'q: %(keys)s.") % {
            'keys': ', '.join(sorted(unknown))}})
    missing = section_keys - set(payload)
    if missing:
        raise ValidationError({'sections': _("Bu bo'limlarga test biriktirilmagan: %(keys)s.") % {
            'keys': ', '.join(sorted(missing))}})

    used_quizzes = set()
    rows = []
    for order, item in enumerate(items):
        quiz, minutes = None, item['minutes']
        if item['type'] == Kind.SECTION:
            entry = payload[item['key']]
            quiz = entry['quiz']
            minutes = entry.get('minutes') or minutes
            _check_quiz(teacher, quiz, item['key'])
            if quiz.id in used_quizzes:
                raise ValidationError({'sections': _("Bir test imtihonda faqat bitta bo'limga biriktiriladi.")})
            used_quizzes.add(quiz.id)
        rows.append((order, item, quiz, minutes))

    total_minutes = sum(minutes for _o, item, _q, minutes in rows if item['type'] != Kind.OFFLINE)
    if total_minutes > MAX_TOTAL_MINUTES:
        raise ValidationError({'sections': _("Imtihon jami %(max)s daqiqadan oshmasligi kerak.") % {
            'max': MAX_TOTAL_MINUTES}})

    exam = Exam.objects.create(
        course=course, created_by=teacher, title=title.strip(), template_key=template_key,
        scoring=scoring, starts_at=starts_at, ends_at=starts_at + timedelta(minutes=total_minutes),
    )
    ExamSection.objects.bulk_create([
        ExamSection(
            exam=exam, order=order, kind=item['type'], key=item['key'], group=item.get('group', ''),
            title=item['title'], minutes=0 if item['type'] == Kind.OFFLINE else minutes,
            manual=item.get('manual', False), weight=item.get('weight', 1), quiz=quiz,
        )
        for order, item, quiz, minutes in rows
    ])
    transaction.on_commit(lambda: _notify_exam(exam))
    return exam


def _check_quiz(teacher: User, quiz: Quiz, key: str) -> None:
    from apps.quizzes import selectors as quiz_selectors

    if not quiz_selectors.quizzes_for(teacher).filter(pk=quiz.pk).exists():
        raise ValidationError({'sections': _("%(key)s: bu test sizga tegishli emas.") % {'key': key}})
    if quiz.status != Quiz.Status.PUBLISHED:
        raise ValidationError({'sections': _("%(key)s: test e'lon qilinmagan (qoralama).") % {'key': key}})
    if not quiz.questions.exists():
        raise ValidationError({'sections': _("%(key)s: testda savol yo'q.") % {'key': key}})


def update_exam(*, teacher: User, exam: Exam, title=None, starts_at=None) -> Exam:
    if not _is_owner(exam, teacher):
        raise PermissionDenied(_('Bu imtihon sizga tegishli emas.'))
    if exam.starts_at <= timezone.now():
        raise ValidationError({'detail': _("Boshlangan imtihonni o'zgartirib bo'lmaydi.")})
    if title is not None:
        exam.title = title.strip()
    if starts_at is not None:
        if starts_at <= timezone.now():
            raise ValidationError({'starts_at': _("Boshlanish vaqti kelajakda bo'lishi kerak.")})
        duration = exam.ends_at - exam.starts_at
        exam.starts_at, exam.ends_at = starts_at, starts_at + duration
    exam.save()
    return exam


def delete_exam(*, teacher: User, exam: Exam) -> None:
    if not _is_owner(exam, teacher):
        raise PermissionDenied(_('Bu imtihon sizga tegishli emas.'))
    if exam.starts_at <= timezone.now() or exam.attempts.exists():
        raise ValidationError({'detail': _("Boshlangan imtihonni o'chirib bo'lmaydi.")})
    exam.delete()


# ---------------------------------------------------------------------------
# Sinxron taymer
# ---------------------------------------------------------------------------
def timeline(exam: Exam, sections=None) -> list:
    """[(ExamSection, start, end)] — offline qismlar kirmaydi."""
    cursor, result = exam.starts_at, []
    for section in sections if sections is not None else exam.sections.all():
        if section.kind == Kind.OFFLINE:
            continue
        end = cursor + timedelta(minutes=section.minutes)
        result.append((section, cursor, end))
        cursor = end
    return result


def exam_state(exam: Exam, now=None) -> str:
    now = now or timezone.now()
    if now < exam.starts_at:
        return 'upcoming'
    if now >= exam.ends_at:
        return 'finished'
    return 'running'


def _item_dict(section, start, end) -> dict:
    return {
        'kind': section.kind, 'key': section.key, 'title': section.title, 'group': section.group,
        'minutes': section.minutes, 'starts_at': start, 'ends_at': end,
    }


def current_payload(*, student: User, exam: Exam, now=None) -> dict:
    """Joriy holat: qaysi bo'lim/tanaffus, server vaqti, savollar va saqlangan javoblar."""
    now = now or timezone.now()
    state = exam_state(exam, now)
    attempt = ExamAttempt.objects.filter(exam=exam, student=student).first()
    submitted = bool(attempt and attempt.finished_at)
    payload = {
        'server_now': now, 'state': 'submitted' if (submitted and state == 'running') else state,
        'starts_at': exam.starts_at, 'ends_at': exam.ends_at, 'item': None, 'next': None,
    }
    if state != 'running' or submitted:
        return payload

    sections = list(exam.sections.select_related('quiz'))
    entries = timeline(exam, sections)
    for index, (section, start, end) in enumerate(entries):
        if start <= now < end:
            item = _item_dict(section, start, end)
            if section.kind == Kind.SECTION:
                attempt, _created = ExamAttempt.objects.get_or_create(exam=exam, student=student)
                if attempt.finished_at:
                    payload['state'] = 'submitted'
                    return payload
                item['questions'] = list(
                    section.quiz.questions.prefetch_related('options')) if section.quiz_id else []
                item['groups'] = list(section.quiz.groups.all()) if section.quiz_id else []
                item['saved'] = [
                    {'question': a.question_id, 'answer': a.answer}
                    for a in ExamAnswer.objects.filter(attempt=attempt, section=section)
                ]
            payload['item'] = item
            if index + 1 < len(entries):
                nxt = entries[index + 1]
                payload['next'] = _item_dict(*nxt)
            break
    return payload


@transaction.atomic
def save_answers(*, student: User, exam: Exam, answers: list, now=None) -> int:
    """Bo'lim javoblarini saqlaydi (avtosaqlash — qayta chaqirsa ustiga yozadi).
    Har javob DARHOL baholanadi; bo'lim vaqti tugagach (+GRACE) rad etiladi."""
    now = now or timezone.now()
    if now < exam.starts_at:
        raise PermissionDenied(_('Imtihon hali boshlanmagan.'))
    attempt, _created = ExamAttempt.objects.get_or_create(exam=exam, student=student)
    if attempt.finished_at:
        raise PermissionDenied(_('Siz imtihonni yakunlagansiz.'))

    sections = list(exam.sections.filter(kind=Kind.SECTION))
    window = {s.id: (start, end) for s, start, end in timeline(exam, list(exam.sections.all()))}
    by_quiz = {s.quiz_id: s for s in sections if s.quiz_id}

    prepared = []
    for answer in answers:
        question = answer['question']
        section = by_quiz.get(question.quiz_id)
        if section is None:
            raise ValidationError({'answers': _('Savol bu imtihonga tegishli emas.')})
        start, end = window[section.id]
        if now < start:
            raise PermissionDenied(_("Bu bo'lim hali boshlanmagan."))
        if now > end + GRACE:
            raise PermissionDenied(_("Bu bo'limning vaqti tugagan."))
        graded = grading.grade(question, answer)
        prepared.append((section, question, graded))

    for section, question, graded in prepared:
        ExamAnswer.objects.update_or_create(
            attempt=attempt, question=question,
            defaults={
                'section': section, 'answer': graded.answer,
                'given_display': graded.given_display, 'earned_points': graded.earned,
            },
        )
    return len(prepared)


def finish_attempt(*, student: User, exam: Exam, now=None) -> ExamAttempt:
    now = now or timezone.now()
    if exam_state(exam, now) != 'running':
        raise PermissionDenied(_('Imtihon hozir davom etmayapti.'))
    attempt, _created = ExamAttempt.objects.get_or_create(exam=exam, student=student)
    if not attempt.finished_at:
        attempt.finished_at = now
        attempt.save(update_fields=['finished_at', 'updated_at'])
    return attempt


# ---------------------------------------------------------------------------
# Natijalar
# ---------------------------------------------------------------------------
def _section_inputs(exam: Exam, attempt_ids: list) -> dict:
    """{attempt_id: [scoring bo'limlari]} — bir nechta so'rov bilan hammasi uchun."""
    sections = [s for s in exam.sections.all() if s.kind != Kind.BREAK]
    quiz_ids = [s.quiz_id for s in sections if s.quiz_id]
    maximum = {
        row['quiz_id']: row['total']
        for row in Question.objects.filter(quiz_id__in=quiz_ids).values('quiz_id').annotate(total=Sum('points'))
    }
    earned = {
        (row['attempt_id'], row['section_id']): row['total']
        for row in ExamAnswer.objects.filter(attempt_id__in=attempt_ids)
        .values('attempt_id', 'section_id').annotate(total=Sum('earned_points'))
    }
    manual = dict(ExamAttempt.objects.filter(pk__in=attempt_ids).values_list('pk', 'manual_scores'))
    result = {}
    for attempt_id in attempt_ids:
        scores = manual.get(attempt_id) or {}
        rows = []
        for section in sections:
            offline = section.kind == Kind.OFFLINE
            rows.append({
                'key': section.key, 'title': section.title, 'group': section.group,
                'weight': section.weight, 'manual': section.manual,
                'earned': None if offline else float(earned.get((attempt_id, section.id)) or 0),
                'max': None if offline else float(maximum.get(section.quiz_id) or 0),
                'manual_score': scores.get(section.key),
            })
        result[attempt_id] = rows
    return result


def _student_info(student: User) -> dict:
    full_name = f'{student.first_name} {student.last_name}'.strip()
    return {'id': student.id, 'username': student.username, 'name': full_name or student.username}


def build_results(exam: Exam, attempts: list, staff: bool = False) -> list:
    from . import writing

    inputs = _section_inputs(exam, [a.id for a in attempts])
    results = []
    for attempt in attempts:
        data = scoring_engines.compute(exam.scoring, inputs[attempt.id])
        data.update({
            'student': _student_info(attempt.student), 'participated': True,
            'finished_at': attempt.finished_at, 'ai': writing.ai_payload(attempt, staff),
        })
        results.append(data)
    return results


def results_visible(exam: Exam, attempt: ExamAttempt | None, now=None) -> bool:
    now = now or timezone.now()
    return now >= exam.ends_at or bool(attempt and attempt.finished_at)


def list_results(*, user: User, exam: Exam) -> dict:
    """Rolga qarab: o'qituvchi/admin — hamma o'quvchilar (kelmaganlar ham);
    o'quvchi — o'zi; ota-ona — bolalari. O'quvchi/ota-ona uchun natija imtihon
    tugagach (yoki o'quvchi o'zi yakunlagach) ko'rinadi."""
    staff = user.role not in (User.Role.STUDENT, User.Role.PARENT)
    if staff:
        students = list(selectors.enrolled_students(exam))
    elif user.role == User.Role.STUDENT:
        students = [user]
    else:
        child_ids = set(selectors.children_of(user).values_list('id', flat=True))
        students = [s for s in selectors.enrolled_students(exam) if s.id in child_ids]

    attempts = {
        a.student_id: a for a in ExamAttempt.objects.filter(
            exam=exam, student__in=students).select_related('student')
    }
    computed = {r['student']['id']: r for r in build_results(exam, list(attempts.values()), staff)}
    now = timezone.now()
    items = []
    for student in students:
        attempt = attempts.get(student.id)
        if not staff and not results_visible(exam, attempt, now):
            items.append({'student': _student_info(student), 'participated': bool(attempt), 'hidden': True})
        elif attempt is None:
            items.append({'student': _student_info(student), 'participated': False})
        else:
            items.append(computed[student.id])
    return {
        'exam': exam.id, 'engine': exam.scoring.get('type') or 'percent',
        'state': exam_state(exam, now), 'results': items,
    }


def student_detail(*, user: User, exam: Exam, student_id) -> dict:
    listing = list_results(user=user, exam=exam)
    for item in listing['results']:
        if str(item['student']['id']) == str(student_id):
            break
    else:
        raise NotFound(_("O'quvchi topilmadi."))
    if user.role not in (User.Role.STUDENT, User.Role.PARENT) and item.get('participated'):
        # O'qituvchi qo'lda baholashi uchun yozma javoblarni ko'radi
        item['manual_answers'] = [
            {'section': a.section.key, 'question': a.question.text, 'answer': a.given_display}
            for a in ExamAnswer.objects.filter(
                attempt__exam=exam, attempt__student_id=student_id, section__manual=True,
            ).select_related('section', 'question')
        ]
    return item


def set_manual_scores(*, teacher: User, exam: Exam, student_id, scores: dict) -> dict:
    if not _is_owner(exam, teacher):
        raise PermissionDenied(_('Bu imtihon sizga tegishli emas.'))
    student = selectors.enrolled_students(exam).filter(pk=student_id).first()
    if student is None:
        raise NotFound(_("O'quvchi topilmadi."))
    manual_keys = {s.key for s in exam.sections.all() if s.manual}
    cleaned = {}
    for key, value in scores.items():
        if key not in manual_keys:
            raise ValidationError({'scores': _("Bu bo'limni qo'lda baholab bo'lmaydi: %(key)s.") % {'key': key}})
        try:
            cleaned[key] = scoring_engines.validate_manual(exam.scoring, key, value)
        except scoring_engines.ManualScoreError as exc:
            raise ValidationError({'scores': f'{key}: {exc}'})
    attempt, _created = ExamAttempt.objects.get_or_create(exam=exam, student=student)
    attempt.manual_scores = {**(attempt.manual_scores or {}), **cleaned}
    attempt.save(update_fields=['manual_scores', 'updated_at'])
    return student_detail(user=teacher, exam=exam, student_id=student.id)
