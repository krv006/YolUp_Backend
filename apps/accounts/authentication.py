"""JWT autentifikatsiya: bekor qilingan (chiqarib yuborilgan) seansning access tokeni darhol rad etiladi."""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from . import sessions


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        sid = token.get('sid')
        if sid and sessions.is_revoked(sid):
            raise InvalidToken('Seans yopilgan.')
        from apps.chat import presence

        presence.touch_last_seen(user.id)  # chat a'zolari ro'yxatidagi "oxirgi faollik"
        return result
