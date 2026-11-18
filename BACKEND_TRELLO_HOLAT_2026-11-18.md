# Trello "Yolup": nima qilindi, nima tekshirildi, nima qoldi (2026-11-18, kechqurun)

Bu [BACKEND_TRELLO_VAZIFALAR_2026-11-18.md](BACKEND_TRELLO_VAZIFALAR_2026-11-18.md) ning davomi: o'sha hujjatdagi 19 ta ochiq karta bo'yicha holat.

**Muhim:** Trello'dan kartalarni bugun ertalab o'qiganman. Hozir qayta o'qimoqchi bo'lsam, ichki brauzerda Trello seansi yana tugagan (HTTP 401), shuning uchun
ertalabdan keyin qo'shilgan yoki ko'chirilgan kartalarni ko'rmadim. Ular bo'lsa ayting yoki Trello'ga kirib bering, shunda solishtiraman.

Belgilar: **DEPLOY** = serverda ishlayapti; **KODDA** = yozildi va testlandi, serverga hali chiqarilmagan; **KUTYAPMAN** = sizdan narsa kerak.

## Qisqa javob

| Savolingiz | Javob |
|---|---|
| Hammasini qildingmi? | **Yo'q, 19 tadan hammasini emas.** 3 tasi serverda ishlayapti, 4 tasi kodda tayyor (deploy kutadi), 5 tasi avvaldan tayyor edi (faqat QA), 3 tasi faqat frontend ishi, 4 tasi sizdan narsa kutadi. Har birining sababi quyida. |
| To'g'ri qildingmi? | Qilganlarimni testlar va serverda tekshirdim. Tekshirib bo'lmaganlarini alohida yozdim. |
| Qolganini ham qildingmi? | Qila oladiganlarimni qildim. Qolganlari uchun nima kerakligini aniq yozdim. |

## 1. Bajarilgan, DEPLOY qilingan, tekshirilgan

