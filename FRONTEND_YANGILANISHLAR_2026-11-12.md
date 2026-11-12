# Frontend uchun: 12-noyabr, uchinchi backend vazifalari javobi

Hammasi backendda tayyor va sinalgan.

---

## 1. Bazadan berish: har guruh uchun aniq o'quvchilar ro'yxati (`targets`)

`POST /homework/assignments/{id}/assign/` endi `targets` qabul qiladi:

```json
{
  "targets": [
    { "course_id": "<guruh>", "student_ids": ["<id>", "<id>"] },
    { "course_id": "<boshqa guruh>" }
  ],
  "due_at": "2026-11-20T23:59:00+05:00",
  "allow_late": true,
  "announce_in_chat": true
}
```

- `student_ids` yo'q yoki bo'sh — **butun guruhga** (chat kartasi bilan, `announce_in_chat` bo'yicha).
- `student_ids` bor — faqat shu guruh o'quvchilariga: nusxaning `assigned_students` i `_publish`dan **oldin** o'rnatiladi, bildirishnoma faqat ularga boradi,
  chat kartasi yuborilmaydi (chat butun guruhga ko'rinadi). Tanlanmaganlar vazifani ko'rmaydi (`404`).
- Guruhning **hamma** o'quvchisi tanlangan bo'lsa, backend uni butun guruh deb hisoblaydi (karta ham yuboriladi).
- Bir o'quvchi bir nechta guruhda (guruh + club) bo'lsa ham muammo yo'q: `course_id` aniq ko'rsatiladi.
- Xatolar (`400`): `error.details.targets["<indeks>"]` ichida — `student_ids` (o'quvchi shu guruhda emas), `course_id` (yo'q yoki ikki marta kiritilgan).
  Guruh o'qituvchiniki bo'lmasa `403`. Xato bo'lsa hech narsa yaratilmaydi.
- `targets` berilsa eski `course_ids` / `student_ids` e'tiborga olinmaydi. Eski shakl avvalgidek ishlayapti (o'zgarmagan).
- Javob avvalgidek: `201 {count, assignments: [...]}`.

Frontend: "Bazadan berish" oynasida har tanlangan guruh uchun `{course_id, student_ids}` yuboring (hammasi belgilangan bo'lsa `student_ids`ni tashlab yuborsangiz ham bo'ladi).
"Butun guruhga bering, keyin cheklang" xabari endi kerak emas.

## 2. Test ro'yxatida urinishlar va boshlangan seans

`GET /quizzes/` (o'quvchi) har elementida yangi maydonlar:

| maydon | ma'nosi |
|---|---|
| `attempts_used` | topshirilgan urinishlar + vaqti tugab sarflanganlari |
| `attempts_left` | `null` — cheklov yo'q; `0` — urinishlar tugagan |
| `session_ends_at` | boshlangan va hali tugamagan vaqtli seansning `ends_at`; yo'q bo'lsa `null` |

"Davom etish · 12:34 qoldi" ni `session_ends_at` dan ko'rsating. O'qituvchi/admin ro'yxatida bu uch maydon `null`.
Guruhsiz (o'quvchiga ko'rinmaydigan) testlarda ham `null`.

## 3. Boshlashdan oldin savollar soni

`GET /quizzes/{id}/` (o'quvchi) javobiga `question_count` qo'shildi: shu urinishda tushadigan savollar soni (`questions_per_attempt` hisobga olingan).
`needs_start: true` bo'lib `questions` bo'sh kelganda ham, urinishlar tugaganda ham (`attempts_left: 0`) to'g'ri keladi. Boshlash ekranida "Savollar: N ta" ni shundan oling.

## 4. Diqqat tekshiruvi: socket push production'da — tasdiqlandi

Production'da (APP, `cron` konteyneri) tekshirildi:
- `cron` `35deda2` dan keyingi kod bilan ishlayapti, `JOBS` da `push_attention` bor.
- `cron` va `ws` konteynerlarida `REDIS_URL` berilgan, kanal qatlami `RedisChannelLayer` (InMemory emas).
- Oxirgi 24 soatda `attention push failed` log'da yo'q.

Hodisa keladimi — jonli darsda o'quvchi doska socketida `{"type": "attention", "check": {...}}` ko'rinishini tekshirish kifoya.

## 5. Bazadagi vazifaning nusxalari

`GET /homework/assignments/{id}/` (bazadagi vazifa, muallif) javobiga `copies` qo'shildi (yangisi birinchi):

```json
"copies_count": 2,
"copies": [
  { "id": "...", "course_id": "...", "course_title": "...", "due_at": "...", "status": "active",
    "submissions_count": 3, "student_ids": null, "created_at": "..." }
]
```

`student_ids` — `null` bo'lsa butun guruh, ro'yxat bo'lsa faqat shu o'quvchilarga berilgan. `id` bo'yicha shu guruh nusxasiga (`GET /homework/assignments/{id}/`) o'tish mumkin.
