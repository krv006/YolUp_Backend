# Dars yozuvi — iOS uchun MP4 (backend javobi)

**Kimga:** iOS / frontend jamoasi
**Holat:** backend tayyor va serverga chiqarilgan (2026-10-15)
**Sizdan:** hech qanday o'zgarish shart emas. Stream manzil o'sha, faqat fayl formati iOS ochadigan formatga o'tadi.

---

## Qisqasi

`BACKEND-IOS.md` dagi muammo (yozuv `video/webm`, iOS ochmaydi) hal qilindi. Dars yozuvining **MP4 (H.264 + AAC)** nusxasi
tayyorlanadi va `recording/stream/` manzili shuni beradi. Variant A (MP4) tanlandi, HLS emas.

| Talab (sizning so'rovingiz) | Natija |
|---|---|
| MP4, H.264, AAC | Ha: `libx264` (yuv420p) + `aac` 96 kbit/s |
| `moov` atomi boshida (`faststart`) | Ha: pleyer butun faylni kutmaydi |
| `content-type: video/mp4` | Ha |
| `Range` so'rovlari | Ha: `accept-ranges: bytes`, `206 Partial Content`, `Content-Range` |
| Eski yozuvlar ham | Ha: avtomatik, navbat bilan (eskisi oldin) |

Qo'shimcha: faqat **audio** yozuvlar (video yo'q) **M4A (AAC)** bo'lib, `content-type: audio/mp4` bilan beriladi (audio WebM ham
iOS'da ochilmaydi).

## Endpoint o'zgarmadi

```
GET /api/v1/lessons/<id>/recording/            -> { ready, stream_url, ... }   (autentifikatsiya bilan, avvalgidek)
GET <stream_url>                               -> yozuv oqimi (token URLda, auth header kerak emas)
```

`stream_url` ichidagi `?t=<token>` **muddatli**: ochishdan oldin `recording/` dan yangisini oling, eski havolani saqlab qo'ymang.

## Muhim: MP4 tayyor bo'lguncha vaqt ketadi

Yozuv dars tugagach **darhol** "tayyor" (`ready: true`) bo'ladi, lekin u paytda hali WebM. MP4 nusxa **fonda** tayyorlanadi:

- yangi dars: odatda dars uzunligining 0.3–0.7 qismicha (45 daqiqalik dars ~15–30 daqiqa), server bandligiga qarab ko'proq ham bo'lishi mumkin;
- eski yozuvlar: hammasi navbat bilan o'giriladi, birinchi kunlarda ko'p yozuv navbatda bo'ladi.

MP4 tayyor bo'lmaguncha `stream_url` avvalgidek `video/webm` beradi: Android va brauzer uchun muammo yo'q, **iPhone'da esa ochilmaydi**.
Ilovada ochilmasa, "yozuv tayyorlanmoqda, birozdan keyin urinib ko'ring" degan xabar ko'rsatish yaxshi bo'ladi. Qaysi format
berilayotganini bilish uchun `Content-Type` sarlavhasiga qarang (pastda).

## Qanday tekshirish

Yozuv havolasi bilan:

```bash
curl -sI "<stream_url>" | grep -i "content-type\|accept-ranges"
```

- MP4 tayyor: `content-type: video/mp4` (audio bo'lsa `audio/mp4`), `accept-ranges: bytes` -> iPhone ochadi.
- Hali tayyor emas: `content-type: video/webm` -> bir ozdan keyin qayta tekshiring.

Range tekshiruvi:

```bash
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" -H "Range: bytes=0-99" "<stream_url>"
```

Kutiladi: `206 100`.

## Muammo chiqsa

Quyidagilarni yuboring (backendchiga):
1. Dars `id` si va `recording/` javobi.
2. `curl -sI "<stream_url>"` natijasi (sarlavhalar).
3. Xato bo'lsa, iOS jurnalidagi `AVFoundationErrorDomain` qatori.

Ba'zi yozuvlar o'girilmay qolishi mumkin (masalan, fayl buzilgan): ular WebM bilan qoladi va backend jurnalida sababi yoziladi.

---

## Backend tomoni (ma'lumot uchun)

- `LessonRecording.mp4_file_name` / `mp4_error`; asl WebM o'chirilmaydi.
- Buyruq: `python manage.py convert_recordings [--limit N] [--retry-failed]`.
- docker-compose'dagi alohida `transcoder` xizmati: bir vaqtda bitta yozuv, CPU cheklangan (`TRANSCODER_CPUS`, standart 2), past ustuvorlik.
- Video: 1280 px gacha, ~15 kadr/s, `crf 28` (ekran yozuvi uchun sifat va hajm muvozanati). Audio: AAC 96 kbit/s.
