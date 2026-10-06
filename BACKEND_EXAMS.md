# Imtihon (Mock test) — IELTS / SAT / Milliy sertifikat / custom

**Holat:** backend tayyor (1-bosqich). **Base:** `/api/v1/exams/`. Barcha endpointlar JWT bilan.
Eski `/api/v1/quizzes/mock-tests/` **yo'q** — shu yangisi o'rniga. Frontenddagi `mock-test` moduli shu API'ga o'tkazilishi kerak.

## Qisqacha g'oya

- **Shablon** = bo'limlar va tanaffuslar zanjiri + ball hisoblash qoidasi. Tayyor shablonlar: `ielts`, `sat`, `milliy`. O'qituvchi o'z **custom** shablonini ham yaratadi.
- O'qituvchi **o'z guruhida imtihon e'lon qiladi**: shablonni tanlaydi, har bo'limga o'zining e'lon qilingan **testini** biriktiradi, **boshlanish sanasi-vaqtini** belgilaydi.
- Imtihon **sinxron**: hamma uchun bir vaqtda boshlanadi va tugaydi. Bo'lim/tanaffus chegaralari serverda hisoblanadi (`boshlanish + bo'limlar davomiyligi`). Kech kirgan o'quvchi joriy bo'limning *qolgan* vaqtini oladi.
- **Qayta topshirish yo'q.** Yana imtihon kerak bo'lsa o'qituvchi yangisini yaratadi.
- Javoblar **avtosaqlanadi** (`PUT answers/`), sahifa yangilansa `current` hammasini tiklaydi.

Barcha rollarga ruxsat: o'qituvchi — yaratadi/boshqaradi; o'quvchi — topshiradi; ota-ona va admin — ko'radi.

---

## 1. Shablonlar

### `GET /api/v1/exams/templates/`
Tayyor + o'qituvchining custom shablonlari:
```json
[
  {"id": "ielts", "kind": "system", "name": "IELTS", "description": "...",
   "scoring": {"type": "ielts"},
   "items": [
     {"type": "section", "key": "listening", "title": "Listening", "minutes": 30, "questions": 40},
     {"type": "section", "key": "reading",   "title": "Reading",   "minutes": 60, "questions": 40},
     {"type": "section", "key": "writing",   "title": "Writing",   "minutes": 60, "manual": true},
     {"type": "offline", "key": "speaking",  "title": "Speaking",  "manual": true}
   ]},
  {"id": "sat", "kind": "system", "items": [rw_1, rw_2, {"type":"break","minutes":10}, math_1, math_2]},
  {"id": "milliy", "kind": "system", "items": [{"type":"section","key":"main","minutes":150}]},
  {"id": "<uuid>", "kind": "custom", "name": "...", "items": [...], "scoring": {...}}
]
```

**Element turlari (`type`):**
| tur | ma'nosi |
|---|---|
| `section` | vaqtli bo'lim — unga **test biriktiriladi** |
| `break` | tanaffus — taymer ishlaydi, test yo'q |
| `offline` | imtihon vaqtida o'tmaydigan qism (IELTS Speaking) — ballini o'qituvchi keyin qo'lda kiritadi; jadvalga kirmaydi |

`manual: true` — shu bo'limni o'qituvchi qo'lda baholaydi. `questions` — faqat tavsiya (UI uchun).

### `POST /api/v1/exams/templates/` — custom shablon (o'qituvchi)
```json
{
  "name": "1-chorak yakuniy",
  "description": "ixtiyoriy",
  "items": [
    {"type": "section", "key": "algebra",  "title": "Algebra",  "minutes": 40, "weight": 2},
    {"type": "break",   "key": "rest",     "title": "Tanaffus", "minutes": 10},
    {"type": "section", "key": "geometry", "title": "Geometriya", "minutes": 30}
  ],
  "scoring": {"scale": 100, "pass_percent": 60}
}
```
- `key`: lotin kichik harf, raqam, `_` (1-50 belgi), shablon ichida takrorlanmaydi.
- `section` 1–300 daqiqa, `break` 1–60 daqiqa, jami ≤ 720.
- Tanaffus birinchi/oxirgi bo'lolmaydi; kamida bitta `section` kerak.
- `weight` (ixtiyoriy, standart 1) — bo'lim natijasining jami ballga ta'siri.
- `scoring`: `scale` (jami shkala, standart 100) va `pass_percent` (ixtiyoriy). Custom doim "foiz" hisobi.
- Xatolar `error.details.items` ostida keladi.

### `DELETE /api/v1/exams/templates/{id}/` — o'z custom shablonini o'chirish (204). Allaqachon yaratilgan imtihonlarga ta'sir qilmaydi (imtihon shablondan nusxa oladi).

---

## 2. Imtihon yaratish (o'qituvchi)

### `POST /api/v1/exams/`
```json
{
  "course": "<course_uuid>",
  "template": "ielts",              // "ielts" | "sat" | "milliy" | custom shablon uuid
  "title": "IELTS mock #3",
  "starts_at": "2026-10-20T10:00:00+05:00",
  "sections": [
    {"key": "listening", "quiz": "<quiz_uuid>"},
    {"key": "reading",   "quiz": "<quiz_uuid>"},
    {"key": "writing",   "quiz": "<quiz_uuid>"}
  ]
}
```
- `sections` — shablondagi **har `section`** uchun bitta yozuv (`break` va `offline` uchun emas).
- Ixtiyoriy `"minutes"` — shu imtihon uchun bo'lim vaqtini o'zgartirish (Milliy sertifikat: matematika 150, boshqa fanda boshqa).
- Test **e'lon qilingan** (qoralama emas), savoli bor, o'qituvchining o'ziniki bo'lishi va **bir imtihonda faqat bir bo'limga** biriktirilishi kerak.
- `starts_at` kelajakda bo'lishi shart. Kurs shu o'qituvchiniki bo'lishi kerak (aks holda 403).
- Yozilgan o'quvchilarga bildirishnoma boradi (`kind: "exam_scheduled"`, `link_type: "exam"`, `link_id: <exam id>`).
- Javob `201` — imtihon tafsiloti (3-bo'limdagi `GET {id}/` bilan bir xil).

### `PATCH /api/v1/exams/{id}/` — `{"title"?, "starts_at"?}`; `DELETE /api/v1/exams/{id}/` (204)
**Faqat boshlanishdan oldin.** Boshlangan imtihonni o'zgartirish/o'chirish `400`.

> Imtihonga biriktirilgan testning **savollarini o'zgartirish yoki testni o'chirish taqiqlanadi** (`400`); nom/mavzu o'zgartirsa bo'ladi. Testlar sahifasida shu holatni ko'rsating.

---

## 3. Ro'yxat va tafsilot

### `GET /api/v1/exams/` (`?course=<uuid>`) — rolga qarab: o'qituvchi o'zining, o'quvchi yozilgan kurslarniki, ota-ona bolalarinikini, admin hammasini.
```json
[{"id": "...", "course": "...", "course_title": "...", "title": "IELTS mock #3",
  "template_key": "ielts", "engine": "ielts",
  "starts_at": "...", "ends_at": "...", "total_minutes": 150,
  "state": "upcoming", "server_now": "..."}]
