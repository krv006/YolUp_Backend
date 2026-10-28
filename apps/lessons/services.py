"""Lessons service layer — kurs/dars/yozilish bo'yicha yozuvchi biznes-logika."""
import logging
import uuid
from datetime import timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts import selectors as account_selectors
from apps.accounts.models import User
from apps.core import audit

from .models import Attendance, Course, Enrollment, Lesson, LessonReminder, ReminderPref


@transaction.atomic
def create_course(*, teacher: User, request=None, **data) -> Course:
    course = Course.objects.create(teacher=teacher, **data)
    # Har kurs = bitta guruh chat (EduTech.docx) — kurs bilan birga ochiladi
    from apps.chat import services as chat_services
    chat_services.ensure_course_room(course)
    audit.record(action='course.create', actor=teacher, target=course, request=request)
    return course


def _set_lesson_quiz(*, lesson: Lesson, quiz) -> None:
    """`quiz=None` — hozir shu darsga biriktirilgan testni (bo'lsa) ajratadi.
    Boshqa test berilsa — eskisi ajratilib, yangisi biriktiriladi. Serializer
    (`LessonSerializer.validate`) allaqachon tekshirgan: berilgan test bo'sh
    (`lesson=None`) yoki aynan shu darsga tegishli bo'lishi shart edi."""
    from apps.quizzes.models import Quiz

    current = Quiz.objects.filter(lesson=lesson).first()
    if current is not None and current != quiz:
        current.lesson = None
        current.save(update_fields=['lesson'])
    if quiz is not None and quiz.lesson_id != lesson.id:
        quiz.lesson = lesson
        quiz.save(update_fields=['lesson'])


@transaction.atomic
def schedule_lesson(*, teacher: User, course: Course, request=None, quiz=None, **data) -> Lesson:
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs egasi dars qo'sha oladi."))
    lesson = Lesson.objects.create(course=course, **data)
    if quiz is not None:
        _set_lesson_quiz(lesson=lesson, quiz=quiz)
    audit.record(action='lesson.schedule', actor=teacher, target=lesson, request=request)
    return lesson


def schedule_series_from(*, teacher: User, course: Course, starts_at, duration_min: int, recurrence: dict,
                         title: str = '', note: str = '', request=None) -> list:
    """`POST /lessons/` ga `recurrence` berilganda: shu dars (starts_at) hafta kuni va soatida `weeks` hafta davomida
    `weekdays` kunlari takrorlanadi (birinchisi — shu darsning o'zi). Qaytaradi: yaratilgan darslar."""
    from datetime import timedelta

    local = timezone.localtime(starts_at)
    end = local + timedelta(minutes=duration_min)
    if end.date() != local.date():
        raise ValidationError({'recurrence': _("Takrorlanuvchi dars yarim tundan o'tib ketmasligi kerak.")})
    days = sorted(set(recurrence['weekdays']) | {local.weekday()})  # shu darsning o'z kuni seriyaga doim kiradi
    return schedule_recurring(
        teacher=teacher, course=course, days=days, start_time=local.time(), end_time=end.time(),
        weeks=recurrence['weeks'], start_date=local.date(), title=title, note=note, request=request,
    )


def apply_to_series(*, lesson: Lesson, changes: dict, shift) -> int:
    """`PATCH ?scope=series`: shu darsdan keyingi (hali o'tmagan, rejalashtirilgan) seriya darslariga ham o'zgarish
    qo'llanadi; `shift` — shu darsning boshlanish vaqti qancha siljigani (hamma darsga bir xil qo'shiladi)."""
    others = Lesson.objects.filter(
        recurrence_id=lesson.recurrence_id, status=Lesson.Status.SCHEDULED, starts_at__gt=timezone.now(),
    ).exclude(pk=lesson.pk)
    count = 0
    for other in others:
        for field, value in changes.items():
            setattr(other, field, value)
        if shift:
            other.starts_at = other.starts_at + shift
        other.save()
        count += 1
    return count


@transaction.atomic
def cancel_lesson(*, teacher: User, lesson: Lesson, scope: str = 'one', request=None) -> list:
    """Darsni bekor qiladi (o'chirmaydi): `status=cancelled`, jadvalda chizilgan holda qoladi, o'quvchilarga bildirishnoma
    boradi. `scope=series` — shu seriyadagi hamma rejalashtirilgan dars. Faqat rejalashtirilgan dars bekor qilinadi."""
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi darsni bekor qila oladi."))
    if scope not in ('one', 'series'):
        raise ValidationError({'scope': _("'one' yoki 'series' bo'lishi kerak.")})
    if lesson.status != Lesson.Status.SCHEDULED:
        raise ValidationError({'detail': _("Faqat rejalashtirilgan darsni bekor qilish mumkin.")})
    if scope == 'series' and lesson.recurrence_id:
        targets = list(Lesson.objects.filter(
            recurrence_id=lesson.recurrence_id, course=lesson.course, status=Lesson.Status.SCHEDULED,
        ))
    else:
        targets = [lesson]
    for target in targets:
        target.status = Lesson.Status.CANCELLED
        target.save(update_fields=['status', 'updated_at'])
    audit.record(
        action='lesson.cancel', actor=teacher, target=lesson,
        meta={'scope': scope, 'count': len(targets)}, request=request,
    )
    _notify_cancelled(teacher, lesson, targets)
    return targets


def _notify_cancelled(teacher: User, lesson: Lesson, targets: list) -> None:
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    title = lesson.title or lesson.course.title
    when = timezone.localtime(lesson.starts_at).strftime('%d.%m.%Y %H:%M')
    text = (
        f'«{lesson.course.title}»: {when} dagi «{title}» darsi bekor qilindi.' if len(targets) == 1
        else f'«{lesson.course.title}»: {when} dan boshlab {len(targets)} ta dars bekor qilindi.'
    )
    students = User.objects.filter(
        enrollments__course=lesson.course, enrollments__status=Enrollment.Status.APPROVED,
    ).distinct()
    for student in students:
        try:
            send_notification(
                sender=teacher, description=text, target_type=Notification.Target.USER, user_id=student.id,
                kind='lesson_cancelled', link_type='lesson', link_id=str(lesson.id),
            )
        except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
            logging.getLogger('apps').warning('lesson_cancelled bildirishnomasi yuborilmadi', exc_info=True)


@transaction.atomic
def update_lesson_quiz(*, teacher: User, lesson: Lesson, quiz, request=None) -> Lesson:
    """Mavjud darsga testni biriktirish/ajratish (`quiz=None`) — tahrirlashda."""
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs egasi darsni tahrirlay oladi."))
    _set_lesson_quiz(lesson=lesson, quiz=quiz)
    audit.record(action='lesson.set_quiz', actor=teacher, target=lesson, request=request)
    return lesson


