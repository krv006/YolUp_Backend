# Frontend uchun: o'quvchi darsga faqat o'qituvchi boshlagandan keyin kiradi

## Qoida

O'quvchi `POST /api/v1/live/token/` orqali darsga **faqat dars `live` bo'lgandan keyin** (o'qituvchi boshlagandan keyin) kira oladi.
Rejalashtirilgan soatdan ertaroq yoki kechroq boshlangani muhim emas: o'qituvchi qachon boshlasa, o'quvchi shundan keyin kiradi.

| holat | o'qituvchi | o'quvchi |
|---|---|---|
| dars `scheduled` (hali boshlanmagan), vaqti bugun, kelajak yoki o'tgan kun | kira oladi va darsni boshlaydi | `400` |
| dars `live` | kira oladi | kira oladi (`200`) |
| dars `finished` / `cancelled` | `400` | `400` |

Avval bugungi yoki kelajakdagi `scheduled` darsga o'quvchi o'qituvchidan oldin kira olardi. Endi kira olmaydi, chunki hech kim o'tkazmayotgan darsga "kirdi" davomati yozilib qolardi.

## Xato javobi

O'quvchi dars boshlanmasdan so'rasa:

```json
{
  "success": false,
  "error": {
    "code": "invalid",
    "message": "Dars hali boshlanmagan. O'qituvchi boshlagandan keyin kira olasiz.",
    "details": {}
  }
}
```

## Frontend uchun

- O'quvchi uchun "Darsga kirish" tugmasini faqat `lesson.status === 'live'` bo'lganda yoqing.
- `scheduled` bo'lsa tugma o'chiq turadi, yonida "O'qituvchi darsni boshlashini kuting" deb yozing.
- Tugma bosilganda `400` kelsa, xabarni (`error.message`) foydalanuvchiga ko'rsating, spinnerda qoldirmang.
- Dars `live` ga o'tganini bilish uchun darslar ro'yxatini vaqti-vaqti bilan yangilab turing yoki chat'dagi "jonli dars boshlandi" signalidan foydalaning (o'qituvchi kirganda guruh chatiga yuboriladi).
- O'qituvchi tomonida o'zgarish yo'q: u istalgan vaqtda, hatto vaqti o'tib ketgan darsni ham kirib boshlay oladi.

## Tekshirish ro'yxati

- `scheduled` darsga o'quvchi bilan token so'rang: `400` va yuqoridagi xabar. Davomat yozilmaydi.
- O'qituvchi kirgach (`live`) o'quvchi token so'rasa: `200`, davomat yoziladi.
- Dars rejadan oldin (ertaroq) boshlansa ham, kechikib boshlansa ham o'quvchi shundan keyin kiradi.
