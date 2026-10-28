import mimetypes
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Course, Enrollment

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


def upload(*, teacher: User, course_id, file, title: str = '') -> Material:
    course = get_course(course_id)
    if course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat guruh o'qituvchisi material yuklay oladi."))
    if file is None:
        raise ValidationError({'file': _('Fayl majburiy.')})
    name = file.name or 'material'
    if Path(name).suffix.lower() not in ALLOWED:
        raise ValidationError({'file': _("Bu turdagi fayl qo'llab-quvvatlanmaydi. Mumkin: %(allowed)s") % {
            'allowed': ', '.join(sorted(ALLOWED))}})
    if file.size > MAX_SIZE_MB * 1024 * 1024:
        raise ValidationError({'file': _('Fayl %(size).1f MB; chegara %(max)s MB.') % {'size': file.size / 1024 / 1024, 'max': MAX_SIZE_MB}})
    return Material.objects.create(
        course=course, uploaded_by=teacher, title=(title or Path(name).stem).strip()[:200], file=file,
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
