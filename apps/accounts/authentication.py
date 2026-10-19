"""JWT autentifikatsiya: bekor qilingan (chiqarib yuborilgan) seansning access tokeni darhol rad etiladi."""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from . import sessions


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        _user, token = result
        sid = token.get('sid')
        if sid and sessions.is_revoked(sid):
            raise InvalidToken('Seans yopilgan.')
        return result
