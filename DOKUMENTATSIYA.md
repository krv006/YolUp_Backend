# Yolup backend: barcha hujjatlar (bitta fayl)

Bu fayl ildizdagi alohida `.md` hujjatlarning hammasini bitta joyga yig'adi (README.md bundan mustasno). Mazmun o'zgartirilmagan: har bo'limning sarlavhasi — avvalgi fayl nomi, ichidagi sarlavhalar ikki pog'ona pastga tushirilgan, hujjatlararo havolalar shu fayl ichidagi bo'limlarga yo'naltirilgan. Eski fayllar git tarixida saqlanadi.

## Mundarija

**1. Loyiha va arxitektura**

- [PROJECT](#project) — Fokus — Onlayn Ta'lim Platformasi (umumiy hujjat)
- [ARCHITECTURE](#architecture) — Fokus — Backend Arxitektura
- [COMPLETED_WORK](#completed_work) — Qilingan ishlar — to'liq API va funksiyalar ro'yxati
- [PUSHED_CHANGES](#pushed_changes) — `asem-mirzaeva` branch — push qilingan o'zgarishlar

**2. Server, deploy va o'lchovlar**

- [DEPLOY](#deploy) — Deploy — edu.thesofmebel.uz
- [SERVER_ARXITEKTURA](#server_arxitektura) — Server arxitekturasi — oddiy tilda
- [SERVER_SOZLASH](#server_sozlash) — Yangi netcup serverlarini sozlash — qadamma-qadam qo'llanma
- [SERVER_OLCHOV_NATIJALARI](#server_olchov_natijalari) — Haqiqiy o'lchov natijalari (taxmin emas) — 2026-10-27
- [HISOB_EKRAN_ULASHISH_VA_TRAFIK_2026-11-17](#hisob_ekran_ulashish_va_trafik_2026-11-17) — Ekran ulashish bitrate'i va server trafigi: hisob-kitoblar va xulosa
- [HISOB_STEAL_VAQT_2026-11-17](#hisob_steal_vaqt_2026-11-17) — "Dedicated" yadrolar va steal time: tekshiruv natijasi

**3. Funksiyalar bo'yicha API hujjatlari**

- [NEW_FEATURES_API](#new_features_api) — Yangi backend funksiyalar (2026-09-03) — frontend uchun
- [LIVE_MODERATION_API](#live_moderation_api) — Dars moderatsiyasi: Invite / Ban / Guruhdan avtomatik chiqarish
- [MIC_REQUEST_GRANT](#mic_request_grant) — Mikrofon so'rov/ruxsat — yangi funksiya
- [ADMIN_TEACHERS_LIST_API](#admin_teachers_list_api) — Admin panel — o'qituvchilar ro'yxati (reyting bilan)
- [BACKEND_OQITUVCHI_PROGRESS](#backend_oqituvchi_progress) — O'qituvchi uchun o'quvchilar progressi (2026-11-03)
- [BACKEND_HOMEWORK_UPDATES](#backend_homework_updates) — Uy vazifasi (homework) — o'zgarishlar (frontend / mobil uchun)
- [HOMEWORK_NOTIFICATIONS_API](#homework_notifications_api) — Uy vazifasi bildirishnomalari — frontend uchun
- [BACKEND_AI_QUIZ](#backend_ai_quiz) — AI bilan test yaratish — imtihon qoidalari bo'yicha (frontend / mobil uchun)
- [BACKEND_QUIZ_GROUPS](#backend_quiz_groups) — Savollar guruhi — matn parchasi (Reading/SAT) va audio (Listening)
- [BACKEND_EXAMS](#backend_exams) — Imtihon (Mock test) — IELTS / SAT / Milliy sertifikat / custom
- [BACKEND_IELTS_WRITING](#backend_ielts_writing) — IELTS: Writing (insho), AI baholash, savol-savol tahlil — backend kontrakti
- [BACKEND_DOSKA_TAHRIR](#backend_doska_tahrir) — Doska: kod muharriri (Notepad++ uslubi) va elementni tahrirlash (Zoom uslubi) — backend tayyor
- [BACKEND_IOS_RECORDING](#backend_ios_recording) — Dars yozuvi — iOS uchun MP4 (backend javobi)

**4. Trello vazifalari va backend holati**

- [BACKEND_VAZIFALAR](#backend_vazifalar) — Backend uchun vazifalar (Trello kartalari, 2026-11)
- [BACKEND_YANGILANISHLAR_2026-11-10](#backend_yangilanishlar_2026-11-10) — Backend yangilanishlari (2026-11-10) — `BACKEND_VAZIFALAR.md` bo'yicha
- [BACKEND_TRELLO_VAZIFALAR_2026-11-18](#backend_trello_vazifalar_2026-11-18) — Trello "Yolup" doskasi: ochiq vazifalar, kod va serverga solishtirilgan (2026-11-18)
- [BACKEND_TRELLO_HOLAT_2026-11-18](#backend_trello_holat_2026-11-18) — Trello "Yolup": nima qilindi, nima tekshirildi, nima qoldi (2026-11-18, kechqurun)

**5. Frontend va mobil jamoa uchun (sana bo'yicha)**

- [FRONTEND_TODO_CAMERA_BOARD](#frontend_todo_camera_board) — Frontend uchun qolgan ishlar — kamera ruxsati + doska signali (2026-09-04)
- [FRONTEND_TODO_SCREEN_SHARE](#frontend_todo_screen_share) — Frontend: ekran ulashishda boshqaruv oynasi (Zoom / Google Meet kabi)
- [FRONTEND_TODO_2026-11-10](#frontend_todo_2026-11-10) — Frontend uchun qolgan ishlar (2026-11-10) — Trello kartalari bo'yicha
- [FRONTEND_YANGILANISHLAR_2026-11-11](#frontend_yangilanishlar_2026-11-11) — Frontend uchun: yangi backend imkoniyatlari (Trello "Todo" kartalari)
- [FRONTEND_YANGILANISHLAR_2026-11-11_2](#frontend_yangilanishlar_2026-11-11_2) — Frontend uchun: 11-noyabrdagi ikkinchi backend vazifalari javobi
- [FRONTEND_QOTISH_TAHLILI_2026-11-12](#frontend_qotish_tahlili_2026-11-12) — O'qituvchi kamerasi qotib qolishi: tahlil va frontend uchun tavsiyalar (2026-11-12)
- [FRONTEND_ROL_ALMASHTIRISH_2026-11-12](#frontend_rol_almashtirish_2026-11-12) — Frontend uchun: o'quvchi hisobidan rolga o'tish (`BACKEND_ROL_ALMASHTIRISH.md` javobi)
- [FRONTEND_ROL_ALMASHTIRISH_2026-11-12_2](#frontend_rol_almashtirish_2026-11-12_2) — Frontend uchun: o'quvchi hisobidan rol almashtirish — qoida aniqlashtirildi (2026-11-12, 2-qism)
- [FRONTEND_YANGILANISHLAR_2026-11-12](#frontend_yangilanishlar_2026-11-12) — Frontend uchun: 12-noyabr, uchinchi backend vazifalari javobi
- [FRONTEND_YANGILANISHLAR_2026-11-12_2](#frontend_yangilanishlar_2026-11-12_2) — Frontend uchun: 12-noyabr, Trello "Todo" kartalari bo'yicha backend yangiliklari
- [FRONTEND_AKKAUNT_BOGLASH_2026-11-13](#frontend_akkaunt_boglash_2026-11-13) — Frontend uchun: akkauntlarni bog'lash xavfsizligi (`BACKEND_VAZIFALAR_2026-11-12.md` javobi)
- [FRONTEND_HOMEWORK_OVOZ_2026-11-13](#frontend_homework_ovoz_2026-11-13) — Frontend uchun: Speaking (ovozli) uy vazifasi — brauzerda yozilgan ovoz endi qabul qilinadi
- [FRONTEND_HOMEWORK_OVOZ_2026-11-13_2](#frontend_homework_ovoz_2026-11-13_2) — Frontend uchun: Speaking uy vazifasiga ovoz yuborish (yangi eslatma)
- [FRONTEND_DARSGA_KIRISH_2026-11-15](#frontend_darsga_kirish_2026-11-15) — Frontend uchun: o'quvchi darsga faqat o'qituvchi boshlagandan keyin kiradi
- [FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16](#frontend_javob_darsga_taklif_2026-11-16) — Backend javobi: darsga taklif bildirishnomasida havola qo'shildi (Trello 60)
- [FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16](#frontend_javob_ekran_yozuv_2026-11-16) — Backend javobi: ekran ulashish o'chirib-yoqilganda yozuv uzilmasin (Trello 62)
- [FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17](#frontend_javob_material_sonlari_2026-11-17) — Backend javobi: guruh papkasida video va doska soni (Materiallar)
- [FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17](#frontend_ulanmagan_endpointlar_2026-11-17) — Frontend ulamagan backend endpointlari — aniq ro'yxat (2026-11-17)
- [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18](#frontend_email_kirish_va_tiklash_2026-11-18) — Email: ro'yxatdan o'tish, email bilan kirish, parolni emailga kod bilan tiklash (2026-11-18)
- [FRONTEND_JAVOB_AI_RASM_2026-11-18](#frontend_javob_ai_rasm_2026-11-18) — Uy vazifasi: AI rasmlarni to'g'ri o'qiydi (2026-11-18)
- [FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18](#frontend_javob_parol_ozgartirish_2026-11-18) — Javob: "Parolni o'zgartirish" (BACKEND_PAROL_OZGARTIRISH.md bo'yicha), 2026-11-18
- [FRONTEND_VAZIFALAR_2026-11-18](#frontend_vazifalar_2026-11-18) — Frontend uchun vazifalar: backend tayyor, frontend qiladigan ishlar (2026-11-18)
- [FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY](#frontend_yangilanishlar_2026-11-18_yakuniy) — Frontend uchun: bugun backendda nima qilindi va frontendda nima qoldi (2026-11-18, yakuniy)
- [FRONTEND_YANGILANISHLAR_2026-11-19](#frontend_yangilanishlar_2026-11-19) — Frontend va mobil jamoa uchun: 2026-11-19 yangilanishlari
- [FRONTEND_YANGILANISHLAR_2026-11-21](#frontend_yangilanishlar_2026-11-21) — Frontend va mobil jamoa uchun: 2026-11-21 (kirish tarixi qurilmalar bo'yicha, chat rasmi, dars vaqtidan oldin kirish)


---

<!-- 1. Loyiha va arxitektura -->

## PROJECT

> Avvalgi fayl: `PROJECT.md`

### Fokus — Onlayn Ta'lim Platformasi (umumiy hujjat)

O'zbekiston maktab o'quvchilari uchun onlayn ta'lim platformasi: jonli video
darslar, Telegram uslubidagi chat, interaktiv doska, AI uy vazifasi tekshiruvi
va ota-ona nazorati. **Bu repo — faqat backend (API)**; frontend alohida
loyihada rivojlantiriladi va shu API'ni chaqiradi.

- Prod: `https://edu.thesofmebel.uz` (API), Swagger: `/api/docs/`
- Repo: `https://github.com/krv006/Education-Tech-Platform`
- Arxitektura qoidalari: [ARCHITECTURE.md](#architecture) · Deploy: [DEPLOY.md](#deploy)

---

#### 1. Stack

| Qatlam | Texnologiya |
|---|---|
| Backend | Django 6 + DRF + SimpleJWT (ASGI) |
| Real-time (chat + doska) | Django Channels 4 + Redis channel layer (WebSocket) |
| Video darslar | LiveKit (self-hosted, WebRTC) + Egress (dars yozuvi MP4) |
| DB / Cache | PostgreSQL 17 / Redis 7 (dev'da sqlite/in-memory fallback) |
| Admin panel | Django admin + **Jazzmin** (Fokus brendi, ikonkalar) |
| Loglar | Fayl rotatsiya: `logs/app.log`, `logs/errors.log` (`make applog/errlog`) |
| Server | Docker Compose: gunicorn+uvicorn worker, Caddy (TLS + proxy) |

#### 2. Arxitektura

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

#### 3. Modullar

| Modul | Nima qiladi | Asosiy endpointlar |
|---|---|---|
| `apps/accounts` | JWT auth, 4 rol (teacher/student/parent/admin), ota-ona↔bola bog'lash (taklif-kod + bolaning tasdig'i), rozilik (consent) | `/api/v1/auth/*` |
| `apps/lessons` | Kurs, dars jadvali, yozilish (enroll), davomat hisoboti | `/api/v1/courses/`, `/api/v1/lessons/`, `/api/v1/attendance/` |
| `apps/live` | LiveKit token, avtomatik davomat (kirdi/chiqdi), "Siz shu yerdamisiz?" diqqat tekshiruvi (random, 15s), fokus jurnali (oynadan chiqib-kirish) | `/api/v1/live/*` |
| `apps/chat` | Telegram uslubi: har kurs = guruh chat; direct faqat o'qituvchi↔o'quvchi (1 martalik so'rov → qabul/block); real-time WebSocket | `/api/v1/chat/*`, `ws /ws/chat/<room_id>/` |
| `apps/board` | Jonli dars doskasi, **real-time WebSocket** (polling yo'q): qalam, marker (shaffof), chiziq/strelka, to'rtburchak, ellips, matn — bari saqlanadi va PDF'ga tushadi; bir nechta sheet; o'chirish SABABI majburiy (jurnal); dars tugagach PDF → kurs chatiga. **Matematik rejim FAQAT matematika kurslarida** (`math_enabled`): MathLive LaTeX bloklari + SymPy yechuvchi | `/api/v1/board/<lesson_id>/*`, `ws /ws/board/<lesson_id>/` |
| `apps/homework` | Uy vazifasi: o'qituvchi vazifani rich-matn (sanitized HTML) yoki fayl (Word/PDF/rasm) bilan beradi, muddat qo'yadi; o'quvchi PDF/rasm/DOCX (Speaking'da audio) topshiradi; o'qituvchi ballni o'zi qo'yib tasdiqlaydi (AI tekshiruv olib tashlangan); statistika, kech topshirish belgisi | `/api/v1/homework/*` |
| `apps/core` | UUID+timestamp baza modellari, soft-delete, RBAC, audit log, yagona xato formati | — |

#### 4. Rollar (RBAC qisqacha)

- **O'qituvchi:** kurs/dars yaratish, doska boshqaruvi, vazifa berish/natijalar,
  chat guruhlari, direct so'rovlarni qabul/block
- **O'quvchi:** darsga kirish, doskada ruxsat so'rash, vazifa topshirish,
  chat (guruh + faqat o'qituvchi bilan direct)
- **Ota-ona:** bola hisobini yaratish/bog'lash (bola tasdig'i bilan), davomat,
  fokus jurnali, vazifa natijalarini ko'rish
- To'liq matritsa: `apps/core/permissions.py` (`ROLE_PERMISSIONS`)

#### 5. Real-time (WebSocket)

Ikkala kanal ham JWT bilan: `?token=<access>`. Yopilish kodlari: `4401` token
yaroqsiz, `4403` a'zo emas.

##### 5.1 Chat — `wss://<domain>/ws/chat/<room_id>/`

| Yo'nalish | Payload | Izoh |
|---|---|---|
| C→S | `{"type":"message","text":"..."}` | Xabar yuborish (REST `POST .../send/` bilan teng kuchli) |
| C→S | `{"type":"typing"}` | "Yozmoqda..." signali |
| S→C | `{"type":"message","message":{id,room,sender,text,created_at}}` | Yangi xabar (REST orqali yuborilgani ham keladi) |
| S→C | `{"type":"typing","user_id","name"}` | Kimdir yozmoqda (o'zingizni filtrlang) |
| S→C | `{"type":"error","detail"}` | Yuborish xatosi |

##### 5.2 Doska — `wss://<domain>/ws/board/<lesson_id>/` (polling KERAK EMAS)

Boshlang'ich holat: REST `GET /api/v1/board/<lesson_id>/`, keyin faqat WS.

| Yo'nalish | Payload |
|---|---|
| C→S | `{"type":"stroke","sheet":0,"stroke":{...}}` — element qo'shish (REST bilan teng kuchli) |
| S→C | `{"type":"stroke","sheet","stroke"}` / `{"type":"erase","sheet","stroke_ids","by","reason"}` / `{"type":"sheet","index"}` / `{"type":"error","detail"}` |

##### 5.3 Doska stroke turlari (bari doimiy saqlanadi va PDF'ga tushadi)

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

#### 6. Uy vazifasi oqimi

1. O'qituvchi vazifa beradi (rich matn `nh3` bilan sanitize, ixtiyoriy fayl, muddat, til fanlari uchun skill: writing/reading/listening/speaking)
2. O'quvchi fayl topshiradi → `Submission(status=pending_review)` → o'qituvchiga bildirishnoma
3. O'qituvchi ballni (0-100) o'zi qo'yib tasdiqlaydi → `status=done`, natija o'quvchi/ota-onaga ochiladi
4. AI (Gemini) tekshiruv loyihadan olib tashlangan (2026-10) — AI kerak bo'lsa alohida tayyor repolar ishlatiladi

#### 7. Muhit o'zgaruvchilari (asosiylari)

| Env | Nima uchun |
|---|---|
| `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Django |
| `CORS_ALLOWED_ORIGINS` | **Frontend domeni SHU YERGA yoziladi** (vergul bilan) |
| `POSTGRES_*` | DB (bo'lmasa sqlite) |
| `REDIS_URL` | Cache + WebSocket channel layer (prod'da shart) |
| `LIVEKIT_API_KEY/SECRET/URL` | Video darslar |

To'liq namuna: `.env.prod.example` (prod), `.env.example` (dev).

#### 8. Ishga tushirish

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

#### 9. Testlar

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

#### 10. EduTech.docx talablar holati

- ✅ Telegram uslubidagi chat, 1 martalik direct so'rov, block
- ✅ Kurs = guruh chat; o'quvchilar orasida DM yo'q
- ✅ Diqqat tekshiruvi (dars bo'ylab teng yoyilgan: har ~24 daqiqaga 1 ta, 2 soat = 5 ta; 15s; vaqti sirlangan)
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

#### 11. LiveKit resurs optimizatsiyasi

- **Simulcast** (har kamera 3 o'lcham) + **adaptiveStream** (ko'rinmagan video
  to'xtaydi, plitka o'lchamiga mos layer) + **dynacast** (keraksiz layerni
  publisher o'chiradi) — frontend Room sozlamalari, tayyor kod README'da
- **Layout:** spiker katta / qolganlar thumbnail — grid emas (shunda yuqoridagilar
  maksimal ishlaydi)
- **Server tomonda:** egress 720p/30 preset (CPU ~2x kam), egress konteyneriga
  `cpus:2, mem_limit:2g` chegara, bo'sh xona 5 daqiqada yopiladi
  (`empty_timeout`), Redis `maxmemory 256mb volatile-ttl`

#### 12. Keyingi qadamlar

1. Desktop app (Electron qobiq): skrinshot-himoya + ikkinchi ekran nazorati + kiosk
2. Video ustiga o'quvchi ismli watermark
3. Mobil ilova (WebView + FLAG_SECURE)
4. Bitta sessiya cheklovi (yangi login eski tokenni bekor qiladi)


[↑ Mundarija](#mundarija)

---

## ARCHITECTURE

> Avvalgi fayl: `ARCHITECTURE.md`

### Fokus — Backend Arxitektura

Bu hujjat tizimning qatlamli arxitekturasini, qoidalarini va nima uchun shunday
qurilganini tavsiflaydi. **Yangi kod yozishdan oldin shu qoidalarga qarang.**

#### 1. Qatlamlar (Layered Architecture)

```
HTTP so'rov
   │
   ▼
┌─────────────────────────────────────────────────┐
│  MIDDLEWARE   RequestID → CORS → Auth → Throttle │
├─────────────────────────────────────────────────┤
│  VIEW (yupqa) faqat: parse → service → serialize │   apps/*/views.py
├────────────────────────┬────────────────────────┤
│  SERVICE (yozish)      │  SELECTOR (o'qish)      │   services.py / selectors.py
│  biznes-qarorlar,      │  "kim nimani ko'radi"   │
│  transaction, audit    │  querylari              │
├────────────────────────┴────────────────────────┤
│  MODEL   UUID PK · timestamps · soft delete      │   models.py
└─────────────────────────────────────────────────┘
```

##### Qat'iy qoidalar

1. **View'da biznes-logika YO'Q.** View faqat HTTP bilan ishlaydi. Qaror qabul
   qilish (`if role == ...`, holat o'zgartirish) — service'da.
2. **Yozuv faqat service orqali.** Har bir service `@transaction.atomic` va
   muhim harakatda `audit.record()` chaqiradi.
3. **Ko'rish huquqi faqat selector'da.** Ota-ona faqat APPROVED bog'lanishdagi
   bolasini ko'rishi — bu selector'larda kodlangan, view unutib qo'yolmaydi.
4. **Ruxsatlar faqat registry'da** (`apps/core/permissions.py`). View'da
   `RequirePerm('kalit')` ishlatiladi, rol tekshiruvi qo'lda yozilmaydi.

#### 2. Core qatlam (`apps/core`)

| Komponent | Vazifasi |
|---|---|
| `TimeStampedUUIDModel` | UUID PK (ID taxmin qilib bo'lmaydi) + created/updated |
| `SoftDeleteModel` | `delete()` belgilaydi, o'chirmaydi — huquqiy/audit talab |
| `AuditLog` + `audit.record()` | FRD security.audit: kim, qachon, nima qildi, qaysi IP |
| `permissions.py` | FRD RBAC matritsasi kodda — rol → ruxsat kalitlari |
| `exceptions.py` | Yagona xato formati (pastda) |
| `middleware.RequestIDMiddleware` | Har so'rovga X-Request-ID — log/debug bog'lash |
| `pagination.py` | Default 20, `?page_size=` max 100 |
| `views.HealthView` | `GET /api/health/` — DB + cache monitoring |

#### 3. Xato formati (Error Envelope)

Barcha xatolar bitta shaklda — frontend bitta handler yozadi:

```json
{
  "success": false,
  "error": {
    "code": "permission_denied",
    "message": "Sizning rolingizda bu amal uchun ruxsat yo'q.",
    "details": { }
  }
}
```

Kutilmagan xatolar (500) log'ga to'liq yoziladi, mijozga ichki tafsilot chiqmaydi.

#### 4. RBAC — ruxsat kalitlari

Rollar: `super_admin`, `admin`, `teacher`, `student`, `parent` (+ guest = anonim).
Kalitlar FRD uslubida: `course.create`, `lesson.finish`, `link.request`,
`consent.manage`, `room.token` ... To'liq matritsa: `apps/core/permissions.py`.

Rolga ruxsat qo'shish/olish — faqat o'sha faylda bitta satr.

#### 5. Xavfsizlik

- **JWT** (60 daq access / 7 kun refresh, refresh rotation)
- **Rate limiting:** anon 60/min, user 240/min, auth endpointlar 30/min (bruteforce)
- **Rozilik modeli:** ota-ona kuzatuvi faqat bola tasdig'i bilan (ParentChildLink),
  bola istalgan payt uzadi; Consent bayroqlari (camera/recording/analytics)
- **Audit log:** har muhim harakat (register, link, consent, dars, room join) yoziladi
- **Prod hardening:** `DJANGO_ENV=prod` — HSTS, secure cookies, SSL redirect,
  insecure SECRET_KEY bilan ishga tushmaydi

#### 6. Muhitlar

```
root/settings/
  base.py   — umumiy (DRF, JWT, RBAC, LiveKit, logging)
  dev.py    — DEBUG, sqlite fallback, locmem cache
  prod.py   — Postgres majburiy, security headers
```

`DJANGO_ENV=prod` bilan prod rejim. Hamma sozlama `.env` dan.

#### 7. Kengayish nuqtalari (keyingi bosqichlar)

| Ehtiyoj | Qayerga qo'shiladi |
|---|---|
| To'lov (Click/Payme) | `apps/payments` — service qatlami tayyor naqsh |
| OTP (Eskiz SMS) | `apps/accounts/services.py` + `auth` throttle scope bor |
| Chat | LiveKit data channels yoki `apps/chat` (WebSocket/Channels) |
| Fokus hodisalari | `apps/focus` — exit_log FRD moduli, Attendance naqshida |
| Celery (hisobot, eslatma) | Redis allaqachon compose'da |

#### 8. Testlar

```bash
python manage.py test          # 14 test: auth, link/consent, RBAC, davomat, soft-delete
python scripts/smoke_test.py   # jonli e2e: 18 tekshiruv
python manage.py seed_demo     # demo ma'lumot
```


[↑ Mundarija](#mundarija)

---

## COMPLETED_WORK

> Avvalgi fayl: `COMPLETED_WORK.md`

### Qilingan ishlar — to'liq API va funksiyalar ro'yxati

Bu — loyihada bajarilgan barcha backend ishlarining **yagona, jamlangan** hujjati
(oldin `STAFF_API.md`, `STUDENT_API.md`, `HOMEWORK_AI_REVIEW_API.md` va shu faylga
bo'lib yozilgan edi — endi bittaga birlashtirildi). Frontend jamoasi shu hujjat
asosida UI qura oladi: har bo'limda aniq endpoint, kim chaqira olishi, so'rov/javob
shakli berilgan.

**Base URL**: `/api/v1/`
**Auth**: JWT (`Authorization: Bearer <access_token>`)

---

#### Mundarija

1. [Rol va ruxsatlar](#1-rol-va-ruxsatlar)
2. [Auth / Accounts](#2-auth--accounts)
3. [Kurslar](#3-kurslar)
4. [Darslar va video yozuv](#4-darslar-va-video-yozuv)
5. [Davomat](#5-davomat)
6. [Live / video dars xonasi](#6-live--video-dars-xonasi)
7. [Chat](#7-chat)
8. [Doska / Whiteboard](#8-doska--whiteboard)
9. [Uyga vazifa (Homework + AI tekshiruv)](#9-uyga-vazifa-homework--ai-tekshiruv)
10. [Bildirishnomalar](#10-bildirishnomalar)
11. [O'quvchiga yopiq endpointlar](#11-oquvchiga-yopiq-endpointlar)

---

#### 1. Rol va ruxsatlar

`apps/core/permissions.py`:

```
super_admin: '*' (hammasi)
admin:       course.view, course.moderate, lesson.view, lesson.cancel,
             attendance.view, audit.view, user.manage, notification.send
teacher:     course.create/edit/view/enroll, lesson.schedule/edit/cancel/finish/view,
             lesson.rate, room.token, room.moderate, attendance.view, chat.use,
             homework.assign/view, child.create
student:     course.view/enroll, lesson.view/rate, room.token/leave, link.respond,
             attendance.view, chat.use, homework.submit/view
parent:      child.create, link.request/view, consent.manage,
             course.view/enroll, lesson.view, attendance.view, homework.view
```

**Muhim eslatmalar**:
- `admin`da `course.create/edit`, `chat.use`, `homework.assign`, `room.token` **yo'q** — admin faqat ko'rish/moderatsiya + bildirishnoma yuborish + foydalanuvchi qidirish uchun, kurs/dars/chatni faqat `super_admin` (wildcard) boshqara oladi.
- `parent`da `chat.use` **yo'q** — ota-ona chatga umuman kira olmaydi (na REST, na WebSocket), garchi farzandining darsi/vazifasi/davomatini ko'rsa ham.
- `course.moderate`/`lesson.cancel` ruxsatlari admin ro'yxatida bor, lekin ularni tekshiradigan **hech qanday endpoint yo'q** (ulanmagan).
- **Bitta akkaunt = bitta qurilma cheklovi olib tashlangan** — endi bir akkaunt bilan bir vaqtda istalgancha qurilmadan kirish mumkin (qarang: §2).

---

#### 2. Auth / Accounts (`/api/v1/auth/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| POST | `/auth/register/` | Hammaga ochiq, lekin `role` faqat `teacher`\|`parent` | `username, password, first_name, last_name, role, phone` | `id, username, first_name, last_name, role, phone` | Ochiq ro'yxatdan o'tish (o'quvchi faqat `/children/` orqali yaratiladi) |
| POST | `/auth/login/` | Hammaga ochiq | `username, password` | `refresh, access` | Login. **Bir akkaunt bilan bir vaqtda istalgancha qurilmadan kirish mumkin** (cheklov olib tashlangan) |
| POST | `/auth/logout/` | Login qilgan | `refresh`(ixtiyoriy) | 204 | Chiqish — berilgan refresh token bekor qilinadi (qayta ishlatib bo'lmaydi); boshqa qurilmalardagi sessiyalarga ta'sir qilmaydi |
| POST | `/auth/token/refresh/` | — | `refresh` | `access` | Access tokenni yangilash |
| GET | `/auth/me/` | Login qilgan | — | `id, username, first_name, last_name, role, phone, invite_code, avatar` | O'z profili |
| PUT/PATCH | `/auth/me/` | Login qilgan | `username, first_name, last_name, phone, avatar`(multipart, rasm fayl) | yuqoridagidek | Profilni tahrirlash (profil rasmi shu orqali o'rnatiladi) |
| GET | `/auth/logins/?student=<id>` | O'zi; ota-ona (tasdiqlangan farzandi uchun) | — | ro'yxat: `{at, ip, user_agent, new_ip, new_device}` | Login tarixi (qurilma/IP o'zgargan hollari belgilangan) |
| POST | `/auth/children/` | teacher, parent (`child.create`) | `username, password, first_name, last_name` | `id, username, first_name, last_name, invite_code` | O'quvchi hisobini yaratadi. Ota-ona yaratsa — `ParentChildLink` darhol APPROVED. O'qituvchi yaratsa — bog'lanish yaratilmaydi, faqat `invite_code` beriladi |
| GET | `/auth/users/search/?q=` | admin, super_admin (`user.manage`) | — | `UserSerializer[]` (max 10) | Barcha rollar bo'yicha foydalanuvchi qidirish |
| GET | `/auth/links/` | student | — | ro'yxat: `id, parent, student, status, created_at, responded_at` | Ota-onadan kelgan bog'lanish so'rovlari |
| POST | `/auth/links/request/` | parent (`link.request`) | `invite_code` | link obyekti | Ota-ona bola invite_code'i orqali bog'lanish so'raydi (PENDING) |
| POST | `/auth/links/{id}/respond/` | student | `action`: `approve`\|`decline` | link obyekti | So'rovni tasdiqlash/rad etish |
| GET/POST | `/auth/consents/` | parent (`consent.manage`) | POST: `student, kind(recording\|camera\|analytics), granted` | `id, student, kind, granted, updated_at` | Ota-ona farzandi uchun rozilik belgilaydi |

---

#### 3. Kurslar (`/api/v1/courses/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/courses/` | student | `?search=` | ro'yxat: `CourseSerializer` | Yozilgan kurslarim |
| GET | `/courses/catalog/` | student | — | `CourseSerializer[]` | Barcha ochiq kurslar (yozilish uchun) |
| GET | `/courses/{id}/` | a'zolar | — | `CourseSerializer` | Kurs tafsiloti |
| POST | `/courses/` | teacher (`course.create`) | `title, subject, description` | `CourseSerializer` | Kurs yaratadi (guruh chati avtomatik ochiladi) |
| PUT/PATCH | `/courses/{id}/` | teacher (o'ziniki) | yuqoridagidek | `CourseSerializer` | Tahrirlash |
| DELETE | `/courses/{id}/` | teacher (o'ziniki) | — | 204 | **Qaytarib bo'lmaydi**: video yozuvlar, doska (chizma+PDF), chat xonasi+xabarlar+fayllar, barcha a'zolik butunlay o'chadi; darslar faqat yashiriladi (Davomat/Baho tarixi saqlanadi) |
| GET | `/courses/requests/` | teacher (`course.edit`) | — | `EnrollmentSerializer[]` | O'z kurslariga kelgan kutilayotgan yozilish so'rovlari |
| POST | `/courses/requests/respond/` | teacher | `enrollment_id, action(approve\|decline)` | `EnrollmentSerializer` | So'rovga javob |
| POST | `/courses/{id}/schedule/` | teacher (`lesson.schedule`) | `title, days:[0-6], start_time, end_time, weeks(1-52), start_date, note` | `{count, lessons:[...]}` (201) | Haftalik jadval bo'yicha ko'plab dars yaratadi; vaqt to'qnashuvini tekshiradi (`{conflicts:[...]}` 400) |
| GET | `/courses/{id}/search-students/?q=` | teacher (o'ziniki), admin | — | `[{...user, enroll_status}]` (max 10) | O'quvchi qidirish |
| GET | `/courses/{id}/students/` | teacher (o'ziniki), admin | — | `EnrollmentSerializer[]` | Kursga yozilgan o'quvchilar |
| POST | `/courses/{id}/enroll/` | student; teacher (o'ziniki); parent (farzandi uchun) | student: — ; teacher/parent: `student_id`/`student` | `EnrollmentSerializer` | Student uchun so'rov (`pending`); teacher/parent uchun **darhol APPROVED** |
| POST | `/courses/{id}/unenroll/` | teacher, parent, student | `student_id` | `{"removed": bool}` | Kursdan chiqarish. **Yon ta'sir**: chiqarilgan o'quvchining o'sha guruh chatida ochiq WebSocket ulanishi bo'lsa, server darhol `{"type": "removed"}` yuboradi va ulanishni `code=4403` bilan yopadi |

**`CourseSerializer`**: `id, teacher, title, subject, description, is_active, student_count, my_status, is_language_subject, created_at`
- `is_language_subject` — `course.subject`dan (`apps.homework.ai.detect_profile`) avtomatik aniqlanadi. Til fani bo'lsa `true`. Frontend shu asosida vazifa yaratishda "tekshiruv turi" (writing/reading/listening/speaking) tanlovini **faqat shunda** ko'rsatishi kerak.

---

#### 4. Darslar va video yozuv (`/api/v1/lessons/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/lessons/` | a'zolar | `?course=`, `?status=`, `?ordering=starts_at` | ro'yxat: `id, course, course_title, title, starts_at, duration_min, status, room_name, created_at, avg_rating, rating_count` | Mening darslarim |
| GET | `/lessons/{id}/` | a'zolar | — | yuqoridagidek | Dars tafsiloti |
| POST | `/lessons/` | teacher (`lesson.schedule`) | `course, title, starts_at, duration_min` | `LessonSerializer` | Bitta dars yaratadi (`starts_at` o'tgan vaqt bo'lishi mumkin emas) |
| PUT/PATCH | `/lessons/{id}/` | teacher (o'ziniki) | yuqoridagidek | `LessonSerializer` | Tahrirlash |
| DELETE | `/lessons/{id}/` | teacher (o'ziniki) | — | 204 | O'chirish (soft-delete) |
| POST | `/lessons/{id}/finish/` | teacher (o'ziniki, `lesson.finish`) | `recording_title`(ixtiyoriy) | `LessonSerializer` | Darsni yakunlaydi: davomatlarni yopadi, chatga `lesson_ended`, doska PDF'ini guruh chatga fayl sifatida tashlaydi, video yozuvni to'xtatadi |
| POST | `/lessons/{id}/rate/` | student | `stars`(1-5), `description`(ixtiyoriy) | `id, lesson, student, stars, description, created_at` | Tugagan darsga baho (dars `finished` bo'lishi shart) |
| GET | `/lessons/{id}/ratings/` | a'zolar | — | `LessonRating[]` | Darsga qoldirilgan barcha baholar |
| GET | `/lessons/{id}/recording/` | a'zolar | — | `{lesson_id, title, status, ready, created_at, ended_at, error, stream_url}` | Yozuv holati. `status`: `recording`\|`completed`\|`failed`. `stream_url` faqat `ready:true`da keladi |
| DELETE | `/lessons/{id}/recording/` | teacher (o'ziniki) | — | 204 | Yozuvni butunlay o'chiradi (fayl + baza) |
| GET | `/lessons/{id}/recording/stream/?t=<token>` | Auth shart emas — faqat imzolangan token | — | video/mp4 oqim (Range/seek qo'llab-quvvatlanadi) | Video oqimi |

**Video yozuv haqida muhim**: `stream_url` — **muddatli imzolangan havola (3 soat)**, doimiy URL emas — har safar `GET /recording/` bilan yangisini olish kerak. Yuklab olish tugmasi yo'q, faqat platforma ichida ko'rish (`inline`). Yozuv o'qituvchi darsga har kirganida **avtomatik** boshlanadi (720p/30fps preset — CPU tejash uchun), dars tugaganda to'xtaydi.

---

#### 5. Davomat (`/api/v1/attendance/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/attendance/` | teacher (o'z kurslari), parent (tasdiqlangan farzandi), student (o'zi), admin (hammasi) | `?lesson=`, `?student=` | ro'yxat: `id, lesson, lesson_title, student, joined_at, left_at, minutes, attention_total, attention_answered, focus_exits, focus{exits, away_seconds, longest_seconds, timeline:[{left_at, returned_at, seconds}]}, focus_alert` | Davomat yozuvlari |
| GET | `/attendance/{id}/` | yuqoridagidek | — | yuqoridagidek | Bitta yozuv tafsiloti |

`focus_alert` (`true`/`false`) — o'quvchi shu darsda diqqat-nazoratida belgilangan chegaradan (default **3** marta oynadan chiqish, `.env`dagi `FOCUS_PARENT_ALERT_THRESHOLD`) oshib ketganmi — ota-onaga signal shu orqali ko'rinadi.

---

#### 6. Live / video dars xonasi (`/api/v1/live/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| POST | `/live/token/` | teacher, student | `lesson_id` | `{token, url, room, is_teacher}` | LiveKit video xonaga kirish tokeni. O'qituvchi kirsa: dars `LIVE` bo'ladi, chatga `lesson_live`, video yozuv avtomatik boshlanadi. O'quvchi kirsa: davomat avtomatik belgilanadi |
| POST | `/live/leave/` | teacher, student | `lesson_id` | `{"updated": bool}` | Darsdan chiqish (davomat yopiladi) |
| GET | `/live/attention/?lesson_id=` | student | — | `{"check": null}` yoki `{"check": {id, due_at}}` | "Sen hali shu yerdamisan?" so'rovi bormi (polling) |
| POST | `/live/attention/` | student | `check_id` | `{"answered_at"}` | Attention check'ga javob |
| POST | `/live/focus/` | student | `lesson_id`, `kind`: `exit`\|`return` | `{"ok", "kind", "exit_count", "threshold", "parent_notified"}` | Anti-cheat: darsdan chiqib/qaytganini belgilash |
| POST | `/live/allow-share/` | teacher (o'ziniki, `room.moderate`) | `lesson_id, identity` | `{"ok": true}` | O'quvchiga ekran ulashish ruxsatini jonli beradi |
| POST | `/live/request-mic/` | student | `lesson_id` | `{"ok": true}` | **Yangi**: mikrofon so'rash ("qo'l ko'tarish") — o'qituvchiga doska WebSocket kanali orqali darhol ko'rinadi |
| POST | `/live/grant-mic/` | teacher (o'ziniki, `room.moderate`) | `lesson_id, student_id` | `{"ok": true}` | **Yangi**: o'quvchiga mikrofon ruxsatini jonli ochadi |
| POST | `/live/deny-mic/` | teacher (o'ziniki, `room.moderate`) | `lesson_id, student_id` | `{"denied": bool}` | **Yangi**: so'rovni rad etadi — ruxsat berilmaydi, faqat navbatdan chiqadi |
| POST | `/live/invite/` | teacher (o'ziniki, `room.moderate`) | `lesson_id`, `student_id`(ixtiyoriy) | `{"invited": N}` | **Yangi**: darsga taklif bildirishnomasi. `student_id` bo'lmasa — kursga yozilgan hammaga |
| POST | `/live/ban/` | teacher (o'ziniki, `room.moderate`) | `lesson_id, student_id` | `{"ok": true}` | **Yangi**: o'quvchini shu darsdan chetlashtiradi — hozir xonada bo'lsa darhol chiqaradi, qayta kirishini bloklaydi (faqat shu darsga, kursga emas) |
| POST | `/live/unban/` | teacher (o'ziniki, `room.moderate`) | `lesson_id, student_id` | `{"unbanned": bool}` | **Yangi**: chetlashtirishni bekor qiladi |

##### Mikrofon: standart holat o'zgardi

**Endi o'quvchi darsga kirganda mikrofon O'CHIQ holda kiradi** (kamera esa erkin) —
avval ikkalasi ham avtomatik yoqiq edi. O'quvchi gapirish uchun avval
`POST /live/request-mic/` chaqiradi ("qo'l ko'tarish"), o'qituvchi buni doska
WebSocket kanali orqali jonli ko'radi (`{"type": "mic_request", "student_id", "name"}`),
`POST /live/grant-mic/` bilan ruxsat beradi. Ruxsat berilgach, ikkala tomonga ham
(o'quvchining o'ziga — mikrofon tugmasini yoqish uchun; o'qituvchiga — kutish
ro'yxatidan olib tashlash uchun) doska kanali orqali `{"type": "mic_granted", "student_id"}`
signali keladi.

So'rov bazada ham saqlanadi (faqat WS xabari emas) — `GET /board/{lesson_id}/`
javobida (teacher uchun, `away_students` bilan bir qatorda) `pending_mic_requests:
[{student_id, name}]` maydoni bor, shuning uchun o'qituvchi so'rovdan keyin kirsa
yoki sahifani yangilasa ham joriy so'rovlar yo'qolib qolmaydi.

**Navbat qoidalari**: `pending_mic_requests` **FIFO** tartibida (birinchi so'ragan
birinchi); bitta o'quvchi bir vaqtda faqat bitta faol so'rovga ega (qayta-qayta
so'rasa dublikat yo'q); so'rov faqat `grant-mic` (ruxsat) yoki `deny-mic` (rad —
`{"type": "mic_denied", "student_id"}` signali bilan) orqali navbatdan chiqadi,
shundan keyingina o'quvchi yana so'ray oladi.

##### Darsdan chetlashtirish (invite/ban) — frontendda nima kutish kerak

- **Taklif** (`invite`) real-time bildirishnoma orqali keladi (mavjud `/ws/notifications/` kanali, yangisi shart emas): `{"type": "notification", "notification": {..., "description": "«<dars>» darsi boshlandi — hoziroq kiring."}}`.
- **Ban** qilingan o'quvchi hozir xonada bo'lsa — LiveKit client SDK'da `disconnected`/kicked hodisasi keladi. Qayta `POST /live/token/` chaqirsa — `403 {"code": "permission_denied", "message": "Siz bu darsdan chetlashtirilgansiz."}`.
- Ban faqat **shu bitta darsga** tegishli — boshqa darslarga yoki `Enrollment`ga ta'sir qilmaydi.

---

#### 7. Chat (`/api/v1/chat/`)

**Diqqat**: `chat.use` faqat `teacher` va `student`da bor — **`parent` chatga umuman kira olmaydi** (REST ham, WebSocket ham).

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/chat/rooms/` | teacher, student | — | ro'yxat: `id, kind(course/direct), course, direct_status, image, title, last_message{text, sender, created_at, file_url}, unread, other_user, live_lesson{id,title,room_name}\|null, updated_at` | Mening chat xonalarim. `live_lesson` bo'lsa — kurs guruhida hozir jonli dars ketyapti |
| GET | `/chat/rooms/{id}/` | a'zolar | — | yuqoridagidek | Xona tafsiloti |
| GET | `/chat/rooms/{id}/messages/` | a'zolar | `?after=<ISO datetime>` | xabarlar: `id, room, sender, text, file_url, created_at` | Xabarlar tarixi / polling |
| POST | `/chat/rooms/{id}/send/` | a'zolar | `text`(max 4000) | xabar obyekti | Xabar yuborish |
| POST | `/chat/rooms/direct/request/` | student | `teacher`(id/username) | `ChatRoomSerializer` | O'qituvchi bilan shaxsiy chat so'rovi |
| POST | `/chat/rooms/direct/respond/` | teacher (o'z shaxsiy xonasi) | `room_id, action(accept\|block)` | `ChatRoomSerializer` | Shaxsiy chat so'roviga javob |
| GET | `/chat/rooms/teachers/` | student | — | `[{...user, direct_status, room_id}]` | Mening o'qituvchilarim (shaxsiy chat boshlash uchun) |
| POST | `/chat/rooms/{id}/image/` | teacher (o'z kurs guruhi) | multipart: `image` | `ChatRoomSerializer` | Guruh chat rasmini o'rnatadi |
| GET | `/chat/files/{message_id}/` | a'zolar | — | fayl | Chatga biriktirilgan faylni ko'rish (doska PDF va h.k.) |

**WebSocket**: `wss://<domain>/ws/chat/<room_id>/?token=<JWT access>`
- Kelib turadi: `{type:"message", message:{...}}`, `{type:"typing", user_id, name}`, `{type:"lesson_live", lesson:{id,title,room_name}}`, `{type:"lesson_ended", lesson_id}`, `{type:"removed"}` (guruhdan chiqarilganda — ulanish `4403` bilan yopiladi)
- Yuboriladi: `{type:"message", text}`, `{type:"typing"}`

---

#### 8. Doska / Whiteboard (`/api/v1/board/{lesson_id}/`)

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/board/{lesson_id}/` | a'zolar | — | `{sheets:[{index, strokes}], can_draw, is_teacher, size, subject}` (teacher uchun qo'shimcha `away_students: [{student_id, name}]`, `pending_mic_requests: [{student_id, name}]`) | Doska holati |
| POST | `/board/{lesson_id}/stroke/` | a'zolar (ruxsat bilan) | `sheet`(int), `stroke` | saqlangan stroke | Chizish/matn qo'shish |
| POST | `/board/{lesson_id}/erase/` | a'zolar (ruxsat bilan) | `sheet`, `stroke_ids`, `reason`(majburiy) | `{"removed": count}` | O'chirish |
| POST | `/board/{lesson_id}/solve/` | a'zolar | `expr` | yechim | Formula yechish (Photomath uslubida) |
| GET | `/board/{lesson_id}/pdf/` | a'zolar | — | PDF | Doskani PDF yuklab olish |
| POST | `/board/{lesson_id}/sheet/` | teacher (o'ziniki, `room.moderate`) | — | `{"index": int}` | Yangi bo'sh sheet |
| POST | `/board/{lesson_id}/grant/` | teacher (o'ziniki, `room.moderate`) | `student_id` | `{"ok": true}` | O'quvchiga chizish ruxsati |

**WebSocket**: `wss://<domain>/ws/board/<lesson_id>/?token=<JWT access>`
- Kelib turadi: `{type:"stroke", ...}`, `{type:"erase", ...}`, `{type:"sheet", index}`, `{type:"focus", student_id, name, kind}` (teacher uchun — o'quvchi oynadan chiqdi/qaytdi), `{type:"mic_request", student_id, name}` (teacher uchun), `{type:"mic_granted", student_id}` (hammaga)
- Yuboriladi: `{type:"stroke", sheet, stroke}`

---

#### 9. Uyga vazifa (Homework + AI tekshiruv) (`/api/v1/homework/`)

##### 9.1 Asosiy endpointlar

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/homework/assignments/?course=<id>` | a'zolar | — | student: ro'yxat + `my_submission`; teacher: + `submissions_count` | Kurs bo'yicha vazifalar |
| GET | `/homework/assignments/{id}/` | a'zolar | — | teacher: `submissions[...]` (hammasi) + `stats`; student: faqat o'ziniki | Vazifa tafsiloti |
| GET | `/homework/assignments/{id}/file/` | a'zolar | — | fayl | Vazifaga biriktirilgan faylni yuklab olish |
| POST | `/homework/assignments/` | teacher (o'ziniki, `homework.assign`) | multipart/JSON: `course_id, title, description, body, due_at, skill_key(writing\|reading\|listening\|speaking), lesson_id(ixtiyoriy), extra_instructions, attachment` | `id, course_id, ..., lesson_id, lesson_title, is_language_subject, created_at` | Vazifa yaratadi. `lesson_id` — shu kursning **tugagan** darsiga bog'lash (400 aks holda). Bitta darsga bir nechta vazifa berish mumkin |
| DELETE | `/homework/assignments/{id}/` | teacher (o'ziniki) | — | 204 | Vazifani o'chiradi |
| POST | `/homework/assignments/{id}/submit/` | student | multipart: `file`(PDF/rasm/DOCX, yoki `speaking` uchun audio) | submission obyekti, `status="pending_review"` | Topshirish — AI tekshiruvi fonda boshlanadi |
| GET | `/homework/submissions/{id}/` | a'zolar | — | quyida (§9.2) | AI natijasini kuzatish (polling) |
| GET | `/homework/submissions/{id}/file/` | a'zolar | — | fayl | Topshirilgan faylni yuklab olish |
| POST | `/homework/submissions/{id}/recheck/` | teacher (o'ziniki, `homework.assign`) | — | teacher shaklida (§9.2) | AI tekshiruvini qayta ishga tushiradi |
| POST | `/homework/submissions/{id}/review/` | teacher (o'ziniki, `homework.assign`) | `overall_score`(ixtiyoriy), `grade`(ixtiyoriy), `result`(ixtiyoriy, to'liq JSON) | teacher shaklida | AI natijasini tasdiqlaydi — quyida §9.3 |
| POST | `/homework/assignments/{id}/focus/` | student | `kind`: `exit`\|`return` | `{"ok": true}` | Vazifa sahifasida vaqt kuzatuvi |

##### 9.2 AI baholash — ish oqimi: AI taklif qiladi, o'qituvchi tasdiqlaydi

Ilgari AI tekshirgach natija darhol `done` bo'lib hammaga ko'rinardi. Endi:

1. AI tekshiradi → status `pending_review` — bu AI'ning **taklifi**, hali yakuniy emas. **Bu bosqichda o'quvchi/ota-onaga natija ko'rinmaydi** (`overall_score`, `grade`, `result` — `null`), faqat status "ko'rib chiqilmoqda" ko'rinadi.
2. **Faqat o'qituvchi** shu bosqichda AI'ning taklifini (ball, baho, feedback) darhol ko'radi.
3. O'qituvchi ko'rib chiqadi — xohlasa ball/baho/feedbackni **tahrirlab**, `POST /review/` bilan tasdiqlaydi. Tasdiqlash **AI natijasining ustidan yoziladi** (bitta yakuniy natija). Shundan keyingina status `done` bo'ladi va natija o'quvchi/ota-onaga ochiladi.
4. AI'ning asl (o'zgarmas) natijasi audit/taqqoslash uchun fonda saqlanadi — faqat o'qituvchiga ko'rinadi.

**`Submission.status` qiymatlari**: `checking` (AI tekshiryapti) → `pending_review` (o'qituvchini kutmoqda) → `done` (tasdiqlangan) yoki `error`.

**Submission javobi — o'quvchi/ota-ona uchun**:
```json
{
  "id": "...", "assignment_id": "...", "student_id": "...", "student_name": "...",
  "file_name": "...", "status": "pending_review",
  "overall_score": null, "grade": "", "result": null,
  "error": "", "is_late": false, "created_at": "...", "checked_at": "..."
}
```
`status == "done"` bo'lsa `overall_score`/`grade`/`result` to'liq qiymat bilan qaytadi.

**Submission javobi — o'qituvchi uchun** (yuqoridagilarga qo'shimcha):
```json
{
  "overall_score": 78, "grade": "Yaxshi", "result": { "...": "AI/yakuniy natija" },
  "reviewed_at": null, "reviewed_by": null,
  "ai_overall_score": 78, "ai_grade": "Yaxshi", "ai_result": { "...": "AI'ning asl natijasi" },
  "focus": {
    "exits": 2, "away_seconds": 340, "longest_seconds": 210,
    "on_page_seconds": 610, "total_seconds": 950,
    "timeline": [{"left_at": "...", "returned_at": "...", "seconds": 210}]
  }
}
```
O'qituvchi `overall_score`ni **PENDING_REVIEW bosqichida ham darhol** ko'radi (AI taklifi) — faqat o'quvchi/ota-onadan yashiriladi. `ai_result`/`focus` faqat tafsilot javobida bor, ro'yxat ko'rinishida yo'q.

##### 9.3 Tasdiqlash

```
POST /homework/submissions/{id}/review/
{}                                                    → AI natijasi o'zgarishsiz tasdiqlanadi
{"overall_score": 90, "grade": "A'lo", "result": {...}}  → tahrirlab tasdiqlanadi
```
Faqat `status == "pending_review"` bo'lgan topshiriqni tasdiqlash mumkin (aks holda 400).

##### 9.4 Vaqt kuzatuvi (focus)

`focus_summary` — darslardagi diqqat kuzatuvi bilan bir xil chiqish/qaytish algoritmi, faqat yopilmagan chiqish `hozir`gacha hisoblanadi (vazifa sahifasida darsning "tugash" chegarasi yo'qligi sababli): `exits`, `away_seconds`, `longest_seconds`, `on_page_seconds`, `total_seconds`, `timeline`. Faqat o'qituvchiga ko'rinadi.

---

#### 10. Bildirishnomalar (`/api/v1/notifications/`)

**Modellar**: `Notification` (`sender, description, target_type(user\|all), created_at`), `NotificationRecipient` (`notification, user, read_at`).

| Method | Path | Rol | Body | Javob | Tavsif |
|---|---|---|---|---|---|
| GET | `/notifications/` | har kim | — | `InboxItemSerializer[]`: `id, notification{id,sender,description,target_type,created_at}, is_read, read_at, created_at` | O'z inbox'i |
| POST | `/notifications/{id}/read/` | qabul qiluvchi | — | `{"ok": true}` | O'qildi deb belgilash |
| GET | `/notifications/unread-count/` | har kim | — | `{"count": int}` | Bell/badge uchun |
| POST | `/notifications/send/` | admin, super_admin (`notification.send`) | `description`(HTML, `nh3` bilan tozalanadi — faqat formatlash teglari, rasm/skript yo'q), `target_type(user\|all)`, `user_id`(target_type=user bo'lsa majburiy) | `id, sender, description, target_type, created_at` | Bitta foydalanuvchiga yoki hammaga yuboradi (real-vaqt WS orqali ham) |
| GET | `/notifications/sent/` | admin, super_admin | — | `id, description, target_type, created_at, read_count, total_count` | Yuborilganlar ro'yxati |
| GET | `/notifications/{id}/recipients/` | admin, super_admin (o'zi yuborgan) | — | `[{user, read_at}]` | Kim o'qidi/o'qimadi |

**WebSocket**: `wss://<domain>/ws/notifications/?token=<JWT access>` — barcha rol uchun ochiq. Kelib turadi: `{"type":"notification", "notification":{...}}`. Ulanish yopilishi: `4401` — token yaroqsiz.

**Django admin** (`/admin/notifications/notification/`) — faqat ko'rish/jurnal; yuborish uchun ro'yxat tepasidagi "Yangi xabar yuborish" havolasi (`/admin/notifications/notification/send/`) orqali maxsus forma ishlatiladi (xom "Add" formasi ataylab o'chirilgan — u fan-out qatorlarini yaratmaydi).

---

#### 11. O'quvchiga yopiq endpointlar

Frontendda o'quvchi rolida ko'rsatilmasin:

- Auth: `/register/`, `/children/`, `/links/request/`, `/consents/` — faqat ota-ona/o'qituvchi
- Kurs/dars: yaratish/tahrirlash/o'chirish, `/courses/requests/`, `/courses/{id}/schedule/`, `/courses/{id}/search-students/`, `/courses/{id}/students/`, `/lessons/{id}/finish/` — faqat o'qituvchi/admin
- Live: `/live/allow-share/`, `/live/grant-mic/`, `/live/deny-mic/`, `/live/invite/`, `/live/ban/`, `/live/unban/` — faqat o'qituvchi
- Chat: `/chat/rooms/direct/respond/` — faqat o'qituvchi
- Doska: `/board/{id}/sheet/`, `/board/{id}/grant/` — faqat o'qituvchi
- Homework: vazifa yaratish/o'chirish, `/submissions/{id}/recheck/`, `/submissions/{id}/review/` — faqat o'qituvchi
- Notifications: `/notifications/send/`, `/notifications/sent/`, `/notifications/{id}/recipients/` — faqat admin/super_admin

**Frontend uchun umumiy eslatma**: yozilish va chat so'rovlari **async** (`pending` → tasdiqlash/rad etish kutiladi) — UI `status`/`my_status`/`direct_status` maydonlariga qarab holatni ko'rsatsin, darhol kirish huquqi berilgan deb hisoblamasin.


[↑ Mundarija](#mundarija)

---

## PUSHED_CHANGES

> Avvalgi fayl: `PUSHED_CHANGES.md`

### `asem-mirzaeva` branch — push qilingan o'zgarishlar

`main` bilan solishtirganda 3 ta commit, 14 ta fayl, 545(+)/9(-) qator.
Hech biri `main`ga merge qilinmagan — hozircha faqat shu branch'da,
PR ochilmagan.

```
git log main..asem-mirzaeva --oneline
f2a4d88 fix: grant TEACHER the room.leave permission
d68bbf1 perf(egress): lower lesson recording to 480p/15fps to cut CPU cost
740ea59 feat: live-room invite/ban moderation + auto-kick chat on unenroll
```

---

#### Commit 1 — `740ea59`: invite/ban moderatsiyasi + guruhdan avtomatik chiqarish

**Nima uchun:** Zoom uslubidagi talab — o'qituvchi darsga o'quvchilarni taklif
qila olishi, xohlaganini chetlashtira olishi kerak edi. Buni qurish jarayonida
alohida bog'liq bug ham topildi va tuzatildi (guruhdan chiqarilgan o'quvchining
ochiq chat WebSocket ulanishi avtomatik yopilmasligi).

##### Yangi endpointlar (`room.moderate` — faqat kurs o'qituvchisi)

| Endpoint | Vazifasi |
|---|---|
| `POST /api/v1/live/invite/` | `{lesson_id, student_id?}` — bittasiga yoki (student_id yo'q bo'lsa) hammasiga real-time bildirishnoma |
| `POST /api/v1/live/ban/` | `{lesson_id, student_id}` — xonadan chiqaradi + shu darsga qayta kirishni bloklaydi |
| `POST /api/v1/live/unban/` | Chetlashtirishni bekor qiladi |

##### Yangi model
`LessonBan` ([apps/lessons/models.py](apps/lessons/models.py)) — `lesson + student + banned_by`, migratsiya `0009_lessonban.py`. `issue_room_token()` endi shu jadvalni tekshiradi.

##### Kuchaytirilgan mavjud endpoint
`POST /courses/{id}/unenroll/` — endi o'chirilgan o'quvchining ochiq guruh-chat WebSocket ulanishi bo'lsa, `{"type": "removed"}` yuborib `code=4403` bilan yopadi (`apps/chat/realtime.py`: `broadcast_member_removed`, `apps/chat/consumers.py`: `chat_member_removed`).

##### Testlar
`apps/lessons/tests.py: InviteBanTests` (9 ta), `apps/chat/tests.py: test_unenroll_closes_removed_students_socket` (real WebSocket testi).

##### Hujjat
[LIVE_MODERATION_API.md](#live_moderation_api) — frontend uchun to'liq shartnoma (request/response, WS event'lari, xato holatlari).

---

#### Commit 2 — `d68bbf1`: dars yozuvini 480p/15fps'ga tushirish (CPU tejash)

**Nima uchun:** LiveKit egress CPU sarfini kamaytirish — 720p/30 preset o'rniga.

##### Kod o'zgarishi
`apps/live/services.py: _egress_start()` — `EncodingOptionsPreset.H264_720P_30` o'rniga custom `EncodingOptions(width=854, height=480, framerate=15, video_bitrate=900, audio_bitrate=64)`. **Muhim:** LiveKit'ning tayyor preset ro'yxatida 480p/540p umuman yo'q (faqat 720p/1080p) — shuning uchun `advanced` maydoni ishlatildi, tayyor preset emas.

##### Infra o'zgarishi
`docker-compose.prod.yml`: egress `cpus: 4 → 3` — **PROVISIONAL**, real `docker stats egress` bilan hali tasdiqlanmagan (izohda aniq yozilgan). LiveKit hujjati: room-composite egress 2-6 CPU oralig'ida ishlatishi mumkin, rezolyutsiyadan qat'iy nazar sobit emas.

##### Diqqat
Bu o'zgarish production'da **hali sinovdan o'tkazilmagan** — real dars yozib, CPU sarfini tekshirish kerak (buyruq: `docker stats egress`), aks holda yozuvlar "resource exhausted" bilan rad etilishi mumkin.

---

#### Commit 3 — `f2a4d88`: TEACHER'ga `room.leave` ruxsati

**Nima uchun:** Frontend `/api/v1/live/leave/`ni o'qituvchi uchun ham chaqiradi (WebRTC uzilganda tozalash), lekin RBAC registrida bu ruxsat faqat STUDENT'da bor edi — o'qituvchi har safar `403` olardi (real skrinshotda ko'ringan xato).

##### Kod o'zgarishi
`apps/core/permissions.py`: `TEACHER` ro'yxatiga `'room.leave'` qo'shildi (1 qator). Xavfsiz — `mark_left()` o'qituvchi uchun mos Attendance topmasa, shunchaki `False` qaytaradi.

---

#### Push qilinmagan, hali ochiq masalalar

- **2 ta stuck LIVE dars** (`lesson-a9371dba4a2a`, `lesson-4edbb7705271`) — production serverda qo'lda `FINISHED`ga o'tkazish kerak (admin panel yoki `manage.py shell`), avtomatik tozalovchi hali yozilmagan.
- **`ENGINEERING_DEEP_DIVE.md`** — lokal, hali push qilinmagan (LiveKit/backend konseptual hujjat).
- **480p/`cpus: 3`** — real serverda tasdiqlanmagan, deploy qilishdan oldin `docker stats` bilan tekshirish kerak.
- **Doskaga chizish uchun "ruxsat so'rash" tugmasi** — backend'da bunday endpoint umuman yo'q (faqat o'qituvchi tomondan `grant/` bor), qurish rejalashtirilgan, hali boshlanmagan.


[↑ Mundarija](#mundarija)

---


---

<!-- 2. Server, deploy va o'lchovlar -->

## DEPLOY

> Avvalgi fayl: `DEPLOY.md`

### Deploy — edu.thesofmebel.uz

Bitta `docker compose` bilan hammasi ko'tariladi: Postgres, Redis, LiveKit, Django (gunicorn), Caddy (TLS + reverse proxy).

**Frontend alohida loyihada** (boshqa jamoa/hosting) — u shu domendagi API'ni chaqiradi.
Frontend domenini `.env` dagi `CORS_ALLOWED_ORIGINS` ga qo'shishni unutmang.

#### Arxitektura

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

#### 1. DNS

`edu.thesofmebel.uz` uchun **A record** -> server IP. (Caddy sertifikat olishi uchun DNS avval ishlashi shart.)

#### 2. Server portlari (firewall/UFW da oching)

- `80/tcp`, `443/tcp`, `443/udp` — Caddy
- `7881/tcp` — LiveKit TCP fallback
- `7882/udp` — LiveKit WebRTC media (UDP mux — bitta port, minglab ulanish)

#### 3. Ishga tushirish — bitta buyruq

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

#### 4. Yangilash

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

#### Muammolar

- **Sertifikat olinmayapti** — DNS hali tarqalmagan yoki 80-port yopiq. `docker compose -f docker-compose.prod.yml logs caddy`
- **Video/audio ulanmayapti (signaling ishlaydi, media yo'q)** — UDP portlar yopiq, yoki LiveKit tashqi IP ni topolmayapti. `docker-compose.prod.yml` da livekit `command` ga qo'shing: `--node-ip <SERVER_PUBLIC_IP>`
- **502 /api da** — backend hali ko'tarilmagan: `docker compose -f docker-compose.prod.yml logs backend`


[↑ Mundarija](#mundarija)

---

## SERVER_ARXITEKTURA

> Avvalgi fayl: `SERVER_ARXITEKTURA.md`

### Server arxitekturasi — oddiy tilda

Bu hujjat **nima qayerda ishlashi, nega shunday va nima yiqilsa nima bo'lishini** tushuntiradi. Sozlash qadamlari: `SERVER_SOZLASH.md`. O'lchovlar: `SERVER_OLCHOV_NATIJALARI.md`.

#### 3 ta asosiy qoida
1. **Jonli dars hech qachon och qolmasin.** Video, chat va darsga kirish eng muhim. Boshqa hech narsa ularning resursini yeb qo'ymasligi kerak.
2. **Kechiktirsa bo'ladigan ishlarga chegara qo'yamiz.** Yozuvni MP4 qilish 1 soat kechiksa hech narsa bo'lmaydi, shuning uchun u har doim cheklangan yadro va eng past ustuvorlik bilan ishlaydi.
3. **Bitta serverning muammosi ikkinchisini yiqitmasin.**

#### Ikki server

```
Foydalanuvchi (telefon / kompyuter)
        │
        ├──► edu.thesofmebel.uz ──► APP server (RS 2000: 8 yadro, 16 GB)
        │                           ├─ Caddy     : kirish eshigi (HTTPS)
        │                           ├─ web       : sayt API
        │                           ├─ ws        : chat, doska (real vaqt)
        │                           ├─ Postgres  : baza
        │                           ├─ Redis     : tezkor xabar almashish
        │                           └─ cron      : eslatmalar, AI, avto-yakunlash
        │                                │  yozuv so'rovlari (/api/v1/lessons/<id>/recording...)
        │                                ▼  yopiq kanal (WireGuard 10.10.0.x)
        └──► lk.thesofmebel.uz  ──► MEDIA server (RS 4000: 12 yadro, 32 GB + qo'shimcha disk)
                                    ├─ LiveKit     : jonli dars video/ovoz      (eng ustuvor)
                                    ├─ rec         : yozuv API'si (bo'lak qabul qilish, birlashtirish, ko'rsatish)
                                    ├─ rec-cron    : qotgan yozuvni tiklash, yetim fayl tozalash, disk ogohlantirishi
                                    ├─ transcoder  : yozuvni MP4 qiladi        (eng past ustuvor, 3 yadro bilan cheklangan)
                                    └─ yozuv fayllari (katta ma'lumot shu yerda)
```

**Nega shunday bo'lindi:** eng katta yuk — jonli dars va yozuv. Shuning uchun kuchli server (RS 4000) ularga berildi. Baza kichik (0.16 GB, yiliga ~6 GB), uni sayt bilan bir joyda saqlash saytni tez qiladi. MEDIA'dagi `rec` bazaga yopiq kanal orqali ulanadi.

#### Funksiyalarning og'irligi va joyi
| Funksiya | Nimani yeydi | Qachon | Joyi |
|---|---|---|---|
| Jonli video (LiveKit) | CPU va tarmoq | dars boshlanishida to'lqin | **MEDIA** |
| Yozuv bo'laklarini qabul qilish | disk yozish, CPU kam | dars davomida doimiy | **MEDIA** |
| Yozuvni MP4 qilish | CPU (og'ir) | dars tugagach to'lqin, kechiktirsa bo'ladi | **MEDIA**, 3 yadro bilan cheklangan |
| Yozuvni tomoshabinga berish | tarmoq (katta fayl) | doimiy | **MEDIA** (keyin Cloudflare) |
| Yozuv fayllari | disk | o'sib boradi | **MEDIA** (+ qo'shimcha disk) |
| Sayt API, login | CPU | to'lqin | **APP** |
| Chat, doska (WebSocket) | ko'p ulanish, CPU kam | doimiy | **APP** |
| Baza, Redis | RAM, CPU kam | doimiy | **APP** |
| Fon ishlari, AI, zaxira | CPU kam | kechiktirsa bo'ladi | **APP** |

#### Ustuvorlik qanday ta'minlanadi (MEDIA serverda)
| Xizmat | CPU ustuvorligi (`cpu_shares`) | Yadro chegarasi |
|---|---|---|
| LiveKit | 4096 (eng yuqori) | cheklanmagan |
| rec (yozuv API) | 1024 | 3 yadro |
| rec-cron | 256 | – |
| transcoder | 256 + `nice 15` | 3 yadro |

CPU yetmay qolsa, Linux avval LiveKit'ga beradi, yozuvni MP4 qilish esa kutadi.

#### Qanday holatlar bo'lishi mumkin
| Holat | Nima bo'ladi | Tayyorgarlik |
|---|---|---|
| 60 dars bir vaqtda boshlanadi | 1 500 o'quvchi 2–3 daqiqada kiradi: login, token, video | refresh token 7 kun (login kam); kirish tokeni arzon (~10 ms); LiveKit alohida serverda; `THROTTLE_AUTH` sozlanadi |
| 60 dars bir vaqtda tugaydi | 60 ta birlashtirish va MP4, ~5 soat navbat | navbat bitta-bitta, transcoder cheklangan; qotib qolsa avto-tiklash (`recover_recordings`); navbat vaqtida WebM ko'rinadi |
| Test yoki vazifa muddati tugashi | hamma bir daqiqada topshiradi | baza ulanishlari puli; AI alohida jarayonda. **Yuk ostida o'lchanmagan** |
| Bitta katta dars (500+) | bir xona bitta serverda | MEDIA'da zaxira bor (500 tomoshabin ≈ 1.6 yadro o'lchangan) |
| Maktab Wi-Fi'si (bitta IP) | ko'p o'quvchi bir IP'dan, kirish bloklanadi | `THROTTLE_AUTH` ni oshirish (`.env`) |
| Disk to'lishi | yozuvlar 9–20 GB/kun | `check_disk`: 80% va 90% da adminlarga bildirishnoma; `prune_recordings`; keyin Cloudflare |
| Kurs o'chiriladi | yozuv fayllari MEDIA'da qoladi | `prune_orphan_recordings` (har soat) yetim fayllarni o'chiradi (48 soatdan eski, bir martada ≤50) |
| Tarmoq limiti (3 TB/kun, so'ng 300 Mbit/s) | video va yozuv ko'rish MEDIA'dan chiqadi | yozuv ko'rishni Cloudflare'ga chiqarish (keyin) |
| Hujum, bot | login taxmin qilish, DDoS | sayt API oldiga Cloudflare (keyin). LiveKit oldiga qo'yib bo'lmaydi (video to'g'ridan-to'g'ri ulanadi) |
| Dars paytida deploy | chat uziladi | darsdan tashqari vaqtda; video uzilmaydi, chunki LiveKit alohida |

#### Biri yiqilsa nima bo'ladi
| Yiqilgan | Ishlayveradi | Ishlamaydi |
|---|---|---|
| **MEDIA** | sayt, chat, baza, doska | yangi jonli dars videosi, yozuv yuklash va ko'rish. Brauzer yozuv bo'laklarini saqlab turadi va keyin yuboradi |
| **APP** | allaqachon ulangan video (LiveKit mustaqil) | saytga kirish, darsga qo'shilish, chat, yozuv API'si (baza yo'q) |
| **WireGuard kanali** | APP'ning hammasi, LiveKit | faqat yozuv bilan bog'liq: MEDIA'dagi `rec` bazaga ulana olmaydi |

**Eng xavfli nuqta:** baza APP'da bitta. Himoya: har kecha `backup.sh` bazani MEDIA serverga ko'chiradi. Tiklashni bir marta sinab ko'rish kerak.

#### Ikki serverda yozuv fayllari qanday ishlaydi (muhim texnik joy)
- O'qituvchi brauzeri yozuv bo'laklarini saytga yuboradi. APP'dagi Caddy `…/recording…` so'rovlarini MEDIA'dagi `rec` ga yo'naltiradi, `rec` ularni diskka yozadi.
- Darsni **majburan yakunlash** (`auto_finish_expired_lessons`) APP serverda bajariladi, lekin fayllar u yerda yo'q. Shu uchun `RECORDINGS_LOCAL=0`: APP faqat belgilarni qo'yadi, birlashtirishni MEDIA'dagi `recover_recordings` bajaradi (fayl 5 daqiqa o'zgarmagach).
- Kurs o'chirilsa baza yozuvi o'chadi, fayllar MEDIA'da qoladi → `prune_orphan_recordings` tozalaydi. Xavfsizlik: bazada hech bir yozuv qatori bo'lmasa hech narsa o'chirmaydi.

#### O'sish yo'li
1. Hozir: 10 000 foydalanuvchi, shu 2 server.
2. APP to'lsa: RS 2000 → RS 4000 (yoki RS 8000). `.env` da `PG_SHARED_BUFFERS=8GB`, `PG_EFFECTIVE_CACHE=20GB`.
3. MEDIA CPU to'lsa: ikkinchi LiveKit serveri qo'shiladi (LiveKit Redis orqali ko'p tugunni qo'llab-quvvatlaydi).
4. Disk to'lsa: yozuvlar Cloudflare R2 ga (ko'rish trafigi ham ketadi). Bu kod o'zgarishini talab qiladi (fayllarni diskka emas R2 ga yozish) — hozir qilinmagan.

#### Hali tekshirilmagan (halol)
- Bu fayllar **haqiqiy serverda hali ishga tushirilmagan**. Birinchi ishga tushirishda kichik xato chiqishi mumkin, shuning uchun avval `edu2` sinov domenida sinaymiz.
- WireGuard kanali orqali bazaga ulanish tezligi o'lchanmagan (bir xil shahar ichida ~1 ms kutiladi).
- Caddy'ning yozuv so'rovlarini yo'naltirish qoidasi (`@recording`) sintaksis jihatdan to'g'ri deb hisoblangan, lekin Caddy'da ishga tushirib ko'rilmagan.
- 1 500 tomoshabinli LiveKit yuki (o'lchangan faqat 500 gacha) va netcup protsessorining haqiqiy tezligi.


[↑ Mundarija](#mundarija)

---

## SERVER_SOZLASH

> Avvalgi fayl: `SERVER_SOZLASH.md`

### Yangi netcup serverlarini sozlash — qadamma-qadam qo'llanma

**Serverlar:**
- **RS 2000** (8 yadro, 16 GB) = **APP** (CORE): sayt, chat, baza, Redis, fon ishlari.
- **RS 4000** (12 yadro, 32 GB) = **MEDIA**: jonli dars video, dars yozuvlari (qabul qilish, birlashtirish, MP4 ga o'tkazish, saqlash).

Nega shunday: eng katta yuk — jonli dars va yozuv. Shuning uchun kuchliroq server (RS 4000) ularga beriladi. Arxitekturaning to'liq tushuntirishi: `SERVER_ARXITEKTURA.md`.

Hamma tayyor fayllar loyihada bor va **har serverniki o'z papkasida** turadi (2026-11-27 dan):

```
deploy/
  app_server/     APP (RS 2000):  docker-compose.yml, .env.example, caddy/Caddyfile      (+ .env — haqiqiy, gitda yo'q)
  media_server/   MEDIA (RS 4000): docker-compose.yml, .env.example, livekit.yaml, caddy/Caddyfile  (+ .env)
  new/            bootstrap, wireguard, backup (ikkala server uchun umumiy skriptlar)
```

**Hamma `docker compose` buyruqlari shu serverning papkasidan ishlatiladi** (`-f` kerak emas): APP — `cd /var/www/edu_platform/deploy/app_server`, MEDIA — `cd /var/www/edu_platform/deploy/media_server`. Loyiha nomi (`edu_platform`) compose faylida qotirilgan, shuning uchun baza va boshqa volume'lar papka o'zgarganda ham o'sha-o'zida qoladi.
**Eslatma:** bu fayllar yozilgan va sintaksisi tekshirilgan, lekin **haqiqiy serverda hali ishga tushirilmagan.** Birinchi ishga tushirishda kichik xato chiqishi mumkin — shuning uchun avval **sinov domenida** (`edu2`) ishga tushiramiz, eski serverga tegmaymiz.

---

#### 0. Qaysi server nima uchun

| Server | Roli | Ichida nimalar |
|---|---|---|
| **RS 2000** → **APP** | Sayt va ma'lumotlar | Caddy (kirish eshigi), `web` (API), `ws` (chat/doska), Postgres, Redis, `cron` (eslatmalar, AI, avto-yakunlash) |
| **RS 4000** → **MEDIA** | Video va yozuvlar | LiveKit (jonli video), `rec` (yozuv API'si), `rec-cron` (tiklash, tozalash), `transcoder` (MP4), yozuv fayllari |

Ikki server o'rtasida **yopiq kanal (WireGuard)**: baza va Redis internetga ochilmaydi, MEDIA serverdagi `rec` ularga shu kanal orqali ulanadi. Yozuv bilan bog'liq so'rovlarni (`/api/v1/lessons/<id>/recording...`) APP serverdagi Caddy MEDIA serverdagi `rec` ga yo'naltiradi.

**Ikkala serverni ham BIR XIL joyda (Vena yoki Nyurnberg) oling** — o'zaro aloqa tez bo'ladi.

---

#### 1. Sizga kerak bo'ladigan ruxsatlar (access) — ro'yxat

**Hech qachon parolni chatga, Telegramga yoki fayl ichiga yozmang.** Parollar faqat parol menejeri (Bitwarden/1Password) yoki bevosita sizga yuboriladigan bir martalik havola orqali beriladi.

| № | Nima kerak | Kimdan | Nima uchun | Qanday beriladi |
|---|---|---|---|---|
| 1 | **Serverlarning IP manzillari** (ikkala server) | Team lead (buyurtmadan keyin) | Ulanish uchun | netcup yuboradigan xat yoki **SCP** (Server Control Panel) dan ko'chirib berish |
| 2 | **Server paneli (SCP)** ga kirish: `servercontrolpanel.de` | Team lead | OS o'rnatish, qayta ishga tushirish, **konsol (VNC)** — SSH buzilsa yagona qutqaruvchi | netcup foydalanuvchi qo'shishga ruxsat bersa — shaxsiy hisob; bo'lmasa team lead birga o'tiradi |
| 3 | **SSH kirish** (root parol yoki SSH kalit) | Siz o'zingiz kalit yaratasiz, team lead o'rnatishda ko'rsatadi | Serverga kirish | 3-bo'limdagi kalit — **faqat OCHIQ kalit** (`.pub`) beriladi |
| 4 | **DNS boshqaruvi** (`thesofmebel.uz` domeni qayerda boshqariladi — registrator yoki Cloudflare) | Team lead yoki domen egasi | `edu2`, `lk`, keyin `edu` yozuvlarini yangi IP'larga qo'yish | Panelga kirish yoki siz aytgan yozuvlarni o'zi qo'yadi (**qaysi yozuvlar — 7-bo'lim**) |
| 5 | **GitHub repo ruxsati** (`krv006/Education-Tech-Platform`) — **Deploy key** qo'shish huquqi | Repo egasi (krv006) | Server kodni `git pull` qilishi uchun (faqat o'qish kaliti) | Repo → Settings → Deploy keys → serveringizning ochiq kaliti (8-bo'lim) |
| 6 | **Eski server (Contabo)** ga root SSH | Sizda bor (hozir ham kirasiz) | `.env`, baza va fayllarni ko'chirish | — |
| 7 | **Eski serverdagi `.env` va Firebase JSON** | Eski serverdan o'zingiz olasiz | Yangi serverda **bir xil** kalitlar (SECRET_KEY, VAPID, OpenAI, LiveKit) bo'lishi shart | `scp` bilan (9-bo'lim) — **xabarlarda ko'rsatilmaydi** |
| 8 | netcup **hisobi 2FA** (ikki bosqichli tasdiq) | Team lead | Hisobni o'g'irlashdan himoya | Team lead yoqadi |

**Kamida kerak (bugun boshlash uchun):** №1, №2 (yoki team lead yonida), №3, №6, №7. №4 va №5 — ertaga ham bo'ladi.

---

#### 2. Team lead bugun nimani tanlab buyurtma qiladi (aytib qo'ying)

- Modellar: **RS 2000 G12.5** (APP) va **RS 4000 G12.5** (MEDIA).
- **Joy:** ikkalasi uchun ham **Vena** yoki **Nyurnberg** (bir xil).
- **Operatsion tizim:** **Ubuntu 24.04 LTS**.
- **IPv4 + IPv6** (IPv4 shart).
- **MEDIA (RS 4000) uchun qo'shimcha disk** (netcup "Local Block Storage" yoki kattaroq): yozuvlar kuniga 9–20 GB qo'shadi, 512 GB 1–4 oyda to'ladi.
- Shartnoma muddati: **birinchi buyurtmada 30 kunlik pul qaytarish bor** — avval 1 yoki 12 oy ni tanlang; 24 oylikni sinovdan keyin (shartnomani keyin o'zgartirish mumkinligini netcup'dan so'rang).
- NDS (VAT) ma'lumotini kompaniya ma'lumotlari bilan to'g'ri kiriting.
- **Savol (netcup qo'llab-quvvatlashiga):** "3 TB/24 soat trafik chegarasi faqat chiquvchimi yoki kiruvchi+chiquvchi birgami?"

---

#### 3. Bugun sizning kompyuteringizda: SSH kalit yaratish (5 daqiqa)

Windows PowerShell'da (bir marta):

```powershell
ssh-keygen -t ed25519 -C "mathu-ishxona"
```
(Enter, Enter, Enter — parol ixtiyoriy, lekin qo'ysangiz yaxshi.) Ochiq kalitni ko'rish:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
```
Chiqqan **bitta satr** (`ssh-ed25519 AAAA... mathu-ishxona`) — **ochiq kalit**. Shuni team leadga bering (u SCP'da OS o'rnatishda SSH kalit sifatida qo'yadi) yoki keyingi qadamda o'zingiz qo'shasiz. **`id_ed25519` (`.pub`siz) — maxfiy kalit, uni hech kimga bermang.**

---

#### 4. Serverga birinchi kirish

Serverlar tayyor bo'lgach (SCP'da Ubuntu 24.04 o'rnatilgan, IP bor):

```powershell
ssh root@<SERVER_IP>
```
Birinchi marta "fingerprint" so'rasa `yes`. **Ikkala server uchun alohida** qiling. Kira olmasangiz: SCP → server → **konsol (Screen/VNC)** orqali ko'ring.

Agar SCP'da kalit qo'yilmagan, parol bilan kirgan bo'lsangiz — ochiq kalitni qo'shing (kompyuteringizdan):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@<SERVER_IP> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

---

#### 5. Serverni tayyorlash (har ikkala serverda, `bootstrap.sh`)

Bu skript yangilaydi, **Docker** o'rnatadi, `deploy` foydalanuvchisini yaratadi, **firewall**, **fail2ban**, avtomatik xavfsizlik yangilanishlarini sozlaydi.

Kodni serverga olishning eng oddiy yo'li — hozircha skriptlarning o'zini nusxalash (repo yopiq bo'lgani uchun). Kompyuteringizdan (loyiha papkasida):

```powershell
scp deploy/new/bootstrap.sh deploy/new/wireguard.sh root@<APP_IP>:/root/
```
```powershell
scp deploy/new/bootstrap.sh deploy/new/wireguard.sh root@<MEDIA_IP>:/root/
```

APP serverda (RS 2000):

```bash
bash /root/bootstrap.sh app
```
MEDIA serverda (RS 4000, o'sha skript, boshqa rol):

```bash
bash /root/bootstrap.sh media
```
Tugagach **yangi terminalda** tekshiring (parolsiz kirishi kerak):

```powershell
ssh deploy@<SERVER_IP>
```
Kirsa — serverda skriptni yana bir marta `--lock-ssh` bilan ishga tushiring (parol va root bilan kirishni o'chiradi). **Kira olmasangiz bu qadamni QILMANG.**

```bash
sudo bash /root/bootstrap.sh app --lock-ssh
```

---

#### 6. Ikki server o'rtasida yopiq kanal (WireGuard)

Bu kanal orqali MEDIA serverdagi yozuv xizmati APP serverdagi bazaga ulanadi. Ikki bosqich.

**1-bosqich** — har serverda o'zining OCHIQ kalitini oling (xavfsiz, berish mumkin):

APP serverda:
```bash
sudo bash /root/wireguard.sh core
```
MEDIA serverda:
```bash
sudo bash /root/wireguard.sh media
```
Har biri bitta satr ochiq kalit chiqaradi. Ikkalasini yozib oling.

**2-bosqich** — har serverda ikkinchisining **public IP** va **ochiq kaliti** bilan ulang:

APP serverda:
```bash
sudo bash /root/wireguard.sh core <MEDIA_PUBLIC_IP> <MEDIA_OCHIQ_KALIT>
```
MEDIA serverda:
```bash
sudo bash /root/wireguard.sh media <APP_PUBLIC_IP> <APP_OCHIQ_KALIT>
```
Oxirida "OK: ... ga kanal orqali ping o'tdi" chiqishi kerak. O'tmasa, ikkala serverda ham 2-bosqich bajarilganini tekshiring. Qo'lda tekshirish: APP serverda `ping -c 3 10.10.0.2`, MEDIA serverda `ping -c 3 10.10.0.1`.

---

#### 7. DNS (team lead yoki siz)

Ikkita yangi yozuv (**A** tur), TTL 300:

| Yozuv | Qiymat | Nima uchun |
|---|---|---|
| `edu2.thesofmebel.uz` | **APP** server IP'si (RS 2000) | Sinov: yangi serverni eski sayt buzilmasdan tekshirish |
| `lk.thesofmebel.uz` | **MEDIA** server IP'si (RS 4000) | Jonli dars serveri (haqiqiy ishlatiladi) |

`edu.thesofmebel.uz` ga **hozircha tegmang** (u eski serverda). Ko'chib o'tish kuni (12-bo'lim) uni yangi APP'ga yo'naltiramiz.
Tekshirish: `nslookup lk.thesofmebel.uz` — MEDIA IP'sini ko'rsatishi kerak.

---

#### 8. Loyihani serverga olish (APP va MEDIA ikkalasida)

`deploy` foydalanuvchisi sifatida (`ssh deploy@<IP>`). Repo yopiq bo'lgani uchun **Deploy key** ishlatamiz (faqat o'qish; parol/token serverda saqlanmaydi):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "deploy-$(hostname)"
```
```bash
cat ~/.ssh/github_deploy.pub
```
Chiqqan kalitni GitHub'da: `krv006/Education-Tech-Platform` → **Settings → Deploy keys → Add deploy key** (Allow write access **QO'YMANG**). Repo egasi qo'shadi. So'ng:

```bash
printf 'Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
```
```bash
git clone git@github.com:krv006/Education-Tech-Platform.git /var/www/edu_platform
```
(Repo asosiy tarmog'i `main`.) Kelgusi yangilashlar: `cd /var/www/edu_platform && git pull`.

---

#### 9. APP serverni ishga tushirish (RS 2000) — AVVAL shuni qiling

Eski serverdan `.env` ni **to'g'ridan-to'g'ri** yangi serverga nusxalang (xabar orqali emas). Buning uchun eski serverga kompyuteringizdan **agent uzatish (`-A`)** bilan kiring — shunda sizning kalitingiz yangi serverga ham o'tadi:

```powershell
ssh -A root@<ESKI_SERVER>
```
Eski serverdan turib:

```bash
scp /var/www/edu_platform/.env deploy@<APP_IP>:/var/www/edu_platform/.env.old
```
(Agar `-A` ishlamasa: faylni avval o'z kompyuteringizga `scp` qiling, keyin yangi serverga. Ishlatib bo'lgach APP serverda `shred -u /var/www/edu_platform/.env.old` bilan o'chiring.)
APP serverda `deploy/app_server/.env.example` asosida yangi `.env` yarating va eski `.env` dan **kalitlarni ko'chiring** (`SECRET_KEY`, `VAPID_*`, `OPENAI_*`, `LIVEKIT_*` va hokazo):

```bash
cd /var/www/edu_platform/deploy/app_server && cp .env.example .env && nano .env
```
O'zgartiriladigan qiymatlar (sinov bosqichi):
- `DOMAIN=edu2.thesofmebel.uz`, `ALLOWED_HOSTS=edu2.thesofmebel.uz`, `CSRF_TRUSTED_ORIGINS=https://edu2.thesofmebel.uz`, `CORS_ALLOWED_ORIGINS=https://edu2.thesofmebel.uz`
- `LIVEKIT_URL=wss://lk.thesofmebel.uz` (`LIVEKIT_API_URL` ni **qo'shmang**)
- `POSTGRES_PASSWORD` — yangi kuchli parol
- `REDIS_PASSWORD` — yangi parol. Hosil qilish: `python3 -c "import secrets; print(secrets.token_hex(24))"` (faqat harf-raqam bo'lishi shart)
- `CORE_WG_IP=10.10.0.1`, `MEDIA_WG_IP=10.10.0.2`, `REC_UPSTREAM=10.10.0.2:8000`. **Agar MEDIA hali tayyor bo'lmasa, `REC_UPSTREAM` qatorini vaqtincha o'chirib qo'ying** — yozuv so'rovlari `web` ga boradi (yozuv ishlamaydi, qolgan hamma narsa ishlaydi).
- Baza xotira sozlamalari RS 2000 uchun standartda qoladi.

Avval bazani ko'taring:

```bash
docker compose up -d --build db redis
```
(Birinchi yig'ish 3–6 daqiqa.) Eski serverdagi **bazani ko'chirish** (yana eski serverda, `ssh -A` bilan kirilgan holda dump):

```bash
docker exec edu_platform-db-1 pg_dump -U edtech -d edtech -Fc > /root/edtech.dump
```
```bash
scp /root/edtech.dump deploy@<APP_IP>:/tmp/edtech.dump
```
APP serverda tiklash:

```bash
cat /tmp/edtech.dump | docker compose exec -T db pg_restore -U edtech -d edtech --no-owner
```
(Ba'zi "already exists" ogohlantirishlari bo'lishi mumkin — xato emas, agar oxirida jadvallar bo'lsa.) Endi hammasini ko'taring:

```bash
docker compose up -d --build
```
Holat va loglar:

```bash
docker compose ps
```
```bash
docker compose logs --tail=50 web
```
Tekshirish (brauzerda): `https://edu2.thesofmebel.uz/api/docs/` ochilishi kerak (Swagger).

**Yuklangan fayllarni ko'chirish** (rasm/vazifa fayllari) — eski serverdan **APP serverga** (`rsync`, eski serverdan turib, `ssh -A` bilan; `tmux` ichida ishga tushiring):

```bash
rsync -az /var/lib/docker/volumes/edu_platform_media/_data/ deploy@<APP_IP>:/tmp/media/
```
APP serverda volume'ga qo'yish:

```bash
sudo rsync -a /tmp/media/ /var/lib/docker/volumes/edu_platform_media/_data/
```
(Volume nomlari loyiha papkasi nomidan olinadi: papka `edu_platform` bo'lsa `edu_platform_media`. Tekshirish: `docker volume ls`.)

---

#### 10. MEDIA serverni ishga tushirish (RS 4000) — APP tayyor bo'lgach

Bu server LiveKit va **yozuv xizmatlarini** ishga tushiradi. Yozuv xizmatlari APP serverdagi bazaga WireGuard orqali ulanadi, shuning uchun **6-bo'lim (WireGuard) bajarilgan va 9-bo'lim (APP) ishlab turgan bo'lishi shart.**

MEDIA serverda `.env`: eng ishonchli yo'l — APP serverdagi `.env` ni shu yerga ko'chirish (kalitlar bir xil bo'lishi shart). APP serverdan:

```bash
scp /var/www/edu_platform/deploy/app_server/.env deploy@<MEDIA_IP>:/var/www/edu_platform/deploy/media_server/.env
```
So'ng MEDIA serverda `deploy/media_server/.env.example` dagi "MEDIA ga xos" qatorlarni qo'shing (`LK_DOMAIN`, `REC_CPUS`, `TRANSCODER_CPUS` va h.k.):

```bash
cd /var/www/edu_platform/deploy/media_server && nano .env
```
`LK_DOMAIN=lk.thesofmebel.uz`, `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` (APP bilan **aynan bir xil**). Ishga tushirish:

```bash
docker compose up -d --build
```
Tekshirish:
```bash
docker compose ps
```
```bash
docker compose logs --tail=30 caddy
```
Caddy logida "certificate obtained" (sertifikat olindi) chiqishi kerak — buning uchun `lk.` DNS yozuvi ishlayotgan bo'lishi shart. Brauzerdan `https://lk.thesofmebel.uz` ni oching: LiveKit javobi chiqsa tayyor.
Agar `manifest unknown` xatosi chiqsa: `.env` da `LIVEKIT_VERSION=1.13.4` (`v`siz) qiling.

Yozuv xizmatini tekshirish (MEDIA serverda):
```bash
docker compose logs --tail=30 rec
```
Bazaga ulana olganini ko'rsatadi. Keyin APP serverda `.env` dagi `REC_UPSTREAM=10.10.0.2:8000` qatori yoqilganini tekshirib, Caddy'ni qayta ishga tushiring:

```bash
docker compose up -d caddy
```

**Dars yozuvlarini ko'chirish** (eski serverdan **MEDIA serverga**, fayllar shu yerda turadi; `tmux` ichida):

```bash
rsync -az /var/lib/docker/volumes/edu_platform_recordings/_data/ deploy@<MEDIA_IP>:/tmp/recordings/
```
MEDIA serverda:
```bash
sudo rsync -a /tmp/recordings/ /var/lib/docker/volumes/edu_platform_recordings/_data/
```

---

#### 11. Sinov ro'yxati (ko'chib o'tishdan oldin)

1. `https://edu2.thesofmebel.uz/api/docs/` ochiladi; `https://edu2.thesofmebel.uz/api/health/` — `ok`.
2. Login qilish ishlaydi (bu yangi bazada eski foydalanuvchilar bilan).
3. **Jonli dars sinovi:** ikki qurilmada (o'qituvchi + o'quvchi) dars — video, ovoz, doska, chat. Frontend sinov domenini bilishi uchun Vercel'da preview muhitida API manzilini `edu2` ga qo'ying yoki test akkaunt bilan sinang.
4. **Dars yozuvi:** o'qituvchi darsni yozib tugatadi → yozuv "tayyor" bo'ladi (bo'laklar MEDIA'dagi `rec` ga boradi) → MP4 ga o'tadi: `docker compose logs --tail=30 transcoder` (MEDIA serverda). Yozuvni ko'rish ham ishlashi kerak.
5. `docker stats --no-stream` — ikkala serverda CPU/RAM me'yorida.
6. **Zaxira nusxa** (12-bo'lim) ishlaydi va tiklash sinab ko'rilgan.
7. **Disk ogohlantirishi:** admin panelda server holati; `check_disk` 80% dan oshsa adminlarga bildirishnoma yuboradi. `check_cpu_steal` har daqiqada hypervisor yadrolarni sekinlashtirmayotganini (steal) kuzatadi: yuk ostida doimiy 3% dan oshsa adminlarga bildirishnoma, har soatda log'ga xulosa (`docker compose logs cron | grep cpu_steal`, MEDIA'da `rec-cron`).

---

#### 12. Zaxira nusxa (APP serverda)

`deploy/new/backup.sh` har kecha bazaning nusxasini oladi va **MEDIA serverga** ko'chiradi (boshqa mashina). Sozlash yo'riqnomasi faylning boshida. Qisqasi: kalit yaratish, MEDIA'ga qo'shish, `crontab -e` ga bitta qator.
Saqlash muddati: kunlik nusxalar **14 kun**, haftalik (yakshanba) **~6 oy**, oylik (1-sana) **~13 oy** (`db_weekly_*`, `db_monthly_*`). Bitta nusxa ~2 MB, shuning uchun uzoq saqlash deyarli bepul.
Eski chatni/ma'lumotni qaytarish kerak bo'lsa: kerakli sanadagi nusxani **alohida bazaga** tiklab (`createdb restore_x; pg_restore -d restore_x --no-owner <fayl>`) kerakli qatorlarni ko'chiring; asosiy bazani `--clean` bilan bosmang.
**Tiklash 2026-11-18 da sinab ko'rilgan:** oxirgi nusxa vaqtinchalik bazaga xatosiz tiklandi, qator sonlari jonli bazaga mos keldi (nusxadan keyingi yangi yozuvlardan tashqari).

---

#### 12a. Email (SMTP) va chiquvchi SMTP himoyasi (APP serverda)

Parolni tiklash, ro'yxatdan o'tishda email tasdiqlash va email bilan kirish xatni **APP server** yuboradi (`.env`: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`; Gmail uchun 16 xonali **ilova paroli**). Majburiylik: `REGISTER_REQUIRES_EMAIL=1`, muhlat: `EMAIL_SETUP_DEADLINE=YYYY-MM-DD`.

- **Netcup "Mail block":** yangi serverlarda standart firewall siyosati SMTP (25/465/587) ni ichkariga ham, tashqariga ham jimgina tashlaydi (SYN javobsiz qoladi,
  `portquiz.net:587` ham ochilmaydi). Xat yuborish uchun SCP → server → Firewall → "netcup Mail block" → Delete → Save. APP serverda 2026-11-18 da o'chirilgan; MEDIA'da qoldi (u xat yubormaydi).
- **Spamdan himoya:** blok o'chgach server 25/465 portlariga erkin chiqa oladi. `deploy/new/block-smtp-egress.sh` host va Docker konteynerlari uchun chiquvchi 25 va 465 ni yopadi (587 ochiq):
  ```bash
  install -m 755 deploy/new/block-smtp-egress.sh /usr/local/sbin/
  install -m 644 deploy/new/block-smtp-egress.service /etc/systemd/system/
  systemctl daemon-reload && systemctl enable --now block-smtp-egress
  /usr/local/sbin/block-smtp-egress.sh status      # qoidalar ko'rinadi
  ```
  Qaytarish: `systemctl disable --now block-smtp-egress`.
- **Tekshirish:** serverdan `timeout 6 bash -c 'exec 3<>/dev/tcp/smtp.gmail.com/587' && echo OPEN`; konteynerdan 25 ga ulanish darhol rad etiladi (`Connection refused`).

---

#### 13. Ko'chib o'tish kuni (cutover) — kechqurun, dars bo'lmagan paytda

1. Bir kun oldin DNS'da `edu.thesofmebel.uz` TTL ni 300 s ga tushiring.
2. Eski serverda saytni vaqtincha to'xtating (yozuv to'xtasin): `docker compose -f docker-compose.prod.yml stop backend cron`.
3. **Oxirgi** bazani qayta dump qiling va yangi APP'ga tiklang (9-bo'lim, YANGI serverdagi bazani avval tozalab: `docker compose exec -T db psql -U edtech -d edtech -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` — **faqat yangi serverda**, hech qachon eskisida!), fayllarni (media va yozuvlar) `rsync -a` bilan yangilang.
4. APP `.env` da `DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` ni `edu.thesofmebel.uz` ga o'zgartiring: `docker compose up -d`. **MEDIA serverdagi `.env` ga ham xuddi shu to'rt qiymatni yozing** va `docker compose up -d`.
5. DNS: `edu.thesofmebel.uz` → **APP IP**. Caddy sertifikatni bir necha soniyada oladi.
6. Tekshiring: login, chat, jonli dars, yozuv. Muammo bo'lsa — DNS'ni **eski IP**ga qaytaring (eski server o'chirilmagan).
7. 1–2 hafta eski serverni **o'chirmasdan** saqlang.

---

#### 14. Kundalik ishlar

| Nima | Buyruq (`/var/www/edu_platform` ichida) |
|---|---|
| APP yangilash (AVVAL shuni) | APP serverda: `git pull && docker compose up -d --build` |
| MEDIA yangilash (APP'dan KEYIN) | MEDIA serverda: `git pull && docker compose up -d --build` |
| Holat | `docker compose ps` (APP) / `docker compose ps` (MEDIA) |
| Log | APP: `... logs --tail=100 web` (yoki `ws`, `cron`, `caddy`); MEDIA: `... logs --tail=100 rec` (yoki `transcoder`, `rec-cron`, `livekit`, `caddy`) |
| Resurs | `docker stats --no-stream` va `htop` |
| Disk | `df -h /` va `docker system df` |
| Admin yaratish | `docker compose exec web python manage.py createsuperuser` |
| Yozuv diskini tozalash (hisobot) | MEDIA: `docker compose exec rec python manage.py prune_recordings` |

**Yangilash tartibi muhim:** migratsiyani APP serverdagi `web` bajaradi, shuning uchun har doim **avval APP, keyin MEDIA**. Deploy'ni dars bo'lmagan vaqtda qiling (`ws` qayta ishga tushganda chat qisqa uziladi; video uzilmaydi).

**Ogohlantirishlar:**
- **Disk:** yozuvlar MEDIA serverda diskni to'ldiradi (~9–20 GB/kun, 60 yozilgan dars/kun bo'lsa). Admin panelda va `check_disk` (80% / 90% da bildirishnoma) orqali kuzating. To'lishiga yaqinlashsa: `prune_recordings` (hisobot, so'ng `--apply --drop-webm`) yoki netcup'da qo'shimcha disk.
- **Trafik:** 24 soatda 3 TB dan oshsa tezlik 300 Mbit/s ga tushadi (MEDIA'da ehtiyot bo'ling: video + yozuv ko'rish shu serverdan chiqadi).
- **Firewall:** Docker o'zi ochgan portlarni `ufw` dan chetlab o'tadi. Shuning uchun baza, Redis va `rec` portlari faqat WireGuard manzilida (`10.10.0.x`) ochilgan, internetda emas. Yangi port qo'shsangiz ehtiyot bo'ling.
- **MEDIA yiqilsa:** jonli video va yozuv to'xtaydi, sayt va chat ishlayveradi. **APP yiqilsa:** yangi o'quvchi darsga kira olmaydi, allaqachon ulangan video davom etadi.
- **SSH'dan chiqib ketib qolsangiz:** SCP'dagi konsol (VNC) orqali kiring.

---

#### 14a. Eski joydan yangi papkalarga ko'chirish (2026-11-27, bir martalik)

Compose, `.env`, Caddy va LiveKit fayllari ildizdan `deploy/app_server/` va `deploy/media_server/` ga ko'chirildi. Serverlarda ishlab turgan narsa **to'xtamaydi va baza o'zgarmaydi**: loyiha nomi (`edu_platform`) faylda qotirilgan, volume'lar va konteynerlar o'sha-o'zida. Faqat buyruq joyi o'zgaradi. Ketma-ketlik: AVVAL APP, keyin MEDIA. Har qadamdan keyin natijani tekshiring.

**APP serverda (RS 2000):**

```bash
cd /var/www/edu_platform
docker compose -f docker-compose.app.yml ls          # NAME = edu_platform ekanini tekshiring (o'zgartirishdan OLDIN)
git pull origin main                                  # yangi papkalar paydo bo'ladi, eski compose fayli yo'qoladi
cp .env deploy/app_server/.env                        # haqiqiy .env ni yangi joyga NUSXALANG (eskisi zaxira bo'lib turadi)
chmod 600 deploy/app_server/.env
cd deploy/app_server
docker compose config -q && echo "config OK"          # xatosiz bo'lishi kerak
docker compose ps                                     # web, ws, cron, db, redis, caddy — hammasi avvalgidek "Up"
```

**Tekshirilgan** (APP serverda haqiqiy `.env` bilan, eski faylni yangisi bilan solishtirib, ishlab turgan narsaga tegmasdan): loyiha nomi, volume'lar (`pgdata`, `media`, `logs`, `caddy_data`, `caddy_config`) va tarmoq AYNAN bir xil; `web`, `ws`, `cron`, `db`, `redis` konfiguratsiyasi o'zgarmagan. Faqat `caddy` farq qiladi (Caddyfile papkasi yo'li o'zgargani uchun): keyingi `docker compose up -d` da u qayta yaratiladi (1-2 soniya uzilish, sertifikatlar volume'da saqlanadi). Shuning uchun `up -d` ni dars bo'lmagan paytda bajaring. Hammasi joyida bo'lsa, eski ildizdagi `.env` ni 1-2 kun saqlab, keyin o'chirishingiz mumkin. Zaxira skripti (`deploy/new/backup.sh`) endi `docker exec edu_platform-db-1 ...` ishlatadi (compose joyiga bog'liq emas); keyingi tunda `/var/backups/edu/` da yangi `db_*.dump` paydo bo'lganini tekshiring.

**MEDIA serverda (RS 4000):**

```bash
cd /var/www/edu_platform
docker compose -f docker-compose.media.yml ls         # NAME ni yozib oling. edu_platform BO'LMASA — deploy/media_server/docker-compose.yml dagi `name:` ni shunga o'zgartiring!
git pull origin main
cp .env deploy/media_server/.env && chmod 600 deploy/media_server/.env
cd deploy/media_server
docker compose config -q && echo "config OK"
docker compose ps                                     # livekit, rec, transcoder, caddy... avvalgidek "Up"
```

Eski buyruqlar (`docker compose -f docker-compose.app.yml ...`) `git pull` dan keyin "no such file" deb xato beradi. Bu xavfsiz: konteynerlarga ta'sir qilmaydi. Yangi buyruqlar shu papkalardan, `-f` siz.

**Serverdagi eski axlat fayllar:** MEDIA serverda ildizda eski `*.md` hujjatlar (FRONTEND_*, BACKEND_*, PROJECT.md va h.k.) qolib ketgan. Ular gitda yo'q, shu serverning o'zida qolgan eski nusxalar. Ularni o'chirishdan oldin ro'yxatni ko'rib, kerakmasligiga ishonch hosil qiling (`ls *.md`, `git status --short`); o'chirish `rm` bilan faqat ro'yxatdagi aniq fayllarga qilinadi.

---

#### 15. Muammo bo'lsa menga yuboring

Quyidagilarni (parollarsiz!) yuboring:
- `docker compose ps` (APP) yoki `docker compose ps` (MEDIA) natijasi
- `docker compose -f docker-compose.<app|media>.yml logs --tail=80 <xizmat>` natijasi
- WireGuard muammosi bo'lsa: `sudo wg show` (maxfiy kalit ko'rsatilmaydi) va `ping -c 3 10.10.0.1` / `10.10.0.2`
- Xato matni va qaysi qadamda chiqqani


[↑ Mundarija](#mundarija)

---

## SERVER_OLCHOV_NATIJALARI

> Avvalgi fayl: `SERVER_OLCHOV_NATIJALARI.md`

### Haqiqiy o'lchov natijalari (taxmin emas) — 2026-10-27

**Qanday o'lchandi:** loyiha kodini mahalliy kompyuterda (AMD Ryzen, 16 oqim, Windows) **10 000 foydalanuvchilik bazada** ishga tushirdim: 10 000 hisob, 300 guruh, 19 880 yozilish, 6 000 dars, **275 700 davomat yozuvi**, 36 000 chat xabari, **149 100 bildirishnoma**, 27 000 topshiriq, 7 500 test urinishi. Har so'rovni 120–150 marta takrorlab median oldim. Skriptlar: `scratchpad/bench/` (loyiha papkasida emas).

**Cheklovlar (halol):**
1. **Baza — SQLite**, Postgres emas. SQL so'rovlar **soni** aniq (bu o'lchanadi), lekin har birining vaqti Postgres'da boshqacha.
2. **Windows.** Haqiqiy serverda Linux (`uvloop`) — ASGI qatlami ancha tezroq bo'lishi kerak. Windows'da yengil so'rov ichki o'lchovda 1.8 ms, haqiqiy uvicorn orqali 8.8 ms chiqdi. **Linux uchun bu raqam hali o'lchanmagan.**
3. **LiveKit o'lchanmadi** (uning dasturi bu kompyuterda yo'q).
4. Kompyuter protsessori netcup EPYC 9645 (Zen 5) dan sekinroq bo'lishi mumkin — raqamlar shu sababli ehtiyotkor tomonga.

---

#### 1. Har bir so'rov qancha protsessor yeydi (bitta so'rov, ichki o'lchov)

| So'rov | Kim, qancha tez-tez | ms | SQL so'rov soni |
|---|---|---|---|
| `GET /live/attention/` | **o'quvchi, darsda, HAR 3 SONIYADA** | **1.8** | 2 |
| `GET /notifications/unread-count/` | har foydalanuvchi, har 60 s | 1.5 | 2 |
| `GET /auth/me/` | sahifa ochilganda | 2.7 | 2 |
| `GET /live/lesson/{id}/presence/` | o'qituvchi, har 20 s | 3.8 | 3 |
| `GET /lessons/?status=live` | chat sahifasidagi har kishi, har 20 s | 13.8 | 8 |
| `POST /live/token/` (darsga kirish) | darsga kirganda 1 marta | 10.3 | 9 |
| `POST /chat/rooms/{id}/send/` | xabar yuborganda | 14.0 | 12 |
| `GET /chat/rooms/{id}/messages/?limit=30` | chat ochilganda | 30.7 | 11 |
| `GET /chat/rooms/` | chat ro'yxati | 44.0 | 21 |
| `GET /courses/` | sahifada | 25.7 | 13 |
| `GET /homework/assignments/` | sahifada | 6.6 | 9 |
| `POST /auth/token/refresh/` | soatiga ~1 marta | 18.7 | 16 |
| **`POST /auth/login/`** | **har kirishda** | **~450** | — |
| `GET /lessons/?page_size=20` | jadval sahifasi | **164** (o'qituvchida 230) | **64** |
| `GET /dashboard/teacher/` | o'qituvchi bosh sahifa | **194** | 8 |
| `GET /attendance/?lesson=` | o'qituvchi, 1 dars (66 o'quvchi) | 128 | — |
| `GET /analytics/me/trends/` | o'qituvchi tahlil | **655** | 26 |
| `GET /analytics/me/` | o'qituvchi tahlil | **1 371** | 46 |
| `GET /board/{id}/` (500 chiziq) | **o'qituvchi, darsda, HAR 2 SONIYADA** | 27 (javob **235 KB**) | — |

**Kirish (login) ~450 ms protsessor** — parolni xeshlash (PBKDF2, 1.2 mln iteratsiya). Bu atayin sekin (xavfsizlik). Muammo: dars boshlanishida 1 500 o'quvchi bir daqiqada kirsa = 675 yadro-soniya ≈ **11 yadro 1 daqiqa**. Token 60 daqiqa, yangilash 7 kun, shuning uchun hamma emas, lekin birinchi kirishlar to'planib qolishi mumkin.

#### 2. Hal qiluvchi topilma: so'rov chastotasi (frontend kodidan)

| Qaerda | Nima | Chastota |
|---|---|---|
| **O'quvchi darsda** (`live-room.tsx`) | `attention` | **har 3 soniya = 0.33 so'rov/s har o'quvchiga** |
| Har kirgan foydalanuvchi | bildirishnoma soni | har 60 s |
| Chat sahifasidagilar | jonli darslar ro'yxati | har 20 s |
| **O'qituvchi darsda** | doska (`useBoard` **WebSocket bo'lsa ham** so'raydi) | **har 2 s, har gal butun doska (235 KB / 500 chiziq)** |
| Imtihon | holat | har 15 s |
| Chat (WebSocket ulangan) | so'rov yo'q | — |

**1 500 o'quvchi darsda bo'lsa: 500 so'rov/soniya faqat `attention` uchun.** Bu butun saytning eng katta yuki. 60 o'qituvchi doskani so'rasa — 30 so'rov/s va ~**56 Mbit/s keraksiz trafik** (500 chiziqda).

#### 3. Haqiqiy uvicorn serveri ustida yuk (Windows, 1 jarayon)

| Sinov | Natija |
|---|---|
| `attention`, 1 mijoz | 117 so'rov/s, **8.8 ms CPU/so'rov**, javob 8 ms |
| `attention`, 16 mijoz | 185 so'rov/s (bitta jarayon chegarasi), p95 101 ms |
| `lessons?status=live`, 30 mijoz | 61 so'rov/s, 30 ms CPU/so'rov |

Ya'ni **Windows'da bitta jarayon ~120–185 yengil so'rov/s** beradi. Linux'da bu yuqoriroq bo'lishi kutiladi, **lekin o'lchanmagan.**

#### 4. WebSocket (chat/doska/bildirishnoma)

| | Natija |
|---|---|
| Xotira, har ochiq ulanish | **34 KB** (735 ulanish o'lchandi, ichki test; haqiqiy uvicorn ulanishi biroz ko'proq xotira olishi mumkin — o'lchanmagan) |
| Ulanishni ochish | 5.3 ms (bazani tekshirish bilan) |
| 1 xabar 60 kishilik guruhga | **30 ms** (= 0.5 ms har yetkazishga; Redis'siz) |
| Kimda nechta ulanish | bildirishnoma (har kirgan) + chat (ochiq bo'lsa) + doska (darsda) |

3 000 ulanish ≈ 100 MB (+ haqiqiy serverdagi qo'shimcha) — xotira bu yerda **muammo emas**.

#### 5. Dars yozuvi (haqiqiy Chrome kodlovchisi, VP8, 1.5 Mbit/s chegara, 15 kadr/s)

| Dars turi | Video hajmi |
|---|---|
| Slayd/matn (10 s da almashadi) | 0.17 MB/daq → **15 MB / 90 daq** |
| Doskada yozish | 1.57 MB/daq → **141 MB / 90 daq** |
| **Eng yomon** (butun ekran doim o'zgaradi) | 8.2 MB/daq → **741 MB / 90 daq** |
| Audio (Opus ~64–90 kbit/s) | ~**60 MB / 90 daq** |

⇒ **Odatiy dars (slayd/doska): webm ~75–200 MB + mp4 ~70–130 MB ≈ 150–330 MB.** Avvalgi "1 GB/dars" taxminim 3–5 marta **ko'p** edi.

| Ish | Real narx |
|---|---|
| Yozuv bo'lagi (5.6 MB) qabul qilish | **21 ms** (diskka yozish bilan) — soniyada 1 bo'lak = 2% yadro |
| Birlashtirish (ffmpeg `-c copy`) | 90 daqiqalik dars uchun **~2–3 soniya**, 0.2 CPU-soniya |
| **MP4 ga o'tkazish** (loyiha buyrug'i, 2 yadro) | slayd/doska: **~6 CPU-daqiqa / 90 daqiqalik dars**; eng yomon: **~17 CPU-daqiqa** |
| MP4 hajmi | video 4–60 MB + audio 65 MB (AAC 96k) |

60 dars/kun uchun MP4 o'tkazish = 6–17 yadro-**soat**/kun = ikki yadroda **3–8 soat/kun**. Bu **yetadi** (avvalgi "18 soat" taxminim noto'g'ri edi).

#### 6. Jarayon xotirasi

Bitta Django jarayoni (hamma kod yuklangan, bir necha ming so'rovdan keyin): **~172 MB**. 11 worker (8 web + 3 ws) + cron + transcoder ≈ **2.5–3 GB**. 32 GB serverda xotira muammo emas; 16 GB'da ham sig'adi (baza bilan).

---

#### 7. Bundan chiqadigan xulosalar (faqat o'lchovga asoslangan)

1. **Eng katta API yuki — `attention` so'rovi (har 3 s).** 1 500 o'quvchi = 500 so'rov/s: ichki narxda ~1 yadro, Windows end-to-end narxda ~4.4 yadro. Uni 3 s dan 15–20 s ga chiqarish yoki WebSocket/LiveKit orqali berish yukni 5–7 barobar kamaytiradi. **Eng arzon va eng katta tejash.**
2. **O'qituvchining doska so'rovi (har 2 s, 235 KB)** — WebSocket ulangan bo'lsa ham ketyapti. To'xtatilsa 56 Mbit/s trafik va ~1 yadro tejaladi. (Kod bo'yicha aniqlandi, haqiqiy darsda tarmoq oynasida tasdiqlash kerak.)
3. **Sekin so'rovlar tuzatilishi kerak:** `GET /lessons/` (64 SQL — har dars uchun 3 ta qo'shimcha so'rov: `quiz_id`, `avg_rating`, `rating_count`), `analytics/me` (1.4 s), `trends` (0.65 s), `dashboard/teacher` (0.19 s). Bular kam so'raladi, lekin 500 o'qituvchi ko'p bo'lsa sezilarli.
4. **Login to'lqini** — dars boshlanishida (xohlansa) bir qancha yadroni bir daqiqaga band qiladi. Throttle (`auth: 30/min`) esa **bitta IP** (maktab) uchun hammani to'sishi mumkin — alohida tekshirish kerak.
5. **Disk:** yozuvlar uchun avvalgidan 3–5 marta kam joy kerak. 60 dars/kun × ~0.25 GB ≈ **15 GB/kun** (webm+mp4), WebM o'chirilsa ~7 GB/kun.
6. **Qaysi serverda nima:** API yuki hozircha taxminan **3.5–8 yadro** (1 500 o'quvchi darsda; yuqoridagi tuzatishlarsiz), bu **APP uchun RS 4000 mantiqli** degan avvalgi qarorni qo'llab-quvvatlaydi, lekin LiveKit narxi (MEDIA) hali **o'lchanmagan**.

#### 8. Hali o'lchanmaganlar (taxmin QILMAYMAN, o'lchash kerak)

| Nima | Nima kerak |
|---|---|
| **LiveKit** (1 500 tomoshabin necha yadro/trafik) | Rasmiy `livekit-server` + `lk` vositasi (GitHub'dan yuklab olish — **sizning ruxsatingiz kerak**) |
| **Linux'dagi** haqiqiy so'rov narxi (uvloop) va **Postgres** | WSL (Ubuntu) ichida Postgres + Python o'rnatish — **ruxsat kerak** |
| **Hozirgi prod yuki** (haqiqiy foydalanish) | Eski serverda 4 ta buyruq ishga tushirib, natijani yuborasiz (pastda) |
| Redis orqali chat tarqatish narxi | WSL'da Redis o'rnatish bilan birga |

##### Eski (Contabo) serverda ishga tushiradigan buyruqlar — hozirgi haqiqiy raqamlar uchun
```bash
docker stats --no-stream
du -sh /var/lib/docker/volumes/edu_platform_recordings/_data /var/lib/docker/volumes/edu_platform_media/_data /var/lib/docker/volumes/edu_platform_pgdata/_data
ls -lhS /var/lib/docker/volumes/edu_platform_recordings/_data | head -15
docker exec edu_platform-db-1 psql -U edtech -d edtech -c "select (select count(*) from accounts_user) users, (select count(*) from lessons_lesson) lessons, (select count(*) from lessons_lessonrecording) recordings, (select count(*) from chat_message) messages;"
```
(Dars paytida `docker stats --no-stream` ni yana bir marta ishga tushiring — jonli dars vaqtidagi haqiqiy yuk.)

---

### 2-QISM: Linux + PostgreSQL + Redis + LiveKit'da yakuniy o'lchov (2026-10-27)

**Muhit:** WSL2 Ubuntu 26.04, 16 oqim, **PostgreSQL 18** (prod: 17), **Redis 8** (prod: 7), Python 3.14 (prod: 3.13), `gunicorn` + `uvicorn[standard]` (uvloop), **LiveKit 1.13.4** (aynan prod versiyasi). Baza — Postgres'da 10 000 foydalanuvchilik (158 MB). Hamma narsa bitta kompyuterda, shuning uchun yuk generatori serverdan resurs "o'g'irlaydi" (pastda chegaralar).

#### 9. Linux + Postgres'da bitta so'rov narxi (ichki o'lchov; Windows'dagidan farqi katta!)

| So'rov | Windows+SQLite | **Linux+Postgres+Redis** |
|---|---|---|
| `attention` (har 3 s) | 1.8 ms | **3.2 ms** |
| `unread-count` | 1.5 | 3.0 |
| `GET /lessons/?status=live` | 13.8 | 12.3 |
| `GET /lessons/?page_size=20` (64 SQL) | 164 | **47** |
| `GET /chat/rooms/` | 44 | 39 |
| `GET /chat/rooms/{id}/messages/` | 31 | 43 |
| `POST /live/token/` (darsga kirish) | 10.3 | 9.7 |
| `POST /chat/rooms/{id}/send/` | 14 | 14 |
| `GET /dashboard/teacher/` | 194 | **58** (SQL 50) |
| `GET /analytics/me/` | 1 371 | **351** (SQL 311) |
| `GET /analytics/me/trends/` | 655 | **200** (SQL 173) |
| `POST /auth/login/` | 453 | **169** |
| Python jarayoni xotirasi | 172 MB | 209 MB |

Postgres'da ro'yxat so'rovlari (64 ta kichik SQL) tezlashdi; **tahlil so'rovlari hamon sekin va baza tomonda** (`analytics/me` 311 ms SQL) — indeks/so'rovni qayta yozish kerak.

#### 10. ENG MUHIM TOPILMA: baza ulanishlari (haqiqiy `gunicorn + uvicorn`, Postgres, 1 jarayon, 64 parallel so'rov)

| Konfiguratsiya | So'rov/s | CPU/so'rov | Postgres ulanishlari | Xatolar |
|---|---|---|---|---|
| **Hozirgi prod:** ASGI + `CONN_MAX_AGE=60` | **31** (qulaydi) | 42 ms | **199** (chegara!) | **872 so'rov xato, 3 500 "too many clients"** |
| ASGI + har so'rovda yangi ulanish | 113 | 14.4 ms | 0 | 0 |
| ASGI + ulanishlar puli (`pool`, 12) | 132 | 8.4 ms | 12 | 0 |
| **WSGI `gthread` (1 jarayon × 8 oqim)** | **263** | **4.5 ms** | **8** | 0 |
| **WSGI, 4 jarayon × 8 oqim** | **853–890** | **5.2–5.4 ms** | 32 | 0 |

**Sabab:** Django ASGI har parallel so'rovni alohida oqimda bajaradi, har oqim o'z baza ulanishini ochadi va `CONN_MAX_AGE=60` uni ochiq qoldiradi — ulanishlar soni cheklanmaydi. Prod'da Postgres standart 100 ulanishga ega, 3 jarayon. **Dars boshlanishida parallel so'rovlar ko'payganda bu xatoga olib keladi.** WSGI `gthread` ulanishlarni `jarayonlar × oqimlar` bilan cheklaydi va 2 barobar kam protsessor yeydi. `docker-compose.app.yml` dagi `web` xizmati shunga o'tkazildi (WebSocket `ws` xizmatida ASGI'da qoladi). **Hozirgi prod (`docker-compose.prod.yml`) hamon ASGI + CONN_MAX_AGE=60 da va bitta jarayon ham HTTP, ham WebSocket'ni ushlaydi** — u yerda shu xavf bor.

`Postgres` o'zi bu yuk ostida (890 so'rov/s): **atigi 0.39 yadro**, 155 MB. Ya'ni baza hozircha to'siq emas.

#### 11. LiveKit (1.13.4, bitta tugun, 1 o'qituvchi video+ovoz har xonada, 25 tomoshabin/xona)

| Tomoshabin | LiveKit CPU (o'rtacha / p95) | Xotira (RSS) | Tomoshabinga bitreyt | Paket yo'qotish |
|---|---|---|---|---|
| 20 | 0.06 yadro | 98 MB | – | 0% |
| **250** | **0.73 / 0.93 yadro** | 554 MB | 343 kbit/s | **0%** |
| **500** | **1.57 / 2.12 yadro** | 972 MB | 349 kbit/s | **0%** |
| 1 000 | 3.0 yadro (**yuk generatori to'ldi: ~25% yo'qotish — NATIJA ISHONCHSIZ**) | 2.1 GB | 145 kbit/s | 25% |
| 500, "high" sifat | 3.1 yadro (generator to'ldi, ~50% yo'qotish — ishonchsiz) | 1.6 GB | – | – |

**Toza (ishonchli) natija: 500 tomoshabingacha.** Undan yuqorisini bu kompyuter (generator + server bir joyda, load avg 11/16) tekshira olmadi — bu LiveKit chegarasi emas, **test mashinasi chegarasi**. Chiziqli ekstrapolyatsiya (faqat 250 va 500 dan): **~3.1 yadro / 1 000 tomoshabin** (345 kbit/s da), **~2 MB xotira / tomoshabin**. 1 500 tomoshabin ≈ **4.7 yadro, ~3 GB xotira** (taxminiy, o'lchanmagan). Yuqori sifatli (1+ Mbit/s) videoda CPU/trafik oshadi — buni haqiqiy darsda frontend `adaptiveStream` (qo'shilgan) bilan tekshirish kerak.

#### 12. RESURS SARFI — CPU, RAM, STORAGE (10 000 ro'yxatdan o'tgan, ~60 parallel dars, ~1 500 o'quvchi videoda, ~2 000 onlayn)

Manba: yuqoridagi o'lchovlar × frontend kodidagi so'rov chastotasi. **✓ = o'lchangan, ~ = o'lchovdan hisoblangan, ? = o'lchanmagan.**

##### CPU (yadro, cho'qqi paytida)

| Komponent | Hozirgi kod | 4 ta tuzatishdan keyin* |
|---|---|---|
| API (web, WSGI): `attention` 500 so'rov/s × 5.3 ms ✓ | 2.7 | 0.5 |
| API: doska so'rovi (o'qituvchi, har 2 s) ~ | 1.1 | 0 |
| API: qolgan so'rovlar (xabarlar, jonli darslar ro'yxati, chat, sahifalar) ~ | 1.5 | 1.5 |
| API: kirish (login) to'lqini (1 500 ta 5 daqiqada, eng yomon) ~ | 0.85 | 0.85 |
| **API jami** | **~6.1** | **~2.9** |
| PostgreSQL (890 so'rov/s da 0.39 ✓) ~ | 0.6–1.0 | 0.3–0.5 |
| WebSocket (ws) — 660 yetkazish/s × 0.5 ms ✓ | 0.35 | 0.35 |
| Redis ~ | 0.1 | 0.1 |
| Yozuv: bo'lak qabul qilish (4/s × 21 ms) ✓ | 0.08 | 0.08 |
| Yozuv: MP4 o'tkazish (60 dars × 6–17 CPU-daq / 24 s) ✓ | 0.25–0.7 (cho'qqi 2 gacha) | shu |
| **APP server jami** | **~7.5–10 yadro** | **~4–5 yadro** |
| **LiveKit (MEDIA)**: 1 500 tomoshabin ~ | **~4.7** | ~4.7 (adaptive bilan kamayishi kutiladi, o'lchanmagan) |

\* tuzatishlar: (1) `web` → WSGI gthread [yangi serverlar uchun qilindi], (2) `attention` 3 s → 15 s, (3) doska so'rovini to'xtatish (WebSocket bor), (4) N+1 va tahlil so'rovlari. **RS 4000 (12 yadro) APP uchun hozirgi kodda ham yetadi (~65–85%), tuzatishdan keyin ~35–40%. RS 2000 (8 yadro) MEDIA uchun yetadi (~60%).** Test kompyuteri protsessori (AMD Zen 3+) netcup EPYC 9645 (Zen 5) dan sekinroq bo'lishi mumkin — raqamlar ehtiyotkor tomonda.

##### RAM

| Komponent | Sarf |
|---|---|
| web: 8 jarayon × ~170 MB ✓ (4 jarayon = 679 MB) | ~1.4 GB |
| ws: 3 jarayon × ~210 MB ✓ + 4 000 ulanish × 34 KB ✓ | ~0.8 GB |
| PostgreSQL: ma'lumot 158 MB + 64–170 ulanish ~ | ~1.5–3 GB (`shared_buffers=8GB` ko'p, 2–4 GB yetadi) |
| Redis ✓ (1.1 MB ishlatilgan) | <0.2 GB |
| cron + transcoder + ffmpeg ~ | ~0.8 GB |
| Operatsion tizim ~ | ~0.6 GB |
| **APP jami** | **~5.5–7 GB (RS 4000 ning 32 GB'idan ~20%)** |
| **LiveKit (MEDIA)**: ~2 MB × 1 500 tomoshabin ✓/~ | **~3 GB (RS 2000 ning 16 GB'idan ~20%)** |

**Xotira hech bir serverda to'siq emas.** Asosiy to'siq — CPU.

##### STORAGE

| Nima | Sarf |
|---|---|
| Baza, 10 000 foydalanuvchi boshlang'ich ✓ | **158 MB** (davomat 68 MB / 276 ming qator; bildirishnomalar 34 MB / 149 ming; chat 13 MB / 36 ming) |
| Baza o'sishi (yiliga) ~ | ~5–6 GB (eng kattasi — bildirishnomalar ~4 GB; tozalanmaydi) |
| **Dars yozuvi, 1 ta 90 daqiqalik dars** ✓ | WebM: 75–200 MB (slayd/doska; eng yomon ~800 MB) + MP4: 70–130 MB |
| 60 dars/kun uchun yozuvlar ~ | **9–20 GB/kun** (WebM+MP4, hozir) · 4–8 GB/kun (faqat MP4) |
| Yozuvlar, 1 yil ~ | **3–7 TB** (hozir) · 1.5–3 TB (faqat MP4) — **o'chirilmaydi** |
| netcup RS 4000 diski (512 GB) | **~1–4 oyga yetadi** → qo'shimcha disk yoki tashqi saqlash KERAK |

#### 13. LOYIHA HOLATINING OPTIMALLIK BAHOSI

Baho — **resurs samaradorligi va yuk ostida ishonchlilik** bo'yicha, faqat o'lchovlarga tayanib.

| Yo'nalish | Ball | Asos (o'lchangan) |
|---|---|---|
| Baza ulanishlari / bir vaqtdalik | **3/10** | ASGI + `CONN_MAX_AGE=60`: 64 parallel so'rovda 199 ulanish, 3 500 xato, o'tkazuvchanlik 31 so'rov/s'ga qulaydi (prod'da hozir shunday) |
| Mijoz so'rov chastotasi (polling) | **3/10** | `attention` har 3 s (500 so'rov/s); o'qituvchi doskani har 2 s butunlay so'raydi (235 KB) — WebSocket ulangan bo'lsa ham |
| Bitta so'rov samaradorligi | **6/10** | Ko'pi 3–15 ms, 2–12 SQL; lekin darslar ro'yxati 64 SQL (N+1), tahlil 46 SQL/351 ms, davomat 158 ms |
| Real vaqt (chat/doska WebSocket) | **8/10** | 34 KB/ulanish, 0.5 ms/yetkazish, Redis qatlami; HTTP bilan bir jarayonda (yangi rejada ajratilgan) |
| Jonli video (LiveKit) | **8/10** | SFU, simulcast; 3.1 yadro/1 000 tomoshabin, 0% yo'qotish 500 gacha; `adaptiveStream` qo'shildi (haqiqiy darsda tasdiqlanmagan) |
| Dars yozuvi quvuri | **8/10** | Yozish brauzerda (server CPU yo'q); bo'lak 21 ms; birlashtirish 2 s; MP4 6–17 CPU-daq; takrorlanishdan himoya va avto-tiklash bor. Kamchilik: WebM o'chirilmaydi |
| Ma'lumotlar bazasi (sxema/indeks) | **7/10** | Yengil so'rovlar Postgres'ni deyarli yuklamaydi (0.39 yadro/890 so'rov/s); baza ixcham; og'ir agregatlar (tahlil) SQL-bog'liq |
| Saqlash (disk) boshqaruvi | **4/10** | Yozuvlar cheksiz o'sadi, WebM+MP4 ikkalasi saqlanadi, muddat/tozalash yo'q, faqat mahalliy disk |
| Autentifikatsiya narxi | **7/10** | Kirish 169 ms (PBKDF2, xavfsizlik uchun to'g'ri); yangilash 15 ms; IP bo'yicha throttle maktab (bitta IP) uchun xavfli |
| Joylashtirish / kuzatuv | **5/10** | Compose bor, yangi 2-serverli reja yozilgan lekin sinalmagan; monitoring faqat konteyner namunasi; zaxira tiklash sinalmagan |

##### **UMUMIY: 5.5 / 10** (hozirgi holat)

**Nega ayni shu:** asos (arxitektura, realtime, video, yozuv) yaxshi qurilgan, lekin **uchta o'lchangan muammo** yuk ostida ishonchlilikni buzadi: baza ulanishlari, 3 soniyalik polling va doska polling'i. Ular tuzatilsa va saqlash boshqarilsa, **taxminan 8/10** bo'ladi:

1. `web` ni WSGI gthread (yoki ulanishlar puli) ga o'tkazish — **yangi serverlar uchun qilindi** (`docker-compose.app.yml`); eski prod'da hali yo'q.
2. `attention` so'rovini 3 s dan 15–20 s ga chiqarish (yoki LiveKit data kanaliga) — frontend.
3. O'qituvchi doska so'rovini to'xtatish (WebSocket ulangan paytda) — frontend.
4. Darslar ro'yxati N+1 (3 SQL/dars) va `analytics/me`, `trends`, `dashboard/teacher` so'rovlarini tezlashtirish — backend.
5. MP4 tayyor bo'lgach WebM'ni o'chirish, yozuvlar uchun qo'shimcha disk/tashqi saqlash.

**O'lchanmaganlar (halol):** (a) 1 000+ LiveKit tomoshabin (test kompyuteri chegarasi); (b) netcup EPYC 9645 protsessorida haqiqiy tezlik; (c) Redis orqali chat yetkazish narxi; (d) haqiqiy prod yuki (eski serverdan `docker stats` natijasi hali kelmagan); (e) cron ishlarining narxi.

---

#### 14. TUZATISHLARDAN KEYIN QAYTA O'LCHOV (2026-10-27, Linux + Postgres 18 + Redis, o'sha 10 000 foydalanuvchili baza)

Birinchi o'lchovda topilgan muammolar tuzatildi va **o'sha usulda qayta o'lchandi**. Tuzatishlar hali prod'da emas — deploy'dan keyin kuchga kiradi.

| So'rov | Oldin | Keyin | Nima qilindi |
|---|---|---|---|
| Darslar ro'yxati | 64 SQL / 47 ms | **4 SQL / 14 ms** | N+1 → sub-so'rovlar |
| Davomat (20 qator) | 124 SQL / ~158 ms | **7 SQL / 17 ms** | guruhli yuklash |
| Tahlil `analytics/me` | 46 SQL / 351 ms | **16 SQL / 26 ms** | guruhli agregatlar |
| Tahlil `trends` | 200 ms | **5 SQL / 19 ms** | filtrli agregat |
| O'qituvchi paneli | 58 ms | **8 SQL / 11 ms** | guruhli |
| Kurslar ro'yxati (o'qituvchi, 5 kurs) | 28 SQL | **6 SQL / 12 ms** | o'quvchilar soni, o'z holati, o'qituvchi — oldindan yuklanadi |
| Bildirishnomalar (o'quvchi) | 33 SQL | **5 SQL / 10 ms** | o'qituvchi reytingi/sertifikatlari bir so'rovga keshlanadi |
| Chat xonalari (5 xona) | 31 SQL | **12 SQL / 38 ms** | o'qilmagan/belgilanish/oxirgi o'qilgan — bitta annotatsiyali so'rov; xona soniga bog'liq emas |
| Baza ulanishlari | 64 parallel → 199 ulanish, 3 500 xato | **chegaralangan** (`DB_POOL_MAX` yoki WSGI gthread) | ulanishlar puli |
| O'qituvchi doska so'rovi | 235 KB har 2 s | **~100 bayt har 3 s** (`/live/lesson/<id>/signals/`) | yengil endpoint |
| `attention` so'rovi | har 3 s | **har 6 s** (tekshiruv oynasi 15 s + 8 s imtiyoz) | frontend |
| `away_students` | butun jurnalni o'qiydi | **faqat hozir chiqib turganlar** (SQL'da) + indeks | `FocusEvent(lesson, student, created_at)` |
| Cron | 8 ta `sleep`-sikl, har ishga tushish ~1 CPU-s (~0,15 yadro doimiy) | **bitta doimiy jarayon** (`run_scheduler`) | Django bir marta yuklanadi |

**Topilgan va tuzatilgan xato:** kurs o'chirilganda faqat asosiy WebM o'chardi — MP4 nusxa va xom video/audio qismlar diskda yetim qolardi. Endi hammasi o'chadi (test bilan).

**Yangi buyruqlar (hech biri o'zi ishga tushmaydi):**

- `python manage.py prune_recordings` — faqat hisobot: qancha GB bo'shatish mumkin. `--apply` xom qismlarni, `--apply --drop-webm` MP4 tayyor yozuvlarning asl WebM'ini ham o'chiradi (faqat 7 kundan eski, fayl o'qilishi tekshirilgandan keyin). Yozuv MP4 bilan ko'rsatiladi.
- `python manage.py prune_notifications [--days 180] [--apply]` — eski bildirishnomalar (yiliga ~4 GB o'sishning asosiy qismi).
- `.env`: `THROTTLE_AUTH`, `THROTTLE_USER`, `THROTTLE_ANON` — maktab Wi-Fi'si (bitta IP) uchun kirish chegarasini oshirish.

##### Yangilangan baho (deploy va quyidagi shartlardan keyin)

| Yo'nalish | Oldin | Keyin |
|---|---|---|
| Baza ulanishlari / bir vaqtdalik | 3 | **8** (puli o'lchangan; real yukda tasdiqlash kerak) |
| Mijoz so'rov chastotasi | 3 | **6** (doska polling'i yengillashdi; haqiqiy darsda tasdiqlanmagan) |
| Bitta so'rov samaradorligi | 6 | **8** |
| Saqlash boshqaruvi | 4 | **5** (vositalar tayyor, lekin qo'llanmagan va saqlash muddati hal qilinmagan) |
| Joylashtirish / kuzatuv | 5 | **5.5** (cron birlashtirildi; zaxira tiklash hali sinalmagan) |
| **UMUMIY** | **5.5** | **~7 / 10** |

8/10 ga yetish uchun qolgan: (1) deploy + ikki hisob bilan haqiqiy darsda tekshirish; (2) `prune_recordings --apply --drop-webm` ni qo'llash va yozuv saqlash muddatini hal qilish; (3) zaxira tiklashni bir marta sinab ko'rish; (4) prod'dan haqiqiy `docker stats`.


[↑ Mundarija](#mundarija)

---

## HISOB_EKRAN_ULASHISH_VA_TRAFIK_2026-11-17

> Avvalgi fayl: `HISOB_EKRAN_ULASHISH_VA_TRAFIK_2026-11-17.md`

### Ekran ulashish bitrate'i va server trafigi: hisob-kitoblar va xulosa

Sana: 2026-11-17. Savol: "Ekran ulashishni 5 fps / ~0.6 Mbps ga tushirsak, trafik cheklovi yo'qoladi va bitta server yetadi" degan da'vo to'g'rimi.

#### 1. Xulosa

1. Hisob-kitobning o'zi to'g'ri, lekin u ekran ulashish **doim eng yuqori bitreytda** ketadi degan taxminga tayanadi. O'lchovda slayd va doskada ekran ulashish 0.02-0.15 Mbps, ya'ni 0.6 dan ancha past. Bu holatda cheklovni tushirish deyarli hech narsa bermaydi.
2. 0.6 Mbps faqat to'liq harakatli videoda trafikni kamaytiradi (1.5 → 0.58 Mbps). Hujjat aylantirishda esa sifatni buzadi: kadr tezligi 15 dan ~1 ga tushadi.
3. "Majburiy" deb qo'yish tavsiya etilmaydi. Haqiqiy xavf trafik limiti emas, kamera bitreyti va bir vaqtdagi sinflar soni. Bu ikkalasi hali haqiqiy o'lchanmagan.
4. 3 TB limiti yumshoq: oshsa server o'chmaydi, 300 Mbit/s gacha sekinlashtiriladi (3-bo'lim).

#### 2. Hozirgi sozlamalar (frontend kodidan)

| Nima | Qiymat | Fayl |
|---|---|---|
| Ekran ulashish | 1280×720, 15 fps, maks. 1.5 Mbps, simulcast yo'q | `src/modules/live/lib/screen-capture.ts` |
| Kamera | 540p, 24 fps, simulcast: qo'shimcha 180p qatlam | `src/pages/live/live-lesson-page.tsx` |
| Xona | `adaptiveStream: true`, `dynacast: true` | shu fayl |
| O'quvchi kamerasi | Faqat o'qituvchi "ochiq rejim" yoqsa (backend token ruxsati). Odatda faqat o'qituvchi videosi tarqaladi | `apps/live/services.py` |

Doska va chat LiveKit orqali emas, WebSocket orqali (APP serveri), MEDIA trafigiga kirmaydi.

#### 3. Limit nima

netcup RS 2000 G12 Pro sahifasida: so'nggi 24 soatda trafik 3 TB dan oshsa, vaqtincha 300 Mbit/s gacha sekinlashtiriladi, shart yo'qolgach olib tashlanadi. Manba: [netcup RS 2000 G12 Pro](https://netcup.com/en/server/root-server/rs-2000-g12-iv-pro-nue-adv25).

- Bu 24 soatlik sirpanuvchi oyna, kalendar kun emas.
- 3 TB / 24 soat = o'rtacha 278 Mbit/s.
- Limitga LiveKit'dan tashqari yozuv ko'rish (MP4 yuklash) ham kiradi.
- Tekshirilmagan: bizda MEDIA serveri hujjatda RS 4000. Uning shartlarini netcup sahifasida alohida tekshirish kerak.

#### 4. Formulalar

- 1 Mbps × 1 soat = 0.45 GB (1 tomoshabin uchun).
- Tomoshabin bitreyti = o'qituvchi kamerasi + ekran ulashish + ovoz.
- Kunlik byudjet (sinf-soat) = 3000 GB / (o'quvchilar × bitrate × 0.45).

#### 5. O'lchov: ekran ulashish bitreyti

**Usul.** Brauzerning haqiqiy WebRTC kodlovchisi (Chrome, VP8), 1280×720 tuvaldan olingan oqim, `contentHint=detail`, `degradationPreference=maintain-resolution`. Sozlama `sender.setParameters` bilan beriladi. Har bir variantga 16 soniya, birinchi 4 soniya hisobga olinmagan, bitreyt `getStats` dagi `bytesSent` farqidan olingan. Test fayli: scratchpad'dagi `screen_test.html` (repoda yo'q).

| Kontent | Hozirgi: 15 fps / 1.5 Mbps | 5 fps / 0.6 Mbps | 10 fps / 0.6 Mbps |
|---|---|---|---|
| Statik slayd (10 s da almashadi) | 24 kbit/s | 18 kbit/s | 18 kbit/s |
| Doskada yozish | 146 kbit/s, 15 fps, QP 15 | 105 kbit/s, 5 fps, QP 15 | 120 kbit/s, 10 fps, QP 15 |
| Hujjat aylantirish (150 px/s) | 763 kbit/s, 15 fps, QP 17 | 497 kbit/s, **1.1 fps**, QP 106 | 502 kbit/s, **1.1 fps**, QP 106 |
| To'liq harakatli video | 1500 kbit/s, 15 fps, QP 60 | 583 kbit/s, 5 fps, QP 53 | 601 kbit/s, 10 fps, QP 81 |

QP: kodlash sifati ko'rsatkichi, kichigi yaxshi. Hujjat aylantirishda 0.6 Mbps ga sig'may, kodlovchi kadrlarni tashlaydi va sifat keskin tushadi.

**Bu o'lchovning cheklovlari:**
- Kontent sintetik, haqiqiy darsdan emas. Aylantirish tezligi va video harakati real darsdagidan farq qilishi mumkin.
- Har variant bir marta o'lchangan, takrorlanmagan (taxminan ±10% xato).
- Loopback: haqiqiy tarmoq tiqilishi va tomoshabin tomoni hisobga olinmagan.
- Kadrlar `canvas.captureStream` dan, haqiqiy `getDisplayMedia` dan emas. Aylantirishdagi "~1 fps" natijani haqiqiy ekran yozuvida qayta tekshirish kerak.
- 2026-10-27 dagi eski o'lchov (Chrome, VP8, 1.5 Mbit/s, 15 fps) ham shunga mos: slayd ~0.02, doska ~0.2, eng yomoni ~1.1 Mbps.

#### 6. Qarshi dalil: "Pro'da 45 kishilik sinflar bilan 5 soat, 0.6 Mbps bilan 9 soat"

Men buni quyidagicha tushundim va hisoblab qayta tikladim. Agar boshqacha nazarda tutilgan bo'lsa, ayting.

Taxmin: bir vaqtda 15 ta sinf × 45 o'quvchi = 675 tomoshabin; har tomoshabinga 2.0 Mbps (kamera ~0.5 + ekran 1.5).

| | Tomoshabin bitreyti | Kunlik byudjet | 15 sinf uchun |
|---|---|---|---|
| Hozirgi (1.5 Mbps) | 2.0 Mbps | 74 sinf-soat | **4.9 soat** |
| 0.6 Mbps | 1.1 Mbps | 135 sinf-soat | **9.0 soat** |

Arifmetika to'g'ri chiqdi: 4.9 ≈ "5 soat", 9.0 = "9 soat". O'qituvchi kuniga 3×2 = 6 soat o'tsa, 5 dan oshadi, 9 ichida qoladi. Bu mantiqan izchil.

**Qayerda zaif:**

1. **Taxmin: ekran doim eng yuqori bitreytda.** O'lchov bo'yicha slayd 0.02, doska 0.15 Mbps. U holda tomoshabin bitreyti 0.4-1.0 Mbps (kameraga qarab) va 15 sinf uchun byudjet 10-26 soat. 0.6 ga tushirmasdan ham 9 soatdan ko'p (7-bo'limdagi jadval).
2. **0.6 Mbps matn aylantirishda sifatni buzadi** (~1 fps, QP 106). Bu "majburiy" qilishga qarshi asosiy dalil.
3. **Kamera bitreyti noaniq.** 0.35 Mbps (o'lchangan) sintetik yuk generatoridan olingan, haqiqiy veb-kameradan emas. Haqiqiy 540p/24 fps kamera 0.5-0.8 Mbps berishi mumkin. Bu natijaga ekran sozlamasidan ko'proq ta'sir qiladi (7-jadval).
4. **15 ta bir vaqtdagi 45 kishilik sinf** taxmini bizda tasdiqlanmagan. Haqiqiy son kerak.
5. Limit yumshoq: oshganda 300 Mbit/s gacha sekinlashadi, uzilmaydi. 300 Mbit/s ≈ 270 tomoshabin × 1.1 Mbps.
6. Byudjetga yozuv ko'rish ham kiradi (1 ta 90 daqiqalik MP4 ≈ 70-130 MB, 45 o'quvchi ko'rsa ≈ 3-6 GB).

#### 7. Sezgirlik jadvali (45 o'quvchi, 15 bir vaqtdagi sinf; qiymat = limitga yetguncha soat)

Kamera bitreyti ustunlar, ekran kontenti qatorlar. Hisob: 3000 / (45 × (kamera + ekran) × 0.45) / 15.

| Ekran kontenti | Kamera 0.35 | Kamera 0.6 | Kamera 0.8 |
|---|---|---|---|
| Slayd (0.024) | 26.4 | 15.8 | 12.0 |
| Doska (0.146) | 19.9 | 13.2 | 10.4 |
| Aylantirish, hozirgi 1.5 Mbps cheklov (0.763) | 8.9 | 7.2 | 6.3 |
| Aylantirish, 0.6 Mbps cheklov (0.497, ~1 fps) | 11.7 | 9.0 | 7.6 |
| Video, hozirgi cheklov (1.5) | 5.3 | 4.7 | 4.3 |
| Video, 0.6 Mbps cheklov (0.583) | 10.6 | 8.3 | 7.1 |

Xulosa jadvaldan: 0.6 Mbps faqat video qatorida sezilarli farq beradi (5.3 → 10.6 soat). Slayd va doskada hozirgi sozlamaning o'zi yetadi. Kamera bitreyti esa qatorlar orasidagi farqdan katta ta'sir qiladi.

Bitta o'qituvchining kunlik trafigi (3 dars × 2 soat × 45 o'quvchi = 270 tomoshabin-soat): 0.38 Mbps da 46 GB, 0.5 da 61 GB, 1.1 da 134 GB, 2.0 da 243 GB. 3 TB ga yetish uchun mos ravishda 65, 49, 22, 12 o'qituvchi.

#### 8. Biz hisobda nimani qildik va qayerda xato bo'lishi mumkin

| Nima | Holat |
|---|---|
| Ekran ulashish kodidagi sozlama | Kod bo'yicha tasdiqlangan |
| Ekran bitreyti o'lchovi | O'lchangan, lekin sintetik kontent va bitta takror |
| 3 TB / 24 soat → 300 Mbit/s | netcup sahifasida tasdiqlangan (RS 2000 G12 Pro). RS 4000 uchun tekshirilmagan |
| Kamera bitreyti | **Noaniq**: 0.35 Mbps sintetik yukdan, haqiqiy kamerani o'lchamadik |
| Bir vaqtdagi sinflar soni | **Noma'lum** |
| LiveKit CPU | Oldingi o'lchov: ~3.1 yadro / 1000 tomoshabin (0.35 Mbps da). 675 tomoshabin ≈ 2 yadro, bu 1.1 yoki 2.0 Mbps da oshishi mumkin, o'lchanmagan |
| Oldingi xabarim "o'qituvchi 7 sinf, 25 o'quvchi, 1.5 soat" | Boshqa taxmin (118 GB har 1 Mbps uchun). Bu hujjatdagi 45 o'quvchi × 3 × 2 soat hisobidan farq qiladi, solishtirib bo'lmaydi |

#### 9. Tavsiya

1. 0.6 Mbps ni majburiy qilmaslik. Matn aylantirishni buzadi, slayd va doskada esa foyda yo'q.
2. Avval haqiqiy raqamlarni olish: MEDIA serverda bir hafta davomida `eth0` trafigini kuzatish (masalan `vnstat`) va dars paytida real kamera bitreyti. Shunda "yetadimi" degan savolga taxmin emas, o'lchov bilan javob beramiz.
3. Haqiqiy ekran yozuvida (`getDisplayMedia`) aylantirish va video testini takrorlash. Kerak bo'lsa o'rta qiymat (masalan 1.0 Mbps) sinash mumkin.
4. Trafik asosan kameradan kelsa, ta'sirli yo'llar: ekran ulashish paytida kamerani kichraytirish yoki o'chirish, kamera bitreyti chegarasi. Bular UI/frontend o'zgarishi, qo'yishdan oldin siz bilan kelishiladi.
5. Xavfsizlik chorasi: MEDIA'da 24 soatlik trafikni kuzatib, 2 TB da adminlarga bildirishnoma yuboradigan tekshiruv (disk tekshiruviga o'xshash). Buni faqat siz aytsangiz qilaman.


[↑ Mundarija](#mundarija)

---

## HISOB_STEAL_VAQT_2026-11-17

> Avvalgi fayl: `HISOB_STEAL_VAQT_2026-11-17.md`

### "Dedicated" yadrolar va steal time: tekshiruv natijasi

Sana: 2026-11-17. Da'vo: "netcup dedicated yadrolarni sekinlashtirgani uchun g'alayon bo'lgan; hisobimiz kafolatlangan yadrolarga tayanadi; steal time (%st) ni kuzatish kerak".

#### 1. Da'vo to'g'rimi

Qisman. Voqea bor, lekin u **G11 avlodiga** tegishli va 2024 yilda bo'lgan.

- LowEndBox va LowEndTalk: [netcup foydalanuvchi g'alayoni](https://lowendbox.com/blog/netcup-faces-user-riot-over-throttling-supposedly-dedicated-cores), [G11 sotuvi to'xtatilgani va unumdorlik 50% ga tushgani haqida munozara](https://lowendtalk.com/discussion/195175/netcup-pauses-all-g11-root-server-orders-and-reduces-performance-by-50). Bir foydalanuvchi benchmark'ida bir yadroli natija 2069 dan 1071 ga tushgan.
- Forumda keltirilgan netcup qo'llab-quvvatlash javobi: dedicated yadro "talab bo'yicha mavjud yadro" deb tushuniladi, har yadroda steal doimiy 3% dan oshsa murojaat qilish kerak.
- Forum yozuvlariga ko'ra muammo 2024 yil avgust-sentyabrda yana takrorlangan. Netcup sababni rasman tushuntirgani topilmadi. Manbalar asosan forum yozuvlari, shuning uchun bu tasdiqlangan texnik sabab emas, shikoyatlar to'plami.
- Bizning serverlar **G12 avlodi** (AMD EPYC 9645, Zen 5, KVM). G12 uchun bunday hodisa haqida ma'lumot topmadim, lekin yo'qligini ham isbotlay olmayman.

#### 2. Bizning serverlarda o'lchandi (faqat o'qish, ma'lumotga tegilmadi)

| | APP (8 yadro) | MEDIA (12 yadro) |
|---|---|---|
| Ishlash vaqti (uptime) | 20 kun | 20 kun |
| Yuklamasiz (bo'sh) paytda `vmstat` steal | 0% | 0% |
| 20 soniya hamma yadro 100% yuk (`nice 19`), steal | **0.063%** | **0.004%** |
| Yuklama paytida band yadrolar | 99.9% | 99.9% |
| Yadrolar bo'yicha taqsimot | bir tekis | bir tekis |

Qo'shimcha: `/proc/stat` bo'yicha 20 kun davomidagi jami steal APP'da umumiy vaqtning 0.05%, band vaqtga nisbatan taxminan 3.7%. MEDIA'da 0.0004%. APP'dagi bu raqam bir marta qisqa muddatli ko'tarilishlardan yig'ilgan bo'lishi mumkin (masalan 31-oktabrdagi yuk sinovi). Hozirgi paytda steal yo'q, lekin vaqt qatori yo'qligi uchun qachon ko'tarilgani noma'lum.

#### 3. Nimani tasdiqlamaydi

- 20 soniyalik sinov sinov paytida steal yo'qligini ko'rsatadi, doim shunday bo'lishini emas. 2024 yildagi hodisa kunlar davomida, qo'shni mijozlar yuki ostida bo'lgan.
- Steal faqat vCPU ishlashga tayyor bo'lganda ko'rinadi. Bo'sh serverda har doim 0 chiqadi, shuning uchun haqiqiy dars yuki paytidagi o'lchov muhim.
- Yadro tezligi (benchmark) o'lchanmadi, faqat steal. Tezlik pasaysa va steal ko'rinmasa, bu usul ushlamaydi.

#### 4. "18 parallel dars o'rniga 12-13" hisobi haqida

Bu "0.5 yadro / dars" taxminiga tayanadi. Bizning o'lchov: LiveKit ~3.1 yadro / 1000 tomoshabin (0.35 Mbps da). 45 kishilik dars uchun ≈ 0.14 yadro. Ya'ni taxmin 3-4 barobar konservativ chiqadi, lekin yuqori bitreytda (ekran + kamera ~2 Mbps) qayta o'lchash kerak. Bundan tashqari yozuv va MP4 o'tkazish ham yadro oladi (3 yadro bilan cheklangan). Aniq javob uchun haqiqiy yuk sinovi kerak.

#### 5. Tavsiya

1. Steal'ni doimiy kuzatish: har daqiqada `/proc/stat` dan steal ulushini fayl/jurnalga yozish va 10 daqiqa ketma-ket 3% dan oshsa adminlarga bildirishnoma yuborish (netcup'ning o'z chegarasi 3%). Bu ikkala serverda oddiy cron skripti, hozir hech narsa o'rnatilmagan.
2. Haqiqiy dars yuki paytida (iloji bo'lsa 2-3 parallel dars) `vmstat 5` natijasini bir marta ko'rish.
3. Yadro tezligini vaqti-vaqti bilan bir xil benchmark bilan o'lchash (masalan haftada bir marta), steal ko'rinmaydigan sekinlashishni ushlash uchun.


[↑ Mundarija](#mundarija)

---


---

<!-- 3. Funksiyalar bo'yicha API hujjatlari -->

## NEW_FEATURES_API

> Avvalgi fayl: `NEW_FEATURES_API.md`

### Yangi backend funksiyalar (2026-09-03) — frontend uchun

Bu hujjat shu sessiyada qo'shilgan **hamma yangi/o'zgargan endpoint**larni
qamrab oladi: o'qituvchi reytingi, o'quvchi ro'yxatdan o'tishi, o'qituvchi
tasdiqlash oqimi, Test (Quiz), sertifikat yuklash, va bitta chat bug-fix.

**Base URL**: `/api/v1/`
**Auth**: hammasida JWT (`Authorization: Bearer <access_token>`), alohida
belgilanmagan bo'lsa.

---

#### 1. O'qituvchi reytingi

Hech qanday yangi endpoint yo'q — mavjud foydalanuvchi ma'lumotiga (`UserSerializer`
qaytaradigan har qanday joyga: `/auth/me/`, qidiruv, o'qituvchilar ro'yxati) ikkita
yangi maydon qo'shildi:

```json
{
  "id": "uuid", "username": "...", "role": "teacher",
  "avg_rating": 4.75,
  "rating_count": 12
}
```

- Faqat `role: "teacher"` bo'lganda hisoblanadi — boshqa rollarda ikkalasi ham `null`.
- `avg_rating` — o'qituvchining **BARCHA** darslari bo'yicha o'rtacha ball (1-5), 2 xona aniqlikda. Hech kim baholamagan bo'lsa `null`.
- `rating_count` — jami baholar soni.

##### Yangi endpoint — admin uchun o'qituvchilar ro'yxati

| Method | Path | Ruxsat | Tavsif |
|---|---|---|---|
| GET | `/auth/teachers/` | admin/super_admin | Barcha o'qituvchilar, `avg_rating`/`rating_count` bilan |

---

#### 2. O'quvchi ro'yxatdan o'tishi

`POST /auth/register/` — endi `role` maydonida `"student"` ham qabul qilinadi
(avval faqat `"teacher"`/`"parent"`).

```json
{ "username": "...", "password": "...", "role": "student", "first_name": "..." }
```

O'quvchi o'zi ro'yxatdan o'tsa ham, javobda `invite_code` keladi — ota-ona
keyinroq shu kod bilan bog'lanishi mumkin (mavjud oqim, o'zgarmagan).

---

#### 3. O'qituvchi tasdiqlash oqimi (faollashtirish)

**O'qituvchi ro'yxatdan o'tgach KIRA OLADI**, lekin admin tasdiqlamaguncha
kurs/dars yaratish kabi amallarga ruxsati yo'q — bunday urinish `403` qaytaradi.

`POST /auth/register/` va `/auth/me/` javobida yangi maydon:

```json
{ "id": "uuid", "username": "...", "role": "teacher", "is_approved": false }
```

##### Yangi endpointlar (admin uchun)

| Method | Path | Tavsif |
|---|---|---|
| GET | `/auth/teachers/pending/` | Hali tasdiqlanmagan (`is_approved=false`) o'qituvchilar |
| POST | `/auth/teachers/{id}/approve/` | Tasdiqlaydi — shundan keyin `is_approved: true`, hammasi ochiladi |

**Frontend uchun muhim**: agar o'qituvchi kirgach kurs/dars yaratishda `403`
olsa, sabab shu bo'lishi mumkin — UI'da "hisobingiz admin tasdig'ini kutmoqda"
degan xabar ko'rsatish kerak (`/auth/me/`dan `is_approved` bilan tekshirib).

---

#### 4. Chat: real-time bug-fix (yangi endpoint yo'q)

Dars tugagach avtomatik yuboriladigan ikkita chat xabari — **video-yozuv
havolasi** va **doska PDF** — avval faqat bazaga yozilib, WebSocket orqali
DARHOL yuborilmasdi (chatni qayta ochmaguncha ko'rinmasdi). Endi tuzatildi —
oddiy xabarlar bilan bir xil real-time push.

**Frontend'da hech narsa o'zgartirish shart emas** — agar WebSocket handler
allaqachon oddiy `chat.message` eventini to'g'ri ishlatayotgan bo'lsa, bu
ikkita xabar turi ham endi xuddi shunday avtomatik keladi.

---

#### 5. Test (Quiz) — YANGI to'liq feature

**Base**: `/api/v1/quizzes/`

Xususiyatlari: faqat variantli savollar (MCQ), **vaqt chegarasi yo'q**,
o'quvchi **cheklanmagan marta qayta topshirishi** mumkin, baholash **darhol
va avtomatik** (AI kerak emas).

##### 5.1. Test yaratish — o'qituvchi

`POST /quizzes/` (ruxsat: teacher, faqat `is_approved: true` bo'lsa)

**So'rov**:
```json
{
  "course": "<course-uuid>",
  "lesson": "<lesson-uuid yoki null>",
  "title": "1-bob testi",
  "description": "Ixtiyoriy",
  "due_at": "2026-09-20T18:00:00Z",
  "opens_at": "2026-09-10T00:00:00Z",
  "questions": [
    {
      "text": "2 + 2 = ?",
      "points": 1,
      "options": [
        { "text": "3", "is_correct": false },
        { "text": "4", "is_correct": true },
        { "text": "5", "is_correct": false }
      ]
    }
  ]
}
```

- `lesson`, `description`, `due_at`, `opens_at` — hammasi **ixtiyoriy** (`null` yoki tushirib qoldirish mumkin).
- Har bir savolda **kamida 2 ta variant** va **aynan 1 ta** `is_correct: true` bo'lishi shart — aks holda `400`.
- `opens_at` — belgilansa, o'quvchi/ota-ona shu vaqtgacha testni **umuman ko'rmaydi** (`404`). O'qituvchi/admin har doim ko'radi.
- **Bildirishnoma**: agar test darhol ochiq bo'lsa (`opens_at` yo'q yoki o'tgan), kursga yozilgan barcha o'quvchilarga real-time bildirishnoma boradi (mavjud notifications infratuzilmasi, `link_type: "quiz"`, `link_id: "<quiz-id>"`). Agar `opens_at` kelajakda bo'lsa — bildirishnoma hozircha YUBORILMAYDI.

**Javob** (`201`) — to'liq struktura, `id`lar bilan (savol/variant `id`lari keyin javob yuborishda kerak bo'ladi):
```json
{
  "id": "quiz-uuid", "course": "...", "lesson": null, "title": "1-bob testi",
  "description": "...", "due_at": "...", "opens_at": null, "created_at": "...",
  "questions": [
    {
      "id": "q1-uuid", "text": "2 + 2 = ?", "points": 1, "order": 0,
      "options": [
        { "id": "o1-uuid", "text": "3", "is_correct": false, "order": 0 },
        { "id": "o2-uuid", "text": "4", "is_correct": true, "order": 1 },
        { "id": "o3-uuid", "text": "5", "is_correct": false, "order": 2 }
      ]
    }
  ]
}
```

##### 5.2. Testlar ro'yxati

`GET /quizzes/` — rolga qarab avtomatik filtrlanadi (o'qituvchi: o'z kurslari;
o'quvchi: yozilgan kurslari, `opens_at` o'tganlar; ota-ona: bog'langan
bolasining kurslari).

```json
[
  { "id": "...", "course": "...", "lesson": null, "title": "...", "description": "...",
    "due_at": null, "opens_at": null, "question_count": 5, "created_at": "..." }
]
```

##### 5.3. Testni ochish

`GET /quizzes/{id}/`

- **O'qituvchi/admin** — `is_correct` bilan (javob kaliti ko'rinadi).
- **O'quvchi/ota-ona** — `is_correct` **YO'Q** (yechish uchun, javob yashiringan).
- Boshqa kursning/yozilmagan kursning testi — `404` (mavjudligi ham bilinmaydi).

##### 5.4. Testni o'chirish

`DELETE /quizzes/{id}/` — faqat egasi o'qituvchi. Boshqasiniki bo'lsa `404`.

##### 5.5. Topshirish — o'quvchi

`POST /quizzes/{id}/attempts/`

**So'rov**:
```json
{
  "answers": [
    { "question": "q1-uuid", "selected_option": "o2-uuid" }
  ]
}
```

Har bir savolga faqat bitta javob; javobsiz qoldirilgan savol ham
maksimal ballga qo'shiladi (adolatli hisob).

**Javob** (`201`) — natija DARHOL, har bir savol bo'yicha to'g'ri javob ochiladi:
```json
{
  "id": "attempt-uuid", "quiz": "...", "student": "...",
  "score": 4, "max_score": 5, "created_at": "...",
  "answers": [
    {
      "question": "q1-uuid", "question_text": "2 + 2 = ?",
      "selected_option": "o2-uuid", "selected_option_text": "4",
      "is_correct": true,
      "correct_option": { "id": "o2-uuid", "text": "4" }
    }
  ]
}
```

`correct_option` — HAR DOIM keladi (to'g'ri javob bo'lsa ham, xato bo'lsa
ham) — o'quvchi xato qilgan bo'lsa, to'g'ri javobni shu yerdan ko'rib,
qayta urinishda tuzatishi mumkin.

##### 5.6. Urinishlar tarixi

`GET /quizzes/{id}/attempts/` — o'quvchi faqat o'zinikini, o'qituvchi/admin/
ota-ona barchasini (ota-ona faqat o'z bolasinikini) ko'radi.

```json
[
  { "id": "...", "quiz": "...", "student": "...", "student_name": "s1",
    "score": 4, "max_score": 5, "created_at": "..." }
]
```

Cheklanmagan qayta urinish — har safar yangi qator qo'shiladi, eskisi o'chmaydi.

---

#### 6. O'qituvchi sertifikatlari — YANGI

`/auth/me/certificates/` — faqat o'qituvchi (`certificate.manage` ruxsati),
faqat **o'zinikiga**.

##### Yuklash

`POST /auth/me/certificates/` — `multipart/form-data`

| Maydon | Majburiymi | Izoh |
|---|---|---|
| `file` | ha | Rasm yoki PDF |
| `title` | yo'q | Masalan "IELTS 8.0" |

Javob (`201`):
```json
{ "id": "cert-uuid", "file": "https://.../media/certificates/2026/09/....png", "title": "IELTS 8.0", "created_at": "..." }
```

##### O'chirish

`DELETE /auth/me/certificates/{id}/` — faqat o'zi yuklaganini. Begonaniki — `404`.

##### Ko'rish

Alohida GET endpoint shart emas — sertifikatlar `UserSerializer` qaytaradigan
HAR QANDAY joyda (`/auth/me/`, o'qituvchilar ro'yxati va h.k.) `certificates`
massivi sifatida avtomatik keladi:

```json
{ "id": "...", "role": "teacher", "certificates": [
  { "id": "cert-uuid", "file": "https://.../....png", "title": "IELTS 8.0", "created_at": "..." }
] }
```

Boshqa rollarda `certificates: []` (bo'sh massiv).

---

#### Muhim eslatmalar

- Barcha yangi endpointlar mavjud RBAC (`RequirePerm`) orqali himoyalangan — noto'g'ri rol/kirish `403`, ko'rishga haqli bo'lmagan obyekt (masalan begona kurs testi) `404` (mavjudligi ham bilinmaydi).
- Migratsiyalar production'da `docker compose ... up -d --build` bilan avtomatik ishga tushadi (`DEPLOY.md`ga qarang) — qo'lda `migrate` kerak emas.


[↑ Mundarija](#mundarija)

---

## LIVE_MODERATION_API

> Avvalgi fayl: `LIVE_MODERATION_API.md`

### Dars moderatsiyasi: Invite / Ban / Guruhdan avtomatik chiqarish

Bugun qo'shilgan 3 ta yangi imkoniyat uchun frontend shartnomasi (Zoom
uslubidagi: o'qituvchi darsga taklif qiladi, xohlagan o'quvchini
chetlashtiradi; guruhdan chiqarilgan o'quvchining ochiq chati o'zi yopiladi).

**Base URL**: `/api/v1/live/`
**Auth**: JWT (`Authorization: Bearer <access_token>`)
**Ruxsat**: uchalasi ham `room.moderate` kaliti bilan ishlaydi — bu allaqachon
TEACHER rolida bor, yangi ruxsat kaliti qo'shilmagan. Faqat **shu darsning
kursiga tegishli o'qituvchi** chaqira oladi — boshqa o'qituvchi `403` oladi.

Xato javoblari umumiy shaklda keladi (`ARCHITECTURE.md`dagi Error Envelope):
```json
{"success": false, "error": {"code": "...", "message": "...", "details": {...}}}
```

---

#### 1. Darsga taklif — `POST /api/v1/live/invite/`

O'quvchiga (yoki hammasiga) "dars boshlandi, kiring" degan **ogohlantirish**
yuboradi. Bu shunchaki bildirishnoma — o'quvchi xonaga baribir o'zi
`POST /api/v1/live/token/` chaqirib kiradi, invite shart emas, faqat uni
xabardor qiladi.

**Body:**
```json
{ "lesson_id": "uuid", "student_id": "uuid | ixtiyoriy" }
```
- `student_id` **berilmasa** → kursga `APPROVED` yozilgan **hamma o'quvchiga**.
- `student_id` **berilsa** → faqat o'sha bittasiga (kursga yozilmagan bo'lsa `404`).

**Javob:**
```json
{ "invited": 5 }
```
(nechta o'quvchiga yuborilgani — sonli)

**Xatolar:** `403` — chaqiruvchi shu kursning o'qituvchisi emas. `404` — dars yoki (student_id berilganda) o'quvchi topilmadi.

##### O'quvchi tomonida qanday keladi

Mavjud bildirishnoma infratuzilmasi orqali — yangi WS kanal shart emas, allaqachon bor:

- **Real-time (onlayn bo'lsa):** `wss://<domain>/ws/notifications/?token=<access>` orqali darhol keladi:
  ```json
  { "type": "notification", "notification": { "id", "sender", "description", "target_type": "user", "created_at" } }
  ```
  `description` matni: `«<dars nomi>» darsi boshlandi — hoziroq kiring.`
- **Oflayn bo'lsa ham:** inboxida qoladi — `GET /api/v1/notifications/` (badge uchun `GET /api/v1/notifications/unread-count/`).

---

#### 2. Chetlashtirish — `POST /api/v1/live/ban/`

O'quvchini shu darsdan **chetlashtiradi**: hozir xonada bo'lsa LiveKit orqali
darhol video/audio ulanishini uzadi, va **qayta kirishini bloklaydi**.

**Body:**
```json
{ "lesson_id": "uuid", "student_id": "uuid" }
```
**Javob:** `{ "ok": true }`
**Xatolar:** `403` — chaqiruvchi egasi emas. `404` — dars yoki o'quvchi topilmadi.

##### Frontendda nima kutish kerak

- Agar o'quvchi hozir xonada bo'lsa — LiveKit client SDK'da `disconnected`/`participant kicked` hodisasi keladi (LiveKit'ning o'z mexanizmi) — shuni ushlab, o'quvchini darsdan chiqaring.
- Ban qilingan o'quvchi **qayta** `POST /api/v1/live/token/` chaqirsa — endi `403`:
  ```json
  {"success": false, "error": {"code": "permission_denied", "message": "Siz bu darsdan chetlashtirilgansiz.", "details": null}}
  ```
- Ban faqat **shu bitta darsga** tegishli (`lesson_id` bo'yicha) — boshqa darslarga yoki kursning o'ziga ta'sir qilmaydi, kurs yozilishi (`Enrollment`) o'zgarmaydi.

#### Chetlashtirishni bekor qilish — `POST /api/v1/live/unban/`

**Body:** `{ "lesson_id": "uuid", "student_id": "uuid" }`
**Javob:** `{ "unbanned": true }` (ban topilmasa `false`)

---

#### 3. Guruhdan chiqarilganda chat avtomatik yopiladi

Bu **yangi endpoint emas** — mavjud `POST /api/v1/courses/{id}/unenroll/`
xatti-harakati kuchaytirildi. Muammo: o'qituvchi o'quvchini kursdan
chiqarganda, agar o'quvchining brauzerida guruh chati **allaqachon ochiq**
(WebSocket ulangan) bo'lsa, u avvalgidek xabarlarni qabul qilib turaverardi —
endi bunday emas.

**O'zgargan xatti-harakat:** `unenroll` muvaffaqiyatli bo'lgach, agar
chiqarilgan o'quvchining o'sha kurs guruh chatida ochiq WS ulanishi bo'lsa,
server unga darhol yuboradi:
```json
{ "type": "removed" }
```
va ulanishni **`code=4403`** bilan yopadi.

**Frontendda nima qilish kerak:** chat WebSocket handlerida `type === "removed"`
kelganda — foydalanuvchini shu chat oynasidan chiqarib yuboring / ro'yxatdan
olib tashlang (server socketni baribir yopadi, lekin foydalanuvchiga tushunarli
signal berish uchun shu eventni alohida ushlash tavsiya etiladi). Qayta
ulanishga urinsa (`wss://<domain>/ws/chat/<room_id>/?token=...`) — endi
`can_read` `false` qaytaradi, ulanish umuman ochilmaydi (`4403`).

Bu faqat **kurs guruh chatiga** tegishli — direct (shaxsiy) chatlarga ta'sir qilmaydi.

---

#### Xulosa jadvali

| Endpoint | Kim chaqiradi | Natija |
|---|---|---|
| `POST /live/invite/` | Kurs o'qituvchisi | O'quvchi(lar)ga real-time + inbox bildirishnoma |
| `POST /live/ban/` | Kurs o'qituvchisi | Xonadan chiqaradi + shu darsga qayta kirishni bloklaydi |
| `POST /live/unban/` | Kurs o'qituvchisi | Ban bekor, qayta kirish mumkin |
| `POST /courses/{id}/unenroll/` (mavjud, kuchaytirildi) | O'qituvchi/o'quvchi/ota-ona | Kursdan chiqaradi + ochiq chat socketini `removed` bilan yopadi |


[↑ Mundarija](#mundarija)

---

## MIC_REQUEST_GRANT

> Avvalgi fayl: `MIC_REQUEST_GRANT.md`

### Mikrofon so'rov/ruxsat — yangi funksiya

#### Nima o'zgardi

Ilgari o'quvchi darsga kirganda **kamera va mikrofon ikkalasi ham avtomatik
yoqiq** edi. Endi: **kamera yoqiq qoladi, mikrofon esa o'chiq holda kiradi** —
o'quvchi gapirish uchun avval so'rashi, o'qituvchi ruxsat berishi kerak
(Zoom/Google Meet uslubidagi "qo'l ko'tarish").

#### Endpointlar

| Method | Path | Kim | Body | Javob |
|---|---|---|---|---|
| POST | `/api/v1/live/request-mic/` | student | `{"lesson_id": "uuid"}` | `{"ok": true}` |
| POST | `/api/v1/live/grant-mic/` | teacher (shu darsning o'qituvchisi) | `{"lesson_id": "uuid", "student_id": "uuid"}` | `{"ok": true}` |
| POST | `/api/v1/live/deny-mic/` | teacher (shu darsning o'qituvchisi) | `{"lesson_id": "uuid", "student_id": "uuid"}` | `{"denied": bool}` |

**Navbat qoidalari**:
- **FIFO** — `pending_mic_requests` har doim so'ralgan tartibda qaytadi (eng birinchi so'ragan birinchi).
- Bitta o'quvchi bir vaqtda **faqat bitta** faol so'rovga ega bo'ladi — qayta-qayta bossa ham navbatga dublikat qo'shilmaydi.
- So'rov faqat ikki holatda navbatdan chiqadi: **ruxsat berilsa** (`grant-mic`, mikrofon yoqiladi) yoki **rad etilsa** (`deny-mic`, mikrofon berilmaydi, LiveKit'ga umuman murojaat qilinmaydi). Ikkalasidan birontasi bo'lgach, o'quvchi yana yangi so'rov yubora oladi.

#### Qanday ishlaydi

1. O'quvchi "Mikrofon so'rash" tugmasini bosadi → `POST /live/request-mic/`.
2. O'qituvchi ekraniga **darhol** (real-time) signal keladi — yangi WebSocket
   ulanish ochish shart emas, dars davomida allaqachon ochiq bo'lgan **doska**
   kanali orqali keladi:
   ```
   wss://<domain>/ws/board/<lesson_id>/?token=<JWT>
   ```
   ```json
   { "type": "mic_request", "student_id": "uuid", "name": "Alisher" }
   ```
   (Frontend faqat `is_teacher=true` bo'lganda shu eventni ko'rsatishi kerak.)

   **Muhim (tuzatildi)**: so'rov bazada ham saqlanadi, faqat WS xabari emas —
   shuning uchun o'qituvchi so'rovdan **keyin** kirsa yoki sahifani yangilasa
   ham, joriy kutayotgan so'rovlar yo'qolib qolmaydi. `GET /api/v1/board/{lesson_id}/`
   javobiga (o'qituvchi uchun, `away_students` bilan bir qatorda) yangi maydon
   qo'shildi:
   ```json
   "pending_mic_requests": [{"student_id": "uuid", "name": "Alisher"}]
   ```
   Frontend doska sahifasini ochganda/yangilaganda shu maydondan boshlang'ich
   ro'yxatni oling, keyin WS `mic_request`/`mic_granted`/`mic_denied` orqali
   jonli yangilang. Ro'yxat FIFO tartibida keladi — birinchi so'ragan birinchi.
3. O'qituvchi ikki xil javob bera oladi:
   - **Ruxsat berish** → `POST /live/grant-mic/` → hammaga `{"type": "mic_granted", "student_id": "uuid"}`.
   - **Rad etish** → `POST /live/deny-mic/` → hammaga `{"type": "mic_denied", "student_id": "uuid"}` (mikrofon berilmaydi, so'rov shunchaki navbatdan olib tashlanadi — o'quvchi xohlasa yana so'ray oladi).
4. Ikkala holatda ham:
   - Agar `student_id` **o'zingizniki** bo'lsa (o'quvchining o'zi) → `mic_granted`da mikrofon tugmasini yoqing, `mic_denied`da "so'rash" tugmasini qayta faollashtiring.
   - Agar siz **o'qituvchi** bo'lsangiz → shu o'quvchini "kutayotganlar"
     ro'yxatidan olib tashlang (server tomonida ham bazadagi so'rov yozuvi
     avtomatik o'chiriladi — keyingi `GET /board/` chaqiruvida ham qaytmaydi).

#### Xato holatlari

- `grant-mic`/`deny-mic`ni darsning egasi bo'lmagan o'qituvchi chaqirsa → `403`
- `deny-mic`ni hech qanday faol so'rov yo'q o'quvchi uchun chaqirsa → `200 {"denied": false}` (xato emas, shunchaki hech narsa o'zgarmadi)
- `student_id` topilmasa → `404`
- `request-mic`ni kursga yozilmagan foydalanuvchi chaqirsa → `403`

#### Muhim eslatma

Bu — **butun platformadagi barcha darslar uchun standart xatti-harakatni
o'zgartiradi**: bu deploy qilingandan keyin barcha o'quvchilar darsga
mikrofonsiz kira boshlaydi. Agar frontendda "so'rash" tugmasi hali qo'shilmagan
bo'lsa, o'quvchilar mikrofon ishlamayotganini ko'radi — shuning uchun bu ikki
endpoint frontend jamoasiga **tezroq** yetkazilishi kerak.


[↑ Mundarija](#mundarija)

---

## ADMIN_TEACHERS_LIST_API

> Avvalgi fayl: `ADMIN_TEACHERS_LIST_API.md`

### Admin panel — o'qituvchilar ro'yxati (reyting bilan)

Admin panelga (`admin-dashboard-page.tsx`) yangi bo'lim qo'shish kerak:
**"O'qituvchilar"** — har biri ism + o'rtacha reyting + baholar soni bilan.

#### Endpoint

```
GET /api/v1/auth/teachers/
Authorization: Bearer <admin access token>
```

Faqat `admin` yoki `super_admin` roli kira oladi.

#### Javob

```json
[
  {
    "id": "uuid",
    "username": "ustoz1",
    "first_name": "Aziz",
    "last_name": "Karimov",
    "avatar": "https://.../media/avatars/....png",
    "avg_rating": 4.75,
    "rating_count": 12,
    "is_approved": true,
    "certificates": [
      { "id": "uuid", "file": "https://.../....pdf", "title": "IELTS 8.0", "created_at": "..." }
    ]
  }
]
```

- `avg_rating` — o'qituvchining barcha darslari bo'yicha o'rtacha ball (1-5). Hech kim baholamagan bo'lsa `null`.
- `rating_count` — jami baholar soni.
- `is_approved` — `false` bo'lsa, bu o'qituvchi hali admin tasdig'ini kutmoqda (pastga qarang).
- `certificates` — o'qituvchi yuklagan malaka sertifikatlari (bo'lsa).

#### Bonus: tasdiq kutayotgan o'qituvchilar

Agar admin panelida "yangi ro'yxatdan o'tgan o'qituvchilar" bo'limi ham kerak bo'lsa:

```
GET /api/v1/auth/teachers/pending/     # is_approved=false bo'lganlar
POST /api/v1/auth/teachers/{id}/approve/   # tasdiqlash
```


[↑ Mundarija](#mundarija)

---

## BACKEND_OQITUVCHI_PROGRESS

> Avvalgi fayl: `BACKEND_OQITUVCHI_PROGRESS.md`

### O'qituvchi uchun o'quvchilar progressi (2026-11-03)

O'qituvchi bitta guruh (kurs) ichida har o'quvchi uchun ko'radi: **to'lov**, **davomat**, **uy vazifalari**, **qachon qo'shilgani**.
Hammasi faqat shu kursning o'qituvchisi uchun (boshqa o'qituvchi/o'quvchi/ota-ona → 403/404).

> **Muhim:** platformada to'lov tizimi (Click/Payme) yo'q. Shuning uchun to'lovni **o'qituvchi o'zi belgilaydi**
> ("shu oy uchun to'ladi"). Belgi bor = to'lagan, yo'q = to'lamagan. Kurs narxi (`monthly_fee`) avvalgidek kurs sozlamasida.

#### 1. Guruh bo'yicha ro'yxat

`GET /api/v1/courses/{course_id}/progress/?range=all|30d|month&month=YYYY-MM`

- `range` — davomat davri (standart `all`; `attendance/summary/` bilan bir xil).
- `month` — qaysi oyning to'lovi ko'rsatiladi (standart — joriy oy).

```json
{
  "course_id": "…", "course_title": "Algebra", "monthly_fee": 450000,
  "range": "all", "month": "2026-11", "lesson_count": 12,
  "summary": {
    "students": 18, "paid": 11, "unpaid": 7,
    "attendance_percent": 84, "focus_percent": 91, "homework_completion_percent": 76
  },
  "students": [
    {
      "id": "…", "name": "Aziza Rahimova", "username": "aziza",
      "joined_at": "2026-08-01T09:12:00Z",
      "last_visit_at": "2026-11-02T14:00:00Z",
      "attendance": { "percent": 92, "attended": 11, "total": 12, "focus_percent": 95 },
      "homework": {
        "total": 9, "submitted": 8, "checked": 6, "awaiting_review": 2, "resubmit_requested": 0,
        "missed": 1, "completion_percent": 89, "average": 8.4, "scale": 10
      },
      "payment": {
        "period": "2026-11", "status": "paid", "amount": 450000, "paid_at": "2026-11-01T10:00:00Z", "note": "Naqd",
        "unpaid_months": 0
      }
    }
  ]
}
```

Ta'riflar:
- `percent` (davomat) / `focus_percent` — kursning "Davomat" sahifasidagi (`attendance/summary/`) raqamlar bilan **aynan bir xil**. Qatnashmagan bo'lsa `focus_percent: null`.
- `joined_at` — o'quvchi guruhga qo'shilgan (tasdiqlangan) vaqt. `last_visit_at` — oxirgi marta darsga kirgan vaqt (`null` = hech kirmagan).
- `homework` — faqat **faol** vazifalar (qoralama kirmaydi), o'quvchi qo'shilgandan keyingilari (+ u topshirgan eskilari).
  - `submitted` — topshirgan (AI tekshirayotgan va o'qituvchi tasdiqlashini kutayotgani ham kiradi).
  - `checked` — o'qituvchi tasdiqlagan; `awaiting_review` — tekshiruv/tasdiq kutilmoqda.
  - `resubmit_requested` — "qayta topshiring" deyilgan (topshirilgan hisoblanmaydi).
  - `missed` — muddati o'tgan va topshirilmagan.
  - `average` — tasdiqlanganlarning o'rtacha bahosi, **10 ballik** (`null` = hali baho yo'q). `completion_percent` — `submitted / total` (`null` = vazifa yo'q).
- `payment.status` — `paid` | `unpaid` (tanlangan `month` uchun). `unpaid_months` — o'quvchi qo'shilgan oydan joriy oygacha to'lov belgisi **yo'q** oylar soni ("3 oy qarzdor").
  `amount` — belgilangan summa (berilmagan bo'lsa kurs narxi); `unpaid` bo'lsa `amount/paid_at: null`, `note: ""`.
  Kurs narxi (`monthly_fee`) `null` bo'lsa — to'lov bo'limini yashirish mumkin.

Tartib: ism bo'yicha (A→Z). Filtr/qidiruvni frontend qiladi (bitta guruhda ~50 tagacha o'quvchi).

#### 2. Bitta o'quvchi (batafsil)

`GET /api/v1/courses/{course_id}/students/{student_id}/progress/?range=all|30d|month`

Javob — yuqoridagi qatorning hammasi (`name`, `joined_at`, `attendance`, `homework`, `payment`, …) **va** qo'shimcha ro'yxatlar:

```json
{
  "lessons": [
    { "lesson_id": "…", "title": "Tenglamalar", "starts_at": "…", "attended": true,
      "joined_at": "…", "left_at": "…", "minutes": 52, "late_reason": "", "teacher_note": "" }
  ],
  "assignments": [
    { "assignment_id": "…", "title": "Essay", "due_at": "…", "state": "done",
      "submitted_at": "…", "submission_id": "…", "score": 8.5 }
  ],
  "payments": [
    { "period": "2026-11", "status": "paid", "amount": 450000, "paid_at": "…", "note": "Naqd" },
    { "period": "2026-10", "status": "unpaid", "amount": null, "paid_at": null, "note": "" }
  ]
}
```

- `lessons` — tugagan darslar, yangisi birinchi. `attended: false` = qatnashmagan.
- `assignments[].state`: `done` (tasdiqlangan, `score` 10 ballik) · `awaiting_review` · `resubmit` · `missed` (muddati o'tgan, topshirilmagan) · `not_submitted` (muddati hali o'tmagan).
  `submission_id` orqali mavjud `/homework/submissions/{id}/` ochiladi.
- `payments` — o'quvchi qo'shilgan oydan joriy oygacha, **eng yangi oy birinchi**.

#### 3. To'lovni belgilash

`PUT /api/v1/courses/{course_id}/students/{student_id}/payments/{YYYY-MM}/`  `{ "amount": 450000, "note": "Naqd" }`
- ikkala maydon ixtiyoriy; `amount` berilmasa kurs narxi ko'rsatiladi. Qayta chaqirish yozuvni yangilaydi (xato emas).
- Javob: `{ "period", "status": "paid", "amount", "paid_at", "note" }`.

`DELETE /api/v1/courses/{course_id}/students/{student_id}/payments/{YYYY-MM}/` — belgini olib tashlaydi (`204`; belgi bo'lmasa ham `204`).

Xatolar (standart format): noto'g'ri oy (`2026-13`, 2020 dan oldin yoki 12 oydan keyin) → 400; summa son emas yoki manfiy → 400;
o'quvchi shu kursda tasdiqlanmagan → 404; kurs o'qituvchisi emas → 403/404.

#### 4. Frontend topgan xatolar — tuzatildi

| Xato | Endi |
|---|---|
| `analytics/child/<id>/rank/?course=abc`, `remind-child {student: "abc"}`, `auth/logins/?student=abc` — UUID bo'lmasa 500 | **400** (`error.details.course` / `student`), standart format |
| `auth/logins/` sahifalashda `next`/`previous` `from`, `to`, `device` filtrlarini yo'qotardi | Barcha filtrlar saqlanadi |
| `remind-child` da `student` yo'q bo'lsa 400 standart formatda emas edi | `{"success": false, "error": {"code": "invalid", "message": "...", "details": {"student": [...]}}}` |

#### Migratsiya

Yangi jadval: `lessons_coursepayment` (migratsiya `0029_course_payment`). Deploy'da APP serverdagi `web` avtomatik migratsiya qiladi.


[↑ Mundarija](#mundarija)

---

## BACKEND_HOMEWORK_UPDATES

> Avvalgi fayl: `BACKEND_HOMEWORK_UPDATES.md`

### Uy vazifasi (homework) — o'zgarishlar (frontend / mobil uchun)

**Qisqasi:** AI tekshiruv bizning backend ichidan olib tashlandi. Hozir u **alohida tashqi xizmat** (AI-home-checker) sifatida ulanadi va **ixtiyoriy**: xizmat yoqilgan bo'lsa AI ballni taklif qiladi, o'chiq yoki ishlamasa o'qituvchi o'zi baholaydi. Har holda **yakuniy ballni o'qituvchi tasdiqlaydi.**

#### 1. Oqim

1. O'quvchi fayl yuklaydi: `POST /homework/assignments/{id}/submit/`. Javob **darhol** `status: "pending_review"` (o'quvchi hech qachon "AI ishlayapti" holatini ko'rmaydi).
2. **AI xizmati yoqilgan bo'lsa:** o'qituvchi ko'rinishida topshiriq 10-60 soniya `status: "checking"` bo'ladi, keyin `pending_review` ga o'tadi va `overall_score`/`grade`/`result` **AI taklifi bilan oldindan to'ldirilgan** bo'ladi (`ai_result`, `ai_overall_score`, `ai_grade` ham to'ldiriladi). O'qituvchiga bildirishnoma shu paytda boradi.
3. **AI xizmati o'chiq/xato/uzoq kutilgan bo'lsa:** topshiriq darhol (yoki 15 daqiqadan keyin) `pending_review` bo'ladi, ball bo'sh, `error` maydonida sabab ("o'zingiz baholang") bo'lishi mumkin; o'qituvchi ballni o'zi kiritadi.
4. O'qituvchi tasdiqlaydi (`POST .../review/`) → `status: "done"`, natija o'quvchi/ota-onaga ochiladi.

O'qituvchi sahifasida `checking` holati qaytdi (spinner / "AI tekshirmoqda"); `checking` da tasdiqlab bo'lmaydi (`400`).

#### 2. Baholash — `POST /homework/submissions/{id}/review/`

```json
{ "overall_score": 85, "grade": "Juda yaxshi", "result": { "...": "..." } }
```
- **`overall_score` — majburiy**, 0 dan 100 gacha son (aks holda `400`, `details.overall_score`). Oldin AI ballni o'zi qo'yar edi, endi o'qituvchi kiritadi — baholash oynasida ball maydoni **bo'sh va majburiy** bo'lsin.
- `grade` — ixtiyoriy matn. Berilmasa ballga qarab avtomatik qo'yiladi (90+ A'lo, 80+ Juda yaxshi, 70+ Yaxshi, 60+ Qoniqarli, 50+ Yaxshilash kerak, undan past Jiddiy yaxshilash kerak). Maydonni oldindan to'ldirib ko'rsatishingiz mumkin.
- `result` — ixtiyoriy obyekt (o'qituvchi izohi: masalan `{"summary": {"strengths": [...], "recommendations": [...]}}`); oldingi AI natijasi bilan bir xil shaklni ishlatsangiz eski ko'rinishlar ishlayveradi.
- **Tasdiqlangan natijani ham tuzatish mumkin:** o'qituvchi `done` topshiriqda yana `review` yuborib ballni o'zgartiradi; o'quvchiga "natija yangilandi" bildirishnomasi boradi. "Tahrirlash" imkoniyati bo'lsin.
- Tasdiqlashgacha o'quvchi/ota-onaga `overall_score`, `grade`, `result` ko'rinmaydi (`null`).

#### 3. Olib tashlanishi kerak bo'lgan UI

- **O'quvchi tomonda** "tekshirilmoqda"/AI haqida hech narsa ko'rsatmang (o'quvchi doim `pending_review` ni ko'radi).
- **"AI taklifi" bloki** (`ai_result`, `ai_overall_score`, `ai_grade`) — o'qituvchida AI yoqilgan bo'lsa to'ladi, aks holda `null`: `null` bo'lsa blokni yashiring.
- **"Qayta tekshirish"** tugmasi (`POST .../recheck/`) faqat AI yoqilgan bo'lsa ishlaydi (topshiriq `checking` ga qaytadi); o'chiq bo'lsa `400` va xabar: *"AI tekshiruv o'chirilgan. Topshiriqni o'zingiz baholang..."* — xabarni ko'rsating.
- Vazifa yaratish formasidagi **"AI uchun qo'shimcha ko'rsatma"** (`extra_instructions`) maydoni endi hech narsaga ta'sir qilmaydi — yashirishingiz mumkin (API uni baribir qabul qiladi).

#### 4. Bildirishnomalar

| `kind` | Kimga | Qachon | `link_type` / `link_id` |
|---|---|---|---|
| `homework_pending_review` | o'qituvchi | topshiriq baholashga **tayyor bo'lgan zahoti**: AI o'chiq bo'lsa topshirilgan paytda, yoqilgan bo'lsa AI natijasi kelganda ("... vazifani topshirdi — «...». Baholashingiz kerak.") | `submission` / `<submission id>` |
| `homework_reviewed` | o'quvchi | o'qituvchi baholaganda yoki tuzatganda ("natijasi tayyor" / "yangilandi") | `submission` / `<submission id>` |

Bildirishnomani bosganda `link_type: "submission"` bo'yicha topshiriq sahifasiga o'ting (`GET /homework/submissions/{id}/`). Mobil push ham shu bildirishnomalardan ketadi.

#### 5. Topshirish cheklovi

`POST .../submit/`: bir vazifaga **soatiga 5 tadan**, jami **soatiga 20 tadan** ko'p topshirib bo'lmaydi — `400`, xato `error.details.file` ostida. Xabarni fayl maydoni tagida ko'rsating.

#### 6. Fayllar

- Topshiriq fayllari va o'qituvchi biriktirmalari **faqat API orqali** olinadi: `GET /homework/submissions/{id}/file/`, `GET /homework/assignments/{id}/file/` (login kerak, asl fayl nomi bilan). `https://.../media/homework/...` to'g'ridan-to'g'ri manzillari **ishlamaydi** (404).
- Sertifikat fayllarining ochiq manzili o'zgarmadi; yangi yuklanganlarning fayl nomi tasodifiy (ro'yxatda `title` ko'rsating).

#### 7. O'zgarmagan narsalar

Vazifa berish/tahrirlash/o'chirish, muddat va "kech topshirilgan" belgisi, o'quvchi sahifa kuzatuvi (`focus`), o'qituvchi statistikasi (o'rtacha ball endi faqat baholangan topshiriqlar bo'yicha), ota-ona hisoboti (`/homework/report/?student_id=...`) — hammasi avvalgidek.

#### 8. Speaking (ovozli) vazifa — AI endi ovozni ham tekshiradi (2026-11-07)

Ko'nikmasi `speaking` bo'lgan vazifaga o'quvchi `.mp3 .wav .m4a .ogg` (25 MB gacha) yuklaydi. Oqim avvalgidek: `checking` -> `pending_review` (o'qituvchi tasdiqlaydi).
Ichkarida: OpenAI avval ovozni **matnga aylantiradi** (transkripsiya), keyin shu matn va ravonlik statistikasi (tezlik, pauzalar) baholanadi.

Javob (`result`) avvalgi formatda, qo'shimcha maydonlar bilan — **frontend o'zgarishi shart emas**, lekin xohlasangiz ko'rsatishingiz mumkin:
- `questions[]` — har bir **mezon** uchun bitta qator: ingliz tilida *Fluency and Coherence*, *Lexical Resource*, *Grammatical Range and Accuracy* (boshqa tillarda Fluency, Vocabulary, Grammar). `score` — foiz.
- `transcript` — o'quvchi aytgan gapning matni (o'qituvchi eshitmasdan ham ko'rib chiqishi uchun).
- `delivery` — `{words, duration_seconds, words_per_minute, pauses, longest_pause_seconds}`.
- `source: "audio-transcript"`.
- `summary.recommendations[0]` — **doim** talaffuz haqidagi ogohlantirish: "Talaffuz va ohang AI tomonidan baholanmadi — o'qituvchi yozuvni eshitib baholasin".

**Muhim cheklov:** AI talaffuz va ohangni baholay olmaydi (ovoz matnga aylangach ular yo'qoladi). Shuning uchun bu faqat **taklif**; yakuniy bahoni o'qituvchi eshitib qo'yadi.
Jim yoki juda qisqa (5 so'zdan kam) yozuv va buzuq fayl AI'ga yuborilmaydi — topshiriq izoh bilan darhol o'qituvchiga tushadi (`error` maydonida sabab).


[↑ Mundarija](#mundarija)

---

## HOMEWORK_NOTIFICATIONS_API

> Avvalgi fayl: `HOMEWORK_NOTIFICATIONS_API.md`

### Uy vazifasi bildirishnomalari — frontend uchun

Bu — **yangi endpoint emas**. Yangi vazifa berilganda va deadline
yaqinlashganda (yarim vaqt / 1 soat qoldi) yuboriladigan bildirishnomalar
**mavjud** `notifications` infratuzilmasi orqali keladi — shu hujjat o'sha
mavjud endpointlarni va yangi xabar matnlarini tasvirlaydi.

**Base URL**: `/api/v1/notifications/`
**Auth**: JWT (`Authorization: Bearer <access_token>`)

#### Endpointlar (mavjud, hozirgacha alohida hujjatlanmagan)

| Method | Path | Tavsif |
|---|---|---|
| GET | `/notifications/` | Mening inbox'im — sahifalangan, eng yangisi tepada |
| GET | `/notifications/unread-count/` | `{"count": N}` — o'qilmagan xabarlar soni (badge uchun) |
| POST | `/notifications/{id}/read/` | O'qildi deb belgilash |

**WebSocket (real-time push)**: `wss://<domain>/ws/notifications/?token=<JWT access>`
```json
{ "type": "notification", "notification": { "id", "sender", "description", "target_type": "user", "created_at" } }
```
Yopilish kodi: `4401` — token yaroqsiz.

#### Inbox javob shakli (`GET /notifications/`)

```json
{
  "results": [
    {
      "id": "uuid",
      "notification": {
        "id": "uuid",
        "sender": { "id", "username", "first_name", ... },
        "description": "«Algebra — 7-sinf»: yangi uy vazifasi — «Kvadrat tenglamalar».",
        "target_type": "user",
        "created_at": "2026-08-24T10:00:00Z"
      },
      "is_read": false,
      "read_at": null,
      "created_at": "2026-08-24T10:00:00Z"
    }
  ]
}
```

#### Yangi qo'shilgan uy-vazifa xabarlari — matn andozalari

Bular **maxsus "type" maydoniga ega emas** — oddiy `Notification` sifatida
keladi (`sender` = kursning o'qituvchisi), faqat `description` matni orqali
farqlanadi. Agar UI'da alohida ikonka/rang ko'rsatmoqchi bo'lsangiz, matnni
shu qoliplar bilan solishtiring:

| Voqea | Kimga | `description` qolipi |
|---|---|---|
| O'qituvchi yangi vazifa berdi | Kursga yozilgan **hamma** o'quvchi, darhol | `«<kurs nomi>»: yangi uy vazifasi — «<vazifa nomi>».` |
| Deadline'ning **yarmi** o'tdi | Hali **topshirmagan** o'quvchilar | `«<kurs nomi>»: «<vazifa nomi>» topshirish muddatining yarmi o'tdi.` |
| Deadline'ga **1 soat** qoldi | Hali **topshirmagan** o'quvchilar | `«<kurs nomi>»: «<vazifa nomi>» topshirish muddatiga 1 soat qoldi!` |

#### Muhim xatti-harakatlar

- Deadline eslatmalari **faqat hali `Submission` topshirmagan** o'quvchilarga boradi — allaqachon topshirgan o'quvchi bu ikkala eslatmani olmaydi.
- Har ikkala eslatma (yarim vaqt, 1 soat) **faqat bir marta** yuboriladi — takror kelmaydi.
- Agar `due_at` belgilanmagan bo'lsa (vazifada muddat yo'q) — deadline eslatmalari umuman yuborilmaydi, faqat "yangi vazifa" xabari keladi.
- Eslatmalar server tomonda **davriy tekshiruv** orqali yuboriladi (real vaqtli emas — cron orqali har 5-15 daqiqada tekshiriladi), shuning uchun deadline vaqtidan bir necha daqiqa kechikish normal.


[↑ Mundarija](#mundarija)

---

## BACKEND_AI_QUIZ

> Avvalgi fayl: `BACKEND_AI_QUIZ.md`

### AI bilan test yaratish — imtihon qoidalari bo'yicha (frontend / mobil uchun)

**Qisqasi:** o'qituvchi **material** (PDF/Word/PowerPoint/Excel/matn) yuklaydi va ixtiyoriy ravishda **imtihon qoidalari**ni
(fayl yoki matn; masalan "IELTS Reading: 3 ta matn, 40 savol, True/False/Not Given, ...") qo'shadi. AI qoidalarni o'qib
testni **shu tuzilma bo'yicha** to'liq tuzadi: bo'limlar, matn parchalari (guruhlar), turli turdagi savollar, ularning
tartibi va talabaga ko'rsatiladigan ko'rsatmalar. **Qoidalar berilmasa** — oddiy variantli (A-B-C-D) test. **Material ham ixtiyoriy:** bo'sh bo'lsa AI mavzu va qoidalar bo'yicha matnni o'zi yozadi.
Natija **qoralama test** (o'quvchiga ko'rinmaydi). Imtihon formati kodda yozilmagan: har qanday imtihon uchun bir xil ishlaydi.

Ish **fonda** bajariladi (1–5 daqiqa): so'rov darhol `202` qaytaradi, keyin holatni so'rab turasiz.

#### 1. Boshlash — `POST /api/v1/quizzes/ai-generate/` (multipart)

| maydon | | |
|---|---|---|
| `file` | ixtiyoriy, **bir nechta** | material fayllari (bir xil `file` nomi bilan 5 tagacha): `.pdf .docx .pptx .xlsx .xlsm .csv .txt .md`, har biri ≤ 20 MB, jami ≤ 40 MB. Fayl darhol o'qiladi: skanerlangan (rasm) PDF yoki buzuq fayl bo'lsa `400` + sabab |
| `material_text` | ixtiyoriy | material matni (≤ 120 000 belgi), fayllarga qo'shimcha yoki ularning o'rniga |
| `exam_name` | ixtiyoriy | imtihon nomi (`IELTS Academic Reading`, `SAT Math`, ...): qoidalar berilmasa AI uning rasmiy tuzilmasini o'zi eslaydi. Qoidalar berilsa — qoidalar ustun |
| `rules_file` | ixtiyoriy | imtihon qoidalari hujjati (shu formatlar), ≤ 5 MB |
| `rules_text` | ixtiyoriy | qoidalar matni (≤ 30 000 belgi). `rules_file` bilan birga ham berish mumkin |
| `topic` | majburiy | mavzu |
| `title` | ixtiyoriy | test nomi (bo'sh bo'lsa AI imtihon nomini qo'yadi) |
| `question_count` | ixtiyoriy | 5–60, standart 20. Oddiy rejimda — savollar soni; qoidalarda son belgilangan bo'lsa, qoidalar ustun |
| `course` yoki `subject` | biri shart | guruh id yoki fan kodi (`math`, `english`, ...) |
| `standard` | ixtiyoriy | `uzbmb\|ielts\|sat` — **Test banki** rejimi (Test-creator, 2026-10 versiyasi): standart bo'yicha reja va savollar banki, faqat A-B-C-D; aynan bitta `file` kerak; `exam_name`, qoidalar va `material_text` e'tiborga olinmaydi. AI sahifasida "Qo'shimcha → Test banki" |
| `language` | ixtiyoriy | test tili: `uz` (o'zbekcha, lotin) \| `uz_cyrl` (кирилл) \| `ru` \| `en`. **Berilmasa:** Test banki rejimida standartga qarab (`uzbmb` → `uz`, `ielts`/`sat` → `en`), oddiy AI generatorda — material tili, **material bo'lmasa o'zbekcha (lotin)** (avval inglizcha chiqib qolar edi). Tanlansa material boshqa tilda bo'lsa ham savollar shu tilda yoziladi (raqam va formulalar o'zgarmaydi). Javobda `language` qaytadi (tanlanmagan bo'lsa `""`). Noto'g'ri qiymat — 400. **Frontend: til tanlash (select) qo'shing, standart qiymati `uz`.** |

Javob `202`: `{ id, status: "queued", mode, topic, ... }`. `mode`: `rules` (qoidalar yoki imtihon nomi bo'yicha) · `simple` (oddiy variantli) ·
`test_creator` (Test banki).

Xatolar (`400`, `error.details.*`): fayl turi/hajmi (`file`, `rules_file`), qoidalar matni uzunligi (`rules_text`), bo'sh mavzu, savollar soni,
guruh/fan yo'q. Cheklov: o'qituvchiga bir vaqtda **3 ta** faol ish, **kuniga 10 ta** (`error.details.detail`). AI sozlanmagan bo'lsa
`400` ("AI bilan test yaratish hozir o'chirilgan") — UI xabarni ko'rsatsin.

#### 2. Holat — `GET /api/v1/quizzes/ai-generate/{id}/` va ro'yxat `GET /api/v1/quizzes/ai-generate/`

`status`: `queued` (navbatda) → `generating` (reja tuzilmoqda / bo'limlar yozilmoqda) → `done` | `failed`.
Test banki rejimida (`mode: test_creator`) oraliq `processing` ham bor: material tahlili, keyin test fonda yig'iladi (`generating`), cron har 30 s holatini so'raydi; xizmat testni so'ralganidan kam savol bilan tugatsa ham (`partial`) qabul qilinadi va `summary`da aytiladi.

| maydon | ma'nosi |
|---|---|
| `quiz` | `done` bo'lganda qoralama testning id'si (`GET /quizzes/{id}/`) |
| `summary` | masalan `"2 bo'lim · 10 savol"`; yaroqsiz savollar tushib qolgan bo'lsa shu haqda eslatma |
| `error` | `failed` bo'lganda sababi (o'qituvchiga ko'rsatiladi) |
| `rules_name` | yuklangan qoidalar fayli nomi |

Har 5 soniyada so'rab turing yoki bildirishnomani kuting: `ai_quiz_ready` (`link_type: quiz`, `link_id: <quiz id>`) / `ai_quiz_failed`.
Vaqtinchalik xatoda (AI band, tarmoq) ish o'zi qayta urinadi (3 marta, orasida 2 daqiqa); tayyor bo'limlar saqlanadi — qayta boshlanmaydi.

#### 3. Tayyor test

`quiz` — oddiy **qoralama** (`status: "draft"`). Unda:
- **Matn parchasi** bo'lgan bo'limlar uchun **savollar guruhi** (`groups[]`: sarlavha + matn), shu bo'lim savollari `group` bilan bog'langan;
- savollar qoidalardagi **tartibda**; har blokning birinchi savolida blok **ko'rsatmasi** (masalan "Choose NO MORE THAN TWO WORDS...") matn boshida;
- savol turlari: `single`, `multiple`, `true_false`, `matching`, `fill_blank` (`{{1}}`), `text` (qisqa javob), `numeric`, `ordering`.
  IELTS'dagi True/False/Not Given va Yes/No/Not Given — 3 variantli `single`.

O'qituvchi qoralamani tahrirlaydi (`PATCH /quizzes/{id}/`), e'lon qiladi (`POST /quizzes/{id}/publish/`), imtihonga ulaydi (`POST /exams/`).
AI javoblari to'g'riligi **kafolatlanmagan** — e'lon qilishdan oldin tekshirish shart.

#### 4. Frontend uchun UI

Workspace → **AI** sahifasi: material, **imtihon qoidalari** (fayl tanlash yoki matn yozish — ixtiyoriy), savollar soni; ostida "Mening AI testlarim"
ro'yxati (holat, `summary`, tayyor bo'lsa "Testni ochish"). Xatoda `error` matnini ko'rsating.

#### 5. Cheklovlar
- Listening bo'limi uchun AI skript yozadi va ovozga (mp3) aylantiradi; skript (`transcript`) faqat o'qituvchiga ko'rinadi. Speaking uchun audio yaratilmaydi.
- Sifat materialning to'liqligiga va qoidalarning aniqligiga bog'liq: qoidalar qanchalik aniq bo'lsa, tuzilma shunchalik to'g'ri chiqadi.

#### 6. Sifat tekshiruvlari (avtomatik, frontend uchun hech narsa o'zgarmaydi)
- **Hisob-kitob**: `numeric` / raqamli variantli savollarda AI javobga mos arifmetik ifoda ham yozadi; biz uni mustaqil hisoblaymiz va
  javobga zid savollarni tashlaymiz (zaxira savol o'rniga keladi). Modul: `apps/quizzes/mathcheck.py`.
- **AI tekshiruvchi (judge)**: har bo'limdan keyin alohida so'rov savollarni manbaga (matn / skript / material) solishtiradi;
  javobi manbada yo'q, noaniq yoki bir nechta to'g'ri javobli savollar tashlanadi. O'chirish: `AI_EXAM_JUDGE=0` (`.env`). Tekshiruv
  ishlamasa yoki savollarning >60% ini rad etsa — e'tiborga olinmaydi, test baribir yaratiladi.
- **Savollar banki**: yaratilgan savollar o'qituvchi + imtihon bo'yicha eslab qolinadi (`BankQuestion`); keyingi testda AI'ga
  "bular allaqachon bor" deb beriladi — takrorlanmaydi.

#### 7. Testni yuklab olish — `GET /api/v1/quizzes/{id}/export/?type=pdf|docx|xlsx|csv|json&mode=student|teacher`
Faqat test egasi (o'qituvchi). `student` — javobsiz (chop etib tarqatish), `teacher` — to'g'ri javoblar va Listening skripti bilan.
Javob — fayl (`Content-Disposition: attachment`). Bearer token bilan so'rang (`fetch` + blob), oddiy `<a href>` ishlamaydi.


[↑ Mundarija](#mundarija)

---

## BACKEND_QUIZ_GROUPS

> Avvalgi fayl: `BACKEND_QUIZ_GROUPS.md`

### Savollar guruhi — matn parchasi (Reading/SAT) va audio (Listening)

**Holat:** backend tayyor. Maqsad: IELTS Reading (bitta matn ostida 13 ta savol), IELTS Listening (bitta audio ostida 10 ta savol), SAT (matn + savol) uchun testlarda **umumiy material** berish. Imtihon (`BACKEND_EXAMS.md`) shu testlarni ishlatadi.

**Orqaga mos:** `groups` va savoldagi `group` **ixtiyoriy**. Eski testlar, Word/Google import va oddiy test yechish hech o'zgarmaydi (guruhsiz savollarda `group: null`, `groups: []`).

---

#### 1. Ma'lumot shakli

**Guruh** (`groups[]` — testning o'qish javobida ham, o'quvchi ko'rinishida ham bor):
```json
{ "id": "<uuid>", "order": 0, "title": "Passage 1", "passage": "matn parchasi ...", "audio_url": null }
```
- `passage` — oddiy matn (yangi qatorlar saqlanadi); uzunligi ≤ 30 000 belgi.
- `audio_url` — **to'liq (absolyut) manzil** (`https://edu.thesofmebel.uz/media/quiz_audio/....mp3`), yo'q bo'lsa `null`. To'g'ridan-to'g'ri `<audio src>` ga qo'yish mumkin.

**Savol** endi `group` maydoniga ega — guruh `id` si yoki `null`:
```json
{ "id": "...", "type": "single", "text": "Q1", "group": "<group uuid>", "options": [...] }
```
Guruhni ko'rsatish: savollarni `group` bo'yicha guruhlab, har guruh tepasida `title` + `passage` + audio pleyer ko'rsating. Guruhsiz savollar oddiy ko'rinadi. Javob kaliti (`is_correct`, `answer_key`) guruhda yo'q.

---

#### 2. Yaratish — `POST /api/v1/quizzes/`

Odatdagi so'rovga `groups` qo'shiladi; savol guruhga **`groups` ro'yxatidagi tartib raqami (0 dan)** bilan ishora qiladi:
```json
{
  "course": "<uuid>", "topic": "Reading mock", "title": "Passage test",
  "groups": [
    {"title": "Passage 1", "passage": "birinchi matn ..."},
    {"title": "Passage 2", "passage": "ikkinchi matn ..."}
  ],
  "questions": [
    {"type": "single", "text": "Q1", "group": 0, "options": [...]},
    {"type": "single", "text": "Q2", "group": 0, "options": [...]},
    {"type": "single", "text": "Q3", "group": 1, "options": [...]},
    {"type": "single", "text": "Q4", "options": [...]}          // guruhsiz
  ]
}
```
- `group` mavjud bo'lmagan tartib raqamiga ishora qilsa — `400` (`details.questions`).
- Javobda (`201`) har guruhning haqiqiy `id` si keladi — audio yuklash uchun kerak.

#### 3. Audio yuklash (IELTS Listening)

`POST /api/v1/quizzes/{quiz_id}/groups/{group_id}/audio/` — **multipart**, maydon `file`.
- Formatlar: `mp3, m4a, aac, ogg, wav`. Hajm ≤ **60 MB**. Xato — `400` (`details.file`).
- Mavjud audio bo'lsa — almashtiriladi (eskisi o'chadi).
- Javob: yangilangan guruh (`audio_url` bilan).
- Faqat test egasi (boshqa kimdir — `403`/`404`).

`DELETE` shu manzilga — audioni olib tashlaydi (`204`).

> **Eslatma (xavfsizlik):** audio ochiq `/media/` orqali beriladi; fayl nomi taxmin qilib bo'lmaydigan tasodifiy (uuid), lekin havolani bilgan kishi eshita oladi. Imtihon uchun amaliy, jiddiy "yopiq" himoya kerak bo'lsa — keyingi bosqich.

#### 4. Tahrirlash — `PATCH /api/v1/quizzes/{id}/`

`groups` va `questions` **to'liq almashtirish** semantikasi bilan ishlaydi, lekin audio yo'qolmasligi uchun guruhlarni `id` bilan yuboring:

| So'rov | Natija |
|---|---|
| `groups` + `questions` | Guruhlar ro'yxatga moslanadi: **`id` berilganlari saqlanadi** (audio bilan), `id`siz — yangi, ro'yxatda yo'qlari **o'chadi** (audiosi ham). Savollar yangi ro'yxat tartib raqami bilan bog'lanadi. |
| faqat `questions` (`groups` yo'q) | Mavjud guruhlar **o'z tartibida** saqlanadi, savollar ularga tartib raqami bilan ishora qiladi. |
| faqat `groups` | Matn/sarlavha yangilanadi, savollarga tegilmaydi. Olib tashlangan guruhning savollari guruhsiz qoladi. |

Cheklovlar (o'zgarmagan): testda urinishlar bo'lsa yoki imtihonga biriktirilgan bo'lsa `questions` o'zgartirib bo'lmaydi; faqat `groups` (matn tahriri) mumkin.

Boshqa testning guruh `id` si yuborilsa e'tiborsiz qoldiriladi (yangi guruh yaratiladi) — boshqa testga ta'sir qilmaydi.

#### 5. Imtihonda

`GET /api/v1/exams/{id}/current/` dagi `item` ichida endi `groups` ham bor (savollar bilan birga):
```json
"item": { "kind": "section", "key": "reading", "groups": [ {...} ], "questions": [ {..., "group": "<id>"} ] }
```
Bo'lim ichida savollarni xuddi shunday `group` bo'yicha guruhlab ko'rsating. IELTS Listening: guruhning `audio_url` si pleyerga.

> Real IELTS Listening audiosi **bir marta** eshittiriladi va to'xtatib bo'lmaydi — bu cheklovni pleyerni UI'da yashirish bilan frontendda qo'yish mumkin (backend faqat audio manzilini beradi).


[↑ Mundarija](#mundarija)

---

## BACKEND_EXAMS

> Avvalgi fayl: `BACKEND_EXAMS.md`

### Imtihon (Mock test) — IELTS / SAT / Milliy sertifikat / custom

**Holat:** backend tayyor (1-bosqich). **Base:** `/api/v1/exams/`. Barcha endpointlar JWT bilan.
Eski `/api/v1/quizzes/mock-tests/` **yo'q** — shu yangisi o'rniga. Frontenddagi `mock-test` moduli shu API'ga o'tkazilishi kerak.

#### Qisqacha g'oya

- **Shablon** = bo'limlar va tanaffuslar zanjiri + ball hisoblash qoidasi. Tayyor shablonlar: `ielts`, `sat`, `milliy`. O'qituvchi o'z **custom** shablonini ham yaratadi.
- O'qituvchi **o'z guruhida imtihon e'lon qiladi**: shablonni tanlaydi, har bo'limga o'zining e'lon qilingan **testini** biriktiradi, **boshlanish sanasi-vaqtini** belgilaydi.
- Imtihon **sinxron**: hamma uchun bir vaqtda boshlanadi va tugaydi. Bo'lim/tanaffus chegaralari serverda hisoblanadi (`boshlanish + bo'limlar davomiyligi`). Kech kirgan o'quvchi joriy bo'limning *qolgan* vaqtini oladi.
- **Qayta topshirish yo'q.** Yana imtihon kerak bo'lsa o'qituvchi yangisini yaratadi.
- Javoblar **avtosaqlanadi** (`PUT answers/`), sahifa yangilansa `current` hammasini tiklaydi.

Barcha rollarga ruxsat: o'qituvchi — yaratadi/boshqaradi; o'quvchi — topshiradi; ota-ona va admin — ko'radi.

---

#### 1. Shablonlar

##### `GET /api/v1/exams/templates/`
Tayyor + o'qituvchining custom shablonlari:
```json
[
  {"id": "ielts", "kind": "system", "name": "IELTS", "description": "...",
   "scoring": {"type": "ielts"},
   "items": [
     {"type": "section", "key": "listening", "title": "Listening", "minutes": 30, "questions": 40},
     {"type": "section", "key": "reading",   "title": "Reading",   "minutes": 60, "questions": 40},
     {"type": "section", "key": "writing",   "title": "Writing",   "minutes": 60, "manual": true},
     {"type": "offline", "key": "speaking",  "title": "Speaking",  "manual": true}
   ]},
  {"id": "sat", "kind": "system", "items": [rw_1, rw_2, {"type":"break","minutes":10}, math_1, math_2]},
  {"id": "milliy", "kind": "system", "items": [{"type":"section","key":"main","minutes":150}]},
  {"id": "<uuid>", "kind": "custom", "name": "...", "items": [...], "scoring": {...}}
]
```

**Element turlari (`type`):**
| tur | ma'nosi |
|---|---|
| `section` | vaqtli bo'lim — unga **test biriktiriladi** |
| `break` | tanaffus — taymer ishlaydi, test yo'q |
| `offline` | imtihon vaqtida o'tmaydigan qism (IELTS Speaking) — ballini o'qituvchi keyin qo'lda kiritadi; jadvalga kirmaydi |

`manual: true` — shu bo'limni o'qituvchi qo'lda baholaydi. `questions` — faqat tavsiya (UI uchun).

##### `POST /api/v1/exams/templates/` — custom shablon (o'qituvchi)
```json
{
  "name": "1-chorak yakuniy",
  "description": "ixtiyoriy",
  "items": [
    {"type": "section", "key": "algebra",  "title": "Algebra",  "minutes": 40, "weight": 2},
    {"type": "break",   "key": "rest",     "title": "Tanaffus", "minutes": 10},
    {"type": "section", "key": "geometry", "title": "Geometriya", "minutes": 30}
  ],
  "scoring": {"scale": 100, "pass_percent": 60}
}
```
- `key`: lotin kichik harf, raqam, `_` (1-50 belgi), shablon ichida takrorlanmaydi.
- `section` 1–300 daqiqa, `break` 1–60 daqiqa, jami ≤ 720.
- Tanaffus birinchi/oxirgi bo'lolmaydi; kamida bitta `section` kerak.
- `weight` (ixtiyoriy, standart 1) — bo'lim natijasining jami ballga ta'siri.
- `scoring`: `scale` (jami shkala, standart 100) va `pass_percent` (ixtiyoriy). Custom doim "foiz" hisobi.
- Xatolar `error.details.items` ostida keladi.

##### `DELETE /api/v1/exams/templates/{id}/` — o'z custom shablonini o'chirish (204). Allaqachon yaratilgan imtihonlarga ta'sir qilmaydi (imtihon shablondan nusxa oladi).

---

#### 2. Imtihon yaratish (o'qituvchi)

##### `POST /api/v1/exams/`
```json
{
  "course": "<course_uuid>",
  "template": "ielts",              // "ielts" | "sat" | "milliy" | custom shablon uuid
  "title": "IELTS mock #3",
  "starts_at": "2026-10-20T10:00:00+05:00",
  "sections": [
    {"key": "listening", "quiz": "<quiz_uuid>"},
    {"key": "reading",   "quiz": "<quiz_uuid>"},
    {"key": "writing",   "quiz": "<quiz_uuid>"}
  ]
}
```
- `sections` — shablondagi **har `section`** uchun bitta yozuv (`break` va `offline` uchun emas).
- Ixtiyoriy `"minutes"` — shu imtihon uchun bo'lim vaqtini o'zgartirish (Milliy sertifikat: matematika 150, boshqa fanda boshqa).
- Test **e'lon qilingan** (qoralama emas), savoli bor, o'qituvchining o'ziniki bo'lishi va **bir imtihonda faqat bir bo'limga** biriktirilishi kerak.
- `starts_at` kelajakda bo'lishi shart. Kurs shu o'qituvchiniki bo'lishi kerak (aks holda 403).
- Yozilgan o'quvchilarga bildirishnoma boradi (`kind: "exam_scheduled"`, `link_type: "exam"`, `link_id: <exam id>`).
- Javob `201` — imtihon tafsiloti (3-bo'limdagi `GET {id}/` bilan bir xil).

##### `PATCH /api/v1/exams/{id}/` — `{"title"?, "starts_at"?}`; `DELETE /api/v1/exams/{id}/` (204)
**Faqat boshlanishdan oldin.** Boshlangan imtihonni o'zgartirish/o'chirish `400`.

> Imtihonga biriktirilgan testning **savollarini o'zgartirish yoki testni o'chirish taqiqlanadi** (`400`); nom/mavzu o'zgartirsa bo'ladi. Testlar sahifasida shu holatni ko'rsating.

---

#### 3. Ro'yxat va tafsilot

##### `GET /api/v1/exams/` (`?course=<uuid>`) — rolga qarab: o'qituvchi o'zining, o'quvchi yozilgan kurslarniki, ota-ona bolalarinikini, admin hammasini.
```json
[{"id": "...", "course": "...", "course_title": "...", "title": "IELTS mock #3",
  "template_key": "ielts", "engine": "ielts",
  "starts_at": "...", "ends_at": "...", "total_minutes": 150,
  "state": "upcoming", "server_now": "..."}]
```
`state`: `upcoming` | `running` | `finished`.

##### `GET /api/v1/exams/{id}/` — bo'limlar jadvali bilan
```json
{ ...yuqoridagi maydonlar...,
  "sections": [
    {"order": 0, "kind": "section", "key": "listening", "group": "", "title": "Listening",
     "minutes": 30, "manual": false,
     "starts_at": "2026-10-20T05:00:00Z", "ends_at": "2026-10-20T05:30:00Z",
     "quiz": "<uuid>"},
    {"order": 3, "kind": "offline", "key": "speaking", "...": "...", "starts_at": null, "ends_at": null}
  ]}
```
`quiz` maydoni faqat o'qituvchi/adminga ko'rinadi.

---

#### 4. O'quvchi: imtihonni topshirish

##### `GET /api/v1/exams/{id}/current/` — joriy holat (polling + tiklash)
```json
{
  "server_now": "2026-10-20T05:12:03Z",
  "state": "running",              // upcoming | running | finished | submitted
  "starts_at": "...", "ends_at": "...",
  "item": {
    "kind": "section", "key": "reading", "title": "Reading", "group": "", "minutes": 60,
    "starts_at": "...", "ends_at": "2026-10-20T06:30:00Z",
    "groups": [ /* umumiy matn parchasi / audio — BACKEND_QUIZ_GROUPS.md */ ],
    "questions": [ /* quizzes `GET {id}/` dagi o'quvchi ko'rinishi bilan bir xil — is_correct YO'Q, `group` bor */ ],
    "saved": [ {"question": "<id>", "answer": { "selected_option": "<id>" }} ]
  },
  "next": {"kind": "break", "title": "Tanaffus", "starts_at": "...", "ends_at": "..."}
}
```
- `upcoming` / `finished` / `submitted` da `item: null`.
- `item.kind == "break"` da `questions` yo'q — faqat taymer ko'rsating.
- **Taymer:** qolgan vaqt = `item.ends_at − server_now`. Brauzer soatiga ishonmang: `server_now` bilan brauzer vaqti orasidagi farqni (offset) bir marta hisoblab, taymerga qo'llang.
- Bo'lim yoki tanaffus tugaganda keyingisiga o'tish uchun `current` ni qayta chaqiring (yoki `ends_at` da avtomatik). Server vaqtidan tashqari hech narsa hal qilmaydi.
- `saved[].answer` — sahifa yangilanganda tanlangan javoblarni tiklash uchun.
- Savol turlari, `matching`/`ordering` aralashtirilishi — oddiy testdagi bilan bir xil.

##### `PUT /api/v1/exams/{id}/answers/` — avtosaqlash
Tanlov o'zgargan sayin (yoki har ~10 soniyada) yuboring. Qayta yuborilsa ustiga yozadi. Format oddiy testdagi `answers` bilan bir xil:
```json
{"answers": [
  {"question": "<id>", "selected_option": "<id>"},
  {"question": "<id>", "value_text": "Toshkent"}
]}
```
Javob: `{"saved": 2, "server_now": "..."}`.
- Faqat **joriy bo'lim** savollari qabul qilinadi (oldingi bo'limga bo'lim tugagandan keyin ~5 soniya ruxsat — oxirgi sekunddagi avtosaqlash uchun). Aks holda `403` ("Bu bo'limning vaqti tugagan").
- Boshlanmagan imtihonga `403`; tugagan yoki o'zi yakunlagan bo'lsa `403`.
- Boshqa imtihonga tegishli savol → `400`.

##### `POST /api/v1/exams/{id}/finish/` — muddatidan oldin yakunlash
Qaytib kirib bo'lmaydi (`state: "submitted"`). Natija darhol ko'rinadi. Tasdiqlash dialogi qo'shing.

---

#### 5. Natijalar

##### `GET /api/v1/exams/{id}/results/`
- **O'qituvchi/admin:** barcha yozilgan o'quvchilar (kelmaganlar `participated: false`), imtihon davomida ham ko'rinadi.
- **O'quvchi:** faqat o'zi. **Ota-ona:** bolalari.
- O'quvchi/ota-ona uchun natija **imtihon tugagach** (yoki o'quvchi o'zi yakunlagach) ochiladi; oldin `{"hidden": true}`.

```json
{ "exam": "...", "engine": "ielts", "state": "finished",
  "results": [{
    "student": {"id": "...", "username": "s1", "name": "Ali Valiyev"},
    "participated": true, "finished_at": null, "engine": "ielts", "approximate": false,
    "sections": [
      {"key": "listening", "title": "Listening", "earned": 32.0, "max": 40.0, "percent": 80.0,
       "score": 7.5, "scale_max": 9, "manual": false},
      {"key": "writing", "manual": true, "score": null, "...": "..."}
    ],
    "total": {"score": 7.5, "max": 9, "label": "Overall band"},   // yoki null
    "pending": ["writing", "speaking"]                              // qo'lda baho kutilmoqda
  }]}
```
- `total: null` va `pending` bo'sh emas bo'lsa — "o'qituvchi bahosi kutilmoqda" deb ko'rsating.
- `approximate: true` bo'lsa natija yonida **"taxminiy"** deb yozing (SAT va Milliy sertifikat).

##### `GET /api/v1/exams/{id}/results/{student_id}/` — bitta o'quvchi tafsiloti
O'qituvchiga qo'shimcha `manual_answers: [{section, question, answer}]` — qo'lda baholanadigan bo'limdagi yozma javoblar (IELTS Writing).

##### `PUT /api/v1/exams/{id}/results/{student_id}/manual/` — qo'lda ball (o'qituvchi)
```json
{"scores": {"writing": 7.0, "speaking": 6.5}}
```
Faqat `manual: true` bo'limlar. IELTS: 0–9, qadam 0.5. Boshqa shablonlar: 0–100 (foiz). Javob — yangilangan o'quvchi natijasi (yuqoridagi format).

---

#### 6. Ball tizimlari

| Shablon | Qanday hisoblanadi |
|---|---|
| **IELTS** | Listening/Reading: to'g'ri javoblar 40 ga keltirilib, rasmiy (Academic) jadvaldan **band** (0–9). Writing/Speaking: o'qituvchi band kiritadi. **Overall** = 4 bandning o'rtachasi, 0.5 gacha yaxlitlanadi (6.25→6.5, 6.75→7.0). Hammasi bo'lmaguncha `total: null`. |
| **SAT** | Reading&Writing va Math har biri **200–800**, jami **400–1600**. College Board'ning **rasmiy o'tkazma jadvali** ishlatiladi (Practice Test #4: natija foizi R&W 66 / Math 54 shkalasiga keltirilib, (past, yuqori) oralig'ining o'rtasi olinadi). **Taxminiy** (`approximate: true`): haqiqiy SAT moslashuvchan va har test shakli o'z jadvaliga ega. `groups: [{key: rw/math, score, range: [past, yuqori]}]` va `total.range` qaytadi — natijani **"1340 (1300–1380)"** ko'rinishida ko'rsatish mumkin. |
| **Milliy sertifikat** | `foiz × 75` (maksimum **75 ball**) va daraja: A+ ≥70, A 65–69.9, B+ 60–64.9, B 55–59.9, C+ 50–54.9, C 46–49.9, undan past — `level: null`. **Taxminiy:** rasmiy ball Rasch modeli bilan hisoblanadi (savol qiyinligi va ishtirokchilarga bog'liq), daraja chegaralari esa rasmiy. |
| **Custom** | Bo'limlarning og'irlikli o'rtacha foizi × `scale`; `pass_percent` bo'lsa `total.passed`. |

> Savol ballari (`points`) testda belgilanadi. Milliy sertifikat matematikasida savol ballari turlicha (1.3 / 2.2 / 3.2) — hozir `points` butun son, shuning uchun foiz hisobi ishlatiladi.

---

#### 7. IELTS Writing — AI baholash (o'qituvchi tasdiqlaydi)

**Qanday ishlaydi:** o'quvchi Writing bo'limida insho yozadi (bo'limdagi test savollari `text` turida: **oxirgi savol = Task 2**, qolganlari = Task 1; savol matni — topshiriq sharti). Imtihon tugagach **server o'zi** (har 5 daqiqada) insholarni Gemini bilan IELTS mezonlari bo'yicha baholaydi va **TAKLIF** sifatida saqlaydi. **Ball o'qituvchi tasdiqlamaguncha o'quvchiga ham, umumiy bandga ham o'tmaydi.**

Har task uchun 4 mezon (0–9, 0.5 qadam): `task_response`, `coherence_cohesion`, `lexical_resource`, `grammatical_range_accuracy`. Task bandi — mezonlar o'rtachasi; **Writing bandi = (Task1 + 2×Task2) / 3**, 0.5 gacha yaxlitlanadi (Task 2 ikki baravar). Hisobni server qiladi.

##### Natijadagi `ai` bloki (`results/` va `results/{student_id}/` ichida)
```json
"ai": {
  "writing": {
    "status": "proposed",              // running | proposed | approved | failed
    "proposed_band": 6.5,              // faqat o'qituvchiga
    "approved_band": null,
    "error": "",
    "generated_at": "2026-10-20T08:12:00Z",
    "result": {
      "writing_band": 6.5,
      "tasks": [{
        "task_number": 1, "words": 160, "min_words": 150, "band": 6.0,
        "criteria": {"task_response": 6.0, "coherence_cohesion": 6.0,
                     "lexical_resource": 6.0, "grammatical_range_accuracy": 6.0},
        "strengths": ["..."], "weaknesses": ["..."],
        "corrections": [{"original": "He go", "corrected": "He goes", "explanation": "..."}],
        "feedback": "..."
      }],
      "summary": {"overall_comment": "...", "recommendations": ["..."]}
    }
  }
}
```
- **O'qituvchi/admin** hamma holatni va `proposed_band`ni ko'radi.
- **O'quvchi/ota-ona** faqat `status: "approved"` bo'lganda va faqat `result` (izoh, mezonlar) ni ko'radi; oldin `ai: {}`.
- `failed` — `error` da sabab; qayta urinish mumkin.

##### `POST /api/v1/exams/{id}/results/{student_id}/ai/` — qo'lda boshlash / qayta urinish (o'qituvchi)
Odatda kerak emas (server o'zi baholaydi); xatodan keyin yoki darhol kerak bo'lsa. `202 {"status": "running"}` — fon oqimida ishlaydi, natijani `results/{student_id}/` dan `ai.writing.status` bilan kuzating (10–60 soniya). Imtihon tugagandan keyin ishlaydi; tasdiqlangan natija qayta baholanmaydi; allaqachon ketayotgan bo'lsa `400`. Xato avtomatik 3 martagacha qayta uriladi.

##### `POST /api/v1/exams/{id}/results/{student_id}/ai/approve/` — tasdiqlash (o'qituvchi)
```json
{}                  // AI taklif qilgan band tasdiqlanadi
{"band": 7.0}       // yoki o'qituvchi o'zgartirib tasdiqlaydi (0–9, 0.5 qadam)
```
Band Writing balli sifatida yoziladi (umumiy band hisoblanadi, Speaking kirilmaguncha `pending`), AI izohi o'quvchiga ochiladi. Javob — yangilangan o'quvchi natijasi. Taklif tayyor bo'lmasa `400`.

> **Tavsiya (UI):** o'qituvchi sahifasida o'quvchi inshosi (`manual_answers`), AI mezonlari, tuzatishlar va `[Tasdiqlash] [Bandni o'zgartirish]` tugmalari. O'quvchida tasdiqlangunga qadar "Writing bahosi o'qituvchi tasdig'ini kutmoqda" yozuvi.

> **Eslatma:** Speaking hozircha o'qituvchi qo'lda band kiritadi (`PUT .../manual/`); audio yozuv va AI baholash keyingi bosqich.

---

#### 8. Xatolar
Umumiy format: `{"success": false, "error": {"code", "message", "details"}}`.
- `403` — vaqt oynasi tashqarisida javob yuborish, tugagan/boshlanmagan imtihon, rol ruxsati yo'q.
- `404` — imtihon topilmadi **yoki sizniki emas** (boshqa guruh).
- `400` — maydon xatolari (`details.items`, `details.sections`, `details.starts_at`, `details.scores`).

#### 9. Hali yo'q (keyingi bosqichlar)
- ~~IELTS Listening audiosi va Reading/SAT matn parchasi~~ — **tayyor**, `BACKEND_QUIZ_GROUPS.md` ga qarang (`current/` javobidagi `item.groups`).
- ~~IELTS Writing AI~~ — **tayyor** (7-bo'lim). IELTS **Speaking**ni AI bilan baholash (o'quvchi ovoz yozuvi yuklashi kerak) — hozir o'qituvchi qo'lda band qo'yadi.
- Tasodifiy variantlar (har o'quvchiga boshqa savollar), imtihon eslatmalari (boshlanishidan oldin).
- IELTS Speaking'ni alohida vaqtda topshirish (hozir `offline` qism sifatida faqat ball kiritiladi).


[↑ Mundarija](#mundarija)

---

## BACKEND_IELTS_WRITING

> Avvalgi fayl: `BACKEND_IELTS_WRITING.md`

### IELTS: Writing (insho), AI baholash, savol-savol tahlil — backend kontrakti

Hammasi mavjud `quizzes` va `exams` API'lariga qo'shimcha; eski mijozlar buzilmaydi.

#### 1. Yangi savol turi: `essay` (Writing)

Yaratish (`POST /api/v1/quizzes/` yoki `PATCH` ichidagi `questions[]`):
```json
{ "type": "essay", "text": "Some people think... Discuss both views.", "points": 9, "min_words": 250 }
```
- To'g'ri javob (`accepted_answers`, `options`) **kerak emas**. `min_words` — 0 dan 2000 gacha (0 — cheklov yo'q).
- O'quvchi ko'rinishida (`GET /quizzes/{id}/`, imtihon `current`): `min_words` bor, javob kaliti yo'q.
- Javob yuborish: boshqa matnli turlar kabi `{ "question": "<id>", "value_text": "..." }` (20 000 belgigacha).
- **Avtomatik baholanmaydi**: `earned_points = 0`. Oddiy testda `max_score` hisobiga **kirmaydi** (insho umumiy foizni tushirmaydi),
  `is_correct = false` — frontend "O'qituvchi tekshiradi" deb ko'rsatishi kerak (`question_type == "essay"`).
- Yuklab olish (`/quizzes/{id}/export/`): insho uchun yozish qatorlari va "kamida N ta so'z" chiqadi, javob kaliti yo'q.

#### 2. IELTS Writing AI tahlili (mock imtihon)

O'qituvchi tugmani bosadi — baholash fonda (cron `sync_exam_writing_ai`, har 30 s):

`POST /api/v1/exams/{exam}/results/{student}/writing-ai/` → `200`, javob — `GET results/{student}/` bilan bir xil (quyida), `writing_ai.status = "queued"`.
Natija tayyor bo'lguncha shu GET'ni har 3–5 soniyada so'rang (`status`: `queued` → `done` | `failed`).

Faqat IELTS imtihon (`scoring.type == "ielts"`), faqat imtihon o'qituvchisi, o'quvchi Writing'ga javob yozgan bo'lishi kerak.
Xatolar: `400` (IELTS emas / javob yo'q / AI sozlanmagan), `403`, `404`.

`GET /api/v1/exams/{exam}/results/{student}/` ga qo'shilgan maydonlar:
```jsonc
"writing_ai": {
  "status": "done",                    // queued | done | failed (failed: "error" matni bor)
  "suggested_band": 6.5,               // FAQAT o'qituvchiga. Writing bandi: Task 1 + 2*Task 2, /3, 0.5 ga yaxlitlangan
  "items": [{
    "question": "...", "task": 2, "word_count": 281, "min_words": 250, "too_short": false,
    "overall_band": 6.5,
    "criteria": [ {"key": "task|coherence|lexical|grammar", "title": "Task Response", "band": 6.5,
                   "capped": false, "comment": "...", "evidence": "..."} , ... ],   // 4 ta
    "errors": [ {"quote": "...", "issue": "...", "correction": "..."} ],
    "strengths": ["..."], "improvements": ["..."], "upgraded_paragraph": "..."
  }]
},
"review": [ ... ]                      // 3-bo'limga qarang
```
- Task raqami savolning `min_words` qiymatidan aniqlanadi (≥200 → Task 2, aks holda Task 1).
- So'z soni minimumdan 10% dan ko'p kam bo'lsa "task" bandi cheklanadi (`capped: true`): 75–90% → 6.0, 50–75% → 5.0, <50% → 4.0 (taxminiy qoida).
- **O'quvchi** `writing_ai` ni faqat o'qituvchi Writing bandini qo'ygach (`PUT .../manual/`) va faqat tahlil qismini (`suggested_band`siz) ko'radi; oldin `null`.
- Yakuniy bandni doim o'qituvchi qo'yadi (`PUT .../manual/`, mavjud endpoint).

#### 3. Savol-savol tahlil (Listening/Reading)

`GET /api/v1/exams/{exam}/results/{student}/` → `review[]` (avtomatik tekshiriladigan bo'limlar, insholarsiz):
```json
{ "section": "reading", "section_title": "Reading", "number": 7, "question": "...", "type": "single",
  "given": "B" , "correct_answer": "C", "earned": 0, "points": 1, "is_correct": false }
```
O'qituvchiga doim; o'quvchi/ota-onaga faqat **imtihon tugagach** (`now >= ends_at`) — erta tugatgan o'quvchi javoblarni
sinfdoshlariga aytib qo'ymasligi uchun. Javob bermagan savolda ham `correct_answer` bor, `given = null`.

#### 4. Uy vazifasi: ingliz tili + `skill_key = "writing"`

Vazifa ingliz tili guruhida `skill_key: "writing"` bilan berilsa, AI tekshiruvi umumiy rubrika o'rniga IELTS 4 mezoni bilan ishlaydi.
Natija (`submission.result`) eski shaklda (frontend o'zgarmaydi): har mezon — bitta `questions[]` elementi (`score` = band/9*100, matnda "Band 6.5"),
umumiy `overall_score` = band/9*100, `grade` = "IELTS Writing Band 6.5", qo'shimcha `result.ielts` — yuqoridagi `items[]` bilan bir xil tuzilma.
O'qituvchi doim tasdiqlaydi (`pending_review`).

#### 5. AI test yaratish: IELTS Writing va daraja

- `exam_name = "IELTS Writing"` → Task 1 (150 so'z; ma'lumot rasm emas, matnli jadval ko'rinishida savol ichida) va Task 2 (250 so'z) `essay` savollari.
- Daraja (target band) mavzuga qo'shiladi (`topic`: "... · band 6.5 darajasi"); yozuvchi AI shu darajaga moslab yozadi.


[↑ Mundarija](#mundarija)

---

## BACKEND_DOSKA_TAHRIR

> Avvalgi fayl: `BACKEND_DOSKA_TAHRIR.md`

### Doska: kod muharriri (Notepad++ uslubi) va elementni tahrirlash (Zoom uslubi) — backend tayyor

Sana: 2026-11-09. Sizning ro'yxatingizdan nima backendda, nima frontendda:

| Talab | Kimda | Holat |
|---|---|---|
| Notepad++ kabi **kod bloki**, til bo'yicha **ranglash** (SQL yozsa SQL ranglanadi) | Saqlash/til ro'yxati — backend; **ranglash brauzerda** — frontend | Backend **tayyor** |
| Yozilgan obyektni **o'zgartirish** (matnni tahrirlash, ko'chirish, rang/o'lcham) — Zoom "edit mode" | Backend: yangi endpoint + socket hodisa; chizish (tutqichlar, tanlash) — frontend | Backend **tayyor** |
| Yonib-o'chib turuvchi **kursor** (caret) | **Faqat frontend** (backend kerak emas) | — |
| Dars tugagach doska PDF/rasm ham kodni **ranglangan** ko'rsatadi | Backend | **tayyor** |

---

#### 1. Yangi element turi: `code`

Mavjud `POST /api/v1/board/<lesson_id>/stroke/` (yoki WebSocket `{"type":"stroke"}`) orqali qo'shiladi — boshqa elementlar bilan bir xil.

```json
{
  "sheet": 0,
  "stroke": {
    "type": "code",
    "text": "SELECT name\nFROM students\n    WHERE age > 18;",
    "language": "sql",
    "x": 80, "y": 120,
    "size": 20,
    "color": "#1c1e3a",
    "w": 520
  }
}
```

| Maydon | Qoida |
|---|---|
| `text` | Majburiy (bo'sh bo'lmasin), eng ko'pi 6000 belgi. **Boshidagi probellar (indent) saqlanadi.** `\r\n` → `\n` |
| `language` | Ro'yxatdan (pastda). Berilmasa `auto`. Noma'lum til → `400` |
| `x`, `y` | **Birinchi qatorning bazaviy chizig'i** `y` da (matn bilan bir xil). Sheet 1600 × 900 |
| `size` | 12–48, standart **20** |
| `color` | Oddiy matn rangi (ranglanmagan qismlar uchun) |
| `w` | Ixtiyoriy: quti kengligi (o'lchamini o'zgartirganda). 40 dan `sheet kengligi − x` gacha |

Javobda server `id`, `by` (ism) va **`by_id`** (muallif user id) qo'shib qaytaradi.

##### Til ro'yxati — yagona manba: doska javobida

`GET /api/v1/board/<lesson_id>/` javobiga **ikkita yangi maydon** qo'shildi:

```json
"code_enabled": true,
"code_languages": [
  {"id": "auto", "label": "Avto"}, {"id": "sql", "label": "SQL"}, {"id": "python", "label": "Python"},
  {"id": "javascript", "label": "JavaScript"}, {"id": "typescript", "label": "TypeScript"},
  {"id": "html", "label": "HTML"}, {"id": "css", "label": "CSS"}, {"id": "java", "label": "Java"},
  {"id": "csharp", "label": "C#"}, {"id": "cpp", "label": "C++"}, {"id": "c", "label": "C"},
  {"id": "php", "label": "PHP"}, {"id": "json", "label": "JSON"}, {"id": "bash", "label": "Bash"},
  {"id": "plaintext", "label": "Oddiy matn"}
]
```

* `code_enabled` — **kod tugmasini ko'rsatish uchun flag**: faqat **Informatika** kursida `true` (`math_enabled`, `chemistry_enabled` kabi). Element backendda barcha fanlarda saqlanadi (zararsiz matn), tugmani ko'rsatish — sizning qaroringiz.
* Tilni qo'lda tanlash ro'yxati — `code_languages` dan oling, frontendda qattiq yozmang.

##### "SQL yozsa SQL ranglansin" — frontend vazifasi

Ranglash **brauzerda** bo'ladi (backend ranglangan HTML yubormaydi):

1. Foydalanuvchi tilni tanlasa (`language: "sql"`) — o'sha til bilan ranglang.
2. `language: "auto"` bo'lsa — kutubxonaning avto-aniqlashidan foydalaning (masalan **highlight.js** `highlightAuto` yoki **CodeMirror 6** til paketlari). Aniqlangan tilni element ichida `language` ga **yozib yuborish shart emas** — `auto` qolishi mumkin; lekin yozib yuborsangiz (masalan "avto-aniqlandi: sql") PDF ham aynan shu til bilan chiqadi — **tavsiya etiladi**.
3. Moslik uchun id lar: `sql, python, javascript, typescript, html, css, java, csharp, cpp, c, php, json, bash, plaintext` — highlight.js / CodeMirror nomlariga to'g'ridan-to'g'ri mos keladi (`csharp`, `cpp` ham).
4. Shrift — **monospace**; indent va bo'sh qatorlar saqlanadi (`white-space: pre`). Tab → 4 probel deb hisoblang.

Dars tugagach hosil bo'ladigan **PDF** va uy vazifasi **rasmlarida** kod serverda ranglanadi (kulrang fon `#f6f8fa`, kalit so'zlar qizil, satrlar to'q ko'k, izohlar kulrang, sonlar ko'k). Server `auto` ni matndan o'zi taxmin qiladi (SQL, Python, JS, HTML, Java, C++, JSON va h.k.).

**Chizish qoidasi (PDF bilan bir xil ko'rinishi uchun):** birinchi qator bazaviy chizig'i `y` da, qatorlar oralig'i **size × 1.35**, fon to'rtburchagi matndan chapga/o'ngga **8 px** kengroq, yuqorida ~size × 1.05, pastda ~size × 0.45.

---

#### 2. Mavjud elementni tahrirlash — YANGI

Hamma element turi (`text`, `code`, `math`, `line`, `rect`, `ellipse`, qalam chizig'i) uchun bitta endpoint.

```
PATCH /api/v1/board/<lesson_id>/stroke/<stroke_id>/
```

```json
{ "sheet": 0, "changes": { "text": "Yangi matn", "color": "#ff0000", "size": 28 } }
```

```json
{ "sheet": 0, "move": [40, -15] }
```

Ikkalasini birga ham yuborish mumkin. Kamida bittasi bo'lishi shart.

| Parametr | Ma'nosi |
|---|---|
| `sheet` | Sahifa raqami |
| `changes` | O'zgargan maydonlar (faqat o'zgarganlarini yuboring): matn tahriri (`text`), `language`, `color`, `size`, `w`, shakl koordinatalari (`x, y, w, h` / `x1..y2`), `latex` (formula), `width`... Server qolgan maydonlarni saqlab qoladi |
| `move` | `[dx, dy]` — **qancha surish** (mutlaq koordinata emas). Server **hamma tur uchun** to'g'ri suradi (qalam chizig'ining barcha nuqtalarini ham — minglab nuqtani yubormaysiz). Shakl sheet chegarasidan chiqib ketmaydi: surish chegarada **kesiladi**, shakl buzilmaydi |

Javob `200`: **yangilangan to'liq element** (`id`, `by`, `by_id`, `edited_by` bilan).

##### Qoidalar
* **Turi** (`type`), `id`, `by`, `by_id` o'zgarmaydi (yuborilsa e'tiborsiz; `type` boshqa qiymat bo'lsa `400`).
* **Kim tahrirlay oladi:** o'qituvchi — **hamma** elementni; chizish ruxsati olgan o'quvchi — faqat **o'zi yozgan** elementni (`by_id` o'ziniki bo'lsa). Boshqasi `403`. Ruxsati yo'q o'quvchi — `403`.
  * Eslatma: **eski elementlarda** (bu yangilanishdan oldin chizilgan) `by_id` yo'q — ularni faqat o'qituvchi tahrirlaydi.
  * UI: o'quvchi uchun boshqa birovning elementida tutqichlar/tahrirlashni ko'rsatmang (`element.by_id === me.id` yoki o'qituvchi).
* Validatsiya yaratishdagi bilan **bir xil** (bo'sh matn, noma'lum til, noto'g'ri koordinata → `400`).
* Element topilmasa `404`. Nima o'zgarishi ko'rsatilmasa `400`.
* Har tahrir jurnalga yoziladi (`board.edit`).
* **Bir vaqtda ikki kishi** bitta elementni o'zgartirsa — oxirgi yozuv g'olib (qulf yo'q). Odatdagi darsda muammo emas.

##### Qachon yuborish kerak
So'rovni **tahrir tugaganda** yuboring, har tugma bosilishida emas:
* matn — kursor elementdan chiqqanda (blur) yoki tasdiqlaganda;
* ko'chirish/o'lcham — sichqoncha **qo'yib yuborilganda** (`mouseup`), sudrash davomida emas (sudrash paytida faqat o'z ekraningizda ko'rsating).

---

#### 3. Real vaqt (WebSocket)

Ulanish o'sha: `wss://<domain>/ws/board/<lesson_id>/?token=<JWT>`.

**Yuborish** (REST PATCH bilan teng kuchli; xato bo'lsa faqat yuboruvchiga `{"type":"error","detail":"..."}`):

```json
{"type": "update", "sheet": 0, "stroke_id": "a1b2c3d4e5f6", "changes": {"text": "Yangi"}, "move": [10, 0]}
```

**Qabul qilish** (hamma ishtirokchiga, yuboruvchining o'ziga ham):

```json
{"type": "stroke_updated", "sheet": 0, "stroke": { "id": "a1b2c3d4e5f6", "type": "text", "text": "Yangi", "...": "..." }}
```

Mijoz `stroke.id` bo'yicha o'z ro'yxatidagi elementni **to'liq almashtiradi** (qisman emas). Element tartibi (qatlam) o'zgarmaydi.

Boshqa hodisalar o'zgarmadi (`stroke`, `erase`, `sheet`, `sheet_renamed`, `current_sheet`, ...). `GET /board/<id>/` har doim eng so'nggi holatni beradi.

---

#### 4. Kursor (blinking caret) — faqat frontend

Backend'ga hech narsa kerak emas. Maslahat: matn/kod elementiga bosganda `contenteditable` yoki `<textarea>` ochiladi (brauzerning o'z yonib-o'chuvchi kursori ishlaydi); tahrir tugagach `PATCH` yuboring (2-bo'lim). Kod uchun CodeMirror 6 yoki Monaco ishlatsangiz kursor, ranglash, indent, avto-aniqlash tayyor keladi.

---

#### 5. Test qilish uchun misollar

```bash
# kod qo'shish
curl -X POST .../api/v1/board/$LESSON/stroke/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"stroke":{"type":"code","text":"SELECT 1;","language":"sql","x":80,"y":120}}'

# matnni tahrirlash
curl -X PATCH .../api/v1/board/$LESSON/stroke/$ID/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"changes":{"text":"SELECT 2;"}}'

# ko'chirish
curl -X PATCH .../api/v1/board/$LESSON/stroke/$ID/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"move":[100,50]}'
```

#### 6. Aytmaganlari (halol)

* **Rotatsiya, qatlam tartibi (oldinga/orqaga), guruhlash, nusxalash/qo'yish** — hozircha yo'q. Kerak bo'lsa ayting: nusxalash uchun yangi element qo'shish (POST) yetadi, qatlam/rotatsiya esa kichik qo'shimcha.
* Elementni o'chirish eskicha: `POST /board/<id>/erase/` — **sabab majburiy**.
* Boshqa odamning kursorini (Zoom'dagi kabi "kim qayerda yozyapti") ko'rsatish hozircha yo'q.
* Bir vaqtda bitta elementni **birgalikda yozish** (Google Docs kabi) yo'q — oxirgi yozuv g'olib.


[↑ Mundarija](#mundarija)

---

## BACKEND_IOS_RECORDING

> Avvalgi fayl: `BACKEND_IOS_RECORDING.md`

### Dars yozuvi — iOS uchun MP4 (backend javobi)

**Kimga:** iOS / frontend jamoasi
**Holat:** backend tayyor va serverga chiqarilgan (2026-10-15)
**Sizdan:** hech qanday o'zgarish shart emas. Stream manzil o'sha, faqat fayl formati iOS ochadigan formatga o'tadi.

---

#### Qisqasi

`BACKEND-IOS.md` dagi muammo (yozuv `video/webm`, iOS ochmaydi) hal qilindi. Dars yozuvining **MP4 (H.264 + AAC)** nusxasi
tayyorlanadi va `recording/stream/` manzili shuni beradi. Variant A (MP4) tanlandi, HLS emas.

| Talab (sizning so'rovingiz) | Natija |
|---|---|
| MP4, H.264, AAC | Ha: `libx264` (yuv420p) + `aac` 96 kbit/s |
| `moov` atomi boshida (`faststart`) | Ha: pleyer butun faylni kutmaydi |
| `content-type: video/mp4` | Ha |
| `Range` so'rovlari | Ha: `accept-ranges: bytes`, `206 Partial Content`, `Content-Range` |
| Eski yozuvlar ham | Ha: avtomatik, navbat bilan (eskisi oldin) |

Qo'shimcha: faqat **audio** yozuvlar (video yo'q) **M4A (AAC)** bo'lib, `content-type: audio/mp4` bilan beriladi (audio WebM ham
iOS'da ochilmaydi).

#### Endpoint o'zgarmadi

```
GET /api/v1/lessons/<id>/recording/            -> { ready, stream_url, ... }   (autentifikatsiya bilan, avvalgidek)
GET <stream_url>                               -> yozuv oqimi (token URLda, auth header kerak emas)
```

`stream_url` ichidagi `?t=<token>` **muddatli**: ochishdan oldin `recording/` dan yangisini oling, eski havolani saqlab qo'ymang.

#### Muhim: MP4 tayyor bo'lguncha vaqt ketadi

Yozuv dars tugagach **darhol** "tayyor" (`ready: true`) bo'ladi, lekin u paytda hali WebM. MP4 nusxa **fonda** tayyorlanadi:

- yangi dars: odatda dars uzunligining 0.3–0.7 qismicha (45 daqiqalik dars ~15–30 daqiqa), server bandligiga qarab ko'proq ham bo'lishi mumkin;
- eski yozuvlar: hammasi navbat bilan o'giriladi, birinchi kunlarda ko'p yozuv navbatda bo'ladi.

MP4 tayyor bo'lmaguncha `stream_url` avvalgidek `video/webm` beradi: Android va brauzer uchun muammo yo'q, **iPhone'da esa ochilmaydi**.
Ilovada ochilmasa, "yozuv tayyorlanmoqda, birozdan keyin urinib ko'ring" degan xabar ko'rsatish yaxshi bo'ladi. Qaysi format
berilayotganini bilish uchun `Content-Type` sarlavhasiga qarang (pastda).

#### Qanday tekshirish

Yozuv havolasi bilan:

```bash
curl -sI "<stream_url>" | grep -i "content-type\|accept-ranges"
```

- MP4 tayyor: `content-type: video/mp4` (audio bo'lsa `audio/mp4`), `accept-ranges: bytes` -> iPhone ochadi.
- Hali tayyor emas: `content-type: video/webm` -> bir ozdan keyin qayta tekshiring.

Range tekshiruvi:

```bash
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" -H "Range: bytes=0-99" "<stream_url>"
```

Kutiladi: `206 100`.

#### Muammo chiqsa

Quyidagilarni yuboring (backendchiga):
1. Dars `id` si va `recording/` javobi.
2. `curl -sI "<stream_url>"` natijasi (sarlavhalar).
3. Xato bo'lsa, iOS jurnalidagi `AVFoundationErrorDomain` qatori.

Ba'zi yozuvlar o'girilmay qolishi mumkin (masalan, fayl buzilgan): ular WebM bilan qoladi va backend jurnalida sababi yoziladi.

---

#### Backend tomoni (ma'lumot uchun)

- `LessonRecording.mp4_file_name` / `mp4_error`; asl WebM o'chirilmaydi.
- Buyruq: `python manage.py convert_recordings [--limit N] [--retry-failed]`.
- docker-compose'dagi alohida `transcoder` xizmati: bir vaqtda bitta yozuv, CPU cheklangan (`TRANSCODER_CPUS`, standart 2), past ustuvorlik.
- Video: 1280 px gacha, ~15 kadr/s, `crf 28` (ekran yozuvi uchun sifat va hajm muvozanati). Audio: AAC 96 kbit/s.


[↑ Mundarija](#mundarija)

---


---

<!-- 4. Trello vazifalari va backend holati -->

## BACKEND_VAZIFALAR

> Avvalgi fayl: `BACKEND_VAZIFALAR.md`

### Backend uchun vazifalar (Trello kartalari, 2026-11)

Bu fayl Trello'dagi Todo kartalari bo'yicha backend tomonda qilinishi kerak bo'lgan ishlarni jamlaydi.
Mahsulot qarorlari egasi bilan kelishib olingan. Endpoint nomlari — taklif, o'zgartirsangiz frontendga ayting.

Har bandda:
- **Hozir** — kodda nima bor;
- **Kerak** — nima qo'shilishi kerak;
- **Frontend** — frontend nima qiladi yoki qilib bo'lgan.

Yo'llar `YolUp_Backend` repo ichida.

---

#### 1. Telefon raqami va akkaunt almashtirish (shoshilinch xato)

Trello: "account almashtirish ishlamayapdi" — ilgari ro'yxatda 3 ta akkaunt chiqardi, hozir faqat 1 ta.

**Hozir**
- `apps/accounts/selectors.py` dagi `linked_accounts` akkauntlarni `phone=user.phone` bo'yicha **aniq satr** sifatida solishtiradi.
- `switch_or_provision_role` ham shu qoidaga tayanadi.
- `clean_phone` raqamni faqat tekshiradi, bir xil ko'rinishga keltirmaydi.
- Frontend 29-oktabrdan 10-noyabrgacha raqamni foydalanuvchi qanday yozsa shunday yuborgan ("901234567", "+998 90 123 45 67"). Shuning uchun bitta odamning akkauntlari bir-biriga bog'lanmay qolgan.

**Kerak**
1. Saqlashda (ro'yxatdan o'tish, profil, telefon o'zgartirish) raqamni `+998XXXXXXXXX` ko'rinishiga keltirish.
2. `linked_accounts` va `switch_account` raqamlarni faqat raqamlari bo'yicha solishtirsin (`core/sms.py` dagi `normalize_phone` kabi).
3. Data migration: bazadagi barcha `phone` qiymatlarini `+998XXXXXXXXX` ko'rinishiga o'tkazish.

**Frontend** — PR #179 da raqam yana `+998XXXXXXXXX` ko'rinishida yuboriladi.

---

#### 2. Davomat: oynadan chiqishlar soni hisobotda

**Hozir** — `GET /courses/{id}/attendance/summary/` da chiqishlar soni yo'q.
- Frontend (PR #179) guruh davomatida har o'quvchi va har dars bo'yicha chiqishlarni ko'rsatadi.
- Buning uchun u `/attendance/?course=` ni 100 tadan sahifalab olib, o'zi qo'shib chiqadi.

**Kerak**
- `summary.students[]` ga `focus_exits` (tanlangan davr bo'yicha jami) qo'shish.
- Darslar ro'yxatiga (`/lessons/?course=`) har dars uchun `focus_exits` (shu darsdagi jami) qo'shish.

Shunda frontend ortiqcha so'rovlarni olib tashlaydi.

---

#### 3. Chat ruxsatlari

Trello: "chat di ko'rish kerak boladi".

**Hozir**
- Shaxsiy chat faqat o'qituvchi ↔ o'quvchi.
  - Faqat o'quvchi `direct/request` yuboradi, u ham o'qituvchining guruhida tasdiqlangan bo'lsa.
  - O'qituvchi accept yoki block qiladi.
- O'qituvchi o'zi chat ocha olmaydi.
- Ota-onada `chat.use` yo'q.
- `ChatRoom` (DIRECT) da faqat `teacher` va `student` maydonlari bor.

**Kerak (kelishilgan qoidalar)**

| Kim → kimga | Qoida |
|---|---|
| O'qituvchi → o'z o'quvchisi | So'rovsiz: chat darhol ACTIVE |
| O'qituvchi → o'z o'quvchisining tasdiqlangan ota-onasi | So'rovsiz: chat darhol ACTIVE |
| O'quvchi → istalgan o'qituvchi | So'rov (PENDING), o'qituvchi accept/block. Guruhda bo'lish sharti olib tashlanadi |
| Ota-ona → farzandining o'qituvchilari | So'rov (PENDING), o'qituvchi accept/block |
| O'quvchi → o'quvchi yoki ota-ona | Mumkin emas |

**Taklif**
- DIRECT xonaga ota-ona uchun ham joy kerak: masalan `parent` FK, yoki `teacher` + `participant`. Juftlik unique bo'lsin.
- Ota-onaga `chat.use` ruxsati (faqat DIRECT, guruh chatlarida emas).
- `POST /chat/direct/open/ {user_id}` — o'qituvchi uchun. Mavjud xonani qaytaradi yoki ACTIVE xona yaratadi.
- `direct/request` ota-ona uchun ham ishlasin.
- `/auth/users/search/` natijasida ota-ona qatorlarida ham `room_id` qaytsin. Hozir u `student_id` bo'yicha qidiriladi, shuning uchun ota-onada doim `null`.

**Frontend** — o'qituvchi uchun "Chat boshlash" (hozir bosilganda hech narsa bo'lmaydi), ota-ona chat bo'limi, ota-onaning so'rov oqimi. Backend tayyor bo'lgach qilinadi.

---

#### 4. Qidiruv

Trello: "search".

**Hozir**
- O'quvchi `/auth/users/search/` da 403 oladi.
- `/search/` da o'quvchi faqat o'z kurslarining o'qituvchilarini topadi.

**Kerak**
- O'quvchi qidiruvda **hammani** topadi: o'qituvchilar, o'quvchilar, ota-onalar. Yozish esa faqat o'qituvchiga, so'rov bilan (3-band).
- Ota-ona qidiruvi: kamida farzandining o'qituvchilari.
- Har natijada:
  - `role`;
  - `room_id` (bo'lsa);
  - `direct_status`;
  - `can_message: "write" | "request" | "none"`.

  Frontend shu maydonga qarab "Yozish", "So'rov yuborish" yoki hech narsa ko'rsatmaydi.
- Maxfiylik: begona foydalanuvchilar uchun faqat ism, username, avatar, rol. Telefon va boshqa ma'lumotlar chiqmasin.

---

#### 5. Spam / shikoyat

Trello: "spam".

**Hozir** — yo'q. Faqat o'qituvchi shaxsiy chatni bloklay oladi.

**Kerak**
- Barcha rollar (o'qituvchi, o'quvchi, ota-ona) shaxsiy chatdagi suhbatdoshini spam deb belgilay oladi.
- Sabab ro'yxatdan tanlanadi:
  - `insult` — haqorat;
  - `harassment` — bezovta qilish;
  - `advertising` — reklama;
  - `other` — boshqa.

  Bunga ixtiyoriy izoh qo'shiladi.
- Belgilangach chat darhol bloklanadi: belgilangan odam belgilaganga yoza olmaydi.
- Shikoyat admin panelga tushadi, adminga bildirishnoma boradi.

**Taklif**
- `SpamReport(reporter, reported, room, reason, comment, status: open|resolved|dismissed, created_at, handled_by, handled_at)`.
- `POST /chat/rooms/{id}/report/ {reason, comment}`.
- Admin uchun:
  - `GET /admin/reports/`;
  - `POST /admin/reports/{id}/resolve|dismiss/`.
- Admin chatni qayta ochishi (unblock) mumkin bo'lsin.

---

#### 6. Rollar (yorliq uchun)

Frontend chat va qidiruvda ism yonida "O'qituvchi / O'quvchi / Ota-ona" yorlig'ini ko'rsatadi.

Ishonch hosil qiling, `role` quyidagi joylarda keladi:
- xabar `sender`ida;
- chat ro'yxatidagi shaxsiy xonalarda (suhbatdosh roli);
- a'zolar ro'yxatida;
- qidiruv natijalarida.

---

#### 7. Kanal

Trello: "Kanal ochish qism". Telegram kanaliga o'xshash.

**Hozir** — yo'q. Faqat kurs guruhining "e'lon rejimi" (`announcement_only`) bor.

**Kelishilgan qoidalar**
- Kanalni o'qituvchi ochadi. Post ham faqat o'qituvchi yozadi.
- A'zolar:
  - guruh tanlansa — uning barcha tasdiqlangan o'quvchilari;
  - yoki alohida tanlangan o'quvchilar;
  - har ikki holatda o'quvchining tasdiqlangan ota-onalari ham qo'shiladi.
- Izohlar har post ostida alohida. O'quvchi ham, ota-ona ham izoh yoza oladi.
- Chat ro'yxatida kanallar boshqa chatlar bilan aralash chiqadi (kanal belgisi bilan).

**Taklif**
- Mavjud chat infratuzilmasidan foydalanish: `ChatRoom.Kind.CHANNEL`.
  - Postlar — xabarlar (yozish faqat egasida).
  - Izohlar — `thread_root=post` bo'lgan xabarlar.
  - Post qatorida `comment_count`.
- `POST /chat/channels/ {title, description, course_ids[], student_ids[]}`.
- A'zolarni boshqarish: `POST/DELETE /chat/channels/{id}/members/`.
- `GET /chat/rooms/` da `kind: "channel"` bilan qaytadi.
- WS hodisalari: yangi post, yangi izoh.

---

#### 8. Speaking club

Trello: "speaking club".

**Hozir** — yo'q. Yaqin narsa: kurs ovozli xonasi (`apps/voice`, bitta kursda bitta faol xona).

**Kelishilgan qoidalar**
- Club = o'z chati + jonli mashg'ulotlar (ovozli/video).
- O'qituvchi turli guruhlaridan o'quvchilarni (yoki butun guruhni) qo'shadi.
- Qo'shilganlar darhol a'zo bo'ladi (taklifni qabul qilish shart emas), ularga bildirishnoma boradi.

**Taklif**
- `Club(teacher, title, description)` va a'zolar.
- Clubning chat xonasi: `ChatRoom.Kind.CLUB` yoki kanaldagi kabi umumiy mexanizm.
- Jonli mashg'ulot: mavjud jonli dars yoki `VoiceRoom` infratuzilmasi kursga emas, clubga bog'lansin.
  - Rejalashtirish.
  - "Boshlandi" bildirishnomasi.

---

#### 9. Materiallar

Trello: "Material qism".

**Hozir** — `Material(course, …)`: faqat guruhga bog'langan, darsga bog'lanmagan.
- Dars video yozuvi (`LessonRecording`) va doska PDF'i materiallarga kirmaydi.

**Kelishilgan qoidalar**
- Tuzilma: **Guruh → darslar → fayllar**.
- Faqat o'qituvchi yuklaydi. O'sha guruh o'quvchilari va ularning ota-onalari ko'radi.
- Dars tugagach uning video yozuvi va doska PDF'i shu darsning papkasida **avtomatik** paydo bo'ladi.
- Kirish faqat Workspace'dagi "Materiallar" orqali.

**Taklif**
- `Material.lesson` (nullable FK). Darsga bog'lanmagan fayllar "Umumiy" papkada.
- Ro'yxatlar:
  - `GET /materials/courses/` — guruhlar va fayllar soni;
  - `GET /materials/courses/{id}/lessons/` — darslar: `file_count`, `has_recording`, `has_board`;
  - `GET /materials/?course=&lesson=` — fayllar.
- Video yozuv va doskani nusxalash shart emas: dars papkasi ro'yxatida ular alohida elementlar sifatida qaytsa yetadi (mavjud endpointlarga havola bilan).
- Upload: `lesson` maydoni ixtiyoriy.

---

#### 10. Balans va to'lov eslatmalari

Trello: "balance qism", "o'qituvchi tomonidan notification borish qism".

**Hozir**
- `Course.monthly_fee`.
- `CoursePayment` — o'qituvchi oyni qo'lda "to'landi" deb belgilaydi.
- To'lov muddati va eslatma yo'q.

**Kelishilgan qoidalar**
- To'lov kunini o'qituvchi har guruh uchun belgilaydi (masalan har oyning 5-sanasi).
- O'qituvchi eslatma vaqtini tanlaydi: muddatdan 3, 5 yoki 7 kun oldin. Bir nechtasini tanlash mumkinmi — 2-ochiq savolga qarang.
- Eslatma **o'quvchiga ham, ota-onaga ham** boradi (faqat shu oy to'lanmagan bo'lsa).
- O'qituvchida to'lamaganlar uchun qizil belgi:
  - chat ro'yxatida guruh yonida;
  - guruhning Progress tabida.

**Taklif**
- `Course.payment_day` (1–28) va `Course.payment_reminder_days` (masalan `[3, 7]`).
- Scheduler'ga kunlik job. Bildirishnoma turi `payment_reminder`, matnda summa va muddat.
- Muddat o'tib ketgan va to'lanmagan bo'lsa holat `overdue`.
- O'qituvchining kurslar yoki chat xonalari ro'yxatida `unpaid_count` (joriy oy).

---

#### 11. O'qituvchining qo'lda bildirishnomasi

**Hozir** — `/notifications/send/` o'qituvchiga `users` va `parents_of` (o'z o'quvchilari) bilan ruxsat beradi. Frontendda o'qituvchi uchun oyna yo'q, frontend uni qo'shadi.

**Kerak (qulaylik uchun)** — `target_type: "course"`: o'qituvchining o'z guruhining barcha o'quvchilari. Ota-onalarga ham yuborish uchun bayroq bo'lsin.

---

#### 12. Ota-ona (Kuzatuvchi)

Trello: "ota ona".

**Hozir** — ota-ona sahifasidagi ball grafigi faqat uy vazifasi ballaridan, 6 haftalik (`apps/analytics/child.py`).

**Kerak**
- Ball tarixiga test (quiz) va mock imtihon natijalari ham qo'shilsin.
- Uzunroq davr bo'lsin (oylar kesimida ham).
- Taklif: `GET /analytics/child/{id}/scores/?range=8w|6m|all` → `points[]: {date, kind: homework|quiz|exam, title, score_10}` va davrlar bo'yicha o'rtachalar.
- Interfeysda "Ota-ona" endi "Kuzatuvchi", "Farzand" endi "O'quvchi" deb yoziladi. Backend yaratadigan matnlarda (bildirishnomalar, xatlar) ham shu so'zlar ishlatilsin.

---

#### 13. Uy vazifasi ichida savollar ("Google forma")

Trello: "Vazifa: HomeWork".

**Hozir** — topshiriq faqat fayl (PDF/rasm/Word, speaking uchun audio) yoki doska. Fayl majburiy.
- AI tekshiruvi va "AI baholay olmadi — o'zingiz baholang" oqimi bor.

**Kerak**
- O'qituvchi vazifaning o'zida savollar tuzadi:
  - bitta to'g'ri javobli test;
  - bir nechta to'g'ri javobli test;
  - qisqa yoki uzun ochiq javob.

  Har savolga ball qo'yiladi.
- O'quvchi shu yerda javob beradi. Savollar bo'lsa, fayl majburiy emas.
- Testlar avtomatik baholanadi.
- Ochiq javoblar: `ai_check` yoqilgan bo'lsa AI baholaydi, aks holda o'qituvchi. Yakuniy ballni o'qituvchi tasdiqlaydi (hozirgidek).

**Taklif**
- `AssignmentQuestion(assignment, order, type, text, options[], correct[], points)`.
- `SubmissionAnswer(submission, question, answer, auto_score, ai_score, final_score)`.

---

#### 14. Sertifikat holati — savol

Trello: "profile qismda xato". Sertifikat doim "Tekshirilmoqda" bo'lib turadi.

**Hozir** — admin `/admin/certificates/{id}/verify|reject/` bilan tasdiqlaydi. Admin tasdiqlamaguncha holat `pending`.

**Savol** — admin tasdiqlash amalda ishlatiladimi?
- Ishlatilmasa: sertifikat yuklanganda avtomatik `verified` bo'lsinmi yoki holat umuman olib tashlansinmi?

Frontend sizning javobingizga qarab o'zgartiradi.

---

#### 15. Test yaratish — pullik (reja)

Trello: "test yaratish qismda" (faqat Backend yorlig'i). Hozircha hammaga ochiq qoladi.

Keyinchalik `GET /auth/me/` da `can_create_tests` kabi bayroq qo'shilsa, frontend pullik holatni ko'rsatishi oson bo'ladi.

---

#### 16. Ekran ulashishda boshqaruv oynasi — backend kerak emas ✅

Backend jamoasi javobi: `FRONTEND_TODO_SCREEN_SHARE.md`.

- Backendda hech narsa qilinmaydi. O'qituvchi tokenida `screen_share` va `screen_share_audio` ruxsatlari allaqachon bor (`TEACHER_PUBLISH_SOURCES`).
- Yangi endpoint, WS hodisasi yoki track qo'shilmaydi. Yozuv ham avvalgidek ishlaydi.
- Ish to'liq frontendda:
  - Document Picture-in-Picture boshqaruv oynasi (Chrome/Edge 116+);
  - qo'llab-quvvatlamaydigan brauzerlar uchun zaxira yo'l;
  - `getDisplayMedia` sozlamalari (`surfaceSwitching`, `monitorTypeSurfaces`).

**Frontend holati** — PR #181 da tayyor va merge qilingan:
- O'qituvchi ekran ulashayotganda boshqa oynaga o'tsa, Chrome ruxsat bersa kichik boshqaruv oynasi o'zi ochiladi. Dars panelidagi tugma bilan ham ochiladi.
- Oynada mikrofon, kamera, "Ulashishni to'xtatish", dars vaqti va o'quvchilar soni bor.
- Oyna qo'lda yopilsa, ulashish davom etadi.
- Safari va Firefox'da bir martalik ogohlantirish chiqadi.
- `vercel.json` dagi `Permissions-Policy` `display-capture` ni bloklamaydi, o'zgartirish kerak bo'lmadi.

---

#### 17. Darsda hammani cheklash: mikrofon va kamera

Trello: "meeting da xammani cheklash".

**Hozir**
- `POST /live/mute-all/` (`apps/live/services.py`, `mute_all`) faqat audio tracklarni o'chiradi.
- Ruxsat olinmaydi: o'quvchi xohlasa qayta yoqa oladi.
- Kamerani hammada o'chiradigan endpoint yo'q.

**Kerak (kelishilgan)**
- Kamera uchun alohida amal. Taklif: `POST /live/camera-off-all/ {lesson, except?}` yoki `mute-all` ga `kind: "audio" | "video"`.
- Ikkala amalda ham o'quvchilarning **ruxsati olinadi**:
  - `can_publish_sources` dan `microphone` yoki `camera` olib tashlanadi;
  - o'qituvchi va `except` ro'yxatidagilarga tegilmaydi;
  - qayta yoqish uchun o'quvchi yana so'rov yuboradi.
- O'quvchi interfeysi "So'rash" holatiga qaytishi uchun WS hodisasi kerak: masalan `mic_revoked` / `camera_revoked` (`student_id` bilan).
- Javob: o'chirilganlar soni (hozirgidek).

**Frontend** — ishtirokchilar panelida ikki tugma: "Hammaning ovozini o'chirish" (bor) va "Hammaning kamerasini o'chirish" (yangi).

---

#### 18. Mikrofon va kamera ruxsati — bir martalik

Trello: "Meeting permission".

**Hozir** — o'qituvchi `grant-mic` yoki `grant-camera` qilsa, ruxsat dars oxirigacha qoladi. O'quvchi o'zi o'chirib-yoqaveradi.

**Kerak (kelishilgan)**
- O'quvchi ruxsat berilgan mikrofon yoki kamerani **o'zi o'chirishi bilan ruxsat ham olinadi**. Qayta yoqish uchun yana so'rov yuboradi.
- Ikki yo'l taklif qilinadi:
  - LiveKit webhook `track_muted` / `track_unpublished` (o'quvchi, `microphone`/`camera`) kelganda shu manba ruxsatini olib tashlash. Ishonchliroq, chunki frontendni chetlab o'tib bo'lmaydi.
  - Yoki frontend chaqiradigan endpoint: `POST /live/release-media/ {lesson, kind}`.
- O'qituvchi paneli yangilanishi uchun WS hodisasi kerak (17-banddagi `mic_revoked` / `camera_revoked`).
- Istisno: 19-banddagi "ochiq" rejim yoqilgan bo'lsa ruxsat olinmaydi.

---

#### 19. Ochiq mikrofon va ochiq kamera rejimi (speaking club)

Trello: "Meeting permission" ("true/false qo'yib qo'yamiz, hammaga mikrofonga dostup").

**Kerak (kelishilgan)**
- O'qituvchi darsda ikkita alohida almashtirgich ko'radi: "Hammaga mikrofon ochiq" va "Hammaga kamera ochiq".
- Yoqilganda barcha o'quvchilar (hozirgi va keyin kirganlar) so'rovsiz yoqa oladi. Token berishda ham hisobga olinsin.
- O'chirilganda ruxsat yana so'rov bilan bo'ladi.
- Ota-ona roziligi (`consent` → `camera`) baribir amal qiladi.

**Taklif**
- `Lesson.open_mic`, `Lesson.open_camera` (bool).
- `PATCH /live/lesson/{id}/media-mode/ {open_mic?, open_camera?}`.
- Holat `GET /live/token/` va `presence` javobida qaytsin.
- WS hodisasi: `media_mode`.

**Savol** — almashtirgich o'chirilganda hozir yoqilgan mikrofon va kameralar ham o'chirilsinmi (ruxsat olinsinmi)? Taklif: ha, 17-banddagidek.

Speaking club'ning (8-band) jonli mashg'ulotlarida ham shu rejim ishlaydi.

---

#### 20. Dars yozuvini guruhga yuborish — ixtiyoriy

Trello: "videa record".

**Hozir** — yozuv tayyor bo'lishi bilan `_announce_recording_ready` → `publish_recording_message` uni guruh chatiga **avtomatik** tashlaydi va bildirishnoma yuboradi.

**Kerak (kelishilgan)**
- Darsni tugatish so'roviga `post_recording: bool` (standart `true`).
- Qiymat yozuvda saqlansin (masalan `LessonRecording.post_to_chat`).
- Yozuv tayyor bo'lganda guruhga xabar va bildirishnoma **faqat `true` bo'lsa** boradi.
- Yozuv sahifasidagi "Chatga yuborish" (`share_recording`) o'zgarmaydi: o'qituvchi keyin qo'lda yubora oladi.

**Frontend** — "Darsni tugatish" oynasida "Video yozuvni guruhga yuborish" belgisi (oldindan belgilangan).

---

#### 21. Yozuv konvertatsiyasi — tayyor bo'lguncha yopiq

Trello: "video screen record".

**Hozir**
- Yozuv WebM bilan darhol `completed` bo'ladi va guruhga e'lon qilinadi.
- MP4 nusxa fonda tayyorlanadi: `apps/lessons/transcode.py`, bir vaqtda bitta, `nice`.

**Kerak (kelishilgan)**
- MP4 tayyor bo'lguncha yozuv **hech kimga ochilmaydi**, o'qituvchiga ham.
  - `recording_info` yangi holatni qaytaradi: `status: "converting"`, `stream_url: null`.
- Guruhga xabar (20-band) va bildirishnoma **konvertatsiya tugagach** yuboriladi.
- Konvertatsiya server yuklamasi kam paytda bajariladi: navbat, CPU chegarasi yoki tungi oyna. Qanday qilishni backend o'zi tanlaydi.
- Taklif: konvertatsiya muvaffaqiyatsiz bo'lsa, asl WebM bilan ochish.

**Frontend** — yozuv sahifasi va ro'yxatlarda "Konvertatsiya qilinmoqda — tayyor bo'lgach xabar beramiz" holati, holatni vaqti-vaqti bilan so'rab turish.

---

#### 22. Diqqat tekshiruvi vaqti — backend tuzatdi ✅

Trello: "darsda aftomatik xabar borishi kerak edi…".

- Backend `bf31014` commitida tuzatdi: tekshiruvlar dars bo'ylab teng yoyiladi (har ~24 daqiqaga 1 ta, 2 soat = 5 ta), kech kirganlarga siqilmaydi.
- Frontendda o'zgarish kerak emas, jonli darsda sinab ko'rish kerak.

---

#### Ochiq savollar (egasi bilan aniqlashtiriladi)

1. Kanal yoki club guruh bo'yicha yaratilgan bo'lsa, guruhga keyin qo'shilgan o'quvchi avtomatik qo'shilsinmi?
2. To'lov eslatmasi: o'qituvchi 3, 5 va 7 kundan bir nechtasini birga tanlay oladimi?
3. 19-band: "ochiq" almashtirgich o'chirilganda yoqilgan mikrofon va kameralar ham o'chirilsinmi?


[↑ Mundarija](#mundarija)

---

## BACKEND_YANGILANISHLAR_2026-11-10

> Avvalgi fayl: `BACKEND_YANGILANISHLAR_2026-11-10.md`

### Backend yangilanishlari (2026-11-10) — `BACKEND_VAZIFALAR.md` bo'yicha

Raqamlar `BACKEND_VAZIFALAR.md` dagi band raqamlari. Endpoint nomlari taklifdagidek; farq bo'lsa shu yerda yozilgan.
Hammasi testlar bilan yopilgan, serverga hali chiqarilmagan (deploy oxirida).

**Bajarilmagan / javob kutayotgan:** 14 (sertifikat holati — savol), 15 (pullik test — "keyinroq" deyilgan, tegilmadi),
"Ochiq savollar"dan 1-savol (kanalga keyin qo'shilgan o'quvchi). 16 va 22 — backendda ish yo'q.

---

#### 1. Telefon raqami va akkaunt almashtirish

- Telefon endi **har doim `+998XXXXXXXXX`** ko'rinishida saqlanadi (ro'yxatdan o'tish, profil, raqam almashtirish, admin — hammasida).
  `901234567`, `+998 90 123 45 67`, `998901234567` bir xil raqam.
- `linked_accounts` va akkaunt almashtirish raqamlarni faqat raqamlari bo'yicha solishtiradi.
- Bazadagi eski raqamlar deploy paytida data-migratsiya bilan (`accounts 0022`) o'tkaziladi. Raqam bo'lmagan qiymatlarga tegilmaydi.
- **Frontend:** raqamni qanday yuborsangiz ham bo'ladi; javobda doim `+998...` qaytadi.

#### 2. Davomat: oynadan chiqishlar

- `GET /courses/{id}/attendance/summary/`: har `students[]` qatorida `focus_exits` va javob ildizida `focus_exits` (tanlangan `range` bo'yicha jami).
- `GET /lessons/?course=`: har darsda `focus_exits` — shu darsdagi barcha o'quvchilarning chiqishlari jami.
  **Faqat o'qituvchi/admin uchun**, boshqalarga `null`.
- Hisob: `exit` hodisalari soni (qaytmagan chiqish ham 1 ta).

#### 3. Chat ruxsatlari

DIRECT xonada `teacher` — o'qituvchi, `student` — o'qituvchidan boshqa ishtirokchi (**o'quvchi yoki ota-ona**). Yangi jadval kerak bo'lmadi.

| Kim → kimga | Qoida |
|---|---|
| O'qituvchi → o'z o'quvchisi / uning tasdiqlangan ota-onasi | So'rovsiz, chat darhol `active` |
| O'quvchi → istalgan o'qituvchi | `pending`, o'qituvchi accept/block (guruhda bo'lish sharti olib tashlandi) |
| Ota-ona → farzandining o'qituvchisi | `pending`, o'qituvchi accept/block |
| Boshqa juftliklar | mumkin emas (`403`) |

- `POST /chat/rooms/direct/open/ {user_id}` — o'qituvchi uchun. Mavjud xonani qaytaradi yoki `active` yaratadi
  (kutayotgan/bloklangan xonani ham `active` qiladi).
- `POST /chat/rooms/direct/request/ {teacher}` — endi ota-ona ham yuboradi (faqat farzandining o'qituvchisiga).
- `GET /chat/rooms/teachers/` — ota-onada farzandlarining o'qituvchilari.
- Ota-onaga `chat.use` berildi: faqat shaxsiy chat. Guruh chatlari ro'yxatida yo'q, guruh xonasi `404` beradi.
- `direct_status` ga yangi qiymat: `spam` (5-band).

#### 4. Qidiruv

`GET /auth/users/search/?q=` va `GET /search/?type=people` — endi o'quvchi va ota-ona ham ishlatadi (avval o'quvchiga `403` edi).

- **O'qituvchi:** o'z guruhlaridagi o'quvchilar (kutayotganlari ham) va ularning ota-onalari (ism, @username, telefon).
- **O'quvchi:** hammani topadi — o'qituvchilar, o'quvchilar, ota-onalar. Telefon bo'yicha begona topilmaydi.
- **Ota-ona:** farzandining o'qituvchilari.
- Har natijada: `id, name, username, role, avatar, room_id, direct_status, can_message`.
  `can_message`: `"write"` (yozish), `"request"` (so'rov yuborish), `"none"`.
- Begona uchun faqat ism, username, avatar, rol chiqadi. Admin qidiruvi o'zgarmagan.

#### 5. Spam / shikoyat

- `POST /chat/rooms/{id}/report/ {reason, comment?}` — `reason`: `insult | harassment | advertising | other`. Barcha rollar, faqat shaxsiy chatda.
  Javob `201`: shikoyat. Chat **darhol** `spam` holatiga o'tadi: belgilangan odam yozolmaydi, qayta so'rov ham yubora olmaydi,
  o'qituvchi accept/open qila olmaydi. Takroriy bosish yangi shikoyat yaratmaydi. Adminlarga bildirishnoma (`kind: spam_report`).
- Admin (`user.manage`):
  - `GET /admin/reports/?status=open|resolved|dismissed` — sahifalangan ro'yxat;
  - `GET /admin/reports/{id}/` — shikoyat + suhbatning oxirgi 10 xabari (`recent_messages`);
  - `POST /admin/reports/{id}/resolve/` — tasdiqlash (chat bloklangan qoladi);
  - `POST /admin/reports/{id}/dismiss/` — rad etish (chat avvalgi holatiga qaytadi);
  - `POST /admin/reports/{id}/unblock/` — chatni qayta ochish.

#### 6. Rollar yorlig'i

`role` hamma joyda bor: xabar `sender.role`, a'zolar ro'yxati, qidiruv, `other_user.role`. Qo'shildi:
chat ro'yxatidagi `last_message.sender_role`.

#### 7. Kanal

`ChatRoom.kind = "channel"`. Mavjud chat endpointlari ishlaydi, qo'shimchalar:

- `POST /chat/channels/ {title, description?, course_ids?: [], student_ids?: []}` — faqat o'qituvchi. A'zolar: tanlangan guruhlarning
  tasdiqlangan o'quvchilari va/yoki alohida o'quvchilar (faqat o'z o'quvchilari); **har ikki holatda** ularning tasdiqlangan ota-onalari ham.
- `PATCH /chat/channels/{id}/ {title?, description?}`, `DELETE /chat/channels/{id}/` — egasi.
- `GET /chat/channels/{id}/members/` (rol bilan), `POST .../members/ {course_ids?, student_ids?}`, `DELETE .../members/{user_id}/`.
  O'quvchi chiqarilsa, kanalda boshqa farzandi qolmagan ota-ona ham chiqadi.
- `GET /chat/rooms/` da kanal `kind: "channel"`, `title`, `description`, `members_count`, `can_write` (post — faqat egasi),
  `can_comment` (egasi va har bir a'zo) bilan chiqadi.
- **Postlar** — oddiy xabarlar: `POST /chat/rooms/{id}/messages/ {text}` (faqat egasi, boshqaga `403`).
  Lentada faqat postlar, har birida `comment_count`.
- **Izohlar:** yozish — `POST /chat/rooms/{id}/messages/ {text, thread_root_id: <post id>}` (o'quvchi ham, ota-ona ham);
  o'qish — `GET /chat/rooms/{id}/messages/?thread=<post id>`. Izoh xabarida `thread_root`.
  Izohlar asosiy lentada, o'qilmaganlar sonida va xonaning "oxirgi xabar"ida hisobga olinmaydi.
- **WS:** yangi post — oddiy `message` hodisasi; yangi izoh — `{type: "channel_comment", post_id, comment_count, message}`.
- Ochiq savol 1: guruhga keyin qo'shilgan o'quvchi kanalga **avtomatik qo'shilmaydi** (o'qituvchi `members` orqali qo'shadi).
  Avtomatik qilish kerak bo'lsa ayting.

#### 8. Speaking club

Club = `Course` (`kind: "club"`): o'z chat xonasi, jonli darslar, davomat va yozuvlar tayyor infratuzilmadan ishlaydi.

- `GET /clubs/` — o'qituvchi: o'z clublari; o'quvchi: a'zo bo'lganlari; ota-ona: farzandining clublari.
- `POST /clubs/ {title, description?, subject?, course_ids?, student_ids?}` — o'qituvchi. Tanlangan guruhlar (butun) yoki alohida
  o'quvchilar **darhol a'zo** bo'ladi (tasdiqlash shart emas) va `kind: club_added` bildirishnomasi oladi.
- `GET/PATCH/DELETE /clubs/{id}/`; `GET|POST /clubs/{id}/members/`, `DELETE /clubs/{id}/members/{student_id}/`.
- Javobda `chat_room_id`, `members_count`, `kind: "club"`.
- **Jonli mashg'ulot:** oddiy `/lessons/` (`course = club id`) — rejalashtirish, "boshlandi" signali, yozuv, davomat shu yo'l bilan.
- `GET /courses/` (guruhlar ro'yxati) clublarni **ko'rsatmaydi**; kerak bo'lsa `?kind=club` yoki `?kind=all`. `GET /courses/catalog/` ham clubsiz.
  `CourseSerializer` ga `kind` qo'shildi.

#### 9. Materiallar: Guruh → darslar → fayllar

- `Material.lesson` (ixtiyoriy). Yuklashda `lesson=<id>` (multipart). Darssiz fayllar — "Umumiy".
- `GET /materials/courses/` — guruhlar va fayllar soni.
- `GET /materials/courses/{id}/lessons/` — `{course, general: {file_count}, lessons: [{id, title, starts_at, status, file_count, has_recording, has_board}]}`.
  O'quvchi/ota-ona faqat mazmuni bor (fayl, tayyor yozuv yoki doska) darslarni ko'radi; o'qituvchi hammasini.
- `GET /materials/?course=&lesson=<id>|general` — fayllar (`lesson_id` har faylda).
- `GET /materials/lessons/{id}/` — dars papkasi: `{lesson, files, recording: {status, info_url} | null, board: {pdf_url} | null}`.
  Video yozuv va doska PDF'i nusxalanmaydi — havola bilan (`info_url` = mavjud `/lessons/{id}/recording/`).
- `GET /materials/lessons/{id}/board.pdf` — doska PDF'i (ota-onada ham ishlaydi).

#### 10. Balans va to'lov eslatmalari

- `Course.payment_day` (1–28) va `Course.payment_reminder_days` (`[3, 5, 7]` dan, bir nechtasi mumkin — ochiq savol 2: ruxsat berilgan)
  — `PATCH /courses/{id}/`. Eslatma kunlari berilsa `payment_day` shart.
- Kunlik (soatlik tekshiruv) job: muddatdan N kun oldin shu oy to'lanmagan o'quvchiga **va** uning tasdiqlangan ota-onalariga
  bildirishnoma (`kind: payment_reminder`, matnda summa va muddat). Har eslatma bir marta.
- `unpaid_count` va `overdue_count` (joriy oy) — o'qituvchida `GET /courses/` va `GET /chat/rooms/` (kurs guruhi) da; boshqalarga `null`.
  To'lov sozlanmagan guruh (`monthly_fee` ham, `payment_day` ham yo'q) "to'lamagan" hisoblanmaydi.
- Progress to'lov qatorida `overdue: bool` (muddat o'tgan va to'lanmagan). `status` hamon `paid | unpaid`.

#### 11. O'qituvchining qo'lda bildirishnomasi

`POST /notifications/send/ {target_type: "course", course_id, include_parents?: bool, description}` — o'z guruhining barcha
tasdiqlangan o'quvchilari (+ ixtiyoriy ota-onalari).

#### 12. Ota-ona: ball tarixi

`GET /analytics/child/{id}/scores/?range=8w|6m|all` — uy vazifasi + test (har testning eng so'nggi urinishi) + mock imtihon, hammasi 10 ballik.

```json
{ "range": "8w", "scale": 10, "period_type": "week",
  "summary": {"overall": 8.1, "homework": 8.5, "quiz": 9.0, "exam": 7.8, "count": 4},
  "periods": [{"start": "2026-11-09", "overall": 9.0, "homework": 9.0, "quiz": 9.0, "exam": null, "count": 2}, ...],
  "points": [{"date": "...", "kind": "homework|quiz|exam", "title": "...", "score_10": 8.0}, ...] }
```

`8w` — 8 hafta (haftalar), `6m` — 6 oy, `all` — birinchi balldan (ko'pi bilan 24 oy), oylar. `analytics` roziligi o'chiq bo'lsa `403`.
Matnlarda "Kuzatuvchi / O'quvchi" so'zlari: backend yaratadigan matnlarda hozircha o'zgarmagan (alohida ish).

#### 13. Uy vazifasi ichida savollar

- Vazifa yaratish/tahrirlashda `questions: [{type: single|multiple|short|long, text, options?, correct?: [indekslar], points?}]`
  (JSON yoki multipart'da JSON matn). `GET /homework/assignments/{id}/` da `questions` (o'quvchiga `correct`siz), `has_questions`, `questions_points`.
  Topshiriq tushgach savollarni o'zgartirib bo'lmaydi.
- Topshirish: `POST /homework/assignments/{id}/submit/ {answers: [{question_id, answer}]}` — test: tanlangan indekslar ro'yxati,
  ochiq: matn. Savollar bo'lsa fayl majburiy emas (xohlasa biriktiradi).
- Testlar darhol baholanadi ("bir nechta to'g'ri"da hammasi yoki hech nima). **Ochiq savol yo'q bo'lsa natija avtomatik tasdiqlanadi (`done`)**.
  Ochiq savol bor bo'lsa: `ai_check` yoqilgan va ichki AI sozlangan bo'lsa AI baholaydi, aks holda o'qituvchi; yakuniy ballni o'qituvchi tasdiqlaydi.
- Natijada `answers: [{question_id, answer, score, correct?, is_correct?, ai_score? (o'qituvchiga)}]`.
- O'qituvchi baholash: `POST /homework/submissions/{id}/review/ {answer_scores: {question_id: ball}}` — umumiy baho berilmasa shulardan hisoblanadi.

#### 17. Darsda hammani cheklash

- `POST /live/mute-all/ {lesson_id, except?}` — endi mikrofonni o'chiradi **va ruxsatini qaytarib oladi**. Javob `{muted: n}`.
- `POST /live/camera-off-all/ {lesson_id, except?}` (yoki `mute-all` ga `kind: "video"`) — kamera. Javob `{camera_off: n}`. Ekran ulashishga tegilmaydi.
- WS (doska kanali): `{type: "mic_revoked" | "camera_revoked", student_id}` — o'quvchi interfeysi "So'rash" holatiga qaytadi,
  o'qituvchi paneli yangilanadi.

#### 18. Bir martalik ruxsat

`POST /live/release-media/ {lesson_id, kind: "microphone"|"camera"}` — o'quvchi ruxsat berilgan mikrofon/kamerani **o'chirgach**
frontend shuni chaqiradi. Javob `{revoked, open}`; ruxsat olinadi, `mic_revoked`/`camera_revoked` hodisasi ketadi.
Ochiq rejim yoqilgan bo'lsa ruxsat olinmaydi (`open: true`).

(LiveKit webhook ishlatilmadi: LiveKit "track muted" webhook hodisasini yubormaydi, faqat `track_unpublished`, shuning uchun ishonchsiz.)

#### 19. Ochiq mikrofon / ochiq kamera

- `Lesson.open_mic`, `Lesson.open_camera`. `PATCH /live/lesson/{id}/media-mode/ {open_mic?, open_camera?}` (o'qituvchi), `GET` — holat.
- Holat `POST /live/token/` javobida (`open_mic`, `open_camera`) va `GET /live/lesson/{id}/presence/` da ham qaytadi.
- Yoqilganda xonadagi o'quvchilarga ruxsat darhol qo'shiladi, keyin kirganlar tokenda oladi. O'chirilganda yoqilgan mikrofon/kameralar
  o'chiriladi va ruxsat olinadi (ochiq savol 3 bo'yicha taklif qilingan "ha").
- Ota-ona roziligi (`consent camera`) baribir amal qiladi.
- WS: `{type: "media_mode", open_mic, open_camera}`.

#### 20. Yozuvni guruhga yuborish — ixtiyoriy

`POST /lessons/{id}/finish/ {recording_title?, post_recording?: bool}` — standart `true`. `false` bo'lsa yozuv tayyor bo'lganda guruhga xabar
va bildirishnoma **yuborilmaydi**. "Chatga yuborish" (`recording/share/`) o'zgarmagan. `GET .../recording/` javobida `post_to_chat`.

#### 21. Yozuv konvertatsiyasi — tayyor bo'lguncha yopiq

- Yangi yozuv MP4 nusxa tayyor bo'lguncha **hech kimga (o'qituvchiga ham) ochilmaydi**: `GET /lessons/{id}/recording/` →
  `status: "converting"`, `ready: false`, `stream_url: null`. Frontend holatni vaqti-vaqti bilan so'rab turadi.
- Guruhga xabar va bildirishnoma konvertatsiya tugagach ketadi.
- Konvertatsiya xato bilan tugasa — asl WebM bilan ochiladi (va e'lon qilinadi). 12 soatdan uzoq cho'zilsa ham WebM bilan ochiladi.
- Eski yozuvlar (shu o'zgarishdan oldingi) avvalgidek ochiq, qayta e'lon qilinmaydi.
- Server yuklamasi: konvertatsiya bitta-bitta, `nice` bilan; server band bo'lsa (1 daqiqalik yuklama > yadrolarning 70%) kutadi
  (`TRANSCODE_MAX_LOAD_RATIO`), lekin yozuv 2 soatdan uzoq kutmaydi.
- Materiallar dars papkasida ham o'qituvchiga `converting`, o'quvchiga yopiq.

---

#### Deploy

Migratsiyalar bor (APP serverda `up -d --build` o'zi bajaradi). Tartib: **avval APP, keyin MEDIA** (yozuv va konvertatsiya MEDIA'da ishlaydi va yangi
maydonlarni yozadi).

Yangi doimiy vazifa: `send_payment_reminders` (`run_scheduler` o'zi oladi, APP'da).


[↑ Mundarija](#mundarija)

---

## BACKEND_TRELLO_VAZIFALAR_2026-11-18

> Avvalgi fayl: `BACKEND_TRELLO_VAZIFALAR_2026-11-18.md`

### Trello "Yolup" doskasi: ochiq vazifalar, kod va serverga solishtirilgan (2026-11-18)

> **Yangilanish (kechqurun):** bu hujjat ertalabki holatni ko'rsatadi. Keyin email ulandi va ishlayapti, parolni emailga kod bilan tiklash qilindi, AI rasm xatolari tuzatildi. Hozirgi holat uchun [BACKEND_TRELLO_HOLAT_2026-11-18.md](#backend_trello_holat_2026-11-18) ga qarang. Shu hujjatdagi "AI xatolari QA sinovdan" degan izoh **noto'g'ri** edi: sabab productiondagi OpenAI kalitining muddati tugaganligi (HOLAT hujjatida).

Doska: https://trello.com/b/AzQSD2X3/yolup. O'qildi: **19 ta ochiq karta** (thinking 4, Todo 7, Processing 4, Testing 3, integration 1). **Done** ustunidagi 45 karta
nazorat uchun ko'rildi, ularga tegilmadi. Kartalarda izoh (comment) yo'q, faqat sarlavha, tavsif va 4 ta skrinshot bor.

Har bir karta uchun: backend kodini o'qidim, productionda (APP server) faqat o'qish so'rovlarini bajardim, frontendning `main` shoxi (`0df424b`) bilan solishtirdim.
**Hech narsa o'zgartirilmadi, deploy qilinmadi.** Quyida "tekshirildi" deganim kod yoki serverdan ko'rganim, "taxmin" deganim tekshirilmagan.

#### Umumiy ko'rinish

| # | Karta (ustun) | Holat | Kim |
|---|---|---|---|
| 1 | homeworkda image ... AI ga jo'natish (Todo) | **Haqiqiy backend ish.** Testda 3 ta xato tasdiqlandi | Backend |
| 2 | firebase dan notification kelishdi to'g'irlash (Todo) + firebase dan olish (integration) | **Haqiqiy backend ish** + sizdan Firebase fayli kerak | Backend + siz |
| 3 | change password (Todo) | **Hozir productionda parolni tiklash ishlamayapti** (SMS ulanmagan). Qaror kerak | Backend + siz |
| 4 | chat vastanavit qlish (thinking) | Zaxira 14 kun saqlanadi. Qaror kerak | Siz + backend |
| 5 | tolov qism balance (Todo) | Tekshirdim, 4 ta kamchilik topdim | Backend |
| 6 | Homework check da AI ni ko'rib berish (Processing) | 1-band bilan birga. Alohida xato topilmadi | Backend |
| 7 | Homework price arzon qilish (thinking) | Narx o'lchanmayapti, avval o'lchash kerak | Backend |
| 8 | Meeting permission (Processing) | **Backend 10-noyabrda tayyor.** QA qoldi | Front QA |
| 9 | spam berish adminga (Processing) | **Backend tayyor, frontend ulangan.** 1 ta ochiq shikoyat turibdi | Admin |
| 10 | video qotib qoldi (Processing) | Serverda sabab ko'rinmadi. Aniq dars kerak | Front + siz |
| 11 | homework (Testing) | Ikkala tomon tayyor, QA qoldi | QA |
| 12 | homeworkcheck (Testing) | Backend tayyor (10-noyabr), QA qoldi | QA |
| 13 | Darsga o'qituvchi kirdi ... (Testing) | **Backend tayyor** (`3cafa7c`) | QA |
| 14 | vazifa berishda (Todo) | Faqat frontend (matn yorlig'i) | Front |
| 15 | Doska (Todo) | Faqat frontend | Front |
| 16 | Qo'lda test yozish imkonini ko'rish (Todo) | **Imkon bor.** Havola quyida | Javob berish |
| 17 | tech padeshka togirlash (thinking) | Tavsif yo'q: "xali idea kere" | Siz |
| 18 | image yuborish qism qande qlamiz (thinking) | Hozirgi holat yozildi, qaror kerak | Siz |

(19-karta, integration ustunidagi "firebase dan olish kere notification uchun", 2-bandga qo'shilgan.)

---

#### 1. homeworkda image qismini encode/decode qilib AI ga jo'natish

**Karta:** "homeworkda image qismdi xammasini encode decode qilish kere ai ga jonatishdan oldin va ai ga jonatish kere boladi" (Backend, Todo, Qadamov Nursulton).

**Hozir qanday:** AI ichki OpenAI orqali ishlaydi (`mode=engine`, model `gpt-4o-mini`, productionda tekshirildi). Rasm JPEG'ga o'tkaziladi
(uzun tomoni 2000 px gacha), PDF/DOCX matni olinadi. Skanerlangan PDF'dan sahifa rasmlari olinadi.
Kod: [apps/homework/ai_grader.py](apps/homework/ai_grader.py:145) (`student_work`, `_jpeg`, `_pdf_images`).

**Topilgan xatolar** (1–3 ni kichik test bilan tasdiqladim, 4–6 ni kodni o'qib topdim):

| # | Xato | Natija |
|---|---|---|
| 1 | **Telefondan olingan rasm yonbosh bo'lib ketadi.** EXIF aylantirish (`exif_transpose`) yo'q. Test: EXIF=6 bilan 400×200 rasm kirdi, AI ga 400×200 (yonbosh) chiqdi, to'g'risi 200×400 bo'lishi kerak edi | Qo'lyozma rasmini AI yonboshdan o'qiydi, ball noto'g'ri yoki "o'qib bo'lmadi" |
| 2 | **Doskada yechilgan ish: faqat 6 sahifagacha AI ga boradi.** Doska 20 sahifagacha bo'ladi ([board.py](apps/homework/board.py:23)), AI ga `MAX_IMAGES = 6` ([ai_grader.py](apps/homework/ai_grader.py:32)). Test: 8 sahifali doska PDF'dan AI ga **6** ta ketdi | 7–20-sahifalar baholanmaydi, hech qanday ogohlantirishsiz |
| 3 | **Qo'shimcha fayllar AI ga umuman ketmaydi.** `student_work` faqat birinchi faylni o'qiydi (`submission.file`), 2–5-fayllar (`SubmissionFile`) e'tiborsiz | O'quvchi 3 ta rasm yuklasa, AI faqat birinchisini ko'radi |
| 4 | **Word (.docx) ichidagi rasmlar olinmaydi.** Faqat matn va jadval o'qiladi ([material_text.py](apps/quizzes/material_text.py:39)) | Qo'lyozma rasmlarini Word'ga qo'ygan o'quvchining ishi "matn yo'q" bo'ladi |
| 5 | **Matnli PDF ichidagi rasmlar olinmaydi.** PDF'da biroz matn bo'lsa, rasm tarmog'iga o'tilmaydi | Aralash PDF (sarlavha matn + yechim rasm) faqat matn bilan baholanadi |
| 6 | **iPhone `.heic` qabul qilinmaydi** ([rules.py](apps/homework/rules.py:6)); o'qituvchining vazifa shartidagi rasm ham AI ga berilmaydi ([_task_text](apps/homework/ai_grader.py:94)) | HEIC xato beradi; shart rasmda bo'lsa AI savolni ko'rmaydi |

**Qilinadigan ish (men):**
1. `ImageOps.exif_transpose` qo'shish (1-xato).
2. Hamma topshirilgan fayllarni (asosiy + qo'shimcha) AI ga yig'ish; rasmlar sonini `MAX_IMAGES` dan oshganda sahifalarni kichraytirib/siyraklashtirib sig'dirish va qaysi sahifa tashlab ketilganini natijaga yozish (2–3-xato).
3. DOCX va aralash PDF dan rasmlarni ajratish (4–5-xato).
4. `.heic` ni qabul qilib JPEG'ga o'tkazish (kutubxona qo'shiladi: `pillow-heif`) va vazifa sharti rasmini AI ga berish (6-xato).
5. Har biriga test.

**Narx haqida ogohlantirish:** rasm soni oshsa AI narxi oshadi (7-band). Shu sababli 2-band bilan birga hajm cheklovi (sahifa kichraytirish) kerak.

**Savol:** doskada 20 sahifa bo'lsa hammasini AI ga berishni xohlaysizmi (qimmat) yoki cheklov (masalan 10) qolsinmi?

**Boshqa kuzatuv (production):** 15 ta topshirishdan 5 tasida `AI baholay olmadi` xatosi bor. Men ularni avval "QA sinov vazifasi" deb izohlagandim, bu NOTO'G'RI: asl sabab OpenAI kalitining muddati tugaganligi (qarang HOLAT hujjati). 4 tasi "QA Test Vazifa" nomli, 1 tasi `kontrakt_kamron.pdf` (2 urinishdan keyin). Oxirgisining aniq sababini log'dan topa olmadim (taxmin: PDF matni vazifaga aloqasiz bo'lgani).

---

#### 2. Firebase / bildirishnomalar (karta "firebase dan notification kelishdi togirlash kerak" + integration kartasi "firebase dan olish kere notification uchun")

**Production holati (tekshirildi):**
- **Veb push:** VAPID kalitlari bor, lekin **bitta ham obuna yo'q** (`PushSubscription` = 0). Frontend obunani faqat sozlamalardagi tugma orqali yoqadi (frontend: `src/modules/notification/model/use-push-notifications.ts`), hech kim yoqmagan.
- **Mobil push (FCM):** 13-noyabrda **bitta iOS qurilma** (app 0.1.0, o'qituvchi) token yuborgan, lekin `GOOGLE_APPLICATION_CREDENTIALS` / `FCM_PROJECT_ID` bo'sh. Shuning uchun [send_mobile_push](apps/notifications/services.py:374) jim o'chirilgan: token saqlanadi, telefonga hech narsa bormaydi.

**Kodda topilgan xatolar (ular Firebase bo'lmasa ham to'g'rilanadi):**

| # | Xato | Qayerda |
|---|---|---|
| 1 | **Sarlavha "Fokus"** (eski nom). Tizim bildirishnomalari uchun `title` bo'sh qaytadi va standart `'Fokus'` chiqadi. Ro'yxatdagi sarlavha (`KIND_TITLES`, masalan "Dars yozuvi tayyor") push'da ishlatilmaydi | [services.py:274](apps/notifications/services.py:274), [:374](apps/notifications/services.py:374) |
| 2 | **Veb push matnida HTML teglar qoladi.** Mobil push `strip_html` qiladi, veb push esa `description[:200]` ni to'g'ridan-to'g'ri yuboradi | [services.py:289](apps/notifications/services.py:289) |
| 3 | **Veb push so'rov ichida ketma-ket yuboriladi** (har obunaga alohida, to'xtab). Obuna ko'payganda xabar yuborish sekinlashadi | [services.py:294](apps/notifications/services.py:294) |
| 4 | **Veb push bosilganda faqat dars ochiladi.** `sw.js` faqat `link_type=lesson` ni taniydi, chat/vazifa/to'lov bosilsa bosh sahifa ochiladi (frontend, `public/sw.js`) | frontend |

**Siz qilishingiz kerak (integration kartasi):** Firebase Console → Project settings → Service accounts → "Generate new private key" (JSON fayl) va `FCM_PROJECT_ID`.
Faylni serverga qo'yaman (`.env` va `docker-compose.app.yml` dagi izohli qator), keyin 13-noyabrdagi iOS qurilmaga `push/test` bilan sinov yuboramiz.

**Qilinadigan ish (men):** 1–3-xatolar (sarlavha, HTML tozalash, push'ni fon oqimiga o'tkazish) va testlar. **Frontend:** 4-xato va veb push'ni birinchi kirishda taklif qilish (hozir yashirin sozlama).

---

#### 3. Parolni o'zgartirish: "email ga code yuboradigan qilsak yaxshi bo'lardi"

**Eng muhim topilma:** parolni tiklash va 2FA **faqat SMS** orqali ishlaydi ([password_reset_request](apps/accounts/services.py:236)), productionda esa SMS **ulanmagan**
(`SMS_BACKEND` bo'sh, `ESKIZ_EMAIL` yo'q). Demak **hozir "parolni unutdim" productionda 503 xato beradi**, foydalanuvchi parolini tiklay olmaydi.

**Email ham ulanmagan:** `EMAIL_HOST` bo'sh, `mailer.configured() = False`. Bundan tashqari 21 foydalanuvchidan **faqat 4 tasida email bor** (19 tasida telefon).

**Variantlar:**

| Variant | Ish | Cheklov |
|---|---|---|
| A. SMS (Eskiz) ulash | Eskiz hisobi va parol; kod tayyor, faqat `.env` | Pulli, Eskiz shablon tasdig'i kerak |
| B. Email orqali tiklash qo'shish | Men yozaman: `password/reset/request` ga `email` varianti (3 qadam bir xil). Tayyor infratuzilma bor (`otp.issue_email`, `mailer`) | SMTP kerak (siz bering), 21 dan 4 foydalanuvchida email bor, qolganlarga ishlamaydi |
| C. Ikkalasi | Telefon bo'lsa SMS, bo'lmasa email | Ikkalasi sozlanishi kerak |

**Tavsiya:** B ni boshlash (karta ham shuni so'raydi) va A ni parallel hal qilish. B uchun sizdan: SMTP ma'lumotlari (Gmail ilova paroli, Brevo/Resend yoki o'z domeningiz pochtasi).
**Savol:** karta "change password" desa ham, ikkala holat kerakmi: (1) kirgan foydalanuvchi parolni almashtirishi (hozir joriy parol bilan ishlaydi, bu tayyor) va (2) parolni unutganlar uchun tiklash? Men (2) deb tushundim.

---

#### 4. "chat vastanavit qlish" (thinking): chatni tiklash, zaxira necha oy

**Tavsifda:** "Rezerv qancha oygacha olib qoyisb".

**Hozir:**
- Xabarni o'chirish **yumshoq** (`deleted_at`), baza qatori qoladi: productionda 140 xabardan 14 tasi o'chirilgan. **Tiklash (restore) endpointi yo'q** va o'chirilgan xabarlarni tozalash ham yo'q.
- **Bazaning zaxirasi bor:** har kecha 03:30 da [backup.sh](deploy/new/backup.sh) nusxa oladi va MEDIA serverga ko'chiradi (ikkala serverda 4–17-noyabr fayllari bor, tekshirildi).
  **Lekin 14 kundan eskisi o'chiriladi** (`-mtime +14`, [backup.sh:21](deploy/new/backup.sh:21)).
- Bitta nusxa hozir ~1,8 MB. 6 oy kunlik saqlash ~0,3 GB, 12 oy ~0,7 GB: disk (251 GB, 6% band) uchun muammo emas.
- Haqiqiy tiklashni sinab ko'rilganmi, bilmayman (SERVER_SOZLASH.md uni tavsiya qiladi).

**Savollar (qaror sizniki):**
1. "Tiklash" nima: (a) foydalanuvchi o'chirgan xabarni qaytarish (kimdir xato o'chirdi), yoki (b) butun bazani tiklash (falokat)?
2. (b) uchun taklifim: kunlik 14 kun + **haftalik 6 oy** + oylik 12 oy saqlash. Nusxalar kichik, qo'shimcha xarajat yo'q.
3. (a) uchun taklifim: o'chirilgan xabarni 30 kun ichida o'qituvchi/admin qaytara olsin (`deleted_at` ni tozalash, endpoint + xona xabarlari yangilanishi), 30 kundan keyin tozalansin.

---

#### 5. "tolov qism balance di check qib chiqish kerak"

Bu tekshiruv kartasi. To'lov mantig'i ([payments.py](apps/lessons/payments.py), [progress.py](apps/lessons/progress.py)) o'qildi va testlari bor. Topilgan 4 narsa:

1. **Eslatma kechasi ketishi mumkin.** `send_payment_reminders` har soat ishlaydi, soat oralig'i cheklovi yo'q ([payments.py:65](apps/lessons/payments.py:65)). Muddatdan 3/5/7 kun qolgan kunning birinchi ishga tushishi ~00:00–01:00 (Asia/Tashkent) bo'ladi. O'quvchi va ota-ona yarim tunda bildirishnoma oladi (taxmin: kod bo'yicha; productionda vaqtini ko'rmadim).
2. **Eslatma "yuborildi" deb belgilanadi, xabar ketmasa ham.** Log yozuvi xabardan oldin yaratiladi ([payments.py:91](apps/lessons/payments.py:91)); xabar yuborishda xato bo'lsa, qayta urinilmaydi.
3. **"To'lamagan" faqat joriy oy bo'yicha** ([unpaid_counts_for_teacher](apps/lessons/payments.py:47)). Oktabrni to'lamagan, noyabrni to'lagan o'quvchi hech qayerda qarzdor ko'rinmaydi.
4. **Qarz (balans) tushunchasi yo'q.** `CoursePayment` faqat "shu oy to'langan" belgisi; summa ixtiyoriy. Kartaning o'zi ("balance") shu degan bo'lishi mumkin, Done ustunidagi "balance qism" kartasi "kim to'lamagan" ko'rinishini so'ragan, u bajarilgan.

**Qilinadigan ish:** 1–2 ni to'g'rilash (eslatma 09:00–20:00 oralig'ida, yuborilgandan keyin belgilash). 3 uchun savol: o'tgan oylar qarzi ko'rinsinmi (masalan, "2 oy qarz")?

---

#### 6. "Homework check da AI ni ko'rib berish kerak"

Alohida karta, lekin mazmuni 1-band bilan bir xil: AI tekshiruvi to'g'ri ishlashi. Productionda AI ishlaydi, hozir tiqilib qolgan topshirish yo'q
(`checking` = 0). Topilgan xatolar 1-bandda. Qo'shimcha: bitta topshirishning `ai_result`i ballsiz (2026-10-15, rasm vazifaga aloqasiz bo'lgani uchun, AI to'g'ri `null` bergan).

---

#### 7. "Homework price ni arzon qlish yollarini korish kerak" (thinking)

**Hozir narx o'lchanmaydi.** AI chaqiruvi tokenlari faqat INFO log'ga yoziladi ([llm.py:175](apps/quizzes/llm.py:175)); serverning 14 kunlik log'ida topilmadi,
bazada narx hisobi yo'q. Shuning uchun "qanchaga tushdi" deb aytolmayman.

**Narx omillari (kodda ko'rinadi):** rasm bo'lsa qimmatlashadi (har rasm 2000 px gacha, `detail` ko'rsatilmagan); 6 tagacha rasm; 30 000 belgigacha matn;
xato bo'lsa 3 martagacha qayta urinish ([services.py:46](apps/homework/services.py:46)); `gpt-4o-mini` allaqachon arzon model.

**Taklif (tartib bilan):**
1. Avval o'lchash: har AI chaqiruvining tokenini bazaga yozish (`ai_tokens`, `ai_cost`) va admin uchun xulosa. 1 kun ish.
2. Keyin tejash: rasm tafsilotini `detail: low/auto` bilan sinash (sifat bilan solishtirib), rasmlarni 2000 px dan 1400 px ga tushirish, matnli PDF'ni rasmga aylantirmaslik, qayta urinishlarni kamaytirish.
3. O'qituvchiga `ai_check` ni vazifa bo'yicha o'chirish imkoni allaqachon bor (`ai_check` maydoni).

---

#### 8. "Meeting permission" (Processing): backend tayyor

**Karta:** mikrofon/kamera ruxsati bir marta berilsa, keyin yana yopiq bo'lishi va 2-marta yana so'rashi kerak; speaking club'larda hammaga mikrofon ochiq (true/false).

Backend 10-noyabrda bajarilgan (`6aa7b53`): "hammani o'chirish ruxsatni qaytarib oladi", `release-media` (o'quvchi o'zi o'chirsa ruxsat qaytadi), dars bo'yicha `open_mic` / `open_camera` ochiq rejim
([BACKEND_YANGILANISHLAR_2026-11-10.md](#backend_yangilanishlar_2026-11-10), [FRONTEND_YANGILANISHLAR_2026-11-12_2.md](#frontend_yangilanishlar_2026-11-12_2)).
Karta o'sha kundan oldin (9-noyabr) yozilgan va Processing'da qolib ketgan. **Qoldi:** frontend QA (3 stsenariy: bir marta ruxsat → o'chirish → qayta so'rash; "hammani o'chirish" → ruxsat qaytadi; ochiq rejim yoqilganda kirgan yangi o'quvchi).

---

#### 9. "spam berish adminga borishi kerak ..." (Processing): tayyor

Oqim to'liq: o'quvchi/o'qituvchi shikoyat yuboradi → barcha adminlarga bildirishnoma ([spam.py](apps/chat/spam.py:71)) → admin ro'yxat (`GET /admin/reports/`) → `resolve` / `dismiss` / `unblock`. Frontend ulangan.
**Diqqat:** productionda **1 ta shikoyat "open" holatida turibdi**, hech kim ko'rmagan. Kartani yopishdan oldin admin ekranini ochib shuni ko'rish kerak.

---

#### 10. "video qotib qoldi" (Processing)

Skrinshotda o'qituvchi kamerasi ("Siz - ustoz") qotgan, tor (telefon o'lchamidagi) oynada. Mijoz salomatlik hisobotlari (`client-health`, productionda 138 ta) bo'yicha:

- Oxirgi 6 kunda faqat 3 ta past FPS hisoboti (hammasi o'qituvchi): **ekran ulashish** treki 1–2 fps, `quality_limitation = none`, CPU va tarmoq cheklovi yo'q (16 va 10 yadroli kompyuter, "excellent" ulanish).
  Bu **statik ekranda normal** (ekran o'zgarmasa kodlagich 1 fps ga tushadi), lekin tomoshabin uchun "qotgan"dek ko'rinadi.
- Kamera qotishi uchun serverda dalil topilmadi. 12-noyabrdagi tahlil ([FRONTEND_QOTISH_TAHLILI_2026-11-12.md](#frontend_qotish_tahlili_2026-11-12)) tavsiyalari frontendda qo'llangan (720p/15 fps, simulcast o'chiq).

**Kerak:** qotish bo'lgan **dars va soat** (men LiveKit logi va hisobotlarni shu soat bo'yicha ko'raman) va qotgan joy: kamerami yoki ekran ulashishmi. Shu bo'lmasa aniq vazifa qilib bo'lmaydi.

---

#### 11–13. Testing ustunidagi kartalar

| Karta | Holat |
|---|---|
| **homework** ("natijani ko'rish ishlamayapdi", skrinshotda "Baho yo'q" + "Tekshirilmoqda") | Backend `ai_state` (`checking/unscored/failed/ready`) qo'shgan (`fccbdb7`), frontend natija oynasi uni ishlatadi (frontend: `src/modules/homework/ui/homework-result-dialog.tsx`). Skrinshotdagi holat eski. **QA:** 4 holatni tekshirish |
| **homeworkcheck** ("file yuklash optional bo'lsin") | Backend: fayl majburiy emas, faqat matn javob ham topshiriq (`9278bb5`). Frontend nusxasidagi eski matn yo'q. **QA:** faqat izoh bilan topshirish |
| **Darsga o'qituvchi kirdi va yubordi "hammaga qo'shil"** | Backend: o'qituvchi darsni boshlagach, o'quvchi rejalashtirilgan vaqtdan oldin ham kira oladi (`3cafa7c`, [FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](#frontend_javob_darsga_taklif_2026-11-16)). **QA:** o'quvchi "aylanib turgan yopiq dars" ko'rmasligini tekshirish |

---

#### 14–16. Frontend kartalari va savol

- **"vazifa berishda" (14):** skrinshot: "Yangi vazifa" oynasida matn maydoni (description) ajralib turmaydi. Faqat frontend (yorliq/sarlavha).
- **"Doska" (15, RedZon):** matn o'lchami va chiziq/yo'naltiruvchi. Backend tayyor: matn o'lchami 12–48, qo'shimcha `w` kengligi, `line`/`rect`/`ellipse`, element tahrirlash (`update_stroke`) ([board/services.py:184](apps/board/services.py:184)). Agar frontend yuborgan qiymat rad etilsa, aniq `400` xabarini bering, men ko'raman.
- **"Qo'lda test yozish imkonini ko'rish kerak ... link berib qo'yila" (16): imkon BOR.**
  - Backend: `POST /api/v1/quizzes/` savollar bilan qo'lda test yaratadi (`quiz.create` ruxsati); `GET /quizzes/template/` shablon.
  - Frontend: guruh ishchi maydonidagi `AddQuizDialog` (frontend: `src/modules/quiz/ui/quiz-create-dialog.tsx`), `src/widgets/group-workspace/group-workspace.tsx` ichida; tahrirlash sahifasi `/teacher/workspace/tests/{id}/edit`.
  - Eslatma: test yaratish hamma o'qituvchi uchun ochiq (admin o'qituvchi bo'yicha boshqaradi, `can_create_tests`).
  Izohdagi "link" so'ralgan: yuqoridagi ro'yxat javob bo'ladi; ekran nomini Trello'ga yozing.

---

#### 17–18. Qaror kartalari (sizdan javob kerak)

- **"tech padeshka togirlash kerak boladi" ("xali idea kere"):** "padeshka" nimani bildiradi? Taxminim: texnik yordam (podderzhka). Agar shu bo'lsa, `support/tickets` (murojaat yuborish, javob, yopish) allaqachon bor ([apps/support](apps/support/urls.py)). Nimasini to'g'rilash kerak: ekranmi, javob tezligimi, Telegram'ga xabarmi?
- **"image yuborish qism qande qlamiz":** chatda rasm yuborish **hozir hamma uchun ochiq** (yozish huquqi bor har kim, o'quvchi ham; rasm turlari jpg/png/gif/webp, qo'shimcha cheklov yo'q). E'lon rejimidagi guruhda faqat o'qituvchi yozadi. Variantlar:
  (a) hozirgidek, (b) faqat o'qituvchi, (c) o'qituvchi sozlaydi (guruh bo'yicha "o'quvchilar rasm yuborsin" tugmasi). Tavsiyam (c), chunki spam va nomaqbul rasm xavfi bor, ammo ba'zi guruhlar (masalan matematika) o'quvchi rasmisiz ishlay olmaydi.

---

#### Tavsiya etilgan tartib

1. **3-band (parol tiklash):** productionda hozir buzuq. Sizdan: SMTP yoki Eskiz hisobi. Men: email orqali tiklash.
2. **1-band (AI + rasm):** haqiqiy xatolar, sizning ruxsatingiz bilan boshlayman (tahminan 1–1,5 kun, testlar bilan).
3. **2-band (bildirishnoma):** sarlavha/HTML/fon yuborish hozir; Firebase fayli kelgach FCM.
4. **5-band (to'lov):** eslatma vaqti va log tartibi, kichik.
5. **9-band:** admin ochiq shikoyatni ko'rsin (kod emas).
6. Qolganlar sizning javobingizga qarab (4, 7, 17, 18-bandlar, 10-banddagi dars vaqti).

#### Tekshirilmagan narsalar

- OpenAI narxi va haqiqiy token sarfi (o'lchanmaydi).
- `kontrakt_kamron.pdf` AI xatosining sababi.
- 4–5-xatolar (DOCX/PDF ichidagi rasm) kod bo'yicha, testsiz. 6-xato (HEIC) ham.
- Backup'ni qayta tiklash hech qachon sinalganmi.
- Frontend QA (8, 11–13-bandlar) men tomondan qilinmadi; faqat kod va hujjat bo'yicha.
- Kartalardagi skrinshotlar faqat 4 tasi ko'rildi (boshqa kartalardagi rasmlar Done ustunida).


[↑ Mundarija](#mundarija)

---

## BACKEND_TRELLO_HOLAT_2026-11-18

> Avvalgi fayl: `BACKEND_TRELLO_HOLAT_2026-11-18.md`

### Trello "Yolup": nima qilindi, nima tekshirildi, nima qoldi (2026-11-18, kechqurun)

Bu [BACKEND_TRELLO_VAZIFALAR_2026-11-18.md](#backend_trello_vazifalar_2026-11-18) ning davomi: o'sha hujjatdagi 19 ta ochiq karta bo'yicha holat.

**Muhim:** Trello'dan kartalarni bugun ertalab o'qiganman. Hozir qayta o'qimoqchi bo'lsam, ichki brauzerda Trello seansi yana tugagan (HTTP 401), shuning uchun
ertalabdan keyin qo'shilgan yoki ko'chirilgan kartalarni ko'rmadim. Ular bo'lsa ayting yoki Trello'ga kirib bering, shunda solishtiraman.

Belgilar: **DEPLOY** = serverda ishlayapti; **KODDA** = yozildi va testlandi, serverga hali chiqarilmagan; **KUTYAPMAN** = sizdan narsa kerak.

#### Qisqa javob

| Savolingiz | Javob |
|---|---|
| Hammasini qildingmi? | **Yo'q, 19 tadan hammasini emas.** 3 tasi serverda ishlayapti, 4 tasi kodda tayyor (deploy kutadi), 5 tasi avvaldan tayyor edi (faqat QA), 3 tasi faqat frontend ishi, 4 tasi sizdan narsa kutadi. Har birining sababi quyida. |
| To'g'ri qildingmi? | Qilganlarimni testlar va serverda tekshirdim. Tekshirib bo'lmaganlarini alohida yozdim. |
| Qolganini ham qildingmi? | Qila oladiganlarimni qildim. Qolganlari uchun nima kerakligini aniq yozdim. |

#### 1. Bajarilgan, DEPLOY qilingan, tekshirilgan

| Karta | Nima qilindi | Qanday tekshirildi |
|---|---|---|
| **homeworkda image ... AI ga jo'natish** + **Homework check da AI ni ko'rib berish** | 6 ta xato to'g'rilandi: EXIF aylantirish, hamma fayllar, token byudjetiga sig'adigan sahifalar (hozirgi modelda ~3 ta, 9.6-band), Word/PDF ichidagi rasmlar, vazifa sharti rasmi, iPhone HEIC. Commit `d467691`. [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](#frontend_javob_ai_rasm_2026-11-18) | 24 ta yangi test; serverdagi konteynerda HEIC→JPEG haqiqiy ishladi. **Haqiqiy OpenAI bilan tekshirib BO'LMADI: productiondagi kalit muddati tugagan** (9-bo'lim) |
| **change password** (email ga kod) | Ro'yxatdan o'tishda tasdiqlangan email, email bilan kirish, parolni emailga kod bilan tiklash, profilda email qo'shish. Commit `199de62`, `94bd14a`. [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](#frontend_email_kirish_va_tiklash_2026-11-18) | 47 ta yangi test; **haqiqiy Gmail orqali** serverdan kod ketdi (`sent: true`); netcup "Mail block" o'chirildi, 25/465 porti himoyalandi |
| **Zaxira: tiklashni sinash** (chat vastanavit kartasining 2-qismi) | Oxirgi kunlik nusxa vaqtinchalik bazaga **tiklandi**: qator sonlari jonli bazaga mos (21 foydalanuvchi, 140→142 xabar yangi yozuvlar sababli) | Serverda haqiqiy `pg_restore`, vaqtinchalik baza o'chirildi |

**Emailda hali ochiq qolgani (aniq):**
- Productionda **bironta ham tasdiqlangan email yo'q**, ya'ni hozir hech kim emailni tiklash orqali parolini almashtira olmaydi, avval emailini qo'shib tasdiqlashi kerak. Buning uchun frontendda "email qo'shish" oynasi kerak (yo'riqnomada bor).
- `REGISTER_REQUIRES_EMAIL` **o'chiq**. Frontend email qadamini qo'shmaguncha yoqsam, ro'yxatdan o'tish buziladi.
- Gmail ilova paroli suhbatda ochiq bo'lgani uchun almashtirilishi kerak (siz yangisini bering).

#### 2. KODDA tayyor, deploy qilinmagan (sizning "ha" ingizni kutyapti)

| Karta | Nima o'zgardi | Testlar |
|---|---|---|
| **firebase dan notification kelishdi to'g'irlash** (Firebase'siz qismi) | (a) Push sarlavhasi endi "Fokus" emas: tizim xabarlarida ro'yxatdagi sarlavha ("Dars yozuvi tayyor", "Yangi baho"), qolganida "YolUp"; (b) veb push matnidagi HTML teglar olib tashlandi; (c) veb va mobil push **fonda** yuboriladi (sekin qurilma xabar yuborishni kutdirmasin). [apps/notifications/services.py](apps/notifications/services.py) | 9 ta yangi test, mavjud push testlari o'tdi |
| **tolov qism balance check** | (a) To'lov eslatmasi faqat **09:00–20:00** (Toshkent) yuboriladi, oldin kun boshlanishi bilan, ~00:00 da ketishi mumkin edi; (b) xabar yuborilmasa "yuborildi" belgisi qolmaydi va keyingi soatda qayta uriniladi; o'quvchiga ketgan bo'lsa, ota-onaga ketmaganda o'quvchiga qayta yuborilmaydi. [apps/lessons/payments.py](apps/lessons/payments.py) | 4 ta yangi test; mavjud testlardan biri (`test_management_command_runs`) real soatga bog'liq edi, tuzatildi |
| **Homework price arzon qilish** (1-qadam: o'lchash) | Har AI baholashning token sarfi `ai_result.usage` ga yoziladi (qayta urinishlar ham hisoblanadi). Hisobot: `python manage.py homework_ai_usage --days 30`. Narx faqat tarifni bersangiz hisoblanadi (`--price-in`, `--price-out`), uni o'zim uydirmayman. [apps/homework/management/commands/homework_ai_usage.py](apps/homework/management/commands/homework_ai_usage.py) | 8 ta yangi test |
| **chat vastanavit: zaxira necha oy** | Zaxira saqlash muddati: kunlik 14 kun (oldingidek) + **haftalik ~6 oy** + **oylik ~13 oy**. Nusxa ~2 MB, jami ~0,5 GB. [deploy/new/backup.sh](deploy/new/backup.sh), [SERVER_SOZLASH.md](#server_sozlash) | skript sintaksisi tekshirildi; serverda deploydan keyin birinchi yakshanba/1-sanada ishga tushadi |

**Eslatma:** AI sarfi (token) yozilishi faqat deploydan **keyingi** tekshiruvlar uchun ishlaydi; eskilarida sarf yo'q, narxni ularga qaytarib hisoblab bo'lmaydi.

#### 3. Avvaldan tayyor edi (backend), faqat QA qoladi

| Karta | Holat |
|---|---|
| **Meeting permission** | `6aa7b53` (10-noyabr): hammani o'chirish ruxsatni qaytaradi, `release-media`, `open_mic/open_camera`. Frontend QA kerak |
| **spam berish adminga** | Oqim to'liq. Productionda **1 ta shikoyat "open" holatida**, admin ko'rishi kerak |
| **homework** (natijani ko'rish), **homeworkcheck** (fayl ixtiyoriy), **Darsga o'qituvchi kirdi** | Backend tayyor (`fccbdb7`, `9278bb5`, `3cafa7c`). Frontend QA kerak |

Bu kartalarning backend qismi uchun butun test to'plami natijasi: **butun backend test to'plami: 2060 ta test, hammasi o'tdi** (9.6–9.8 tuzatishlarigacha bo'lgan hamma o'zgarishlar bilan, 736 soniyada)

#### 4. KUTYAPMAN: sizdan nima kerak

| Karta | Nima kerak | Nega men qila olmayman |
|---|---|---|
| **firebase dan olish kere** (integration) + mobil push | Firebase **service account `.json`** (Project settings → Service accounts → Generate new private key) va **Project ID**. Faylni chatga emas, fayl yo'lini yozing. iPhone uchun APNs kaliti Firebase'ga yuklanishi kerak | Kalitsiz FCM ulanmaydi; skrinshotdagi `google-services.json` serverga kerak emas |
| **chat vastanavit qlish** | Qaysi "tiklash"? (a) o'chirilgan xabarni qaytarish, (b) falokatdan keyin butun bazani tiklash. (b) tayyor (yuqorida). (a) uchun taklif: 30 kun ichida o'qituvchi/admin qaytara oladi | Mazmuni noaniq, taxmin bilan funksiya yozmadim |
| **image yuborish qism qande qlamiz** | Variant: (a) hamma, (b) faqat o'qituvchi, (c) guruh bo'yicha o'qituvchi sozlaydi. Tavsiya (c) | Mahsulot qarori |
| **tech padeshka togirlash** | "padeshka" nima? Tavsif: "xali idea kere" | Spetsifikatsiya yo'q |
| **video qotib qoldi** | Qotish bo'lgan **dars va soat**, qotgan joy: kamerami yoki ekran ulashishmi | Serverda sabab ko'rinmadi: CPU/tarmoq cheklovi yo'q, FPS 1–2 faqat ekran ulashishda (statik ekranda normal) |
| **tolov qism: o'tgan oylar qarzi** | O'tgan oylar qarzi ko'rinsinmi ("2 oy qarz")? Hozir faqat joriy oy | Mahsulot qarori |
| **change password** (email majburiy qilish) | Frontend email qadamini qo'shgach: `REGISTER_REQUIRES_EMAIL=1` va muhlat sanasi (tavsiya: 14 kun) | Frontendsiz yoqsam ro'yxatdan o'tish buziladi |

#### 5. Frontend kartalari (backendda qiladigan ish yo'q)

- **vazifa berishda**: "description" yorlig'i ko'zga ko'rinsin (skrinshot bor).
- **Doska** (RedZon): matn o'lchami va chiziq yo'naltiruvchisi. Backend tayyor (matn 12–48, line/rect/ellipse, tahrirlash). Frontend yuborgan qiymat rad etilsa, `400` xabarini bering.
- **Qo'lda test yozish imkonini ko'rish**: **imkon bor** (`POST /quizzes/`, frontendda `AddQuizDialog`), javobi [BACKEND_TRELLO_VAZIFALAR_2026-11-18.md](#backend_trello_vazifalar_2026-11-18) 16-bandda.
- Frontendga qo'shimcha ishlar (yo'riqnomalarda): veb push'ni birinchi kirishda taklif qilish va `sw.js` da chat/vazifa/to'lov bosilganda to'g'ri sahifani ochish (hozir faqat dars), HEIC `accept`, AI natijasida `skipped_images`, email qadamlari.

#### 6. Eng muhim xavflar (aniq)

1. **Production hozir:** parolni tiklash faqat **emaili tasdiqlanganlar** uchun ishlaydi, va hozir tasdiqlangan email nolta. Ya'ni parolini unutgan foydalanuvchi hozircha baribir tiklay olmaydi, frontend email oynasi chiqmaguncha.
2. **Firebase'siz** mobil push ishlamaydi (iOS qurilma token yuborgan, lekin xabar bormaydi).
3. **Veb push**: obunalar nolta, chunki frontend uni faqat yashirin sozlamada taklif qiladi, deploy bunga ta'sir qilmaydi.

#### 7. Tekshirilmagan (halol ro'yxat)

- Haqiqiy OpenAI bilan AI baholash (rasmlar, narx), faqat soxta javob bilan.
- To'lov eslatmasining haqiqiy productiondagi vaqti (kun soati), faqat testda.
- Veb/mobil push haqiqiy qurilmada (testda soxta yuborish).
- Frontend QA (meeting, homework, homeworkcheck, dars kirishi): faqat kod va testlar bo'yicha.
- Trello'ning ertalabdan keyingi o'zgarishlari (seans tugagan).

#### 8. Qayta tekshiruv (so'rovingizdan keyin) va to'g'rilangan kamchiliklar

Oldingi hisobotni qayta tekshirdim. Topilgan va to'g'rilangan:

| Kamchilik | Holat |
|---|---|
| Email xabarlari (8 ta yangi matn) faqat o'zbekcha edi, ru/en foydalanuvchi o'zbekcha xato ko'rardi | **Tuzatildi:** ru va en tarjimalar qo'shildi, 5 ta test bilan tekshirildi. Deploydan keyin ishlaydi |
| Email oqimi productionda faqat "kod yuborildi" darajasida tekshirilgan edi | **To'liq sinab ko'rildi:** productionda haqiqiy Gmail bilan ro'yxatdan o'tish → email bilan kirish → parolni emailga kod bilan tiklash → yangi parol bilan kirish, 10 qadamning hammasi o'tdi. Sinov akkaunti bekor qilinadigan tranzaksiyada edi: bazada qolmadi |
| "Push fonda yuboriladi" degan gapim faqat testga tayangan edi | Productionda `BACKGROUND_ASYNC=True` ekani tekshirildi |
| Chiquvchi 25/465 himoyasi qayta ishga tushganda saqlanishi | `block-smtp-egress` xizmati `enabled` va `active`. Server qayta ishga tushirib sinalmadi (production, xavfli) |
| Admin panelda `email_exempt` ko'rinmasdi | Qo'shildi (foydalanuvchi sahifasida `email_verified` va `email_exempt`) |

**Hali ochiq (aniq):**
- **Bola akkauntlari:** `email_exempt` faqat YANGI yaratilganlarda qo'yiladi. Eskilarini avtomatik aniqlab bo'lmadi: productionda bola yaratilganini ko'rsatadigan audit yozuvi yo'q (0 ta), mavjud 5 ta "ro'yxatdan o'tmagan" o'quvchi hisobi test/seed ko'rinishida. `REGISTER_REQUIRES_EMAIL` yoqilishidan oldin admin kerakli hisoblarni panelda belgilashi kerak.
- **Real foydalanuvchilar emailsiz ro'yxatdan o'tmoqda:** bugun 13:40 (o'qituvchi) va 13:53 (ota-ona) da yangi hisoblar ochilgan, ikkalasida email yo'q. Frontend email qadamini qo'shmaguncha shunday davom etadi.
- **Frontend QA** (meeting, homework, dars kirishi va h.k.) men tomondan qilinmagan va qila olmayman.

#### 9. Ikkinchi qayta tekshiruv: eng muhim topilma va tuzatishlar

##### 9.1. Productiondagi OpenAI kaliti MUDDATI TUGAGAN: hamma AI ishlamayapti

Productionda haqiqiy AI baholashni sinab ko'rmoqchi bo'lib, OpenAI'ga so'rov yubordim: **HTTP 401, `expired_secret_key`: "Your API key has expired. Create a new API key to continue."** Kalit mavjud (`sk-proj...`), lekin amal qilmaydi. Bu `/models` ro'yxati, model va chat so'rovi uchun ham bir xil.

- **Nima ishlamaydi:** uy vazifasini AI bilan baholash, AI test yaratish, imtihon Writing AI, Speaking ovozni matnga o'girish, matnni ovozga aylantirish (hammasi shu kalitdan).
- **Qachondan:** oxirgi muvaffaqiyatli AI natijalari: uy vazifasi 2026-10-17, AI test yaratish 2026-10-21. Keyin xatolar: 10, 13 va 17-noyabr. Aniq sana noma'lum (shu oraliqda).
- **Foydalanuvchiga ta'siri:** tizim yiqilmaydi. Topshirish qabul qilinadi va "AI baholay olmadi — o'zingiz baholang" belgisi bilan o'qituvchiga tushadi. Ya'ni o'qituvchi hamma narsani qo'lda baholayapti.
- **Men avval xato qilgan joyim:** 5 ta "AI baholay olmadi" xatosini "QA sinov vazifalari" deb izohlagan edim. Bu **noto'g'ri** edi, sabab kalit.
- **Natijada:** men yozgan AI rasm tuzatishlari (EXIF, HEIC, ko'p sahifa, Word/PDF ichidagi rasmlar) **haqiqiy OpenAI bilan hech qachon tekshirilmagan**, faqat soxta javob bilan (testlar o'tdi). Yangi kalit kelganda sinab ko'raman.
- **Sizdan kerak:** platform.openai.com → API keys → yangi kalit yarating (iloji bo'lsa muddatsiz) va oylik byudjet cheklovi qo'ying. Kalitni chatga yozishingiz mumkin, men serverdagi `.env` ga (`OPENAI_API_KEY`) yozaman va darhol haqiqiy sinovni o'tkazaman: yonbosh telefon surati va HEIC bilan.

##### 9.2. Zaxira nusxa bilan birga `.env` nusxasi MEDIA serverga ko'chib ketgan edi: o'chirildi

SMTP sozlamasini yozganimda serverdagi `.env` ning zaxira nusxasini `/var/backups/edu/` ga qo'ygan edim. Tungi `rsync` (va bugun 14:01 da men qo'lda ishga tushirgan zaxira) uni MEDIA serverning `/var/backups/edu-app/` ga ham ko'chirgan. Ikkala nusxani ham o'chirdim (ikkala serverda `env` fayli 0 ta). U yerda **faqat bir necha daqiqa** turdi va ikkala server ham sizniki; yangi sir (Gmail paroli) o'sha nusxada yo'q edi (u eski `.env` edi). Baribir tuzatildi.

##### 9.3. Zaxira skripti haqiqiy ishga tushirildi

`backup.sh` ni serverda to'liq ishga tushirdim (MEDIA nusxasi bilan): kunlik nusxa yaratildi va MEDIA'ga ko'chirildi, haftalik nusxa (`db_weekly_2026-11-15.dump`) ikkala serverda bor. Oylik nusxa 1-dekabrda avtomatik yaratiladi (bu hali kuzatilmagan).

##### 9.4. Email bor-yo'qligi javob vaqtidan bilinib qolishi mumkin edi: tuzatildi (deploy kutadi)

Men "email bazada bor-yo'qligi oshkor bo'lmaydi" degan edim, lekin faqat javob **matni** bo'yicha to'g'ri edi. Vaqt bo'yicha farq bor edi: (1) parolni tiklashda mavjud email uchun SMTP kutilardi (~1 soniya), noma'lum uchun yo'q; (2) email bilan kirishda mavjud email uchun 2 ta parol hisoblash, noma'lum uchun 1 ta. Ikkalasi tenglashtirildi: xat fonda yuboriladi, noma'lum emailda soxta parol hisoblash bajariladi. 4 ta yangi test (parol hisoblash soni barcha holatda 2). **Serverda hali yo'q.**

##### 9.5. Boshqa aniqlangan faktlar
- Productionda **hech bir kursda `payment_day` belgilanmagan** (0 ta) va to'lov eslatmalari hech qachon yuborilmagan (0 ta yozuv). Ya'ni to'lov eslatmasi funksiyasi hozir ishlatilmayapti, mening tuzatishim productionda sinab bo'lmaydi, faqat testda.
- Bugun ikki yangi foydalanuvchi emailsiz ro'yxatdan o'tgan (13:40 o'qituvchi, 13:53 ota-ona).
- Eski hujjatlardagi (`FRONTEND_EMAIL_...`, `FRONTEND_ULANMAGAN_...`, `BACKEND_TRELLO_VAZIFALAR_...`) "email ulanmagan" degan gaplar eskirgan edi, tuzatildi.

##### 9.6. Rasm tuzatishimdagi XATO topildi va to'g'rilandi: "10 sahifagacha" haqiqatda ishlamasdi

"10 sahifagacha AI ga boradi" degan gapim noto'g'ri edi. OpenAI hujjatiga ko'ra `gpt-4o-mini` uchun har bir rasm **2833 + 5667 x (512 px bo'laklar soni)** token oladi; bitta to'liq sahifa (768x1024 yoki 1536x1536) **25 501 token**. Modelning kontekst oynasi 128 000 token. Demak **4 tadan ko'p sahifa bitta so'rovga sig'maydi** (5 ta = 127 505 token, matnsiz). Eski kod (6 ta) ham, mening 10 talik chegaram ham shu sababli ko'p sahifali ishda so'rov rad etilishiga olib kelardi.
- **Tuzatish:** rasmlar endi token byudjetiga qarab tanlanadi (`HOMEWORK_AI_IMAGE_TOKEN_BUDGET`, standart 80 000: bu ~3 ta to'liq sahifa). Sig'maganlari AI ga berilmaydi va natijada `skipped_images` + ogohlantirish bo'ladi. Vazifa sharti rasmi ham byudjetdan joy oladi. Formula OpenAI'ning o'z misoli bilan tekshirildi (1536x1536 → 25 501).
- **Oqibat:** hozirgi modelda AI bitta ishdan taxminan **3 ta sahifa/surat** ko'radi. Ko'p sahifali doska yoki ko'p suratli ishlarda o'qituvchi qolganini o'zi ko'rishi shart.
- **`gpt-4o-mini` OpenAI sahifasida "Deprecated" (eskirgan) deb belgilangan** (o'chirish sanasi o'sha sahifada ko'rsatilmagan). Rasm bilan ishlashda u eng qimmat model (har sahifa ~25 500 token). Yangi kalit kelgach boshqa, rasm uchun arzonroq va yangiroq modelni (masalan gpt-4.1-mini) solishtirib ko'rishni tavsiya qilaman: `OPENAI_MODEL` `.env` da sozlanadi. Hozir buni **sinab ko'rmadim** (kalit yo'q), shuning uchun faqat tavsiya.

##### 9.7. Kirishdagi urinishlar hisoblagichi: email "ikkinchi imkoniyat" edi: to'g'rilandi

Xato kirishlar (10 ta, keyin 429) `(IP, kiritilgan matn)` bo'yicha sanalardi. Email bilan kirish qo'shilgach, bitta akkauntga login bilan 10 va email bilan 10 ta urinish mumkin bo'lib qolgan edi. Endi tasdiqlangan email bitta akkauntga tegishli bo'lsa, urinishlar o'sha akkauntning loginiga yig'iladi (katta-kichik harf variantlari ham). 4 ta test.

##### 9.8. MEDIA serverda eski kod ishlayapti: bildirishnoma tuzatishi to'liq emas

MEDIA server hali `c76a991` da (APP'da `a3fd185` va undan keyingilar). "Dars yozuvi tayyor" bildirishnomasi **MEDIA'dagi `rec`/transcoder** jarayonidan yuboriladi, shuning uchun u hali eski kod bilan ketadi: push sarlavhasi "Fokus", matnda HTML, push so'rov ichida sinxron. Bildirishnoma tuzatishi MEDIA ham yangilangandan keyingina to'liq bo'ladi. (Yangilash: faqat `rec`, `rec-cron`, `transcoder` qayta quriladi; LiveKit va Caddy tegilmaydi. Jonli dars va "converting" yozuv bo'lmaganda.)

#### 10. Deploy holati (2026-11-18, kechqurun): ikkala server `17124e3` da

| Server | Versiya | Nima qayta qurildi | Tekshirildi |
|---|---|---|---|
| APP (152.53.33.65) | `17124e3` | web, ws, cron | web `healthy`; migratsiya yo'q (0 ta yangi); haqiqiy productionda 11 ta tekshiruv, hammasi o'tdi (pastda) |
| MEDIA (152.53.0.228) | `17124e3` | `rec`, `rec-cron`, `transcoder` (LiveKit va Caddy tegilmadi, 7 kun ishlayapti) | 3 konteyner ham ishlayapti, qayta ishga tushish 0, OOM yo'q; `rec` yangi kodni ishlatyapti (`recording_ready` sarlavhasi "Dars yozuvi tayyor"); APP watchdog'i MEDIA'ni `OK` ko'ryapti; loglarda xato 0 ta |

Deploydan oldin: jonli dars 0 ta, "converting" holatidagi yozuv yo'q; migratsiya farqi yo'q, `manage.py check` toza, tarjima fayllari to'g'ri, 2060 ta test o'tgan.

**APP'da haqiqiy productionda o'tgan 11 ta tekshiruv:**
1. rasm token byudjeti 80 000; 2. `BACKGROUND_ASYNC` yoqilgan; 3. email ulangan; 4. token formulasi OpenAI misoli bilan mos (1536x1536 = 25 501);
5–7. xato xabarlari ru/en/uz tilida to'g'ri chiqadi (haqiqiy so'rov orqali); 8. push sarlavhalarida "Fokus" yo'q;
9–10. parolni tiklash: mavjud va mavjud bo'lmagan email bir xil javob oladi; javob vaqti 62 ms va 11 ms (oldin mavjud email uchun ~1 soniya, endi xat kutilmaydi; ~50 ms farq qoldi: audit yozuvi va fon vazifasini yuborish);
11. login va email bilan xato urinishlar bitta hisoblagichda (11-urinish `429`).
Sinov foydalanuvchisi bekor qilinadigan tranzaksiyada bo'ldi: bazada qolmadi.

**Hali ham tasdiqlanmagan (kalit yoki real hodisa kerak):** haqiqiy OpenAI bilan AI baholash (kalit muddati tugagan); MEDIA'dan haqiqiy yozuv tayyor bo'lganda push sarlavhasi (kod yangi, real hodisa kutilmoqda); oylik zaxira (1-dekabr); serverni qayta ishga tushirganda 25/465 himoyasi.

#### 11. Parol o'zgartirish (frontend xabari bo'yicha), APP `08c2296`

Frontend `BACKEND_PAROL_OZGARTIRISH.md` yubordi; ikkala kamchilik ham haqiqiy ekani tasdiqlandi va tuzatildi (batafsil: [FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18.md](#frontend_javob_parol_ozgartirish_2026-11-18)).

- Avtomatik ochilgan rol akkauntiga endi manba akkaunt paroli beriladi (oldin tasodifiy, hech kim bilmasdi). Productionda shunday 4 akkaunt bor edi (teacher1_student, krv006_student, teacher1_parent, mukhammaddiyor_parent): `sync_provisioned_passwords` avval sinov rejimida ko'rsatildi (4 ta, 0 o'tkazilgan), keyin `--apply` bilan yozildi; qayta ishga tushirish hech narsani o'zgartirmadi; 4 tasi ham manba xeshiga ega, audit'da 4 yozuv.
- `uz` da parol tekshiruvi xabarlari inglizcha edi: o'zbekcha tarjima qo'shildi (`locale/uz`).
- Productionda haqiqiy 8 ta tekshiruv (bekor qilinadigan tranzaksiyada) o'tdi: yangi rol akkaunti ochilishi, xesh tengligi, manba paroli bilan kirish, parolni o'zgartirish, noto'g'ri joriy parol rad etilishi, uz va ru xabarlari.
- Butun backend test to'plami: 2075 ta, hammasi o'tdi. MEDIA'ga tegilmadi (bu o'zgarish MEDIA'da ishlatilmaydi, u `17124e3` da qoldi).
- Parol qoidalari (raqam/katta harf) backendda ataylab qattiqlashtirilmadi (mobil ilova va mavjud foydalanuvchilar).

#### 12. Email majburiy qilindi (2026-11-19), APP serverda faqat `.env` o'zgardi

Kod o'zgarmadi (`08c2296`). APP `.env` ga ikki qator qo'shildi: `REGISTER_REQUIRES_EMAIL=1` va `EMAIL_SETUP_DEADLINE=2026-12-03` (14 kun). Konteynerlar qayta yaratildi (jonli dars 0 ta edi), web `healthy`, loglarda xato 0.

**Productionda haqiqiy tekshiruv (bekor qilinadigan tranzaksiyada, iz qolmadi):**
- `GET /auth/register/options/` → `email_required: true`.
- Emailsiz ro'yxatdan o'tish `400`: "Email tasdiqlanishi shart: avval emailga kelgan kodni tasdiqlang." Akkaunt yaratilmadi.
- Emailsiz mavjud foydalanuvchi `/auth/me/`: `email_setup_required: true`, `email_setup_deadline: 2026-12-03`.
- `email_exempt` foydalanuvchi: `email_setup_required: false`.

**Muhim:**
- Hozir productionda 28 foydalanuvchidan faqat 2 tasida tasdiqlangan email bor; qolganlarga `/me` da `email_setup_required: true` chiqadi. Muddatgacha bu faqat eslatma; 3-dekabrdan keyin majburiylikni frontend qo'llaydi.
- `email_exempt` hech kimga qo'yilmadi: bolalar akkauntlarini ishonchli aniqlab bo'lmaydi (`child.create` audit yozuvi yo'q). Telefonsiz o'quvchilar: `lolo`, `Jaloliddin` (va test akkaunt `admin`). Ular bola bo'lsa, adminda `email_exempt` belgilanadi. Bolani ota-ona/o'qituvchi yaratganda belgi avtomatik qo'yiladi.
- Qaytarish: `.env` dagi ikki qatorni olib tashlab, `docker compose -f docker-compose.app.yml up -d`.

#### 13. Mobil push (FCM) ulandi (2026-11-19), APP `18f5b13`

Firebase loyihasi `yolup-28bb7`. Service account JSON APP serverda `/etc/yolup/firebase-service-account.json` (egasi root, ruxsat 600, papka 700), `docker-compose.app.yml` uni konteynerga `/run/secrets/...` sifatida faqat o'qish uchun ulaydi. `.env`: `GOOGLE_APPLICATION_CREDENTIALS` va `FCM_PROJECT_ID=yolup-28bb7`. Kalit repoga qo'shilmagan.

**Productionda tekshirildi:** Firebase Admin ishga tushdi; ro'yxatdagi qurilma tokeniga `dry_run` yuborilganda Google so'rovni qabul qilib, faqat tokenning o'zini rad etdi ("not a valid FCM registration token"). Ya'ni kalit va loyiha to'g'ri, xato tokenda. Hech qanday haqiqiy xabar yuborilmadi.

**Hali tasdiqlanmagan:** haqiqiy qurilmaga xabar yetib borishi. Productionda faqat 1 ta qurilma bor (`ios`) va tokeni FCM tokeni emas (ehtimol xom APNs tokeni yoki sinov qiymati). Mobil ilova to'g'ri FCM tokenini yuborganda sinab ko'riladi. iOS uchun Firebase konsolida APNs kaliti ham yuklangan bo'lishi kerak.

**Eslatma:** `google-services.json` Android ilovasi uchun (mobil jamoaga beriladi), backendga kerak emas. MEDIA serverda FCM ulanmagan: "yozuv tayyor" xabarlarini MEDIA yaratadi, shuning uchun ular uchun mobil push hozircha ketmaydi (web push va ilova ichidagi xabar ishlaydi).

##### 13a. MEDIA serverga ham ulandi (2026-11-19), `92cc52f`

"Yozuv tayyor" xabarlarini MEDIA yaratadi, shuning uchun kalit u yerga ham qo'yildi (`/etc/yolup/firebase-service-account.json`, root, 600), `docker-compose.media.yml` uni ulaydi, `.env` ga ikki qator qo'shildi. MEDIA kodi `08c2296` ga yangilandi; `rec`, `rec-cron`, `transcoder` qayta yig'ilib ishga tushirildi (jonli dars 0, ffmpeg ishlamayotgan edi; LiveKit va Caddy tegilmadi). Tekshiruv: Firebase ishga tushdi, Google so'rovni qabul qildi (soxta tokenni rad etdi), loglarda xato 0.

#### 14. OpenAI kaliti almashtirildi, AI qayta ishlayapti (2026-11-19)

Yangi `sk-proj-...` kalit APP `.env` ga qo'yildi (kalit hujjatga yozilmaydi), konteynerlar qayta yaratildi (jonli dars 0), web `healthy`. MEDIA'ga kerak emas: AI chaqiruvlari faqat APP'da.

**Haqiqiy OpenAI bilan tekshirilgan:**
- Kalit: `gpt-4o-mini`, `whisper-1`, `tts-1` hisobda ochiq; chat so'rovi `200`.
- **To'liq AI baholash** (yon tomonga burilgan EXIF rasm, yuklash → `sync_ai_results`): `pending_review`, rasm to'g'ri o'qildi, 1-savol 100 ball, 2-savol (`2x+3=11`, o'quvchi x=5) xato deb topildi (to'g'ri javob x=4), umumiy ball 80, xulosa o'zbekcha; 26 461 token, ~5.7 soniya.
- **Production konteynerida:** chat JSON (`17+25` → 42); Speaking: matn → ovoz → matn aylanishi ("The quick brown fox..." so'zma-so'z qaytdi, 9 ta so'z vaqti bilan).
- **Rasm tokeni formulasi:** 768x1024 sahifa uchun taxmin 25 501, OpenAI haqiqiy hisobi 25 524 (farq: matn so'rovi). Byudjet hisobi to'g'ri.
- Sinov vaqtinchalik edi: repoga test qo'shilmadi, productionda bazaga yozilgan narsa yo'q (faqat so'rovlar).

**Hali sinalmagan:** HEIC va ko'p sahifali (3+) hujjat haqiqiy OpenAI bilan (unit testlarda tekshirilgan); AI test yaratish va IELTS writing haqiqiy so'rov bilan.

#### 15. AI bo'yicha qolgan ishlar: haqiqiy OpenAI bilan sinash va topilgan xatolar (2026-11-19)

Hamma AI imkoniyati haqiqiy OpenAI kaliti bilan (vaqtinchalik test, repoga qo'shilmagan) sinab chiqildi. Sinovdan o'tganlar va topilgan 4 ta haqiqiy xato:

**Ishlagani (haqiqiy OpenAI bilan):**
- 3 ta alohida surat (har biri bitta misol): hammasi o'qildi, xato misol topildi.
- Yon tomonga burilgan (EXIF) surat: to'g'ri o'qildi.
- HEIC (iPhone): `.jpg` ga o'tkazildi, o'qildi, xato topildi.
- Vazifa sharti faqat rasmda, javoblar alohida suratda: AI savolni rasmdan o'qib baholadi.
- 5 sahifali rasmli PDF: byudjetga 3 sahifa sig'di, 2 tasi `skipped_images` + o'qituvchiga ogohlantirish bilan qoldi.
- Word (matn + ichiga qo'yilgan rasm).
- Speaking: ovoz → matn (so'zma-so'z), 3 mezon bo'yicha baho.
- Guruh AI xulosasi (`POST .../ai-summary/`).
- AI test yaratish: Reading (8 savol, to'g'ri javoblar bilan, e'lon qilindi) va Listening (haqiqiy ovoz, 10 savol, skript yashirin).
- O'quvchi uchun AI tushuntirish va mashq; IELTS Writing (Task 2, band 6.0, mezonlar bo'yicha).

**Topilgan va tuzatilgan xatolar:**
1. **Umumiy ball savollarga mos kelmasdi.** `gpt-4o-mini` savollar 100/0/100 bo'lsa ham umumiy 100, 100/0 bo'lsa 0 yoki 80 deb berardi (4 ta haqiqiy ishdan 4 tasida). O'qituvchining ball maydoni shu bilan to'ldiriladi. Endi umumiy ballni kod hisoblaydi: savol ballari o'rtachasi, vazifada ball yozilgan bo'lsa shu og'irliklar bilan (`weight`). Eski "oraliqda bo'lsa qabul" qoidasi olib tashlandi.
2. **Qisqa matnli javob "matn yo'q" deb tashlanardi.** Word/PDF'da 80 belgidan qisqa matn (masalan "1) 1 + 1 = 2") AI'ga umuman berilmasdi. Endi o'quvchi ishida qisqa matn ham o'tadi.
3. **O'quvchi mashqida noto'g'ri javobli savollar.** Haqiqiy sinovda 11 ta tenglama savolidan 4 tasida kalit xato edi ("4x-3=2x+9" uchun 5 belgilangan, aslida 6). Tuzatish: (a) model avval yechimini yozadi, keyin javobni tanlaydi; (b) savollar test yaratishdagi AI tekshiruvchidan o'tadi; (c) **tenglamani kod o'zi tekshiradi**: javobni qo'yib ikki tomonni solishtiradi (`mathcheck.satisfying_options`). Kalit xato bo'lib, to'g'ri qiymat variantlar orasida bo'lsa kalit tuzatiladi, bo'lmasa savol tashlanadi. Tuzatishdan keyin 38 ta tenglama savoli qo'lda hisoblab tekshirildi: hammasi to'g'ri.
4. **AI test yaratishda (e'lon qilinadigan testlar) ham xuddi shunday xavf**: tenglama savollari uchun `equation` maydoni so'raladi va kalit tenglamaga zid bo'lsa savol tashlanib, zaxira savol o'rniga keladi.

**Cheklov (muhim):** tekshirish faqat bitta noma'lumli (`x`) chiziqli tenglamalarni qamrab oladi. Boshqa mavzular (geometriya, so'z masalalari, kvadrat tenglama) uchun javob to'g'riligini AI tekshiruvchi tekshiradi, u algebrada ishonchsiz ekani sinovda ko'rindi. O'qituvchi AI yaratgan testni ko'rib chiqishi tavsiya etiladi.

**Hali sinalmagan:** `gpt-4o-mini` "deprecated" bo'lgani uchun boshqa modelga o'tish (qaror sizniki, `OPENAI_MODEL`); IELTS Writing imtihon oqimi (apps/exams) alohida haqiqiy so'rov bilan (u shu `ielts_writing.evaluate` dan foydalanadi, u sinaldi).

#### 16. O'quvchi darsga kira olmadi ("loading" da qotdi): qotib qolgan navbat hisoblagichi (2026-11-19)

**Nima bo'lgan:** o'qituvchi darsni ertaroq boshlagan, o'quvchi ekranda "loading" da qolgan. Backend o'quvchiga token bergan, lekin javobda `join_delay_ms = 636 000` (10 daqiqa 36 soniya) bo'lgan: frontend shuncha kutadi va undan keyin LiveKit'ga ulanadi. LiveKit loglarida o'quvchining izi umuman yo'q edi (ulanish hali boshlanmagan).

**Sabab:** ulanishlar navbati (portlashni oldini olish uchun, 6 kishi/1.2 s) global hisoblagich bilan hisoblanadi (`live:join_queue:global`) va u 15 soniya jim turilsa nolga qaytishi kerak. Redis'da bu kalit **muddatsiz** (`TTL = -1`) qolib ketgan va qiymati **3183** ga yetgan: har bir kirish uni oshirib, kutishni o'stirgan. Mumkin bo'lgan mexanizm: Django `incr` avval kalit borligini tekshiradi, keyin oshiradi; orada kalit eskirsa, Redis uni muddatsiz qayta yaratadi. (Qachondan beri qotganini aniq bilmayman; kalit qiymati ko'p kirishni ko'rsatadi, ehtimol 2026-10-31 yuk sinovidan beri.)

**Darhol qilingan:** productionda kalit o'chirildi (faqat vaqtinchalik navbat raqami): yangi kalit muddati bilan yaratildi (TTL 12 s ga tushdi), keyingi o'quvchining kutishi 0.

**Kod tuzatishi (`apps/live/services.py`):** (1) hisoblagich qayta yaratilsa (qiymat 1) muddat majburan qo'yiladi; (2) mantiqsiz katta qiymat (>1500, ya'ni 5 daqiqadan ortiq kutish) o'zini tiklaydi. 3 ta yangi test (qotgan hisoblagich o'zi tiklanadi, poyga holatida muddat qo'yiladi, oddiy portlash o'rtada nolga qaytmaydi); dars va live testlari: 191 ta, hammasi o'tdi. **Serverda hali yo'q (deploy kutadi):** qo'lda tozalash hozircha yetarli, lekin kalit yana qotishi mumkin.

**Frontendga:** `join_delay_ms` ni ko'rsating ("navbatdagi o'rin, ~N soniya") va juda uzun (masalan 30 soniyadan ortiq) bo'lsa foydalanuvchiga xabar bering, aks holda sahifa shunchaki "loading" bo'lib qoladi.


[↑ Mundarija](#mundarija)

---


---

<!-- 5. Frontend va mobil jamoa uchun (sana bo'yicha) -->

## FRONTEND_TODO_CAMERA_BOARD

> Avvalgi fayl: `FRONTEND_TODO_CAMERA_BOARD.md`

### Frontend uchun qolgan ishlar — kamera ruxsati + doska signali (2026-09-04)

Backend tomoni **to'liq tayyor va production'da**. Bu hujjat faqat frontendda
qolgan ikkita narsani tasvirlaydi. Ikkalasi ham mavjud **mikrofon** oqimi
bilan bir xil naqsh — `useMicSignals` hook'ini nusxalab, nomlarni almashtirish
kifoya.

**WebSocket**: hammasi mavjud `wss://<domain>/ws/board/<lesson_id>/?token=<JWT>`
ulanishining o'zidan keladi — yangi ulanish ochish shart emas.

---

#### 1. Kamera endi ruxsat bilan ochiladi (avval hammaga erkin edi)

**O'zgargan xatti-harakat**: o'quvchining LiveKit tokeni endi kamera nashr
qilish huquqisiz keladi. O'qituvchi ruxsat berguncha, o'quvchi **kamerasini
umuman yoqolmaydi** (`TrackToggle`/`setCameraEnabled` xato qaytaradi yoki
jimgina ishlamaydi — LiveKit server rad etadi).

##### REST — mikrofon bilan AYNAN bir xil naqsh

| Method | Path | Kim | Tavsif |
|---|---|---|---|
| POST | `/api/v1/live/request-camera/` | O'quvchi | `{lesson_id}` — kamera so'raydi |
| POST | `/api/v1/live/grant-camera/` | O'qituvchi | `{lesson_id, student_id}` — ruxsat beradi |
| POST | `/api/v1/live/deny-camera/` | O'qituvchi | `{lesson_id, student_id}` — rad etadi |

Javoblar `request-mic`/`grant-mic`/`deny-mic` bilan bir xil shaklda
(`{"ok": true}` yoki `{"denied": true/false}`).

##### WebSocket eventlari (board kanali orqali, `mic_*` bilan bir xil qatordan)

```json
{ "type": "camera_request", "student_id": "uuid", "name": "Sardor" }
{ "type": "camera_granted", "student_id": "uuid" }
{ "type": "camera_denied", "student_id": "uuid" }
```

Frontend logikasi mikrofonnikiga bir xil bo'lishi kerak:
- **`camera_request`** — faqat `is_teacher=true` bo'lganda ko'rsatiladi ("qo'l ko'tarish" belgisi, mikrofon so'rovi qatoriga o'xshab).
- **`camera_granted`** — HAMMAGA keladi, har bir client o'zi filtrlaydi: `studentId === room.localParticipant.identity` bo'lsa — o'zining kamera tugmasini yoqadi/faollashtiradi.
- **`camera_denied`** — shu o'quvchining o'zi "so'rash" tugmasini qayta faollashtiradi.

##### Sahifa yangilanganda / qayta ulanganda holatni tiklash

`GET /api/v1/board/{lesson_id}/` javobiga yangi maydon qo'shildi (faqat
`is_teacher=true` bo'lganda, `pending_mic_requests` bilan bir qatorda):

```json
{
  "pending_mic_requests": [{ "student_id": "uuid", "name": "Sardor" }],
  "pending_camera_requests": [{ "student_id": "uuid", "name": "Sardor" }]
}
```

##### UI

`live-room.tsx`dagi `TrackToggle source={Track.Source.Camera}` hozircha
**shartsiz** ko'rsatiladi (mikrofon esa `canPublishSource` bilan tekshiriladi).
Kamerani ham xuddi shunday — `useLocalParticipantPermissions()` +
`canPublishSource(permissions, CAMERA_SOURCE)` bilan tekshirish, ruxsat
bo'lmasa `StudentMicControl`ga o'xshash "so'rash" tugmasi ko'rsatish kerak.

---

#### 2. Doska ruxsati — yangi WebSocket signali

**Bug**: o'qituvchi doskaga chizish ruxsatini bergach, o'quvchi sahifani
yangilamaguncha buni bilmay, chiza olmay turardi (backend ruxsat berilgan
edi, lekin frontendga signal ketmagan). Endi tuzatildi:

```json
{ "type": "board_granted", "student_id": "uuid" }
```

Frontend: bu event kelganda, agar `student_id === o'zim` bo'lsa — doskaning
`can_draw` holatini `true`ga o'rnatish (yoki oddiygina `GET /board/{id}/`ni
qayta chaqirish) kerak. Hozircha bu event uchun HECH QANDAY handler yo'q —
qo'shilishi kerak.

---

#### Eslatma

Kamera cheklovi **hozir productionda faol** — frontend bu ishni qilib
bo'lmaguncha, o'quvchilar kamerani umuman yoqa olmaydi. Tezroq qilingani
ma'qul.


[↑ Mundarija](#mundarija)

---

## FRONTEND_TODO_SCREEN_SHARE

> Avvalgi fayl: `FRONTEND_TODO_SCREEN_SHARE.md`

### Frontend: ekran ulashishda boshqaruv oynasi (Zoom / Google Meet kabi)

**Backend tomonida hech narsa kerak emas.** O'qituvchi LiveKit tokenida
`screen_share` va `screen_share_audio` ruxsatlari allaqachon bor
(`TEACHER_PUBLISH_SOURCES`). Yangi endpoint, WebSocket event yoki track
qo'shilmaydi. Hammasi brauzerda hal bo'ladi.

---

#### Muammo

O'qituvchi ekranni (yoki bitta dastur oynasini) ulashib, boshqa oyna/ekranga
o'tsa, platforma ko'rinmay qoladi. Boshqaruv tugmalari (mikrofon, kamera,
"To'xtatish") va ishtirokchilar videosi yo'qoladi.

Zoom va Google Meet'da bunday emas: boshqa oynaga o'tsa ham boshqaruv paneli
ustida turadi.

#### Nima uchun Zoom'da ishlaydi, bizda yo'q

Zoom oddiy dastur, boshqa oynalar ustida chiza oladi. Veb-sahifa brauzer
oynasidan tashqariga chiza olmaydi. Google Meet buni
**Document Picture-in-Picture API** bilan hal qiladi: har doim boshqa
oynalar ustida turadigan kichik oyna, ichiga oddiy HTML qo'yish mumkin.

#### Nima qilish kerak

##### 1. Boshqaruv oynasi (asosiy ish)

Ekran ulashish boshlanganda Document PiP oynasini ochish:

```js
if ('documentPictureInPicture' in window) {
  const pip = await documentPictureInPicture.requestWindow({
    width: 360,
    height: 220,
  });
  // pip.document.body ichiga boshqaruv UI'ni chizing:
  // mikrofon, kamera, "Ulashishni to'xtatish", ixtiyoriy: ishtirokchilar videosi
}
```

- Oyna ichida mikrofon, kamera va **"Ulashishni to'xtatish"** tugmalari bo'lsin.
- Ixtiyoriy: o'qituvchi/talabalar videosi (Meet'dagidek kichik plitkalar).
- `requestWindow` foydalanuvchi harakatidan (tugma bosish) chaqirilishi shart.
  Ulashish tugmasi bosilgan paytning o'zida chaqiring.
- PiP oynasi yangi `document`. Asosiy sahifaning CSS'i u yerga o'tmaydi:
  stillarni `pip.document.head` ga nusxalang yoki `<style>` qo'shing.
- React ishlatilsa, boshqaruv komponentini `createPortal(..., pip.document.body)`
  bilan chizing.
- Ulashish to'xtaganda yoki foydalanuvchi PiP oynasini yopganda holatni
  to'g'ri tozalang (`pip.close()`, `pagehide` eventi).

##### 2. Qo'llab-quvvatlanmaydigan brauzerlar (Safari, Firefox)

Document PiP faqat **Chrome / Edge 116+** da bor. Boshqalarda zaxira:

- Oddiy video PiP: `videoElement.requestPictureInPicture()`. Unda faqat
  bitta video ko'rinadi (masalan, o'qituvchi kamerasi), tugmalar bo'lmaydi.
- Yoki ulashish boshlanganda foydalanuvchiga qisqa ogohlantirish ko'rsating.

Tekshiruv: `'documentPictureInPicture' in window`.

##### 3. `getDisplayMedia` sozlamalari

LiveKit'ning `setScreenShareEnabled` ga yoki to'g'ridan-to'g'ri
`getDisplayMedia` ga quyidagilarni bering:

```js
{
  video: true,
  audio: true,                    // dastur/tab tovushi (qo'llab-quvvatlansa)
  selfBrowserSurface: 'exclude',  // platformaning o'zi ro'yxatda chiqmasin
  surfaceSwitching: 'include',    // ulashish paytida oynani almashtirish mumkin
  systemAudio: 'include',
  monitorTypeSurfaces: 'include',
}
```

- `selfBrowserSurface: 'exclude'` bo'lmasa, o'qituvchi platformaning o'z
  tabini ulashib qo'yadi va "oyna ichida oyna" (cheksiz tunnel) effekti chiqadi.
- Brauzer o'zining "Stop sharing" panelini ko'rsatadi (skrinshotdagi
  yashil "Вы запустили демонстрацию экрана" paneli). Uni o'zgartirib
  bo'lmaydi, bu normal.

#### Tekshirish ro'yxati

- [ ] Ekran ulashish boshlanganda PiP boshqaruv oynasi ochiladi.
- [ ] Boshqa oyna/ekranga o'tilganda PiP oynasi ustida turadi.
- [ ] PiP ichidagi mic/kamera/"To'xtatish" tugmalari ishlaydi.
- [ ] "To'xtatish" bosilsa ulashish ham, PiP oynasi ham yopiladi.
- [ ] PiP oynasi qo'lda yopilsa, ulashish davom etadi (yoki ataylab
      to'xtatiladi, qaror sizniki), holat noto'g'ri qolib ketmaydi.
- [ ] Platformaning o'z tabi ulashish ro'yxatida chiqmaydi.
- [ ] Safari/Firefox'da xato bermaydi, zaxira yo'l ishlaydi.
- [ ] Yozuv (recording) avvalgidek ishlaydi. Tracklar o'zgarmaydi, shuning
      uchun backend va yozuvga ta'sir qilmasligi kerak.

#### Eslatma: server sarlavhalari

Frontend serverida (Vercel va h.k.) `Permissions-Policy` sarlavhasi qo'yilgan
bo'lsa, `display-capture` ni bloklamaganini tekshiring. Backend va Caddy
tomonida bunday sarlavha yo'q.


[↑ Mundarija](#mundarija)

---

## FRONTEND_TODO_2026-11-10

> Avvalgi fayl: `FRONTEND_TODO_2026-11-10.md`

### Frontend uchun qolgan ishlar (2026-11-10) — Trello kartalari bo'yicha

Backend tomoni tayyor (`BACKEND_YANGILANISHLAR_2026-11-10.md` ga qo'shimcha). Bu hujjat faqat **frontendda** qoladigan ishlarni tasvirlaydi.

---

#### 1. Screen record: ekranda username va Yolup logosi ("screeen record" kartasi)

**Maqsad:** kimdir darsni ekran yozuvi bilan (telefon, OBS, QuickTime, boshqa dastur) yozib olib, uchinchi tomonga tarqatsa, **kim yozganini** bilish mumkin
bo'lsin. Buning uchun har bir foydalanuvchining o'z ekranida uning `username`i va kichik Yolup logosi doim ko'rinib turadi, yozib olingan videoda ham.

**Nima qilish kerak (web):**
- Dars (jonli xona), doska, yozuvni ko'rish (`recording` sahifasi), material/PDF ko'rish sahifalarida butun ekran ustidan **yarim shaffof belgi** (watermark):
  - kichik **Yolup logosi** (burchakda, masalan pastki o'ng);
  - foydalanuvchining `username`i (yoki ism + username) — kamida bitta joyda doim, yaxshisi bir necha joyda (burchaklarda yoki yengil qiyshaygan
    takrorlanuvchi yozuv sifatida), shunda kadrni qirqib tashlash qiyin bo'ladi.
- Belgi sahifa tarkibini to'sib qo'ymasligi kerak: `position: fixed`, `pointer-events: none`, yuqori `z-index`, shaffoflik ~15–25%.
- Ma'lumot manbai: `GET /auth/me/` → `username` (qo'shimcha backend kerak emas).
- Belgini DOM'dan osongina olib tashlab bo'lmasligi uchun (DevTools) `MutationObserver` bilan o'chirilsa qayta qo'shib turing. To'liq himoya mumkin emas:
  brauzer operatsion tizim darajasidagi ekran yozuvini taqiqlay olmaydi, belgi faqat kim yozganini aniqlashga yordam beradi.
- **O'qituvchining ekran ulashishi** (`getDisplayMedia`) va serverga yuklanadigan dars yozuvi (`recording`) o'qituvchi brauzerida olinadi. Yozuvning ichiga
  belgi tushishini xohlasangiz, belgini ulashilayotgan sahifada emas, **ulashishdan oldin** `canvas`ga chizib yozing (yoki dars sahifasidagi belgidan
  foydalaning). Backend yozuvni qayta ishlamaydi, shuning uchun bu butunlay frontend qarori.
- Logo faylini dizayner beradi (SVG, och va to'q fon uchun ikki variant).

#### 2. Chatda sana ajratgichlari ("chatda xato bor" kartasi)

Xabarlar orasida kun almashganda sana yozuvi bo'lsin, aks holda "bugun"/"kecha" ajratib bo'lmaydi:

- Xabarlar ro'yxatida har kunning birinchi xabari oldiga ajratgich: **"Bugun"**, **"Kecha"**, undan eskisi uchun sana (`10.11.2026`; joriy yildan boshqasi bo'lsa yil bilan).
- Hisob **foydalanuvchi mahalliy vaqti** bo'yicha: `created_at` — ISO vaqt (UTC offset bilan), uni brauzer vaqt zonasiga o'tkazib, kun bo'yicha guruhlang.
- Chat ro'yxatidagi oxirgi xabar vaqti: bugun — soat (`14:05`), kecha — "Kecha", shu hafta — hafta kuni, undan eski — sana.
- Pastga/tepaga qo'shimcha yuklaganda (`before`, `after`) ajratgichlarni qayta hisoblang (bir kun ikki sahifaga bo'linib qolsa, ajratgich ikki marta chiqmasin).

#### 3. Bildirishnomalarda sana ("notification da xatolik" kartasi)

- Inbox qatorida faqat soat emas, **sana va soat**: `GET /notifications/` har qatorida `created_at` (va `notification.created_at`) bor. Bugun bo'lsa "Bugun 14:05",
  kecha — "Kecha 14:05", undan eski — `10.11.2026 14:05`.
- Backend ham matnlarga sana qo'shdi: dars eslatmasi ("... 15 daqiqadan keyin boshlanadi (10.11.2026 18:00)") va ota-onaga davomat xabari
  ("... 10.11.2026 18:03 da qo'shildi"). Frontend matnni o'zgartirmasdan ko'rsatadi.

#### 4. Test yaratish — pullik xizmat ("test yaratish qismda" kartasi)

- `GET /auth/me/` da `can_create_tests: bool` (hozircha hammada `true`). `false` bo'lsa: test yaratish tugmalarini (qo'lda, fayldan/Google'dan import, AI) yopiq
  ("Pullik xizmat") holatda ko'rsating va administrator bilan bog'lanish yo'lini bering.
- Yopiq foydalanuvchi yaratishga urinsa backend `403` qaytaradi (`error.code: "permission_denied"`, xabar: "Test yaratish xizmati sizda yoqilmagan..."), shuning uchun
  tugmani `can_create_tests` bo'yicha oldindan yashiring. Mavjud testlarni ko'rish, o'tkazish va natijalar yopilmaydi.
- **Admin paneli:**
  - `GET /auth/teachers/` — har o'qituvchida `can_create_tests`;
  - `PATCH /admin/users/{id}/test-access/ {enabled: true|false}` → `{id, username, can_create_tests}` (faqat admin). Ro'yxatda har qatorga almashtirgich qo'ying.

#### 5. Eslatma (ilgari yozilgan, qisqacha)

- "Ota-ona" → **"Kuzatuvchi"**, "Farzand" → **"O'quvchi"**: backend yaratadigan matnlarda va rol nomida (`role: "parent"` kodi o'zgarmadi) shunday bo'ldi.
  Interfeysdagi yorliqlarni ham shunga moslang.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-11

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-11.md`

### Frontend uchun: yangi backend imkoniyatlari (Trello "Todo" kartalari)

Hammasi backendda tayyor va sinalgan. Quyida har bir karta uchun nima o'zgargani va frontend nima qilishi kerakligi.

---

#### 1. "test yaratish qismi" — guruh ixtiyoriy

`POST /quizzes/` (va AI/import/Google yo'llari) endi **guruh ham, fan ham bermasdan** ishlaydi.
- Guruhsiz test faqat muallif o'qituvchiga ko'rinadi, o'quvchilarga chiqmaydi.
- Keyin guruhga berish: `PATCH /quizzes/{id}/ {course: "<id>"}` (avvalgidek).
- "Guruh" maydonini formada ixtiyoriy qiling ("Guruhsiz saqlash").

#### 2. "test di guruhga berish" — alohida o'quvchilarga berish

Guruhga berishda (`Guruhga berish` oynasi) o'quvchilar ro'yxati chiqadi, **hammasi belgilangan** holda; o'qituvchi keraklilarini qoldiradi.

- Berish: `PATCH /quizzes/{id}/ {course, due_at, student_ids: ["<id>", ...]}`; yaratishda ham `student_ids` bor (`POST /quizzes/`).
  `student_ids` yuborilmasa / bo'sh bo'lsa / guruhning hamma o'quvchisi bo'lsa — **hamma** (cheklov yo'q).
- Kimlar ocha olishini ko'rish: `GET /quizzes/{id}/audience/`
  ```json
  { "restricted": true, "total": 12, "assigned_count": 7,
    "students": [ {"id","name","username","avatar_url","assigned": true, "can_attend": true, "attempted": false}, ... ] }
  ```
  `can_attend=false` — o'quvchi testni ko'rmaydi va topshira olmaydi; `attempted` — topshirgan.
- Keyinroq o'zgartirish: `PUT /quizzes/{id}/audience/ {student_ids: [...]}` (bo'sh ro'yxat = hammaga). Yangi qo'shilgan o'quvchiga bildirishnoma boradi.
- Test javobida (`GET /quizzes/`, `GET /quizzes/{id}/`, o'qituvchi/admin uchun): `student_ids` — `null` bo'lsa hamma, ro'yxat bo'lsa faqat shular.
- Tanlanmagan o'quvchi va uning kuzatuvchisi uchun test ro'yxatda yo'q, to'g'ridan-to'g'ri ochsa `404`.

#### 3. "dars yaratish" — bir vaqtda bir nechta dars

Yangi: `POST /lessons/bulk/`
```json
{ "course": "<id>",
  "lessons": [ {"title": "...", "starts_at": "2026-11-12T18:00:00+05:00", "duration_min": 60, "note": ""},
               {"title": "...", "starts_at": "2026-11-14T10:00:00+05:00"} ] }
```
- Eng ko'pi bilan 50 ta. Har dars o'z `course`ini ham berishi mumkin (o'qituvchining o'z guruhlari).
- **Hammasi yoki hech biri**: birortasi xato bo'lsa hech narsa yaratilmaydi va xato qaysi dars (indeks) ekanini aytadi:
  `error.details.lessons["1"].starts_at = ["Dars boshlanish vaqti o'tgan..."]`.
- Javob: `201 {count, lessons: [...]}`.
- Haftalik takrorlanish (`recurrence`) avvalgidek `POST /lessons/` orqali ("Takrorlanuvchi" tab) — o'zgarmagan.

#### 4. "Kanal image change"

- `POST /chat/channels/{id}/image/` (multipart, `image` fayl) — kanal rasmini o'rnatadi/almashtiradi;
  `DELETE /chat/channels/{id}/image/` — olib tashlaydi. Faqat kanal egasi.
  Xuddi shu ishni `POST/DELETE /chat/rooms/{id}/image/` ham qiladi (guruh va kanal uchun).
- Javob — xonaning to'liq ma'lumoti; `image` — to'liq URL (yoki `null`). Chat ro'yxatida va a'zolarda shu `image` ko'rinadi.

#### 5. "homeworkcheck" — fayl yuklash ixtiyoriy

- `POST /homework/assignments/{id}/submit/`: fayl bo'lmasa ham **izoh (`comment`) bilan** topshirsa bo'ladi (matnli javob).
  Na fayl, na izoh bo'lsa — `400`.
- Faylsiz topshiriq AI'ga yuborilmaydi, to'g'ridan-to'g'ri o'qituvchiga baholashga tushadi. Javobda `files: []`, `file_name: ""`.
- O'qituvchi sahifasida faylsiz topshiriq uchun yuklab olish tugmasini yashiring (`GET .../submissions/{id}/file/` bunda `404` beradi); `comment` ni asosiy javob sifatida ko'rsating.
- Formada "Faylni yuklang" bloki ixtiyoriy bo'lsin: "Fayl yuklang yoki javobingizni izohga yozing".

#### 6. "homework" — natijani ko'rish ishlamayapti ("AI tekshiruv natijasi" bo'sh)

Skrinshotda oyna "— ball / Baho yo'q" bilan bo'sh chiqqan, chunki topshiriq hali `Tekshirilmoqda` edi. Endi o'qituvchiga topshiriq javobida aniq holat keladi:

| `ai_state` | ma'nosi | Oynada nima ko'rsatish |
|---|---|---|
| `checking` | AI hali tekshirmoqda (`ai_checking_since` — qachondan) | "AI tekshirmoqda…" (spinner), ball maydonini yashirish |
| `ready` | AI natijasi tayyor (`ai_result`, `ai_overall_score`) | Natija |
| `failed` | AI baholay olmadi (`error` — sabab) | "AI baholay olmadi — o'zingiz baholang" |
| `none` | AI ishlatilmagan | AI bo'limini yashirish |

- Backend AI tekshiruvi 15 daqiqa ichida tugamasa yoki xato bersa topshiriqni avtomatik o'qituvchiga (`failed`) o'tkazadi, shuning uchun "Tekshirilmoqda" abadiy qolmaydi.
- `ai_state` faqat o'qituvchi/admin javobida bor; o'quvchida yo'q.

#### 7. "account almashtirish ishlamayapdi"

Karta 2026-11-10 ertalab ochilgan edi. O'shandan beri backendda telefon raqamlari bir xil ko'rinishga keltirildi (`+998XXXXXXXXX`), shu sababli bitta odamning akkauntlari (o'qituvchi/o'quvchi/kuzatuvchi) endi bir-biriga to'g'ri bog'lanadi.
- Ro'yxat: `GET /auth/me/` → `linked_accounts` (joriy akkauntdan boshqalari). O'tish: `POST /auth/switch/{id}/`.
- "Boshqa akkaunt qo'shish": `POST /auth/switch-role/ {role: "teacher"|"parent"|"student"}` — rol hali yo'q bo'lsa avtomatik ochiladi (o'quvchi akkauntidan boshqa rolga o'tib bo'lmaydi).
- Agar yangilangandan keyin ham faqat bitta akkaunt chiqsa — shu odamning boshqa akkauntlarida telefon raqami boshqacha yoki bo'sh; xabar bering, tekshiramiz.

---

#### Backendga tegishli bo'lmagan kartalar (frontend)

- **"test yaratish qism"** — Word/Excel/Google Forms tugmalari bir xil ochilishi (UI).
- **"meeting"** — qaysi ekran ulashilayotgani doim ko'rinib tursin (UI + LiveKit trek nomi; backend kerak emas).
- **"vazifa berish da"** — fon (background) muammosi (UI).

#### Savol bor

**"Vazifa: HomeWork"** kartasi ("file yuklash, google forma qilish imkoni; doska; ruchnoy; AI qila olmasa o'zin hal qil") — bir qismi allaqachon bor (doskada yechish, AI qila olmasa o'qituvchiga tushishi, savolli vazifa). Google Form orqali topshirish qanday bo'lishi kerakligini aniqlashtirish kerak: (a) o'qituvchi vazifaga Google Form havolasini qo'shadi va o'quvchi shu yerda to'ldiradimi, yoki (b) Google Form'dan savollarni vazifaga import qilamizmi (testlardagidek)?


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-11_2

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-11_2.md`

### Frontend uchun: 11-noyabrdagi ikkinchi backend vazifalari javobi

Hammasi backendda tayyor va sinalgan. Har bir band uchun nima o'zgargani va frontend nima qilishi kerakligi.

---

#### 1. Uy vazifasi: Google Form havolasi

- `POST /homework/assignments/` va `PATCH /homework/assignments/{id}/` — `google_form_url` (ixtiyoriy). Bo'sh satr = olib tashlash.
  Faqat `https://docs.google.com/forms/...`, `https://forms.google.com/...` yoki `https://forms.gle/...` qabul qilinadi, boshqasiga `400` (`error.details.google_form_url`).
- Javobda (o'qituvchi, o'quvchi, kuzatuvchi; ro'yxat ham, batafsil ham): `google_form_url` (`""` — yo'q).
- Oqim: o'quvchi vazifani ochadi → "Formani ochish" tugmasi (`google_form_url`) → to'ldirgach platformada **izoh bilan** topshiradi
  (`POST .../submit/` faylsiz, `comment` bilan; masalan "Formani to'ldirdim"). Form o'zi vazifa ichida ochilmaydi (Google iframe'ga ruxsat bermaydi) — yangi tabda oching.

#### 2. Test: vaqt, urinishlar soni, nechta savol

O'qituvchi yaratishda (`POST /quizzes/`) yoki guruhga berishda (`PATCH /quizzes/{id}/`) quyidagilarni yuboradi (hammasi ixtiyoriy, `null` yoki yuborilmasa = cheklov yo'q):

| maydon | qiymat | ma'nosi |
|---|---|---|
| `time_limit_minutes` | 1–600 | testni boshlagandan keyin shuncha daqiqa ichida topshirish kerak |
| `max_attempts` | 1–20 | necha marta topshirish mumkin |
| `questions_per_attempt` | 1..testdagi savollar soni | har o'quvchiga savollardan nechtasi tushadi |

Test javobida (o'qituvchi uchun batafsil ham, ro'yxat ham) uchala maydon bor. `questions_per_attempt` matn/audioga bog'langan (`groups`) testda **berilmaydi** (`400`) — savollar o'z tartibida qoladi.

##### O'quvchi oqimi

`GET /quizzes/{id}/` (o'quvchi) javobida yangi maydonlar:

```json
{ "time_limit_minutes": 20, "max_attempts": 2, "questions_per_attempt": 3,
  "attempts_used": 0, "attempts_left": 2,
  "started_at": null, "ends_at": null, "needs_start": true,
  "questions": [], "groups": [] }
```

1. **Vaqt chegarali** testda (`time_limit_minutes` bor) test boshlanguncha `needs_start: true`, `questions` va `groups` **bo'sh**. Ro'yxatdan "Boshlash" tugmasi
   `POST /quizzes/{id}/start/` ni chaqiradi:
   ```json
   { "started_at": "...", "ends_at": "...", "time_limit_minutes": 20, "attempts_used": 0, "attempts_left": 2, "question_count": 3 }
   ```
   Taymerni `ends_at` va `started_at` farqi (yoki `time_limit_minutes`) bo'yicha ko'rsating. Qayta chaqirilsa shu faol seans qaytadi (vaqt yangilanmaydi),
   sahifa yangilansa ham taymer davom etadi. Shundan keyin `GET /quizzes/{id}/` savollarni beradi.
2. Vaqt chegarasiz testda `start` shart emas (chaqirsangiz ham bo'ladi, `ends_at: null`).
3. Topshirish: `POST /quizzes/{id}/attempts/` (avvalgidek). Vaqt tugaganda taymer nolga yetishi bilan avtomatik topshiring.
   - Vaqt tugagach ~30 soniyadan keyin kelgan javob **qabul qilinmaydi** (`400`, "Test vaqti tugagan...") va bu urinish **sarflangan** hisoblanadi (`attempts_used` oshadi).
   - Vaqt chegarali testni `start`siz topshirishga urinsa `400`.
   - `duration_seconds` yuborilmasa server o'zi hisoblab qo'yadi (seansdan).
4. **Urinishlar:** `attempts_used` / `attempts_left` (cheklov yo'q bo'lsa `attempts_left: null`). `attempts_left: 0` bo'lsa test savollari yashirin (`questions: []`),
   `start` va `attempts` — `400`. Interfeysda "Urinishlar tugagan" ko'rsating.
5. **`questions_per_attempt`:** o'quvchiga faqat N ta (tasodifiy tanlangan) savol keladi; shular bo'yicha ball hisoblanadi (`max_score` ham shularniki).
   Boshqa savolga javob yuborilsa `400`. Tanlov bitta urinishda o'zgarmaydi, yangi urinishda va boshqa o'quvchida boshqacha.

#### 3. Savollar va variantlar tasodifiy tartibda

- Har o'quvchiga savollar va `single`/`multiple` variantlari o'z tartibida beriladi (avval faqat `ordering` va `matching` aralashar edi). To'g'ri javob doim bir joyda turmaydi.
- Tartib bitta urinish davomida o'zgarmaydi (sahifa yangilansa ham bir xil), yangi urinishda qayta aralashadi (urinish topshirilgach yoki vaqti tugagach).
- Matn/audioga bog'langan (`groups`, IELTS reading/listening) testda **savollar tartibi saqlanadi**, faqat variantlar aralashadi.
- Frontend `questions` va `options` ni **kelgan tartibda** ko'rsatsin (o'zi saralamasin, `order` bo'yicha ham emas). Natija sahifasida esa javoblar `answers` ro'yxati bo'yicha.
- Imtihon (`exams`) va o'qituvchi ko'rinishi (`GET` o'qituvchi/admin) o'zgarmagan.

#### 4. Uy vazifasi ikki bosqichda: baza va biriktirish

Backend qarori: **har guruh uchun alohida nusxa** (topshiriqlar, muddat va baholash guruh bo'yicha mustaqil). Bazadagi asl vazifa saqlanib qoladi va qayta-qayta berilishi mumkin.

1. **Bazaga yaratish:** `POST /homework/assignments/` ni `course_id`siz yuboring — vazifa bazaga tushadi (javobda `is_bank: true`, `course_id: null`, `status: "bank"`).
   Hamma maydonlar (matn, fayl, savollar, `google_form_url`, baholash) avvalgidek. Bazadagi vazifani faqat muallif ko'radi; unga topshirib bo'lmaydi (`404`).
   Tahrirlash va o'chirish: `PATCH`/`DELETE /homework/assignments/{id}/` (avvalgidek).
2. **Baza ro'yxati:** `GET /homework/assignments/?bank=1` → `[{..., is_bank, copies_count (nechta guruhga berilgan), questions_count}]`.
3. **Biriktirish:** `POST /homework/assignments/{id}/assign/`
   ```json
   { "course_ids": ["<id>", "<id>"], "student_ids": ["<id>"], "due_at": "2026-11-20T23:59:00+05:00", "allow_late": true, "announce_in_chat": true }
   ```
   - `course_ids` — butun guruhga; `student_ids` — faqat shu o'quvchilarga. Ikkalasi birga bo'lsa birlashtiriladi (guruh + boshqa guruhdan qo'shimcha o'quvchilar).
   - Faqat `student_ids` bo'lsa va o'quvchi o'qituvchining **bitta** guruhida bo'lsa, guruh o'zi aniqlanadi. Bir nechta guruhda bo'lsa `400` — `course_ids` bilan guruhni ko'rsating.
   - Javob: `201 {count, assignments: [...]}` — har guruh uchun bitta yangi vazifa (`source_id` — baza vazifasi). Ular oddiy faol vazifalar: o'quvchilarga bildirishnoma va guruh chatiga karta tushadi
     (faqat tanlangan o'quvchilarga berilganda chat kartasi yuborilmaydi, chunki chat butun guruhga ko'rinadi).
4. **Kimga berilgani** (testlardagi `audience` kabi), guruhga berilgan vazifa uchun:
   - `GET /homework/assignments/{id}/audience/` → `{restricted, total, assigned_count, students: [{id, name, username, assigned, can_submit, submitted}]}`
   - `PUT /homework/assignments/{id}/audience/ {student_ids: [...]}` — faqat shularga (bo'sh ro'yxat yoki hamma o'quvchi = cheklovsiz). Keyin qo'shilganlarga bildirishnoma boradi.
   - Vazifa javobida (o'qituvchi uchun, batafsil va ro'yxat): `student_ids` — `null` bo'lsa hamma, ro'yxat bo'lsa faqat shular.
   - Tanlanmagan o'quvchi va uning kuzatuvchisiga vazifa ko'rinmaydi (ro'yxatda yo'q, to'g'ridan-to'g'ri ochsa `404`), topshira olmaydi.
5. Oddiy (guruhga bevosita yaratilgan) vazifalar avvalgidek ishlaydi: `POST` ni `course_id` bilan yuboring.


[↑ Mundarija](#mundarija)

---

## FRONTEND_QOTISH_TAHLILI_2026-11-12

> Avvalgi fayl: `FRONTEND_QOTISH_TAHLILI_2026-11-12.md`

### O'qituvchi kamerasi qotib qolishi: tahlil va frontend uchun tavsiyalar (2026-11-12)

**Holat:** bugun jonli darsda o'qituvchi kamerasi ochiq turib, qisqa vaqtga qotib qoldi.

#### Serverda nima ko'rildi

- LiveKit (MEDIA): oxirgi 24 soatda ogohlantirish/xato yo'q, qayta ishga tushish yo'q, server bo'sh (CPU/tarmoq muammosi yo'q).
- Bugungi ikkala dars (11:04–11:16) bitta brauzerdan: **Windows, Chrome 157**. Birinchi seans 43 soniyadan keyin **mijozning o'zi** chiqib ketgan
  (`CLIENT_REQUEST_LEAVE`), 15 soniyadan keyin qayta kirgan (yozuv tizimi ham shu 14,6 soniyali tanaffusni qayd etgan). Ya'ni sabab serverda emas.

#### O'qituvchi brauzeri bir vaqtda nima qilyapti (LiveKit log'idan va kod'dan)

O'qituvchi darsga kirgan zahoti, **hammasi bitta kompyuterda, dasturiy (software) VP8 kodlash bilan**:

| # | nima | o'lcham / bitreyt | manba |
|---|---|---|---|
| 1–3 | **Kamera**, simulcast 3 qatlam | 1280×720 (1,7 Mbit/s) + 640×360 + 320×180 | `video={choices.cameraOn}` standart sozlama, `ROOM_OPTIONS` da `videoCaptureDefaults`/`publishDefaults` yo'q |
| 4–5 | **Ekran ulashish**, simulcast 2 qatlam | **1920×1080** (1,5 Mbit/s) + 960×540 | `requestScreenCapture` o'lcham cheklamaydi; `SCREEN_SHARE_ENCODING` faqat bitreyt/kadr |
| 6 | **Dars yozuvi** (`MediaRecorder`, VP8) | ekran oqimi, 1,5 Mbit/s | `teacher-video-recording.ts` |
| 7 | Audio yozuvi + mikrofon + ekran audiosi | — | `teacher-audio-recording.ts` |

Ya'ni 5–6 ta bir vaqtdagi video kodlash (bittasi to'liq 1080p), ustiga doska, chat, PiP va React render. Kuchsiz yoki issiq noutbukda CPU 100% ga yetadi,
Chrome kadrlarni tashlaydi va kamera "qotadi". Bu **eng ehtimolli sabab**, lekin hali isbotlanmagan (serverda ko'rinmaydi, faqat mijozda o'lchanadi).

#### Tavsiya etilgan o'zgarishlar (taʼsiri kattasidan boshlab)

1. **Ekran ulashishni 720p ga tushiring va simulcast'ni o'chiring.**
   `getDisplayMedia({ video: { width: { max: 1280 }, height: { max: 720 }, frameRate: { ideal: 15, max: 15 } } })` va
   `publishTrack(..., { source, screenShareEncoding: SCREEN_SHARE_ENCODING, simulcast: false })`. 1080p ekran matn o'qish uchun ham keraksiz bo'lishi mumkin; bitta qatlam 2 ta kodlashni 1 taga tushiradi.
2. **Kamerani 540p/360p qiling, qatlamlarni kamaytiring.** `ROOM_OPTIONS` ga:
   `videoCaptureDefaults: { resolution: VideoPresets.h540.resolution, frameRate: 24 }` va
   `publishDefaults: { videoSimulcastLayers: [VideoPresets.h180] }` (jami 2 qatlam). O'quvchilarga 720p kamera kerak emas (kichik oynada ko'rinadi).
3. **Qurilmada apparat kodlagichni sinab ko'ring:** `publishDefaults: { videoCodec: "h264" }` (Windows'da GPU orqali kodlanadi, CPU keskin kamayadi).
   Eslatma: o'quvchi brauzerlarida (Safari/eski Android) H.264 dekodlash muammosi bo'lmasligi uchun avval 1–2 qurilmada tekshiring; kerak bo'lsa `backupCodec` qoldiring.
4. **Dars yozuvi kodlashini yengillashtiring.** `MediaRecorder` hozir to'liq ekran oqimini qayta kodlaydi. Variantlar: `videoBitsPerSecond` ni 800 kbit/s gacha tushirish; yozuvni 1280×720
   ga tushirilgan oqimdan olish (1-band bilan bir xil oqim); CPU zo'riqqanda yozuvni to'xtatmasdan sifatini pasaytirish.
5. **CPU zo'riqishini aniqlang va ko'rsating.** LiveKit klienti brauzer `qualityLimitationReason = "cpu"` desa CPU cheklovi hodisasini beradi (`ParticipantEvent.LocalTrackCpuConstrained` / `TrackEvent.CpuConstrained`; nomini o'rnatilgan `livekit-client` versiyasida tekshiring).
   Unda o'qituvchiga "Kompyuter zo'riqmoqda: kamera sifati pasaytirildi" deb ko'rsating va avtomatik pastroq sifatga o'ting (masalan kamera 360p, yozuv bitreyti pastroq).
6. **Diagnostika (keyingi safar sababni aniq bilish uchun).** Darsda har 30 soniyada `localTrack.getSenderStats()` dan `framesPerSecond`, `qualityLimitationReason`,
   `targetBitrate` va `navigator.hardwareConcurrency`, `navigator.deviceMemory`, brauzer/OT ni yig'ib backendga yuboring.
   Backend endpoint **tayyor** (6-band uchun, pastga qarang).

#### Hozir tekshirib ko'rish uchun

- Qotish bo'lgan kompyuterda dars paytida Chrome **Task Manager** (Shift+Esc) da brauzer CPU foizini ko'ring; 80–100% bo'lsa sabab shu.
- `chrome://webrtc-internals` → kamera `outbound-rtp` da `qualityLimitationReason` (`cpu` bo'lsa tasdiqlanadi) va `framesPerSecond`.
- Taqqoslash: faqat kamera (ekran ulashishsiz, yozuvsiz) qotadimi? Shunda qaysi qism asosiy yuk ekani ko'rinadi.

#### Alohida eslatma (deploy)

Bugun 11:22 va 11:37 da backend deploy paytida API va WebSocket so'rovlari ~4 va ~16 soniya xato bergan (konteynerlar qayta yaratilgan). Bu videoga emas, chat/bildirishnoma/doskaga ta'sir qiladi.
Jonli dars vaqtida deploy qilmaslik qoidasi qo'llanyapti.

#### Diagnostika endpoint'i (backend tayyor)

`POST /api/v1/live/lesson/{lesson_id}/client-health/` — darsda har ~30 soniyada yuboring (o'qituvchi ham, o'quvchi ham; faqat shu darsning o'qituvchisi/yozilgan o'quvchisi, aks holda `404`).
Chastota cheklovi: **12 so'rov/daqiqa** (oshsa `429`). Javob: `201 {"id": "..."}`. Kerakmas maydonlar tashlab yuborilsa bo'ladi, noma'lum maydonlar e'tiborga olinmaydi.

```json
{
  "cpu_constrained": true,
  "hardware_concurrency": 8,
  "device_memory": 8,
  "connection_quality": "good",
  "page_visible": true,
  "events": ["cpu_constrained"],
  "tracks": [
    { "source": "camera", "fps": 9.5, "width": 1280, "height": 720,
      "target_bitrate": 1700000, "bitrate": 400000,
      "quality_limitation_reason": "cpu", "packets_lost": 0, "jitter": 0.004, "rtt": 35 },
    { "source": "screen_share", "fps": 15, "width": 1920, "height": 1080, "quality_limitation_reason": "none" }
  ]
}
```

- `tracks[].source`: `camera` | `screen_share` | `microphone` | `screen_share_audio` (ko'pi bilan 8 ta). `quality_limitation_reason`: `none` | `cpu` | `bandwidth` | `other`
  (`getSenderStats()` / `outbound-rtp` dan). Raqamlar sonlar bo'lishi kerak (matn emas), `fps` ≤ 240, o'lcham ≤ 8192.
- `connection_quality`: `excellent` | `good` | `poor` | `lost` | `unknown` (LiveKit `ConnectionQuality`). `events`: ko'pi bilan 10 ta qisqa matn (masalan `cpu_constrained`, `reconnecting`).
- Xato bo'lsa `400` (`error.details` da qaysi maydon).
- Admin ko'radi: `GET /api/v1/monitoring/client-health/?hours=24&lesson=<id>&user=<id>` — foydalanuvchilar kesimida xulosa (CPU tufayli sifati tushgan hisobotlar soni, eng past FPS,
  protsessor yadrolari, xotira, brauzer) va so'nggi hisobotlar. Hisobotlar 14 kun saqlanadi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_ROL_ALMASHTIRISH_2026-11-12

> Avvalgi fayl: `FRONTEND_ROL_ALMASHTIRISH_2026-11-12.md`

### Frontend uchun: o'quvchi hisobidan rolga o'tish (`BACKEND_ROL_ALMASHTIRISH.md` javobi)

Backend tayyor va production'ga chiqarilgan (`77217a2`). Frontend'dan boshqa o'zgarish talab qilinmaydi: o'quvchi profilidagi
"Akkauntni almashtirish" oynasidagi **O'qituvchi** va **Kuzatuvchi** qatorlari endi xatosiz ishlaydi.

#### Nima o'zgardi

`POST /api/v1/auth/switch-role/ {role}` o'quvchi hisobidan ham ishlaydi (avval `403`: "O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi").
Boshqa tekshiruvlar avvalgidek.

#### Xatti-harakat

- `role`: `teacher` | `parent` | `student`.
- Shu telefon raqamida o'sha rol **allaqachon bor bo'lsa** — shunga o'tiladi (ikkinchisi yaratilmaydi).
- **Yo'q bo'lsa** — ro'yxatdan o'tishsiz avtomatik ochiladi (parolsiz, bir martalik tasodifiy parol bilan; foydalanuvchi keyin "Parolni tiklash"
  orqali o'rnatishi mumkin) va darhol shunga o'tiladi. Ism-familiya va telefon joriy akkauntdan ko'chiriladi.
- Yangi ochilgan o'qituvchi darhol ishlay oladi (`is_approved` odatiy `true`, 2026-10-05 qarori) — "tasdiqlanmagan o'qituvchi" holati chiqmaydi.

#### Javob

`200`:

```json
{ "access": "...", "refresh": "...", "user": { "id": "...", "role": "teacher", "linked_accounts": [ { "id": "...", "role": "student", ... } ], ... } }
```

Yangi `access`/`refresh` ni saqlang (joriy sessiya yangi akkauntniki bo'ladi). `user.linked_accounts` da boshqa rollar (o'quvchi ham) ko'rinadi, shu bilan
orqaga qaytish mumkin: `POST /api/v1/auth/switch/{linked_account_id}/` (avvalgidek, parolsiz).

#### Xatolar

| holat | status | `error.details` |
|---|---|---|
| telefoni yo'q akkaunt | `400` | `role`: "Rol almashtirish uchun avval telefon raqamingizni kiriting." — profilda telefon kiritishni taklif qiling |
| noto'g'ri rol (`teacher`/`parent`/`student` dan boshqa) | `400` | `role` |
| allaqachon shu roldasiz | `400` | `role`: "Siz allaqachon shu roldasiz." |
| shu rol-akkaunt faolsizlantirilgan | `403` | — |
| token yo'q/eskirgan | `401` | — |

Chastota cheklovi: `auth` scope (login bilan bir xil) — tez-tez bosilsa `429`.

#### Tekshirish ro'yxati

- Telefoni bor o'quvchi → `{role: "teacher"}` → `200`, yangi tokenlar, `linked_accounts` da `student` bor.
- O'quvchi → `{role: "parent"}` → `200`.
- Shu raqamda o'qituvchi allaqachon bor → shunga o'tadi, `user.id` mavjud akkauntniki.
- Telefonsiz o'quvchi → `400`, `error.details.role`.


[↑ Mundarija](#mundarija)

---

## FRONTEND_ROL_ALMASHTIRISH_2026-11-12_2

> Avvalgi fayl: `FRONTEND_ROL_ALMASHTIRISH_2026-11-12_2.md`

### Frontend uchun: o'quvchi hisobidan rol almashtirish — qoida aniqlashtirildi (2026-11-12, 2-qism)

Oldingi `FRONTEND_ROL_ALMASHTIRISH_2026-11-12.md` dagi "o'quvchi hisobidan har qanday rolga o'tish mumkin" qoidasi **o'zgardi**. Backend production'da (`770ce7f`).

#### Yangi qoida

- **O'qituvchi yoki kuzatuvchidan o'quvchi rolini ochib o'tgan** foydalanuvchi (boshqa rol-akkaunti bor) — `POST /auth/switch-role/` ishlaydi: orqaga qaytadi (`teacher`/`parent`) va yangi rol ham ocha oladi.
- **O'zi o'quvchi bo'lib ro'yxatdan o'tgan va boshqa akkaunti yo'q** foydalanuvchi — `switch-role` `403` qaytaradi: "O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi."
- Telefoni yo'q bo'lsa — avvalgidek `400` (`error.details.role`).

#### `GET /auth/me/` da yangi qiymat

`role_switch_blocked` endi uch xil:

| qiymat | ma'nosi | nima qilish |
|---|---|---|
| `null` | almashtirish mumkin | "Akkauntni almashtirish" bo'limini ko'rsating, `available_roles` dagi rollarni taklif qiling |
| `"phone_required"` | telefon yo'q | telefon kiritishni taklif qiling |
| `"student_not_allowed"` | **yangi**: o'zi o'quvchi bo'lib kirgan, boshqa akkaunti yo'q | almashtirish bo'limini umuman ko'rsatmang (`available_roles` ham bo'sh) |

#### Xatolar jadvaliga qo'shimcha

| holat | status | `error.details` |
|---|---|---|
| o'zi o'quvchi bo'lib kirgan, boshqa akkaunti yo'q | `403` | — |

#### Tekshirish ro'yxati

- Oddiy o'quvchi (boshqa akkauntsiz) → `me.role_switch_blocked == "student_not_allowed"`, bo'lim ko'rinmaydi; `switch-role` → `403`.
- O'qituvchi → `{role: "student"}` → `200` → shu o'quvchidan `{role: "teacher"}` → `200`, o'sha o'qituvchi akkauntiga qaytadi.
- O'qituvchidan ochilgan o'quvchi → `{role: "parent"}` → `200`.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-12

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-12.md`

### Frontend uchun: 12-noyabr, uchinchi backend vazifalari javobi

Hammasi backendda tayyor va sinalgan.

---

#### 1. Bazadan berish: har guruh uchun aniq o'quvchilar ro'yxati (`targets`)

`POST /homework/assignments/{id}/assign/` endi `targets` qabul qiladi:

```json
{
  "targets": [
    { "course_id": "<guruh>", "student_ids": ["<id>", "<id>"] },
    { "course_id": "<boshqa guruh>" }
  ],
  "due_at": "2026-11-20T23:59:00+05:00",
  "allow_late": true,
  "announce_in_chat": true
}
```

- `student_ids` yo'q yoki bo'sh — **butun guruhga** (chat kartasi bilan, `announce_in_chat` bo'yicha).
- `student_ids` bor — faqat shu guruh o'quvchilariga: nusxaning `assigned_students` i `_publish`dan **oldin** o'rnatiladi, bildirishnoma faqat ularga boradi,
  chat kartasi yuborilmaydi (chat butun guruhga ko'rinadi). Tanlanmaganlar vazifani ko'rmaydi (`404`).
- Guruhning **hamma** o'quvchisi tanlangan bo'lsa, backend uni butun guruh deb hisoblaydi (karta ham yuboriladi).
- Bir o'quvchi bir nechta guruhda (guruh + club) bo'lsa ham muammo yo'q: `course_id` aniq ko'rsatiladi.
- Xatolar (`400`): `error.details.targets["<indeks>"]` ichida — `student_ids` (o'quvchi shu guruhda emas), `course_id` (yo'q yoki ikki marta kiritilgan).
  Guruh o'qituvchiniki bo'lmasa `403`. Xato bo'lsa hech narsa yaratilmaydi.
- `targets` berilsa eski `course_ids` / `student_ids` e'tiborga olinmaydi. Eski shakl avvalgidek ishlayapti (o'zgarmagan).
- Javob avvalgidek: `201 {count, assignments: [...]}`.

Frontend: "Bazadan berish" oynasida har tanlangan guruh uchun `{course_id, student_ids}` yuboring (hammasi belgilangan bo'lsa `student_ids`ni tashlab yuborsangiz ham bo'ladi).
"Butun guruhga bering, keyin cheklang" xabari endi kerak emas.

#### 2. Test ro'yxatida urinishlar va boshlangan seans

`GET /quizzes/` (o'quvchi) har elementida yangi maydonlar:

| maydon | ma'nosi |
|---|---|
| `attempts_used` | topshirilgan urinishlar + vaqti tugab sarflanganlari |
| `attempts_left` | `null` — cheklov yo'q; `0` — urinishlar tugagan |
| `session_ends_at` | boshlangan va hali tugamagan vaqtli seansning `ends_at`; yo'q bo'lsa `null` |

"Davom etish · 12:34 qoldi" ni `session_ends_at` dan ko'rsating. O'qituvchi/admin ro'yxatida bu uch maydon `null`.
Guruhsiz (o'quvchiga ko'rinmaydigan) testlarda ham `null`.

#### 3. Boshlashdan oldin savollar soni

`GET /quizzes/{id}/` (o'quvchi) javobiga `question_count` qo'shildi: shu urinishda tushadigan savollar soni (`questions_per_attempt` hisobga olingan).
`needs_start: true` bo'lib `questions` bo'sh kelganda ham, urinishlar tugaganda ham (`attempts_left: 0`) to'g'ri keladi. Boshlash ekranida "Savollar: N ta" ni shundan oling.

#### 4. Diqqat tekshiruvi: socket push production'da — tasdiqlandi

Production'da (APP, `cron` konteyneri) tekshirildi:
- `cron` `35deda2` dan keyingi kod bilan ishlayapti, `JOBS` da `push_attention` bor.
- `cron` va `ws` konteynerlarida `REDIS_URL` berilgan, kanal qatlami `RedisChannelLayer` (InMemory emas).
- Oxirgi 24 soatda `attention push failed` log'da yo'q.

Hodisa keladimi — jonli darsda o'quvchi doska socketida `{"type": "attention", "check": {...}}` ko'rinishini tekshirish kifoya.

#### 5. Bazadagi vazifaning nusxalari

`GET /homework/assignments/{id}/` (bazadagi vazifa, muallif) javobiga `copies` qo'shildi (yangisi birinchi):

```json
"copies_count": 2,
"copies": [
  { "id": "...", "course_id": "...", "course_title": "...", "due_at": "...", "status": "active",
    "submissions_count": 3, "student_ids": null, "created_at": "..." }
]
```

`student_ids` — `null` bo'lsa butun guruh, ro'yxat bo'lsa faqat shu o'quvchilarga berilgan. `id` bo'yicha shu guruh nusxasiga (`GET /homework/assignments/{id}/`) o'tish mumkin.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-12_2

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-12_2.md`

### Frontend uchun: 12-noyabr, Trello "Todo" kartalari bo'yicha backend yangiliklari

Hammasi backendda tayyor va sinalgan.

---

#### 1. "Count qism larni ko'rib to'g'irlash" — vazifalar ro'yxatidagi "N / M topshirdi"

`GET /homework/assignments/?course=<id>` (o'qituvchi) har elementida yangi maydonlar:

| maydon | ma'nosi |
|---|---|
| `students_count` | vazifa berilgan o'quvchilar (guruh yoki tanlanganlar) |
| `submitted_count` | shulardan topshirganlar (bitta o'quvchi ko'p marta topshirsa ham 1) |
| `pending_review_count` | tekshiruv kutayotganlar (AI yoki o'qituvchi) |
| `graded_count` | o'qituvchi tasdiqlab baholaganlar |

Avvalgi `submissions_count` (jami topshiriq soni) saqlangan. "0 / 0 topshirdi" o'rniga `submitted_count / students_count` ko'rsating.

#### 2. "Homework check da AI ni ko'rib berish" — AI holati

O'qituvchi uchun topshiriq javobida (`GET /homework/submissions/{id}/` va vazifa ichidagi `submissions[]`):

| `ai_state` | ma'nosi | nima ko'rsatish |
|---|---|---|
| `checking` | AI hali tekshirmoqda | "AI tekshirmoqda…" |
| `ready` | ball va natija bor | ball, baho, `ai_result` (savollar kesimida) |
| `unscored` | AI xulosa yozdi, lekin **ball qo'ymadi** | `ai_summary` matnini ko'rsating + "AI ball qo'ymadi — o'zingiz baholang" (oldin oyna "— ball / Baho yo'q" bo'lib bo'sh qolardi) |
| `failed` | AI baholay olmadi (`error`) | "AI baholay olmadi — o'zingiz baholang" |
| `none` | AI ishlatilmagan | AI bo'limini yashiring |

Yangi `ai_summary` (matn yoki `null`) — AI natijasidagi umumiy xulosa. Production'da AI hozir ichki OpenAI orqali ishlayapti (5 ta topshiriqdan 3 tasi baholangan, 1 tasi "baholay olmadi").

#### 3. "ekran share, mic va camera" — hammasi bir martalik ruxsat

Mikrofon va kamera ruxsati avval ham bir martalik edi (`POST /live/release-media/`). Endi **ekran ulashish** ham:

- O'quvchi ulashishni to'xtatgach: `POST /live/release-media/ {lesson_id, kind: "screen"}` (`"screen_share"` ham bo'ladi) → `{revoked, open}`.
- Ruxsat (ekran video + ekran audio) olinadi; qayta ulashish uchun yana so'rov kerak. Mikrofon/kamera ruxsatlariga tegilmaydi.
- Hodisa (doska WebSocket'i): `{"type": "screen_revoked", "student_id": "..."}` — o'quvchi interfeysi "Ruxsat so'rash" holatiga qaytadi, o'qituvchi paneli yangilanadi
  (`mic_revoked` / `camera_revoked` kabi).
- Hammasi uchun qoida: o'quvchi mikrofon/kamera/ekranni **o'zi o'chirgan/to'xtatgan zahoti** `release-media` ni chaqiring.

#### 4. "O'qituvchi tomonidan notification" — o'qituvchi + guruh nomi, xabar matni

O'qituvchi yozgan xabarda (`POST /notifications/send/`, `kind` yo'q) sarlavha va ma'lumot endi:

- `title`: **"O'qituvchi ismi · Guruh nomi"** (guruhsiz yuborilsa faqat ism; ism bo'lmasa login). Inbox ro'yxati, WebSocket va push bildirishnomada bir xil.
- `body`: o'qituvchi yozgan matnning o'zi (HTML'siz).
- `data`: `{teacher_name, course_id, course_title}` (guruhga yuborilganda).
- Tizim xabarlari (`kind` bor: dars eslatmasi, vazifa va h.k.) sarlavhasi avvalgidek.
- Web push va mobil push sarlavhasi ham shu ("Fokus" o'rniga).

#### 5. "video record qilish qism" — yozuvni guruhga yuborishni darsga kirgach so'rash

O'qituvchi darsga kirgach: "Dars yozuvi tayyor bo'lgach guruhga tashlansinmi?" deb so'raladi.

- `GET /lessons/{id}/recording-choice/` → `{post_recording: true|false|null, decided: bool}`; `null` / `decided: false` — hali tanlanmagan, **so'rang**.
- `PATCH /lessons/{id}/recording-choice/ {post_recording: true|false}` — tanlov saqlanadi (faqat dars o'qituvchisi; boshqa qiymat `400`).
- Dars javobida (`GET /lessons/{id}/`) ham `post_recording` (`true|false|null`) bor.
- Dars tugaganda (`POST /lessons/{id}/finish/`) `post_recording` yuborilmasa shu tanlov ishlatiladi (tanlanmagan bo'lsa `true`); yuborilsa — yuborilgani ustun.

#### 6. "account almashtirish ishlamayapdi"

`GET /auth/me/` ga ikkita maydon qo'shildi — "Akkauntni almashtirish" oynasini aniq chizish uchun:

- `available_roles`: hali **ochilmagan** rollar (`["teacher", "parent", "student"]` dan joriy va allaqachon bog'langanlari chiqarilgan). Shu ro'yxatdagi har bir rol uchun
  "ochib o'tish" qatori (`POST /auth/switch-role/ {role}`).
- `role_switch_blocked`: telefon raqami yo'q bo'lsa `"phone_required"` (`available_roles` bo'sh bo'ladi) — oynada "Avval profilga telefon raqamini kiriting" deb ko'rsating.
  Telefoni bor bo'lsa `null`.
- Mavjud bog'langan akkauntlar avvalgidek `linked_accounts` da (`POST /auth/switch/{id}/`).
- Production ma'lumoti: foydalanuvchilarning ~1/3 qismida telefon yo'q (bunday akkauntlar almashtira olmaydi), faqat bitta telefon raqamida ikkita rol bor.
  Ko'pchilikda "boshqa rol" hali ochilmagan bo'lgani uchun oynada faqat o'zi ko'rinishi normal; qolgan rollar `available_roles` dan chiziladi.

#### 7. "spam berish adminga borishi kerak" — mavjud oqim (o'zgarmagan)

Backend 10-noyabrda tayyor. Qisqacha:
1. Shaxsiy chatda `POST /chat/rooms/{id}/report/ {reason, comment?}` (`reason`: `insult` | `harassment` | `advertising` | `other`) — chat darhol `spam` holatiga o'tadi.
2. **Barcha adminlarga** bildirishnoma boradi (`kind: "spam_report"`, `link_type: "spam_report"`, `link_id` — shikoyat id).
3. Admin paneli: `GET /admin/reports/?status=open|resolved|dismissed`, `GET /admin/reports/{id}/` (oxirgi 10 xabar bilan),
   `POST /admin/reports/{id}/resolve/` (to'g'ri, chat bloklangan qoladi), `.../dismiss/` (asossiz, chat qayta ochiladi), `.../unblock/` (istalgan paytda qayta ochish).
Production'da hozircha birorta shikoyat yo'q (sinab ko'ring).

#### 8. "video qotib qoldi" — diagnostika

Alohida hujjat: `FRONTEND_QOTISH_TAHLILI_2026-11-12.md` (sabab tahlili, tavsiyalar va `client-health` endpoint'i).


[↑ Mundarija](#mundarija)

---

## FRONTEND_AKKAUNT_BOGLASH_2026-11-13

> Avvalgi fayl: `FRONTEND_AKKAUNT_BOGLASH_2026-11-13.md`

### Frontend uchun: akkauntlarni bog'lash xavfsizligi (`BACKEND_VAZIFALAR_2026-11-12.md` javobi)

Tanlangan variant: **A (aniq bog'lanish)**. Backend production'ga chiqariladi, shundan keyin frontend parol so'rash oynasini qo'shadi.
Oldingi hujjatlar (`FRONTEND_ROL_ALMASHTIRISH_2026-11-12*.md`) o'z kuchida, faqat quyidagi o'zgarishlar bor.

#### Nima o'zgardi

- Akkauntlar endi **telefon raqami bir xil bo'lgani uchun bog'lanmaydi**. Bog'lanish faqat ikki yo'l bilan paydo bo'ladi:
  1. `POST /auth/switch-role/` bilan yangi rol-akkaunt **ochilganda** (u joriy sessiyadan ochilgani uchun shu odamniki) — avtomatik bog'lanadi;
  2. boshqa akkauntning **parolini kiritib** `POST /auth/account-links/` orqali.
- `GET /auth/me/` → `linked_accounts` faqat aniq bog'langanlarni qaytaradi. Profilda telefon raqami o'zgarsa, bog'lanish o'zgarmaydi.
- `POST /auth/switch/{id}/` faqat bog'langan akkauntga ishlaydi (aks holda `403`, avvalgidek).
- Shu rol shu raqamda bor, lekin **bog'lanmagan** bo'lsa, `switch-role` endi o'tkazmaydi — `409` qaytaradi (pastga qarang).
- Production'dagi mavjud ma'lumotlar: avval `switch-role` bilan ochilgan juftliklar avtomatik bog'langan deb ko'chiriladi. Faqat "raqami bir xil" bo'lgan eski juftliklar
  bog'lanmagan bo'ladi — ular keyingi o'tishda parol kiritadi. Shuning uchun almashtirish oynasida **bog'lanmagan akkaunt chiqmay qolishi** normal.

#### 1. `POST /auth/account-links/` — parol bilan bog'lash

So'rov (kirgan foydalanuvchi tokeni bilan):

```json
{ "username": "ustoz_ali", "password": "u akkauntning paroli" }
```

Muvaffaqiyatli — `201`:

```json
{
  "account": { "id": "...", "username": "ustoz_ali", "role": "teacher" },
  "linked_accounts": [ { "id": "...", "username": "ustoz_ali", "role": "teacher", ... } ]
}
```

Shundan keyin ikkalasi bir-biriga parolsiz o'tadi (`POST /auth/switch/{account.id}/`). Joriy sessiya o'zgarmaydi, yangi token berilmaydi.
Bog'lash ikki tomonlama va **o'tuvchan**: A–B va B–C bog'langan bo'lsa, A, B, C hammasi bitta guruhda.
Bu endpoint **har qanday rol uchun** ishlaydi, o'quvchi uchun ham (`role_switch_blocked == "student_not_allowed"` bo'lsa ham) — o'quvchi boshqa akkauntini parol bilan bog'lashi mumkin.

##### Xatolar

| holat | status | `error.code` | `error.details` | nima qilish |
|---|---|---|---|---|
| login yoki parol noto'g'ri (yoki bunday login yo'q — bir xil javob) | `400` | `invalid` | `password`: "Login yoki parol noto'g'ri." | maydonda xato ko'rsating |
| o'z akkauntingiz | `400` | `invalid` | `username` | |
| shu rolda akkaunt allaqachon bog'langan | `400` | `invalid` | `username`: "Bu rolda akkaunt allaqachon bog'langan." | |
| allaqachon bog'langan | `400` | `invalid` | `username` | oddiy `switch` qiling |
| admin/boshqa tizim akkaunti | `400` | `invalid` | `username` | |
| u akkauntda ikki bosqichli himoya yoqilgan | `400` | `two_factor_enabled` | — | "Bu akkauntni bog'lab bo'lmaydi (2FA yoqilgan)" |
| ketma-ket 5 marta noto'g'ri parol | `429` | `throttled` | `retry_after` soniyada (15 daqiqa) | kutishni ko'rsating |
| umumiy chastota cheklovi (`auth` scope) | `429` | | | |
| token yo'q/eskirgan | `401` | | | |

#### 2. `POST /auth/switch-role/` — yangi `409` holat

Shu raqamda o'sha rolda akkaunt bor, lekin joriy akkauntga bog'lanmagan bo'lsa:

```json
{
  "success": false,
  "error": {
    "code": "account_exists",
    "message": "Bu rolda akkaunt bor. Bog'lash uchun uning parolini kiriting.",
    "details": { "detail": "...", "account": { "id": "...", "username": "ustoz_ali", "role": "teacher" } }
  }
}
```

Frontend: parol so'rash oynasini oching ("`ustoz_ali` (O'qituvchi) akkauntining parolini kiriting"). Parol kiritilsa — `POST /auth/account-links/ {username: details.account.username, password}`,
`201` kelgach — **`switch-role` ni qayta yuboring** (endi bog'langan, shu akkauntga o'tadi, `200` + tokenlar).

Qolgan xatolar (telefon yo'q `400`, noto'g'ri rol `400`, o'zi o'quvchi bo'lib kirgan `403`, faolsizlantirilgan `403`) o'zgarmagan.

#### 3. Almashtirish oynasi (tavsiya)

- Ro'yxat: `me.linked_accounts` — bosilsa `POST /auth/switch/{id}/` (parolsiz, avvalgidek).
- "Boshqa akkauntni bog'lash" tugmasi: `username` + `password` oynasi → `POST /auth/account-links/`. Oddiy (boshqa akkauntsiz) o'quvchida ham ko'rsating.
- Hali ochilmagan rollar: `me.available_roles` → `switch-role`. `409 account_exists` kelsa yuqoridagi parol oynasi.

#### Tekshirish ro'yxati

- Bir xil raqam bilan alohida ro'yxatdan o'tgan ikki akkaunt: `me.linked_accounts` bo'sh; `switch/{id}/` → `403`; `switch-role` → `409 account_exists`.
- Parolni to'g'ri kiritib bog'lash → `201`, keyin ikkala tomondan parolsiz o'tiladi.
- Noto'g'ri parol → `400`; 5 marta ketma-ket → `429`.
- O'qituvchidan `switch-role` bilan ochilgan kuzatuvchi/o'quvchi akkaunti: ikkala tomonga parolsiz o'tiladi (oqim buzilmagan).
- Profilda raqamni boshqa akkaunt raqamiga o'zgartirish `linked_accounts` ga ta'sir qilmaydi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_HOMEWORK_OVOZ_2026-11-13

> Avvalgi fayl: `FRONTEND_HOMEWORK_OVOZ_2026-11-13.md`

### Frontend uchun: Speaking (ovozli) uy vazifasi — brauzerda yozilgan ovoz endi qabul qilinadi

#### Muammo

Speaking vazifasiga faqat `.mp3 .wav .m4a .ogg` qabul qilinardi. Brauzer (`MediaRecorder`) esa odatda boshqa format beradi:

| brauzer | odatiy format | fayl kengaytmasi |
|---|---|---|
| Chrome, Edge, Firefox (Android ham) | `audio/webm;codecs=opus` | `.webm` |
| Safari / iPhone | `audio/mp4` | `.mp4` yoki `.m4a` |

Shuning uchun ilovada yozilgan ovoz `400` ("'.webm' qo'llab-quvvatlanmaydi") bilan rad etilardi.

#### Nima o'zgardi

Speaking vazifasida endi qabul qilinadi: `.mp3 .wav .m4a .ogg .webm .mp4 .flac .oga .opus` (25 MB gacha, bir topshiriqda ko'pi bilan 5 ta fayl — avvalgidek).
AI tekshiruvi (ovozni matnga aylantirish va baholash) hammasi uchun bir xil ishlaydi; javob formati o'zgarmagan.
Speaking bo'lmagan vazifaga audio yuklansa — avvalgidek `400`: "Audio faqat Speaking vazifalari uchun."

#### Frontend uchun

- Yozilgan blob'ni yuborganda fayl nomining kengaytmasi **blob turiga mos** bo'lsin: `blob.type.includes('webm') ? 'voice.webm' : 'voice.mp4'` (Safari).
  Kengaytma bo'lmasa yoki noto'g'ri bo'lsa backend `400` qaytaradi.
- `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` bo'lmasa `audio/mp4` ni sinab ko'ring.
- Xato matni `error.details.file` da keladi — foydalanuvchiga ko'rsating.

#### Tekshirish ro'yxati

- Chrome'da yozilgan `voice.webm` → Speaking vazifaga `201`, keyin AI natijasi (`source: "audio-transcript"`).
- Safari/iPhone'da yozilgan `voice.mp4` → `201`.
- Writing vazifasiga `voice.webm` → `400`.


[↑ Mundarija](#mundarija)

---

## FRONTEND_HOMEWORK_OVOZ_2026-11-13_2

> Avvalgi fayl: `FRONTEND_HOMEWORK_OVOZ_2026-11-13_2.md`

### Frontend uchun: Speaking uy vazifasiga ovoz yuborish (yangi eslatma)

Holat: backend **productionda ishlayapti** (2026-11-13 deploy qilingan). Frontend tomonidan faqat yuborish kodini tekshirish kerak.

#### 1. Nima o'zgardi

Speaking vazifasiga endi brauzerda yozilgan ovoz ham qabul qilinadi. Qabul qilinadigan kengaytmalar:

`.mp3 .wav .m4a .ogg .webm .mp4 .flac .oga .opus`

- Hajm: bitta fayl 25 MB gacha, bir topshiriqda ko'pi bilan 5 ta fayl (avvalgidek).
- AI tekshiruvi (ovozni matnga aylantirish va baholash) hamma formatda bir xil ishlaydi.
- Javob formati o'zgarmagan.
- Speaking bo'lmagan vazifaga (Writing va boshqalar) audio yuborilsa: `400`, "Audio faqat Speaking vazifalari uchun."

#### 2. Nega avval ishlamagan

`MediaRecorder` beradigan format brauzerga bog'liq, avval esa faqat `.mp3 .wav .m4a .ogg` qabul qilinardi:

| Brauzer | Format | Fayl kengaytmasi |
|---|---|---|
| Chrome, Edge, Firefox (Android ham) | `audio/webm;codecs=opus` | `.webm` |
| Safari / iPhone | `audio/mp4` | `.mp4` yoki `.m4a` |

Shu sabab yozilgan ovoz `400` bilan qaytarilardi.

#### 3. Frontend nima qilishi kerak

Fayl nomining kengaytmasi blob turiga mos bo'lishi shart. Backend turni kengaytmaga qarab aniqlaydi, kengaytma bo'lmasa yoki noto'g'ri bo'lsa `400` qaytaradi.

```js
// yozishni boshlashdan oldin qo'llab-quvvatlangan formatni tanlang
const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
  ? 'audio/webm;codecs=opus'
  : 'audio/mp4'; // Safari / iPhone

const recorder = new MediaRecorder(stream, { mimeType });

// yuborishda
const blob = new Blob(chunks, { type: recorder.mimeType });
const ext = blob.type.includes('webm') ? 'webm' : 'mp4';

const form = new FormData();
form.append('file', blob, `voice.${ext}`); // kengaytma blob turiga mos
```

Eslatma: `file` maydon nomini mavjud submission endpoint'dagi nom bilan bir xil qoldiring, bu yerda faqat fayl nomi va kengaytma muhim.

Xato bo'lsa matn `error.details.file` da keladi, uni foydalanuvchiga ko'rsating.

#### 4. Tekshirish ro'yxati

- Chrome'da yozilgan `voice.webm` Speaking vazifaga yuborilsa `201`, keyin AI natijasi keladi (`source: "audio-transcript"`).
- Safari / iPhone'da yozilgan `voice.mp4` yuborilsa `201`.
- Writing vazifasiga `voice.webm` yuborilsa `400` (kutilgan xatti-harakat).
- Hali ham xato bo'lsa: brauzer konsolidagi xato va javob tanasini (response body) backendga yuboring.


[↑ Mundarija](#mundarija)

---

## FRONTEND_DARSGA_KIRISH_2026-11-15

> Avvalgi fayl: `FRONTEND_DARSGA_KIRISH_2026-11-15.md`

### Frontend uchun: o'quvchi darsga faqat o'qituvchi boshlagandan keyin kiradi

#### Qoida

O'quvchi `POST /api/v1/live/token/` orqali darsga **faqat dars `live` bo'lgandan keyin** (o'qituvchi boshlagandan keyin) kira oladi.
Rejalashtirilgan soatdan ertaroq yoki kechroq boshlangani muhim emas: o'qituvchi qachon boshlasa, o'quvchi shundan keyin kiradi.

| holat | o'qituvchi | o'quvchi |
|---|---|---|
| dars `scheduled` (hali boshlanmagan), vaqti bugun, kelajak yoki o'tgan kun | kira oladi va darsni boshlaydi | `400` |
| dars `live` | kira oladi | kira oladi (`200`) |
| dars `finished` / `cancelled` | `400` | `400` |

Avval bugungi yoki kelajakdagi `scheduled` darsga o'quvchi o'qituvchidan oldin kira olardi. Endi kira olmaydi, chunki hech kim o'tkazmayotgan darsga "kirdi" davomati yozilib qolardi.

#### Xato javobi

O'quvchi dars boshlanmasdan so'rasa:

```json
{
  "success": false,
  "error": {
    "code": "invalid",
    "message": "Dars hali boshlanmagan. O'qituvchi boshlagandan keyin kira olasiz.",
    "details": {}
  }
}
```

#### Frontend uchun

- O'quvchi uchun "Darsga kirish" tugmasini faqat `lesson.status === 'live'` bo'lganda yoqing.
- `scheduled` bo'lsa tugma o'chiq turadi, yonida "O'qituvchi darsni boshlashini kuting" deb yozing.
- Tugma bosilganda `400` kelsa, xabarni (`error.message`) foydalanuvchiga ko'rsating, spinnerda qoldirmang.
- Dars `live` ga o'tganini bilish uchun darslar ro'yxatini vaqti-vaqti bilan yangilab turing yoki chat'dagi "jonli dars boshlandi" signalidan foydalaning (o'qituvchi kirganda guruh chatiga yuboriladi).
- O'qituvchi tomonida o'zgarish yo'q: u istalgan vaqtda, hatto vaqti o'tib ketgan darsni ham kirib boshlay oladi.

#### Tekshirish ro'yxati

- `scheduled` darsga o'quvchi bilan token so'rang: `400` va yuqoridagi xabar. Davomat yozilmaydi.
- O'qituvchi kirgach (`live`) o'quvchi token so'rasa: `200`, davomat yoziladi.
- Dars rejadan oldin (ertaroq) boshlansa ham, kechikib boshlansa ham o'quvchi shundan keyin kiradi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16

> Avvalgi fayl: `FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md`

### Backend javobi: darsga taklif bildirishnomasida havola qo'shildi (Trello 60)

#### Nima o'zgardi

O'qituvchi `POST /api/v1/live/invite/` orqali o'quvchilarni chaqirganda ketadigan bildirishnomada endi quyidagilar bor:

| maydon | qiymat |
|---|---|
| `kind` | `lesson_invite` |
| `link_type` | `lesson` |
| `link_id` | dars id'si (UUID matn) |
| `title` | `Darsga taklif` |

`link` (tuzilgan ko'rinish) ham `{ "kind": "lesson", "id": "<dars id>" }` bo'lib keladi. `category` o'zgarmadi (`announcement`).

Frontendda o'zgarish kerak emas: `link_type == 'lesson'` bildirishnoma `/live/{id}` sahifasini ochadi.

#### Eslatma

- Bildirishnomani bosgan o'quvchi darsga faqat dars `live` bo'lsa kira oladi. Taklif o'qituvchi darsni boshlagandan keyin ketadi, shuning uchun odatda dars `live` bo'ladi.
- Push bildirishnomada ham xuddi shu `link_type` / `link_id` boradi.

#### Tekshirish

1. O'qituvchi darsni vaqtidan oldin boshlaydi va "Hammani chaqirish" ni bosadi.
2. O'quvchiga "Darsga taklif" sarlavhali bildirishnoma keladi.
3. Bosilganda `/live/{lesson_id}` ochiladi va o'quvchi darsga kiradi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16

> Avvalgi fayl: `FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md`

### Backend javobi: ekran ulashish o'chirib-yoqilganda yozuv uzilmasin (Trello 62)

#### Natija

Frontend yuboradigan ma'lumotda o'zgarish yo'q (`POST /lessons/{id}/recording/video/`: `chunk`, `session`, `index`, `started_at`).
Backend tomonida yozuvni birlashtirish kodi mustahkamlandi.

#### Backendda nima o'zgardi

| xavf | nima qilindi |
|---|---|
| Sessiyalar har xil o'lchamda (oyna almashtirildi) | Eng uzoq sessiya kadri asos qilinadi. Boshqa o'lchamli sessiyalar shu kadrga sig'diriladi (nisbat saqlanadi, bo'sh joy qora) va shundan keyin ulanadi. Eng uzoq sessiya qayta kodlanmaydi |
| Yakuniy MP4 da o'lcham o'rtada o'zgaradi | MP4 qat'iy o'lchamda chiqadi (birinchi kadr o'lchami, eni 1280 gacha). Boshqa o'lchamli kadrlar cho'zilmaydi, qora chiziq bilan joylashadi |
| Ko'p sessiya (10-20 marta to'xtatib-yoqish) | Bitta sessiyaning `started_at` yo'q bo'lsa ham qolgan tanaffuslar to'ldiriladi. Avval hammasi o'chib qolardi. Vaqt aniqlanmaganda qolgan sessiyalar tashlab yuborilardi, endi ulanadi |
| Juda qisqa sessiya (1-2 soniya, kadrsiz) | O'qib bo'lmaydigan bo'lak tashlanadi, uning vaqti keyingi tanaffusga qo'shiladi |

Tanaffus paytida videoda oxirgi kadr qotib turadi (avvalgidek). Boshqa ko'rinish kerak bo'lsa, mahsulot egasi bilan kelishib, ayting.

#### Tekshirildi

Haqiqiy `ffmpeg` va `mkvmerge` bilan avtomatik testlarda:
- har xil o'lchamli 3 ta sessiya (128x72, 110x80) bitta uzluksiz videoga ulanadi, davomiyligi tanaffuslar bilan mos;
- 12 ta qisqa sessiya hammasi yozuvda bor;
- o'lchami o'zgargan fayldan yakuniy MP4 qat'iy o'lchamda, xatosiz chiqadi;
- avvalgi yozuv testlari (tanaffus, oxirini tenglash, tiklash) hammasi o'tadi.

#### Tekshirilmagan (frontend/QA bilan real brauzerda ko'rish kerak)

- Chrome'da haqiqiy oyna almashtirish va "Share this tab instead" bilan to'liq dars.
- Qabul mezonidagi 1-6 ssenariylar real darsda. Avtomatik testlar ularning asosiy qismini (ko'p sessiya, har xil o'lcham, ekran to'xtatilgan holda oxirini tenglash) fayl darajasida yopadi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17

> Avvalgi fayl: `FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md`

### Backend javobi: guruh papkasida video va doska soni (Materiallar)

#### Nima o'zgardi

`GET /api/v1/materials/courses/` javobidagi har guruhga 2 ta maydon qo'shildi:

| maydon | ma'nosi |
|---|---|
| `recording_count` | guruhdagi video yozuvi bor darslar soni |
| `board_count` | guruhdagi doskasi bo'sh bo'lmagan darslar soni |

`file_count` o'zgarmadi.

```json
[
  { "id": "…", "title": "Ingliz Tili A1", "kind": "group", "subject": "english", "file_count": 2, "recording_count": 3, "board_count": 1 }
]
```

Frontendda o'zgarish kerak emas, tayyor kod yangi maydonlarni o'zi oladi.

#### Qoidalar (guruh ichidagi dars ro'yxati bilan bir xil)

- Bekor qilingan va o'chirilgan darslar sanalmaydi.
- Doska: bitta darsda bir nechta varaq bo'lsa ham 1 deb sanaladi. Faqat chizilgan varaq hisobga olinadi, bo'sh varaq sanalmaydi.
- Video, o'qituvchi va admin: yozuvi bor har dars sanaladi (hali birlashayotgan yoki o'girilayotgani ham).
- Video, o'quvchi va ota-ona: faqat tayyor yozuv sanaladi. MP4 ga o'girilayotgan yozuv tayyor bo'lgach sanaladi.

Shuning uchun son dars ro'yxatidagi `has_recording` va `has_board` belgilari soniga teng chiqadi.

#### Tekshirildi

Avtomatik testda: o'qituvchi, o'quvchi va ota-ona uchun sonlar, ko'p varaqli doska (1 ta), bo'sh varaq, bekor qilingan va o'chirilgan dars, boshqa guruh aralashmasligi, birlashayotgan yozuv tayyor bo'lgach o'quvchi soni oshishi, dars ro'yxati bilan moslik.

#### Tekshirish (QA)

1. O'qituvchi: yozilgan va doskaga chizilgan, fayl yuklanmagan dars bor guruh. Kutiladi: `file_count: 0`, `recording_count: 1`, `board_count: 1`.
2. O'quvchi: shu guruhda yozuv hali o'girilmoqda. Kutiladi: `recording_count: 0`. Tayyor bo'lgach `1`.
3. Bekor qilingan yoki o'chirilgan dars sanalmaydi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17

> Avvalgi fayl: `FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md`

### Frontend ulamagan backend endpointlari — aniq ro'yxat (2026-11-17)

Backend marshrutlari (294 ta yo'l) frontend repo'si `krv006/YolUp_Web` (`main`, `0df424b`) bilan yo'l bo'yicha taqqoslandi,
so'ng har bir endpoint backend kodidan o'qib chiqildi. Hamma yo'llar `/api/v1/` bilan boshlanadi. Auth: `Authorization: Bearer <access>`.

> **Tuzatish.** Avval "23 ta" degan edim. Aniqrog'i **21 ta**: 2 tasi endpoint emas, DRF'ning ko'rsatkich sahifalari
> (`/api/v1/` va `/api/v1/chat/`). Bu 21 tadan **7 tasi frontendga allaqachon ulangan** (boshqa yo'l bilan yoki serverdan kelgan havola orqali),
> shuning uchun **haqiqatan ulanmagani 14 ta**.

#### Qisqa xulosa

| Guruh | Soni | Frontend nima qilsin |
|---|---|---|
| **A. Hozir ishlaydi, UI yo'q** | 3 | Ulash mumkin va kerak: [1](#1-uy-vazifasi-sahifadan-chiqib-kirish), [2](#2-kanaldan-guruhni-ajratish), [3](#3-adminga-mijoz-salomatligi-xulosasi) |
| **B. Tayyor, lekin serverda xizmat ulanmagan** | 11 | UI'ni tayyorlash mumkin, lekin ishlashi uchun biz tashqi kalit/xizmat ulashimiz kerak ([4](#4-sms-va-email-tasdiqlash-8-ta), [5](#5-google--apple-bilan-kirish), [6](#6-mobil-push-faqat-mobil-ilova)) |
| **C. Allaqachon ulangan (yolg'on signal)** | 3 | Hech narsa qilmang: havola javob ichida keladi ([7](#7-javob-ichida-keladigan-havolalar-ulangan)) |
| **D. Eskirgan takror (alias)** | 4 | Hech narsa qilmang: frontend yangisidan foydalanadi ([8](#8-takror-yollar-alias)) |

---

#### A. Hozir ishlaydi — frontend UI'si yo'q (3 ta)

##### 1. Uy vazifasi sahifasidan chiqib-kirish

`POST /api/v1/homework/assignments/{assignment_id}/focus/` — **o'quvchi** (ruxsat `homework.submit`).

```json
{ "kind": "exit" }      // sahifadan chiqdi (tab almashtirdi / oynadan chiqdi)
{ "kind": "return" }    // qaytdi
```
- Javob `200 {"ok": true}`.
- Xatolar: `400 {"kind": ["exit yoki return."]}`, `403` (o'quvchi shu kursga yozilmagan), `404` (vazifa yo'q).
- **Nega kerak:** o'qituvchi topshirilgan ishni ochganda javobda `focus` maydoni keladi:
  `{exits, away_seconds, longest_seconds, on_page_seconds, total_seconds, timeline:[{left_at, returned_at, seconds}]}`.
  Frontend bu hodisalarni hech qachon yubormagani uchun hozir hamma o'quvchida `exits: 0` va nol vaqtlar ko'rinadi.
- **Qanday ulash:** vazifa topshirish sahifasida `visibilitychange` / `blur`+`focus` da `exit` / `return` yuboring
  (imtihondagi `POST /exams/{id}/focus/` bilan bir xil g'oya, u allaqachon ulangan).
- Server tomonda ochiq `exit` o'qituvchi ko'rayotgan paytgacha hisoblanadi (qaytmagan o'quvchi uchun).

##### 2. Kanaldan guruhni ajratish

`DELETE /api/v1/chat/channels/{channel_id}/courses/{course_id}/` — **kanal egasi (o'qituvchi)**, ruxsat `chat.use`.

- Javob `200 {"removed": 12}` — nechta a'zo chiqarildi.
- Faqat **shu guruh orqali** kelgan a'zolar chiqariladi. Kanalga alohida (`student_ids` bilan) qo'shilganlar qoladi.
- Hozir frontendda kanalga a'zo qo'shish (`POST channels/{id}/members/`) bor, lekin guruhni ajratish tugmasi yo'q.
- Qaysi guruhlar ulangani kanal javobida bor: `GET chat/rooms/` (`kind: "channel"`) da `course_ids` va `courses: [{id, title}]`. Ro'yxatni shundan oling, har bir guruh yoniga "ajratish" tugmasini qo'ying; muvaffaqiyatdan keyin kanalni qayta yuklang.

##### 3. Adminga mijoz salomatligi xulosasi

`GET /api/v1/monitoring/client-health/?hours=24&lesson=<id>&user=<id>` — **admin** (ruxsat `audit.view`).

- Parametrlar ixtiyoriy: `hours` (1–336, standart 24), `lesson`, `user`.
- Javob:
  ```json
  {
    "hours": 24, "total": 118, "cpu_limited_total": 9,
    "users": [{"user_id": "...", "username": "...", "role": "student", "reports": 14,
               "cpu_limited_reports": 3, "bandwidth_limited_reports": 1, "min_fps": 6,
               "last_at": "...", "hardware_concurrency": 4, "device_memory_gb": 4, "user_agent": "..."}],
    "recent": [{"id": "...", "lesson_id": "...", "user_id": "...", "username": "...", "role": "...", "created_at": "...",
                "cpu_constrained": true, "limited_by": "cpu", "min_fps": 6, "connection_quality": "...",
                "page_visible": true, "tracks": [], "events": []}]
  }
  ```
- Hisobotlarni frontend allaqachon yuboradi (`live/lesson/{id}/client-health/`); bu endpoint ularni admin uchun yig'ib beradi.
  "Kimning kompyuteri darsni sekinlashtiryapti" degan savolga javob, admin panelga jadval qilib qo'yish mumkin.
- `users` eng ko'pi 200 ta, `recent` eng ko'pi 50 ta. Hisobotlar 14 kun saqlanadi.

---

#### B. Backend tayyor, lekin serverda tashqi xizmat ulanmagan (11 ta)

**Production holati (2026-11-17 da tekshirilgan; 2026-11-18 da YANGILANDI):** `SMS_BACKEND`, `ESKIZ_EMAIL`, `GOOGLE_CLIENT_IDS`, `APPLE_CLIENT_IDS`, `FCM_PROJECT_ID` hali bo'sh.
**Email (`EMAIL_HOST`) 2026-11-18 dan ulangan va ishlaydi**: `auth/email/send-code`, `auth/email/verify` va yangi email endpointlari ishlaydi (qarang `FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md`).
SMS, Google/Apple va mobil push endpointlari hozir ishlab chiqarishda **503** qaytaradi. Bu ataylab: kod yuborilmagan bo'lsa "yuborildi" deb yolg'on aytilmaydi.
UI'ni oldindan yozish mumkin, lekin 503 ni chiroyli ko'rsating ("Hozircha mavjud emas").

##### 4. SMS va email tasdiqlash (8 ta)

Hammasida kod 5 xonali, **120 soniya** amal qiladi; qayta yuborish **45 soniyadan** keyin; kuniga eng ko'pi **10** marta;
noto'g'ri kiritish **5 martadan** keyin kodni bekor qiladi. Barchasi `POST`.

**Yuborish javobi (hammasida bir xil):** `200 {"sent": true, "expires_in": 120, "retry_after": 45}`
**Xatolar (hammasida):** `429` (juda tez/ko'p, `Retry-After` sarlavhasi va `wait`), `400 {"detail": "Kod noto'g'ri yoki muddati o'tgan"}`,
`503` (SMS/email ulanmagan), `502` (provayder xato berdi).

###### 4.1 Ro'yxatdan o'tishdan OLDIN telefonni tasdiqlash (login kerak emas)

1. `POST /auth/register/phone/request/` — `{ "phone": "+998901234567" }` → yuborish javobi.
2. `POST /auth/register/phone/verify/` — `{ "phone": "...", "code": "12345" }` → `{ "phone_token": "...", "expires_in": 1800 }`.
3. `POST /auth/register/` — oddiy ro'yxatdan o'tish tanasiga `"phone_token": "<token>"` qo'shing.
   Token **bir marta** ishlaydi, 30 daqiqa amal qiladi, aynan shu raqamga bog'liq. Token berilmasa, raqam tasdiqlanmagan holda saqlanadi
   (hozirgi frontend oqimi shunday ishlaydi, ya'ni buzilmaydi). Yaroqsiz token bo'lsa `400 {"phone_token": [...]}`.

###### 4.2 Profildagi telefonni almashtirish (login kerak)

1. `POST /auth/me/phone/request/` — `{ "phone": "+998..." }` → YANGI raqamga kod ketadi (eski raqam kod tasdiqlanguncha o'zgarmaydi).
2. `POST /auth/me/phone/confirm/` — `{ "phone": "+998...", "code": "12345" }` → yangilangan profil (`GET /auth/me/` shaklida);
   `phone_verified: true` bo'ladi.

###### 4.3 Mavjud telefon / emailni tasdiqlash (login kerak)

Profilda allaqachon yozilgan raqam yoki email uchun:

| Yuborish | Tekshirish | Tana |
|---|---|---|
| `POST /auth/phone/send-code/` | `POST /auth/phone/verify/` | tekshirishga `{ "code": "12345" }` |
| `POST /auth/email/send-code/` | `POST /auth/email/verify/` | tekshirishga `{ "code": "12345" }` |

- Yuborishga tana kerak emas, kod profildagi `phone` / `email` ga ketadi.
- Muvaffaqiyat: `200 {"verified": true}`.
- Qo'shimcha xatolar (`400 {"detail": ...}`): profilda telefon/email yo'q; allaqachon tasdiqlangan.

> Eslatma: telefonni SMS bilan tasdiqlashni biz **ataylab keyinga qoldirganmiz**. Hozir bitta telefon raqami bilan parolsiz hisob almashtirish
> mumkin (tasdiqlanmagan raqam bo'yicha). Tasdiqlash yoqilganda shu 8 ta endpoint ishlatiladi.

##### 5. Google / Apple bilan kirish

`POST /api/v1/auth/social/{provider}/` — `provider`: `google` yoki `apple`. Ochiq (login kerak emas). Sorov chegarasi: `login` (odatiy kirish bilan bir xil).

```json
{ "id_token": "<Google/Apple JWT>", "role": "student", "first_name": "...", "last_name": "..." }
```
`role` (`teacher` / `parent` / `student`), `first_name`, `last_name` ixtiyoriy. Apple ismni **faqat birinchi marta** beradi, shuning uchun uni shu birinchi so'rovda `first_name`/`last_name` bilan yuboring.

Javoblar (holatga qarab):

| Holat | Javob |
|---|---|
| Mavjud akkauntga kirdi | `200 {access, refresh}` |
| Akkauntda 2FA yoqilgan | `200 {two_factor_required: true, challenge_token, expires_in, retry_after, phone_hint}` (odatiy loginniki bilan bir xil, `/auth/2fa/login/` davom etadi) |
| Yangi foydalanuvchi, `role` berilmagan | `200 {signup_required: true, email, first_name, last_name}` → rol tanlatib, **xuddi shu `id_token` bilan** qayta yuboring |
| Yangi akkaunt ochildi (`role` bilan) | `201 {...foydalanuvchi, access, refresh}` |

Xatolar: `404` (provayder `google`/`apple` emas), `400 {"role": [...]}` (admin rolini tanlab bo'lmaydi), `401` (token yaroqsiz), `403` (akkaunt faol emas), `503` (hozirgi holat).

- **Xavfsizlik:** mavjud akkauntga faqat ikkala tomonda email tasdiqlangan bo'lsagina bog'lanadi.
- Ijtimoiy akkauntda parol yo'q (`parolni tiklash` orqali o'rnatiladi).
- **Ishlashi uchun:** Google Cloud'da Web + iOS + Android client ID'lar (`GOOGLE_CLIENT_IDS`), Apple'da Services ID / Bundle ID (`APPLE_CLIENT_IDS`) kerak. Ularni hali olmaganmiz.

##### 6. Mobil push (faqat mobil ilova)

Brauzer push (`push/vapid-key`, `push/subscribe`, `push/unsubscribe`) frontendda ulangan. Bu ikkitasi **mobil ilova** (FCM) uchun, veb uchun kerak emas.

- `POST /api/v1/notifications/push/device/` — har ilova ochilganda chaqiriladi (takror so'rov xato emas, yangilaydi):
  ```json
  { "token": "<FCM token>", "platform": "android", "device_id": "<barqaror ID>", "app_version": "1.2.0" }
  ```
  `platform`: `android` yoki `ios`. Javob `201 {"ok": true}`. Kalit: `(foydalanuvchi, device_id)`, token o'zgarsa yangilanadi.
- `DELETE /api/v1/notifications/push/device/` — tana `{ "device_id": "..." }` → `200 {"removed": true|false}`. Chiqishda chaqiring.
- `POST /api/v1/notifications/push/test/` — o'ziga sinov bildirishnomasi yuboradi (tana kerak emas) → `201` (bildirishnoma obyekti).
  Token → baza → FCM → telefon zanjirini tekshirish uchun.
- **Ishlashi uchun:** Firebase service-account JSON va `FCM_PROJECT_ID` kerak, ular hali yo'q. Shuning uchun hozir token saqlanadi, lekin telefonga xabar bormaydi (jim o'chirilgan, xato bermaydi).

---

#### C. Allaqachon ulangan: yo'l javob ichida keladi (3 ta)

Skript buni "ishlatilmayapti" deb ko'rsatdi, chunki frontend yo'lni qo'lda yozmaydi, **serverdan kelgan havolani** ishlatadi. Hech narsa qilmang.

##### 7. Javob ichida keladigan havolalar (ulangan)

| Endpoint | Frontend qayerdan oladi |
|---|---|
| `GET /chat/attachments/{id}/` (`?thumb=1` — eskiz) | `GET /chat/rooms/{id}/attachments/` javobidagi `url` / `thumbnail_url` (`message.api.ts`) |
| `GET /lessons/{id}/recording/stream/?t=<token>` | `GET /lessons/{id}/recording/` javobidagi `stream_url` (`lesson-recording-player.tsx`) |
| `GET /lessons/{id}/board/preview/{n}/?t=<token>` | o'sha javobdagi `board_page_previews[].image_url` (`lesson.mappers.ts`) |

> **Muhim qoida:** `stream_url` va `image_url` — **imzolangan, muddatli** havolalar (`?t=...`). Ularni qo'lda yig'ib yoki keshlab qo'ymang;
> har safar `recording/` ni so'rab yangisini oling. Bu ikkisida `Authorization` sarlavhasi kerak emas (`<video src>`, `<img src>` uchun).

---

#### D. Eskirgan takror yo'llar — alias (4 ta)

Hech narsa qilmang. Backendda bir xil ishni bajaradigan boshqa yo'l bor va frontend o'shani ishlatadi.

##### 8. Takror yo'llar (alias)

| Takror yo'l | Frontend ishlatadigan yo'l | Farqi |
|---|---|---|
| `POST /chat/rooms/{id}/forward/` `{message_ids}` | `POST /chat/messages/forward/` `{message_ids, target_room_ids}` | yangisi bir nechta chatga yuboradi |
| `POST/DELETE /chat/rooms/{id}/pin/` `{message_id}` | `GET/POST /chat/rooms/{id}/pinned/`, `DELETE .../pinned/{message_id}/` | eskisi faqat **bitta** xabar qadaydi, yangisi bir nechta |
| `POST/DELETE /chat/channels/{id}/image/` | `POST/DELETE /chat/rooms/{id}/image/` | ikkalasi bir xil kodni ishlatadi, kanal ham "room" |
| `GET /lessons/{id}/board/` | `GET /board/{lesson_id}/` | yozuv sahifasi uchun qulay nusxa, javobi bir xil |

(`/chat/rooms/{id}/pin-room/` — bu suhbatni ro'yxat tepasiga qadash, boshqa narsa, frontend uni ishlatadi.)

---

#### Tekshirilmagan narsalar

- Solishtirish **yo'l bo'yicha** bo'ldi, HTTP metod bo'yicha emas (masalan, frontend `GET` ishlatib, `DELETE` ni ishlatmayotgan bo'lishi mumkin).
- Faqat web frontend `main` shoxi o'qildi. Mobil ilova yoki boshqa shoxlar bu endpointlarni ishlatayotgan bo'lishi mumkin.
- `${...}` bilan dinamik yig'ilgan yo'llar va `.js`/`.tsx` dan tashqari fayllar qidiruvga tushmagan bo'lishi mumkin.
- SMS, email, Google/Apple va FCM oqimlarini **haqiqiy xizmat bilan** sinab ko'rmadim, faqat kod va testlarda tekshirilgan. Ishlab chiqarishda ular ulanmagan.

#### Qaysi birini avval ulash kerak (tavsiya)

1. **Uy vazifasi `focus`** (1-band): backend tayyor va ishlaydi, hozir o'qituvchi hamma o'quvchida "chiqmagan" ko'radi, bu noto'g'ri ko'rsatkich.
2. **Kanaldan guruhni ajratish** (2-band): kichik UI.
3. **Admin client-health** (3-band): ixtiyoriy, admin panelga qo'shimcha.
4. B guruhi (4–6): kalitlar/xizmatlar ulangandan keyin.


[↑ Mundarija](#mundarija)

---

## FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18

> Avvalgi fayl: `FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md`

### Email: ro'yxatdan o'tish, email bilan kirish, parolni emailga kod bilan tiklash (2026-11-18)

Trello: "change password qism togirlash kerak" (email ga code yuboradigan qilib). Login va parol QOLADI; email qo'shiladi.
Hamma yo'llar `/api/v1/auth/...`. **Production holati (2026-11-18, tekshirilgan):** email xizmati **ulangan va ishlayapti** (Gmail SMTP). Ro'yxatdan o'tish, email bilan kirish va parolni tiklash productionda haqiqiy xat bilan boshidan oxirigacha sinab ko'rildi. SMS xizmati hali ulanmagan: telefon orqali kod yuboradigan endpointlar `503` beradi.
Majburiylik bayrog'i (`email_required`) ham hozir **o'chiq**; avval frontend tayyor bo'ladi, keyin yoqamiz.

Kod hamma joyda bir xil: 5 xonali, **120 soniya** amal qiladi, qayta yuborish **45 soniyadan** keyin, kuniga 10 marta, 5 ta xato urinishdan keyin kod bekor bo'ladi.
Yuborish javobi: `200 {"sent": true, "expires_in": 120, "retry_after": 45}`. Xatolar: `429` (tez-tez), `400` ("Kod noto'g'ri yoki muddati o'tgan"), `503` (email ulanmagan), `502` (yuborib bo'lmadi).

#### 1. Ro'yxatdan o'tish oynasi

Avval `GET /auth/register/options/` (login shart emas) → `{"email_required": false, "email_available": false, "phone_available": false}`.
- `email_required: true` bo'lsa, email qadami **majburiy**. `false` bo'lsa, ixtiyoriy (yoki yashirin), eskicha ishlaydi.
- `email_available: false` bo'lsa kod yuborib bo'lmaydi (503); bu holatda majburiy qilmang, sahifada xabar ko'rsating.

Qadamlar (telefon oqimidagi kabi):
1. `POST /auth/register/email/request/` `{ "email": "ali@example.com" }` → kod emailga ketadi.
2. `POST /auth/register/email/verify/` `{ "email": "...", "code": "12345" }` → `{ "email_token": "...", "expires_in": 1800 }`.
3. `POST /auth/register/` oddiy tanaga **`email` va `email_token`** qo'shing. Token 30 daqiqa amal qiladi, **bir marta** ishlaydi va aynan shu emailga bog'liq.
   Xato: `400`, maydon xatosi `error.details.email_token` (token yo'q, eskirgan yoki boshqa emailga).
   Email katta-kichik harfdan qat'i nazar kichik harfga o'tkaziladi.

Boshqa o'zgarishlar:
- **Yangi loginda `@` taqiqlanadi** (`400`, `error.details.username`), chunki kirishda `@` li yozuv email deb qaraladi. Eski loginlar o'zgarmaydi.
- Ota-ona yoki o'qituvchi yaratgan bola akkaunti (`POST /auth/children/`) emailsiz yaratiladi va hech qachon email so'ralmaydi.

#### 2. Kirish: login YOKI email

`POST /auth/login/` o'sha `{ "username": "...", "password": "..." }`. `username` maydoniga **login ham, tasdiqlangan email ham** yozish mumkin.
Faqat yorliqni "Login yoki email" ga o'zgartiring. Endpoint, javob va xato shakli o'zgarmaydi.
- Noto'g'ri email yoki parol: odatiy `401` (email bor-yo'qligi oshkor bo'lmaydi).
- Bir email bir nechta akkauntga (bitta odamning rol-akkauntlari) bog'langan bo'lsa va parol ularning bir nechtasiga mos kelsa:
  `400` "Bu email bir nechta akkauntga bog'langan. Kirish uchun login (username) ni yozing." Shu xabarni ko'rsating.
- Tasdiqlanmagan email bilan kirib bo'lmaydi (faqat login bilan).

#### 3. Parolni tiklash

Oqim o'sha 3 qadam, endi `phone` o'rniga `email` ham mumkin (ikkalasidan bittasini yuboring):
1. `POST /auth/password/reset/request/` `{ "email": "ali@example.com" }` (yoki `{ "phone": "..." }`).
2. `POST /auth/password/reset/verify/` `{ "email": "...", "code": "12345" }` → `{ "reset_token": "...", "expires_in": 600 }`.
3. `POST /auth/password/reset/confirm/` `{ "reset_token": "...", "password": "..." }` → `{ "ok": true }`.

Farqlar:
- **Xat fonda yuboriladi:** parolni tiklash so'rovi SMTP javobini kutmaydi (shuning uchun mavjud va mavjud bo'lmagan email bir xil tez javob oladi). Xat yuborilmasa ham javob `200`, xato faqat serverda log'ga yoziladi. Kod kelmasa foydalanuvchiga "spam papkasini tekshiring, 2 daqiqadan keyin qayta so'rang" deb ayting.
- **Email topilmasa ham 1-qadam `200 {"sent": true, ...}` qaytaradi** (xavfsizlik: manzil bazada bor-yo'qligi oshkor bo'lmasin). Shuning uchun matn: "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi."
  Telefon bilan tiklashda esa oldingidek raqam topilmasa `404`.
- Faqat **tasdiqlangan** email bo'yicha tiklanadi.
- Parol yangilangach shu emaildagi hamma akkauntning paroli o'zgaradi va hamma seans yopiladi (telefon bilan tiklashdagidek).

#### 4. Mavjud foydalanuvchi: emailni qo'shish va tasdiqlash

`GET /auth/me/` da 2 ta yangi maydon:
- `email_setup_required` (bool): tasdiqlangan emaili yo'q va talab yoqilgan (bola akkauntlari uchun hech qachon `true` emas).
- `email_setup_deadline` (`"2026-12-02"` yoki `null`): shu sanagacha eslatma, **sanadan keyin majburiy**. `null` bo'lsa faqat eslatma.

`email_setup_required: true` bo'lsa, kirgandan keyin "Emailingizni qo'shing va tasdiqlang" oynasini ko'rsating (muhlatgacha "keyinroq" tugmasi bilan).
- `POST /auth/me/email/request/` `{ "email": "..." }` → YANGI manzilga kod ketadi (tasdiqlanguncha eski email o'zgarmaydi).
- `POST /auth/me/email/confirm/` `{ "email": "...", "code": "12345" }` → yangilangan profil (`GET /auth/me/` shaklida), `email_verified: true`.

Profilni `PATCH /auth/me/` bilan emailni to'g'ridan-to'g'ri o'zgartirsangiz, `email_verified` yana `false` bo'ladi (oldingidek). Tasdiqlash uchun yuqoridagi ikki endpointdan foydalaning.

#### QA

- Ro'yxatdan o'tish: kod → token → akkaunt; xato kod; eskirgan/qayta ishlatilgan token.
- Email bilan kirish (katta-kichik harf farqsiz); noto'g'ri parol; bir nechta akkauntli email.
- Tiklash: email → kod → yangi parol → yangi parol bilan kirish; mavjud bo'lmagan email ham xuddi shunday xabar ko'rsatadi.
- Eski foydalanuvchi: eslatma oynasi, email qo'shish, tasdiqlangach oyna yo'qoladi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_JAVOB_AI_RASM_2026-11-18

> Avvalgi fayl: `FRONTEND_JAVOB_AI_RASM_2026-11-18.md`

### Uy vazifasi: AI rasmlarni to'g'ri o'qiydi (2026-11-18)

Trello kartasi: "homeworkda image qismdi xammasini encode decode qilish kere ai ga jonatishdan oldin va ai ga jonatish kere boladi".
Backend o'zgardi. Frontend uchun majburiy ish yo'q, lekin 3 ta kichik narsa foydali.

#### Backend nimani to'g'riladi

| Oldin | Endi |
|---|---|
| Telefondan olingan rasm AI ga yonbosh bo'lib borardi | EXIF bo'yicha to'g'ri aylantiriladi |
| Doska/PDF'dan faqat 6 sahifa AI ga borardi (aslida 4 tadan ko'pi modelning kontekst oynasiga sig'maydi, ya'ni so'rov butunlay rad etilishi mumkin edi) | Rasmlar **token byudjetiga** qarab tanlanadi: hozirgi model (`gpt-4o-mini`) uchun bitta to'liq sahifa ~25 500 token, kontekst 128 000, shuning uchun **taxminan 3 ta to'liq sahifa/surat** AI ga boradi, qolgani "sig'madi" deb belgilanadi (so'rov rad etilmaydi) |
| Faqat birinchi fayl AI ga borardi | Hamma fayllar (5 tagacha), tartib bilan |
| Word (.docx) va aralash PDF ichidagi rasmlar olinmasdi | Matn bilan birga ichidagi rasmlar ham boradi (logo/ikonka kabi kichik rasmlar olinmaydi) |
| O'qituvchining vazifa sharti rasm bo'lsa, AI savolni ko'rmasdi | Shart rasmi AI ga o'quvchi ishidan alohida beriladi (eng ko'pi 2 ta) |
| iPhone `.heic` rad etilardi | Qabul qilinadi va yuklashda JPEG'ga o'tkaziladi |

#### Frontendga ta'siri

1. **`.heic` / `.heif` endi qabul qilinadi** (`POST /homework/assignments/{id}/submit/`). Fayl tanlash oynasidagi `accept` ro'yxatiga va "PDF, JPG, PNG, DOCX · 25 MB gacha"
   matniga `HEIC` qo'shishni ko'rib chiqing. Server faylni JPEG qilib saqlaydi: `file_name` `IMG_1.jpg` bo'lib qaytadi, o'qituvchi brauzerda ocha oladi.
   Buzuq HEIC uchun `400 {"file": ["iPhone rasmini (HEIC) o'qib bo'lmadi. JPG yoki PNG yuklang."]}`.
2. **AI natijasida yangi maydon:** `ai_result.skipped_images` (son). Ish **taxminan 3 ta sahifa/suratdan** ko'p bo'lsa (token byudjeti, qarang yuqorida), qolgan sahifalar baholanmaydi va
   `ai_result.summary.recommendations[0]` ga ogohlantirish yoziladi ("... N ta rasmi/sahifasi AI ga sig'madi ... o'qituvchi qolganlarini o'zi ko'rib chiqsin").
   O'qituvchi natija oynasida shuni ajratib ko'rsatsangiz yaxshi (masalan sariq belgi): ball faqat ko'rilgan sahifalar bo'yicha.
   Qisqa ishlarda bu maydon umuman kelmaydi.
3. Boshqa hech narsa o'zgarmadi: endpointlar, `ai_state`, ball formati oldingidek.

#### QA (qo'lda tekshirish)

- iPhone'dan HEIC rasm bilan topshirish → o'qituvchida rasm ochiladi, AI natijasi keladi.
- Yonbosh olingan telefon surati → AI natijasidagi `student_answer` o'qiladi (oldin "o'qib bo'lmadi" ga yaqin chiqardi).
- 8 sahifali doska → natijada `skipped_images: 5` va ogohlantirish (AI faqat dastlabki 3 sahifani ko'radi, shuning uchun o'qituvchi qolganini o'zi ko'rishi kerak).
- Word faylga qo'lyozma rasmi qo'yilgan ish → AI rasmni ham ko'radi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18

> Avvalgi fayl: `FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18.md`

### Javob: "Parolni o'zgartirish" (BACKEND_PAROL_OZGARTIRISH.md bo'yicha), 2026-11-18

Hammasi backend kodi va productiondagi ma'lumotlar bo'yicha tekshirildi. Frontendda **hech narsa o'zgartirish shart emas**.

#### 1. Avtomatik ochilgan rol akkauntida joriy parol noma'lum: tasdiqlandi va tuzatildi

**Tasdiqlandi:** `switch_or_provision_role` yangi akkauntga `secrets.token_urlsafe(32)` qo'yardi. Productionda shunday akkauntlar **4 ta**
(2 ta o'quvchi, 2 ta kuzatuvchi; hammasi o'qituvchi akkauntidan ochilgan, parollari hech qachon o'zgartirilmagan). Parolsiz (`unusable`) akkaunt yo'q.

**Tanlangan yo'l:** `password_set` belgisi **qo'shilmaydi**, "Parol o'rnatish" oynasi ham kerak emas. Frontend o'zgarmaydi: `current_password` majburiy qoladi.

| Holat | Nima qilindi |
|---|---|
| **Yangi** avtomatik ochiladigan akkauntlar | Parol xeshi manba akkauntdan nusxalanadi: bitta odamning rol-akkauntlarida parol bir xil. Yangi akkauntga login va manba paroli bilan to'g'ridan-to'g'ri ham kirsa bo'ladi |
| **Mavjud 4 ta** akkaunt | Alohida buyruq: `manage.py sync_provisioned_passwords` (standart: faqat ko'rsatadi, `--apply` bilan yozadi). Faqat shu shartlarda nusxalaydi: akkaunt audit'da avtomatik ochilgan deb yozilgan; parol hech qachon o'zgartirilmagan (foydalanuvchi o'zi qo'ygan parol bosilmaydi); manba va nishon hozir ham bitta bog'langan guruhda va faol. Takror ishga tushirish xavfsiz |

**Eslatma:** bu o'zgarish serverga chiqarilgach ishlaydi; mavjud 4 akkaunt uchun buyruqni men ishga tushiraman (xabar beraman). Shundan keyin
o'qituvchi "O'quvchi" yoki "Kuzatuvchi" akkauntida "Parolni o'zgartirish" ni **o'qituvchi paroli bilan** ocha oladi. Manba akkaunt paroli o'zgarmaydi,
va keyin bitta akkauntda parol o'zgartirilsa, boshqa rol-akkauntlarniki o'zgarmaydi (parolni tiklash esa shu telefon/emaildagi hammasini o'zgartiradi, oldingidek).

#### 2. Parol qoidalari: backend o'zgartirilmadi (qaror)

Backend raqam va katta harfni talab qilmaydi, frontend talab qiladi. **Backendni qattiqlashtirmadim**, sabab: mobil ilova va allaqachon ro'yxatdan
o'tgan foydalanuvchilar mavjud; yangi talab birdaniga ularning ro'yxatdan o'tishi va parolni tiklashini `400` ga aylantirishi mumkin. Frontendning qattiqroq
qoidasi to'g'ri va yetarli (backend undan yumshoqroq, ziddiyat yo'q). Agar backendda ham majburiy bo'lishini xohlasangiz, ayting: ro'yxatdan o'tish,
tiklash va o'zgartirishga birdan qo'shiladi, mobil ilova jamoasi bilan kelishib.

#### 3. Validator xabarlari tili: tasdiqlandi va tuzatildi

**Tasdiqlandi:** `uz` da `new_password` xatolari inglizcha chiqardi (Django'ning `uz` katalogida bu satrlar bo'sh), `ru` da ruscha edi. Haqiqiy tekshirilgan.

**Tuzatildi:** `uz` tarjimasi qo'shildi. Endi `Accept-Language: uz` (yoki til yuborilmasa, standart) bilan:

| Qoida | uz | ru / en |
|---|---|---|
| juda qisqa | Parol juda qisqa: kamida 8 ta belgi bo'lsin. | o'zgarmadi |
| juda oddiy | Bu parol juda oddiy, boshqasini tanlang. | o'zgarmadi |
| faqat raqam | Parol faqat raqamlardan iborat bo'lmasin. | o'zgarmadi |
| loginga o'xshash | Parol quyidagi ma'lumotga juda o'xshash: login. | o'zgarmadi |

Xatolar oldingidek `error.details.new_password` ichida (ro'yxat).

#### Tekshirish (QA)
1. O'qituvchi birinchi marta "O'quvchi" roliga o'tadi (yangi akkaunt ochiladi), o'quvchi akkauntida "Parolni o'zgartirish": o'qituvchi paroli bilan ishlashi kerak.
2. `Accept-Language: uz` bilan `new_password: "12345678"` → o'zbekcha ikki xabar.


[↑ Mundarija](#mundarija)

---

## FRONTEND_VAZIFALAR_2026-11-18

> Avvalgi fayl: `FRONTEND_VAZIFALAR_2026-11-18.md`

### Frontend uchun vazifalar: backend tayyor, frontend qiladigan ishlar (2026-11-18)

> **ALMASHTIRILDI:** bu ertalabki holat edi (P1 email, P2 focus, P5 kanal/admin panel siz tomondan bugun bajarilgan). Hozirgi aniq ro'yxat: [FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY.md](#frontend_yangilanishlar_2026-11-18_yakuniy).

Bugun backendda qilingan hamma ishning frontendga ta'siri bir joyda. Har bandda batafsil yo'riqnoma havolasi bor. Tartib: eng muhimidan.
Backend `main` da `a3fd185`, APP serverga chiqarilgan. Frontend `main` (`ed7bf08`) bilan solishtirildi.

#### P1. Email: ro'yxatdan o'tish, kirish, parolni tiklash (productionda parol tiklash shunga bog'liq)

Batafsil: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](#frontend_email_kirish_va_tiklash_2026-11-18). Email xizmati endi **ulangan** va ishlayapti.

- [ ] **Parolni tiklash** oynasida telefon o'rniga **email** varianti: `POST /auth/password/reset/request|verify|confirm/` (`phone` yoki `email`). Email topilmasa ham javob `200 {sent:true}`: matn "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi".
- [ ] **Kirish** maydoni yorlig'i "Login yoki email" (endpoint o'sha `/auth/login/`, `username` maydoniga email ham yoziladi). Bir email bir nechta akkauntda bo'lsa `400` xabarini ko'rsating.
- [ ] **Ro'yxatdan o'tish:** `GET /auth/register/options/` ga qarab email qadami (`register/email/request` → `verify` → `email_token`). Hozir `email_required: false`, shuning uchun hozirgi oqim buzilmaydi; siz tayyor bo'lgach men `true` qilaman.
- [ ] **"Emailingizni qo'shing" oynasi** (mavjud foydalanuvchilar): `GET /auth/me/` dagi `email_setup_required` va `email_setup_deadline`; `POST /auth/me/email/request|confirm/`.
- Muhim: hozir productionda **tasdiqlangan email nolta**, ya'ni parolni unutgan hech kim tiklay olmaydi, shuning uchun oxirgi band birinchi chiqishi kerak.

#### P2. Uy vazifasi: sahifadan chiqib-kirishni yuborish (hozir noto'g'ri nollar ko'rinadi)

Backend tayyor, frontend hech qachon yubormaydi, shu sababli o'qituvchi hamma o'quvchida "chiqmagan, 0 soniya" ko'radi.

- [ ] Vazifa topshirish sahifasida `visibilitychange` / `blur`+`focus` da `POST /homework/assignments/{id}/focus/` `{ "kind": "exit" }` va `{ "kind": "return" }` yuboring.
- Imtihondagi `POST /exams/{id}/focus/` bilan bir xil g'oya (u ulangan). Javob `200 {ok:true}`; `400` agar `kind` boshqacha, `403` agar kursga yozilmagan.
- O'qituvchi topshirilgan ishni ochganda javobdagi `focus` (`exits`, `away_seconds`, `timeline`...) endi haqiqiy bo'ladi. Batafsil: [FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md](#frontend_ulanmagan_endpointlar_2026-11-17) 1-band.

#### P3. Bildirishnomalar (push)

Backendda tuzatildi: push sarlavhasi endi "Fokus" emas ("Dars yozuvi tayyor", "Yangi baho", "To'lov" yoki "YolUp"), veb push matnida HTML yo'q, push fonda yuboriladi.

- [ ] **`public/sw.js`**: bosilganda faqat `link_type=lesson` ochiladi, qolganlari bosh sahifaga olib boradi. Backend `link_type` lari: `assignment`, `lesson`, `quiz`, `submission`, `course`, `chat_room`, `certificate`, `exam`, `recording`, `support`, `spam_report`, `teacher`, `link`, `login`. Ilovadagi bildirishnoma ro'yxati ishlatadigan `mapNotificationLink` (frontend: `src/modules/notification/lib/notification.mappers.ts`) mantiqini service worker'ga ham qo'llang (yoki push'dagi `link_type`/`link_id` ni ilovaga uzatib, o'sha yerda marshrutlang).
- [ ] **Veb push'ni taklif qilish.** Hozir u faqat sozlamalardagi yashirin tugma orqali yoqiladi (`use-push-notifications.ts`), productionda **obunalar nolta**. Birinchi kirishda "Bildirishnomalarni yoqish" taklifini ko'rsating (`enablePush()` tayyor).
- Mobil push (FCM) Firebase fayli kelgach ishlaydi, bu hozircha kutilmoqda.

#### P4. Uy vazifasi: AI va rasmlar

Batafsil: [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](#frontend_javob_ai_rasm_2026-11-18).

- [ ] Fayl tanlashga **`.heic` / `.heif`** qo'shing (`accept` va "PDF, JPG, PNG, DOCX · 25 MB gacha" matni). Server JPEG'ga o'tkazadi.
- [ ] O'qituvchi AI natijasida `ai_result.skipped_images` (son) bor bo'lsa, ajratib ko'rsating (masalan sariq belgi: "N ta sahifa AI ga sig'madi, ball faqat ko'rilganlar bo'yicha"). Ogohlantirish matni `ai_result.summary.recommendations[0]` da.

#### P5. Backendda tayyor, lekin ekrani yo'q

- [ ] **Kanaldan guruhni ajratish:** `DELETE /chat/channels/{id}/courses/{course_id}/` → `{removed: n}`. Guruhlar ro'yxati kanal javobida: `course_ids`, `courses:[{id,title}]`.
- [ ] **Admin: mijoz salomatligi jadvali:** `GET /monitoring/client-health/?hours=24` (ixtiyoriy, admin paneliga).
- Ikkalasi: [FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md](#frontend_ulanmagan_endpointlar_2026-11-17) 2-3 bandlar.

#### P6. Trello'dagi frontend kartalari

- [ ] **vazifa berishda**: "Yangi vazifa" oynasida vazifa matni maydoni (description) ko'zga tashlanib turishi kerak (karta skrinshoti bor).
- [ ] **Doska** (RedZon): matn o'lchami ishlamay qolgan joy va chiziq yo'naltiruvchisi. Backend tayyor: matn o'lchami 12–48, `w` kengligi, `line`/`rect`/`ellipse`, tahrirlash (`update_stroke`). Backend rad etgan bo'lsa, `400` xabarini yuboring.
- **Qo'lda test yozish imkoni BOR** (kartaning savoliga javob): backend `POST /quizzes/`, frontendda `AddQuizDialog` (`group-workspace.tsx` ichida). Trello'ga shuni yozib, kartani yoping.

#### QA: backend tayyor, frontendda tekshirish kerak

| Nima | Qanday tekshirish |
|---|---|
| **Meeting permission** ([FRONTEND_YANGILANISHLAR_2026-11-12_2.md](#frontend_yangilanishlar_2026-11-12_2)) | (1) bir marta ruxsat → o'quvchi o'chirdi → qayta so'ralishi; (2) "hammani o'chirish" → ruxsat qaytadi; (3) ochiq rejimda kirgan yangi o'quvchi so'rovsiz yoqa oladi |
| **homework natija oynasi** | AI holatlari `checking / ready / unscored / failed` to'g'ri chiqishi |
| **homeworkcheck (fayl ixtiyoriy)** | faqat izoh bilan topshirish ishlashi |
| **Dars yozuvi uzluksizligi** ([FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md](#frontend_javob_ekran_yozuv_2026-11-16)) | oynalar almashtirilganda, ko'p seans va juda qisqa seansda yozuv uzilmasligi |
| **Darsga kirish** ([FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](#frontend_javob_darsga_taklif_2026-11-16)) | o'qituvchi boshlagach o'quvchi rejalashtirilgan vaqtdan oldin ham kira olishi, "aylanib turgan yopiq dars" ko'rinmasligi |
| **Material sonlari** ([FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md](#frontend_javob_material_sonlari_2026-11-17)) | guruh papkasida `recording_count`, `board_count` |
| **Spam shikoyatlari (admin)** | ro'yxat, `resolve` / `dismiss` / `unblock`; productionda 1 ta ochiq shikoyat turibdi |

#### Hozircha frontendga tegishli bo'lmagan (backend kutmoqda)

Firebase (mobil push), chat xabarini tiklash, rasm yuborish qoidasi, "tech padeshka", o'tgan oylar qarzi: bular mahsulot qarori yoki tashqi kalit kutyapti. Qaror chiqqach alohida yozaman.

#### Eslatma

- Yangi backend xabarlari (email, HEIC, login `@` qoidasi) ru va en tilida ham chiqadi (`Accept-Language` bo'yicha).
- `ai_result.usage` (token sarfi) o'qituvchi javobida ichki maydon sifatida keladi; ekranda ko'rsatish shart emas.
- Barcha endpoint yo'llari `/api/v1/...` bilan boshlanadi.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY.md`

### Frontend uchun: bugun backendda nima qilindi va frontendda nima qoldi (2026-11-18, yakuniy)

Backend: APP va MEDIA serverlar `17124e3` da ishlayapti (productionda tekshirilgan). Frontend `main` (`33afa65`, bugungi PR #197–#200 gacha) bilan solishtirildi.
Bu hujjat [FRONTEND_VAZIFALAR_2026-11-18.md](#frontend_vazifalar_2026-11-18) ni **almashtiradi** (u ertalabki holat edi, ichidagi ko'p narsa siz tomondan bugun bajarilgan).

#### 1. Siz bugun qilgan va backend shartnomasiga MOS ekani tekshirilgan

Endpoint nomlari va so'rov tanalari backend bilan solishtirildi (kod bo'yicha). Brauzerda o'zim sinab ko'rmadim.

| Siz qilgan | Backend bilan mosligi |
|---|---|
| PR #199: email bilan ro'yxatdan o'tish (`register/options`, `register/email/request`, `verify`, `email_token`), "Login yoki email", parolni emailga kod bilan tiklash, profilda emailni tasdiqlash, "Emailingizni qo'shing" oynasi | Mos. Productionda haqiqiy xat bilan boshidan oxirigacha sinalgan |
| PR #197: uy vazifasi `focus` (exit/return), kanaldan guruhni ajratish, admin "Mijoz salomatligi" paneli | Mos (`{kind: "exit"|"return"}`, `GET monitoring/client-health/`) |
| PR #198: doska yordamchi katagi, PR #200: parolni o'zgartirishda xato maydon ostida | Backend tomonida o'zgarish talab qilinmaydi |

#### 2. Frontendda QOLGAN ishlar (aniq, tekshirilgan)

| # | Nima | Qayerda / qanday |
|---|---|---|
| 1 | **iPhone `.heic` / `.heif` ni qabul qilish** | frontend: `src/pages/student/workspace/student-homework-item-page.tsx:39` dagi `ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.docx"` ga `.heic,.heif` qo'shing va "PDF, JPG, PNG, DOCX · 25 MB" matniga HEIC ni yozing. Server uni JPEG'ga o'tkazadi, `file_name` `IMG_1.jpg` bo'lib qaytadi |
| 2 | **`ai_result.skipped_images` ni ko'rsatish** (o'qituvchi natija oynasi) | Son bo'lsa, ajratib ko'rsating (sariq belgi): "N ta sahifa AI ga sig'madi, ball faqat ko'rilganlar bo'yicha". Matni `ai_result.summary.recommendations[0]` da. Qisqa ishlarda maydon kelmaydi. Sabab 4-bo'limda |
| 3 | **`public/sw.js`: push bosilganda to'g'ri sahifani ochish** | Hozir faqat `link_type=lesson` ochiladi (`urlFromLink`), qolganlari bosh sahifaga olib boradi. Backend `link_type` lari: `assignment`, `lesson`, `quiz`, `submission`, `course`, `chat_room`, `certificate`, `exam`, `recording`, `support`, `spam_report`, `teacher`, `link`, `login`. Ilovadagi bildirishnoma ro'yxati ishlatadigan `mapNotificationLink` mantiqini service worker'ga ham qo'llang |
| 4 | **Veb push'ni taklif qilish** | Hozir u faqat sozlamalardagi tugma orqali yoqiladi (`system-settings-page.tsx`), productionda **obunalar nolta**. Birinchi kirishda "Bildirishnomalarni yoqish" taklifini ko'rsating (`enablePush()` tayyor) |
| 5 | Trello: **"vazifa berishda"** | "Yangi vazifa" oynasida vazifa matni (description) maydoni ko'zga tashlanib turishi kerak (kartada skrinshot) |
| 6 | Trello: **"Qolda test yozish imkonini ko'rish"** | Javob: **imkon bor** (backend `POST /quizzes/`, frontendda `AddQuizDialog`, `group-workspace.tsx`). Kartaga shuni yozib yoping |

#### 3. Backend tomonida nima o'zgardi (sizga ta'siri)

**Email (productionda ishlayapti, Gmail SMTP)**
- `GET /auth/register/options/` hozir: `{email_required: false, email_available: true, phone_available: false}`.
- `REGISTER_REQUIRES_EMAIL` hozir **o'chiq**. Siz email qadamini tayyorlab bo'ldingiz, shuning uchun backend uni yoqishga tayyor: **ayting, qachon yoqamiz** (yoqilgach `email_required: true`, tasdiqlangan emailsiz ro'yxatdan o'tib bo'lmaydi). Muhlat sanasi (`email_setup_deadline`) ni ham birga belgilaymiz (tavsiya: 14 kun).
- Productionda hozircha **tasdiqlangan emaili bor foydalanuvchi nolta**: bugun ham 2 ta yangi hisob emailsiz ochilgan. Parolni unutgan foydalanuvchi emailni tasdiqlamaguncha tiklay olmaydi.
- **Kirish:** `username` maydoniga login ham, tasdiqlangan email ham yoziladi. Bir email bir nechta akkauntga bog'langan bo'lsa va parol ularning bir nechtasiga mos kelsa: `400`, `error.message` "Bu email bir nechta akkauntga bog'langan. Kirish uchun login (username) ni yozing." Shu xabarni ko'rsating.
- **Xato kirishlar:** bir akkauntga login va email bilan jami **10 ta xato urinishdan** keyin `429` ("Juda ko'p muvaffaqiyatsiz urinish. Bir necha daqiqadan keyin qayta urinib ko'ring."), 10 daqiqa. Login va email urinishlari **bitta hisoblagichda**.
- **Yangi loginda `@` taqiqlanadi** (`400`, `error.details.username`). Eski loginlar o'zgarmaydi.
- **Parolni tiklash:** email topilmasa ham `200 {sent:true}`. Xat **fonda** yuboriladi: SMTP xato bersa ham javob `200`, xato faqat serverda log'ga yoziladi. Shuning uchun matnda: "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi. Kelmasa spam papkasini tekshiring va 2 daqiqadan keyin qayta so'rang."
- Kod: 5 xonali, 120 soniya amal qiladi, qayta yuborish 45 soniyadan keyin (`retry_after`), kuniga 10 marta, 5 xato urinishdan keyin kod bekor. `auth` chegarasi: IP bo'yicha 30 so'rov/daqiqa (`429`).
- Batafsil: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](#frontend_email_kirish_va_tiklash_2026-11-18).

**Backend xabarlari endi ru va en tilida ham** (`Accept-Language`): email, HEIC va login qoidasi xatolari. Oldin faqat o'zbekcha edi.

**Push (veb va mobil)**
- Sarlavha endi "Fokus" emas: tizim xabarlarida ro'yxatdagi sarlavha ("Dars yozuvi tayyor", "Yangi baho", "To'lov"), o'qituvchi xabarida "Ism · Guruh", boshqasida "E'lon"/"YolUp".
- Veb push matnidan HTML teglar olib tashlandi. Push payload maydonlari: `title`, `body`, `kind`, `link_type`, `link_id`.
- Push fonda yuboriladi (APP va MEDIA'da). "Dars yozuvi tayyor" bildirishnomasini MEDIA yuboradi, u ham yangilandi.
- Mobil push (FCM) hali ishlamaydi: Firebase kaliti kutilmoqda.

**To'lov eslatmasi:** faqat 09:00–20:00 (Toshkent) yuboriladi; xabar ketmasa keyingi soatda qayta uriniladi. Frontendga ta'siri yo'q.

#### 4. Uy vazifasi: AI va rasmlar (muhim cheklovlar)

- **AI hozir umuman ishlamayapti:** OpenAI kaliti muddati tugagan (kalit yangilanishini kutyapmiz). Yangi topshirish `status: pending_review`, `ai_state: "failed"`, `error: "AI baholay olmadi — o'zingiz baholang."` bilan o'qituvchiga tushadi. Frontend `failed` holatini "AI mavjud emas, qo'lda baholang" deb to'g'ri ko'rsatayotganini tekshiring (QA). Kalit kelgach hammasi o'zi tiklanadi, frontend o'zgarishi shart emas.
- **Rasm/sahifa soni:** AI bitta ishdan **taxminan 3 ta to'liq sahifa/suratni** ko'ra oladi (modelning kontekst chegarasi, har sahifa ~25 500 token). Ortig'i AI ga berilmaydi va `ai_result.skipped_images` + ogohlantirish bo'ladi (yuqorida 2-band). Bu ataylab: aks holda butun so'rov rad etilardi. Ko'p sahifali doskada o'qituvchi qolganini o'zi ko'rishi kerak.
- **Yaxshilanganlar** (frontend o'zgarishi shart emas): telefon surati to'g'ri aylantiriladi (EXIF), hamma yuklangan fayllar (5 tagacha) AI ga boradi, Word/PDF ichidagi rasmlar olinadi, vazifa sharti rasmi AI ga beriladi, iPhone HEIC JPEG'ga o'tkaziladi.
- `ai_result.usage` (token sarfi) o'qituvchi javobida ichki maydon sifatida keladi, ekranda ko'rsatish shart emas.
- Batafsil: [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](#frontend_javob_ai_rasm_2026-11-18).

#### 5. QA: backend tayyor, frontendda tekshirish kerak

| Nima | Qanday tekshirish |
|---|---|
| **Meeting permission** ([FRONTEND_YANGILANISHLAR_2026-11-12_2.md](#frontend_yangilanishlar_2026-11-12_2)) | (1) bir marta ruxsat → o'quvchi o'chirdi → qayta so'ralishi; (2) "hammani o'chirish" → ruxsat qaytadi; (3) ochiq rejimda kirgan yangi o'quvchi so'rovsiz yoqa oladi |
| **homework natija oynasi** | `ai_state`: `checking / ready / unscored / failed` to'g'ri chiqishi (hozir `failed` ko'p uchraydi) |
| **homeworkcheck** | faqat izoh bilan (fayl yo'q) topshirish ishlashi |
| **Dars yozuvi uzluksizligi** ([FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md](#frontend_javob_ekran_yozuv_2026-11-16)) | oynalar almashtirilganda, ko'p seans va juda qisqa seansda yozuv uzilmasligi |
| **Darsga kirish** ([FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](#frontend_javob_darsga_taklif_2026-11-16)) | o'qituvchi boshlagach o'quvchi rejalashtirilgan vaqtdan oldin ham kira olishi |
| **Material sonlari** ([FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md](#frontend_javob_material_sonlari_2026-11-17)) | guruh papkasida `recording_count`, `board_count` |
| **Spam shikoyatlari (admin)** | ro'yxat, `resolve` / `dismiss` / `unblock`; productionda 1 ta ochiq shikoyat turibdi |
| **Email oqimi (brauzerda)** | ro'yxatdan o'tish → kod → akkaunt; email bilan kirish; tiklash; profilda email tasdiqlash. Backend haqiqiy xat bilan sinalgan, frontend brauzerda sinalmagan |
| **Homework focus** | vazifa sahifasidan chiqib-kirish; o'qituvchida `focus.exits` > 0 bo'lishi |

#### 6. Hali backendda kutilayotgan (frontendga bog'liq emas)

Firebase (mobil push), chat xabarini tiklash, rasm yuborish qoidasi ("hamma / faqat o'qituvchi"), "tech padeshka", o'tgan oylar to'lov qarzi: mahsulot qarori yoki tashqi kalit kutyapti. OpenAI kaliti ham shu ro'yxatda. Qaror chiqqach alohida yozaman.

Barcha endpoint yo'llari `/api/v1/...` bilan boshlanadi. Xato javobi: `{success:false, error:{code, message, details}}`.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-19

> Avvalgi fayl: `FRONTEND_YANGILANISHLAR_2026-11-19.md`

### Frontend va mobil jamoa uchun: 2026-11-19 yangilanishlari

Hammasi productionda (APP va MEDIA) ishlayapti. Backend testlari (2075 ta) o'tgan, productionda haqiqiy tekshiruvlar qilingan.

#### 1. Email endi ro'yxatdan o'tishda MAJBURIY (faqat `.env` o'zgardi, kod yangi emas)

Batafsil oqim: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](#frontend_email_kirish_va_tiklash_2026-11-18). Bu yerda faqat endi nima o'zgargani.

| Nima | Hozirgi holat (productionda tekshirilgan) |
|---|---|
| `GET /api/v1/auth/register/options/` | `{"email_required": true, "email_available": true, "phone_available": false}` |
| `POST /api/v1/auth/register/` emailsiz (`email_token` yo'q) | `400`, `error.details.email_token`: "Email tasdiqlanishi shart: avval emailga kelgan kodni tasdiqlang." Akkaunt yaratilmaydi |
| `GET /api/v1/auth/me/` emailsiz mavjud foydalanuvchi | `email_setup_required: true`, `email_setup_deadline: "2026-12-03"` |
| `GET /api/v1/auth/me/` `email_exempt` foydalanuvchi (ota-ona/o'qituvchi yaratgan bola) | `email_setup_required: false`, `email_setup_deadline: null` |

Frontendga ish:
- Ro'yxatdan o'tishda email qadami albatta bo'lsin (`register/email/request/` → `register/email/verify/` → `email_token` ni `register/` ga yuborish). `options` dagi `email_required` ga qarab ko'rsatish yoki yashirish mumkin.
- Mavjud foydalanuvchilar uchun: `email_setup_required: true` bo'lsa eslatma ko'rsatiladi. **2026-12-03** dan keyin email qo'shishni majburiy qilish frontendda (backend bloklamaydi). Email qo'shish: `me/email/request/` va `me/email/confirm/`.
- Hozir productionda 28 foydalanuvchidan faqat 2 tasida tasdiqlangan email bor, ya'ni deyarli hamma eslatma ko'radi. Kutilgan holat.
- Bolalar akkauntlari uchun eslatma chiqmasligi kerak: `email_setup_required` ga ishoning, o'zingiz rolga qarab taxmin qilmang. Eski bola akkauntlari (telefonsiz o'quvchilar) adminda `email_exempt` qilib belgilanadi. Kerak bo'lsa ro'yxatini ayting.

#### 2. Mobil push (FCM) backendda ulandi

Firebase loyihasi: `yolup-28bb7`. APP va MEDIA serverlarida kalit qo'yilgan (MEDIA'da ham, chunki "yozuv tayyor" xabarini o'sha server yaratadi).

Mobil jamoaga:
- Android uchun `google-services.json` (package `uz.yolup.edu`) mobil ilovaga qo'yiladi, backendga kerak emas.
- Ilova har ochilganda FCM tokenini yuboradi: `POST /api/v1/notifications/push/device/`
  ```json
  {"token": "<FCM registration token>", "platform": "android" | "ios", "device_id": "<barqaror qurilma id>", "app_version": "1.0.0"}
  ```
  Javob `201 {"ok": true}`. Chiqishda `DELETE` shu manzilga `{"device_id": "..."}`.
- **Muhim, iOS:** productionda hozir faqat 1 ta qurilma ro'yxatda (`ios`) va uning tokeni haqiqiy **FCM** tokeni emas (Google rad etdi: "not a valid FCM registration token"). iOS'da xom APNs tokenini emas, Firebase SDK bergan FCM tokenini yuboring. iOS push uchun Firebase konsolida APNs kaliti ham yuklangan bo'lishi kerak (buni mobil jamoa/Firebase egasi qiladi).
- Xabar maydonlari (`data`): `notification_id`, `link_type`, `link_id`, `kind`. Sarlavha ("YolUp" yoki mazmunga mos) va matn `notification` ichida.
- **Sinash:** to'g'ri token yuborilgach, `POST /api/v1/notifications/push/test/` o'ziga sinov xabarini yuboradi (token → baza → FCM → telefon). Natijani backendga xabar bering.

Hali tasdiqlanmagan: haqiqiy telefonga xabar yetib borishi (to'g'ri FCM tokeni kerak).

#### 3. Parolni o'zgartirish (avvalgi javobning yakuni)

`sync_provisioned_passwords --apply` productionda ishga tushirildi: avtomatik ochilgan 4 ta rol akkaunti tuzatildi, takror ishga tushirish hech narsani o'zgartirmadi. Yangi avtomatik ochiladigan akkauntlar ham manba parolini oladi. O'qituvchi "O'quvchi"/"Kuzatuvchi" akkauntida "Parolni o'zgartirish" ni o'qituvchi paroli bilan ocha oladi. `uz` da parol xabarlari o'zbekcha. Frontendda o'zgarish shart emas. Batafsil: [FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18.md](#frontend_javob_parol_ozgartirish_2026-11-18).

#### 4. AI qayta ishlayapti (yangi OpenAI kaliti, 2026-11-19)

AI baholash, AI test yaratish, yozma imtihon AI va Speaking (ovoz → matn, matn → ovoz) yana ishlaydi. Haqiqiy tekshiruv: burilgan rasmli uy vazifasi to'g'ri baholandi (xato javob topildi, xulosa o'zbekcha), Speaking audio aylanishi ishladi. Frontendda o'zgarish shart emas. Oldingi ogohlantirishlar (HEIC, `ai_result.skipped_images`) o'z kuchida.

#### 5. Hali ochiq

- **Haqiqiy mobil push:** to'g'ri FCM tokeni kerak (2-bo'lim).
- HEIC va 3+ sahifali hujjat haqiqiy OpenAI bilan hali sinalmagan (testlarda tekshirilgan). QA'da shularni ham sinab ko'ring.


[↑ Mundarija](#mundarija)

---

## FRONTEND_YANGILANISHLAR_2026-11-21

> Yangi bo'lim (alohida fayl emas: hujjatlar endi shu faylda).

### Frontend va mobil jamoa uchun: 2026-11-21

Trello kartalari bo'yicha. Productionga chiqargach shu yerda "productionda" deb belgilanadi.

### 1. "Kirish tarixi": har qurilma bitta qator (backend tayyor)

Trello: "kirish tarixi qism da", "kun sana qib qo'yish kerak". Hozir ro'yxat har bir KIRISHNI alohida ko'rsatadi, shuning uchun juda uzun. Kerak: nechta qurilma bo'lsa shuncha qator, har birida oxirgi kirish sanasi va vaqti.

`GET /api/v1/auth/logins/?group=device` (o'zingiz uchun; ota-ona uchun `&student=<id>`, avvalgi ruxsat qoidalari o'zgarmagan). Filtrlar: `device=phone|tablet|computer`, `from`, `to`. Sahifalash bilan ham ishlaydi (`page`, `page_size`: `{count, next, previous, results}`), `count` = qurilmalar soni. Qurilmalar eng oxirgi kirish bo'yicha tartiblangan.

Har qatorda:

| Maydon | Ma'nosi |
|---|---|
| `device` | Ko'rsatiladigan nom: "Chrome · Windows", "Mobil ilova" yoki mobil ilova yuborgan model |
| `browser`, `os`, `device_type` | `device_type`: `phone`, `tablet`, `computer` |
| `last_login_at` | OXIRGI kirish (ISO sana-vaqt). Kun, sana va soatni shundan ko'rsating |
| `first_login_at`, `login_count` | Birinchi kirish va shu qurilmadan nechta kirish bo'lgan |
| `last_ip`, `location`, `country` | Oxirgi kirishdagi IP va joylashuv (`location` GeoIP sozlangan bo'lsagina) |
| `session_active` | Shu qurilmada hozir ochiq seans bor |
| `is_current` | Hozirgi qurilma (faqat o'z tarixida) |
| `last_login_id` | Oxirgi kirish yozuvining id'si (ota-onaning "Bu farzandim" amali uchun) |

Eslatmalar:
- Qurilma IP bo'yicha aniqlanmaydi (mobil internetda IP tez-tez o'zgaradi). Qurilma = ko'rsatiladigan nom + turi. Brauzer versiyasi yangilansa (Chrome 157 dan 158 ga) yangi qurilma bo'lmaydi.
- **Mobil jamoaga:** bir nechta telefonni ajratish uchun login so'rovida `X-Device-Name: <model>` sarlavhasini yuboring (masalan "Xiaomi Redmi Note 12"). Aks holda hamma telefonlar bitta "Mobil ilova" qatoriga birlashadi. Sarlavha yuborilmagan eski kirishlar User-Agent bo'yicha guruhlanadi.
- `?group=device` berilmasa eski ro'yxat (har kirish alohida) o'zgarishsiz qoladi.
- Qatorni bosganda seansni yopish kerak bo'lsa avvalgi `GET/DELETE /auth/sessions/` ishlatiladi.

### 2. Chatda rasm yuborish: hamma yubora oladi (kod kerak emas)

Trello: "image yuborish qism qande qlamiz". Backendda rasm yuborishni rolga bog'lash yo'q: yozish huquqi bor har kim (o'quvchi, ota-ona, o'qituvchi) rasm yubora oladi: shaxsiy chat, guruh, kanalga izoh. Faqat kanalga POST (post yozish) va "e'lon rejimi" yoqilgan guruhda yozish hamma xabar turi uchun o'qituvchida qoladi. Frontend rasm tugmasini hamma rolga ko'rsatsa bo'ladi. Chegara: rasm 20 MB, bir xabarda 10 tagacha fayl.

### 3. Mock test'ni olib tashlash

Backend `exams` ga tegilmadi. Workspace'dagi "Mock testlar" kartasi va "Mock imtihon" statistikasi frontendda yashiriladi. Kerak bo'lsa backend API'ni ham o'chirishni ayting.

### 4. Darsga vaqtidan oldin kirish (productionda, 2026-11-20)

O'qituvchi ertaroq boshlagan darsga o'quvchilar kira olmasligining sababi kirish navbati hisoblagichi edi (`join_delay_ms` 10 daqiqadan oshib ketgan). Tuzatildi. Frontend `join_delay_ms > 0` bo'lsa "Navbatda, ~N soniya" deb ko'rsatsin, aks holda sahifa shunchaki "loading" bo'lib ko'rinadi.

### 5. Aniqlashtirish kerak: doskadagi formulalar

Trello: "Doskada bor formula qismlari hammasi yozish qismda chiqib kelsin va doskada ham shuni ko'rsatish". Rasm/tavsif yo'q. Doskadagi formula bloki (MathLive, LaTeX) allaqachon bor. Taxminim: shu formula tugmalari vazifa/test javobi yozish maydonida ham chiqsin. Bu asosan frontend ishi; qaysi sahifa ekanini ayting.

[↑ Mundarija](#mundarija)

---
