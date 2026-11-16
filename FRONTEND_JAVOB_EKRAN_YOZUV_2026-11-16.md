# Backend javobi: ekran ulashish o'chirib-yoqilganda yozuv uzilmasin (Trello 62)

## Natija

Frontend yuboradigan ma'lumotda o'zgarish yo'q (`POST /lessons/{id}/recording/video/`: `chunk`, `session`, `index`, `started_at`).
Backend tomonida yozuvni birlashtirish kodi mustahkamlandi.

## Backendda nima o'zgardi

| xavf | nima qilindi |
|---|---|
| Sessiyalar har xil o'lchamda (oyna almashtirildi) | Eng uzoq sessiya kadri asos qilinadi. Boshqa o'lchamli sessiyalar shu kadrga sig'diriladi (nisbat saqlanadi, bo'sh joy qora) va shundan keyin ulanadi. Eng uzoq sessiya qayta kodlanmaydi |
| Yakuniy MP4 da o'lcham o'rtada o'zgaradi | MP4 qat'iy o'lchamda chiqadi (birinchi kadr o'lchami, eni 1280 gacha). Boshqa o'lchamli kadrlar cho'zilmaydi, qora chiziq bilan joylashadi |
| Ko'p sessiya (10-20 marta to'xtatib-yoqish) | Bitta sessiyaning `started_at` yo'q bo'lsa ham qolgan tanaffuslar to'ldiriladi. Avval hammasi o'chib qolardi. Vaqt aniqlanmaganda qolgan sessiyalar tashlab yuborilardi, endi ulanadi |
| Juda qisqa sessiya (1-2 soniya, kadrsiz) | O'qib bo'lmaydigan bo'lak tashlanadi, uning vaqti keyingi tanaffusga qo'shiladi |

Tanaffus paytida videoda oxirgi kadr qotib turadi (avvalgidek). Boshqa ko'rinish kerak bo'lsa, mahsulot egasi bilan kelishib, ayting.

## Tekshirildi

Haqiqiy `ffmpeg` va `mkvmerge` bilan avtomatik testlarda:
- har xil o'lchamli 3 ta sessiya (128x72, 110x80) bitta uzluksiz videoga ulanadi, davomiyligi tanaffuslar bilan mos;
- 12 ta qisqa sessiya hammasi yozuvda bor;
- o'lchami o'zgargan fayldan yakuniy MP4 qat'iy o'lchamda, xatosiz chiqadi;
- avvalgi yozuv testlari (tanaffus, oxirini tenglash, tiklash) hammasi o'tadi.

## Tekshirilmagan (frontend/QA bilan real brauzerda ko'rish kerak)

- Chrome'da haqiqiy oyna almashtirish va "Share this tab instead" bilan to'liq dars.
- Qabul mezonidagi 1-6 ssenariylar real darsda. Avtomatik testlar ularning asosiy qismini (ko'p sessiya, har xil o'lcham, ekran to'xtatilgan holda oxirini tenglash) fayl darajasida yopadi.
