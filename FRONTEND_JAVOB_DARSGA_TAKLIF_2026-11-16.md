# Backend javobi: darsga taklif bildirishnomasida havola qo'shildi (Trello 60)

## Nima o'zgardi

O'qituvchi `POST /api/v1/live/invite/` orqali o'quvchilarni chaqirganda ketadigan bildirishnomada endi quyidagilar bor:

| maydon | qiymat |
|---|---|
| `kind` | `lesson_invite` |
| `link_type` | `lesson` |
| `link_id` | dars id'si (UUID matn) |
| `title` | `Darsga taklif` |

`link` (tuzilgan ko'rinish) ham `{ "kind": "lesson", "id": "<dars id>" }` bo'lib keladi. `category` o'zgarmadi (`announcement`).

Frontendda o'zgarish kerak emas: `link_type == 'lesson'` bildirishnoma `/live/{id}` sahifasini ochadi.

## Eslatma

- Bildirishnomani bosgan o'quvchi darsga faqat dars `live` bo'lsa kira oladi. Taklif o'qituvchi darsni boshlagandan keyin ketadi, shuning uchun odatda dars `live` bo'ladi.
- Push bildirishnomada ham xuddi shu `link_type` / `link_id` boradi.

## Tekshirish

1. O'qituvchi darsni vaqtidan oldin boshlaydi va "Hammani chaqirish" ni bosadi.
2. O'quvchiga "Darsga taklif" sarlavhali bildirishnoma keladi.
3. Bosilganda `/live/{lesson_id}` ochiladi va o'quvchi darsga kiradi.
