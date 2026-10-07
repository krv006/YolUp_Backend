# Fokus — EdTech Platformasi (MVP v0)

Onlayn ta'lim platformasi: jonli video darslar (LiveKit), avtomatik davomat va
rozilikka asoslangan ota-ona paneli. O'zbekiston bozori uchun.

> **Loyihaning to'liq umumiy hujjati: [PROJECT.md](PROJECT.md)** — modullar, API/WS
> shartnomasi, deploy, talablar holati.
> Arxitektura qoidalari: [ARCHITECTURE.md](ARCHITECTURE.md) — yangi kod yozishdan oldin o'qing.

## Stack

- **Backend:** Django + DRF + SimpleJWT (`root/` — settings, `apps/` — modullar)
- **Video:** LiveKit (self-hosted, docker-compose)
- **DB:** PostgreSQL (dev'da sqlite fallback)
- **Frontend:** ALOHIDA loyihada (boshqa jamoa) — bu repo faqat API beradi.
  Frontend domenini `.env` dagi `CORS_ALLOWED_ORIGINS` ga qo'shish kerak.
  API hujjatlari: `/api/docs/` (Swagger), sxema: `/api/schema/`

## Modullar

| Modul | Vazifasi |
|---|---|
| `apps/accounts` | Auth (JWT), 4 rol, ota-ona↔bola bog'lash (taklif-kod + tasdiq), rozilik (consent) |
| `apps/lessons` | Kurs, dars jadvali, yozilish, davomat hisoboti |
| `apps/live` | LiveKit xona tokeni + avtomatik davomat, diqqat tekshiruvi, fokus jurnali |
| `apps/chat` | Telegram uslubidagi chat: kurs guruhlari + o'qituvchi↔o'quvchi direct (so'rov/block) |
| `apps/board` | Jonli dars doskasi: chizish, matn/formula, o'chirish sababi, PDF → chat |
| `apps/homework` | Uy vazifasi: vazifa berish, fayl topshirish, o'qituvchi baholashi |
| `apps/core` | UUID/timestamp baza modellari, RBAC (`permissions.py`), audit log |

## Frontend integratsiyasi (alohida loyiha uchun shartnoma)

- **Auth:** `POST /api/v1/auth/login/` → `{access, refresh}`; har so'rovda `Authorization: Bearer <access>`
- **Doska real-time (WebSocket, polling KERAK EMAS):**
  `wss://<domain>/ws/board/<lesson_id>/?token=<access>` — boshlang'ich holatni
  REST `GET /board/<id>/` bilan oling, keyin faqat WS eventlarini qo'llang:
  `{"type":"stroke","sheet",...}`, `{"type":"erase",...}`, `{"type":"sheet",...}`.
  Chizishni WS orqali yuborish ham mumkin: `{"type":"stroke","sheet":0,"stroke":{...}}`
- **Doska stroke turlari (hammasi saqlanadi va PDF'ga tushadi):**
  qalam `{points,color,width,opacity?}` (opacity<1 = marker), matn
  `{type:'text',text,x,y,size,color}`, chiziq/strelka
  `{type:'line',x1,y1,x2,y2,arrow?}`, `{type:'rect',x,y,w,h}`,
  `{type:'ellipse',x,y,w,h}`, formula `{type:'math',latex,...}` (faqat matematika)
- **Chat real-time (WebSocket):** `wss://<domain>/ws/chat/<room_id>/?token=<access>`
  - Yopilish kodlari: `4401` token yaroqsiz, `4403` xonaga a'zo emas
  - Yuborish: `{"type":"message","text":"..."}` (yoki avvalgidek REST `POST .../send/` — ikkalasi ham broadcast bo'ladi)
  - "Yozmoqda...": `{"type":"typing"}` yuboriladi → boshqalarga `{"type":"typing","user_id","name"}` keladi (o'zingizni filtrlab tashlang)
  - Kelgan xabar: `{"type":"message","message":{id,room,sender,text,created_at}}`
  - Tarix/o'qilgan belgisi avvalgidek REST orqali (`GET .../messages/`, `POST .../read/`)
- **Hujjatlar:** `/api/docs/` (Swagger UI), `/api/schema/` (OpenAPI — client generatsiya qilsa bo'ladi)
- **LiveKit:** token `POST /api/v1/live/token/` (`{lesson_id}`), ulanish `wss://<domain>/livekit`
- **LiveKit optimizatsiya (MAJBURIY frontend sozlamalari)** — trafik/CPU bir
  necha barobar kamayadi:

  ```js
  import { Room, VideoPresets } from 'livekit-client';

  const room = new Room({
    // (2) Ko'rinmagan video umuman kelmaydi, kichik plitkaga kichik layer:
    adaptiveStream: true,
    // (1+2) Hech kim obuna bo'lmagan layerni PUBLISHER o'chiradi:
    dynacast: true,
    // Kamera 540p yetadi (plitkalar kichik) — 720p+ shart emas:
    videoCaptureDefaults: { resolution: VideoPresets.h540.resolution },
    publishDefaults: {
      // (1) Simulcast: har kamera 3 o'lchamda (katta/o'rta/kichik):
      simulcast: true,
      videoSimulcastLayers: [VideoPresets.h90, VideoPresets.h216],
    },
  });
  ```

  - **(3) Layout:** teng grid EMAS — spiker/o'qituvchi katta, qolganlar kichik
    thumbnail qatorda (`@livekit/components-react` da `FocusLayout` +
    `CarouselLayout`). Plitka kichik bo'lsa `adaptiveStream` avtomatik past
    layerga tushadi — 1 va 2-band o'z-o'zidan kuchliroq ishlaydi
  - Video elementlarni DOMdan olib tashlamang/`display:none` qiling —
    `adaptiveStream` ko'rinmaslikni o'zi aniqlab oqimni to'xtatadi
- **Doska PDF havolasi:** dars tugaganda backend kurs chatiga `"... /boards/<lesson_id>"`
  matnli xabar yuboradi — frontend shu yo'l uchun sahifa qilishi kerak
  (doska ma'lumoti: `GET /api/v1/board/<lesson_id>/`, PDF: `.../pdf/`)
- **Doska matematik rejimi (MathLive):** `GET /board/<id>/` javobidagi
  `math_enabled` bayrog'iga qarang — `true` bo'lsagina (faqat matematika
  kurslari) formula vositasini ko'rsating. Formula kiritish uchun
  [MathLive](https://mathlive.io/mathfield/) `<math-field>` tavsiya etiladi;
  doskaga saqlash: `POST .../stroke/` body `{sheet, stroke: {type:'math',
  latex:'\\frac{a}{b}', x, y, size, color}}` (LaTeX'ni `math-field.value`dan
  oling). Boshqa fanlarda server bu blokni 400 bilan rad etadi; SymPy yechuvchi
  (`POST .../solve/`) ham faqat matematikada ishlaydi. Statik ko'rsatish uchun
  MathLive'ning `convertLatexToMarkup` funksiyasi bor
- **Fayllar:** uy vazifasi fayllari auth talab qiladi — `GET /api/v1/homework/submissions/<id>/file/`
  va `.../assignments/<id>/file/` (to'g'ridan-to'g'ri `/media/` URL ishlatilmaydi)
- **CORS:** frontend domenini `.env` → `CORS_ALLOWED_ORIGINS` ga qo'shish shart

## Ishga tushirish

```bash
# 1. Muhit
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Infratuzilma (ixtiyoriy — sqlite bilan ham ishlaydi)
docker compose up -d          # Postgres + Redis + LiveKit

# 3. Migratsiya va server
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API hujjatlari: http://localhost:8000/api/docs/

## Smoke test

To'liq oqim (ro'yxat → bola → taklif-kod → dars → LiveKit token → davomat):

```bash
python scripts/smoke_test.py
```

## Muhim qarorlar

- **Rozilik-modeli:** ota-ona bolani faqat bolaning taklif-kodi va tasdig'i bilan
  kuzatadi; bola istalgan payt uzadi (prototipdagi Tahlil oqimi).
- **Self-hosted LiveKit:** birlik iqtisodi + data localization talabi
  (Tanqidiy Tahlil v4, 5- va 7-bo'limlar).
- **Migratsiyalar git'da yo'q:** har muhitda `makemigrations` qilinadi.
