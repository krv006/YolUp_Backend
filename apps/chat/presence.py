"""Onlayn holati — WebSocket ulanishlarini cache'da sanaydi (har foydalanuvchi uchun ochiq ulanishlar soni).

Ulanish ochilganda +1, yopilganda -1. Server kutilmaganda o'chib qolsa hisoblagich eskirib qolishi mumkin —
shuning uchun kalit TTL bilan saqlanadi va har yangi ulanishda yangilanadi.
"""
from django.core.cache import cache
from django.utils import timezone

TTL = 6 * 60 * 60


def _key(user_id) -> str:
    return f'chat:online:{user_id}'


def mark_online(user_id) -> None:
    key = _key(user_id)
    cache.add(key, 0, TTL)
    try:
        cache.incr(key)
    except ValueError:  # kalit shu orada o'chib ketgan
        cache.set(key, 1, TTL)
    cache.touch(key, TTL)


def mark_offline(user_id) -> None:
    key = _key(user_id)
    try:
        left = cache.decr(key)
    except ValueError:
        return
    if left <= 0:
        cache.delete(key)


def online_ids(user_ids) -> set:
    ids = [str(i) for i in user_ids]
    found = cache.get_many([_key(i) for i in ids])
    return {i for i in ids if (found.get(_key(i)) or 0) > 0}


SEEN_THROTTLE = 120  # soniya: oxirgi faollik bazaga ko'pi bilan 2 daqiqada bir yoziladi


def touch_last_seen(user_id, force: bool = False) -> None:
    """`User.last_seen_at` ni yangilaydi (har so'rovda emas — cache bilan cheklangan). `force` — chat ulanishi yopilganda."""
    from apps.accounts.models import User

    try:
        fresh = cache.add(f'chat:seen:{user_id}', 1, SEEN_THROTTLE)
    except Exception:  # noqa: BLE001 — cache ishlamasa so'rov to'xtamasin
        return
    if fresh or force:
        User.objects.filter(pk=user_id).update(last_seen_at=timezone.now())
