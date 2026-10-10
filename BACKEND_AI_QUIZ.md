# AI bilan test yaratish — imtihon qoidalari bo'yicha (frontend / mobil uchun)

**Qisqasi:** o'qituvchi **material** (PDF/Word/PowerPoint/Excel/matn) yuklaydi va ixtiyoriy ravishda **imtihon qoidalari**ni
(fayl yoki matn; masalan "IELTS Reading: 3 ta matn, 40 savol, True/False/Not Given, ...") qo'shadi. AI qoidalarni o'qib
testni **shu tuzilma bo'yicha** to'liq tuzadi: bo'limlar, matn parchalari (guruhlar), turli turdagi savollar, ularning
tartibi va talabaga ko'rsatiladigan ko'rsatmalar. **Qoidalar berilmasa** — oddiy variantli (A-B-C-D) test. **Material ham ixtiyoriy:** bo'sh bo'lsa AI mavzu va qoidalar bo'yicha matnni o'zi yozadi.
Natija **qoralama test** (o'quvchiga ko'rinmaydi). Imtihon formati kodda yozilmagan: har qanday imtihon uchun bir xil ishlaydi.

Ish **fonda** bajariladi (1–5 daqiqa): so'rov darhol `202` qaytaradi, keyin holatni so'rab turasiz.

## 1. Boshlash — `POST /api/v1/quizzes/ai-generate/` (multipart)

| maydon | | |
|---|---|---|
| `file` | ixtiyoriy, **bir nechta** | material fayllari (bir xil `file` nomi bilan 5 tagacha): `.pdf .docx .pptx .xlsx .xlsm .csv .txt .md`, har biri ≤ 20 MB, jami ≤ 40 MB. Fayl darhol o'qiladi: skanerlangan (rasm) PDF yoki buzuq fayl bo'lsa `400` + sabab |
| `material_text` | ixtiyoriy | material matni (≤ 120 000 belgi), fayllarga qo'shimcha yoki ularning o'rniga |
| `exam_name` | ixtiyoriy | imtihon nomi (`IELTS Academic Reading`, `SAT Math`, ...): qoidalar berilmasa AI uning rasmiy tuzilmasini o'zi eslaydi. Qoidalar berilsa — qoidalar ustun |
| `rules_file` | ixtiyoriy | imtihon qoidalari hujjati (shu formatlar), ≤ 5 MB |
| `rules_text` | ixtiyoriy | qoidalar matni (≤ 30 000 belgi). `rules_file` bilan birga ham berish mumkin |
| `topic` | majburiy | mavzu |
| `title` | ixtiyoriy | test nomi (bo'sh bo'lsa AI imtihon nomini qo'yadi) |
| `question_count` | ixtiyoriy | 5–60, standart 20. Oddiy rejimda — savollar soni; qoidalarda son belgilangan bo'lsa, qoidalar ustun |
| `course` yoki `subject` | biri shart | guruh id yoki fan kodi (`math`, `english`, ...) |
| `standard` | ixtiyoriy | `uzbmb\|ielts\|sat` — **Test banki** rejimi (Test-creator, 2026-10 versiyasi): standart bo'yicha reja va savollar banki, faqat A-B-C-D; aynan bitta `file` kerak; `exam_name`, qoidalar va `material_text` e'tiborga olinmaydi. AI sahifasida "Qo'shimcha → Test banki" |

Javob `202`: `{ id, status: "queued", mode, topic, ... }`. `mode`: `rules` (qoidalar yoki imtihon nomi bo'yicha) · `simple` (oddiy variantli) ·
`test_creator` (Test banki).

Xatolar (`400`, `error.details.*`): fayl turi/hajmi (`file`, `rules_file`), qoidalar matni uzunligi (`rules_text`), bo'sh mavzu, savollar soni,
guruh/fan yo'q. Cheklov: o'qituvchiga bir vaqtda **3 ta** faol ish, **kuniga 10 ta** (`error.details.detail`). AI sozlanmagan bo'lsa
`400` ("AI bilan test yaratish hozir o'chirilgan") — UI xabarni ko'rsatsin.

## 2. Holat — `GET /api/v1/quizzes/ai-generate/{id}/` va ro'yxat `GET /api/v1/quizzes/ai-generate/`

`status`: `queued` (navbatda) → `generating` (reja tuzilmoqda / bo'limlar yozilmoqda) → `done` | `failed`.
Test banki rejimida (`mode: test_creator`) oraliq `processing` ham bor: material tahlili, keyin test fonda yig'iladi (`generating`), cron har 30 s holatini so'raydi; xizmat testni so'ralganidan kam savol bilan tugatsa ham (`partial`) qabul qilinadi va `summary`da aytiladi.

| maydon | ma'nosi |
|---|---|
| `quiz` | `done` bo'lganda qoralama testning id'si (`GET /quizzes/{id}/`) |
| `summary` | masalan `"2 bo'lim · 10 savol"`; yaroqsiz savollar tushib qolgan bo'lsa shu haqda eslatma |
| `error` | `failed` bo'lganda sababi (o'qituvchiga ko'rsatiladi) |
| `rules_name` | yuklangan qoidalar fayli nomi |

Har 5 soniyada so'rab turing yoki bildirishnomani kuting: `ai_quiz_ready` (`link_type: quiz`, `link_id: <quiz id>`) / `ai_quiz_failed`.
Vaqtinchalik xatoda (AI band, tarmoq) ish o'zi qayta urinadi (3 marta, orasida 2 daqiqa); tayyor bo'limlar saqlanadi — qayta boshlanmaydi.

## 3. Tayyor test

`quiz` — oddiy **qoralama** (`status: "draft"`). Unda:
- **Matn parchasi** bo'lgan bo'limlar uchun **savollar guruhi** (`groups[]`: sarlavha + matn), shu bo'lim savollari `group` bilan bog'langan;
- savollar qoidalardagi **tartibda**; har blokning birinchi savolida blok **ko'rsatmasi** (masalan "Choose NO MORE THAN TWO WORDS...") matn boshida;
- savol turlari: `single`, `multiple`, `true_false`, `matching`, `fill_blank` (`{{1}}`), `text` (qisqa javob), `numeric`, `ordering`.
  IELTS'dagi True/False/Not Given va Yes/No/Not Given — 3 variantli `single`.

O'qituvchi qoralamani tahrirlaydi (`PATCH /quizzes/{id}/`), e'lon qiladi (`POST /quizzes/{id}/publish/`), imtihonga ulaydi (`POST /exams/`).
AI javoblari to'g'riligi **kafolatlanmagan** — e'lon qilishdan oldin tekshirish shart.

## 4. Frontend uchun UI

Workspace → **AI** sahifasi: material, **imtihon qoidalari** (fayl tanlash yoki matn yozish — ixtiyoriy), savollar soni; ostida "Mening AI testlarim"
ro'yxati (holat, `summary`, tayyor bo'lsa "Testni ochish"). Xatoda `error` matnini ko'rsating.

## 5. Cheklovlar
- Audio (Listening) yaratilmaydi; Listening/Speaking uchun faqat savol/topshiriq matni bo'lishi mumkin, audio'ni o'qituvchi yuklaydi.
- Sifat materialning to'liqligiga va qoidalarning aniqligiga bog'liq: qoidalar qanchalik aniq bo'lsa, tuzilma shunchalik to'g'ri chiqadi.
