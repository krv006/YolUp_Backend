# Deploy — edu.thesofmebel.uz

Bitta `docker compose` bilan hammasi ko'tariladi: Postgres, Redis, LiveKit, Django (gunicorn), Caddy (TLS + reverse proxy).

**Frontend alohida loyihada** (boshqa jamoa/hosting) — u shu domendagi API'ni chaqiradi.
Frontend domenini `.env` dagi `CORS_ALLOWED_ORIGINS` ga qo'shishni unutmang.

## Arxitektura

```
Internet ──443──> Caddy (TLS avto, Let's Encrypt)
                   ├── /            -> 302 /api/docs/ (frontend bu yerda emas)
                   ├── /api, /admin -> backend:8000 (gunicorn + uvicorn worker, ASGI)
                   ├── /ws          -> backend:8000 (chat + doska WebSocket)
                   ├── /static      -> backend (whitenoise)
                   ├── /media       -> umumiy volume (file_server)
                   └── /livekit     -> livekit:7880 (WebSocket signaling)
Internet ──7881/tcp, 7882/udp──> LiveKit (WebRTC media, to'g'ridan-to'g'ri, UDP mux — bitta port)
backend ──> o'qituvchi brauzeridan bo'lak-bo'lak yuklangan video/audio -> `recordings`
            volume'ga yoziladi va birlashtiriladi (auth stream orqali beriladi) —
            server-tomon LiveKit Egress ENDI ISHLATILMAYDI (2026-08-28'da olib tashlangan)
```

Volume'lar: `pgdata` (DB), `media` (yuklamalar), `logs` (app/errors loglari),
`recordings` (dars videolari), `caddy_data/config` (TLS sertifikatlar).

Loglarni ko'rish: `make applog` (hammasi), `make errlog` (faqat xatolar),
`make logs` (konteyner loglari).

## 1. DNS

`edu.thesofmebel.uz` uchun **A record** -> server IP. (Caddy sertifikat olishi uchun DNS avval ishlashi shart.)

## 2. Server portlari (firewall/UFW da oching)

- `80/tcp`, `443/tcp`, `443/udp` — Caddy
- `7881/tcp` — LiveKit TCP fallback
- `7882/udp` — LiveKit WebRTC media (UDP mux — bitta port, minglab ulanish)

## 3. Ishga tushirish — bitta buyruq

```bash
bash scripts/deploy.sh
```

Skript o'zi: host'dagi nginx/apache'ni to'xtatadi (80/443 Caddy'ga o'tadi), `.env` yo'q
bo'lsa sekretlarni generatsiya qilib yaratadi, ufw portlarini ochadi, `docker compose up -d --build` qiladi.

Keyin admin yaratish:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Qulaylik uchun `Makefile` bor (`make help` — ro'yxat): `make deploy`, `make fake` (fake data:
teacher / perents / student, parol: 1), `make logs`, `make superuser` va h.k.

Qo'lda qilmoqchi bo'lsangiz: `cp .env.prod.example .env` -> to'ldiring -> `docker compose -f docker-compose.prod.yml up -d --build`.

Tekshirish: `https://edu.thesofmebel.uz/api/health/`, `/admin/` (Django admin), `/api/docs/` (Swagger).

## 4. Yangilash

Serverda:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Yoki lokal kompyuterdan bitta buyruq bilan (SSH kalit bir marta `ssh-copy-id deploy@<SERVER_IP>`
bilan sozlangan bo'lishi kerak):

```bash
bash scripts/deploy-remote.sh
```

Migratsiya va collectstatic har startda avtomatik bajariladi.

## Muammolar

- **Sertifikat olinmayapti** — DNS hali tarqalmagan yoki 80-port yopiq. `docker compose -f docker-compose.prod.yml logs caddy`
- **Video/audio ulanmayapti (signaling ishlaydi, media yo'q)** — UDP portlar yopiq, yoki LiveKit tashqi IP ni topolmayapti. `docker-compose.prod.yml` da livekit `command` ga qo'shing: `--node-ip <SERVER_PUBLIC_IP>`
- **502 /api da** — backend hali ko'tarilmagan: `docker compose -f docker-compose.prod.yml logs backend`
