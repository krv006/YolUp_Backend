# Uy vazifasi (homework) — o'zgarishlar (frontend / mobil uchun)

**Qisqasi:** AI tekshiruv bizning backend ichidan olib tashlandi. Hozir u **alohida tashqi xizmat** (AI-home-checker) sifatida ulanadi va **ixtiyoriy**: xizmat yoqilgan bo'lsa AI ballni taklif qiladi, o'chiq yoki ishlamasa o'qituvchi o'zi baholaydi. Har holda **yakuniy ballni o'qituvchi tasdiqlaydi.**

## 1. Oqim

1. O'quvchi fayl yuklaydi: `POST /homework/assignments/{id}/submit/`. Javob **darhol** `status: "pending_review"` (o'quvchi hech qachon "AI ishlayapti" holatini ko'rmaydi).
2. **AI xizmati yoqilgan bo'lsa:** o'qituvchi ko'rinishida topshiriq 10-60 soniya `status: "checking"` bo'ladi, keyin `pending_review` ga o'tadi va `overall_score`/`grade`/`result` **AI taklifi bilan oldindan to'ldirilgan** bo'ladi (`ai_result`, `ai_overall_score`, `ai_grade` ham to'ldiriladi). O'qituvchiga bildirishnoma shu paytda boradi.
3. **AI xizmati o'chiq/xato/uzoq kutilgan bo'lsa:** topshiriq darhol (yoki 15 daqiqadan keyin) `pending_review` bo'ladi, ball bo'sh, `error` maydonida sabab ("o'zingiz baholang") bo'lishi mumkin; o'qituvchi ballni o'zi kiritadi.
4. O'qituvchi tasdiqlaydi (`POST .../review/`) → `status: "done"`, natija o'quvchi/ota-onaga ochiladi.

O'qituvchi sahifasida `checking` holati qaytdi (spinner / "AI tekshirmoqda"); `checking` da tasdiqlab bo'lmaydi (`400`).

## 2. Baholash — `POST /homework/submissions/{id}/review/`

