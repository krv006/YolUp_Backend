# Frontend uchun: bugun backendda nima qilindi va frontendda nima qoldi (2026-11-18, yakuniy)

Backend: APP va MEDIA serverlar `17124e3` da ishlayapti (productionda tekshirilgan). Frontend `main` (`33afa65`, bugungi PR #197–#200 gacha) bilan solishtirildi.
Bu hujjat [FRONTEND_VAZIFALAR_2026-11-18.md](FRONTEND_VAZIFALAR_2026-11-18.md) ni **almashtiradi** (u ertalabki holat edi, ichidagi ko'p narsa siz tomondan bugun bajarilgan).

## 1. Siz bugun qilgan va backend shartnomasiga MOS ekani tekshirilgan

Endpoint nomlari va so'rov tanalari backend bilan solishtirildi (kod bo'yicha). Brauzerda o'zim sinab ko'rmadim.

| Siz qilgan | Backend bilan mosligi |
|---|---|
| PR #199: email bilan ro'yxatdan o'tish (`register/options`, `register/email/request`, `verify`, `email_token`), "Login yoki email", parolni emailga kod bilan tiklash, profilda emailni tasdiqlash, "Emailingizni qo'shing" oynasi | Mos. Productionda haqiqiy xat bilan boshidan oxirigacha sinalgan |
| PR #197: uy vazifasi `focus` (exit/return), kanaldan guruhni ajratish, admin "Mijoz salomatligi" paneli | Mos (`{kind: "exit"|"return"}`, `GET monitoring/client-health/`) |
| PR #198: doska yordamchi katagi, PR #200: parolni o'zgartirishda xato maydon ostida | Backend tomonida o'zgarish talab qilinmaydi |

## 2. Frontendda QOLGAN ishlar (aniq, tekshirilgan)

| # | Nima | Qayerda / qanday |
|---|---|---|
| 1 | **iPhone `.heic` / `.heif` ni qabul qilish** | frontend: `src/pages/student/workspace/student-homework-item-page.tsx:39` dagi `ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.docx"` ga `.heic,.heif` qo'shing va "PDF, JPG, PNG, DOCX · 25 MB" matniga HEIC ni yozing. Server uni JPEG'ga o'tkazadi, `file_name` `IMG_1.jpg` bo'lib qaytadi |
| 2 | **`ai_result.skipped_images` ni ko'rsatish** (o'qituvchi natija oynasi) | Son bo'lsa, ajratib ko'rsating (sariq belgi): "N ta sahifa AI ga sig'madi, ball faqat ko'rilganlar bo'yicha". Matni `ai_result.summary.recommendations[0]` da. Qisqa ishlarda maydon kelmaydi. Sabab 4-bo'limda |
| 3 | **`public/sw.js`: push bosilganda to'g'ri sahifani ochish** | Hozir faqat `link_type=lesson` ochiladi (`urlFromLink`), qolganlari bosh sahifaga olib boradi. Backend `link_type` lari: `assignment`, `lesson`, `quiz`, `submission`, `course`, `chat_room`, `certificate`, `exam`, `recording`, `support`, `spam_report`, `teacher`, `link`, `login`. Ilovadagi bildirishnoma ro'yxati ishlatadigan `mapNotificationLink` mantiqini service worker'ga ham qo'llang |
| 4 | **Veb push'ni taklif qilish** | Hozir u faqat sozlamalardagi tugma orqali yoqiladi (`system-settings-page.tsx`), productionda **obunalar nolta**. Birinchi kirishda "Bildirishnomalarni yoqish" taklifini ko'rsating (`enablePush()` tayyor) |
| 5 | Trello: **"vazifa berishda"** | "Yangi vazifa" oynasida vazifa matni (description) maydoni ko'zga tashlanib turishi kerak (kartada skrinshot) |
| 6 | Trello: **"Qolda test yozish imkonini ko'rish"** | Javob: **imkon bor** (backend `POST /quizzes/`, frontendda `AddQuizDialog`, `group-workspace.tsx`). Kartaga shuni yozib yoping |

