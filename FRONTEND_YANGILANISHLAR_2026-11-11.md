# Frontend uchun: yangi backend imkoniyatlari (Trello "Todo" kartalari)

Hammasi backendda tayyor va sinalgan. Quyida har bir karta uchun nima o'zgargani va frontend nima qilishi kerakligi.

---

## 1. "test yaratish qismi" — guruh ixtiyoriy

`POST /quizzes/` (va AI/import/Google yo'llari) endi **guruh ham, fan ham bermasdan** ishlaydi.
- Guruhsiz test faqat muallif o'qituvchiga ko'rinadi, o'quvchilarga chiqmaydi.
- Keyin guruhga berish: `PATCH /quizzes/{id}/ {course: "<id>"}` (avvalgidek).
- "Guruh" maydonini formada ixtiyoriy qiling ("Guruhsiz saqlash").

## 2. "test di guruhga berish" — alohida o'quvchilarga berish

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

## 3. "dars yaratish" — bir vaqtda bir nechta dars

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

## 4. "Kanal image change"

- `POST /chat/channels/{id}/image/` (multipart, `image` fayl) — kanal rasmini o'rnatadi/almashtiradi;
  `DELETE /chat/channels/{id}/image/` — olib tashlaydi. Faqat kanal egasi.
  Xuddi shu ishni `POST/DELETE /chat/rooms/{id}/image/` ham qiladi (guruh va kanal uchun).
- Javob — xonaning to'liq ma'lumoti; `image` — to'liq URL (yoki `null`). Chat ro'yxatida va a'zolarda shu `image` ko'rinadi.

## 5. "homeworkcheck" — fayl yuklash ixtiyoriy

- `POST /homework/assignments/{id}/submit/`: fayl bo'lmasa ham **izoh (`comment`) bilan** topshirsa bo'ladi (matnli javob).
  Na fayl, na izoh bo'lsa — `400`.
- Faylsiz topshiriq AI'ga yuborilmaydi, to'g'ridan-to'g'ri o'qituvchiga baholashga tushadi. Javobda `files: []`, `file_name: ""`.
- O'qituvchi sahifasida faylsiz topshiriq uchun yuklab olish tugmasini yashiring (`GET .../submissions/{id}/file/` bunda `404` beradi); `comment` ni asosiy javob sifatida ko'rsating.
- Formada "Faylni yuklang" bloki ixtiyoriy bo'lsin: "Fayl yuklang yoki javobingizni izohga yozing".

## 6. "homework" — natijani ko'rish ishlamayapti ("AI tekshiruv natijasi" bo'sh)

Skrinshotda oyna "— ball / Baho yo'q" bilan bo'sh chiqqan, chunki topshiriq hali `Tekshirilmoqda` edi. Endi o'qituvchiga topshiriq javobida aniq holat keladi:

| `ai_state` | ma'nosi | Oynada nima ko'rsatish |
|---|---|---|
| `checking` | AI hali tekshirmoqda (`ai_checking_since` — qachondan) | "AI tekshirmoqda…" (spinner), ball maydonini yashirish |
| `ready` | AI natijasi tayyor (`ai_result`, `ai_overall_score`) | Natija |
| `failed` | AI baholay olmadi (`error` — sabab) | "AI baholay olmadi — o'zingiz baholang" |
| `none` | AI ishlatilmagan | AI bo'limini yashirish |

- Backend AI tekshiruvi 15 daqiqa ichida tugamasa yoki xato bersa topshiriqni avtomatik o'qituvchiga (`failed`) o'tkazadi, shuning uchun "Tekshirilmoqda" abadiy qolmaydi.
- `ai_state` faqat o'qituvchi/admin javobida bor; o'quvchida yo'q.

## 7. "account almashtirish ishlamayapdi"

Karta 2026-11-10 ertalab ochilgan edi. O'shandan beri backendda telefon raqamlari bir xil ko'rinishga keltirildi (`+998XXXXXXXXX`), shu sababli bitta odamning akkauntlari (o'qituvchi/o'quvchi/kuzatuvchi) endi bir-biriga to'g'ri bog'lanadi.
- Ro'yxat: `GET /auth/me/` → `linked_accounts` (joriy akkauntdan boshqalari). O'tish: `POST /auth/switch/{id}/`.
- "Boshqa akkaunt qo'shish": `POST /auth/switch-role/ {role: "teacher"|"parent"|"student"}` — rol hali yo'q bo'lsa avtomatik ochiladi (o'quvchi akkauntidan boshqa rolga o'tib bo'lmaydi).
- Agar yangilangandan keyin ham faqat bitta akkaunt chiqsa — shu odamning boshqa akkauntlarida telefon raqami boshqacha yoki bo'sh; xabar bering, tekshiramiz.

---

## Backendga tegishli bo'lmagan kartalar (frontend)

- **"test yaratish qism"** — Word/Excel/Google Forms tugmalari bir xil ochilishi (UI).
- **"meeting"** — qaysi ekran ulashilayotgani doim ko'rinib tursin (UI + LiveKit trek nomi; backend kerak emas).
- **"vazifa berish da"** — fon (background) muammosi (UI).

## Savol bor

**"Vazifa: HomeWork"** kartasi ("file yuklash, google forma qilish imkoni; doska; ruchnoy; AI qila olmasa o'zin hal qil") — bir qismi allaqachon bor (doskada yechish, AI qila olmasa o'qituvchiga tushishi, savolli vazifa). Google Form orqali topshirish qanday bo'lishi kerakligini aniqlashtirish kerak: (a) o'qituvchi vazifaga Google Form havolasini qo'shadi va o'quvchi shu yerda to'ldiradimi, yoki (b) Google Form'dan savollarni vazifaga import qilamizmi (testlardagidek)?
