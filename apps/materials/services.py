import mimetypes
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Exists, OuterRef, Q
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment, Lesson

from .models import Material

MAX_SIZE_MB = 50
KINDS = {
    'pdf': {'.pdf'},
    'doc': {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.odt', '.csv'},
    'audio': {'.mp3', '.m4a', '.wav', '.ogg'},
    'video': {'.mp4', '.mov', '.webm'},
    'image': {'.png', '.jpg', '.jpeg', '.webp'},
    'other': {'.zip'},
}
ALLOWED = set().union(*KINDS.values())


def kind_of(name: str) -> str:
    ext = Path(name or '').suffix.lower()
    return next((kind for kind, exts in KINDS.items() if ext in exts), 'other')


def can_view(user: User, course: Course) -> bool:
    """O'qituvchi (egasi), tasdiqlangan o'quvchi, o'quvchisi shu kursda bo'lgan tasdiqlangan ota-ona, admin."""
    if user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN) or course.teacher_id == user.id:
        return True
    approved = Enrollment.Status.APPROVED
    if user.role == User.Role.STUDENT:
        return Enrollment.objects.filter(course=course, student=user, status=approved).exists()
    if user.role == User.Role.PARENT:
        return Enrollment.objects.filter(
            course=course, status=approved, student__parent_links__parent=user,
            student__parent_links__status=ParentChildLink.Status.APPROVED,
        ).exists()
    return False


def visible_courses(user: User):
    if user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN):
        return Course.objects.all()
    if user.role == User.Role.TEACHER:
        return Course.objects.filter(teacher=user)
    approved = Enrollment.Status.APPROVED
    if user.role == User.Role.STUDENT:
        return Course.objects.filter(enrollments__student=user, enrollments__status=approved)
    return Course.objects.filter(
        enrollments__status=approved, enrollments__student__parent_links__parent=user,
        enrollments__student__parent_links__status=ParentChildLink.Status.APPROVED,
    ).distinct()


