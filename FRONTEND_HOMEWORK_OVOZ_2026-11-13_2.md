# Frontend uchun: Speaking uy vazifasiga ovoz yuborish (yangi eslatma)

Holat: backend **productionda ishlayapti** (2026-11-13 deploy qilingan). Frontend tomonidan faqat yuborish kodini tekshirish kerak.

## 1. Nima o'zgardi

Speaking vazifasiga endi brauzerda yozilgan ovoz ham qabul qilinadi. Qabul qilinadigan kengaytmalar:

`.mp3 .wav .m4a .ogg .webm .mp4 .flac .oga .opus`

- Hajm: bitta fayl 25 MB gacha, bir topshiriqda ko'pi bilan 5 ta fayl (avvalgidek).
- AI tekshiruvi (ovozni matnga aylantirish va baholash) hamma formatda bir xil ishlaydi.
- Javob formati o'zgarmagan.
- Speaking bo'lmagan vazifaga (Writing va boshqalar) audio yuborilsa: `400`, "Audio faqat Speaking vazifalari uchun."

## 2. Nega avval ishlamagan

`MediaRecorder` beradigan format brauzerga bog'liq, avval esa faqat `.mp3 .wav .m4a .ogg` qabul qilinardi:

| Brauzer | Format | Fayl kengaytmasi |
|---|---|---|
| Chrome, Edge, Firefox (Android ham) | `audio/webm;codecs=opus` | `.webm` |
| Safari / iPhone | `audio/mp4` | `.mp4` yoki `.m4a` |

Shu sabab yozilgan ovoz `400` bilan qaytarilardi.

## 3. Frontend nima qilishi kerak

Fayl nomining kengaytmasi blob turiga mos bo'lishi shart. Backend turni kengaytmaga qarab aniqlaydi, kengaytma bo'lmasa yoki noto'g'ri bo'lsa `400` qaytaradi.

```js
// yozishni boshlashdan oldin qo'llab-quvvatlangan formatni tanlang
const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
  ? 'audio/webm;codecs=opus'
  : 'audio/mp4'; // Safari / iPhone

const recorder = new MediaRecorder(stream, { mimeType });

// yuborishda
const blob = new Blob(chunks, { type: recorder.mimeType });
const ext = blob.type.includes('webm') ? 'webm' : 'mp4';

const form = new FormData();
form.append('file', blob, `voice.${ext}`); // kengaytma blob turiga mos
```

Eslatma: `file` maydon nomini mavjud submission endpoint'dagi nom bilan bir xil qoldiring, bu yerda faqat fayl nomi va kengaytma muhim.

Xato bo'lsa matn `error.details.file` da keladi, uni foydalanuvchiga ko'rsating.

## 4. Tekshirish ro'yxati

- Chrome'da yozilgan `voice.webm` Speaking vazifaga yuborilsa `201`, keyin AI natijasi keladi (`source: "audio-transcript"`).
- Safari / iPhone'da yozilgan `voice.mp4` yuborilsa `201`.
- Writing vazifasiga `voice.webm` yuborilsa `400` (kutilgan xatti-harakat).
- Hali ham xato bo'lsa: brauzer konsolidagi xato va javob tanasini (response body) backendga yuboring.