@transaction.atomic
def schedule_recurring(*, teacher: User, course: Course, days: list[int],
                       start_time, end_time, weeks: int, start_date, title: str = '', note: str = '',
                       request=None) -> list[Lesson]:
    """Haftalik jadval asosida ko'plab darslarni bir yo'la yaratadi.

    O'qituvchining BOSHQA kurslari bilan ham (masalan ingliz tili + matematika)
    vaqt ustma-ust tushmasligini tekshiradi — course__teacher bo'yicha, faqat
    joriy kurs emas.
    """
    from datetime import datetime, timedelta

    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs egasi dars qo'sha oladi."))

    duration_min = int(
        (datetime.combine(start_date, end_time) - datetime.combine(start_date, start_time)).total_seconds() // 60,
    )

    now = timezone.now()
    week_start = start_date - timedelta(days=start_date.weekday())
    slots = []
    for week in range(weeks):
        for day in sorted(set(days)):
            lesson_date = week_start + timedelta(weeks=week, days=day)
            if lesson_date < start_date:
                continue
            slot = timezone.make_aware(datetime.combine(lesson_date, start_time))
            if slot < now:  # bugungi kun uchun soat allaqachon o'tib ketgan bo'lishi mumkin
                continue
            slots.append(slot)

    if not slots:
        raise ValidationError(_("Berilgan parametrlar bo'yicha hech qanday dars yaratilmaydi."))

    existing = list(Lesson.objects.filter(
        course__teacher=teacher,
        status__in=[Lesson.Status.SCHEDULED, Lesson.Status.LIVE],
        starts_at__range=(slots[0] - timedelta(hours=24), slots[-1] + timedelta(minutes=duration_min)),
    ).values('title', 'course__title', 'starts_at', 'duration_min'))

    conflicts = []
    for new_start in slots:
        new_end = new_start + timedelta(minutes=duration_min)
        for ex in existing:
            ex_end = ex['starts_at'] + timedelta(minutes=ex['duration_min'])
            if ex['starts_at'] < new_end and ex_end > new_start:
                conflicts.append({
                    'date': new_start.strftime('%Y-%m-%d'),
                    'time': f"{new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')}",
                    'existing': ex['title'] or ex['course__title'],
                })
                break

    if conflicts:
        raise ValidationError({'conflicts': conflicts})

    series_id = uuid.uuid4()  # bitta seriyadagi darslarni bog'laydi: butun seriyani tahrirlash/bekor qilish uchun
    recurrence = {'freq': 'weekly', 'weeks': weeks, 'weekdays': sorted(set(days))}
    lessons = Lesson.objects.bulk_create([
        Lesson(
            course=course, title=title, note=note or '', starts_at=s, duration_min=duration_min,
            room_name=f'lesson-{uuid.uuid4().hex[:12]}', recurrence=recurrence, recurrence_id=series_id,
        )
        for s in slots
    ])
    audit.record(
        action='lesson.schedule_recurring', actor=teacher, target=course,
        meta={'count': len(lessons), 'weeks': weeks, 'days': days, 'note': note},
        request=request,
    )
    return lessons


# ---------------------------------------------------------------------------
# Taklif havolasi: o'qituvchi havola yaratadi, o'quvchi kod bilan qo'shiladi
# ---------------------------------------------------------------------------
INVITE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # chalkash belgilar (0/O, 1/I) yo'q


def _invite_dict(course: Course) -> dict:
    if not course.invite_code:
        return {'code': None, 'url': None, 'expires_at': None, 'require_approval': course.invite_requires_approval}
    base = getattr(settings, 'INVITE_BASE_URL', '').rstrip('/')
    return {
        'code': course.invite_code, 'url': f'{base}/j/{course.invite_code}',
        'expires_at': course.invite_expires_at, 'require_approval': course.invite_requires_approval,
    }


def _owned_course(user: User, course: Course) -> Course:
    if course.teacher_id != user.id:
        raise PermissionDenied(_("Taklif havolasini faqat kurs o'qituvchisi boshqaradi."))
    return course


def get_invite_link(*, teacher: User, course: Course) -> dict:
    return _invite_dict(_owned_course(teacher, course))


def create_invite_link(*, teacher: User, course: Course, require_approval=None, expires_in_days=None, request=None) -> dict:
    """Yangi havola yaratadi (eskisi bekor bo'ladi). `require_approval` — qo'shilganlar o'qituvchi tasdig'ini kutadi;
    `expires_in_days` — muddat (bo'sh = muddatsiz)."""
    import secrets
    from datetime import timedelta

    _owned_course(teacher, course)
    if expires_in_days not in (None, ''):
        try:
            days = int(expires_in_days)
        except (TypeError, ValueError):
            raise ValidationError({'expires_in_days': _("Son bo'lishi kerak.")}) from None
        if not 1 <= days <= 365:
            raise ValidationError({'expires_in_days': _('1 dan 365 kungacha.')})
        course.invite_expires_at = timezone.now() + timedelta(days=days)
    else:
        course.invite_expires_at = None
    if require_approval is not None:
        course.invite_requires_approval = bool(require_approval)
    while True:
        code = ''.join(secrets.choice(INVITE_ALPHABET) for _unused in range(6))
        if not Course.objects.filter(invite_code=code).exists():
            break
    course.invite_code = code
    course.save(update_fields=['invite_code', 'invite_expires_at', 'invite_requires_approval', 'updated_at'])
    audit.record(action='course.invite_link_create', actor=teacher, target=course, request=request)
    return _invite_dict(course)


def revoke_invite_link(*, teacher: User, course: Course, request=None) -> None:
    _owned_course(teacher, course)
    if course.invite_code:
        course.invite_code = None
        course.invite_expires_at = None
        course.save(update_fields=['invite_code', 'invite_expires_at', 'updated_at'])
        audit.record(action='course.invite_link_revoke', actor=teacher, target=course, request=request)


@transaction.atomic
def join_by_code(*, student: User, code: str, request=None) -> dict:
    """O'quvchi kod bilan guruhga qo'shiladi: `{course_id, status: joined | pending}`."""
    if student.role != User.Role.STUDENT:
        raise PermissionDenied(_("Havola orqali faqat o'quvchi qo'shiladi."))
    code = (code or '').strip().upper()
    course = Course.objects.filter(invite_code=code, is_active=True).select_related('teacher').first() if code else None
    if course is None:
        raise NotFound(_('Taklif havolasi topilmadi yoki bekor qilingan.'))
    if course.invite_expires_at and course.invite_expires_at < timezone.now():
        raise ValidationError({'detail': _('Taklif havolasining muddati tugagan.')})
    target = Enrollment.Status.PENDING if course.invite_requires_approval else Enrollment.Status.APPROVED
    enrollment, created = Enrollment.objects.get_or_create(course=course, student=student, defaults={'status': target})
    if enrollment.status == Enrollment.Status.DECLINED:
        raise PermissionDenied(_("Bu guruhga qo'shilish so'rovingiz rad etilgan."))
    if created:
        audit.record(
            action='course.join_by_link', actor=student, target=course,
            meta={'status': enrollment.status}, request=request,
        )
        _notify_joined(course, student, enrollment.status)
    return {
        'course_id': str(course.id),
        'status': 'joined' if enrollment.status == Enrollment.Status.APPROVED else 'pending',
    }


