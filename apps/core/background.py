"""Sekin ishlarni (push, xat yuborish) so'rovdan tashqarida bajarish.

`BACKGROUND_ASYNC=1` (standart) — kichik oqimlar to'plamida; testlarda yoki `BACKGROUND_ASYNC=0` bo'lsa — joyida (sinxron),
shunda testlar natijani darhol tekshira oladi. Xato hech qachon chaqiruvchiga ko'tarilmaydi, faqat log'ga yoziladi.
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger('apps')

_executor: ThreadPoolExecutor | None = None


def _pool() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='bg')
    return _executor


def _call(func, args, kwargs) -> None:
    try:
        func(*args, **kwargs)
    except Exception:  # noqa: BLE001 — fon ishi xatosi asosiy jarayonni buzmasin
        logger.exception('Fon ishi bajarilmadi: %s', getattr(func, '__name__', func))
    finally:
        close_old_connections()


def run(func, *args, **kwargs) -> None:
    """`func(*args, **kwargs)` ni fonda ishga tushiradi (sozlamaga qarab joyida)."""
    if getattr(settings, 'BACKGROUND_ASYNC', False):
        _pool().submit(_call, func, args, kwargs)
    else:
        _call(func, args, kwargs)