```
`state`: `upcoming` | `running` | `finished`.

### `GET /api/v1/exams/{id}/` — bo'limlar jadvali bilan
```json
{ ...yuqoridagi maydonlar...,
  "sections": [
    {"order": 0, "kind": "section", "key": "listening", "group": "", "title": "Listening",
     "minutes": 30, "manual": false,
     "starts_at": "2026-10-20T05:00:00Z", "ends_at": "2026-10-20T05:30:00Z",
     "quiz": "<uuid>"},
    {"order": 3, "kind": "offline", "key": "speaking", "...": "...", "starts_at": null, "ends_at": null}
  ]}
```
`quiz` maydoni faqat o'qituvchi/adminga ko'rinadi.

---

## 4. O'quvchi: imtihonni topshirish

### `GET /api/v1/exams/{id}/current/` — joriy holat (polling + tiklash)
```json
{
  "server_now": "2026-10-20T05:12:03Z",
  "state": "running",              // upcoming | running | finished | submitted
  "starts_at": "...", "ends_at": "...",
  "item": {
    "kind": "section", "key": "reading", "title": "Reading", "group": "", "minutes": 60,
    "starts_at": "...", "ends_at": "2026-10-20T06:30:00Z",
    "groups": [ /* umumiy matn parchasi / audio — BACKEND_QUIZ_GROUPS.md */ ],
    "questions": [ /* quizzes `GET {id}/` dagi o'quvchi ko'rinishi bilan bir xil — is_correct YO'Q, `group` bor */ ],
    "saved": [ {"question": "<id>", "answer": { "selected_option": "<id>" }} ]
  },
  "next": {"kind": "break", "title": "Tanaffus", "starts_at": "...", "ends_at": "..."}
}
```
- `upcoming` / `finished` / `submitted` da `item: null`.
- `item.kind == "break"` da `questions` yo'q — faqat taymer ko'rsating.
- **Taymer:** qolgan vaqt = `item.ends_at − server_now`. Brauzer soatiga ishonmang: `server_now` bilan brauzer vaqti orasidagi farqni (offset) bir marta hisoblab, taymerga qo'llang.
- Bo'lim yoki tanaffus tugaganda keyingisiga o'tish uchun `current` ni qayta chaqiring (yoki `ends_at` da avtomatik). Server vaqtidan tashqari hech narsa hal qilmaydi.
- `saved[].answer` — sahifa yangilanganda tanlangan javoblarni tiklash uchun.
- Savol turlari, `matching`/`ordering` aralashtirilishi — oddiy testdagi bilan bir xil.

### `PUT /api/v1/exams/{id}/answers/` — avtosaqlash
Tanlov o'zgargan sayin (yoki har ~10 soniyada) yuboring. Qayta yuborilsa ustiga yozadi. Format oddiy testdagi `answers` bilan bir xil:
```json
{"answers": [
  {"question": "<id>", "selected_option": "<id>"},
  {"question": "<id>", "value_text": "Toshkent"}
]}
```
Javob: `{"saved": 2, "server_now": "..."}`.
- Faqat **joriy bo'lim** savollari qabul qilinadi (oldingi bo'limga bo'lim tugagandan keyin ~5 soniya ruxsat — oxirgi sekunddagi avtosaqlash uchun). Aks holda `403` ("Bu bo'limning vaqti tugagan").
- Boshlanmagan imtihonga `403`; tugagan yoki o'zi yakunlagan bo'lsa `403`.
- Boshqa imtihonga tegishli savol → `400`.

### `POST /api/v1/exams/{id}/finish/` — muddatidan oldin yakunlash
Qaytib kirib bo'lmaydi (`state: "submitted"`). Natija darhol ko'rinadi. Tasdiqlash dialogi qo'shing.

---

## 5. Natijalar

### `GET /api/v1/exams/{id}/results/`
- **O'qituvchi/admin:** barcha yozilgan o'quvchilar (kelmaganlar `participated: false`), imtihon davomida ham ko'rinadi.
- **O'quvchi:** faqat o'zi. **Ota-ona:** bolalari.
- O'quvchi/ota-ona uchun natija **imtihon tugagach** (yoki o'quvchi o'zi yakunlagach) ochiladi; oldin `{"hidden": true}`.

```json
{ "exam": "...", "engine": "ielts", "state": "finished",
  "results": [{
    "student": {"id": "...", "username": "s1", "name": "Ali Valiyev"},
    "participated": true, "finished_at": null, "engine": "ielts", "approximate": false,
    "sections": [
      {"key": "listening", "title": "Listening", "earned": 32.0, "max": 40.0, "percent": 80.0,
       "score": 7.5, "scale_max": 9, "manual": false},
      {"key": "writing", "manual": true, "score": null, "...": "..."}
    ],
    "total": {"score": 7.5, "max": 9, "label": "Overall band"},   // yoki null
    "pending": ["writing", "speaking"]                              // qo'lda baho kutilmoqda
  }]}
