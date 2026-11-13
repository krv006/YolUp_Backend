# Frontend uchun: Speaking (ovozli) uy vazifasi — brauzerda yozilgan ovoz endi qabul qilinadi

## Muammo

Speaking vazifasiga faqat `.mp3 .wav .m4a .ogg` qabul qilinardi. Brauzer (`MediaRecorder`) esa odatda boshqa format beradi:

| brauzer | odatiy format | fayl kengaytmasi |
|---|---|---|
| Chrome, Edge, Firefox (Android ham) | `audio/webm;codecs=opus` | `.webm` |
| Safari / iPhone | `audio/mp4` | `.mp4` yoki `.m4a` |

Shuning uchun ilovada yozilgan ovoz `400` ("'.webm' qo'llab-quvvatlanmaydi") bilan rad etilardi.

## Nima o'zgardi

Speaking vazifasida endi qabul qilinadi: `.mp3 .wav .m4a .ogg .webm .mp4 .flac .oga .opus` (25 MB gacha, bir topshiriqda ko'pi bilan 5 ta fayl — avvalgidek).
AI tekshiruvi (ovozni matnga aylantirish va baholash) hammasi uchun bir xil ishlaydi; javob formati o'zgarmagan.
Speaking bo'lmagan vazifaga audio yuklansa — avvalgidek `400`: "Audio faqat Speaking vazifalari uchun."

## Frontend uchun

- Yozilgan blob'ni yuborganda fayl nomining kengaytmasi **blob turiga mos** bo'lsin: `blob.type.includes('webm') ? 'voice.webm' : 'voice.mp4'` (Safari).
  Kengaytma bo'lmasa yoki noto'g'ri bo'lsa backend `400` qaytaradi.
- `MediaRecorder.isTypeSupported('audio/webm;codecs=opus')` bo'lmasa `audio/mp4` ni sinab ko'ring.
- Xato matni `error.details.file` da keladi — foydalanuvchiga ko'rsating.

## Tekshirish ro'yxati

- Chrome'da yozilgan `voice.webm` → Speaking vazifaga `201`, keyin AI natijasi (`source: "audio-transcript"`).
- Safari/iPhone'da yozilgan `voice.mp4` → `201`.
- Writing vazifasiga `voice.webm` → `400`.