def get_course(course_id) -> Course:
    try:
        return Course.objects.get(pk=course_id)
    except (Course.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Guruh topilmadi.'))


def get_lesson(course: Course, lesson_id) -> Lesson:
    try:
        return Lesson.objects.get(pk=lesson_id, course=course, is_deleted=False)
    except (Lesson.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise ValidationError({'lesson': _("Dars bu guruhda topilmadi.")})


def upload(*, teacher: User, course_id, file, title: str = '', lesson_id=None) -> Material:
    course = get_course(course_id)
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat guruh o'qituvchisi material yuklay oladi."))
    lesson = get_lesson(course, lesson_id) if lesson_id else None
    if file is None:
        raise ValidationError({'file': _('Fayl majburiy.')})
    name = file.name or 'material'
    if Path(name).suffix.lower() not in ALLOWED:
        raise ValidationError({'file': _("Bu turdagi fayl qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
            'allowed': ', '.join(sorted(ALLOWED))}})
    if file.size > MAX_SIZE_MB * 1024 * 1024:
        raise ValidationError({'file': _('Fayl %(size).1f MB; chegara %(max)s MB.') % {'size': file.size / 1024 / 1024, 'max': MAX_SIZE_MB}})
    return Material.objects.create(
        course=course, lesson=lesson, uploaded_by=teacher, title=(title or Path(name).stem).strip()[:200], file=file,
        original_name=name[:255], size=file.size, kind=kind_of(name),
    )


def get_material(material_id) -> Material:
    try:
        return Material.objects.select_related('course', 'uploaded_by').get(pk=material_id)
    except (Material.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Material topilmadi.'))


def delete(*, user: User, material_id) -> None:
    material = get_material(material_id)
    if material.course.teacher_id != user.id and user.role not in (User.Role.ADMIN, User.Role.SUPER_ADMIN):
        raise PermissionDenied(_("Materialni faqat guruh o'qituvchisi o'chira oladi."))
    material.file.delete(save=False)
    material.delete()


def file_for(*, user: User, material_id):
    material = get_material(material_id)
    if not can_view(user, material.course):
        raise PermissionDenied(_("Bu materialni ko'rish huquqingiz yo'q."))
    return material.file.path, material.original_name, mimetypes.guess_type(material.original_name)[0] or 'application/octet-stream'


# ── Papka tuzilmasi: Guruh -> darslar -> fayllar (2026-11-10) ──────────────────────────────────────

def course_folders(user: User) -> list:
    """Guruhlar va ulardagi fayllar soni (Workspace -> Materiallar boshlanish ekrani)."""
    courses = visible_courses(user).annotate(file_count=Count('materials', distinct=True)).order_by('title')
    return [
        {'id': str(c.id), 'title': c.title, 'kind': c.kind, 'subject': c.subject, 'file_count': c.file_count}
        for c in courses.distinct()
    ]


def _board_exists(lesson_ref):
    from apps.board.models import BoardSheet

    return Exists(BoardSheet.objects.filter(lesson=lesson_ref).exclude(strokes=[]))


def _recording_exists(lesson_ref, viewer_is_teacher: bool):
    from apps.lessons.models import LessonRecording

    qs = LessonRecording.objects.filter(lesson=lesson_ref)
    if not viewer_is_teacher:
        qs = qs.filter(status=LessonRecording.Status.COMPLETED)
    return Exists(qs)


def lesson_folders(*, user: User, course_id) -> dict:
    """Guruhdagi darslar: `file_count`, `has_recording`, `has_board` (+ darssiz fayllar "Umumiy" papkasi).
    O'quvchi/ota-ona faqat mazmuni bor (fayl, tayyor yozuv yoki doska) darslarni ko'radi; o'qituvchi hammasini (yuklash uchun)."""
    course = get_course(course_id)
    if not can_view(user, course):
        raise PermissionDenied(_("Bu guruh materiallarini ko'rish huquqingiz yo'q."))
    is_owner = course.teacher_id == user.id or user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN)
    lessons = (
        Lesson.objects.filter(course=course, is_deleted=False).exclude(status=Lesson.Status.CANCELLED)
        .annotate(
            file_count=Count('materials', distinct=True),
            has_recording=_recording_exists(OuterRef('pk'), is_owner), has_board=_board_exists(OuterRef('pk')),
        )
        .order_by('-starts_at')
    )
    if not is_owner:
        lessons = lessons.filter(Q(file_count__gt=0) | Q(has_recording=True) | Q(has_board=True))
    return {
        'course': {'id': str(course.id), 'title': course.title, 'kind': course.kind},
        'general': {'file_count': Material.objects.filter(course=course, lesson__isnull=True).count()},
        'lessons': [{
            'id': str(lesson.id), 'title': lesson.title or course.title, 'starts_at': lesson.starts_at, 'status': lesson.status,
            'file_count': lesson.file_count, 'has_recording': lesson.has_recording, 'has_board': lesson.has_board,
        } for lesson in lessons],
    }


def lesson_folder(*, user: User, lesson_id) -> dict:
    """Bitta dars papkasi: yuklangan fayllar + (tayyor bo'lsa) video yozuv va doska PDF'i alohida elementlar sifatida —
    mavjud endpointlarga havola bilan (nusxalanmaydi)."""
    try:
        lesson = Lesson.objects.select_related('course').get(pk=lesson_id, is_deleted=False)
    except (Lesson.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound(_('Dars topilmadi.'))
    if not can_view(user, lesson.course):
        raise PermissionDenied(_("Bu dars materiallarini ko'rish huquqingiz yo'q."))
    from apps.board.models import BoardSheet
    from apps.lessons.models import LessonRecording

    is_owner = lesson.course.teacher_id == user.id or user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN)
    recording = LessonRecording.objects.filter(lesson=lesson).first()
    if recording is not None and not is_owner and recording.status != LessonRecording.Status.COMPLETED:
        recording = None
    has_board = BoardSheet.objects.filter(lesson=lesson).exclude(strokes=[]).exists()
    return {
        'lesson': {'id': str(lesson.id), 'title': lesson.title or lesson.course.title, 'starts_at': lesson.starts_at, 'status': lesson.status},
        'files': list(Material.objects.filter(lesson=lesson).select_related('course', 'uploaded_by')),
        'recording': {
            'status': recording.status, 'info_url': f'/api/v1/lessons/{lesson.id}/recording/',
        } if recording is not None else None,
        'board': {'pdf_url': f'/api/v1/materials/lessons/{lesson.id}/board.pdf'} if has_board else None,
    }


def board_pdf_for(*, user: User, lesson_id):
    """Doska PDF'i Materiallar orqali (ota-onada `room.token` ruxsati yo'q, shuning uchun alohida yo'l)."""
    from apps.board import services as board_services

    lesson = lesson_folder(user=user, lesson_id=lesson_id)['lesson']  # ruxsatni tekshiradi
    obj = Lesson.objects.get(pk=lesson['id'])
    path = board_services._pdf_path(obj)
    if not path.exists():
        path = board_services.generate_pdf(obj)
        if path is None:
            raise NotFound(_("Doska bo'sh — PDF yo'q."))
    return path
