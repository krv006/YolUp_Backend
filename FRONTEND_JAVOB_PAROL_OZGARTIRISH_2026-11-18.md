# Javob: "Parolni o'zgartirish" (BACKEND_PAROL_OZGARTIRISH.md bo'yicha), 2026-11-18

Hammasi backend kodi va productiondagi ma'lumotlar bo'yicha tekshirildi. Frontendda **hech narsa o'zgartirish shart emas**.

## 1. Avtomatik ochilgan rol akkauntida joriy parol noma'lum: tasdiqlandi va tuzatildi

**Tasdiqlandi:** `switch_or_provision_role` yangi akkauntga `secrets.token_urlsafe(32)` qo'yardi. Productionda shunday akkauntlar **4 ta**
(2 ta o'quvchi, 2 ta kuzatuvchi; hammasi o'qituvchi akkauntidan ochilgan, parollari hech qachon o'zgartirilmagan). Parolsiz (`unusable`) akkaunt yo'q.

**Tanlangan yo'l:** `password_set` belgisi **qo'shilmaydi**, "Parol o'rnatish" oynasi ham kerak emas. Frontend o'zgarmaydi: `current_password` majburiy qoladi.

| Holat | Nima qilindi |
|---|---|
| **Yangi** avtomatik ochiladigan akkauntlar | Parol xeshi manba akkauntdan nusxalanadi: bitta odamning rol-akkauntlarida parol bir xil. Yangi akkauntga login va manba paroli bilan to'g'ridan-to'g'ri ham kirsa bo'ladi |
| **Mavjud 4 ta** akkaunt | Alohida buyruq: `manage.py sync_provisioned_passwords` (standart: faqat ko'rsatadi, `--apply` bilan yozadi). Faqat shu shartlarda nusxalaydi: akkaunt audit'da avtomatik ochilgan deb yozilgan; parol hech qachon o'zgartirilmagan (foydalanuvchi o'zi qo'ygan parol bosilmaydi); manba va nishon hozir ham bitta bog'langan guruhda va faol. Takror ishga tushirish xavfsiz |

**Eslatma:** bu o'zgarish serverga chiqarilgach ishlaydi; mavjud 4 akkaunt uchun buyruqni men ishga tushiraman (xabar beraman). Shundan keyin
o'qituvchi "O'quvchi" yoki "Kuzatuvchi" akkauntida "Parolni o'zgartirish" ni **o'qituvchi paroli bilan** ocha oladi. Manba akkaunt paroli o'zgarmaydi,
va keyin bitta akkauntda parol o'zgartirilsa, boshqa rol-akkauntlarniki o'zgarmaydi (parolni tiklash esa shu telefon/emaildagi hammasini o'zgartiradi, oldingidek).

## 2. Parol qoidalari: backend o'zgartirilmadi (qaror)

Backend raqam va katta harfni talab qilmaydi, frontend talab qiladi. **Backendni qattiqlashtirmadim**, sabab: mobil ilova va allaqachon ro'yxatdan
o'tgan foydalanuvchilar mavjud; yangi talab birdaniga ularning ro'yxatdan o'tishi va parolni tiklashini `400` ga aylantirishi mumkin. Frontendning qattiqroq
qoidasi to'g'ri va yetarli (backend undan yumshoqroq, ziddiyat yo'q). Agar backendda ham majburiy bo'lishini xohlasangiz, ayting: ro'yxatdan o'tish,
tiklash va o'zgartirishga birdan qo'shiladi, mobil ilova jamoasi bilan kelishib.

## 3. Validator xabarlari tili: tasdiqlandi va tuzatildi

**Tasdiqlandi:** `uz` da `new_password` xatolari inglizcha chiqardi (Django'ning `uz` katalogida bu satrlar bo'sh), `ru` da ruscha edi. Haqiqiy tekshirilgan.

**Tuzatildi:** `uz` tarjimasi qo'shildi. Endi `Accept-Language: uz` (yoki til yuborilmasa, standart) bilan:

| Qoida | uz | ru / en |
|---|---|---|
| juda qisqa | Parol juda qisqa: kamida 8 ta belgi bo'lsin. | o'zgarmadi |
| juda oddiy | Bu parol juda oddiy, boshqasini tanlang. | o'zgarmadi |
| faqat raqam | Parol faqat raqamlardan iborat bo'lmasin. | o'zgarmadi |
| loginga o'xshash | Parol quyidagi ma'lumotga juda o'xshash: login. | o'zgarmadi |

Xatolar oldingidek `error.details.new_password` ichida (ro'yxat).

## Tekshirish (QA)
1. O'qituvchi birinchi marta "O'quvchi" roliga o'tadi (yangi akkaunt ochiladi), o'quvchi akkauntida "Parolni o'zgartirish": o'qituvchi paroli bilan ishlashi kerak.
2. `Accept-Language: uz` bilan `new_password: "12345678"` → o'zbekcha ikki xabar.