def _notify_joined(course: Course, student: User, status: str) -> None:
    """O'qituvchiga: "X guruhga qo'shildi" (yoki so'rov yubordi)."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    name = student.get_full_name() or student.username
    verb = "qo'shildi" if status == Enrollment.Status.APPROVED else "qo'shilish so'rovini yubordi"
    try:
        send_notification(
            sender=student, target_type=Notification.Target.USER, user_id=course.teacher_id, kind='member_joined',
            description=f'{name} «{course.title}» guruhiga havola orqali {verb}.',
            link_type='course', link_id=str(course.id),
        )
    except Exception:  # noqa: BLE001 — bildirishnoma ixtiyoriy
        logging.getLogger('apps').warning('member_joined bildirishnomasi yuborilmadi', exc_info=True)


def _get_course(course_id) -> Course:
    try:
        return Course.objects.get(pk=course_id, is_active=True)
    except (Course.DoesNotExist, ValueError):
        raise NotFound(_('Kurs topilmadi.'))


def _resolve_student_ref(student_ref: str) -> User:
    """O'quvchini login yoki taklif kodi bo'yicha topadi (o'qituvchi biriktirishi uchun)."""
    student = User.objects.filter(role=User.Role.STUDENT, username=student_ref).first()
    if student is None:
        student = User.objects.filter(role=User.Role.STUDENT, invite_code=student_ref.upper()).first()
    if student is None:
        raise NotFound(_("Bunday login yoki taklif kodli o'quvchi topilmadi."))
    return student


def _resolve_enroll_target(*, course: Course, by_user: User, student_id=None, student_ref=None) -> User:
    """Kimni yozish/chiqarish mumkinligini aniqlaydi — enroll va unenroll uchun bitta qoida."""
    if by_user.role == User.Role.STUDENT:
        return by_user
    if by_user.role == User.Role.PARENT:
        if not student_id or not account_selectors.is_linked(by_user, student_id):
            raise PermissionDenied(_("Bu o'quvchi sizga bog'lanmagan."))
        return User.objects.get(pk=student_id)
    if by_user.role == User.Role.TEACHER:
        if course.teacher_id != by_user.id:
            raise PermissionDenied(_("Faqat o'z kursingizga o'quvchi biriktira olasiz."))
        if student_id:
            try:
                return User.objects.get(pk=student_id, role=User.Role.STUDENT)
            except (User.DoesNotExist, ValueError):
                raise NotFound(_("O'quvchi topilmadi."))
        if not student_ref:
            raise NotFound(_("O'quvchi login yoki taklif kodini kiriting."))
        return _resolve_student_ref(student_ref)
    raise PermissionDenied(_("Faqat o'quvchi, ota-ona yoki kurs o'qituvchisi yoza oladi."))


@transaction.atomic
def enroll(*, course_id, by_user: User, student_id=None, student_ref=None, request=None) -> tuple[Enrollment, bool]:
    """O'quvchi/ota-ona yozilish SO'ROVI yuboradi (pending), o'qituvchi o'z kursiga
    biriktirsa darhol tasdiqlanadi. O'quvchi darsga faqat APPROVED bo'lgach kiradi."""
    course = _get_course(course_id)
    student = _resolve_enroll_target(
        course=course, by_user=by_user, student_id=student_id, student_ref=student_ref,
    )
    target_status = (
        Enrollment.Status.APPROVED if by_user.role == User.Role.TEACHER
        else Enrollment.Status.PENDING
    )
    enrollment, created = Enrollment.objects.get_or_create(
        course=course, student=student, defaults={'status': target_status},
    )
    if not created and enrollment.status != Enrollment.Status.APPROVED and enrollment.status != target_status:
        # rad etilgan so'rov qayta yuborilsa yana pending; o'qituvchi biriktirsa approved
        enrollment.status = target_status
        enrollment.save(update_fields=['status'])
    if created:
        audit.record(
            action='course.enroll', actor=by_user, target=course,
            meta={'student_id': str(student.id), 'status': enrollment.status}, request=request,
        )
    return enrollment, created


@transaction.atomic
def respond_enrollment(*, teacher: User, enrollment_id, action: str, request=None) -> Enrollment:
    """O'qituvchi yozilish so'rovini tasdiqlaydi yoki rad etadi."""
    try:
        enrollment = Enrollment.objects.select_related('course').get(pk=enrollment_id)
    except (Enrollment.DoesNotExist, ValueError):
        raise NotFound(_("So'rov topilmadi."))
    if enrollment.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi so'rovga javob beradi."))
    if action not in ('approve', 'decline'):
        raise NotFound(_("Amal noto'g'ri: approve yoki decline."))
    enrollment.status = (
        Enrollment.Status.APPROVED if action == 'approve' else Enrollment.Status.DECLINED
    )
    enrollment.save(update_fields=['status'])
    audit.record(
        action=f'course.enroll_{action}', actor=teacher, target=enrollment.course,
        meta={'student_id': str(enrollment.student_id)}, request=request,
    )
    return enrollment


@transaction.atomic
def unenroll(*, course_id, by_user: User, student_id=None, request=None) -> bool:
    """Yozuvni bekor qilish — o'quvchi o'zini, ota-ona bolasini, o'qituvchi o'z kursidan chiqaradi."""
    course = _get_course(course_id)
    student = _resolve_enroll_target(course=course, by_user=by_user, student_id=student_id)
    deleted, _details = Enrollment.objects.filter(course=course, student=student).delete()
    if deleted:
        audit.record(
            action='course.unenroll', actor=by_user, target=course,
            meta={'student_id': str(student.id)}, request=request,
        )
        # Guruh chatidagi ALLAQACHON ochiq WebSocket ulanishi bo'lsa — o'zini
        # yopsin (ruxsat faqat yangi so'rovda tekshiriladi, ochiq soket buni
        # bilmaydi). Xato bo'lsa ham unenroll o'zi muvaffaqiyatli qolaveradi.
        try:
            from apps.chat import realtime as chat_realtime
            chat_realtime.broadcast_member_removed(course.id, student.id)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('member_removed broadcast failed')
    return bool(deleted)


@transaction.atomic
def delete_course(*, teacher: User, course: Course, request=None) -> None:
    """Guruhni (kursni) o'chiradi — barcha a'zolar chiqib ketadi, chat/doska/video
    ma'lumotlari BUTUNLAY o'chadi (fayllar diskdan ham). Davomat va baholar tarix
    sifatida saqlanadi — shu sabab Kurs/Dars o'zi faqat soft-delete qilinadi
    (Attendance/LessonRating shularga CASCADE FK bilan bog'langan)."""
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs egasi guruhni o'chira oladi."))

    lessons = list(course.lessons.all())
    lesson_ids = [lesson.id for lesson in lessons]

    # Jonli darslar bo'lsa — xonani to'xtatishga urinamiz (best-effort,
    # LiveKit muammosi o'chirishni to'xtatmasin). Yozuv endi brauzer-tomon
    # boshqariladi — bu yerda alohida to'xtatish shart emas.
    from apps.live import services as live_services
    for lesson in lessons:
        if lesson.status == Lesson.Status.LIVE:
            try:
                live_services.end_room(lesson=lesson)
            except Exception:  # noqa: BLE001
                import logging
                logging.getLogger('apps').exception('course delete: live room stop failed')

    # Video yozuvlar — fayl + baza yozuvi butunlay o'chadi
    from .models import LessonRecording
    for recording in LessonRecording.objects.filter(lesson_id__in=lesson_ids):
        remove_recording_files(recording)
        recording.delete()

    # Doska — chizmalar, chizish ruxsatlari, o'chirish jurnali + PDF fayllar
    from pathlib import Path

    from django.conf import settings as dj_settings

    from apps.board.models import BoardErase, BoardGrant, BoardSheet
    BoardSheet.objects.filter(lesson_id__in=lesson_ids).delete()
    BoardGrant.objects.filter(lesson_id__in=lesson_ids).delete()
    BoardErase.objects.filter(lesson_id__in=lesson_ids).delete()
    boards_dir = Path(dj_settings.BASE_DIR) / 'private' / 'boards'
    for lesson_id in lesson_ids:
        pdf_path = boards_dir / f'{lesson_id}.pdf'
        if pdf_path.exists():
            pdf_path.unlink()

    # Chat — guruh xonasi + barcha xabarlar (biriktirilgan fayllar diskdan ham) butunlay o'chadi
    from apps.chat.models import ChatRoom
    room = ChatRoom.objects.filter(kind=ChatRoom.Kind.COURSE, course=course).first()
    if room is not None:
        for msg in room.messages.exclude(file=''):
            msg.file.delete(save=False)
        room.delete()

    # A'zolik — barcha userlar guruhdan chiqib ketadi
    course.enrollments.all().delete()

    # Kurs/darslar — SOFT delete (Attendance/LessonRating tarixi saqlanishi uchun)
    course.lessons.update(is_deleted=True, deleted_at=timezone.now())
    course.delete()

    audit.record(
        action='course.delete', actor=teacher, target=course,
        meta={'lesson_count': len(lesson_ids)}, request=request,
    )


@transaction.atomic
def finish_lesson(*, teacher: User, lesson: Lesson, recording_title: str = '', request=None) -> Lesson:
    """Darsni yakunlash — davomatlar yopiladi, doska PDF chatga tushadi,
    video yozuv to'xtatilib O'QITUVCHI BERGAN NOM bilan guruh chatga e'lon qilinadi."""
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat o'qituvchi darsni tugata oladi."))
    lesson.status = Lesson.Status.FINISHED
    lesson.save(update_fields=['status'])
    lesson.attendances.filter(left_at__isnull=True).update(left_at=timezone.now())
    # Guruh chatga "jonli dars tugadi" signali (Telegram uslubidagi chiziq yo'qoladi)
    try:
        from apps.chat import realtime as chat_realtime
        chat_realtime.broadcast_lesson_ended(lesson)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('lesson_ended broadcast failed')
    # Doska lentasi -> PDF -> guruh chat (EduTech.docx). Xato yakunlashni to'xtatmaydi.
    try:
        from apps.board import services as board_services
        board_services.publish_board_pdf(lesson)
    except Exception:  # noqa: BLE001 — PDF muammosi dars yakunidan muhimroq emas
        import logging
        logging.getLogger('apps').exception('board pdf publish failed')
    # Video yozuv nomi: o'qituvchi bergan nomni saqlab qo'yamiz — brauzer
    # video/audio yuklashni HALI tugatmagan bo'lishi mumkin (chunked
    # upload + birlashtirish asinxron davom etadi), shuning uchun guruh
    # chatga e'lon BU YERDA emas, balki fayl haqiqatan tayyor bo'lgan
    # paytda (apps.live.services.maybe_start_merge/finalize_single_side
    # muvaffaqiyatli tugaganda) yuboriladi.
    try:
        from .models import LessonRecording
        recording, _created = LessonRecording.objects.get_or_create(lesson=lesson)
        title = (recording_title or '').strip() or lesson.title or lesson.course.title
        recording.title = title[:200]
        recording.ended_at = timezone.now()
        recording.save(update_fields=['title', 'ended_at', 'updated_at'])
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('apps').exception('recording finalize failed')
    audit.record(action='lesson.finish', actor=teacher, target=lesson, request=request)
    return lesson


def auto_finish_expired_lessons(*, now=None) -> int:
    """HAQIQIY boshlangan vaqti (live_started_at + duration_min + 30 daqiqa
    grace) o'tib ketgan, lekin hali LIVE holatda qolib ketgan darslarni
    avtomatik yakunlaydi — o'qituvchi brauzeri yiqilib/ulanish uzilib,
    `lesson.finish` hech qachon chaqirilmagan holatlar uchun (masalan
    lesson-a9371dba4a2a kabi "stuck LIVE" darslar).

    DIQQAT (2026-09-04 tuzatildi): muddat REJALASHTIRILGAN `starts_at`dan
    emas, `live_started_at`dan hisoblanadi — o'qituvchi kech kirsa (masalan
    soat 15:00ga rejalashtirilgan, 15:45da kirgan), eski hisob-kitob darsni
    boshlangan zahoti "tugagan" deb topib, hali davom etayotgan safar
    o'rtada uzib qo'yardi (production'da kuzatilgan real bug).

    Davriy chaqirish uchun mo'ljallangan (management command + tashqi cron —
    loyihada Celery yo'q, xuddi send_deadline_reminders kabi). Video xonasi
    ham bir vaqtda o'chiriladi (apps.live.services.end_room) — faqat status
    emas, ishtirokchilar ham chiqarib yuboriladi.

    DIQQAT (2026-09-05 topilgan, production): `finish_lesson` o'zi yozuvni
    FINALIZE qilmaydi — bu odatda frontend'ning alohida
    `finalize_recording_video`/`finalize_recording_audio` so'rovlariga
    bog'liq, ular esa faqat o'qituvchi QO'LDA "Yakunlash"ni bosgan yo'ldan
    yuboriladi. O'qituvchi shu yerga — auto-finish yo'liga — tushib qolgan
    bo'lsa (frontend hech qachon "Yakunlash"ni chaqirmagan), o'sha
    so'rovlar HECH QACHON kelmaydi va yozuv abadiy "recording" holatida
    qotib qolardi, dars "finished" bo'lganidan keyin ham. Shuning uchun
    bu yerda `_ensure_recording_finalized` orqali mavjud bo'lgan
    bo'lak(lar) backend tomonidan o'zi finalize qilinadi.
    """
    now = now or timezone.now()
    finished = 0
    live_lessons = Lesson.objects.filter(status=Lesson.Status.LIVE).select_related('course', 'course__teacher')
    for lesson in live_lessons:
        if lesson.live_started_at:
            # Haqiqiy boshlangan vaqtdan hisoblanadi (o'qituvchi kech kirgan
            # bo'lishi mumkin) + 30 daqiqa "grace" — bu ish faqat chindan
            # OSILIB QOLGAN darslarni tozalash uchun, hali davom etayotgan
            # (rejalashtirilgandan uzoqroq cho'zilgan) darsni to'xtatmasin.
            ends_at = lesson.live_started_at + timedelta(minutes=lesson.duration_min + 30)
        else:
            # Hech qachon jonli bo'lmagan (lekin nima uchundir LIVE holatda
            # qolib ketgan) eski yozuvlar uchun zaxira — eski xatti-harakat.
            ends_at = lesson.starts_at + timedelta(minutes=lesson.duration_min)
        if now < ends_at:
            continue
        finish_lesson(teacher=lesson.course.teacher, lesson=lesson)
        try:
            _ensure_recording_finalized(lesson)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('auto_finish_expired_lessons: recording finalize failed')
        try:
            from apps.live import services as live_services
            live_services.end_room(lesson)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger('apps').exception('auto_finish_expired_lessons: end_room failed')
        finished += 1
    return finished


def _can_see_lesson(user: User, lesson: Lesson) -> bool:
    return lessons_visible_to(user).filter(pk=lesson.pk).exists()


def lessons_visible_to(user: User):
    from . import selectors

    return selectors.lessons_for(user)


def set_lesson_reminder(*, user: User, lesson_id, minutes_before=None) -> ReminderPref:
    """"Eslatma qo'yish": shu dars boshlanishidan `minutes_before` (1-1440) daqiqa oldin shaxsiy bildirishnoma."""
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))
    if not _can_see_lesson(user, lesson):
        raise NotFound(_('Dars topilmadi.'))
    if lesson.status != Lesson.Status.SCHEDULED:
        raise ValidationError({'detail': _("Faqat boshlanmagan darsga eslatma qo'yiladi.")})
    minutes = _reminder_minutes(minutes_before, user)
    pref, _created = ReminderPref.objects.update_or_create(
        user=user, kind=ReminderPref.Kind.LESSON, target_id=lesson.id, defaults={'minutes_before': minutes, 'sent_at': None},
    )
    return pref


