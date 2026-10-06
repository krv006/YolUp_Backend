# Savollar guruhi — matn parchasi (Reading/SAT) va audio (Listening)

**Holat:** backend tayyor. Maqsad: IELTS Reading (bitta matn ostida 13 ta savol), IELTS Listening (bitta audio ostida 10 ta savol), SAT (matn + savol) uchun testlarda **umumiy material** berish. Imtihon (`BACKEND_EXAMS.md`) shu testlarni ishlatadi.

**Orqaga mos:** `groups` va savoldagi `group` **ixtiyoriy**. Eski testlar, Word/Google import va oddiy test yechish hech o'zgarmaydi (guruhsiz savollarda `group: null`, `groups: []`).

---

## 1. Ma'lumot shakli

**Guruh** (`groups[]` — testning o'qish javobida ham, o'quvchi ko'rinishida ham bor):
```json
{ "id": "<uuid>", "order": 0, "title": "Passage 1", "passage": "matn parchasi ...", "audio_url": null }
```
- `passage` — oddiy matn (yangi qatorlar saqlanadi); uzunligi ≤ 30 000 belgi.
- `audio_url` — **to'liq (absolyut) manzil** (`https://edu.thesofmebel.uz/media/quiz_audio/....mp3`), yo'q bo'lsa `null`. To'g'ridan-to'g'ri `<audio src>` ga qo'yish mumkin.

**Savol** endi `group` maydoniga ega — guruh `id` si yoki `null`:
```json
{ "id": "...", "type": "single", "text": "Q1", "group": "<group uuid>", "options": [...] }
```
Guruhni ko'rsatish: savollarni `group` bo'yicha guruhlab, har guruh tepasida `title` + `passage` + audio pleyer ko'rsating. Guruhsiz savollar oddiy ko'rinadi. Javob kaliti (`is_correct`, `answer_key`) guruhda yo'q.

---

## 2. Yaratish — `POST /api/v1/quizzes/`

Odatdagi so'rovga `groups` qo'shiladi; savol guruhga **`groups` ro'yxatidagi tartib raqami (0 dan)** bilan ishora qiladi:
```json
{
  "course": "<uuid>", "topic": "Reading mock", "title": "Passage test",
  "groups": [
    {"title": "Passage 1", "passage": "birinchi matn ..."},
    {"title": "Passage 2", "passage": "ikkinchi matn ..."}
  ],
  "questions": [
    {"type": "single", "text": "Q1", "group": 0, "options": [...]},
    {"type": "single", "text": "Q2", "group": 0, "options": [...]},
    {"type": "single", "text": "Q3", "group": 1, "options": [...]},
    {"type": "single", "text": "Q4", "options": [...]}          // guruhsiz
  ]
}
```
- `group` mavjud bo'lmagan tartib raqamiga ishora qilsa — `400` (`details.questions`).
- Javobda (`201`) har guruhning haqiqiy `id` si keladi — audio yuklash uchun kerak.

## 3. Audio yuklash (IELTS Listening)

`POST /api/v1/quizzes/{quiz_id}/groups/{group_id}/audio/` — **multipart**, maydon `file`.
- Formatlar: `mp3, m4a, aac, ogg, wav`. Hajm ≤ **60 MB**. Xato — `400` (`details.file`).
- Mavjud audio bo'lsa — almashtiriladi (eskisi o'chadi).
- Javob: yangilangan guruh (`audio_url` bilan).
- Faqat test egasi (boshqa kimdir — `403`/`404`).

`DELETE` shu manzilga — audioni olib tashlaydi (`204`).

> **Eslatma (xavfsizlik):** audio ochiq `/media/` orqali beriladi; fayl nomi taxmin qilib bo'lmaydigan tasodifiy (uuid), lekin havolani bilgan kishi eshita oladi. Imtihon uchun amaliy, jiddiy "yopiq" himoya kerak bo'lsa — keyingi bosqich.

## 4. Tahrirlash — `PATCH /api/v1/quizzes/{id}/`

`groups` va `questions` **to'liq almashtirish** semantikasi bilan ishlaydi, lekin audio yo'qolmasligi uchun guruhlarni `id` bilan yuboring:

| So'rov | Natija |
|---|---|
| `groups` + `questions` | Guruhlar ro'yxatga moslanadi: **`id` berilganlari saqlanadi** (audio bilan), `id`siz — yangi, ro'yxatda yo'qlari **o'chadi** (audiosi ham). Savollar yangi ro'yxat tartib raqami bilan bog'lanadi. |
| faqat `questions` (`groups` yo'q) | Mavjud guruhlar **o'z tartibida** saqlanadi, savollar ularga tartib raqami bilan ishora qiladi. |
| faqat `groups` | Matn/sarlavha yangilanadi, savollarga tegilmaydi. Olib tashlangan guruhning savollari guruhsiz qoladi. |

Cheklovlar (o'zgarmagan): testda urinishlar bo'lsa yoki imtihonga biriktirilgan bo'lsa `questions` o'zgartirib bo'lmaydi; faqat `groups` (matn tahriri) mumkin.

Boshqa testning guruh `id` si yuborilsa e'tiborsiz qoldiriladi (yangi guruh yaratiladi) — boshqa testga ta'sir qilmaydi.

## 5. Imtihonda

`GET /api/v1/exams/{id}/current/` dagi `item` ichida endi `groups` ham bor (savollar bilan birga):
```json
"item": { "kind": "section", "key": "reading", "groups": [ {...} ], "questions": [ {..., "group": "<id>"} ] }
```
Bo'lim ichida savollarni xuddi shunday `group` bo'yicha guruhlab ko'rsating. IELTS Listening: guruhning `audio_url` si pleyerga.

> Real IELTS Listening audiosi **bir marta** eshittiriladi va to'xtatib bo'lmaydi — bu cheklovni pleyerni UI'da yashirish bilan frontendda qo'yish mumkin (backend faqat audio manzilini beradi).
