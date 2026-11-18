# Frontend uchun vazifalar: backend tayyor, frontend qiladigan ishlar (2026-11-18)

> **ALMASHTIRILDI:** bu ertalabki holat edi (P1 email, P2 focus, P5 kanal/admin panel siz tomondan bugun bajarilgan). Hozirgi aniq ro'yxat: [FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY.md](FRONTEND_YANGILANISHLAR_2026-11-18_YAKUNIY.md).

Bugun backendda qilingan hamma ishning frontendga ta'siri bir joyda. Har bandda batafsil yo'riqnoma havolasi bor. Tartib: eng muhimidan.
Backend `main` da `a3fd185`, APP serverga chiqarilgan. Frontend `main` (`ed7bf08`) bilan solishtirildi.

## P1. Email: ro'yxatdan o'tish, kirish, parolni tiklash (productionda parol tiklash shunga bog'liq)

Batafsil: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md). Email xizmati endi **ulangan** va ishlayapti.

- [ ] **Parolni tiklash** oynasida telefon o'rniga **email** varianti: `POST /auth/password/reset/request|verify|confirm/` (`phone` yoki `email`). Email topilmasa ham javob `200 {sent:true}`: matn "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi".
- [ ] **Kirish** maydoni yorlig'i "Login yoki email" (endpoint o'sha `/auth/login/`, `username` maydoniga email ham yoziladi). Bir email bir nechta akkauntda bo'lsa `400` xabarini ko'rsating.
- [ ] **Ro'yxatdan o'tish:** `GET /auth/register/options/` ga qarab email qadami (`register/email/request` → `verify` → `email_token`). Hozir `email_required: false`, shuning uchun hozirgi oqim buzilmaydi; siz tayyor bo'lgach men `true` qilaman.
- [ ] **"Emailingizni qo'shing" oynasi** (mavjud foydalanuvchilar): `GET /auth/me/` dagi `email_setup_required` va `email_setup_deadline`; `POST /auth/me/email/request|confirm/`.
- Muhim: hozir productionda **tasdiqlangan email nolta**, ya'ni parolni unutgan hech kim tiklay olmaydi, shuning uchun oxirgi band birinchi chiqishi kerak.

## P2. Uy vazifasi: sahifadan chiqib-kirishni yuborish (hozir noto'g'ri nollar ko'rinadi)

Backend tayyor, frontend hech qachon yubormaydi, shu sababli o'qituvchi hamma o'quvchida "chiqmagan, 0 soniya" ko'radi.

- [ ] Vazifa topshirish sahifasida `visibilitychange` / `blur`+`focus` da `POST /homework/assignments/{id}/focus/` `{ "kind": "exit" }` va `{ "kind": "return" }` yuboring.
- Imtihondagi `POST /exams/{id}/focus/` bilan bir xil g'oya (u ulangan). Javob `200 {ok:true}`; `400` agar `kind` boshqacha, `403` agar kursga yozilmagan.
- O'qituvchi topshirilgan ishni ochganda javobdagi `focus` (`exits`, `away_seconds`, `timeline`...) endi haqiqiy bo'ladi. Batafsil: [FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md](FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md) 1-band.

## P3. Bildirishnomalar (push)

Backendda tuzatildi: push sarlavhasi endi "Fokus" emas ("Dars yozuvi tayyor", "Yangi baho", "To'lov" yoki "YolUp"), veb push matnida HTML yo'q, push fonda yuboriladi.

- [ ] **`public/sw.js`**: bosilganda faqat `link_type=lesson` ochiladi, qolganlari bosh sahifaga olib boradi. Backend `link_type` lari: `assignment`, `lesson`, `quiz`, `submission`, `course`, `chat_room`, `certificate`, `exam`, `recording`, `support`, `spam_report`, `teacher`, `link`, `login`. Ilovadagi bildirishnoma ro'yxati ishlatadigan `mapNotificationLink` (frontend: `src/modules/notification/lib/notification.mappers.ts`) mantiqini service worker'ga ham qo'llang (yoki push'dagi `link_type`/`link_id` ni ilovaga uzatib, o'sha yerda marshrutlang).
- [ ] **Veb push'ni taklif qilish.** Hozir u faqat sozlamalardagi yashirin tugma orqali yoqiladi (`use-push-notifications.ts`), productionda **obunalar nolta**. Birinchi kirishda "Bildirishnomalarni yoqish" taklifini ko'rsating (`enablePush()` tayyor).
- Mobil push (FCM) Firebase fayli kelgach ishlaydi, bu hozircha kutilmoqda.

