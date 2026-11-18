# Frontend ulamagan backend endpointlari — aniq ro'yxat (2026-11-17)

Backend marshrutlari (294 ta yo'l) frontend repo'si `krv006/YolUp_Web` (`main`, `0df424b`) bilan yo'l bo'yicha taqqoslandi,
so'ng har bir endpoint backend kodidan o'qib chiqildi. Hamma yo'llar `/api/v1/` bilan boshlanadi. Auth: `Authorization: Bearer <access>`.

> **Tuzatish.** Avval "23 ta" degan edim. Aniqrog'i **21 ta**: 2 tasi endpoint emas, DRF'ning ko'rsatkich sahifalari
> (`/api/v1/` va `/api/v1/chat/`). Bu 21 tadan **7 tasi frontendga allaqachon ulangan** (boshqa yo'l bilan yoki serverdan kelgan havola orqali),
> shuning uchun **haqiqatan ulanmagani 14 ta**.

## Qisqa xulosa

| Guruh | Soni | Frontend nima qilsin |
|---|---|---|
| **A. Hozir ishlaydi, UI yo'q** | 3 | Ulash mumkin va kerak: [1](#1-uy-vazifasi-sahifadan-chiqib-kirish), [2](#2-kanaldan-guruhni-ajratish), [3](#3-adminga-mijoz-salomatligi-xulosasi) |
| **B. Tayyor, lekin serverda xizmat ulanmagan** | 11 | UI'ni tayyorlash mumkin, lekin ishlashi uchun biz tashqi kalit/xizmat ulashimiz kerak ([4](#4-sms-va-email-tasdiqlash-8-ta), [5](#5-google--apple-bilan-kirish), [6](#6-mobil-push-faqat-mobil-ilova)) |
| **C. Allaqachon ulangan (yolg'on signal)** | 3 | Hech narsa qilmang: havola javob ichida keladi ([7](#7-javob-ichida-keladigan-havolalar-ulangan)) |
| **D. Eskirgan takror (alias)** | 4 | Hech narsa qilmang: frontend yangisidan foydalanadi ([8](#8-takror-yollar-alias)) |

---

## A. Hozir ishlaydi — frontend UI'si yo'q (3 ta)

### 1. Uy vazifasi sahifasidan chiqib-kirish

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

### 2. Kanaldan guruhni ajratish

`DELETE /api/v1/chat/channels/{channel_id}/courses/{course_id}/` — **kanal egasi (o'qituvchi)**, ruxsat `chat.use`.

- Javob `200 {"removed": 12}` — nechta a'zo chiqarildi.
- Faqat **shu guruh orqali** kelgan a'zolar chiqariladi. Kanalga alohida (`student_ids` bilan) qo'shilganlar qoladi.
- Hozir frontendda kanalga a'zo qo'shish (`POST channels/{id}/members/`) bor, lekin guruhni ajratish tugmasi yo'q.
- Qaysi guruhlar ulangani kanal javobida bor: `GET chat/rooms/` (`kind: "channel"`) da `course_ids` va `courses: [{id, title}]`. Ro'yxatni shundan oling, har bir guruh yoniga "ajratish" tugmasini qo'ying; muvaffaqiyatdan keyin kanalni qayta yuklang.

### 3. Adminga mijoz salomatligi xulosasi

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

## B. Backend tayyor, lekin serverda tashqi xizmat ulanmagan (11 ta)

**Production holati (2026-11-17 da tekshirilgan; 2026-11-18 da YANGILANDI):** `SMS_BACKEND`, `ESKIZ_EMAIL`, `GOOGLE_CLIENT_IDS`, `APPLE_CLIENT_IDS`, `FCM_PROJECT_ID` hali bo'sh.
**Email (`EMAIL_HOST`) 2026-11-18 dan ulangan va ishlaydi**: `auth/email/send-code`, `auth/email/verify` va yangi email endpointlari ishlaydi (qarang `FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md`).
SMS, Google/Apple va mobil push endpointlari hozir ishlab chiqarishda **503** qaytaradi. Bu ataylab: kod yuborilmagan bo'lsa "yuborildi" deb yolg'on aytilmaydi.
UI'ni oldindan yozish mumkin, lekin 503 ni chiroyli ko'rsating ("Hozircha mavjud emas").

### 4. SMS va email tasdiqlash (8 ta)

Hammasida kod 5 xonali, **120 soniya** amal qiladi; qayta yuborish **45 soniyadan** keyin; kuniga eng ko'pi **10** marta;
noto'g'ri kiritish **5 martadan** keyin kodni bekor qiladi. Barchasi `POST`.

**Yuborish javobi (hammasida bir xil):** `200 {"sent": true, "expires_in": 120, "retry_after": 45}`
**Xatolar (hammasida):** `429` (juda tez/ko'p, `Retry-After` sarlavhasi va `wait`), `400 {"detail": "Kod noto'g'ri yoki muddati o'tgan"}`,
`503` (SMS/email ulanmagan), `502` (provayder xato berdi).

#### 4.1 Ro'yxatdan o'tishdan OLDIN telefonni tasdiqlash (login kerak emas)

1. `POST /auth/register/phone/request/` — `{ "phone": "+998901234567" }` → yuborish javobi.
2. `POST /auth/register/phone/verify/` — `{ "phone": "...", "code": "12345" }` → `{ "phone_token": "...", "expires_in": 1800 }`.
3. `POST /auth/register/` — oddiy ro'yxatdan o'tish tanasiga `"phone_token": "<token>"` qo'shing.
   Token **bir marta** ishlaydi, 30 daqiqa amal qiladi, aynan shu raqamga bog'liq. Token berilmasa, raqam tasdiqlanmagan holda saqlanadi
   (hozirgi frontend oqimi shunday ishlaydi, ya'ni buzilmaydi). Yaroqsiz token bo'lsa `400 {"phone_token": [...]}`.

#### 4.2 Profildagi telefonni almashtirish (login kerak)

1. `POST /auth/me/phone/request/` — `{ "phone": "+998..." }` → YANGI raqamga kod ketadi (eski raqam kod tasdiqlanguncha o'zgarmaydi).
2. `POST /auth/me/phone/confirm/` — `{ "phone": "+998...", "code": "12345" }` → yangilangan profil (`GET /auth/me/` shaklida);
   `phone_verified: true` bo'ladi.

#### 4.3 Mavjud telefon / emailni tasdiqlash (login kerak)

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

### 5. Google / Apple bilan kirish

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

### 6. Mobil push (faqat mobil ilova)

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

## C. Allaqachon ulangan: yo'l javob ichida keladi (3 ta)

Skript buni "ishlatilmayapti" deb ko'rsatdi, chunki frontend yo'lni qo'lda yozmaydi, **serverdan kelgan havolani** ishlatadi. Hech narsa qilmang.

### 7. Javob ichida keladigan havolalar (ulangan)

| Endpoint | Frontend qayerdan oladi |
|---|---|
| `GET /chat/attachments/{id}/` (`?thumb=1` — eskiz) | `GET /chat/rooms/{id}/attachments/` javobidagi `url` / `thumbnail_url` (`message.api.ts`) |
| `GET /lessons/{id}/recording/stream/?t=<token>` | `GET /lessons/{id}/recording/` javobidagi `stream_url` (`lesson-recording-player.tsx`) |
| `GET /lessons/{id}/board/preview/{n}/?t=<token>` | o'sha javobdagi `board_page_previews[].image_url` (`lesson.mappers.ts`) |

> **Muhim qoida:** `stream_url` va `image_url` — **imzolangan, muddatli** havolalar (`?t=...`). Ularni qo'lda yig'ib yoki keshlab qo'ymang;
> har safar `recording/` ni so'rab yangisini oling. Bu ikkisida `Authorization` sarlavhasi kerak emas (`<video src>`, `<img src>` uchun).

---

## D. Eskirgan takror yo'llar — alias (4 ta)

Hech narsa qilmang. Backendda bir xil ishni bajaradigan boshqa yo'l bor va frontend o'shani ishlatadi.

### 8. Takror yo'llar (alias)

| Takror yo'l | Frontend ishlatadigan yo'l | Farqi |
|---|---|---|
| `POST /chat/rooms/{id}/forward/` `{message_ids}` | `POST /chat/messages/forward/` `{message_ids, target_room_ids}` | yangisi bir nechta chatga yuboradi |
| `POST/DELETE /chat/rooms/{id}/pin/` `{message_id}` | `GET/POST /chat/rooms/{id}/pinned/`, `DELETE .../pinned/{message_id}/` | eskisi faqat **bitta** xabar qadaydi, yangisi bir nechta |
| `POST/DELETE /chat/channels/{id}/image/` | `POST/DELETE /chat/rooms/{id}/image/` | ikkalasi bir xil kodni ishlatadi, kanal ham "room" |
| `GET /lessons/{id}/board/` | `GET /board/{lesson_id}/` | yozuv sahifasi uchun qulay nusxa, javobi bir xil |

(`/chat/rooms/{id}/pin-room/` — bu suhbatni ro'yxat tepasiga qadash, boshqa narsa, frontend uni ishlatadi.)

---

## Tekshirilmagan narsalar

- Solishtirish **yo'l bo'yicha** bo'ldi, HTTP metod bo'yicha emas (masalan, frontend `GET` ishlatib, `DELETE` ni ishlatmayotgan bo'lishi mumkin).
- Faqat web frontend `main` shoxi o'qildi. Mobil ilova yoki boshqa shoxlar bu endpointlarni ishlatayotgan bo'lishi mumkin.
- `${...}` bilan dinamik yig'ilgan yo'llar va `.js`/`.tsx` dan tashqari fayllar qidiruvga tushmagan bo'lishi mumkin.
- SMS, email, Google/Apple va FCM oqimlarini **haqiqiy xizmat bilan** sinab ko'rmadim, faqat kod va testlarda tekshirilgan. Ishlab chiqarishda ular ulanmagan.

## Qaysi birini avval ulash kerak (tavsiya)

1. **Uy vazifasi `focus`** (1-band): backend tayyor va ishlaydi, hozir o'qituvchi hamma o'quvchida "chiqmagan" ko'radi, bu noto'g'ri ko'rsatkich.
2. **Kanaldan guruhni ajratish** (2-band): kichik UI.
3. **Admin client-health** (3-band): ixtiyoriy, admin panelga qo'shimcha.
4. B guruhi (4–6): kalitlar/xizmatlar ulangandan keyin.
