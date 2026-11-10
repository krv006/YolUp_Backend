# Backend yangilanishlari (2026-11-10) — `BACKEND_VAZIFALAR.md` bo'yicha

Raqamlar `BACKEND_VAZIFALAR.md` dagi band raqamlari. Endpoint nomlari taklifdagidek; farq bo'lsa shu yerda yozilgan.
Hammasi testlar bilan yopilgan, serverga hali chiqarilmagan (deploy oxirida).

**Bajarilmagan / javob kutayotgan:** 14 (sertifikat holati — savol), 15 (pullik test — "keyinroq" deyilgan, tegilmadi),
"Ochiq savollar"dan 1-savol (kanalga keyin qo'shilgan o'quvchi). 16 va 22 — backendda ish yo'q.

---

## 1. Telefon raqami va akkaunt almashtirish

- Telefon endi **har doim `+998XXXXXXXXX`** ko'rinishida saqlanadi (ro'yxatdan o'tish, profil, raqam almashtirish, admin — hammasida).
  `901234567`, `+998 90 123 45 67`, `998901234567` bir xil raqam.
- `linked_accounts` va akkaunt almashtirish raqamlarni faqat raqamlari bo'yicha solishtiradi.
- Bazadagi eski raqamlar deploy paytida data-migratsiya bilan (`accounts 0022`) o'tkaziladi. Raqam bo'lmagan qiymatlarga tegilmaydi.
- **Frontend:** raqamni qanday yuborsangiz ham bo'ladi; javobda doim `+998...` qaytadi.

## 2. Davomat: oynadan chiqishlar

- `GET /courses/{id}/attendance/summary/`: har `students[]` qatorida `focus_exits` va javob ildizida `focus_exits` (tanlangan `range` bo'yicha jami).
- `GET /lessons/?course=`: har darsda `focus_exits` — shu darsdagi barcha o'quvchilarning chiqishlari jami.
  **Faqat o'qituvchi/admin uchun**, boshqalarga `null`.
- Hisob: `exit` hodisalari soni (qaytmagan chiqish ham 1 ta).

## 3. Chat ruxsatlari

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

## 4. Qidiruv

`GET /auth/users/search/?q=` va `GET /search/?type=people` — endi o'quvchi va ota-ona ham ishlatadi (avval o'quvchiga `403` edi).