## 3. Backend tomonida nima o'zgardi (sizga ta'siri)

**Email (productionda ishlayapti, Gmail SMTP)**
- `GET /auth/register/options/` hozir: `{email_required: false, email_available: true, phone_available: false}`.
- `REGISTER_REQUIRES_EMAIL` hozir **o'chiq**. Siz email qadamini tayyorlab bo'ldingiz, shuning uchun backend uni yoqishga tayyor: **ayting, qachon yoqamiz** (yoqilgach `email_required: true`, tasdiqlangan emailsiz ro'yxatdan o'tib bo'lmaydi). Muhlat sanasi (`email_setup_deadline`) ni ham birga belgilaymiz (tavsiya: 14 kun).
- Productionda hozircha **tasdiqlangan emaili bor foydalanuvchi nolta**: bugun ham 2 ta yangi hisob emailsiz ochilgan. Parolni unutgan foydalanuvchi emailni tasdiqlamaguncha tiklay olmaydi.
- **Kirish:** `username` maydoniga login ham, tasdiqlangan email ham yoziladi. Bir email bir nechta akkauntga bog'langan bo'lsa va parol ularning bir nechtasiga mos kelsa: `400`, `error.message` "Bu email bir nechta akkauntga bog'langan. Kirish uchun login (username) ni yozing." Shu xabarni ko'rsating.
- **Xato kirishlar:** bir akkauntga login va email bilan jami **10 ta xato urinishdan** keyin `429` ("Juda ko'p muvaffaqiyatsiz urinish. Bir necha daqiqadan keyin qayta urinib ko'ring."), 10 daqiqa. Login va email urinishlari **bitta hisoblagichda**.
- **Yangi loginda `@` taqiqlanadi** (`400`, `error.details.username`). Eski loginlar o'zgarmaydi.
- **Parolni tiklash:** email topilmasa ham `200 {sent:true}`. Xat **fonda** yuboriladi: SMTP xato bersa ham javob `200`, xato faqat serverda log'ga yoziladi. Shuning uchun matnda: "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi. Kelmasa spam papkasini tekshiring va 2 daqiqadan keyin qayta so'rang."
- Kod: 5 xonali, 120 soniya amal qiladi, qayta yuborish 45 soniyadan keyin (`retry_after`), kuniga 10 marta, 5 xato urinishdan keyin kod bekor. `auth` chegarasi: IP bo'yicha 30 so'rov/daqiqa (`429`).
- Batafsil: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md).

**Backend xabarlari endi ru va en tilida ham** (`Accept-Language`): email, HEIC va login qoidasi xatolari. Oldin faqat o'zbekcha edi.