## P4. Uy vazifasi: AI va rasmlar

Batafsil: [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](FRONTEND_JAVOB_AI_RASM_2026-11-18.md).

- [ ] Fayl tanlashga **`.heic` / `.heif`** qo'shing (`accept` va "PDF, JPG, PNG, DOCX · 25 MB gacha" matni). Server JPEG'ga o'tkazadi.
- [ ] O'qituvchi AI natijasida `ai_result.skipped_images` (son) bor bo'lsa, ajratib ko'rsating (masalan sariq belgi: "N ta sahifa AI ga sig'madi, ball faqat ko'rilganlar bo'yicha"). Ogohlantirish matni `ai_result.summary.recommendations[0]` da.

## P5. Backendda tayyor, lekin ekrani yo'q

- [ ] **Kanaldan guruhni ajratish:** `DELETE /chat/channels/{id}/courses/{course_id}/` → `{removed: n}`. Guruhlar ro'yxati kanal javobida: `course_ids`, `courses:[{id,title}]`.
- [ ] **Admin: mijoz salomatligi jadvali:** `GET /monitoring/client-health/?hours=24` (ixtiyoriy, admin paneliga).
- Ikkalasi: [FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md](FRONTEND_ULANMAGAN_ENDPOINTLAR_2026-11-17.md) 2-3 bandlar.

## P6. Trello'dagi frontend kartalari

- [ ] **vazifa berishda**: "Yangi vazifa" oynasida vazifa matni maydoni (description) ko'zga tashlanib turishi kerak (karta skrinshoti bor).
- [ ] **Doska** (RedZon): matn o'lchami ishlamay qolgan joy va chiziq yo'naltiruvchisi. Backend tayyor: matn o'lchami 12–48, `w` kengligi, `line`/`rect`/`ellipse`, tahrirlash (`update_stroke`). Backend rad etgan bo'lsa, `400` xabarini yuboring.
- **Qo'lda test yozish imkoni BOR** (kartaning savoliga javob): backend `POST /quizzes/`, frontendda `AddQuizDialog` (`group-workspace.tsx` ichida). Trello'ga shuni yozib, kartani yoping.

## QA: backend tayyor, frontendda tekshirish kerak

| Nima | Qanday tekshirish |
|---|---|
| **Meeting permission** ([FRONTEND_YANGILANISHLAR_2026-11-12_2.md](FRONTEND_YANGILANISHLAR_2026-11-12_2.md)) | (1) bir marta ruxsat → o'quvchi o'chirdi → qayta so'ralishi; (2) "hammani o'chirish" → ruxsat qaytadi; (3) ochiq rejimda kirgan yangi o'quvchi so'rovsiz yoqa oladi |
| **homework natija oynasi** | AI holatlari `checking / ready / unscored / failed` to'g'ri chiqishi |
| **homeworkcheck (fayl ixtiyoriy)** | faqat izoh bilan topshirish ishlashi |
| **Dars yozuvi uzluksizligi** ([FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md](FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md)) | oynalar almashtirilganda, ko'p seans va juda qisqa seansda yozuv uzilmasligi |
| **Darsga kirish** ([FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md)) | o'qituvchi boshlagach o'quvchi rejalashtirilgan vaqtdan oldin ham kira olishi, "aylanib turgan yopiq dars" ko'rinmasligi |
| **Material sonlari** ([FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md](FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md)) | guruh papkasida `recording_count`, `board_count` |
| **Spam shikoyatlari (admin)** | ro'yxat, `resolve` / `dismiss` / `unblock`; productionda 1 ta ochiq shikoyat turibdi |

## Hozircha frontendga tegishli bo'lmagan (backend kutmoqda)

Firebase (mobil push), chat xabarini tiklash, rasm yuborish qoidasi, "tech padeshka", o'tgan oylar qarzi: bular mahsulot qarori yoki tashqi kalit kutyapti. Qaror chiqqach alohida yozaman.

## Eslatma

- Yangi backend xabarlari (email, HEIC, login `@` qoidasi) ru va en tilida ham chiqadi (`Accept-Language` bo'yicha).
- `ai_result.usage` (token sarfi) o'qituvchi javobida ichki maydon sifatida keladi; ekranda ko'rsatish shart emas.
- Barcha endpoint yo'llari `/api/v1/...` bilan boshlanadi.
