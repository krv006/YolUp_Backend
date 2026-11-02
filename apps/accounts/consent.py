"""Rozilik (consent) tekshiruvi: ota-ona farzand uchun "Faollik tahlili" / "Kamera" / "Yozib olish" ni o'chirib qo'yishi mumkin.

Qoida: rozilik yozuvi YO'Q bo'lsa — ruxsat (avvalgi xatti-harakat saqlanadi); aniq `granted=False` bo'lsa — yopiq.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from .models import Consent, ParentChildLink, User


class ConsentRequired(PermissionDenied):
    """403 `{"success": false, "error": {"code": "consent_required", "details": {"kind": "analytics", ...}}}`."""

    default_code = 'consent_required'

    def __init__(self, kind: str):
        super().__init__(detail={'detail': _("Bu ma'lumot yopiq: ota-ona/o'quvchi rozilik bermagan."), 'kind': kind})


def is_denied(student, kind: str) -> bool:
    """Aniq `granted=False` bo'lsa True (yozuv yo'q bo'lsa False)."""
    return Consent.objects.filter(student=student, kind=kind, granted=False).exists()


def denied_student_ids(student_ids, kind: str) -> set:
    return set(Consent.objects.filter(student_id__in=list(student_ids), kind=kind, granted=False).values_list('student_id', flat=True))


def require(student, kind: str) -> None:
    if is_denied(student, kind):
        raise ConsentRequired(kind)


def approved_child(parent: User, student_id) -> User:
    """Ota-onaning TASDIQLANGAN farzandi (aks holda 403/404)."""
    from rest_framework.exceptions import NotFound

    try:
        link = ParentChildLink.objects.select_related('student').get(
            parent=parent, student_id=student_id, status=ParentChildLink.Status.APPROVED,
        )
    except (ParentChildLink.DoesNotExist, ValueError, TypeError):
        raise PermissionDenied(_("Bu o'quvchi sizga bog'lanmagan."))
    if link.student.role != User.Role.STUDENT:
        raise NotFound(_("O'quvchi topilmadi."))
    return link.student