def _reminder_minutes(value, user: User) -> int:
    if value in (None, ''):
        return user.lesson_reminder_minutes or 15
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise ValidationError({'minutes_before': _("Daqiqa son bo'lishi kerak.")})
    if not 1 <= minutes <= 1440:
        raise ValidationError({'minutes_before': _("1 dan 1440 gacha (24 soat).")})
    return minutes


def clear_reminder(*, user: User, kind: str, target_id) -> None:
    ReminderPref.objects.filter(user=user, kind=kind, target_id=target_id).delete()


def send_personal_reminders(*, now=None) -> int:
    """Shaxsiy eslatmalar (dars va imtihon): vaqti kelganlarini yuboradi (bir marta — `sent_at`)."""
    from apps.exams.models import Exam
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    now = now or timezone.now()
    sent = 0
    due = ReminderPref.objects.filter(sent_at__isnull=True).select_related('user')
    for pref in due:
        if pref.kind == ReminderPref.Kind.LESSON:
            target = Lesson.objects.filter(pk=pref.target_id, status=Lesson.Status.SCHEDULED).select_related('course').first()
            title, link, kind = (target.title or target.course.title) if target else '', 'lesson', 'lesson_reminder'
            sender = target.course.teacher if target else None
        else:
            target = Exam.objects.filter(pk=pref.target_id).select_related('course').first()
            title, link, kind = target.title if target else '', 'exam', 'exam_reminder'
            sender = target.course.teacher if target else None
        starts_at = target.starts_at if target else None
        if target is None or starts_at <= now:
            ReminderPref.objects.filter(pk=pref.pk).delete()  # dars/imtihon o'tib ketgan, bekor yoki o'chirilgan
            continue
        if now < starts_at - timedelta(minutes=pref.minutes_before):
            continue
        send_notification(
            sender=sender, description=f'«{title}» {pref.minutes_before} daqiqadan keyin boshlanadi.',
            target_type=Notification.Target.USER, user_id=pref.user_id, kind=kind, link_type=link, link_id=str(pref.target_id),
        )
        ReminderPref.objects.filter(pk=pref.pk).update(sent_at=now)
        sent += 1
    return sent


