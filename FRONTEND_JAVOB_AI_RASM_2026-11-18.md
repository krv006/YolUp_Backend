# Uy vazifasi: AI rasmlarni to'g'ri o'qiydi (2026-11-18)

Trello kartasi: "homeworkda image qismdi xammasini encode decode qilish kere ai ga jonatishdan oldin va ai ga jonatish kere boladi".
Backend o'zgardi. Frontend uchun majburiy ish yo'q, lekin 3 ta kichik narsa foydali.

## Backend nimani to'g'riladi

| Oldin | Endi |
|---|---|
| Telefondan olingan rasm AI ga yonbosh bo'lib borardi | EXIF bo'yicha to'g'ri aylantiriladi |
| Doska/PDF'dan faqat 6 sahifa AI ga borardi (aslida 4 tadan ko'pi modelning kontekst oynasiga sig'maydi, ya'ni so'rov butunlay rad etilishi mumkin edi) | Rasmlar **token byudjetiga** qarab tanlanadi: hozirgi model (`gpt-4o-mini`) uchun bitta to'liq sahifa ~25 500 token, kontekst 128 000, shuning uchun **taxminan 3 ta to'liq sahifa/surat** AI ga boradi, qolgani "sig'madi" deb belgilanadi (so'rov rad etilmaydi) |
| Faqat birinchi fayl AI ga borardi | Hamma fayllar (5 tagacha), tartib bilan |
| Word (.docx) va aralash PDF ichidagi rasmlar olinmasdi | Matn bilan birga ichidagi rasmlar ham boradi (logo/ikonka kabi kichik rasmlar olinmaydi) |
| O'qituvchining vazifa sharti rasm bo'lsa, AI savolni ko'rmasdi | Shart rasmi AI ga o'quvchi ishidan alohida beriladi (eng ko'pi 2 ta) |
| iPhone `.heic` rad etilardi | Qabul qilinadi va yuklashda JPEG'ga o'tkaziladi |

## Frontendga ta'siri

1. **`.heic` / `.heif` endi qabul qilinadi** (`POST /homework/assignments/{id}/submit/`). Fayl tanlash oynasidagi `accept` ro'yxatiga va "PDF, JPG, PNG, DOCX · 25 MB gacha"
   matniga `HEIC` qo'shishni ko'rib chiqing. Server faylni JPEG qilib saqlaydi: `file_name` `IMG_1.jpg` bo'lib qaytadi, o'qituvchi brauzerda ocha oladi.
   Buzuq HEIC uchun `400 {"file": ["iPhone rasmini (HEIC) o'qib bo'lmadi. JPG yoki PNG yuklang."]}`.
2. **AI natijasida yangi maydon:** `ai_result.skipped_images` (son). Ish **taxminan 3 ta sahifa/suratdan** ko'p bo'lsa (token byudjeti, qarang yuqorida), qolgan sahifalar baholanmaydi va
   `ai_result.summary.recommendations[0]` ga ogohlantirish yoziladi ("... N ta rasmi/sahifasi AI ga sig'madi ... o'qituvchi qolganlarini o'zi ko'rib chiqsin").
   O'qituvchi natija oynasida shuni ajratib ko'rsatsangiz yaxshi (masalan sariq belgi): ball faqat ko'rilgan sahifalar bo'yicha.
   Qisqa ishlarda bu maydon umuman kelmaydi.
3. Boshqa hech narsa o'zgarmadi: endpointlar, `ai_state`, ball formati oldingidek.

## QA (qo'lda tekshirish)

- iPhone'dan HEIC rasm bilan topshirish → o'qituvchida rasm ochiladi, AI natijasi keladi.
- Yonbosh olingan telefon surati → AI natijasidagi `student_answer` o'qiladi (oldin "o'qib bo'lmadi" ga yaqin chiqardi).
- 8 sahifali doska → natijada `skipped_images: 5` va ogohlantirish (AI faqat dastlabki 3 sahifani ko'radi, shuning uchun o'qituvchi qolganini o'zi ko'rishi kerak).
- Word faylga qo'lyozma rasmi qo'yilgan ish → AI rasmni ham ko'radi.
