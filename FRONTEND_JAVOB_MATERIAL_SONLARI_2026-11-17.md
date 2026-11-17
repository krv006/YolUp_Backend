# Backend javobi: guruh papkasida video va doska soni (Materiallar)

## Nima o'zgardi

`GET /api/v1/materials/courses/` javobidagi har guruhga 2 ta maydon qo'shildi:

| maydon | ma'nosi |
|---|---|
| `recording_count` | guruhdagi video yozuvi bor darslar soni |
| `board_count` | guruhdagi doskasi bo'sh bo'lmagan darslar soni |

`file_count` o'zgarmadi.

```json
[
  { "id": "…", "title": "Ingliz Tili A1", "kind": "group", "subject": "english", "file_count": 2, "recording_count": 3, "board_count": 1 }
]
```

Frontendda o'zgarish kerak emas, tayyor kod yangi maydonlarni o'zi oladi.

## Qoidalar (guruh ichidagi dars ro'yxati bilan bir xil)

- Bekor qilingan va o'chirilgan darslar sanalmaydi.
- Doska: bitta darsda bir nechta varaq bo'lsa ham 1 deb sanaladi. Faqat chizilgan varaq hisobga olinadi, bo'sh varaq sanalmaydi.
- Video, o'qituvchi va admin: yozuvi bor har dars sanaladi (hali birlashayotgan yoki o'girilayotgani ham).
- Video, o'quvchi va ota-ona: faqat tayyor yozuv sanaladi. MP4 ga o'girilayotgan yozuv tayyor bo'lgach sanaladi.

Shuning uchun son dars ro'yxatidagi `has_recording` va `has_board` belgilari soniga teng chiqadi.

## Tekshirildi

Avtomatik testda: o'qituvchi, o'quvchi va ota-ona uchun sonlar, ko'p varaqli doska (1 ta), bo'sh varaq, bekor qilingan va o'chirilgan dars, boshqa guruh aralashmasligi, birlashayotgan yozuv tayyor bo'lgach o'quvchi soni oshishi, dars ro'yxati bilan moslik.

## Tekshirish (QA)

1. O'qituvchi: yozilgan va doskaga chizilgan, fayl yuklanmagan dars bor guruh. Kutiladi: `file_count: 0`, `recording_count: 1`, `board_count: 1`.
2. O'quvchi: shu guruhda yozuv hali o'girilmoqda. Kutiladi: `recording_count: 0`. Tayyor bo'lgach `1`.
3. Bekor qilingan yoki o'chirilgan dars sanalmaydi.