def send_lesson_reminders(*, now=None) -> int:
    """"Dars N daqiqadan keyin boshlanadi" bildirishnomasi — o'qituvchi va
    kursga APPROVED yozilgan har bir o'quvchi uchun, har biri o'zining
    `User.lesson_reminder_minutes` sozlamasiga ko'ra (standart — 15 daqiqa).

    Davriy chaqirish uchun (management command + tashqi cron, har daqiqada —
    boshqa davriy vazifalardan farqli, bu yerda vaqt aniqligi muhim, 10
    daqiqalik oraliq eslatmani 5-15 daqiqa orasida noaniq qilib qo'yardi).
    Har (dars, foydalanuvchi) juftligiga faqat bir marta — `LessonReminder`
    bilan belgilanadi.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    now = now or timezone.now()
    # Sozlama foydalanuvchiga xos bo'lgani uchun, oldindan "qancha vaqt oldin"
    # ekanini bilmaymiz — oqilona yuqori chegara (eng uzoq real sozlamani
    # ham qamrab oladi), har juftlik uchun aniq chegara alohida tekshiriladi.
    upper_bound = now + timedelta(hours=24)
    lessons = (
        Lesson.objects.filter(
            status=Lesson.Status.SCHEDULED, starts_at__gt=now, starts_at__lte=upper_bound,
        )
        .select_related('course', 'course__teacher')
    )
    sent = 0
    personal = set(ReminderPref.objects.filter(
        kind=ReminderPref.Kind.LESSON, target_id__in=[lesson.id for lesson in lessons],
    ).values_list('target_id', 'user_id'))
    for lesson in lessons:
        participants = [lesson.course.teacher] + list(
            User.objects.filter(
                enrollments__course=lesson.course, enrollments__status=Enrollment.Status.APPROVED,
            )
        )
        for user in participants:
            if (lesson.id, user.id) in personal:
                continue  # shaxsiy eslatma shu dars uchun umumiy sozlamani almashtiradi (pastda yuboriladi)
            remind_at = lesson.starts_at - timedelta(minutes=user.lesson_reminder_minutes)
            if now < remind_at or LessonReminder.objects.filter(lesson=lesson, user=user).exists():
                continue
            send_notification(
                sender=lesson.course.teacher,
                description=(
                    f'«{lesson.title or lesson.course.title}» darsi '
                    f'{user.lesson_reminder_minutes} daqiqadan keyin boshlanadi.'
                ),
                target_type=Notification.Target.USER, user_id=user.id,
                kind='lesson_reminder', link_type='lesson', link_id=str(lesson.id),
            )
            LessonReminder.objects.create(lesson=lesson, user=user)
            sent += 1
    return sent + send_personal_reminders(now=now)


def _ensure_recording_finalized(lesson: Lesson) -> None:
    """`auto_finish_expired_lessons` darsni majburan yakunlaganda chaqiriladi.

    Oddiy yo'lda (o'qituvchi qo'lda "Yakunlash"ni bosganda) frontend
    darsni tugatgandan keyin ikkita alohida so'rov yuboradi:
    `finalize_recording_video` va `finalize_recording_audio`. Shu yerga —
    auto-finish yo'liga — tushgan darsda bu so'rovlar HECH QACHON
    kelmaydi (frontend bu holatdan bexabar), shuning uchun mavjud bo'lgan
    video/audio bo'lak(lar)ini backend o'zi "tayyor" deb belgilaydi va
    birlashtirishni (yoki bitta tomon bilan yakunlashni) ishga tushiradi —
    frontend signaliga umuman bog'liq qolmasdan."""
    from django.conf import settings

    from apps.live import services as live_services

    from .models import LessonRecording

    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None:
        return
    if recording.video_file_name and not recording.video_ready_at:
        recording.video_ready_at = timezone.now()
        recording.save(update_fields=['video_ready_at', 'updated_at'])
    if recording.audio_file_name and not recording.audio_finalized_at:
        recording.audio_finalized_at = timezone.now()
        recording.save(update_fields=['audio_finalized_at', 'updated_at'])
    if not settings.RECORDINGS_LOCAL:
        return  # fayllar boshqa serverda — birlashtirishni o'sha yerdagi `recover_recordings` bajaradi
    live_services.maybe_start_merge(lesson.id)
    live_services.finalize_single_side(lesson.id)


@transaction.atomic
def mark_joined(*, lesson: Lesson, student: User) -> Attendance:
    attendance, _created = Attendance.objects.get_or_create(lesson=lesson, student=student)
    if attendance.joined_at is None:
        attendance.joined_at = timezone.now()
        attendance.save(update_fields=['joined_at'])
    return attendance


