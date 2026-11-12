# Frontend uchun: o'quvchi hisobidan rol almashtirish — qoida aniqlashtirildi (2026-11-12, 2-qism)

Oldingi `FRONTEND_ROL_ALMASHTIRISH_2026-11-12.md` dagi "o'quvchi hisobidan har qanday rolga o'tish mumkin" qoidasi **o'zgardi**. Backend production'da (`770ce7f`).

## Yangi qoida

- **O'qituvchi yoki kuzatuvchidan o'quvchi rolini ochib o'tgan** foydalanuvchi (boshqa rol-akkaunti bor) — `POST /auth/switch-role/` ishlaydi: orqaga qaytadi (`teacher`/`parent`) va yangi rol ham ocha oladi.
- **O'zi o'quvchi bo'lib ro'yxatdan o'tgan va boshqa akkaunti yo'q** foydalanuvchi — `switch-role` `403` qaytaradi: "O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi."
- Telefoni yo'q bo'lsa — avvalgidek `400` (`error.details.role`).

## `GET /auth/me/` da yangi qiymat

`role_switch_blocked` endi uch xil:

| qiymat | ma'nosi | nima qilish |
|---|---|---|
| `null` | almashtirish mumkin | "Akkauntni almashtirish" bo'limini ko'rsating, `available_roles` dagi rollarni taklif qiling |
| `"phone_required"` | telefon yo'q | telefon kiritishni taklif qiling |
| `"student_not_allowed"` | **yangi**: o'zi o'quvchi bo'lib kirgan, boshqa akkaunti yo'q | almashtirish bo'limini umuman ko'rsatmang (`available_roles` ham bo'sh) |

## Xatolar jadvaliga qo'shimcha

| holat | status | `error.details` |
|---|---|---|
| o'zi o'quvchi bo'lib kirgan, boshqa akkaunti yo'q | `403` | — |

## Tekshirish ro'yxati

- Oddiy o'quvchi (boshqa akkauntsiz) → `me.role_switch_blocked == "student_not_allowed"`, bo'lim ko'rinmaydi; `switch-role` → `403`.
- O'qituvchi → `{role: "student"}` → `200` → shu o'quvchidan `{role: "teacher"}` → `200`, o'sha o'qituvchi akkauntiga qaytadi.
- O'qituvchidan ochilgan o'quvchi → `{role: "parent"}` → `200`.
