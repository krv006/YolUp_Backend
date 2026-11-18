# Trello "Yolup" doskasi: ochiq vazifalar, kod va serverga solishtirilgan (2026-11-18)

> **Yangilanish (kechqurun):** bu hujjat ertalabki holatni ko'rsatadi. Keyin email ulandi va ishlayapti, parolni emailga kod bilan tiklash qilindi, AI rasm xatolari tuzatildi. Hozirgi holat uchun [BACKEND_TRELLO_HOLAT_2026-11-18.md](BACKEND_TRELLO_HOLAT_2026-11-18.md) ga qarang. Shu hujjatdagi "AI xatolari QA sinovdan" degan izoh **noto'g'ri** edi: sabab productiondagi OpenAI kalitining muddati tugaganligi (HOLAT hujjatida).

Doska: https://trello.com/b/AzQSD2X3/yolup. O'qildi: **19 ta ochiq karta** (thinking 4, Todo 7, Processing 4, Testing 3, integration 1). **Done** ustunidagi 45 karta
nazorat uchun ko'rildi, ularga tegilmadi. Kartalarda izoh (comment) yo'q, faqat sarlavha, tavsif va 4 ta skrinshot bor.

Har bir karta uchun: backend kodini o'qidim, productionda (APP server) faqat o'qish so'rovlarini bajardim, frontendning `main` shoxi (`0df424b`) bilan solishtirdim.
**Hech narsa o'zgartirilmadi, deploy qilinmadi.** Quyida "tekshirildi" deganim kod yoki serverdan ko'rganim, "taxmin" deganim tekshirilmagan.

## Umumiy ko'rinish

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

## 1. homeworkda image qismini encode/decode qilib AI ga jo'natish

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

## 2. Firebase / bildirishnomalar (karta "firebase dan notification kelishdi togirlash kerak" + integration kartasi "firebase dan olish kere notification uchun")

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

## 3. Parolni o'zgartirish: "email ga code yuboradigan qilsak yaxshi bo'lardi"

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

## 4. "chat vastanavit qlish" (thinking): chatni tiklash, zaxira necha oy

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

## 5. "tolov qism balance di check qib chiqish kerak"

Bu tekshiruv kartasi. To'lov mantig'i ([payments.py](apps/lessons/payments.py), [progress.py](apps/lessons/progress.py)) o'qildi va testlari bor. Topilgan 4 narsa:

1. **Eslatma kechasi ketishi mumkin.** `send_payment_reminders` har soat ishlaydi, soat oralig'i cheklovi yo'q ([payments.py:65](apps/lessons/payments.py:65)). Muddatdan 3/5/7 kun qolgan kunning birinchi ishga tushishi ~00:00–01:00 (Asia/Tashkent) bo'ladi. O'quvchi va ota-ona yarim tunda bildirishnoma oladi (taxmin: kod bo'yicha; productionda vaqtini ko'rmadim).
2. **Eslatma "yuborildi" deb belgilanadi, xabar ketmasa ham.** Log yozuvi xabardan oldin yaratiladi ([payments.py:91](apps/lessons/payments.py:91)); xabar yuborishda xato bo'lsa, qayta urinilmaydi.
3. **"To'lamagan" faqat joriy oy bo'yicha** ([unpaid_counts_for_teacher](apps/lessons/payments.py:47)). Oktabrni to'lamagan, noyabrni to'lagan o'quvchi hech qayerda qarzdor ko'rinmaydi.
4. **Qarz (balans) tushunchasi yo'q.** `CoursePayment` faqat "shu oy to'langan" belgisi; summa ixtiyoriy. Kartaning o'zi ("balance") shu degan bo'lishi mumkin, Done ustunidagi "balance qism" kartasi "kim to'lamagan" ko'rinishini so'ragan, u bajarilgan.

**Qilinadigan ish:** 1–2 ni to'g'rilash (eslatma 09:00–20:00 oralig'ida, yuborilgandan keyin belgilash). 3 uchun savol: o'tgan oylar qarzi ko'rinsinmi (masalan, "2 oy qarz")?

---

## 6. "Homework check da AI ni ko'rib berish kerak"

Alohida karta, lekin mazmuni 1-band bilan bir xil: AI tekshiruvi to'g'ri ishlashi. Productionda AI ishlaydi, hozir tiqilib qolgan topshirish yo'q
(`checking` = 0). Topilgan xatolar 1-bandda. Qo'shimcha: bitta topshirishning `ai_result`i ballsiz (2026-10-15, rasm vazifaga aloqasiz bo'lgani uchun, AI to'g'ri `null` bergan).

---

## 7. "Homework price ni arzon qlish yollarini korish kerak" (thinking)

**Hozir narx o'lchanmaydi.** AI chaqiruvi tokenlari faqat INFO log'ga yoziladi ([llm.py:175](apps/quizzes/llm.py:175)); serverning 14 kunlik log'ida topilmadi,
bazada narx hisobi yo'q. Shuning uchun "qanchaga tushdi" deb aytolmayman.