@transaction.atomic
def mark_left(*, lesson_id, student: User) -> bool:
    updated = Attendance.objects.filter(
        lesson_id=lesson_id, student=student, left_at__isnull=True
    ).update(left_at=timezone.now())
    return bool(updated)


# ── Dars video yozuvi: ko'rish/oqim/o'chirish (faqat platforma ichida) ──────
# EduTech.docx: yozuv faqat platformada ochiladi — yuklab olib bo'lmaydi.
# Himoya: auth bilan beriladigan MUDDATLI imzolangan stream havolasi (3 soat),
# Content-Disposition: inline (pleer ochadi, "saqlash" taklif qilinmaydi),
# doimiy/ochiq URL yo'q.

RECORDING_STREAM_MAX_AGE = 3 * 60 * 60  # imzolangan havola muddati (sekund)


def _can_view_lesson(user: User, lesson: Lesson) -> bool:
    if lesson.course.teacher_id == user.id:
        return True
    if Enrollment.objects.filter(
        course=lesson.course, student=user, status=Enrollment.Status.APPROVED,
    ).exists():
        return True
    from apps.accounts.models import ParentChildLink
    child_ids = ParentChildLink.objects.filter(
        parent=user, status=ParentChildLink.Status.APPROVED,
    ).values_list('student_id', flat=True)
    return Enrollment.objects.filter(
        course=lesson.course, student_id__in=child_ids,
        status=Enrollment.Status.APPROVED,
    ).exists()


def _recording_path(recording):
    """Ijro etiladigan fayl: tayyor MP4 nusxa bo'lsa — shu (asl WebM `prune_recordings` bilan o'chirilgan bo'lishi mumkin),
    aks holda asl fayl."""
    from django.conf import settings
    if recording.mp4_file_name:
        mp4_path = settings.RECORDINGS_DIR / recording.mp4_file_name
        if mp4_path.exists():
            return mp4_path
    return settings.RECORDINGS_DIR / recording.file_name


def remove_recording_files(recording) -> None:
    """Yozuvning BARCHA fayllarini (yakuniy WebM, MP4/M4A nusxa, xom video va audio qismlar) diskdan o'chiradi."""
    from django.conf import settings
    for name in (recording.file_name, recording.mp4_file_name, recording.video_file_name, recording.audio_file_name):
        if name:
            (settings.RECORDINGS_DIR / name).unlink(missing_ok=True)


def _one_side_stale(recording, *, wait=timedelta(minutes=2)) -> bool:
    """Video YOKI audiodan bittasi tayyor, ikkinchisi belgilangan vaqtdan
    beri kelmagan bo'lsa — True (finalize_single_side chaqirilishi kerak).
    Ikkalasi ham hali yo'q, yoki ikkalasi ham tayyor bo'lsa — False
    (bu holatlar boshqa yo'l bilan hal qilinadi)."""
    if recording.video_ready_at and not recording.audio_finalized_at:
        return timezone.now() - recording.video_ready_at > wait
    if recording.audio_finalized_at and not recording.video_ready_at:
        return timezone.now() - recording.audio_finalized_at > wait
    return False


def _recording_stats(lesson: Lesson) -> dict:
    """Dars yozuvi ekranidagi kartalar: ishtirokchilar (qatnashgan o'quvchilar), davomat foizi, doska sahifalari."""
    attended = Attendance.objects.filter(lesson=lesson, joined_at__isnull=False).count()
    enrolled = Enrollment.objects.filter(course=lesson.course, status=Enrollment.Status.APPROVED).count()
    pages = sum(1 for sheet in lesson.board_sheets.all() if sheet.strokes)
    return {
        'participants_count': attended,
        'attendance_rate': round(attended * 100 / enrolled) if enrolled else 0,
        'board_pages': pages,
    }


def _board_extras(lesson: Lesson, recording) -> dict:
    """Yozuv sahifasi uchun doska ma'lumotlari: `chapters` (doska sahifasi almashgan vaqtlar), `board_page_previews`
    (sahifalarning kichik rasmlari — imzolangan muddatli havola), `pdf_url` (bo'sh bo'lmasa)."""
    from django.core import signing

    sheets = [s for s in lesson.board_sheets.order_by('index') if s.strokes]
    if not sheets:
        return {'chapters': [], 'board_page_previews': [], 'pdf_url': None}
    started = recording.video_started_at or recording.audio_started_at or lesson.live_started_at or recording.created_at
    token = signing.TimestampSigner(salt='board-preview').sign(str(lesson.id))
    chapters, previews = [], []
    for position, sheet in enumerate(sheets):
        seconds = 0 if position == 0 else max(0, int((sheet.created_at - started).total_seconds()))
        chapters.append({'seconds': seconds, 'title': sheet.title or f'Doska {sheet.index + 1}'})
        previews.append({
            'page': sheet.index + 1, 'title': sheet.title,
            'image_url': f'/api/v1/lessons/{lesson.id}/board/preview/{sheet.index}/?t={token}',
        })
    return {'chapters': chapters, 'board_page_previews': previews, 'pdf_url': f'/api/v1/board/{lesson.id}/pdf/'}


def board_preview_png(*, lesson: Lesson, index: int, token: str) -> bytes:
    """Imzolangan token bilan doska sahifasining PNG rasmi (kengligi 640 px)."""
    import io

    from django.core import signing

    from apps.board.render import render_sheet

    try:
        value = signing.TimestampSigner(salt='board-preview').unsign(token, max_age=RECORDING_STREAM_MAX_AGE)
    except signing.BadSignature:
        raise PermissionDenied(_('Havola yaroqsiz yoki muddati tugagan.'))
    if value != str(lesson.id):
        raise PermissionDenied(_('Havola boshqa darsga tegishli.'))
    sheet = lesson.board_sheets.filter(index=index).first()
    if sheet is None or not sheet.strokes:
        raise NotFound(_('Sahifa topilmadi.'))
    image = render_sheet(sheet.strokes).convert('RGB')
    image.thumbnail((640, 360))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def lesson_conflicts(*, teacher: User, start, duration, exclude=None) -> dict:
    """O'qituvchining berilgan vaqt oralig'iga (`start` dan `duration` daqiqa) to'g'ri keladigan boshqa darslari.
    Bekor qilingan/tugagan darslar hisobga olinmaydi."""
    from datetime import timedelta

    from django.utils.dateparse import parse_datetime

    moment = parse_datetime(str(start or ''))
    if moment is None:
        raise ValidationError({'start': _("Noto'g'ri vaqt (ISO ko'rinishida bo'lishi kerak).")})
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    try:
        minutes = int(duration if duration not in (None, '') else 45)
    except (TypeError, ValueError):
        raise ValidationError({'duration': _("Butun son bo'lishi kerak.")}) from None
    if not 1 <= minutes <= 24 * 60:
        raise ValidationError({'duration': _("1 dan 1440 daqiqagacha bo'lishi kerak.")})
    end = moment + timedelta(minutes=minutes)
    # Dars davomiyligi bazada daqiqa (butun son) — kesishishni Python'da tekshiramiz; bazadan faqat mumkin bo'lgan
    # oynadagilar olinadi (bir dars sutkadan uzoq bo'lmaydi)
    rows = Lesson.objects.filter(
        course__teacher=teacher, status__in=(Lesson.Status.SCHEDULED, Lesson.Status.LIVE),
        starts_at__lt=end, starts_at__gt=moment - timedelta(days=1),
    ).select_related('course')
    if exclude:
        rows = rows.exclude(pk=exclude) if _is_uuid_text(exclude) else rows
    lessons = [
        {'id': str(row.id), 'title': row.title, 'course': str(row.course_id), 'course_title': row.course.title,
         'starts_at': row.starts_at, 'duration_min': row.duration_min}
        for row in rows.order_by('starts_at') if row.starts_at + timedelta(minutes=row.duration_min) > moment
    ]
    return {'has_conflict': bool(lessons), 'lessons': lessons}


