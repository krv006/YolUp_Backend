# O'qituvchi kamerasi qotib qolishi: tahlil va frontend uchun tavsiyalar (2026-11-12)

**Holat:** bugun jonli darsda o'qituvchi kamerasi ochiq turib, qisqa vaqtga qotib qoldi.

## Serverda nima ko'rildi

- LiveKit (MEDIA): oxirgi 24 soatda ogohlantirish/xato yo'q, qayta ishga tushish yo'q, server bo'sh (CPU/tarmoq muammosi yo'q).
- Bugungi ikkala dars (11:04–11:16) bitta brauzerdan: **Windows, Chrome 157**. Birinchi seans 43 soniyadan keyin **mijozning o'zi** chiqib ketgan
  (`CLIENT_REQUEST_LEAVE`), 15 soniyadan keyin qayta kirgan (yozuv tizimi ham shu 14,6 soniyali tanaffusni qayd etgan). Ya'ni sabab serverda emas.

## O'qituvchi brauzeri bir vaqtda nima qilyapti (LiveKit log'idan va kod'dan)

O'qituvchi darsga kirgan zahoti, **hammasi bitta kompyuterda, dasturiy (software) VP8 kodlash bilan**:

| # | nima | o'lcham / bitreyt | manba |
|---|---|---|---|
| 1–3 | **Kamera**, simulcast 3 qatlam | 1280×720 (1,7 Mbit/s) + 640×360 + 320×180 | `video={choices.cameraOn}` standart sozlama, `ROOM_OPTIONS` da `videoCaptureDefaults`/`publishDefaults` yo'q |
| 4–5 | **Ekran ulashish**, simulcast 2 qatlam | **1920×1080** (1,5 Mbit/s) + 960×540 | `requestScreenCapture` o'lcham cheklamaydi; `SCREEN_SHARE_ENCODING` faqat bitreyt/kadr |
| 6 | **Dars yozuvi** (`MediaRecorder`, VP8) | ekran oqimi, 1,5 Mbit/s | `teacher-video-recording.ts` |
| 7 | Audio yozuvi + mikrofon + ekran audiosi | — | `teacher-audio-recording.ts` |

Ya'ni 5–6 ta bir vaqtdagi video kodlash (bittasi to'liq 1080p), ustiga doska, chat, PiP va React render. Kuchsiz yoki issiq noutbukda CPU 100% ga yetadi,
Chrome kadrlarni tashlaydi va kamera "qotadi". Bu **eng ehtimolli sabab**, lekin hali isbotlanmagan (serverda ko'rinmaydi, faqat mijozda o'lchanadi).

## Tavsiya etilgan o'zgarishlar (taʼsiri kattasidan boshlab)

1. **Ekran ulashishni 720p ga tushiring va simulcast'ni o'chiring.**
   `getDisplayMedia({ video: { width: { max: 1280 }, height: { max: 720 }, frameRate: { ideal: 15, max: 15 } } })` va
   `publishTrack(..., { source, screenShareEncoding: SCREEN_SHARE_ENCODING, simulcast: false })`. 1080p ekran matn o'qish uchun ham keraksiz bo'lishi mumkin; bitta qatlam 2 ta kodlashni 1 taga tushiradi.
2. **Kamerani 540p/360p qiling, qatlamlarni kamaytiring.** `ROOM_OPTIONS` ga:
   `videoCaptureDefaults: { resolution: VideoPresets.h540.resolution, frameRate: 24 }` va
   `publishDefaults: { videoSimulcastLayers: [VideoPresets.h180] }` (jami 2 qatlam). O'quvchilarga 720p kamera kerak emas (kichik oynada ko'rinadi).
3. **Qurilmada apparat kodlagichni sinab ko'ring:** `publishDefaults: { videoCodec: "h264" }` (Windows'da GPU orqali kodlanadi, CPU keskin kamayadi).
   Eslatma: o'quvchi brauzerlarida (Safari/eski Android) H.264 dekodlash muammosi bo'lmasligi uchun avval 1–2 qurilmada tekshiring; kerak bo'lsa `backupCodec` qoldiring.
4. **Dars yozuvi kodlashini yengillashtiring.** `MediaRecorder` hozir to'liq ekran oqimini qayta kodlaydi. Variantlar: `videoBitsPerSecond` ni 800 kbit/s gacha tushirish; yozuvni 1280×720
   ga tushirilgan oqimdan olish (1-band bilan bir xil oqim); CPU zo'riqqanda yozuvni to'xtatmasdan sifatini pasaytirish.