```json
{ "overall_score": 85, "grade": "Juda yaxshi", "result": { "...": "..." } }
```
- **`overall_score` — majburiy**, 0 dan 100 gacha son (aks holda `400`, `details.overall_score`). Oldin AI ballni o'zi qo'yar edi, endi o'qituvchi kiritadi — baholash oynasida ball maydoni **bo'sh va majburiy** bo'lsin.
- `grade` — ixtiyoriy matn. Berilmasa ballga qarab avtomatik qo'yiladi (90+ A'lo, 80+ Juda yaxshi, 70+ Yaxshi, 60+ Qoniqarli, 50+ Yaxshilash kerak, undan past Jiddiy yaxshilash kerak). Maydonni oldindan to'ldirib ko'rsatishingiz mumkin.
- `result` — ixtiyoriy obyekt (o'qituvchi izohi: masalan `{"summary": {"strengths": [...], "recommendations": [...]}}`); oldingi AI natijasi bilan bir xil shaklni ishlatsangiz eski ko'rinishlar ishlayveradi.
- **Tasdiqlangan natijani ham tuzatish mumkin:** o'qituvchi `done` topshiriqda yana `review` yuborib ballni o'zgartiradi; o'quvchiga "natija yangilandi" bildirishnomasi boradi. "Tahrirlash" imkoniyati bo'lsin.
- Tasdiqlashgacha o'quvchi/ota-onaga `overall_score`, `grade`, `result` ko'rinmaydi (`null`).

## 3. Olib tashlanishi kerak bo'lgan UI

- **O'quvchi tomonda** "tekshirilmoqda"/AI haqida hech narsa ko'rsatmang (o'quvchi doim `pending_review` ni ko'radi).
- **"AI taklifi" bloki** (`ai_result`, `ai_overall_score`, `ai_grade`) — o'qituvchida AI yoqilgan bo'lsa to'ladi, aks holda `null`: `null` bo'lsa blokni yashiring.
- **"Qayta tekshirish"** tugmasi (`POST .../recheck/`) faqat AI yoqilgan bo'lsa ishlaydi (topshiriq `checking` ga qaytadi); o'chiq bo'lsa `400` va xabar: *"AI tekshiruv o'chirilgan. Topshiriqni o'zingiz baholang..."* — xabarni ko'rsating.
- Vazifa yaratish formasidagi **"AI uchun qo'shimcha ko'rsatma"** (`extra_instructions`) maydoni endi hech narsaga ta'sir qilmaydi — yashirishingiz mumkin (API uni baribir qabul qiladi).

## 4. Bildirishnomalar

| `kind` | Kimga | Qachon | `link_type` / `link_id` |
|---|---|---|---|
| `homework_pending_review` | o'qituvchi | topshiriq baholashga **tayyor bo'lgan zahoti**: AI o'chiq bo'lsa topshirilgan paytda, yoqilgan bo'lsa AI natijasi kelganda ("... vazifani topshirdi — «...». Baholashingiz kerak.") | `submission` / `<submission id>` |
| `homework_reviewed` | o'quvchi | o'qituvchi baholaganda yoki tuzatganda ("natijasi tayyor" / "yangilandi") | `submission` / `<submission id>` |

Bildirishnomani bosganda `link_type: "submission"` bo'yicha topshiriq sahifasiga o'ting (`GET /homework/submissions/{id}/`). Mobil push ham shu bildirishnomalardan ketadi.

## 5. Topshirish cheklovi

`POST .../submit/`: bir vazifaga **soatiga 5 tadan**, jami **soatiga 20 tadan** ko'p topshirib bo'lmaydi — `400`, xato `error.details.file` ostida. Xabarni fayl maydoni tagida ko'rsating.

## 6. Fayllar

- Topshiriq fayllari va o'qituvchi biriktirmalari **faqat API orqali** olinadi: `GET /homework/submissions/{id}/file/`, `GET /homework/assignments/{id}/file/` (login kerak, asl fayl nomi bilan). `https://.../media/homework/...` to'g'ridan-to'g'ri manzillari **ishlamaydi** (404).
- Sertifikat fayllarining ochiq manzili o'zgarmadi; yangi yuklanganlarning fayl nomi tasodifiy (ro'yxatda `title` ko'rsating).

## 7. O'zgarmagan narsalar

Vazifa berish/tahrirlash/o'chirish, muddat va "kech topshirilgan" belgisi, o'quvchi sahifa kuzatuvi (`focus`), o'qituvchi statistikasi (o'rtacha ball endi faqat baholangan topshiriqlar bo'yicha), ota-ona hisoboti (`/homework/report/?student_id=...`) — hammasi avvalgidek.

## 8. Speaking (ovozli) vazifa — AI endi ovozni ham tekshiradi (2026-11-07)

Ko'nikmasi `speaking` bo'lgan vazifaga o'quvchi `.mp3 .wav .m4a .ogg` (25 MB gacha) yuklaydi. Oqim avvalgidek: `checking` -> `pending_review` (o'qituvchi tasdiqlaydi).
Ichkarida: OpenAI avval ovozni **matnga aylantiradi** (transkripsiya), keyin shu matn va ravonlik statistikasi (tezlik, pauzalar) baholanadi.

Javob (`result`) avvalgi formatda, qo'shimcha maydonlar bilan — **frontend o'zgarishi shart emas**, lekin xohlasangiz ko'rsatishingiz mumkin:
- `questions[]` — har bir **mezon** uchun bitta qator: ingliz tilida *Fluency and Coherence*, *Lexical Resource*, *Grammatical Range and Accuracy* (boshqa tillarda Fluency, Vocabulary, Grammar). `score` — foiz.
- `transcript` — o'quvchi aytgan gapning matni (o'qituvchi eshitmasdan ham ko'rib chiqishi uchun).
- `delivery` — `{words, duration_seconds, words_per_minute, pauses, longest_pause_seconds}`.
- `source: "audio-transcript"`.
- `summary.recommendations[0]` — **doim** talaffuz haqidagi ogohlantirish: "Talaffuz va ohang AI tomonidan baholanmadi — o'qituvchi yozuvni eshitib baholasin".

**Muhim cheklov:** AI talaffuz va ohangni baholay olmaydi (ovoz matnga aylangach ular yo'qoladi). Shuning uchun bu faqat **taklif**; yakuniy bahoni o'qituvchi eshitib qo'yadi.
Jim yoki juda qisqa (5 so'zdan kam) yozuv va buzuq fayl AI'ga yuborilmaydi — topshiriq izoh bilan darhol o'qituvchiga tushadi (`error` maydonida sabab).