def _is_uuid_text(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def share_recording(*, teacher: User, lesson: Lesson):
    """Tayyor dars yozuvini guruh chatiga yuboradi. Qaytaradi: chat xabari."""
    from .models import LessonRecording

    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi yozuvni chatga yuboradi."))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None or recording.status != LessonRecording.Status.COMPLETED:
        raise ValidationError({'detail': _("Yozuv hali tayyor emas.")})
    return publish_recording_message(lesson, recording.title or lesson.title or lesson.course.title)


def recording_info(*, user: User, lesson: Lesson) -> dict:
    """Yozuv holati + tayyor bo'lsa muddatli stream havolasi."""
    from django.core import signing

    from .models import LessonRecording

    if not _can_view_lesson(user, lesson):
        raise PermissionDenied(_("Bu dars yozuvini ko'rish huquqingiz yo'q."))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None:
        raise NotFound(_("Bu darsda video yozuv yo'q."))

    from datetime import timedelta

    # Fayl diskka tushgan bo'lsa — tayyor deb belgilaymiz
    path = _recording_path(recording) if recording.file_name else None
    file_ready = bool(path and path.exists() and path.stat().st_size > 0)
    in_progress = recording.status in (
        LessonRecording.Status.PENDING, LessonRecording.Status.RECORDING,
        LessonRecording.Status.MERGING,
    )
    if file_ready and in_progress and lesson.status == Lesson.Status.FINISHED:
        recording.status = LessonRecording.Status.COMPLETED
        recording.save(update_fields=['status', 'updated_at'])
    elif (
        in_progress and lesson.status == Lesson.Status.FINISHED and not file_ready
        and _one_side_stale(recording)
    ):
        # Video YOKI audiodan faqat bittasi keldi, ikkinchisi 2 daqiqadan
        # beri kelmadi (masalan o'qituvchi brauzeri yopilib qoldi) —
        # butun yozuvni yo'qotmaslik uchun MAVJUD tomon bilan yakunlaymiz.
        from apps.live import services as live_services
        live_services.finalize_single_side(lesson.id)
        recording.refresh_from_db()
        path = _recording_path(recording) if recording.file_name else None
        file_ready = bool(path and path.exists() and path.stat().st_size > 0)
    elif in_progress and lesson.status == Lesson.Status.FINISHED and not file_ready:
        # Dars tugagan, video ham hali boshlanmagan/tayyor emas — yozuv
        # chiqmagan (masalan, xonada media bo'lmagan). Abadiy "yozilmoqda"
        # qolib ketmasin — halol failed holatiga o'tkazamiz.
        reference = recording.ended_at or recording.updated_at
        if reference and timezone.now() - reference > timedelta(minutes=3):
            recording.status = LessonRecording.Status.FAILED
            recording.error = (
                "Yozuv fayli yaratilmadi — darsda video/audio bo'lmagan "
                "bo'lishi mumkin."
            )
            recording.save(update_fields=['status', 'error', 'updated_at'])

    data = {
        'lesson_id': str(lesson.id),
        'title': recording.title or lesson.title or lesson.course.title,
        'status': recording.status,
        'ready': file_ready,
        'created_at': recording.created_at,
        'ended_at': recording.ended_at,
        'error': recording.error,
        'stream_url': None,
        'thumbnail_url': None,
        **_recording_stats(lesson),
        **_board_extras(lesson, recording),
    }
    previews = data.get('board_page_previews') or []
    data['thumbnail_url'] = previews[0].get('image_url') if previews else None  # video muqovasi: doskaning birinchi sahifasi
    if file_ready:
        # Imzolangan, muddatli havola — <video src> uchun (headerlarsiz),
        # 3 soatdan keyin yaroqsiz. Foydalanuvchi tekshiruvi SHU yerda bo'ldi.
        token = signing.TimestampSigner().sign(str(lesson.id))
        data['stream_url'] = f'/api/v1/lessons/{lesson.id}/recording/stream/?t={token}'
    return data


def recording_stream_path(*, lesson: Lesson, token: str):
    """Imzolangan tokenni tekshirib fayl yo'lini qaytaradi (stream view uchun)."""
    from django.core import signing

    from .models import LessonRecording

    try:
        value = signing.TimestampSigner().unsign(token, max_age=RECORDING_STREAM_MAX_AGE)
    except signing.BadSignature:
        raise PermissionDenied(_('Havola yaroqsiz yoki muddati tugagan.'))
    if value != str(lesson.id):
        raise PermissionDenied(_('Havola boshqa darsga tegishli.'))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None or not recording.file_name:
        raise NotFound(_("Yozuv topilmadi."))
    path = _recording_path(recording)  # iOS ham ochadigan MP4 nusxa tayyor bo'lsa — shu (WebM iOS'da ochilmaydi)
    if not path.exists():
        raise NotFound(_("Yozuv fayli hali tayyor emas."))
    return path


def delete_recording(*, teacher: User, lesson: Lesson) -> None:
    """Faqat kurs o'qituvchisi. Fayllar (yakuniy + xom video/audio) ham,
    yozuv ham o'chadi."""
    from django.conf import settings

    from .models import LessonRecording

    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Yozuvni faqat kurs o'qituvchisi o'chira oladi."))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None:
        raise NotFound(_("Yozuv yo'q."))
    remove_recording_files(recording)
    recording.delete()


# ── Dars video+audio yozuvi — o'qituvchi brauzeridan chunked upload ────────
# EduTech optimallashtirish (2026-08-28, 2-bosqich): ikkalasi HAM
# o'qituvchi brauzeridan keladi — video `getDisplayMedia` orqali ekranning
# o'zi ("print screen" kabi — kim gapirsa, kim ekran ulashsa, kim
# kamerasini yoqsa, hammasi tabiiy ko'rinadi), audio esa Web Audio API
# orqali barcha ishtirokchilar ovozi ichkarida aralashtiriladi. Ikkalasi
# ham bo'lak-bo'lak (30-60s) yuboriladi — server deyarli CPU sarflamaydi
# (faqat diskka yozish). Ikkalasi tayyor bo'lgach
# `apps.live.services.maybe_start_merge` fon jarayonida ffmpeg bilan
# birlashtiradi; faqat bittasi kelsa (ikkinchisi hech qachon kelmasa),
# `finalize_single_side` mavjud bo'lgani bilan yakunlaydi.

AUDIO_CHUNK_MAX_MB = 10  # 30-60s audio uchun me'yordan ancha katta — xato/suiiste'moldan himoya
VIDEO_CHUNK_MAX_MB = 50  # 30-60s ekran video uchun me'yordan ancha katta


def _append_chunk(*, kind: str, teacher: User, lesson: Lesson, chunk, started_at, session, index) -> bool:
    """Audio/video bo'lagini yozuv fayliga qo'shib boradi. `kind` — 'audio' | 'video'.

    Takror yuborishdan himoya: brauzer `session` (yozuv sessiyasi id'si) va `index` (shu sessiyadagi 0 dan boshlanuvchi
    tartib raqami) yuborsa, allaqachon yozilgan raqam (`index < kutilgan`) qayta YOZILMAYDI — javob yo'qolib qayta
    yuborilgan bo'lak faylni buzmaydi. Yangi `session` (sahifa qayta ochilgan, yozuv qayta boshlangan) — yangi hisob.
    Ikkalasi ham berilmasa (eski mijoz) — avvalgidek shunchaki qo'shiladi. Qator qulflanadi: bir vaqtda kelgan ikki so'rov
    fayl ichida aralashib ketmaydi. Qaytaradi: bo'lak yozildimi (False — takror edi)."""
    from django.conf import settings
    from django.db import transaction
    from django.utils.dateparse import parse_datetime

    from .models import LessonRecording

    label = {'audio': 'audio', 'video': 'video'}[kind]
    max_mb = AUDIO_CHUNK_MAX_MB if kind == 'audio' else VIDEO_CHUNK_MAX_MB
    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi %(what)s yuklashi mumkin.") % {'what': label})
    if chunk.size > max_mb * 1024 * 1024:
        raise ValidationError({'chunk': _("Bo'lak %(max_mb)s MB dan katta.") % {'max_mb': max_mb}})
    session = (session or '').strip()[:64]
    if index is not None:
        try:
            index = int(index)
        except (TypeError, ValueError):
            raise ValidationError({'index': _("Butun son bo'lishi kerak.")}) from None
        if index < 0:
            raise ValidationError({'index': _("Manfiy bo'lishi mumkin emas.")})

    file_field, started_field = f'{kind}_file_name', f'{kind}_started_at'
    session_field, next_field = f'{kind}_session', f'{kind}_next_index'
    with transaction.atomic():
        recording, _created = LessonRecording.objects.select_for_update().get_or_create(lesson=lesson)
        fields = []
        if not getattr(recording, file_field):
            parsed = parse_datetime(started_at) if started_at else None
            if parsed and timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, dt_timezone.utc)
            setattr(recording, file_field, f'{lesson.room_name}-{kind}.webm')
            setattr(recording, started_field, parsed or timezone.now())
            fields += [file_field, started_field]
            if recording.status == LessonRecording.Status.PENDING:
                recording.status = LessonRecording.Status.RECORDING
                fields.append('status')
        if session and index is not None:
            if getattr(recording, session_field) == session:
                if index < getattr(recording, next_field):
                    return False  # allaqachon yozilgan bo'lak qayta kelgan — jim o'tkazamiz
            else:
                setattr(recording, session_field, session)
                fields.append(session_field)
            setattr(recording, next_field, index + 1)
            fields.append(next_field)
        if fields:
            recording.save(update_fields=[*fields, 'updated_at'])
        path = settings.RECORDINGS_DIR / getattr(recording, file_field)
        with open(path, 'ab') as handle:
            for part in chunk.chunks():
                handle.write(part)
    return True