- **O'qituvchi:** o'z guruhlaridagi o'quvchilar (kutayotganlari ham) va ularning ota-onalari (ism, @username, telefon).
- **O'quvchi:** hammani topadi — o'qituvchilar, o'quvchilar, ota-onalar. Telefon bo'yicha begona topilmaydi.
- **Ota-ona:** farzandining o'qituvchilari.
- Har natijada: `id, name, username, role, avatar, room_id, direct_status, can_message`.
  `can_message`: `"write"` (yozish), `"request"` (so'rov yuborish), `"none"`.
- Begona uchun faqat ism, username, avatar, rol chiqadi. Admin qidiruvi o'zgarmagan.

## 5. Spam / shikoyat

- `POST /chat/rooms/{id}/report/ {reason, comment?}` — `reason`: `insult | harassment | advertising | other`. Barcha rollar, faqat shaxsiy chatda.
  Javob `201`: shikoyat. Chat **darhol** `spam` holatiga o'tadi: belgilangan odam yozolmaydi, qayta so'rov ham yubora olmaydi,
  o'qituvchi accept/open qila olmaydi. Takroriy bosish yangi shikoyat yaratmaydi. Adminlarga bildirishnoma (`kind: spam_report`).
- Admin (`user.manage`):
  - `GET /admin/reports/?status=open|resolved|dismissed` — sahifalangan ro'yxat;
  - `GET /admin/reports/{id}/` — shikoyat + suhbatning oxirgi 10 xabari (`recent_messages`);
  - `POST /admin/reports/{id}/resolve/` — tasdiqlash (chat bloklangan qoladi);
  - `POST /admin/reports/{id}/dismiss/` — rad etish (chat avvalgi holatiga qaytadi);
  - `POST /admin/reports/{id}/unblock/` — chatni qayta ochish.

## 6. Rollar yorlig'i

`role` hamma joyda bor: xabar `sender.role`, a'zolar ro'yxati, qidiruv, `other_user.role`. Qo'shildi:
chat ro'yxatidagi `last_message.sender_role`.

## 7. Kanal

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

## 8. Speaking club

Club = `Course` (`kind: "club"`): o'z chat xonasi, jonli darslar, davomat va yozuvlar tayyor infratuzilmadan ishlaydi.

- `GET /clubs/` — o'qituvchi: o'z clublari; o'quvchi: a'zo bo'lganlari; ota-ona: farzandining clublari.
- `POST /clubs/ {title, description?, subject?, course_ids?, student_ids?}` — o'qituvchi. Tanlangan guruhlar (butun) yoki alohida
  o'quvchilar **darhol a'zo** bo'ladi (tasdiqlash shart emas) va `kind: club_added` bildirishnomasi oladi.
- `GET/PATCH/DELETE /clubs/{id}/`; `GET|POST /clubs/{id}/members/`, `DELETE /clubs/{id}/members/{student_id}/`.
- Javobda `chat_room_id`, `members_count`, `kind: "club"`.
- **Jonli mashg'ulot:** oddiy `/lessons/` (`course = club id`) — rejalashtirish, "boshlandi" signali, yozuv, davomat shu yo'l bilan.
- `GET /courses/` (guruhlar ro'yxati) clublarni **ko'rsatmaydi**; kerak bo'lsa `?kind=club` yoki `?kind=all`. `GET /courses/catalog/` ham clubsiz.
  `CourseSerializer` ga `kind` qo'shildi.

## 9. Materiallar: Guruh → darslar → fayllar

- `Material.lesson` (ixtiyoriy). Yuklashda `lesson=<id>` (multipart). Darssiz fayllar — "Umumiy".
- `GET /materials/courses/` — guruhlar va fayllar soni.
- `GET /materials/courses/{id}/lessons/` — `{course, general: {file_count}, lessons: [{id, title, starts_at, status, file_count, has_recording, has_board}]}`.
  O'quvchi/ota-ona faqat mazmuni bor (fayl, tayyor yozuv yoki doska) darslarni ko'radi; o'qituvchi hammasini.
- `GET /materials/?course=&lesson=<id>|general` — fayllar (`lesson_id` har faylda).
- `GET /materials/lessons/{id}/` — dars papkasi: `{lesson, files, recording: {status, info_url} | null, board: {pdf_url} | null}`.
  Video yozuv va doska PDF'i nusxalanmaydi — havola bilan (`info_url` = mavjud `/lessons/{id}/recording/`).
- `GET /materials/lessons/{id}/board.pdf` — doska PDF'i (ota-onada ham ishlaydi).

## 10. Balans va to'lov eslatmalari

- `Course.payment_day` (1–28) va `Course.payment_reminder_days` (`[3, 5, 7]` dan, bir nechtasi mumkin — ochiq savol 2: ruxsat berilgan)
  — `PATCH /courses/{id}/`. Eslatma kunlari berilsa `payment_day` shart.
- Kunlik (soatlik tekshiruv) job: muddatdan N kun oldin shu oy to'lanmagan o'quvchiga **va** uning tasdiqlangan ota-onalariga
  bildirishnoma (`kind: payment_reminder`, matnda summa va muddat). Har eslatma bir marta.
- `unpaid_count` va `overdue_count` (joriy oy) — o'qituvchida `GET /courses/` va `GET /chat/rooms/` (kurs guruhi) da; boshqalarga `null`.
  To'lov sozlanmagan guruh (`monthly_fee` ham, `payment_day` ham yo'q) "to'lamagan" hisoblanmaydi.
- Progress to'lov qatorida `overdue: bool` (muddat o'tgan va to'lanmagan). `status` hamon `paid | unpaid`.

## 11. O'qituvchining qo'lda bildirishnomasi

`POST /notifications/send/ {target_type: "course", course_id, include_parents?: bool, description}` — o'z guruhining barcha
tasdiqlangan o'quvchilari (+ ixtiyoriy ota-onalari).

## 12. Ota-ona: ball tarixi

`GET /analytics/child/{id}/scores/?range=8w|6m|all` — uy vazifasi + test (har testning eng so'nggi urinishi) + mock imtihon, hammasi 10 ballik.

```json
{ "range": "8w", "scale": 10, "period_type": "week",
  "summary": {"overall": 8.1, "homework": 8.5, "quiz": 9.0, "exam": 7.8, "count": 4},
  "periods": [{"start": "2026-11-09", "overall": 9.0, "homework": 9.0, "quiz": 9.0, "exam": null, "count": 2}, ...],
  "points": [{"date": "...", "kind": "homework|quiz|exam", "title": "...", "score_10": 8.0}, ...] }
```

`8w` — 8 hafta (haftalar), `6m` — 6 oy, `all` — birinchi balldan (ko'pi bilan 24 oy), oylar. `analytics` roziligi o'chiq bo'lsa `403`.
Matnlarda "Kuzatuvchi / O'quvchi" so'zlari: backend yaratadigan matnlarda hozircha o'zgarmagan (alohida ish).

## 13. Uy vazifasi ichida savollar

- Vazifa yaratish/tahrirlashda `questions: [{type: single|multiple|short|long, text, options?, correct?: [indekslar], points?}]`
  (JSON yoki multipart'da JSON matn). `GET /homework/assignments/{id}/` da `questions` (o'quvchiga `correct`siz), `has_questions`, `questions_points`.
  Topshiriq tushgach savollarni o'zgartirib bo'lmaydi.
- Topshirish: `POST /homework/assignments/{id}/submit/ {answers: [{question_id, answer}]}` — test: tanlangan indekslar ro'yxati,
  ochiq: matn. Savollar bo'lsa fayl majburiy emas (xohlasa biriktiradi).
- Testlar darhol baholanadi ("bir nechta to'g'ri"da hammasi yoki hech nima). **Ochiq savol yo'q bo'lsa natija avtomatik tasdiqlanadi (`done`)**.
  Ochiq savol bor bo'lsa: `ai_check` yoqilgan va ichki AI sozlangan bo'lsa AI baholaydi, aks holda o'qituvchi; yakuniy ballni o'qituvchi tasdiqlaydi.
- Natijada `answers: [{question_id, answer, score, correct?, is_correct?, ai_score? (o'qituvchiga)}]`.
- O'qituvchi baholash: `POST /homework/submissions/{id}/review/ {answer_scores: {question_id: ball}}` — umumiy baho berilmasa shulardan hisoblanadi.

## 17. Darsda hammani cheklash

- `POST /live/mute-all/ {lesson_id, except?}` — endi mikrofonni o'chiradi **va ruxsatini qaytarib oladi**. Javob `{muted: n}`.
- `POST /live/camera-off-all/ {lesson_id, except?}` (yoki `mute-all` ga `kind: "video"`) — kamera. Javob `{camera_off: n}`. Ekran ulashishga tegilmaydi.
- WS (doska kanali): `{type: "mic_revoked" | "camera_revoked", student_id}` — o'quvchi interfeysi "So'rash" holatiga qaytadi,
  o'qituvchi paneli yangilanadi.

## 18. Bir martalik ruxsat

`POST /live/release-media/ {lesson_id, kind: "microphone"|"camera"}` — o'quvchi ruxsat berilgan mikrofon/kamerani **o'chirgach**
frontend shuni chaqiradi. Javob `{revoked, open}`; ruxsat olinadi, `mic_revoked`/`camera_revoked` hodisasi ketadi.
Ochiq rejim yoqilgan bo'lsa ruxsat olinmaydi (`open: true`).

(LiveKit webhook ishlatilmadi: LiveKit "track muted" webhook hodisasini yubormaydi, faqat `track_unpublished`, shuning uchun ishonchsiz.)

## 19. Ochiq mikrofon / ochiq kamera

- `Lesson.open_mic`, `Lesson.open_camera`. `PATCH /live/lesson/{id}/media-mode/ {open_mic?, open_camera?}` (o'qituvchi), `GET` — holat.
- Holat `POST /live/token/` javobida (`open_mic`, `open_camera`) va `GET /live/lesson/{id}/presence/` da ham qaytadi.
- Yoqilganda xonadagi o'quvchilarga ruxsat darhol qo'shiladi, keyin kirganlar tokenda oladi. O'chirilganda yoqilgan mikrofon/kameralar
  o'chiriladi va ruxsat olinadi (ochiq savol 3 bo'yicha taklif qilingan "ha").
- Ota-ona roziligi (`consent camera`) baribir amal qiladi.
- WS: `{type: "media_mode", open_mic, open_camera}`.

## 20. Yozuvni guruhga yuborish — ixtiyoriy

`POST /lessons/{id}/finish/ {recording_title?, post_recording?: bool}` — standart `true`. `false` bo'lsa yozuv tayyor bo'lganda guruhga xabar
va bildirishnoma **yuborilmaydi**. "Chatga yuborish" (`recording/share/`) o'zgarmagan. `GET .../recording/` javobida `post_to_chat`.

## 21. Yozuv konvertatsiyasi — tayyor bo'lguncha yopiq

- Yangi yozuv MP4 nusxa tayyor bo'lguncha **hech kimga (o'qituvchiga ham) ochilmaydi**: `GET /lessons/{id}/recording/` →
  `status: "converting"`, `ready: false`, `stream_url: null`. Frontend holatni vaqti-vaqti bilan so'rab turadi.
- Guruhga xabar va bildirishnoma konvertatsiya tugagach ketadi.
- Konvertatsiya xato bilan tugasa — asl WebM bilan ochiladi (va e'lon qilinadi). 12 soatdan uzoq cho'zilsa ham WebM bilan ochiladi.
- Eski yozuvlar (shu o'zgarishdan oldingi) avvalgidek ochiq, qayta e'lon qilinmaydi.
- Server yuklamasi: konvertatsiya bitta-bitta, `nice` bilan; server band bo'lsa (1 daqiqalik yuklama > yadrolarning 70%) kutadi
  (`TRANSCODE_MAX_LOAD_RATIO`), lekin yozuv 2 soatdan uzoq kutmaydi.
- Materiallar dars papkasida ham o'qituvchiga `converting`, o'quvchiga yopiq.

---

## Deploy

Migratsiyalar bor (APP serverda `up -d --build` o'zi bajaradi). Tartib: **avval APP, keyin MEDIA** (yozuv va konvertatsiya MEDIA'da ishlaydi va yangi
maydonlarni yozadi).

Yangi doimiy vazifa: `send_payment_reminders` (`run_scheduler` o'zi oladi, APP'da).
