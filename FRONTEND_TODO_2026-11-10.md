# Frontend uchun qolgan ishlar (2026-11-10) — Trello kartalari bo'yicha

Backend tomoni tayyor (`BACKEND_YANGILANISHLAR_2026-11-10.md` ga qo'shimcha). Bu hujjat faqat **frontendda** qoladigan ishlarni tasvirlaydi.

---

## 1. Screen record: ekranda username va Yolup logosi ("screeen record" kartasi)

**Maqsad:** kimdir darsni ekran yozuvi bilan (telefon, OBS, QuickTime, boshqa dastur) yozib olib, uchinchi tomonga tarqatsa, **kim yozganini** bilish mumkin
bo'lsin. Buning uchun har bir foydalanuvchining o'z ekranida uning `username`i va kichik Yolup logosi doim ko'rinib turadi, yozib olingan videoda ham.

**Nima qilish kerak (web):**
- Dars (jonli xona), doska, yozuvni ko'rish (`recording` sahifasi), material/PDF ko'rish sahifalarida butun ekran ustidan **yarim shaffof belgi** (watermark):
  - kichik **Yolup logosi** (burchakda, masalan pastki o'ng);
  - foydalanuvchining `username`i (yoki ism + username) — kamida bitta joyda doim, yaxshisi bir necha joyda (burchaklarda yoki yengil qiyshaygan
    takrorlanuvchi yozuv sifatida), shunda kadrni qirqib tashlash qiyin bo'ladi.
- Belgi sahifa tarkibini to'sib qo'ymasligi kerak: `position: fixed`, `pointer-events: none`, yuqori `z-index`, shaffoflik ~15–25%.
- Ma'lumot manbai: `GET /auth/me/` → `username` (qo'shimcha backend kerak emas).
- Belgini DOM'dan osongina olib tashlab bo'lmasligi uchun (DevTools) `MutationObserver` bilan o'chirilsa qayta qo'shib turing. To'liq himoya mumkin emas:
  brauzer operatsion tizim darajasidagi ekran yozuvini taqiqlay olmaydi, belgi faqat kim yozganini aniqlashga yordam beradi.
- **O'qituvchining ekran ulashishi** (`getDisplayMedia`) va serverga yuklanadigan dars yozuvi (`recording`) o'qituvchi brauzerida olinadi. Yozuvning ichiga
  belgi tushishini xohlasangiz, belgini ulashilayotgan sahifada emas, **ulashishdan oldin** `canvas`ga chizib yozing (yoki dars sahifasidagi belgidan
  foydalaning). Backend yozuvni qayta ishlamaydi, shuning uchun bu butunlay frontend qarori.
- Logo faylini dizayner beradi (SVG, och va to'q fon uchun ikki variant).

## 2. Chatda sana ajratgichlari ("chatda xato bor" kartasi)

Xabarlar orasida kun almashganda sana yozuvi bo'lsin, aks holda "bugun"/"kecha" ajratib bo'lmaydi:

- Xabarlar ro'yxatida har kunning birinchi xabari oldiga ajratgich: **"Bugun"**, **"Kecha"**, undan eskisi uchun sana (`10.11.2026`; joriy yildan boshqasi bo'lsa yil bilan).
- Hisob **foydalanuvchi mahalliy vaqti** bo'yicha: `created_at` — ISO vaqt (UTC offset bilan), uni brauzer vaqt zonasiga o'tkazib, kun bo'yicha guruhlang.
- Chat ro'yxatidagi oxirgi xabar vaqti: bugun — soat (`14:05`), kecha — "Kecha", shu hafta — hafta kuni, undan eski — sana.
- Pastga/tepaga qo'shimcha yuklaganda (`before`, `after`) ajratgichlarni qayta hisoblang (bir kun ikki sahifaga bo'linib qolsa, ajratgich ikki marta chiqmasin).

## 3. Bildirishnomalarda sana ("notification da xatolik" kartasi)

- Inbox qatorida faqat soat emas, **sana va soat**: `GET /notifications/` har qatorida `created_at` (va `notification.created_at`) bor. Bugun bo'lsa "Bugun 14:05",
  kecha — "Kecha 14:05", undan eski — `10.11.2026 14:05`.
- Backend ham matnlarga sana qo'shdi: dars eslatmasi ("... 15 daqiqadan keyin boshlanadi (10.11.2026 18:00)") va ota-onaga davomat xabari
  ("... 10.11.2026 18:03 da qo'shildi"). Frontend matnni o'zgartirmasdan ko'rsatadi.

## 4. Test yaratish — pullik xizmat ("test yaratish qismda" kartasi)

- `GET /auth/me/` da `can_create_tests: bool` (hozircha hammada `true`). `false` bo'lsa: test yaratish tugmalarini (qo'lda, fayldan/Google'dan import, AI) yopiq
  ("Pullik xizmat") holatda ko'rsating va administrator bilan bog'lanish yo'lini bering.
- Yopiq foydalanuvchi yaratishga urinsa backend `403` qaytaradi (`error.code: "permission_denied"`, xabar: "Test yaratish xizmati sizda yoqilmagan..."), shuning uchun
  tugmani `can_create_tests` bo'yicha oldindan yashiring. Mavjud testlarni ko'rish, o'tkazish va natijalar yopilmaydi.
- **Admin paneli:**
  - `GET /auth/teachers/` — har o'qituvchida `can_create_tests`;
  - `PATCH /admin/users/{id}/test-access/ {enabled: true|false}` → `{id, username, can_create_tests}` (faqat admin). Ro'yxatda har qatorga almashtirgich qo'ying.

## 5. Eslatma (ilgari yozilgan, qisqacha)

- "Ota-ona" → **"Kuzatuvchi"**, "Farzand" → **"O'quvchi"**: backend yaratadigan matnlarda va rol nomida (`role: "parent"` kodi o'zgarmadi) shunday bo'ldi.
  Interfeysdagi yorliqlarni ham shunga moslang.