def upload_recording_audio_chunk(*, teacher: User, lesson: Lesson, chunk, started_at: str | None = None,
                                 session=None, index=None) -> bool:
    """Brauzerdan kelgan audio bo'lagini yozuv fayliga qo'shib boradi (format brauzer tomonidan belgilanadi, server
    hech narsani qayta kodlamaydi). `session`/`index` — takrorlanishdan himoya (qarang `_append_chunk`)."""
    return _append_chunk(
        kind='audio', teacher=teacher, lesson=lesson, chunk=chunk, started_at=started_at, session=session, index=index,
    )


def finalize_recording_audio(*, teacher: User, lesson: Lesson) -> None:
    """O'qituvchi 'audio yozuv tugadi' deb belgilaydi — video ham tayyor
    bo'lsa, fon jarayonida birlashtirish ishga tushadi."""
    from apps.live import services as live_services

    from .models import LessonRecording

    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi audio yozuvni yakunlashi mumkin."))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None or not recording.audio_file_name:
        raise ValidationError(_('Bu darsga audio yuklanmagan.'))
    recording.audio_finalized_at = timezone.now()
    recording.save(update_fields=['audio_finalized_at', 'updated_at'])
    live_services.maybe_start_merge(lesson.id)


def upload_recording_video_chunk(*, teacher: User, lesson: Lesson, chunk, started_at: str | None = None,
                                 session=None, index=None) -> bool:
    """Brauzerdan (ekran/`getDisplayMedia`) kelgan video bo'lagini yozuv fayliga qo'shib boradi —
    `upload_recording_audio_chunk` bilan bir xil naqsh va himoya."""
    return _append_chunk(
        kind='video', teacher=teacher, lesson=lesson, chunk=chunk, started_at=started_at, session=session, index=index,
    )


def finalize_recording_video(*, teacher: User, lesson: Lesson) -> None:
    """O'qituvchi 'video yozuv tugadi' deb belgilaydi — audio ham tayyor
    bo'lsa, fon jarayonida birlashtirish ishga tushadi."""
    from apps.live import services as live_services

    from .models import LessonRecording

    if lesson.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi video yozuvni yakunlashi mumkin."))
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is None or not recording.video_file_name:
        raise ValidationError(_('Bu darsga video yuklanmagan.'))
    recording.video_ready_at = timezone.now()
    recording.save(update_fields=['video_ready_at', 'updated_at'])
    live_services.maybe_start_merge(lesson.id)


def publish_recording_message(lesson: Lesson, title: str):
    """Dars tugagach guruh chatga yozuv havolasini tashlaydi (board PDF uslubi)."""
    from django.db import transaction

    from apps.chat import realtime
    from apps.chat import services as chat_services
    from apps.chat.models import Message

    room = chat_services.ensure_course_room(lesson.course)
    message = Message.objects.create(
        room=room,
        sender=lesson.course.teacher,
        text=(
            f'🎥 "{title}" — dars video yozuvi tayyor!\n'
            f"Ko'rish (faqat platformada): /recordings/{lesson.id}"
        ),
        kind=Message.Kind.SYSTEM,
        system_key='recording_ready',
        system_params={'lesson_title': title, 'lesson_id': str(lesson.id)},
    )
    room.save(update_fields=['updated_at'])
    # send_message bilan bir xil: WebSocket'ga darhol tarqatamiz, aks holda
    # chat qayta ochilmaguncha (yoki sahifa yangilanmaguncha) ko'rinmay turadi.
    transaction.on_commit(lambda: realtime.broadcast_message(message))
    _notify_recording_ready(lesson, title)
    return message


def _notify_recording_ready(lesson: Lesson, title: str) -> None:
    """Yozuv tayyor bo'lganda guruh o'quvchilariga bildirishnoma ("Ochish" -> dars yozuvi sahifasi)."""
    import logging

    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    student_ids = list(lesson.course.enrollments.filter(status=Enrollment.Status.APPROVED).values_list('student_id', flat=True))
    if not student_ids:
        return
    try:
        send_notification(
            sender=lesson.course.teacher, description=_('Dars yozuvi tayyor: %(title)s') % {'title': title},
            target_type=Notification.Target.USERS, user_ids=student_ids, kind='recording_ready',
            link_type='recording', link_id=str(lesson.id),
        )
    except Exception:  # noqa: BLE001 — bildirishnoma xatosi yozuv e'lonini to'xtatmasin
        logging.getLogger('apps').exception('recording_ready notification failed')