**Push (veb va mobil)**
- Sarlavha endi "Fokus" emas: tizim xabarlarida ro'yxatdagi sarlavha ("Dars yozuvi tayyor", "Yangi baho", "To'lov"), o'qituvchi xabarida "Ism · Guruh", boshqasida "E'lon"/"YolUp".
- Veb push matnidan HTML teglar olib tashlandi. Push payload maydonlari: `title`, `body`, `kind`, `link_type`, `link_id`.
- Push fonda yuboriladi (APP va MEDIA'da). "Dars yozuvi tayyor" bildirishnomasini MEDIA yuboradi, u ham yangilandi.
- Mobil push (FCM) hali ishlamaydi: Firebase kaliti kutilmoqda.

**To'lov eslatmasi:** faqat 09:00–20:00 (Toshkent) yuboriladi; xabar ketmasa keyingi soatda qayta uriniladi. Frontendga ta'siri yo'q.

## 4. Uy vazifasi: AI va rasmlar (muhim cheklovlar)

- **AI hozir umuman ishlamayapti:** OpenAI kaliti muddati tugagan (kalit yangilanishini kutyapmiz). Yangi topshirish `status: pending_review`, `ai_state: "failed"`, `error: "AI baholay olmadi — o'zingiz baholang."` bilan o'qituvchiga tushadi. Frontend `failed` holatini "AI mavjud emas, qo'lda baholang" deb to'g'ri ko'rsatayotganini tekshiring (QA). Kalit kelgach hammasi o'zi tiklanadi, frontend o'zgarishi shart emas.
- **Rasm/sahifa soni:** AI bitta ishdan **taxminan 3 ta to'liq sahifa/suratni** ko'ra oladi (modelning kontekst chegarasi, har sahifa ~25 500 token). Ortig'i AI ga berilmaydi va `ai_result.skipped_images` + ogohlantirish bo'ladi (yuqorida 2-band). Bu ataylab: aks holda butun so'rov rad etilardi. Ko'p sahifali doskada o'qituvchi qolganini o'zi ko'rishi kerak.
- **Yaxshilanganlar** (frontend o'zgarishi shart emas): telefon surati to'g'ri aylantiriladi (EXIF), hamma yuklangan fayllar (5 tagacha) AI ga boradi, Word/PDF ichidagi rasmlar olinadi, vazifa sharti rasmi AI ga beriladi, iPhone HEIC JPEG'ga o'tkaziladi.
- `ai_result.usage` (token sarfi) o'qituvchi javobida ichki maydon sifatida keladi, ekranda ko'rsatish shart emas.
- Batafsil: [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](FRONTEND_JAVOB_AI_RASM_2026-11-18.md).

## 5. QA: backend tayyor, frontendda tekshirish kerak

| Nima | Qanday tekshirish |
|---|---|
| **Meeting permission** ([FRONTEND_YANGILANISHLAR_2026-11-12_2.md](FRONTEND_YANGILANISHLAR_2026-11-12_2.md)) | (1) bir marta ruxsat → o'quvchi o'chirdi → qayta so'ralishi; (2) "hammani o'chirish" → ruxsat qaytadi; (3) ochiq rejimda kirgan yangi o'quvchi so'rovsiz yoqa oladi |
| **homework natija oynasi** | `ai_state`: `checking / ready / unscored / failed` to'g'ri chiqishi (hozir `failed` ko'p uchraydi) |
| **homeworkcheck** | faqat izoh bilan (fayl yo'q) topshirish ishlashi |
| **Dars yozuvi uzluksizligi** ([FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md](FRONTEND_JAVOB_EKRAN_YOZUV_2026-11-16.md)) | oynalar almashtirilganda, ko'p seans va juda qisqa seansda yozuv uzilmasligi |
| **Darsga kirish** ([FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md](FRONTEND_JAVOB_DARSGA_TAKLIF_2026-11-16.md)) | o'qituvchi boshlagach o'quvchi rejalashtirilgan vaqtdan oldin ham kira olishi |
| **Material sonlari** ([FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md](FRONTEND_JAVOB_MATERIAL_SONLARI_2026-11-17.md)) | guruh papkasida `recording_count`, `board_count` |
| **Spam shikoyatlari (admin)** | ro'yxat, `resolve` / `dismiss` / `unblock`; productionda 1 ta ochiq shikoyat turibdi |
| **Email oqimi (brauzerda)** | ro'yxatdan o'tish → kod → akkaunt; email bilan kirish; tiklash; profilda email tasdiqlash. Backend haqiqiy xat bilan sinalgan, frontend brauzerda sinalmagan |
| **Homework focus** | vazifa sahifasidan chiqib-kirish; o'qituvchida `focus.exits` > 0 bo'lishi |

## 6. Hali backendda kutilayotgan (frontendga bog'liq emas)

Firebase (mobil push), chat xabarini tiklash, rasm yuborish qoidasi ("hamma / faqat o'qituvchi"), "tech padeshka", o'tgan oylar to'lov qarzi: mahsulot qarori yoki tashqi kalit kutyapti. OpenAI kaliti ham shu ro'yxatda. Qaror chiqqach alohida yozaman.

Barcha endpoint yo'llari `/api/v1/...` bilan boshlanadi. Xato javobi: `{success:false, error:{code, message, details}}`.
