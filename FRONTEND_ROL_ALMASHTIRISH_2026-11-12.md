# Frontend uchun: o'quvchi hisobidan rolga o'tish (YANGILANDI: faqat boshqa akkaunti bor o'quvchi uchun) (`BACKEND_ROL_ALMASHTIRISH.md` javobi)

Backend tayyor va production'ga chiqarilgan (`77217a2`). Frontend'dan boshqa o'zgarish talab qilinmaydi: o'quvchi profilidagi
"Akkauntni almashtirish" oynasidagi **O'qituvchi** va **Kuzatuvchi** qatorlari endi xatosiz ishlaydi.

## Yangilanish (2-versiya)

Avvalgi versiyada har qanday o'quvchi rol ocha olardi. Endi **farqlanadi**:

- **O'qituvchi/kuzatuvchidan o'quvchi rolini ochib o'tgan** foydalanuvchi (boshqa rol-akkaunti bor) — orqaga (`teacher`/`parent`) qaytishi va yangi rol ochishi mumkin.
- **O'zi o'quvchi bo'lib ro'yxatdan o'tgan va boshqa akkaunti yo'q** foydalanuvchi — `switch-role` `403` qaytaradi ("O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi").
- `GET /auth/me/` da: bunday o'quvchida `available_roles: []` va `role_switch_blocked: "student_not_allowed"`. Shunda "Akkauntni almashtirish" bo'limini umuman ko'rsatmang.
  Boshqa qiymatlar: `null` (almashtirish mumkin) | `"phone_required"` (telefon yo'q).

## Nima o'zgardi

`POST /api/v1/auth/switch-role/ {role}` o'quvchi hisobidan ham ishlaydi (avval `403`: "O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi").
Boshqa tekshiruvlar avvalgidek.

## Xatti-harakat

- `role`: `teacher` | `parent` | `student`.
- Shu telefon raqamida o'sha rol **allaqachon bor bo'lsa** — shunga o'tiladi (ikkinchisi yaratilmaydi).
- **Yo'q bo'lsa** — ro'yxatdan o'tishsiz avtomatik ochiladi (parolsiz, bir martalik tasodifiy parol bilan; foydalanuvchi keyin "Parolni tiklash"
  orqali o'rnatishi mumkin) va darhol shunga o'tiladi. Ism-familiya va telefon joriy akkauntdan ko'chiriladi.
- Yangi ochilgan o'qituvchi darhol ishlay oladi (`is_approved` odatiy `true`, 2026-10-05 qarori) — "tasdiqlanmagan o'qituvchi" holati chiqmaydi.

## Javob

`200`:

```json
{ "access": "...", "refresh": "...", "user": { "id": "...", "role": "teacher", "linked_accounts": [ { "id": "...", "role": "student", ... } ], ... } }
```

Yangi `access`/`refresh` ni saqlang (joriy sessiya yangi akkauntniki bo'ladi). `user.linked_accounts` da boshqa rollar (o'quvchi ham) ko'rinadi, shu bilan
orqaga qaytish mumkin: `POST /api/v1/auth/switch/{linked_account_id}/` (avvalgidek, parolsiz).

## Xatolar

| holat | status | `error.details` |
|---|---|---|
| telefoni yo'q akkaunt | `400` | `role`: "Rol almashtirish uchun avval telefon raqamingizni kiriting." — profilda telefon kiritishni taklif qiling |
| noto'g'ri rol (`teacher`/`parent`/`student` dan boshqa) | `400` | `role` |
| allaqachon shu roldasiz | `400` | `role`: "Siz allaqachon shu roldasiz." |
| shu rol-akkaunt faolsizlantirilgan | `403` | — |
| o'zi o'quvchi bo'lib kirgan, boshqa akkaunti yo'q | `403` | — (`me.role_switch_blocked == "student_not_allowed"`) |
| token yo'q/eskirgan | `401` | — |

Chastota cheklovi: `auth` scope (login bilan bir xil) — tez-tez bosilsa `429`.

## Tekshirish ro'yxati

- Telefoni bor o'qituvchi → `{role: "student"}` → `200`, yangi tokenlar, `linked_accounts` da `teacher` bor.
- O'qituvchidan ochilgan o'quvchi → `{role: "parent"}` → `200`.
- Shu raqamda o'qituvchi allaqachon bor → shunga o'tadi, `user.id` mavjud akkauntniki.
- Telefonsiz o'quvchi → `400`, `error.details.role`.
- Oddiy (boshqa akkauntsiz) o'quvchi → `403`; o'qituvchidan o'quvchiga o'tgan foydalanuvchi → o'qituvchiga qaytadi (`200`).