```
- `total: null` va `pending` bo'sh emas bo'lsa — "o'qituvchi bahosi kutilmoqda" deb ko'rsating.
- `approximate: true` bo'lsa natija yonida **"taxminiy"** deb yozing (SAT va Milliy sertifikat).

### `GET /api/v1/exams/{id}/results/{student_id}/` — bitta o'quvchi tafsiloti
O'qituvchiga qo'shimcha `manual_answers: [{section, question, answer}]` — qo'lda baholanadigan bo'limdagi yozma javoblar (IELTS Writing).

### `PUT /api/v1/exams/{id}/results/{student_id}/manual/` — qo'lda ball (o'qituvchi)
```json
{"scores": {"writing": 7.0, "speaking": 6.5}}
```
Faqat `manual: true` bo'limlar. IELTS: 0–9, qadam 0.5. Boshqa shablonlar: 0–100 (foiz). Javob — yangilangan o'quvchi natijasi (yuqoridagi format).

---

## 6. Ball tizimlari

| Shablon | Qanday hisoblanadi |
|---|---|
| **IELTS** | Listening/Reading: to'g'ri javoblar 40 ga keltirilib, rasmiy (Academic) jadvaldan **band** (0–9). Writing/Speaking: o'qituvchi band kiritadi. **Overall** = 4 bandning o'rtachasi, 0.5 gacha yaxlitlanadi (6.25→6.5, 6.75→7.0). Hammasi bo'lmaguncha `total: null`. |
| **SAT** | Reading&Writing va Math har biri **200–800**, jami **400–1600**. College Board'ning **rasmiy o'tkazma jadvali** ishlatiladi (Practice Test #4: natija foizi R&W 66 / Math 54 shkalasiga keltirilib, (past, yuqori) oralig'ining o'rtasi olinadi). **Taxminiy** (`approximate: true`): haqiqiy SAT moslashuvchan va har test shakli o'z jadvaliga ega. `groups: [{key: rw/math, score, range: [past, yuqori]}]` va `total.range` qaytadi — natijani **"1340 (1300–1380)"** ko'rinishida ko'rsatish mumkin. |
| **Milliy sertifikat** | `foiz × 75` (maksimum **75 ball**) va daraja: A+ ≥70, A 65–69.9, B+ 60–64.9, B 55–59.9, C+ 50–54.9, C 46–49.9, undan past — `level: null`. **Taxminiy:** rasmiy ball Rasch modeli bilan hisoblanadi (savol qiyinligi va ishtirokchilarga bog'liq), daraja chegaralari esa rasmiy. |
| **Custom** | Bo'limlarning og'irlikli o'rtacha foizi × `scale`; `pass_percent` bo'lsa `total.passed`. |

> Savol ballari (`points`) testda belgilanadi. Milliy sertifikat matematikasida savol ballari turlicha (1.3 / 2.2 / 3.2) — hozir `points` butun son, shuning uchun foiz hisobi ishlatiladi.

---

## 7. IELTS Writing — AI baholash (o'qituvchi tasdiqlaydi)

**Qanday ishlaydi:** o'quvchi Writing bo'limida insho yozadi (bo'limdagi test savollari `text` turida: **oxirgi savol = Task 2**, qolganlari = Task 1; savol matni — topshiriq sharti). Imtihon tugagach **server o'zi** (har 5 daqiqada) insholarni Gemini bilan IELTS mezonlari bo'yicha baholaydi va **TAKLIF** sifatida saqlaydi. **Ball o'qituvchi tasdiqlamaguncha o'quvchiga ham, umumiy bandga ham o'tmaydi.**

Har task uchun 4 mezon (0–9, 0.5 qadam): `task_response`, `coherence_cohesion`, `lexical_resource`, `grammatical_range_accuracy`. Task bandi — mezonlar o'rtachasi; **Writing bandi = (Task1 + 2×Task2) / 3**, 0.5 gacha yaxlitlanadi (Task 2 ikki baravar). Hisobni server qiladi.

### Natijadagi `ai` bloki (`results/` va `results/{student_id}/` ichida)
```json
"ai": {
  "writing": {
    "status": "proposed",              // running | proposed | approved | failed
    "proposed_band": 6.5,              // faqat o'qituvchiga
    "approved_band": null,
    "error": "",
    "generated_at": "2026-10-20T08:12:00Z",
    "result": {
      "writing_band": 6.5,
      "tasks": [{
        "task_number": 1, "words": 160, "min_words": 150, "band": 6.0,
        "criteria": {"task_response": 6.0, "coherence_cohesion": 6.0,
                     "lexical_resource": 6.0, "grammatical_range_accuracy": 6.0},
        "strengths": ["..."], "weaknesses": ["..."],
        "corrections": [{"original": "He go", "corrected": "He goes", "explanation": "..."}],
        "feedback": "..."
      }],
      "summary": {"overall_comment": "...", "recommendations": ["..."]}
    }
  }
}
```
- **O'qituvchi/admin** hamma holatni va `proposed_band`ni ko'radi.
- **O'quvchi/ota-ona** faqat `status: "approved"` bo'lganda va faqat `result` (izoh, mezonlar) ni ko'radi; oldin `ai: {}`.
- `failed` — `error` da sabab; qayta urinish mumkin.

### `POST /api/v1/exams/{id}/results/{student_id}/ai/` — qo'lda boshlash / qayta urinish (o'qituvchi)
Odatda kerak emas (server o'zi baholaydi); xatodan keyin yoki darhol kerak bo'lsa. `202 {"status": "running"}` — fon oqimida ishlaydi, natijani `results/{student_id}/` dan `ai.writing.status` bilan kuzating (10–60 soniya). Imtihon tugagandan keyin ishlaydi; tasdiqlangan natija qayta baholanmaydi; allaqachon ketayotgan bo'lsa `400`. Xato avtomatik 3 martagacha qayta uriladi.

### `POST /api/v1/exams/{id}/results/{student_id}/ai/approve/` — tasdiqlash (o'qituvchi)
```json
{}                  // AI taklif qilgan band tasdiqlanadi
{"band": 7.0}       // yoki o'qituvchi o'zgartirib tasdiqlaydi (0–9, 0.5 qadam)
```
Band Writing balli sifatida yoziladi (umumiy band hisoblanadi, Speaking kirilmaguncha `pending`), AI izohi o'quvchiga ochiladi. Javob — yangilangan o'quvchi natijasi. Taklif tayyor bo'lmasa `400`.

> **Tavsiya (UI):** o'qituvchi sahifasida o'quvchi inshosi (`manual_answers`), AI mezonlari, tuzatishlar va `[Tasdiqlash] [Bandni o'zgartirish]` tugmalari. O'quvchida tasdiqlangunga qadar "Writing bahosi o'qituvchi tasdig'ini kutmoqda" yozuvi.

> **Eslatma:** Speaking hozircha o'qituvchi qo'lda band kiritadi (`PUT .../manual/`); audio yozuv va AI baholash keyingi bosqich.

---

## 8. Xatolar
Umumiy format: `{"success": false, "error": {"code", "message", "details"}}`.
- `403` — vaqt oynasi tashqarisida javob yuborish, tugagan/boshlanmagan imtihon, rol ruxsati yo'q.
- `404` — imtihon topilmadi **yoki sizniki emas** (boshqa guruh).
- `400` — maydon xatolari (`details.items`, `details.sections`, `details.starts_at`, `details.scores`).

## 9. Hali yo'q (keyingi bosqichlar)
- ~~IELTS Listening audiosi va Reading/SAT matn parchasi~~ — **tayyor**, `BACKEND_QUIZ_GROUPS.md` ga qarang (`current/` javobidagi `item.groups`).
- ~~IELTS Writing AI~~ — **tayyor** (7-bo'lim). IELTS **Speaking**ni AI bilan baholash (o'quvchi ovoz yozuvi yuklashi kerak) — hozir o'qituvchi qo'lda band qo'yadi.
- Tasodifiy variantlar (har o'quvchiga boshqa savollar), imtihon eslatmalari (boshlanishidan oldin).
- IELTS Speaking'ni alohida vaqtda topshirish (hozir `offline` qism sifatida faqat ball kiritiladi).
