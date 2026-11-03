# O'qituvchi uchun o'quvchilar progressi (2026-11-03)

O'qituvchi bitta guruh (kurs) ichida har o'quvchi uchun ko'radi: **to'lov**, **davomat**, **uy vazifalari**, **qachon qo'shilgani**.
Hammasi faqat shu kursning o'qituvchisi uchun (boshqa o'qituvchi/o'quvchi/ota-ona → 403/404).

> **Muhim:** platformada to'lov tizimi (Click/Payme) yo'q. Shuning uchun to'lovni **o'qituvchi o'zi belgilaydi**
> ("shu oy uchun to'ladi"). Belgi bor = to'lagan, yo'q = to'lamagan. Kurs narxi (`monthly_fee`) avvalgidek kurs sozlamasida.

## 1. Guruh bo'yicha ro'yxat

`GET /api/v1/courses/{course_id}/progress/?range=all|30d|month&month=YYYY-MM`

- `range` — davomat davri (standart `all`; `attendance/summary/` bilan bir xil).
- `month` — qaysi oyning to'lovi ko'rsatiladi (standart — joriy oy).

```json
{
  "course_id": "…", "course_title": "Algebra", "monthly_fee": 450000,
  "range": "all", "month": "2026-11", "lesson_count": 12,
  "summary": {
    "students": 18, "paid": 11, "unpaid": 7,
    "attendance_percent": 84, "focus_percent": 91, "homework_completion_percent": 76
  },
  "students": [
    {
      "id": "…", "name": "Aziza Rahimova", "username": "aziza",
      "joined_at": "2026-08-01T09:12:00Z",
      "last_visit_at": "2026-11-02T14:00:00Z",
      "attendance": { "percent": 92, "attended": 11, "total": 12, "focus_percent": 95 },
      "homework": {
        "total": 9, "submitted": 8, "checked": 6, "awaiting_review": 2, "resubmit_requested": 0,
        "missed": 1, "completion_percent": 89, "average": 8.4, "scale": 10
      },
      "payment": {
        "period": "2026-11", "status": "paid", "amount": 450000, "paid_at": "2026-11-01T10:00:00Z", "note": "Naqd",
        "unpaid_months": 0
      }
    }
  ]
}
```

Ta'riflar:
- `percent` (davomat) / `focus_percent` — kursning "Davomat" sahifasidagi (`attendance/summary/`) raqamlar bilan **aynan bir xil**. Qatnashmagan bo'lsa `focus_percent: null`.
- `joined_at` — o'quvchi guruhga qo'shilgan (tasdiqlangan) vaqt. `last_visit_at` — oxirgi marta darsga kirgan vaqt (`null` = hech kirmagan).
- `homework` — faqat **faol** vazifalar (qoralama kirmaydi), o'quvchi qo'shilgandan keyingilari (+ u topshirgan eskilari).
  - `submitted` — topshirgan (AI tekshirayotgan va o'qituvchi tasdiqlashini kutayotgani ham kiradi).
  - `checked` — o'qituvchi tasdiqlagan; `awaiting_review` — tekshiruv/tasdiq kutilmoqda.
  - `resubmit_requested` — "qayta topshiring" deyilgan (topshirilgan hisoblanmaydi).
  - `missed` — muddati o'tgan va topshirilmagan.
  - `average` — tasdiqlanganlarning o'rtacha bahosi, **10 ballik** (`null` = hali baho yo'q). `completion_percent` — `submitted / total` (`null` = vazifa yo'q).
- `payment.status` — `paid` | `unpaid` (tanlangan `month` uchun). `unpaid_months` — o'quvchi qo'shilgan oydan joriy oygacha to'lov belgisi **yo'q** oylar soni ("3 oy qarzdor").
  `amount` — belgilangan summa (berilmagan bo'lsa kurs narxi); `unpaid` bo'lsa `amount/paid_at: null`, `note: ""`.
  Kurs narxi (`monthly_fee`) `null` bo'lsa — to'lov bo'limini yashirish mumkin.

Tartib: ism bo'yicha (A→Z). Filtr/qidiruvni frontend qiladi (bitta guruhda ~50 tagacha o'quvchi).

## 2. Bitta o'quvchi (batafsil)

`GET /api/v1/courses/{course_id}/students/{student_id}/progress/?range=all|30d|month`

Javob — yuqoridagi qatorning hammasi (`name`, `joined_at`, `attendance`, `homework`, `payment`, …) **va** qo'shimcha ro'yxatlar:

```json
{
  "lessons": [
    { "lesson_id": "…", "title": "Tenglamalar", "starts_at": "…", "attended": true,
      "joined_at": "…", "left_at": "…", "minutes": 52, "late_reason": "", "teacher_note": "" }
  ],
  "assignments": [
    { "assignment_id": "…", "title": "Essay", "due_at": "…", "state": "done",
      "submitted_at": "…", "submission_id": "…", "score": 8.5 }
  ],
  "payments": [
    { "period": "2026-11", "status": "paid", "amount": 450000, "paid_at": "…", "note": "Naqd" },
    { "period": "2026-10", "status": "unpaid", "amount": null, "paid_at": null, "note": "" }
  ]
}
```

- `lessons` — tugagan darslar, yangisi birinchi. `attended: false` = qatnashmagan.
- `assignments[].state`: `done` (tasdiqlangan, `score` 10 ballik) · `awaiting_review` · `resubmit` · `missed` (muddati o'tgan, topshirilmagan) · `not_submitted` (muddati hali o'tmagan).
  `submission_id` orqali mavjud `/homework/submissions/{id}/` ochiladi.
- `payments` — o'quvchi qo'shilgan oydan joriy oygacha, **eng yangi oy birinchi**.

## 3. To'lovni belgilash

`PUT /api/v1/courses/{course_id}/students/{student_id}/payments/{YYYY-MM}/`  `{ "amount": 450000, "note": "Naqd" }`
- ikkala maydon ixtiyoriy; `amount` berilmasa kurs narxi ko'rsatiladi. Qayta chaqirish yozuvni yangilaydi (xato emas).
- Javob: `{ "period", "status": "paid", "amount", "paid_at", "note" }`.

`DELETE /api/v1/courses/{course_id}/students/{student_id}/payments/{YYYY-MM}/` — belgini olib tashlaydi (`204`; belgi bo'lmasa ham `204`).

Xatolar (standart format): noto'g'ri oy (`2026-13`, 2020 dan oldin yoki 12 oydan keyin) → 400; summa son emas yoki manfiy → 400;
o'quvchi shu kursda tasdiqlanmagan → 404; kurs o'qituvchisi emas → 403/404.

## 4. Frontend topgan xatolar — tuzatildi

| Xato | Endi |
|---|---|
| `analytics/child/<id>/rank/?course=abc`, `remind-child {student: "abc"}`, `auth/logins/?student=abc` — UUID bo'lmasa 500 | **400** (`error.details.course` / `student`), standart format |
| `auth/logins/` sahifalashda `next`/`previous` `from`, `to`, `device` filtrlarini yo'qotardi | Barcha filtrlar saqlanadi |
| `remind-child` da `student` yo'q bo'lsa 400 standart formatda emas edi | `{"success": false, "error": {"code": "invalid", "message": "...", "details": {"student": [...]}}}` |

## Migratsiya

Yangi jadval: `lessons_coursepayment` (migratsiya `0029_course_payment`). Deploy'da APP serverdagi `web` avtomatik migratsiya qiladi.
