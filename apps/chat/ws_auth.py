"""WebSocket uchun JWT autentifikatsiya.

Brauzer WebSocket'da Authorization header yubora olmaydi — shuning uchun
access token query-string orqali keladi:

    wss://<domain>/ws/chat/<room_id>/?token=<access>

Token SimpleJWT bilan tekshiriladi; yaroqsiz/yo'q bo'lsa scope['user']
AnonymousUser bo'ladi va consumer ulanishni 4401 bilan yopadi.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async


@database_sync_to_async
def _user_from_token(raw_token: str):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.tokens import AccessToken

    from apps.accounts.models import User

    try:
        from apps.accounts import sessions

        token = AccessToken(raw_token)
        if token.get('sid') and sessions.is_revoked(token['sid']):
            return AnonymousUser()  # chiqarib yuborilgan seans
        return User.objects.get(pk=token['user_id'])
    except Exception:  # yaroqsiz token / user yo'q
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        params = parse_qs(scope.get('query_string', b'').decode())
        raw = (params.get('token') or [''])[0]
        scope['user'] = await _user_from_token(raw) if raw else AnonymousUser()
        return await self.inner(scope, receive, send)
