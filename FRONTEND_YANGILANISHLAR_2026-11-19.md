# Frontend va mobil jamoa uchun: 2026-11-19 yangilanishlari

Hammasi productionda (APP va MEDIA) ishlayapti. Backend testlari (2075 ta) o'tgan, productionda haqiqiy tekshiruvlar qilingan.

## 1. Email endi ro'yxatdan o'tishda MAJBURIY (faqat `.env` o'zgardi, kod yangi emas)

Batafsil oqim: [FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md](FRONTEND_EMAIL_KIRISH_VA_TIKLASH_2026-11-18.md). Bu yerda faqat endi nima o'zgargani.

| Nima | Hozirgi holat (productionda tekshirilgan) |
|---|---|
| `GET /api/v1/auth/register/options/` | `{"email_required": true, "email_available": true, "phone_available": false}` |
| `POST /api/v1/auth/register/` emailsiz (`email_token` yo'q) | `400`, `error.details.email_token`: "Email tasdiqlanishi shart: avval emailga kelgan kodni tasdiqlang." Akkaunt yaratilmaydi |
| `GET /api/v1/auth/me/` emailsiz mavjud foydalanuvchi | `email_setup_required: true`, `email_setup_deadline: "2026-12-03"` |
| `GET /api/v1/auth/me/` `email_exempt` foydalanuvchi (ota-ona/o'qituvchi yaratgan bola) | `email_setup_required: false`, `email_setup_deadline: null` |

Frontendga ish:
- Ro'yxatdan o'tishda email qadami albatta bo'lsin (`register/email/request/` → `register/email/verify/` → `email_token` ni `register/` ga yuborish). `options` dagi `email_required` ga qarab ko'rsatish yoki yashirish mumkin.
- Mavjud foydalanuvchilar uchun: `email_setup_required: true` bo'lsa eslatma ko'rsatiladi. **2026-12-03** dan keyin email qo'shishni majburiy qilish frontendda (backend bloklamaydi). Email qo'shish: `me/email/request/` va `me/email/confirm/`.
- Hozir productionda 28 foydalanuvchidan faqat 2 tasida tasdiqlangan email bor, ya'ni deyarli hamma eslatma ko'radi. Kutilgan holat.
- Bolalar akkauntlari uchun eslatma chiqmasligi kerak: `email_setup_required` ga ishoning, o'zingiz rolga qarab taxmin qilmang. Eski bola akkauntlari (telefonsiz o'quvchilar) adminda `email_exempt` qilib belgilanadi. Kerak bo'lsa ro'yxatini ayting.

## 2. Mobil push (FCM) backendda ulandi

Firebase loyihasi: `yolup-28bb7`. APP va MEDIA serverlarida kalit qo'yilgan (MEDIA'da ham, chunki "yozuv tayyor" xabarini o'sha server yaratadi).

Mobil jamoaga:
- Android uchun `google-services.json` (package `uz.yolup.edu`) mobil ilovaga qo'yiladi, backendga kerak emas.
- Ilova har ochilganda FCM tokenini yuboradi: `POST /api/v1/notifications/push/device/`
  ```json
  {"token": "<FCM registration token>", "platform": "android" | "ios", "device_id": "<barqaror qurilma id>", "app_version": "1.0.0"}
  ```
  Javob `201 {"ok": true}`. Chiqishda `DELETE` shu manzilga `{"device_id": "..."}`.
- **Muhim, iOS:** productionda hozir faqat 1 ta qurilma ro'yxatda (`ios`) va uning tokeni haqiqiy **FCM** tokeni emas (Google rad etdi: "not a valid FCM registration token"). iOS'da xom APNs tokenini emas, Firebase SDK bergan FCM tokenini yuboring. iOS push uchun Firebase konsolida APNs kaliti ham yuklangan bo'lishi kerak (buni mobil jamoa/Firebase egasi qiladi).
- Xabar maydonlari (`data`): `notification_id`, `link_type`, `link_id`, `kind`. Sarlavha ("YolUp" yoki mazmunga mos) va matn `notification` ichida.
- **Sinash:** to'g'ri token yuborilgach, `POST /api/v1/notifications/push/test/` o'ziga sinov xabarini yuboradi (token → baza → FCM → telefon). Natijani backendga xabar bering.

Hali tasdiqlanmagan: haqiqiy telefonga xabar yetib borishi (to'g'ri FCM tokeni kerak).

## 3. Parolni o'zgartirish (avvalgi javobning yakuni)

`sync_provisioned_passwords --apply` productionda ishga tushirildi: avtomatik ochilgan 4 ta rol akkaunti tuzatildi, takror ishga tushirish hech narsani o'zgartirmadi. Yangi avtomatik ochiladigan akkauntlar ham manba parolini oladi. O'qituvchi "O'quvchi"/"Kuzatuvchi" akkauntida "Parolni o'zgartirish" ni o'qituvchi paroli bilan ocha oladi. `uz` da parol xabarlari o'zbekcha. Frontendda o'zgarish shart emas. Batafsil: [FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18.md](FRONTEND_JAVOB_PAROL_OZGARTIRISH_2026-11-18.md).

## 4. AI qayta ishlayapti (yangi OpenAI kaliti, 2026-11-19)

AI baholash, AI test yaratish, yozma imtihon AI va Speaking (ovoz → matn, matn → ovoz) yana ishlaydi. Haqiqiy tekshiruv: burilgan rasmli uy vazifasi to'g'ri baholandi (xato javob topildi, xulosa o'zbekcha), Speaking audio aylanishi ishladi. Frontendda o'zgarish shart emas. Oldingi ogohlantirishlar (HEIC, `ai_result.skipped_images`) o'z kuchida.

## 5. Hali ochiq

- **Haqiqiy mobil push:** to'g'ri FCM tokeni kerak (2-bo'lim).
- HEIC va 3+ sahifali hujjat haqiqiy OpenAI bilan hali sinalmagan (testlarda tekshirilgan). QA'da shularni ham sinab ko'ring.
