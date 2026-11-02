"""Yagona xato formati — frontend har doim bitta shaklni kutadi:

    {"success": false, "error": {"code": "...", "message": "...", "details": {...}}}

Kutilmagan (500) xatolar log'ga to'liq yoziladi, mijozga ichki tafsilot chiqmaydi.
"""
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('apps.errors')


def _first_message(data) -> str:
    """DRF error strukturasidan odam o'qiydigan birinchi xabarni sug'urib oladi."""
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        return _first_message(data[0])
    if isinstance(data, dict):
        for key in ('detail', 'message', 'non_field_errors'):
            if key in data:
                return _first_message(data[key])
        for value in data.values():
            return _first_message(value)
    return _('Xatolik yuz berdi.')


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        request = context.get('request')
        logger.exception(
            'Unhandled exception at %s %s',
            getattr(request, 'method', '?'), getattr(request, 'path', '?'),
        )
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'server_error',
                    'message': _("Ichki xatolik. Birozdan so'ng qayta urinib ko'ring."),
                    'details': None,
                },
            },
            status=500,
        )

    code = getattr(exc, 'default_code', 'error')
    wrapped = {
        'success': False,
        'error': {
            'code': str(code),
            'message': _first_message(response.data),
            'details': response.data,
        },
    }
    if isinstance(exc, Throttled) and exc.wait is not None:
        wrapped['error']['retry_after'] = int(-(-exc.wait // 1))  # soniya, yuqoriga yaxlitlangan (Retry-After bilan bir xil)
    return Response(wrapped, status=response.status_code, headers=dict(response.headers.items()))
