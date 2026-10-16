# IELTS: Writing (insho), AI baholash, savol-savol tahlil — backend kontrakti

Hammasi mavjud `quizzes` va `exams` API'lariga qo'shimcha; eski mijozlar buzilmaydi.

## 1. Yangi savol turi: `essay` (Writing)

Yaratish (`POST /api/v1/quizzes/` yoki `PATCH` ichidagi `questions[]`):
```json
{ "type": "essay", "text": "Some people think... Discuss both views.", "points": 9, "min_words": 250 }
```
- To'g'ri javob (`accepted_answers`, `options`) **kerak emas**. `min_words` — 0 dan 2000 gacha (0 — cheklov yo'q).
- O'quvchi ko'rinishida (`GET /quizzes/{id}/`, imtihon `current`): `min_words` bor, javob kaliti yo'q.
- Javob yuborish: boshqa matnli turlar kabi `{ "question": "<id>", "value_text": "..." }` (20 000 belgigacha).
- **Avtomatik baholanmaydi**: `earned_points = 0`. Oddiy testda `max_score` hisobiga **kirmaydi** (insho umumiy foizni tushirmaydi),
  `is_correct = false` — frontend "O'qituvchi tekshiradi" deb ko'rsatishi kerak (`question_type == "essay"`).
- Yuklab olish (`/quizzes/{id}/export/`): insho uchun yozish qatorlari va "kamida N ta so'z" chiqadi, javob kaliti yo'q.

## 2. IELTS Writing AI tahlili (mock imtihon)

O'qituvchi tugmani bosadi — baholash fonda (cron `sync_exam_writing_ai`, har 30 s):

`POST /api/v1/exams/{exam}/results/{student}/writing-ai/` → `200`, javob — `GET results/{student}/` bilan bir xil (quyida), `writing_ai.status = "queued"`.
Natija tayyor bo'lguncha shu GET'ni har 3–5 soniyada so'rang (`status`: `queued` → `done` | `failed`).

Faqat IELTS imtihon (`scoring.type == "ielts"`), faqat imtihon o'qituvchisi, o'quvchi Writing'ga javob yozgan bo'lishi kerak.
Xatolar: `400` (IELTS emas / javob yo'q / AI sozlanmagan), `403`, `404`.

`GET /api/v1/exams/{exam}/results/{student}/` ga qo'shilgan maydonlar:
```jsonc
"writing_ai": {
  "status": "done",                    // queued | done | failed (failed: "error" matni bor)
  "suggested_band": 6.5,               // FAQAT o'qituvchiga. Writing bandi: Task 1 + 2*Task 2, /3, 0.5 ga yaxlitlangan
  "items": [{
    "question": "...", "task": 2, "word_count": 281, "min_words": 250, "too_short": false,
    "overall_band": 6.5,
    "criteria": [ {"key": "task|coherence|lexical|grammar", "title": "Task Response", "band": 6.5,
                   "capped": false, "comment": "...", "evidence": "..."} , ... ],   // 4 ta
    "errors": [ {"quote": "...", "issue": "...", "correction": "..."} ],
    "strengths": ["..."], "improvements": ["..."], "upgraded_paragraph": "..."
  }]
},
"review": [ ... ]                      // 3-bo'limga qarang
```
- Task raqami savolning `min_words` qiymatidan aniqlanadi (≥200 → Task 2, aks holda Task 1).
- So'z soni minimumdan 10% dan ko'p kam bo'lsa "task" bandi cheklanadi (`capped: true`): 75–90% → 6.0, 50–75% → 5.0, <50% → 4.0 (taxminiy qoida).
- **O'quvchi** `writing_ai` ni faqat o'qituvchi Writing bandini qo'ygach (`PUT .../manual/`) va faqat tahlil qismini (`suggested_band`siz) ko'radi; oldin `null`.
- Yakuniy bandni doim o'qituvchi qo'yadi (`PUT .../manual/`, mavjud endpoint).

## 3. Savol-savol tahlil (Listening/Reading)

`GET /api/v1/exams/{exam}/results/{student}/` → `review[]` (avtomatik tekshiriladigan bo'limlar, insholarsiz):
```json
{ "section": "reading", "section_title": "Reading", "number": 7, "question": "...", "type": "single",
  "given": "B" , "correct_answer": "C", "earned": 0, "points": 1, "is_correct": false }
```
O'qituvchiga doim; o'quvchi/ota-onaga faqat **imtihon tugagach** (`now >= ends_at`) — erta tugatgan o'quvchi javoblarni
sinfdoshlariga aytib qo'ymasligi uchun. Javob bermagan savolda ham `correct_answer` bor, `given = null`.

## 4. Uy vazifasi: ingliz tili + `skill_key = "writing"`

Vazifa ingliz tili guruhida `skill_key: "writing"` bilan berilsa, AI tekshiruvi umumiy rubrika o'rniga IELTS 4 mezoni bilan ishlaydi.
Natija (`submission.result`) eski shaklda (frontend o'zgarmaydi): har mezon — bitta `questions[]` elementi (`score` = band/9*100, matnda "Band 6.5"),
umumiy `overall_score` = band/9*100, `grade` = "IELTS Writing Band 6.5", qo'shimcha `result.ielts` — yuqoridagi `items[]` bilan bir xil tuzilma.
O'qituvchi doim tasdiqlaydi (`pending_review`).

## 5. AI test yaratish: IELTS Writing va daraja

- `exam_name = "IELTS Writing"` → Task 1 (150 so'z; ma'lumot rasm emas, matnli jadval ko'rinishida savol ichida) va Task 2 (250 so'z) `essay` savollari.
- Daraja (target band) mavzuga qo'shiladi (`topic`: "... · band 6.5 darajasi"); yozuvchi AI shu darajaga moslab yozadi.
