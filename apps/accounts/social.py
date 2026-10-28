"""Google va Apple bilan kirish: provayderning `id_token` (JWT) ini tekshiradi va foydalanuvchi ma'lumotini qaytaradi.

Tekshiruv provayderning ochiq kalitlari (JWKS) bo'yicha: imzo, `iss`, `aud` (bizning client ID'lar) va muddat. Client ID'lar
`.env` da: `GOOGLE_CLIENT_IDS` (Web + iOS + Android client ID'lari, vergul bilan), `APPLE_CLIENT_IDS` (Services ID va/yoki
iOS Bundle ID, vergul bilan). Sozlanmagan provayder — 503 (jim ishlamaydi).
"""
import logging
from dataclasses import dataclass

import jwt
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from jwt import PyJWKClient
from rest_framework.exceptions import APIException, AuthenticationFailed

logger = logging.getLogger('apps')

GOOGLE = 'google'
APPLE = 'apple'

_PROVIDERS = {
    GOOGLE: {
        'jwks': 'https://www.googleapis.com/oauth2/v3/certs',
        'issuers': ('https://accounts.google.com', 'accounts.google.com'),
        'audiences': lambda: settings.GOOGLE_CLIENT_IDS,
    },
    APPLE: {
        'jwks': 'https://appleid.apple.com/auth/keys',
        'issuers': ('https://appleid.apple.com',),
        'audiences': lambda: settings.APPLE_CLIENT_IDS,
    },
}

_clients: dict = {}


class SocialLoginNotConfigured(APIException):
    status_code = 503
    default_code = 'social_login_not_configured'
    default_detail = _("Bu usul bilan kirish hozircha sozlanmagan.")


@dataclass(frozen=True)
class SocialClaims:
    provider: str
    subject: str
    email: str
    email_verified: bool
    first_name: str = ''
    last_name: str = ''


def _jwks_client(provider: str) -> PyJWKClient:
    """Provayder kalitlari keshlanadi (kalit aylanganda PyJWKClient o'zi qayta yuklaydi)."""
    if provider not in _clients:
        _clients[provider] = PyJWKClient(_PROVIDERS[provider]['jwks'], cache_keys=True, lifespan=3600)
    return _clients[provider]


def _truthy(value) -> bool:
    """Apple `email_verified` ni ba'zan matn ("true") ko'rinishida yuboradi."""
    return value is True or str(value).lower() == 'true'


def verify_id_token(provider: str, token: str) -> SocialClaims:
    if provider not in _PROVIDERS:
        raise AuthenticationFailed(_("Noma'lum provayder."))
    config = _PROVIDERS[provider]
    audiences = list(config['audiences']())
    if not audiences:
        raise SocialLoginNotConfigured()
    if not isinstance(token, str) or not token.strip():
        raise AuthenticationFailed(_('id_token berilmadi.'))
    try:
        key = _jwks_client(provider).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=['RS256'], audience=audiences, options={'require': ['exp', 'iss', 'aud', 'sub']},
            issuer=list(config['issuers']),
        )
    except jwt.PyJWTError as exc:
        logger.info('social %s token rad etildi: %s', provider, exc)
        raise AuthenticationFailed(_('Token yaroqsiz yoki muddati tugagan.')) from exc
    except Exception as exc:  # noqa: BLE001 — JWKS yuklanmadi (tarmoq) va h.k.
        logger.warning('social %s kalitlari olinmadi: %s', provider, exc)
        raise AuthenticationFailed(_("Tokenni tekshirib bo'lmadi. Keyinroq urinib ko'ring.")) from exc
    return SocialClaims(
        provider=provider,
        subject=str(claims['sub']),
        email=(claims.get('email') or '').strip().lower(),
        email_verified=_truthy(claims.get('email_verified')),
        first_name=(claims.get('given_name') or '')[:150],
        last_name=(claims.get('family_name') or '')[:150],
    )