5. **CPU zo'riqishini aniqlang va ko'rsating.** LiveKit klienti brauzer `qualityLimitationReason = "cpu"` desa CPU cheklovi hodisasini beradi (`ParticipantEvent.LocalTrackCpuConstrained` / `TrackEvent.CpuConstrained`; nomini o'rnatilgan `livekit-client` versiyasida tekshiring).
   Unda o'qituvchiga "Kompyuter zo'riqmoqda: kamera sifati pasaytirildi" deb ko'rsating va avtomatik pastroq sifatga o'ting (masalan kamera 360p, yozuv bitreyti pastroq).
6. **Diagnostika (keyingi safar sababni aniq bilish uchun).** Darsda har 30 soniyada `localTrack.getSenderStats()` dan `framesPerSecond`, `qualityLimitationReason`,
   `targetBitrate` va `navigator.hardwareConcurrency`, `navigator.deviceMemory`, brauzer/OT ni yig'ib backendga yuboring.
   Backend endpoint **tayyor** (6-band uchun, pastga qarang).

## Hozir tekshirib ko'rish uchun

- Qotish bo'lgan kompyuterda dars paytida Chrome **Task Manager** (Shift+Esc) da brauzer CPU foizini ko'ring; 80–100% bo'lsa sabab shu.
- `chrome://webrtc-internals` → kamera `outbound-rtp` da `qualityLimitationReason` (`cpu` bo'lsa tasdiqlanadi) va `framesPerSecond`.
- Taqqoslash: faqat kamera (ekran ulashishsiz, yozuvsiz) qotadimi? Shunda qaysi qism asosiy yuk ekani ko'rinadi.

## Alohida eslatma (deploy)

Bugun 11:22 va 11:37 da backend deploy paytida API va WebSocket so'rovlari ~4 va ~16 soniya xato bergan (konteynerlar qayta yaratilgan). Bu videoga emas, chat/bildirishnoma/doskaga ta'sir qiladi.
Jonli dars vaqtida deploy qilmaslik qoidasi qo'llanyapti.

## Diagnostika endpoint'i (backend tayyor)

`POST /api/v1/live/lesson/{lesson_id}/client-health/` — darsda har ~30 soniyada yuboring (o'qituvchi ham, o'quvchi ham; faqat shu darsning o'qituvchisi/yozilgan o'quvchisi, aks holda `404`).
Chastota cheklovi: **12 so'rov/daqiqa** (oshsa `429`). Javob: `201 {"id": "..."}`. Kerakmas maydonlar tashlab yuborilsa bo'ladi, noma'lum maydonlar e'tiborga olinmaydi.

```json
{
  "cpu_constrained": true,
  "hardware_concurrency": 8,
  "device_memory": 8,
  "connection_quality": "good",
  "page_visible": true,
  "events": ["cpu_constrained"],
  "tracks": [
    { "source": "camera", "fps": 9.5, "width": 1280, "height": 720,
      "target_bitrate": 1700000, "bitrate": 400000,
      "quality_limitation_reason": "cpu", "packets_lost": 0, "jitter": 0.004, "rtt": 35 },
    { "source": "screen_share", "fps": 15, "width": 1920, "height": 1080, "quality_limitation_reason": "none" }
  ]
}
```

- `tracks[].source`: `camera` | `screen_share` | `microphone` | `screen_share_audio` (ko'pi bilan 8 ta). `quality_limitation_reason`: `none` | `cpu` | `bandwidth` | `other`
  (`getSenderStats()` / `outbound-rtp` dan). Raqamlar sonlar bo'lishi kerak (matn emas), `fps` ≤ 240, o'lcham ≤ 8192.
- `connection_quality`: `excellent` | `good` | `poor` | `lost` | `unknown` (LiveKit `ConnectionQuality`). `events`: ko'pi bilan 10 ta qisqa matn (masalan `cpu_constrained`, `reconnecting`).
- Xato bo'lsa `400` (`error.details` da qaysi maydon).
- Admin ko'radi: `GET /api/v1/monitoring/client-health/?hours=24&lesson=<id>&user=<id>` — foydalanuvchilar kesimida xulosa (CPU tufayli sifati tushgan hisobotlar soni, eng past FPS,
  protsessor yadrolari, xotira, brauzer) va so'nggi hisobotlar. Hisobotlar 14 kun saqlanadi.
