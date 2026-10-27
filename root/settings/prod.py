"""Production settings — hardened. Requires real env values, refuses insecure defaults."""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

if os.getenv('SECRET_KEY', '').startswith('django-insecure') or not os.getenv('SECRET_KEY'):
    raise RuntimeError('PROD: haqiqiy SECRET_KEY .env da berilishi shart.')
if not os.getenv('POSTGRES_DB'):
    raise RuntimeError('PROD: Postgres majburiy (POSTGRES_DB va h.k.).')
# ALLOWED_HOSTS = ['*'] — Caddy faqat bizning domenlarni backendga o'tkazadi,
# host filtri proxy darajasida hal bo'lgan

# Static — whitenoise (gunicorn orqali beriladi, Caddy /static ni backendga proxy qiladi)
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,  # noqa: F405
    'whitenoise.middleware.WhiteNoiseMiddleware',
)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Kechirimli manifest — Jazzmin'ning papka-static so'rovi 500 bermasin
    'staticfiles': {'BACKEND': 'apps.core.staticfiles.ForgivingManifestStaticFilesStorage'},
}

# Base'dagi ro'yxat saqlanadi, .env dagilar USTIGA qo'shiladi (almashtirmaydi)
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS + [  # noqa: F405
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip() and o.strip() not in CSRF_TRUSTED_ORIGINS  # noqa: F405
]

from .db import build_database  # noqa: E402

DATABASES = {'default': build_database(os.environ)}

# Security hardening
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'true').lower() == 'true'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'
