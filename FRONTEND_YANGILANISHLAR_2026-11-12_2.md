# Frontend uchun: 12-noyabr, Trello "Todo" kartalari bo'yicha backend yangiliklari

Hammasi backendda tayyor va sinalgan.

---

## 1. "Count qism larni ko'rib to'g'irlash" — vazifalar ro'yxatidagi "N / M topshirdi"

`GET /homework/assignments/?course=<id>` (o'qituvchi) har elementida yangi maydonlar:

| maydon | ma'nosi |
|---|---|
| `students_count` | vazifa berilgan o'quvchilar (guruh yoki tanlanganlar) |
| `submitted_count` | shulardan topshirganlar (bitta o'quvchi ko'p marta topshirsa ham 1) |
| `pending_review_count` | tekshiruv kutayotganlar (AI yoki o'qituvchi) |
| `graded_count` | o'qituvchi tasdiqlab baholaganlar |

Avvalgi `submissions_count` (jami topshiriq soni) saqlangan. "0 / 0 topshirdi" o'rniga `submitted_count / students_count` ko'rsating.

## 2. "Homework check da AI ni ko'rib berish" — AI holati

O'qituvchi uchun topshiriq javobida (`GET /homework/submissions/{id}/` va vazifa ichidagi `submissions[]`):

| `ai_state` | ma'nosi | nima ko'rsatish |
|---|---|---|
| `checking` | AI hali tekshirmoqda | "AI tekshirmoqda…" |
| `ready` | ball va natija bor | ball, baho, `ai_result` (savollar kesimida) |
| `unscored` | AI xulosa yozdi, lekin **ball qo'ymadi** | `ai_summary` matnini ko'rsating + "AI ball qo'ymadi — o'zingiz baholang" (oldin oyna "— ball / Baho yo'q" bo'lib bo'sh qolardi) |
| `failed` | AI baholay olmadi (`error`) | "AI baholay olmadi — o'zingiz baholang" |
| `none` | AI ishlatilmagan | AI bo'limini yashiring |

Yangi `ai_summary` (matn yoki `null`) — AI natijasidagi umumiy xulosa. Production'da AI hozir ichki OpenAI orqali ishlayapti (5 ta topshiriqdan 3 tasi baholangan, 1 tasi "baholay olmadi").

## 3. "ekran share, mic va camera" — hammasi bir martalik ruxsat

Mikrofon va kamera ruxsati avval ham bir martalik edi (`POST /live/release-media/`). Endi **ekran ulashish** ham:

- O'quvchi ulashishni to'xtatgach: `POST /live/release-media/ {lesson_id, kind: "screen"}` (`"screen_share"` ham bo'ladi) → `{revoked, open}`.
- Ruxsat (ekran video + ekran audio) olinadi; qayta ulashish uchun yana so'rov kerak. Mikrofon/kamera ruxsatlariga tegilmaydi.
- Hodisa (doska WebSocket'i): `{"type": "screen_revoked", "student_id": "..."}` — o'quvchi interfeysi "Ruxsat so'rash" holatiga qaytadi, o'qituvchi paneli yangilanadi
  (`mic_revoked` / `camera_revoked` kabi).
- Hammasi uchun qoida: o'quvchi mikrofon/kamera/ekranni **o'zi o'chirgan/to'xtatgan zahoti** `release-media` ni chaqiring.

## 4. "O'qituvchi tomonidan notification" — o'qituvchi + guruh nomi, xabar matni

O'qituvchi yozgan xabarda (`POST /notifications/send/`, `kind` yo'q) sarlavha va ma'lumot endi:

- `title`: **"O'qituvchi ismi · Guruh nomi"** (guruhsiz yuborilsa faqat ism; ism bo'lmasa login). Inbox ro'yxati, WebSocket va push bildirishnomada bir xil.
- `body`: o'qituvchi yozgan matnning o'zi (HTML'siz).
- `data`: `{teacher_name, course_id, course_title}` (guruhga yuborilganda).
- Tizim xabarlari (`kind` bor: dars eslatmasi, vazifa va h.k.) sarlavhasi avvalgidek.
- Web push va mobil push sarlavhasi ham shu ("Fokus" o'rniga).

## 5. "video record qilish qism" — yozuvni guruhga yuborishni darsga kirgach so'rash

O'qituvchi darsga kirgach: "Dars yozuvi tayyor bo'lgach guruhga tashlansinmi?" deb so'raladi.

- `GET /lessons/{id}/recording-choice/` → `{post_recording: true|false|null, decided: bool}`; `null` / `decided: false` — hali tanlanmagan, **so'rang**.
- `PATCH /lessons/{id}/recording-choice/ {post_recording: true|false}` — tanlov saqlanadi (faqat dars o'qituvchisi; boshqa qiymat `400`).
- Dars javobida (`GET /lessons/{id}/`) ham `post_recording` (`true|false|null`) bor.
- Dars tugaganda (`POST /lessons/{id}/finish/`) `post_recording` yuborilmasa shu tanlov ishlatiladi (tanlanmagan bo'lsa `true`); yuborilsa — yuborilgani ustun.

## 6. "account almashtirish ishlamayapdi"

`GET /auth/me/` ga ikkita maydon qo'shildi — "Akkauntni almashtirish" oynasini aniq chizish uchun:

- `available_roles`: hali **ochilmagan** rollar (`["teacher", "parent", "student"]` dan joriy va allaqachon bog'langanlari chiqarilgan). Shu ro'yxatdagi har bir rol uchun
  "ochib o'tish" qatori (`POST /auth/switch-role/ {role}`).
- `role_switch_blocked`: telefon raqami yo'q bo'lsa `"phone_required"` (`available_roles` bo'sh bo'ladi) — oynada "Avval profilga telefon raqamini kiriting" deb ko'rsating.
  Telefoni bor bo'lsa `null`.
- Mavjud bog'langan akkauntlar avvalgidek `linked_accounts` da (`POST /auth/switch/{id}/`).
- Production ma'lumoti: foydalanuvchilarning ~1/3 qismida telefon yo'q (bunday akkauntlar almashtira olmaydi), faqat bitta telefon raqamida ikkita rol bor.
  Ko'pchilikda "boshqa rol" hali ochilmagan bo'lgani uchun oynada faqat o'zi ko'rinishi normal; qolgan rollar `available_roles` dan chiziladi.

## 7. "spam berish adminga borishi kerak" — mavjud oqim (o'zgarmagan)

Backend 10-noyabrda tayyor. Qisqacha:
1. Shaxsiy chatda `POST /chat/rooms/{id}/report/ {reason, comment?}` (`reason`: `insult` | `harassment` | `advertising` | `other`) — chat darhol `spam` holatiga o'tadi.
2. **Barcha adminlarga** bildirishnoma boradi (`kind: "spam_report"`, `link_type: "spam_report"`, `link_id` — shikoyat id).
3. Admin paneli: `GET /admin/reports/?status=open|resolved|dismissed`, `GET /admin/reports/{id}/` (oxirgi 10 xabar bilan),
   `POST /admin/reports/{id}/resolve/` (to'g'ri, chat bloklangan qoladi), `.../dismiss/` (asossiz, chat qayta ochiladi), `.../unblock/` (istalgan paytda qayta ochish).
Production'da hozircha birorta shikoyat yo'q (sinab ko'ring).

## 8. "video qotib qoldi" — diagnostika

Alohida hujjat: `FRONTEND_QOTISH_TAHLILI_2026-11-12.md` (sabab tahlili, tavsiyalar va `client-health` endpoint'i).
