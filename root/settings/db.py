"""Baza sozlamasi (prod) — alohida funksiya, shunda uni testlash mumkin.

Nega ulanishlar puli: ASGI (uvicorn) da har parallel so'rov alohida oqimda, har oqim o'z baza ulanishini ochadi va
`CONN_MAX_AGE>0` uni ochiq qoldiradi — ulanishlar soni CHEKLANMAYDI. 2026-10-27 o'lchovi (Linux, Postgres): bitta jarayon
64 parallel so'rovda 199 ta ulanish ochib, "too many clients" xatosi berdi (3 500 xato, o'tkazuvchanlik 31 so'rov/s).
Puli (psycopg_pool) bilan: 132 so'rov/s, 12 ulanish, 0 xato.

  DB_POOL_MAX=<n>   — shu jarayon uchun ko'pi bilan n ulanishli pul (CONN_MAX_AGE avtomatik 0). ASGI jarayonlar uchun (chat/doska).
  DB_POOL_MAX yo'q  — oddiy doimiy ulanish (CONN_MAX_AGE=60): WSGI gthread (workers x threads bilan cheklangan) va cron uchun yaxshi.
"""


def build_database(env) -> dict:
    pool_max = int(env.get('DB_POOL_MAX') or 0)
    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.get('POSTGRES_DB'),
        'USER': env.get('POSTGRES_USER'),
        'PASSWORD': env.get('POSTGRES_PASSWORD'),
        'HOST': env.get('POSTGRES_HOST', 'localhost'),
        'PORT': env.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 0 if pool_max else int(env.get('DB_CONN_MAX_AGE') or 60),
    }
    if pool_max:
        config['OPTIONS'] = {'pool': {'min_size': min(2, pool_max), 'max_size': pool_max, 'timeout': 20}}
    return config