| Karta | Nima qilindi | Qanday tekshirildi |
|---|---|---|
| **homeworkda image ... AI ga jo'natish** + **Homework check da AI ni ko'rib berish** | 6 ta xato to'g'rilandi: EXIF aylantirish, hamma fayllar, token byudjetiga sig'adigan sahifalar (hozirgi modelda ~3 ta, 9.6-band), Word/PDF ichidagi rasmlar, vazifa sharti rasmi, iPhone HEIC. Commit `d467691`. [FRONTEND_JAVOB_AI_RASM_2026-11-18.md](FRONTEND_JAVOB_AI_RASM_2026-11-18.md) | 24 ta yangi test; serverdagi konteynerda HEIC→JPEG haqiqiy ishladi. **Haqiqiy OpenAI bilan tekshirib BO'LMADI: productiondagi kalit muddati tugagan** (9-bo'lim) |
| **change password** (email ga kod) | Ro'yxatdan o'tishda tasdiqlangan email, email bilan kirish, parolni emailga kod bilan tiklash, profilda email qo'shish. Commit `199de62`, `94bd14a`. [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md) | 47 ta yangi test; **haqiqiy Gmail orqali** serverdan kod ketdi (`sent: true`); netcup "Mail block" o'chirildi, 25/465 porti himoyalandi |
| **Zaxira: tiklashni sinash** (chat vastanavit kartasining 2-qismi) | Oxirgi kunlik nusxa vaqtinchalik bazaga **tiklandi**: qator sonlari jonli bazaga mos (21 foydalanuvchi, 140→142 xabar yangi yozuvlar sababli) | Serverda haqiqiy `pg_restore`, vaqtinchalik baza o'chirildi |

**Emailda hali ochiq qolgani (aniq):**
- Productionda **bironta ham tasdiqlangan email yo'q**, ya'ni hozir hech kim emailni tiklash orqali parolini almashtira olmaydi, avval emailini qo'shib tasdiqlashi kerak. Buning uchun frontendda "email qo'shish" oynasi kerak (yo'riqnomada bor).
- `REGISTER_REQUIRES_EMAIL` **o'chiq**. Frontend email qadamini qo'shmaguncha yoqsam, ro'yxatdan o'tish buziladi.
- Gmail ilova paroli suhbatda ochiq bo'lgani uchun almashtirilishi kerak (siz yangisini bering).

## 2. KODDA tayyor, deploy qilinmagan (sizning "ha" ingizni kutyapti)

| Karta | Nima o'zgardi | Testlar |
|---|---|---|
| **firebase dan notification kelishdi to'g'irlash** (Firebase'siz qismi) | (a) Push sarlavhasi endi "Fokus" emas: tizim xabarlarida ro'yxatdagi sarlavha ("Dars yozuvi tayyor", "Yangi baho"), qolganida "YolUp"; (b) veb push matnidagi HTML teglar olib tashlandi; (c) veb va mobil push **fonda** yuboriladi (sekin qurilma xabar yuborishni kutdirmasin). [apps/notifications/services.py](apps/notifications/services.py) | 9 ta yangi test, mavjud push testlari o'tdi |
| **tolov qism balance check** | (a) To'lov eslatmasi faqat **09:00–20:00** (Toshkent) yuboriladi, oldin kun boshlanishi bilan, ~00:00 da ketishi mumkin edi; (b) xabar yuborilmasa "yuborildi" belgisi qolmaydi va keyingi soatda qayta uriniladi; o'quvchiga ketgan bo'lsa, ota-onaga ketmaganda o'quvchiga qayta yuborilmaydi. [apps/lessons/payments.py](apps/lessons/payments.py) | 4 ta yangi test; mavjud testlardan biri (`test_management_command_runs`) real soatga bog'liq edi, tuzatildi |
| **Homework price arzon qilish** (1-qadam: o'lchash) | Har AI baholashning token sarfi `ai_result.usage` ga yoziladi (qayta urinishlar ham hisoblanadi). Hisobot: `python manage.py homework_ai_usage --days 30`. Narx faqat tarifni bersangiz hisoblanadi (`--price-in`, `--price-out`), uni o'zim uydirmayman. [apps/homework/management/commands/homework_ai_usage.py](apps/homework/management/commands/homework_ai_usage.py) | 8 ta yangi test |
| **chat vastanavit: zaxira necha oy** | Zaxira saqlash muddati: kunlik 14 kun (oldingidek) + **haftalik ~6 oy** + **oylik ~13 oy**. Nusxa ~2 MB, jami ~0,5 GB. [deploy/new/backup.sh](deploy/new/backup.sh), [SERVER_SOZLASH.md](SERVER_SOZLASH.md) | skript sintaksisi tekshirildi; serverda deploydan keyin birinchi yakshanba/1-sanada ishga tushadi |

**Eslatma:** AI sarfi (token) yozilishi faqat deploydan **keyingi** tekshiruvlar uchun ishlaydi; eskilarida sarf yo'q, narxni ularga qaytarib hisoblab bo'lmaydi.

## 3. Avvaldan tayyor edi (backend), faqat QA qoladi

| Karta | Holat |
|---|---|
| **Meeting permission** | `6aa7b53` (10-noyabr): hammani o'chirish ruxsatni qaytaradi, `release-media`, `open_mic/open_camera`. Frontend QA kerak |
| **spam berish adminga** | Oqim to'liq. Productionda **1 ta shikoyat "open" holatida**, admin ko'rishi kerak |
| **homework** (natijani ko'rish), **homeworkcheck** (fayl ixtiyoriy), **Darsga o'qituvchi kirdi** | Backend tayyor (`fccbdb7`, `9278bb5`, `3cafa7c`). Frontend QA kerak |

Bu kartalarning backend qismi uchun butun test to'plami natijasi: **butun backend test to'plami: 2060 ta test, hammasi o'tdi** (9.6–9.8 tuzatishlarigacha bo'lgan hamma o'zgarishlar bilan, 736 soniyada)

## 4. KUTYAPMAN: sizdan nima kerak

| Karta | Nima kerak | Nega men qila olmayman |
|---|---|---|
| **firebase dan olish kere** (integration) + mobil push | Firebase **service account `.json`** (Project settings → Service accounts → Generate new private key) va **Project ID**. Faylni chatga emas, fayl yo'lini yozing. iPhone uchun APNs kaliti Firebase'ga yuklanishi kerak | Kalitsiz FCM ulanmaydi; skrinshotdagi `google-services.json` serverga kerak emas |
| **chat vastanavit qlish** | Qaysi "tiklash"? (a) o'chirilgan xabarni qaytarish, (b) falokatdan keyin butun bazani tiklash. (b) tayyor (yuqorida). (a) uchun taklif: 30 kun ichida o'qituvchi/admin qaytara oladi | Mazmuni noaniq, taxmin bilan funksiya yozmadim |
| **image yuborish qism qande qlamiz** | Variant: (a) hamma, (b) faqat o'qituvchi, (c) guruh bo'yicha o'qituvchi sozlaydi. Tavsiya (c) | Mahsulot qarori |
| **tech padeshka togirlash** | "padeshka" nima? Tavsif: "xali idea kere" | Spetsifikatsiya yo'q |
| **video qotib qoldi** | Qotish bo'lgan **dars va soat**, qotgan joy: kamerami yoki ekran ulashishmi | Serverda sabab ko'rinmadi: CPU/tarmoq cheklovi yo'q, FPS 1–2 faqat ekran ulashishda (statik ekranda normal) |
| **tolov qism: o'tgan oylar qarzi** | O'tgan oylar qarzi ko'rinsinmi ("2 oy qarz")? Hozir faqat joriy oy | Mahsulot qarori |
| **change password** (email majburiy qilish) | Frontend email qadamini qo'shgach: `REGISTER_REQUIRES_EMAIL=1` va muhlat sanasi (tavsiya: 14 kun) | Frontendsiz yoqsam ro'yxatdan o'tish buziladi |

## 5. Frontend kartalari (backendda qiladigan ish yo'q)

- **vazifa berishda**: "description" yorlig'i ko'zga ko'rinsin (skrinshot bor).
- **Doska** (RedZon): matn o'lchami va chiziq yo'naltiruvchisi. Backend tayyor (matn 12–48, line/rect/ellipse, tahrirlash). Frontend yuborgan qiymat rad etilsa, `400` xabarini bering.
- **Qo'lda test yozish imkonini ko'rish**: **imkon bor** (`POST /quizzes/`, frontendda `AddQuizDialog`), javobi [BACKEND_TRELLO_VAZIFALAR_2026-11-18.md](BACKEND_TRELLO_VAZIFALAR_2026-11-18.md) 16-bandda.
- Frontendga qo'shimcha ishlar (yo'riqnomalarda): veb push'ni birinchi kirishda taklif qilish va `sw.js` da chat/vazifa/to'lov bosilganda to'g'ri sahifani ochish (hozir faqat dars), HEIC `accept`, AI natijasida `skipped_images`, email qadamlari.

## 6. Eng muhim xavflar (aniq)

1. **Production hozir:** parolni tiklash faqat **emaili tasdiqlanganlar** uchun ishlaydi, va hozir tasdiqlangan email nolta. Ya'ni parolini unutgan foydalanuvchi hozircha baribir tiklay olmaydi, frontend email oynasi chiqmaguncha.
2. **Firebase'siz** mobil push ishlamaydi (iOS qurilma token yuborgan, lekin xabar bormaydi).
3. **Veb push**: obunalar nolta, chunki frontend uni faqat yashirin sozlamada taklif qiladi, deploy bunga ta'sir qilmaydi.

## 7. Tekshirilmagan (halol ro'yxat)

- Haqiqiy OpenAI bilan AI baholash (rasmlar, narx), faqat soxta javob bilan.
- To'lov eslatmasining haqiqiy productiondagi vaqti (kun soati), faqat testda.
- Veb/mobil push haqiqiy qurilmada (testda soxta yuborish).
- Frontend QA (meeting, homework, homeworkcheck, dars kirishi): faqat kod va testlar bo'yicha.
- Trello'ning ertalabdan keyingi o'zgarishlari (seans tugagan).

## 8. Qayta tekshiruv (so'rovingizdan keyin) va to'g'rilangan kamchiliklar

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

## 9. Ikkinchi qayta tekshiruv: eng muhim topilma va tuzatishlar

### 9.1. Productiondagi OpenAI kaliti MUDDATI TUGAGAN: hamma AI ishlamayapti

Productionda haqiqiy AI baholashni sinab ko'rmoqchi bo'lib, OpenAI'ga so'rov yubordim: **HTTP 401, `expired_secret_key`: "Your API key has expired. Create a new API key to continue."** Kalit mavjud (`sk-proj...`), lekin amal qilmaydi. Bu `/models` ro'yxati, model va chat so'rovi uchun ham bir xil.

- **Nima ishlamaydi:** uy vazifasini AI bilan baholash, AI test yaratish, imtihon Writing AI, Speaking ovozni matnga o'girish, matnni ovozga aylantirish (hammasi shu kalitdan).
- **Qachondan:** oxirgi muvaffaqiyatli AI natijalari: uy vazifasi 2026-10-17, AI test yaratish 2026-10-21. Keyin xatolar: 10, 13 va 17-noyabr. Aniq sana noma'lum (shu oraliqda).
- **Foydalanuvchiga ta'siri:** tizim yiqilmaydi. Topshirish qabul qilinadi va "AI baholay olmadi — o'zingiz baholang" belgisi bilan o'qituvchiga tushadi. Ya'ni o'qituvchi hamma narsani qo'lda baholayapti.
- **Men avval xato qilgan joyim:** 5 ta "AI baholay olmadi" xatosini "QA sinov vazifalari" deb izohlagan edim. Bu **noto'g'ri** edi, sabab kalit.
- **Natijada:** men yozgan AI rasm tuzatishlari (EXIF, HEIC, ko'p sahifa, Word/PDF ichidagi rasmlar) **haqiqiy OpenAI bilan hech qachon tekshirilmagan**, faqat soxta javob bilan (testlar o'tdi). Yangi kalit kelganda sinab ko'raman.
- **Sizdan kerak:** platform.openai.com → API keys → yangi kalit yarating (iloji bo'lsa muddatsiz) va oylik byudjet cheklovi qo'ying. Kalitni chatga yozishingiz mumkin, men serverdagi `.env` ga (`OPENAI_API_KEY`) yozaman va darhol haqiqiy sinovni o'tkazaman: yonbosh telefon surati va HEIC bilan.

### 9.2. Zaxira nusxa bilan birga `.env` nusxasi MEDIA serverga ko'chib ketgan edi: o'chirildi

SMTP sozlamasini yozganimda serverdagi `.env` ning zaxira nusxasini `/var/backups/edu/` ga qo'ygan edim. Tungi `rsync` (va bugun 14:01 da men qo'lda ishga tushirgan zaxira) uni MEDIA serverning `/var/backups/edu-app/` ga ham ko'chirgan. Ikkala nusxani ham o'chirdim (ikkala serverda `env` fayli 0 ta). U yerda **faqat bir necha daqiqa** turdi va ikkala server ham sizniki; yangi sir (Gmail paroli) o'sha nusxada yo'q edi (u eski `.env` edi). Baribir tuzatildi.

### 9.3. Zaxira skripti haqiqiy ishga tushirildi

`backup.sh` ni serverda to'liq ishga tushirdim (MEDIA nusxasi bilan): kunlik nusxa yaratildi va MEDIA'ga ko'chirildi, haftalik nusxa (`db_weekly_2026-11-15.dump`) ikkala serverda bor. Oylik nusxa 1-dekabrda avtomatik yaratiladi (bu hali kuzatilmagan).

### 9.4. Email bor-yo'qligi javob vaqtidan bilinib qolishi mumkin edi: tuzatildi (deploy kutadi)

Men "email bazada bor-yo'qligi oshkor bo'lmaydi" degan edim, lekin faqat javob **matni** bo'yicha to'g'ri edi. Vaqt bo'yicha farq bor edi: (1) parolni tiklashda mavjud email uchun SMTP kutilardi (~1 soniya), noma'lum uchun yo'q; (2) email bilan kirishda mavjud email uchun 2 ta parol hisoblash, noma'lum uchun 1 ta. Ikkalasi tenglashtirildi: xat fonda yuboriladi, noma'lum emailda soxta parol hisoblash bajariladi. 4 ta yangi test (parol hisoblash soni barcha holatda 2). **Serverda hali yo'q.**

### 9.5. Boshqa aniqlangan faktlar
- Productionda **hech bir kursda `payment_day` belgilanmagan** (0 ta) va to'lov eslatmalari hech qachon yuborilmagan (0 ta yozuv). Ya'ni to'lov eslatmasi funksiyasi hozir ishlatilmayapti, mening tuzatishim productionda sinab bo'lmaydi, faqat testda.
- Bugun ikki yangi foydalanuvchi emailsiz ro'yxatdan o'tgan (13:40 o'qituvchi, 13:53 ota-ona).
- Eski hujjatlardagi (`FRONTEND_EMAIL_...`, `FRONTEND_ULANMAGAN_...`, `BACKEND_TRELLO_VAZIFALAR_...`) "email ulanmagan" degan gaplar eskirgan edi, tuzatildi.

### 9.6. Rasm tuzatishimdagi XATO topildi va to'g'rilandi: "10 sahifagacha" haqiqatda ishlamasdi

"10 sahifagacha AI ga boradi" degan gapim noto'g'ri edi. OpenAI hujjatiga ko'ra `gpt-4o-mini` uchun har bir rasm **2833 + 5667 x (512 px bo'laklar soni)** token oladi; bitta to'liq sahifa (768x1024 yoki 1536x1536) **25 501 token**. Modelning kontekst oynasi 128 000 token. Demak **4 tadan ko'p sahifa bitta so'rovga sig'maydi** (5 ta = 127 505 token, matnsiz). Eski kod (6 ta) ham, mening 10 talik chegaram ham shu sababli ko'p sahifali ishda so'rov rad etilishiga olib kelardi.
- **Tuzatish:** rasmlar endi token byudjetiga qarab tanlanadi (`HOMEWORK_AI_IMAGE_TOKEN_BUDGET`, standart 80 000: bu ~3 ta to'liq sahifa). Sig'maganlari AI ga berilmaydi va natijada `skipped_images` + ogohlantirish bo'ladi. Vazifa sharti rasmi ham byudjetdan joy oladi. Formula OpenAI'ning o'z misoli bilan tekshirildi (1536x1536 → 25 501).
- **Oqibat:** hozirgi modelda AI bitta ishdan taxminan **3 ta sahifa/surat** ko'radi. Ko'p sahifali doska yoki ko'p suratli ishlarda o'qituvchi qolganini o'zi ko'rishi shart.
- **`gpt-4o-mini` OpenAI sahifasida "Deprecated" (eskirgan) deb belgilangan** (o'chirish sanasi o'sha sahifada ko'rsatilmagan). Rasm bilan ishlashda u eng qimmat model (har sahifa ~25 500 token). Yangi kalit kelgach boshqa, rasm uchun arzonroq va yangiroq modelni (masalan gpt-4.1-mini) solishtirib ko'rishni tavsiya qilaman: `OPENAI_MODEL` `.env` da sozlanadi. Hozir buni **sinab ko'rmadim** (kalit yo'q), shuning uchun faqat tavsiya.

### 9.7. Kirishdagi urinishlar hisoblagichi: email "ikkinchi imkoniyat" edi: to'g'rilandi

Xato kirishlar (10 ta, keyin 429) `(IP, kiritilgan matn)` bo'yicha sanalardi. Email bilan kirish qo'shilgach, bitta akkauntga login bilan 10 va email bilan 10 ta urinish mumkin bo'lib qolgan edi. Endi tasdiqlangan email bitta akkauntga tegishli bo'lsa, urinishlar o'sha akkauntning loginiga yig'iladi (katta-kichik harf variantlari ham). 4 ta test.

### 9.8. MEDIA serverda eski kod ishlayapti: bildirishnoma tuzatishi to'liq emas

MEDIA server hali `c76a991` da (APP'da `a3fd185` va undan keyingilar). "Dars yozuvi tayyor" bildirishnomasi **MEDIA'dagi `rec`/transcoder** jarayonidan yuboriladi, shuning uchun u hali eski kod bilan ketadi: push sarlavhasi "Fokus", matnda HTML, push so'rov ichida sinxron. Bildirishnoma tuzatishi MEDIA ham yangilangandan keyingina to'liq bo'ladi. (Yangilash: faqat `rec`, `rec-cron`, `transcoder` qayta quriladi; LiveKit va Caddy tegilmaydi. Jonli dars va "converting" yozuv bo'lmaganda.)
