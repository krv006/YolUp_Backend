# Frontend uchun: 11-noyabrdagi ikkinchi backend vazifalari javobi

Hammasi backendda tayyor va sinalgan. Har bir band uchun nima o'zgargani va frontend nima qilishi kerakligi.

---

## 1. Uy vazifasi: Google Form havolasi

- `POST /homework/assignments/` va `PATCH /homework/assignments/{id}/` — `google_form_url` (ixtiyoriy). Bo'sh satr = olib tashlash.
  Faqat `https://docs.google.com/forms/...`, `https://forms.google.com/...` yoki `https://forms.gle/...` qabul qilinadi, boshqasiga `400` (`error.details.google_form_url`).
- Javobda (o'qituvchi, o'quvchi, kuzatuvchi; ro'yxat ham, batafsil ham): `google_form_url` (`""` — yo'q).
- Oqim: o'quvchi vazifani ochadi → "Formani ochish" tugmasi (`google_form_url`) → to'ldirgach platformada **izoh bilan** topshiradi
  (`POST .../submit/` faylsiz, `comment` bilan; masalan "Formani to'ldirdim"). Form o'zi vazifa ichida ochilmaydi (Google iframe'ga ruxsat bermaydi) — yangi tabda oching.

## 2. Test: vaqt, urinishlar soni, nechta savol

O'qituvchi yaratishda (`POST /quizzes/`) yoki guruhga berishda (`PATCH /quizzes/{id}/`) quyidagilarni yuboradi (hammasi ixtiyoriy, `null` yoki yuborilmasa = cheklov yo'q):

| maydon | qiymat | ma'nosi |
|---|---|---|
| `time_limit_minutes` | 1–600 | testni boshlagandan keyin shuncha daqiqa ichida topshirish kerak |
| `max_attempts` | 1–20 | necha marta topshirish mumkin |
| `questions_per_attempt` | 1..testdagi savollar soni | har o'quvchiga savollardan nechtasi tushadi |

Test javobida (o'qituvchi uchun batafsil ham, ro'yxat ham) uchala maydon bor. `questions_per_attempt` matn/audioga bog'langan (`groups`) testda **berilmaydi** (`400`) — savollar o'z tartibida qoladi.

### O'quvchi oqimi

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

## 3. Savollar va variantlar tasodifiy tartibda

- Har o'quvchiga savollar va `single`/`multiple` variantlari o'z tartibida beriladi (avval faqat `ordering` va `matching` aralashar edi). To'g'ri javob doim bir joyda turmaydi.
- Tartib bitta urinish davomida o'zgarmaydi (sahifa yangilansa ham bir xil), yangi urinishda qayta aralashadi (urinish topshirilgach yoki vaqti tugagach).
- Matn/audioga bog'langan (`groups`, IELTS reading/listening) testda **savollar tartibi saqlanadi**, faqat variantlar aralashadi.
- Frontend `questions` va `options` ni **kelgan tartibda** ko'rsatsin (o'zi saralamasin, `order` bo'yicha ham emas). Natija sahifasida esa javoblar `answers` ro'yxati bo'yicha.
- Imtihon (`exams`) va o'qituvchi ko'rinishi (`GET` o'qituvchi/admin) o'zgarmagan.

## 4. Uy vazifasi ikki bosqichda: baza va biriktirish

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
