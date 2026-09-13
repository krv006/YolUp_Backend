"""RBAC registry — FRD'dagi ruxsat matritsasining koddagi yagona manbasi.

Har bir himoyalangan amal `modul.amal` kaliti bilan belgilanadi (FRD uslubi:
course.create, lesson.schedule, link.request ...). Rolga ruxsat berish/olish
FAQAT shu faylda o'zgaradi — view'larda hech qachon `if user.role == ...` yozilmaydi.

Foydalanish:
    permission_classes = [RequirePerm('course.create')]
    yoki viewset ichida: self.require('lesson.finish')
"""
from rest_framework.permissions import BasePermission

# Rol kodlari (apps.accounts.models.User.Role bilan mos — import sikliga yo'l
# qo'ymaslik uchun satr ko'rinishida)
SUPER_ADMIN = 'super_admin'
ADMIN = 'admin'
TEACHER = 'teacher'
STUDENT = 'student'
PARENT = 'parent'

ROLE_PERMISSIONS: dict[str, set[str]] = {
    SUPER_ADMIN: {'*'},
    ADMIN: {
        'course.view', 'course.moderate',
        'lesson.view', 'lesson.cancel',
        'attendance.view',
        'audit.view',
        'user.manage',
        'notification.send',
        'quiz.view',
    },
    TEACHER: {
        'course.create', 'course.edit', 'course.view', 'course.enroll',
        'lesson.schedule', 'lesson.edit', 'lesson.cancel', 'lesson.finish', 'lesson.view',
        'room.token', 'room.moderate', 'room.leave',
        'attendance.view',
        'chat.use',
        'homework.assign', 'homework.view',
        'child.create',
        'quiz.create', 'quiz.view',
        'certificate.manage',
        'rating.view_own',
    },
    STUDENT: {
        'course.view', 'course.enroll',
        'lesson.view', 'lesson.rate',
        'room.token', 'room.leave',
        'link.respond',
        'attendance.view',
        'chat.use',
        'homework.submit', 'homework.view',
        'quiz.view', 'quiz.attempt',
    },
    PARENT: {
        'child.create',
        'link.request', 'link.view',
        'consent.manage',
        'course.view', 'course.enroll',
        'lesson.view',
        'attendance.view',
        'homework.view',
        'quiz.view',
    },
}


def role_has_perm(role: str, perm: str) -> bool:
    granted = ROLE_PERMISSIONS.get(role, set())
    return '*' in granted or perm in granted


def user_has_perm(user, perm: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', '')
    # Tasdiqlanmagan o'qituvchi kira oladi, lekin admin tasdiqlamaguncha
    # hech qanday amalga ruxsati yo'q (kurs/dars ochish va h.k.).
    if role == TEACHER and not getattr(user, 'is_approved', True):
        return False
    return role_has_perm(role, perm)


def RequirePerm(*perms: str):
    """DRF permission fabrikasi: foydalanuvchi rolida BARCHA kalitlar bo'lishi shart."""

    class _RequirePerm(BasePermission):
        message = "Sizning rolingizda bu amal uchun ruxsat yo'q."

        def has_permission(self, request, view):
            return all(user_has_perm(request.user, p) for p in perms)

    _RequirePerm.__name__ = f'RequirePerm[{",".join(perms)}]'
    return _RequirePerm
