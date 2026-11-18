# Email: ro'yxatdan o'tish, email bilan kirish, parolni emailga kod bilan tiklash (2026-11-18)

Trello: "change password qism togirlash kerak" (email ga code yuboradigan qilib). Login va parol QOLADI; email qo'shiladi.
Hamma yo'llar `/api/v1/auth/...`. **Production holati (2026-11-18, tekshirilgan):** email xizmati **ulangan va ishlayapti** (Gmail SMTP). Ro'yxatdan o'tish, email bilan kirish va parolni tiklash productionda haqiqiy xat bilan boshidan oxirigacha sinab ko'rildi. SMS xizmati hali ulanmagan: telefon orqali kod yuboradigan endpointlar `503` beradi.
Majburiylik bayrog'i (`email_required`) ham hozir **o'chiq**; avval frontend tayyor bo'ladi, keyin yoqamiz.

Kod hamma joyda bir xil: 5 xonali, **120 soniya** amal qiladi, qayta yuborish **45 soniyadan** keyin, kuniga 10 marta, 5 ta xato urinishdan keyin kod bekor bo'ladi.
Yuborish javobi: `200 {"sent": true, "expires_in": 120, "retry_after": 45}`. Xatolar: `429` (tez-tez), `400` ("Kod noto'g'ri yoki muddati o'tgan"), `503` (email ulanmagan), `502` (yuborib bo'lmadi).

## 1. Ro'yxatdan o'tish oynasi

Avval `GET /auth/register/options/` (login shart emas) → `{"email_required": false, "email_available": false, "phone_available": false}`.
- `email_required: true` bo'lsa, email qadami **majburiy**. `false` bo'lsa, ixtiyoriy (yoki yashirin), eskicha ishlaydi.
- `email_available: false` bo'lsa kod yuborib bo'lmaydi (503); bu holatda majburiy qilmang, sahifada xabar ko'rsating.

Qadamlar (telefon oqimidagi kabi):
1. `POST /auth/register/email/request/` `{ "email": "ali@example.com" }` → kod emailga ketadi.
2. `POST /auth/register/email/verify/` `{ "email": "...", "code": "12345" }` → `{ "email_token": "...", "expires_in": 1800 }`.
3. `POST /auth/register/` oddiy tanaga **`email` va `email_token`** qo'shing. Token 30 daqiqa amal qiladi, **bir marta** ishlaydi va aynan shu emailga bog'liq.
   Xato: `400`, maydon xatosi `error.details.email_token` (token yo'q, eskirgan yoki boshqa emailga).
   Email katta-kichik harfdan qat'i nazar kichik harfga o'tkaziladi.

Boshqa o'zgarishlar:
- **Yangi loginda `@` taqiqlanadi** (`400`, `error.details.username`), chunki kirishda `@` li yozuv email deb qaraladi. Eski loginlar o'zgarmaydi.
- Ota-ona yoki o'qituvchi yaratgan bola akkaunti (`POST /auth/children/`) emailsiz yaratiladi va hech qachon email so'ralmaydi.

## 2. Kirish: login YOKI email

`POST /auth/login/` o'sha `{ "username": "...", "password": "..." }`. `username` maydoniga **login ham, tasdiqlangan email ham** yozish mumkin.
Faqat yorliqni "Login yoki email" ga o'zgartiring. Endpoint, javob va xato shakli o'zgarmaydi.
- Noto'g'ri email yoki parol: odatiy `401` (email bor-yo'qligi oshkor bo'lmaydi).
- Bir email bir nechta akkauntga (bitta odamning rol-akkauntlari) bog'langan bo'lsa va parol ularning bir nechtasiga mos kelsa:
  `400` "Bu email bir nechta akkauntga bog'langan. Kirish uchun login (username) ni yozing." Shu xabarni ko'rsating.
- Tasdiqlanmagan email bilan kirib bo'lmaydi (faqat login bilan).

## 3. Parolni tiklash

Oqim o'sha 3 qadam, endi `phone` o'rniga `email` ham mumkin (ikkalasidan bittasini yuboring):
1. `POST /auth/password/reset/request/` `{ "email": "ali@example.com" }` (yoki `{ "phone": "..." }`).
2. `POST /auth/password/reset/verify/` `{ "email": "...", "code": "12345" }` → `{ "reset_token": "...", "expires_in": 600 }`.
3. `POST /auth/password/reset/confirm/` `{ "reset_token": "...", "password": "..." }` → `{ "ok": true }`.

Farqlar:
- **Xat fonda yuboriladi:** parolni tiklash so'rovi SMTP javobini kutmaydi (shuning uchun mavjud va mavjud bo'lmagan email bir xil tez javob oladi). Xat yuborilmasa ham javob `200`, xato faqat serverda log'ga yoziladi. Kod kelmasa foydalanuvchiga "spam papkasini tekshiring, 2 daqiqadan keyin qayta so'rang" deb ayting.
- **Email topilmasa ham 1-qadam `200 {"sent": true, ...}` qaytaradi** (xavfsizlik: manzil bazada bor-yo'qligi oshkor bo'lmasin). Shuning uchun matn: "Agar bu email ro'yxatdan o'tgan bo'lsa, kod yuborildi."
  Telefon bilan tiklashda esa oldingidek raqam topilmasa `404`.
- Faqat **tasdiqlangan** email bo'yicha tiklanadi.
- Parol yangilangach shu emaildagi hamma akkauntning paroli o'zgaradi va hamma seans yopiladi (telefon bilan tiklashdagidek).

## 4. Mavjud foydalanuvchi: emailni qo'shish va tasdiqlash

`GET /auth/me/` da 2 ta yangi maydon:
- `email_setup_required` (bool): tasdiqlangan emaili yo'q va talab yoqilgan (bola akkauntlari uchun hech qachon `true` emas).
- `email_setup_deadline` (`"2026-12-02"` yoki `null`): shu sanagacha eslatma, **sanadan keyin majburiy**. `null` bo'lsa faqat eslatma.

`email_setup_required: true` bo'lsa, kirgandan keyin "Emailingizni qo'shing va tasdiqlang" oynasini ko'rsating (muhlatgacha "keyinroq" tugmasi bilan).
- `POST /auth/me/email/request/` `{ "email": "..." }` → YANGI manzilga kod ketadi (tasdiqlanguncha eski email o'zgarmaydi).
- `POST /auth/me/email/confirm/` `{ "email": "...", "code": "12345" }` → yangilangan profil (`GET /auth/me/` shaklida), `email_verified: true`.

Profilni `PATCH /auth/me/` bilan emailni to'g'ridan-to'g'ri o'zgartirsangiz, `email_verified` yana `false` bo'ladi (oldingidek). Tasdiqlash uchun yuqoridagi ikki endpointdan foydalaning.

## QA

- Ro'yxatdan o'tish: kod → token → akkaunt; xato kod; eskirgan/qayta ishlatilgan token.
- Email bilan kirish (katta-kichik harf farqsiz); noto'g'ri parol; bir nechta akkauntli email.
- Tiklash: email → kod → yangi parol → yangi parol bilan kirish; mavjud bo'lmagan email ham xuddi shunday xabar ko'rsatadi.
- Eski foydalanuvchi: eslatma oynasi, email qo'shish, tasdiqlangach oyna yo'qoladi.
