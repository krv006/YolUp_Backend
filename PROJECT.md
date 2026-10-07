# Fokus — Onlayn Ta'lim Platformasi (umumiy hujjat)

O'zbekiston maktab o'quvchilari uchun onlayn ta'lim platformasi: jonli video
darslar, Telegram uslubidagi chat, interaktiv doska, AI uy vazifasi tekshiruvi
va ota-ona nazorati. **Bu repo — faqat backend (API)**; frontend alohida
loyihada rivojlantiriladi va shu API'ni chaqiradi.

- Prod: `https://edu.thesofmebel.uz` (API), Swagger: `/api/docs/`
- Repo: `https://github.com/krv006/Education-Tech-Platform`
- Arxitektura qoidalari: [ARCHITECTURE.md](ARCHITECTURE.md) · Deploy: [DEPLOY.md](DEPLOY.md)

---

## 1. Stack

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 6 + DRF + SimpleJWT (ASGI) |
| Real-time (chat + doska) | Django Channels 4 + Redis channel layer (WebSocket) |
| Video darslar | LiveKit (self-hosted, WebRTC) + Egress (dars yozuvi MP4) |
| DB / Cache | PostgreSQL 17 / Redis 7 (dev'da sqlite/in-memory fallback) |
| Admin panel | Django admin + **Jazzmin** (Fokus brendi, ikonkalar) |
| Loglar | Fayl rotatsiya: `logs/app.log`, `logs/errors.log` (`make applog/errlog`) |
| Server | Docker Compose: gunicorn+uvicorn worker, Caddy (TLS + proxy) |

## 2. Arxitektura

```
Internet ──443──> Caddy (TLS avto, Let's Encrypt)
                   ├── /api, /admin, /static -> backend:8000 (gunicorn/uvicorn, ASGI)
                   ├── /ws/*                 -> backend:8000 (chat + doska WebSocket)
                   ├── /media                -> umumiy volume
                   ├── /livekit              -> livekit:7880 (WebRTC signaling)
                   └── /                     -> 302 /api/docs/
Internet ──7881/tcp, 7882/udp──> LiveKit (WebRTC media, UDP mux — bitta port)
egress (konteyner) ──> darsni MP4 ga yozadi -> recordings volume -> backend auth stream
test-admin-api.navigocrm.com ──> navigo tarmog'idagi nginx (boshqa loyiha, shu Caddy orqali)
```

Kod qatlamlari (ARCHITECTURE.md qoidasi): `views.py` yupqa → biznes-logika
`services.py`da → o'qish `selectors.py`da. Ruxsatlar faqat
`apps/core/permissions.py` (RBAC matritsasi) orqali.

## 3. Modullar

| Modul | Nima qiladi | Asosiy endpointlar |
|---|---|---|
| `apps/accounts` | JWT auth, 4 rol (teacher/student/parent/admin), ota-ona↔bola bog'lash (taklif-kod + bolaning tasdig'i), rozilik (consent) | `/api/v1/auth/*` |
| `apps/lessons` | Kurs, dars jadvali, yozilish (enroll), davomat hisoboti | `/api/v1/courses/`, `/api/v1/lessons/`, `/api/v1/attendance/` |
| `apps/live` | LiveKit token, avtomatik davomat (kirdi/chiqdi), "Siz shu yerdamisiz?" diqqat tekshiruvi (random, 15s), fokus jurnali (oynadan chiqib-kirish) | `/api/v1/live/*` |
| `apps/chat` | Telegram uslubi: har kurs = guruh chat; direct faqat o'qituvchi↔o'quvchi (1 martalik so'rov → qabul/block); real-time WebSocket | `/api/v1/chat/*`, `ws /ws/chat/<room_id>/` |
| `apps/board` | Jonli dars doskasi, **real-time WebSocket** (polling yo'q): qalam, marker (shaffof), chiziq/strelka, to'rtburchak, ellips, matn — bari saqlanadi va PDF'ga tushadi; bir nechta sheet; o'chirish SABABI majburiy (jurnal); dars tugagach PDF → kurs chatiga. **Matematik rejim FAQAT matematika kurslarida** (`math_enabled`): MathLive LaTeX bloklari + SymPy yechuvchi | `/api/v1/board/<lesson_id>/*`, `ws /ws/board/<lesson_id>/` |
| `apps/homework` | Uy vazifasi: o'qituvchi vazifani rich-matn (sanitized HTML) yoki fayl (Word/PDF/rasm) bilan beradi, muddat qo'yadi; o'quvchi PDF/rasm/DOCX (Speaking'da audio) topshiradi; o'qituvchi ballni o'zi qo'yib tasdiqlaydi (AI tekshiruv olib tashlangan); statistika, kech topshirish belgisi | `/api/v1/homework/*` |
| `apps/core` | UUID+timestamp baza modellari, soft-delete, RBAC, audit log, yagona xato formati | — |

## 4. Rollar (RBAC qisqacha)

- **O'qituvchi:** kurs/dars yaratish, doska boshqaruvi, vazifa berish/natijalar,
  chat guruhlari, direct so'rovlarni qabul/block
- **O'quvchi:** darsga kirish, doskada ruxsat so'rash, vazifa topshirish,
  chat (guruh + faqat o'qituvchi bilan direct)
- **Ota-ona:** bola hisobini yaratish/bog'lash (bola tasdig'i bilan), davomat,
  fokus jurnali, vazifa natijalarini ko'rish
- To'liq matritsa: `apps/core/permissions.py` (`ROLE_PERMISSIONS`)

## 5. Real-time (WebSocket)

Ikkala kanal ham JWT bilan: `?token=<access>`. Yopilish kodlari: `4401` token
yaroqsiz, `4403` a'zo emas.

### 5.1 Chat — `wss://<domain>/ws/chat/<room_id>/`

| Yo'nalish | Payload | Izoh |
|---|---|---|
| C→S | `{"type":"message","text":"..."}` | Xabar yuborish (REST `POST .../send/` bilan teng kuchli) |
| C→S | `{"type":"typing"}` | "Yozmoqda..." signali |
| S→C | `{"type":"message","message":{id,room,sender,text,created_at}}` | Yangi xabar (REST orqali yuborilgani ham keladi) |
| S→C | `{"type":"typing","user_id","name"}` | Kimdir yozmoqda (o'zingizni filtrlang) |
| S→C | `{"type":"error","detail"}` | Yuborish xatosi |

### 5.2 Doska — `wss://<domain>/ws/board/<lesson_id>/` (polling KERAK EMAS)

Boshlang'ich holat: REST `GET /api/v1/board/<lesson_id>/`, keyin faqat WS.

| Yo'nalish | Payload |
|---|---|
| C→S | `{"type":"stroke","sheet":0,"stroke":{...}}` — element qo'shish (REST bilan teng kuchli) |
| S→C | `{"type":"stroke","sheet","stroke"}` / `{"type":"erase","sheet","stroke_ids","by","reason"}` / `{"type":"sheet","index"}` / `{"type":"error","detail"}` |

### 5.3 Doska stroke turlari (bari doimiy saqlanadi va PDF'ga tushadi)

| Asbob | Format |
|---|---|
| Qalam | `{points:[[x,y],...], color, width}` |
| Marker (shaffof) | `{points, ..., opacity: 0.4}` |
| Chiziq / strelka | `{type:'line', x1,y1,x2,y2, arrow?:true, color, width}` |
| To'rtburchak | `{type:'rect', x,y,w,h, color, width}` |
| Ellips | `{type:'ellipse', x,y,w,h, color, width}` |
| Matn/raqam | `{type:'text', text, x,y, size, color}` |
| Formula (MathLive) | `{type:'math', latex, x,y, size, color}` — faqat `math_enabled` kurslarda |

Yopilish kodlari: `4401` — token yaroqsiz, `4403` — xonaga a'zo emas.
Tarix va o'qilgan belgisi REST'da: `GET .../messages/`, `POST .../read/`.
Texnik: Channels 4, JWT query-param auth (`apps/chat/ws_auth.py`), xona guruhi
`chat_<room_id>`, broadcast `transaction.on_commit`dan keyin (`realtime.py`).

## 6. Uy vazifasi oqimi

1. O'qituvchi vazifa beradi (rich matn `nh3` bilan sanitize, ixtiyoriy fayl, muddat, til fanlari uchun skill: writing/reading/listening/speaking)
2. O'quvchi fayl topshiradi → `Submission(status=pending_review)` → o'qituvchiga bildirishnoma
3. O'qituvchi ballni (0-100) o'zi qo'yib tasdiqlaydi → `status=done`, natija o'quvchi/ota-onaga ochiladi
4. AI (Gemini) tekshiruv loyihadan olib tashlangan (2026-10) — AI kerak bo'lsa alohida tayyor repolar ishlatiladi

## 7. Muhit o'zgaruvchilari (asosiylari)

| Env | Nima uchun |
|---|---|
| `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Django |
| `CORS_ALLOWED_ORIGINS` | **Frontend domeni SHU YERGA yoziladi** (vergul bilan) |
| `POSTGRES_*` | DB (bo'lmasa sqlite) |
| `REDIS_URL` | Cache + WebSocket channel layer (prod'da shart) |
| `LIVEKIT_API_KEY/SECRET/URL` | Video darslar |

To'liq namuna: `.env.prod.example` (prod), `.env.example` (dev).

## 8. Ishga tushirish

**Dev (Windows/Linux):**
```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d              # ixtiyoriy: Postgres+Redis+LiveKit
python manage.py migrate && python manage.py runserver   # runserver ASGI (daphne)
python manage.py seed_fake        # demo: teacher/student/perents, parol: 1
```

**Prod (serverda):**
```bash
cd /var/www/edu_platform && git pull && make up
```
Birinchi o'rnatish: `bash scripts/deploy.sh`. Lokaldan: `bash scripts/deploy-remote.sh`.

## 9. Testlar

```bash
python manage.py test            # hammasi
python manage.py test apps.chat apps.board apps.homework
```
Qamrov: chat (REST + 5 WS testi), doska (ruxsat/o'chirish sababi/PDF/shakllar/
MathLive cheklovi + 4 WS testi), homework (AI mock, RBAC, fayllar, statistika),
davomat + fokus tahlili, video yozuv (nom/chat/stream/ruxsat), login jurnali.
AI/egress chaqiruvlari testlarda mock yoki o'chirilgan — tashqi servis kerak emas.

Prod'ga o'xshash muhitda (DEBUG=False + manifest static) lokal tekshirish:
`DJANGO_SETTINGS_MODULE=root.settings.stagetest python manage.py runserver`

## 10. EduTech.docx talablar holati

- ✅ Telegram uslubidagi chat, 1 martalik direct so'rov, block
- ✅ Kurs = guruh chat; o'quvchilar orasida DM yo'q
- ✅ Random diqqat tekshiruvi (3-5 marta, 15s, vaqti sirlangan)
- ✅ Doska: ruxsat so'rash, chizish, sheet'lar, sababli o'chirish, PDF→chat, faqat platformada
- ✅ Fokus jurnali (oynadan chiqib-kirish — ota-onaga): necha marta chiqdi,
  HAR BIR chiqishda qancha turdi, qachon qaytdi, jami/eng uzun yo'qlik —
  davomat hisobotidagi `focus` maydonida (`exits`, `away_seconds`,
  `longest_seconds`, `timeline[{left_at, returned_at, seconds}]`)
- ✅ AI uy vazifasi (qo'shimcha talab sifatida qo'shildi)
- ⚠️ Skrinshot/screenrecord taqiqlash — brauzerda IMKONSIZ; yechim: desktop app
  (Electron `setContentProtection`) yoki mobil ilova (`FLAG_SECURE`) — reja
- ⚠️ Qo'shimcha ekran taqiqlash — brauzerda imkonsiz; desktop app'da amaliy hal bo'ladi
- ✅ Dars video yozuvi (LiveKit Egress): o'qituvchi darsga HAR kirganda
  kafolatlanadi (boshlaydi yoki aktiv egress'ni topib oladi — restart/qayta
  kirishga chidamli); holatlar: `pending → recording → completed/failed`,
  xato matnlari o'zbekcha; e'lon chatga faqat haqiqiy yozuvda tushadi;
  tugatishda o'qituvchi nom beradi (`finish` -> `recording_title`) va yozuv guruh
  chatga e'lon qilinadi (`/recordings/<lesson_id>`); fayl FAQAT platformada
  ochiladi — muddatli imzolangan stream (3 soat), inline pleer, doimiy/ochiq URL
  yo'q, yuklab olish taklif qilinmaydi. Endpointlar:
  `GET /lessons/<id>/recording/` (holat+stream_url), `.../recording/stream/?t=`,
  `DELETE /lessons/<id>/recording/` (o'qituvchi)
- ✅ Login jurnali: har login IP + qurilma (User-Agent) bilan yoziladi,
  o'zgarish bayroqlari (`new_ip`, `new_device`); tarix: `GET /auth/logins/`
  (o'ziniki), ota-ona `?student=<id>` bilan bolasiniki

## 11. LiveKit resurs optimizatsiyasi

- **Simulcast** (har kamera 3 o'lcham) + **adaptiveStream** (ko'rinmagan video
  to'xtaydi, plitka o'lchamiga mos layer) + **dynacast** (keraksiz layerni
  publisher o'chiradi) — frontend Room sozlamalari, tayyor kod README'da
- **Layout:** spiker katta / qolganlar thumbnail — grid emas (shunda yuqoridagilar
  maksimal ishlaydi)
- **Server tomonda:** egress 720p/30 preset (CPU ~2x kam), egress konteyneriga
  `cpus:2, mem_limit:2g` chegara, bo'sh xona 5 daqiqada yopiladi
  (`empty_timeout`), Redis `maxmemory 256mb volatile-ttl`

## 12. Keyingi qadamlar

1. Desktop app (Electron qobiq): skrinshot-himoya + ikkinchi ekran nazorati + kiosk
2. Video ustiga o'quvchi ismli watermark
3. Mobil ilova (WebView + FLAG_SECURE)
4. Bitta sessiya cheklovi (yangi login eski tokenni bekor qiladi)