**Narx omillari (kodda ko'rinadi):** rasm bo'lsa qimmatlashadi (har rasm 2000 px gacha, `detail` ko'rsatilmagan); 6 tagacha rasm; 30 000 belgigacha matn;
xato bo'lsa 3 martagacha qayta urinish ([services.py:46](apps/homework/services.py:46)); `gpt-4o-mini` allaqachon arzon model.

**Taklif (tartib bilan):**
1. Avval o'lchash: har AI chaqiruvining tokenini bazaga yozish (`ai_tokens`, `ai_cost`) va admin uchun xulosa. 1 kun ish.
2. Keyin tejash: rasm tafsilotini `detail: low/auto` bilan sinash (sifat bilan solishtirib), rasmlarni 2000 px dan 1400 px ga tushirish, matnli PDF'ni rasmga aylantirmaslik, qayta urinishlarni kamaytirish.
3. O'qituvchiga `ai_check` ni vazifa bo'yicha o'chirish imkoni allaqachon bor (`ai_check` maydoni).

---

## 8. "Meeting permission" (Processing): backend tayyor

**Karta:** mikrofon/kamera ruxsati bir marta berilsa, keyin yana yopiq bo'lishi va 2-marta yana so'rashi kerak; speaking club'larda hammaga mikrofon ochiq (true/false).

Backend 10-noyabrda bajarilgan (`6aa7b53`): "hammani o'chirish ruxsatni qaytarib oladi", `release-media` (o'quvchi o'zi o'chirsa ruxsat qaytadi), dars bo'yicha `open_mic` / `open_camera` ochiq rejim
([BACKEND_YANGILANISHLAR_2026-11-10.md](BACKEND_YANGILANISHLAR_2026-11-10.md), [FRONTEND_YANGILANISHLAR_2026-11-12_2.md](FRONTEND_YANGILANISHLAR_2026-11-12_2.md)).
Karta o'sha kundan oldin (9-noyabr) yozilgan va Processing'da qolib ketgan. **Qoldi:** frontend QA (3 stsenariy: bir marta ruxsat → o'chirish → qayta so'rash; "hammani o'chirish" → ruxsat qaytadi; ochiq rejim yoqilganda kirgan yangi o'quvchi).

---

## 9. "spam berish adminga borishi kerak ..." (Processing): tayyor

Oqim to'liq: o'quvchi/o'qituvchi shikoyat yuboradi → barcha adminlarga bildirishnoma ([spam.py](apps/chat/spam.py:71)) → admin ro'yxat (`GET /admin/reports/`) → `resolve` / `dismiss` / `unblock`. Frontend ulangan.
**Diqqat:** productionda **1 ta shikoyat "open" holatida turibdi**, hech kim ko'rmagan. Kartani yopishdan oldin admin ekranini ochib shuni ko'rish kerak.

---

## 10. "video qotib qoldi" (Processing)

Skrinshotda o'qituvchi kamerasi ("Siz - ustoz") qotgan, tor (telefon o'lchamidagi) oynada. Mijoz salomatlik hisobotlari (`client-health`, productionda 138 ta) bo'yicha:

- Oxirgi 6 kunda faqat 3 ta past FPS hisoboti (hammasi o'qituvchi): **ekran ulashish** treki 1–2 fps, `quality_limitation = none`, CPU va tarmoq cheklovi yo'q (16 va 10 yadroli kompyuter, "excellent" ulanish).
  Bu **statik ekranda normal** (ekran o'zgarmasa kodlagich 1 fps ga tushadi), lekin tomoshabin uchun "qotgan"dek ko'rinadi.
- Kamera qotishi uchun serverda dalil topilmadi. 12-noyabrdagi tahlil ([FRONTEND_QOTISH_TAHLILI_2026-11-12.md](FRONTEND_QOTISH_TAHLILI_2026-11-12.md)) tavsiyalari frontendda qo'llangan (720p/15 fps, simulcast o'chiq).

**Kerak:** qotish bo'lgan **dars va soat** (men LiveKit logi va hisobotlarni shu soat bo'yicha ko'raman) va qotgan joy: kamerami yoki ekran ulashishmi. Shu bo'lmasa aniq vazifa qilib bo'lmaydi.

---

## 11–13. Testing ustunidagi kartalar

| Karta | Holat |
|---|---|
| **homework** ("natijani ko'rish ishlamayapdi", skrinshotda "Baho yo'q" + "Tekshirilmoqda") | Backend `ai_state` (`checking/unscored/failed/ready`) qo'shgan (`fccbdb7`), frontend natija oynasi uni ishlatadi (frontend: `src/modules/homework/ui/homework-result-dialog.tsx`). Skrinshotdagi holat eski. **QA:** 4 holatni tekshirish |
| **homeworkcheck** ("file yuklash optional bo'lsin") | Backend: fayl majburiy emas, faqat matn javob ham topshiriq (`9278bb5`). Frontend nusxasidagi eski matn yo'q. **QA:** faqat izoh bilan topshirish |
| **Darsga o'qituvchi kirdi va yubordi "hammaga qo'shil"** | Backend: o'qituvchi darsni boshlagach, o'quvchi rejalashtirilgan vaqtdan oldin ham kira oladi (`3cafa7c`, [FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md)). **QA:** o'quvchi "aylanib turgan yopiq dars" ko'rmasligini tekshirish |

---

## 14–16. Frontend kartalari va savol

- **"vazifa berishda" (14):** skrinshot: "Yangi vazifa" oynasida matn maydoni (description) ajralib turmaydi. Faqat frontend (yorliq/sarlavha).
- **"Doska" (15, RedZon):** matn o'lchami va chiziq/yo'naltiruvchi. Backend tayyor: matn o'lchami 12–48, qo'shimcha `w` kengligi, `line`/`rect`/`ellipse`, element tahrirlash (`update_stroke`) ([board/services.py:184](apps/board/services.py:184)). Agar frontend yuborgan qiymat rad etilsa, aniq `400` xabarini bering, men ko'raman.
- **"Qo'lda test yozish imkonini ko'rish kerak ... link berib qo'yila" (16): imkon BOR.**
  - Backend: `POST /api/v1/quizzes/` savollar bilan qo'lda test yaratadi (`quiz.create` ruxsati); `GET /quizzes/template/` shablon.
  - Frontend: guruh ishchi maydonidagi `AddQuizDialog` (frontend: `src/modules/quiz/ui/quiz-create-dialog.tsx`), `src/widgets/group-workspace/group-workspace.tsx` ichida; tahrirlash sahifasi `/teacher/workspace/tests/{id}/edit`.
  - Eslatma: test yaratish hamma o'qituvchi uchun ochiq (admin o'qituvchi bo'yicha boshqaradi, `can_create_tests`).
  Izohdagi "link" so'ralgan: yuqoridagi ro'yxat javob bo'ladi; ekran nomini Trello'ga yozing.

---

## 17–18. Qaror kartalari (sizdan javob kerak)

- **"tech padeshka togirlash kerak boladi" ("xali idea kere"):** "padeshka" nimani bildiradi? Taxminim: texnik yordam (podderzhka). Agar shu bo'lsa, `support/tickets` (murojaat yuborish, javob, yopish) allaqachon bor ([apps/support](apps/support/urls.py)). Nimasini to'g'rilash kerak: ekranmi, javob tezligimi, Telegram'ga xabarmi?
- **"image yuborish qism qande qlamiz":** chatda rasm yuborish **hozir hamma uchun ochiq** (yozish huquqi bor har kim, o'quvchi ham; rasm turlari jpg/png/gif/webp, qo'shimcha cheklov yo'q). E'lon rejimidagi guruhda faqat o'qituvchi yozadi. Variantlar:
  (a) hozirgidek, (b) faqat o'qituvchi, (c) o'qituvchi sozlaydi (guruh bo'yicha "o'quvchilar rasm yuborsin" tugmasi). Tavsiyam (c), chunki spam va nomaqbul rasm xavfi bor, ammo ba'zi guruhlar (masalan matematika) o'quvchi rasmisiz ishlay olmaydi.

---

## Tavsiya etilgan tartib

1. **3-band (parol tiklash):** productionda hozir buzuq. Sizdan: SMTP yoki Eskiz hisobi. Men: email orqali tiklash.
2. **1-band (AI + rasm):** haqiqiy xatolar, sizning ruxsatingiz bilan boshlayman (tahminan 1–1,5 kun, testlar bilan).
3. **2-band (bildirishnoma):** sarlavha/HTML/fon yuborish hozir; Firebase fayli kelgach FCM.
4. **5-band (to'lov):** eslatma vaqti va log tartibi, kichik.
5. **9-band:** admin ochiq shikoyatni ko'rsin (kod emas).
6. Qolganlar sizning javobingizga qarab (4, 7, 17, 18-bandlar, 10-banddagi dars vaqti).

## Tekshirilmagan narsalar

- OpenAI narxi va haqiqiy token sarfi (o'lchanmaydi).
- `kontrakt_kamron.pdf` AI xatosining sababi.
- 4–5-xatolar (DOCX/PDF ichidagi rasm) kod bo'yicha, testsiz. 6-xato (HEIC) ham.
- Backup'ni qayta tiklash hech qachon sinalganmi.
- Frontend QA (8, 11–13-bandlar) men tomondan qilinmadi; faqat kod va hujjat bo'yicha.
- Kartalardagi skrinshotlar faqat 4 tasi ko'rildi (boshqa kartalardagi rasmlar Done ustunida).
