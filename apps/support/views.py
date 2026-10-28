from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import send_notification

from .models import FaqItem, HelpVideo, SupportMessage, SupportTicket

STAFF = (User.Role.ADMIN, User.Role.SUPER_ADMIN)


def _is_staff(user) -> bool:
    return user.role in STAFF


def _name(user) -> str:
    return user.get_full_name() or user.username


def ticket_dict(ticket: SupportTicket, *, with_messages: bool = False) -> dict:
    last = ticket.messages.last()
    data = {
        'id': str(ticket.id), 'subject': ticket.subject, 'status': ticket.status, 'created_at': ticket.created_at,
        'updated_at': ticket.updated_at, 'last_message': last.body[:120] if last else '',
        'user': {'id': str(ticket.user_id), 'name': _name(ticket.user)},
    }
    if with_messages:
        data['messages'] = [{
            'id': str(m.id), 'body': m.body, 'from_staff': m.from_staff, 'author': _name(m.author), 'created_at': m.created_at,
        } for m in ticket.messages.select_related('author')]
    return data


def _notify(*, sender, recipients, text, ticket, kind):
    for user in recipients:
        try:
            send_notification(
                sender=sender, description=text, target_type=Notification.Target.USER, user_id=user.id, kind=kind,
                link_type='support', link_id=str(ticket.id),
            )
        except Exception:  # noqa: BLE001 — bildirishnoma murojaatni to'xtatmasin
            pass


def _get_ticket(user, pk) -> SupportTicket:
    try:
        ticket = SupportTicket.objects.select_related('user').get(pk=pk)
    except (SupportTicket.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Murojaat topilmadi.'))
    if ticket.user_id != user.id and not _is_staff(user):
        raise PermissionDenied(_("Bu murojaatni ko'rish huquqingiz yo'q."))
    return ticket


class TicketListCreateView(APIView):
    """`GET /support/tickets/` — o'zimniki (admin: `?all=1` hammasi, `?status=`); `POST {subject, message}` — yangi murojaat."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'

    def get_throttles(self):
        return super().get_throttles() if self.request.method == 'POST' else []

    def get(self, request):
        qs = SupportTicket.objects.select_related('user')
        if not (_is_staff(request.user) and request.query_params.get('all') == '1'):
            qs = qs.filter(user=request.user)
        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        return Response([ticket_dict(t) for t in qs[:100]])

    def post(self, request):
        subject = (request.data.get('subject') or '').strip()
        message = (request.data.get('message') or '').strip()
        if not subject:
            raise ValidationError({'subject': _('Mavzuni yozing.')})
        if not message:
            raise ValidationError({'message': _('Xabarni yozing.')})
        ticket = SupportTicket.objects.create(user=request.user, subject=subject[:200])
        SupportMessage.objects.create(ticket=ticket, author=request.user, body=message[:5000])
        _notify(
            sender=request.user, recipients=User.objects.filter(role__in=STAFF, is_active=True),
            text=_('Yangi murojaat: %(subject)s') % {'subject': ticket.subject}, ticket=ticket, kind='support_new',
        )
        return Response(ticket_dict(ticket, with_messages=True), status=status.HTTP_201_CREATED)


class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(ticket_dict(_get_ticket(request.user, pk), with_messages=True))


class TicketReplyView(APIView):
    """`POST {message}` — foydalanuvchi yoki admin javob yozadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = _get_ticket(request.user, pk)
        body = (request.data.get('message') or '').strip()
        if not body:
            raise ValidationError({'message': _('Xabarni yozing.')})
        if ticket.status == SupportTicket.Status.CLOSED:
            raise ValidationError({'detail': _('Murojaat yopilgan.')})
        staff = _is_staff(request.user)
        SupportMessage.objects.create(ticket=ticket, author=request.user, body=body[:5000], from_staff=staff)
        ticket.status = SupportTicket.Status.ANSWERED if staff else SupportTicket.Status.OPEN
        ticket.save(update_fields=['status', 'updated_at'])
        if staff:
            _notify(sender=request.user, recipients=[ticket.user], text=_("Murojaatingizga javob keldi: %(subject)s") % {
                'subject': ticket.subject}, ticket=ticket, kind='support_reply')
        else:
            _notify(sender=request.user, recipients=User.objects.filter(role__in=STAFF, is_active=True),
                    text=_('Murojaatga yangi xabar: %(subject)s') % {'subject': ticket.subject}, ticket=ticket, kind='support_new')
        return Response(ticket_dict(ticket, with_messages=True))


class TicketCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = _get_ticket(request.user, pk)
        ticket.status = SupportTicket.Status.CLOSED
        ticket.save(update_fields=['status', 'updated_at'])
        return Response(ticket_dict(ticket))


class HelpVideoListView(APIView):
    """`GET /help/videos/?role=teacher|student|parent` — sarlavha, davomiylik, URL (admin panelda boshqariladi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get('role') or request.user.role
        qs = HelpVideo.objects.filter(is_active=True).filter(Q(role='') | Q(role=role))
        return Response([{
            'id': str(v.id), 'title': v.title, 'url': v.url, 'duration_seconds': v.duration_seconds,
        } for v in qs])


class FaqListView(APIView):
    """`GET /help/faq/?role=` — savol-javoblar."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get('role') or request.user.role
        qs = FaqItem.objects.filter(is_active=True).filter(Q(role='') | Q(role=role))
        return Response([{'id': str(f.id), 'question': f.question, 'answer': f.answer} for f in qs])
