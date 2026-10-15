# Dars yozuvi — iOS uchun MP4 (backend javobi)

**Holat:** backend tayyor. Frontend/iOS tarafda o'zgarish **shart emas**: stream manzil o'sha (`.../recording/stream/?t=<token>`).

## Nima o'zgardi
- Dars yozuvi brauzerdan WebM (VP8/VP9 + Opus) bo'lib keladi — u asl nusxa sifatida saqlanadi va darhol "tayyor" bo'ladi.
- Yozuv tayyor bo'lgach, **fonda** iOS ochadigan nusxa tayyorlanadi: **MP4 (H.264 + AAC)**, `faststart` (indeks faylning boshida),
  1280 px gacha, ~15 kadr/s. Faqat audio yozuvlar uchun **M4A (AAC)**.
- Nusxa tayyor bo'lsa, `recording/stream/` shuni beradi: `content-type: video/mp4` (audio uchun `audio/mp4`), `accept-ranges: bytes`
  (Range ishlaydi, oldinga surish mumkin). Tayyor bo'lmaguncha avvalgidek `video/webm` beriladi.
- **Eski yozuvlar** ham avtomatik, navbat bilan (eskisi oldin) o'giriladi — qo'lda hech narsa qilish shart emas.

## Muhim: o'girish vaqt oladi
Yangi dars tugagach, MP4 nusxa **darhol emas**, bir necha daqiqadan bir necha soatgacha (dars uzunligi va server bandligiga qarab)
tayyor bo'ladi. Shu vaqtgacha iPhone'da yozuv ochilmasligi mumkin (WebM beriladi). Eski yozuvlar uchun ham shunday: ularning hammasi
o'girilguncha biroz kutish kerak. Ilovada "yozuv tayyorlanmoqda" holati ko'rsatish foydali bo'lishi mumkin.

## Tekshirish
```bash
curl -sI "<yozuv havolasi>" | grep -i "content-type\|accept-ranges"
```
MP4 tayyor bo'lgan yozuvda: `content-type: video/mp4`, `accept-ranges: bytes`.

## Backend tomoni (ma'lumot uchun)
`LessonRecording.mp4_file_name` / `mp4_error`; buyruq `python manage.py convert_recordings [--limit N] [--retry-failed]`;
docker-compose'dagi alohida `transcoder` xizmati (bir vaqtda bitta yozuv, CPU cheklangan, past ustuvorlik).
