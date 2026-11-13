# Frontend uchun: akkauntlarni bog'lash xavfsizligi (`BACKEND_VAZIFALAR_2026-11-12.md` javobi)

Tanlangan variant: **A (aniq bog'lanish)**. Backend production'ga chiqariladi, shundan keyin frontend parol so'rash oynasini qo'shadi.
Oldingi hujjatlar (`FRONTEND_ROL_ALMASHTIRISH_2026-11-12*.md`) o'z kuchida, faqat quyidagi o'zgarishlar bor.

## Nima o'zgardi

- Akkauntlar endi **telefon raqami bir xil bo'lgani uchun bog'lanmaydi**. Bog'lanish faqat ikki yo'l bilan paydo bo'ladi:
  1. `POST /auth/switch-role/` bilan yangi rol-akkaunt **ochilganda** (u joriy sessiyadan ochilgani uchun shu odamniki) — avtomatik bog'lanadi;
  2. boshqa akkauntning **parolini kiritib** `POST /auth/account-links/` orqali.
- `GET /auth/me/` → `linked_accounts` faqat aniq bog'langanlarni qaytaradi. Profilda telefon raqami o'zgarsa, bog'lanish o'zgarmaydi.
- `POST /auth/switch/{id}/` faqat bog'langan akkauntga ishlaydi (aks holda `403`, avvalgidek).
- Shu rol shu raqamda bor, lekin **bog'lanmagan** bo'lsa, `switch-role` endi o'tkazmaydi — `409` qaytaradi (pastga qarang).
- Production'dagi mavjud ma'lumotlar: avval `switch-role` bilan ochilgan juftliklar avtomatik bog'langan deb ko'chiriladi. Faqat "raqami bir xil" bo'lgan eski juftliklar
  bog'lanmagan bo'ladi — ular keyingi o'tishda parol kiritadi. Shuning uchun almashtirish oynasida **bog'lanmagan akkaunt chiqmay qolishi** normal.

## 1. `POST /auth/account-links/` — parol bilan bog'lash

So'rov (kirgan foydalanuvchi tokeni bilan):

```json
{ "username": "ustoz_ali", "password": "u akkauntning paroli" }
```

Muvaffaqiyatli — `201`:

```json
{
  "account": { "id": "...", "username": "ustoz_ali", "role": "teacher" },
  "linked_accounts": [ { "id": "...", "username": "ustoz_ali", "role": "teacher", ... } ]
}
```

Shundan keyin ikkalasi bir-biriga parolsiz o'tadi (`POST /auth/switch/{account.id}/`). Joriy sessiya o'zgarmaydi, yangi token berilmaydi.
Bog'lash ikki tomonlama va **o'tuvchan**: A–B va B–C bog'langan bo'lsa, A, B, C hammasi bitta guruhda.
Bu endpoint **har qanday rol uchun** ishlaydi, o'quvchi uchun ham (`role_switch_blocked == "student_not_allowed"` bo'lsa ham) — o'quvchi boshqa akkauntini parol bilan bog'lashi mumkin.

### Xatolar

| holat | status | `error.code` | `error.details` | nima qilish |
|---|---|---|---|---|
| login yoki parol noto'g'ri (yoki bunday login yo'q — bir xil javob) | `400` | `invalid` | `password`: "Login yoki parol noto'g'ri." | maydonda xato ko'rsating |
| o'z akkauntingiz | `400` | `invalid` | `username` | |
| shu rolda akkaunt allaqachon bog'langan | `400` | `invalid` | `username`: "Bu rolda akkaunt allaqachon bog'langan." | |
| allaqachon bog'langan | `400` | `invalid` | `username` | oddiy `switch` qiling |
| admin/boshqa tizim akkaunti | `400` | `invalid` | `username` | |
| u akkauntda ikki bosqichli himoya yoqilgan | `400` | `two_factor_enabled` | — | "Bu akkauntni bog'lab bo'lmaydi (2FA yoqilgan)" |
| ketma-ket 5 marta noto'g'ri parol | `429` | `throttled` | `retry_after` soniyada (15 daqiqa) | kutishni ko'rsating |
| umumiy chastota cheklovi (`auth` scope) | `429` | | | |
| token yo'q/eskirgan | `401` | | | |

## 2. `POST /auth/switch-role/` — yangi `409` holat

Shu raqamda o'sha rolda akkaunt bor, lekin joriy akkauntga bog'lanmagan bo'lsa:

```json
{
  "success": false,
  "error": {
    "code": "account_exists",
    "message": "Bu rolda akkaunt bor. Bog'lash uchun uning parolini kiriting.",
    "details": { "detail": "...", "account": { "id": "...", "username": "ustoz_ali", "role": "teacher" } }
  }
}
```

Frontend: parol so'rash oynasini oching ("`ustoz_ali` (O'qituvchi) akkauntining parolini kiriting"). Parol kiritilsa — `POST /auth/account-links/ {username: details.account.username, password}`,
`201` kelgach — **`switch-role` ni qayta yuboring** (endi bog'langan, shu akkauntga o'tadi, `200` + tokenlar).

Qolgan xatolar (telefon yo'q `400`, noto'g'ri rol `400`, o'zi o'quvchi bo'lib kirgan `403`, faolsizlantirilgan `403`) o'zgarmagan.

## 3. Almashtirish oynasi (tavsiya)

- Ro'yxat: `me.linked_accounts` — bosilsa `POST /auth/switch/{id}/` (parolsiz, avvalgidek).
- "Boshqa akkauntni bog'lash" tugmasi: `username` + `password` oynasi → `POST /auth/account-links/`. Oddiy (boshqa akkauntsiz) o'quvchida ham ko'rsating.
- Hali ochilmagan rollar: `me.available_roles` → `switch-role`. `409 account_exists` kelsa yuqoridagi parol oynasi.

## Tekshirish ro'yxati

- Bir xil raqam bilan alohida ro'yxatdan o'tgan ikki akkaunt: `me.linked_accounts` bo'sh; `switch/{id}/` → `403`; `switch-role` → `409 account_exists`.
- Parolni to'g'ri kiritib bog'lash → `201`, keyin ikkala tomondan parolsiz o'tiladi.
- Noto'g'ri parol → `400`; 5 marta ketma-ket → `429`.
- O'qituvchidan `switch-role` bilan ochilgan kuzatuvchi/o'quvchi akkaunti: ikkala tomonga parolsiz o'tiladi (oqim buzilmagan).
- Profilda raqamni boshqa akkaunt raqamiga o'zgartirish `linked_accounts` ga ta'sir qilmaydi.
