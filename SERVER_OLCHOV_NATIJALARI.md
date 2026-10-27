# Haqiqiy o'lchov natijalari (taxmin emas) — 2026-10-27

**Qanday o'lchandi:** loyiha kodini mahalliy kompyuterda (AMD Ryzen, 16 oqim, Windows) **10 000 foydalanuvchilik bazada** ishga tushirdim: 10 000 hisob, 300 guruh, 19 880 yozilish, 6 000 dars, **275 700 davomat yozuvi**, 36 000 chat xabari, **149 100 bildirishnoma**, 27 000 topshiriq, 7 500 test urinishi. Har so'rovni 120–150 marta takrorlab median oldim. Skriptlar: `scratchpad/bench/` (loyiha papkasida emas).

**Cheklovlar (halol):**
1. **Baza — SQLite**, Postgres emas. SQL so'rovlar **soni** aniq (bu o'lchanadi), lekin har birining vaqti Postgres'da boshqacha.
2. **Windows.** Haqiqiy serverda Linux (`uvloop`) — ASGI qatlami ancha tezroq bo'lishi kerak. Windows'da yengil so'rov ichki o'lchovda 1.8 ms, haqiqiy uvicorn orqali 8.8 ms chiqdi. **Linux uchun bu raqam hali o'lchanmagan.**
3. **LiveKit o'lchanmadi** (uning dasturi bu kompyuterda yo'q).
4. Kompyuter protsessori netcup EPYC 9645 (Zen 5) dan sekinroq bo'lishi mumkin — raqamlar shu sababli ehtiyotkor tomonga.

---

## 1. Har bir so'rov qancha protsessor yeydi (bitta so'rov, ichki o'lchov)

| So'rov | Kim, qancha tez-tez | ms | SQL so'rov soni |
|---|---|---|---|
| `GET /live/attention/` | **o'quvchi, darsda, HAR 3 SONIYADA** | **1.8** | 2 |
| `GET /notifications/unread-count/` | har foydalanuvchi, har 60 s | 1.5 | 2 |
| `GET /auth/me/` | sahifa ochilganda | 2.7 | 2 |
| `GET /live/lesson/{id}/presence/` | o'qituvchi, har 20 s | 3.8 | 3 |
| `GET /lessons/?status=live` | chat sahifasidagi har kishi, har 20 s | 13.8 | 8 |
| `POST /live/token/` (darsga kirish) | darsga kirganda 1 marta | 10.3 | 9 |
| `POST /chat/rooms/{id}/send/` | xabar yuborganda | 14.0 | 12 |
| `GET /chat/rooms/{id}/messages/?limit=30` | chat ochilganda | 30.7 | 11 |
| `GET /chat/rooms/` | chat ro'yxati | 44.0 | 21 |
| `GET /courses/` | sahifada | 25.7 | 13 |
| `GET /homework/assignments/` | sahifada | 6.6 | 9 |
| `POST /auth/token/refresh/` | soatiga ~1 marta | 18.7 | 16 |
| **`POST /auth/login/`** | **har kirishda** | **~450** | — |
| `GET /lessons/?page_size=20` | jadval sahifasi | **164** (o'qituvchida 230) | **64** |
| `GET /dashboard/teacher/` | o'qituvchi bosh sahifa | **194** | 8 |
| `GET /attendance/?lesson=` | o'qituvchi, 1 dars (66 o'quvchi) | 128 | — |
| `GET /analytics/me/trends/` | o'qituvchi tahlil | **655** | 26 |
| `GET /analytics/me/` | o'qituvchi tahlil | **1 371** | 46 |
| `GET /board/{id}/` (500 chiziq) | **o'qituvchi, darsda, HAR 2 SONIYADA** | 27 (javob **235 KB**) | — |

**Kirish (login) ~450 ms protsessor** — parolni xeshlash (PBKDF2, 1.2 mln iteratsiya). Bu atayin sekin (xavfsizlik). Muammo: dars boshlanishida 1 500 o'quvchi bir daqiqada kirsa = 675 yadro-soniya ≈ **11 yadro 1 daqiqa**. Token 60 daqiqa, yangilash 7 kun, shuning uchun hamma emas, lekin birinchi kirishlar to'planib qolishi mumkin.

## 2. Hal qiluvchi topilma: so'rov chastotasi (frontend kodidan)

| Qaerda | Nima | Chastota |
|---|---|---|
| **O'quvchi darsda** (`live-room.tsx`) | `attention` | **har 3 soniya = 0.33 so'rov/s har o'quvchiga** |
| Har kirgan foydalanuvchi | bildirishnoma soni | har 60 s |
| Chat sahifasidagilar | jonli darslar ro'yxati | har 20 s |
| **O'qituvchi darsda** | doska (`useBoard` **WebSocket bo'lsa ham** so'raydi) | **har 2 s, har gal butun doska (235 KB / 500 chiziq)** |
| Imtihon | holat | har 15 s |
| Chat (WebSocket ulangan) | so'rov yo'q | — |

**1 500 o'quvchi darsda bo'lsa: 500 so'rov/soniya faqat `attention` uchun.** Bu butun saytning eng katta yuki. 60 o'qituvchi doskani so'rasa — 30 so'rov/s va ~**56 Mbit/s keraksiz trafik** (500 chiziqda).

## 3. Haqiqiy uvicorn serveri ustida yuk (Windows, 1 jarayon)

| Sinov | Natija |
|---|---|
| `attention`, 1 mijoz | 117 so'rov/s, **8.8 ms CPU/so'rov**, javob 8 ms |
| `attention`, 16 mijoz | 185 so'rov/s (bitta jarayon chegarasi), p95 101 ms |
| `lessons?status=live`, 30 mijoz | 61 so'rov/s, 30 ms CPU/so'rov |

Ya'ni **Windows'da bitta jarayon ~120–185 yengil so'rov/s** beradi. Linux'da bu yuqoriroq bo'lishi kutiladi, **lekin o'lchanmagan.**

## 4. WebSocket (chat/doska/bildirishnoma)

| | Natija |
|---|---|
| Xotira, har ochiq ulanish | **34 KB** (735 ulanish o'lchandi, ichki test; haqiqiy uvicorn ulanishi biroz ko'proq xotira olishi mumkin — o'lchanmagan) |
| Ulanishni ochish | 5.3 ms (bazani tekshirish bilan) |
| 1 xabar 60 kishilik guruhga | **30 ms** (= 0.5 ms har yetkazishga; Redis'siz) |
| Kimda nechta ulanish | bildirishnoma (har kirgan) + chat (ochiq bo'lsa) + doska (darsda) |

3 000 ulanish ≈ 100 MB (+ haqiqiy serverdagi qo'shimcha) — xotira bu yerda **muammo emas**.

## 5. Dars yozuvi (haqiqiy Chrome kodlovchisi, VP8, 1.5 Mbit/s chegara, 15 kadr/s)

| Dars turi | Video hajmi |
|---|---|
| Slayd/matn (10 s da almashadi) | 0.17 MB/daq → **15 MB / 90 daq** |
| Doskada yozish | 1.57 MB/daq → **141 MB / 90 daq** |
| **Eng yomon** (butun ekran doim o'zgaradi) | 8.2 MB/daq → **741 MB / 90 daq** |
| Audio (Opus ~64–90 kbit/s) | ~**60 MB / 90 daq** |

⇒ **Odatiy dars (slayd/doska): webm ~75–200 MB + mp4 ~70–130 MB ≈ 150–330 MB.** Avvalgi "1 GB/dars" taxminim 3–5 marta **ko'p** edi.

| Ish | Real narx |
|---|---|
| Yozuv bo'lagi (5.6 MB) qabul qilish | **21 ms** (diskka yozish bilan) — soniyada 1 bo'lak = 2% yadro |
| Birlashtirish (ffmpeg `-c copy`) | 90 daqiqalik dars uchun **~2–3 soniya**, 0.2 CPU-soniya |
| **MP4 ga o'tkazish** (loyiha buyrug'i, 2 yadro) | slayd/doska: **~6 CPU-daqiqa / 90 daqiqalik dars**; eng yomon: **~17 CPU-daqiqa** |
| MP4 hajmi | video 4–60 MB + audio 65 MB (AAC 96k) |

60 dars/kun uchun MP4 o'tkazish = 6–17 yadro-**soat**/kun = ikki yadroda **3–8 soat/kun**. Bu **yetadi** (avvalgi "18 soat" taxminim noto'g'ri edi).

## 6. Jarayon xotirasi

Bitta Django jarayoni (hamma kod yuklangan, bir necha ming so'rovdan keyin): **~172 MB**. 11 worker (8 web + 3 ws) + cron + transcoder ≈ **2.5–3 GB**. 32 GB serverda xotira muammo emas; 16 GB'da ham sig'adi (baza bilan).

---

## 7. Bundan chiqadigan xulosalar (faqat o'lchovga asoslangan)

1. **Eng katta API yuki — `attention` so'rovi (har 3 s).** 1 500 o'quvchi = 500 so'rov/s: ichki narxda ~1 yadro, Windows end-to-end narxda ~4.4 yadro. Uni 3 s dan 15–20 s ga chiqarish yoki WebSocket/LiveKit orqali berish yukni 5–7 barobar kamaytiradi. **Eng arzon va eng katta tejash.**
2. **O'qituvchining doska so'rovi (har 2 s, 235 KB)** — WebSocket ulangan bo'lsa ham ketyapti. To'xtatilsa 56 Mbit/s trafik va ~1 yadro tejaladi. (Kod bo'yicha aniqlandi, haqiqiy darsda tarmoq oynasida tasdiqlash kerak.)
3. **Sekin so'rovlar tuzatilishi kerak:** `GET /lessons/` (64 SQL — har dars uchun 3 ta qo'shimcha so'rov: `quiz_id`, `avg_rating`, `rating_count`), `analytics/me` (1.4 s), `trends` (0.65 s), `dashboard/teacher` (0.19 s). Bular kam so'raladi, lekin 500 o'qituvchi ko'p bo'lsa sezilarli.
4. **Login to'lqini** — dars boshlanishida (xohlansa) bir qancha yadroni bir daqiqaga band qiladi. Throttle (`auth: 30/min`) esa **bitta IP** (maktab) uchun hammani to'sishi mumkin — alohida tekshirish kerak.
5. **Disk:** yozuvlar uchun avvalgidan 3–5 marta kam joy kerak. 60 dars/kun × ~0.25 GB ≈ **15 GB/kun** (webm+mp4), WebM o'chirilsa ~7 GB/kun.
6. **Qaysi serverda nima:** API yuki hozircha taxminan **3.5–8 yadro** (1 500 o'quvchi darsda; yuqoridagi tuzatishlarsiz), bu **APP uchun RS 4000 mantiqli** degan avvalgi qarorni qo'llab-quvvatlaydi, lekin LiveKit narxi (MEDIA) hali **o'lchanmagan**.

## 8. Hali o'lchanmaganlar (taxmin QILMAYMAN, o'lchash kerak)

| Nima | Nima kerak |
|---|---|
| **LiveKit** (1 500 tomoshabin necha yadro/trafik) | Rasmiy `livekit-server` + `lk` vositasi (GitHub'dan yuklab olish — **sizning ruxsatingiz kerak**) |
| **Linux'dagi** haqiqiy so'rov narxi (uvloop) va **Postgres** | WSL (Ubuntu) ichida Postgres + Python o'rnatish — **ruxsat kerak** |
| **Hozirgi prod yuki** (haqiqiy foydalanish) | Eski serverda 4 ta buyruq ishga tushirib, natijani yuborasiz (pastda) |
| Redis orqali chat tarqatish narxi | WSL'da Redis o'rnatish bilan birga |

### Eski (Contabo) serverda ishga tushiradigan buyruqlar — hozirgi haqiqiy raqamlar uchun
```bash
docker stats --no-stream
du -sh /var/lib/docker/volumes/edu_platform_recordings/_data /var/lib/docker/volumes/edu_platform_media/_data /var/lib/docker/volumes/edu_platform_pgdata/_data
ls -lhS /var/lib/docker/volumes/edu_platform_recordings/_data | head -15
docker exec edu_platform-db-1 psql -U edtech -d edtech -c "select (select count(*) from accounts_user) users, (select count(*) from lessons_lesson) lessons, (select count(*) from lessons_lessonrecording) recordings, (select count(*) from chat_message) messages;"
```
(Dars paytida `docker stats --no-stream` ni yana bir marta ishga tushiring — jonli dars vaqtidagi haqiqiy yuk.)

---

# 2-QISM: Linux + PostgreSQL + Redis + LiveKit'da yakuniy o'lchov (2026-10-27)

**Muhit:** WSL2 Ubuntu 26.04, 16 oqim, **PostgreSQL 18** (prod: 17), **Redis 8** (prod: 7), Python 3.14 (prod: 3.13), `gunicorn` + `uvicorn[standard]` (uvloop), **LiveKit 1.13.4** (aynan prod versiyasi). Baza — Postgres'da 10 000 foydalanuvchilik (158 MB). Hamma narsa bitta kompyuterda, shuning uchun yuk generatori serverdan resurs "o'g'irlaydi" (pastda chegaralar).

## 9. Linux + Postgres'da bitta so'rov narxi (ichki o'lchov; Windows'dagidan farqi katta!)

| So'rov | Windows+SQLite | **Linux+Postgres+Redis** |
|---|---|---|
| `attention` (har 3 s) | 1.8 ms | **3.2 ms** |
| `unread-count` | 1.5 | 3.0 |
| `GET /lessons/?status=live` | 13.8 | 12.3 |
| `GET /lessons/?page_size=20` (64 SQL) | 164 | **47** |
| `GET /chat/rooms/` | 44 | 39 |
| `GET /chat/rooms/{id}/messages/` | 31 | 43 |
| `POST /live/token/` (darsga kirish) | 10.3 | 9.7 |
| `POST /chat/rooms/{id}/send/` | 14 | 14 |
| `GET /dashboard/teacher/` | 194 | **58** (SQL 50) |
| `GET /analytics/me/` | 1 371 | **351** (SQL 311) |
| `GET /analytics/me/trends/` | 655 | **200** (SQL 173) |
| `POST /auth/login/` | 453 | **169** |
| Python jarayoni xotirasi | 172 MB | 209 MB |

Postgres'da ro'yxat so'rovlari (64 ta kichik SQL) tezlashdi; **tahlil so'rovlari hamon sekin va baza tomonda** (`analytics/me` 311 ms SQL) — indeks/so'rovni qayta yozish kerak.

## 10. ENG MUHIM TOPILMA: baza ulanishlari (haqiqiy `gunicorn + uvicorn`, Postgres, 1 jarayon, 64 parallel so'rov)

| Konfiguratsiya | So'rov/s | CPU/so'rov | Postgres ulanishlari | Xatolar |
|---|---|---|---|---|
| **Hozirgi prod:** ASGI + `CONN_MAX_AGE=60` | **31** (qulaydi) | 42 ms | **199** (chegara!) | **872 so'rov xato, 3 500 "too many clients"** |
| ASGI + har so'rovda yangi ulanish | 113 | 14.4 ms | 0 | 0 |
| ASGI + ulanishlar puli (`pool`, 12) | 132 | 8.4 ms | 12 | 0 |
| **WSGI `gthread` (1 jarayon × 8 oqim)** | **263** | **4.5 ms** | **8** | 0 |
| **WSGI, 4 jarayon × 8 oqim** | **853–890** | **5.2–5.4 ms** | 32 | 0 |

**Sabab:** Django ASGI har parallel so'rovni alohida oqimda bajaradi, har oqim o'z baza ulanishini ochadi va `CONN_MAX_AGE=60` uni ochiq qoldiradi — ulanishlar soni cheklanmaydi. Prod'da Postgres standart 100 ulanishga ega, 3 jarayon. **Dars boshlanishida parallel so'rovlar ko'payganda bu xatoga olib keladi.** WSGI `gthread` ulanishlarni `jarayonlar × oqimlar` bilan cheklaydi va 2 barobar kam protsessor yeydi. `docker-compose.app.yml` dagi `web` xizmati shunga o'tkazildi (WebSocket `ws` xizmatida ASGI'da qoladi). **Hozirgi prod (`docker-compose.prod.yml`) hamon ASGI + CONN_MAX_AGE=60 da va bitta jarayon ham HTTP, ham WebSocket'ni ushlaydi** — u yerda shu xavf bor.

`Postgres` o'zi bu yuk ostida (890 so'rov/s): **atigi 0.39 yadro**, 155 MB. Ya'ni baza hozircha to'siq emas.

## 11. LiveKit (1.13.4, bitta tugun, 1 o'qituvchi video+ovoz har xonada, 25 tomoshabin/xona)

| Tomoshabin | LiveKit CPU (o'rtacha / p95) | Xotira (RSS) | Tomoshabinga bitreyt | Paket yo'qotish |
|---|---|---|---|---|
| 20 | 0.06 yadro | 98 MB | – | 0% |
| **250** | **0.73 / 0.93 yadro** | 554 MB | 343 kbit/s | **0%** |
| **500** | **1.57 / 2.12 yadro** | 972 MB | 349 kbit/s | **0%** |
| 1 000 | 3.0 yadro (**yuk generatori to'ldi: ~25% yo'qotish — NATIJA ISHONCHSIZ**) | 2.1 GB | 145 kbit/s | 25% |
| 500, "high" sifat | 3.1 yadro (generator to'ldi, ~50% yo'qotish — ishonchsiz) | 1.6 GB | – | – |

**Toza (ishonchli) natija: 500 tomoshabingacha.** Undan yuqorisini bu kompyuter (generator + server bir joyda, load avg 11/16) tekshira olmadi — bu LiveKit chegarasi emas, **test mashinasi chegarasi**. Chiziqli ekstrapolyatsiya (faqat 250 va 500 dan): **~3.1 yadro / 1 000 tomoshabin** (345 kbit/s da), **~2 MB xotira / tomoshabin**. 1 500 tomoshabin ≈ **4.7 yadro, ~3 GB xotira** (taxminiy, o'lchanmagan). Yuqori sifatli (1+ Mbit/s) videoda CPU/trafik oshadi — buni haqiqiy darsda frontend `adaptiveStream` (qo'shilgan) bilan tekshirish kerak.

## 12. RESURS SARFI — CPU, RAM, STORAGE (10 000 ro'yxatdan o'tgan, ~60 parallel dars, ~1 500 o'quvchi videoda, ~2 000 onlayn)

Manba: yuqoridagi o'lchovlar × frontend kodidagi so'rov chastotasi. **✓ = o'lchangan, ~ = o'lchovdan hisoblangan, ? = o'lchanmagan.**

### CPU (yadro, cho'qqi paytida)

| Komponent | Hozirgi kod | 4 ta tuzatishdan keyin* |
|---|---|---|
| API (web, WSGI): `attention` 500 so'rov/s × 5.3 ms ✓ | 2.7 | 0.5 |
| API: doska so'rovi (o'qituvchi, har 2 s) ~ | 1.1 | 0 |
| API: qolgan so'rovlar (xabarlar, jonli darslar ro'yxati, chat, sahifalar) ~ | 1.5 | 1.5 |
| API: kirish (login) to'lqini (1 500 ta 5 daqiqada, eng yomon) ~ | 0.85 | 0.85 |
| **API jami** | **~6.1** | **~2.9** |
| PostgreSQL (890 so'rov/s da 0.39 ✓) ~ | 0.6–1.0 | 0.3–0.5 |
| WebSocket (ws) — 660 yetkazish/s × 0.5 ms ✓ | 0.35 | 0.35 |
| Redis ~ | 0.1 | 0.1 |
| Yozuv: bo'lak qabul qilish (4/s × 21 ms) ✓ | 0.08 | 0.08 |
| Yozuv: MP4 o'tkazish (60 dars × 6–17 CPU-daq / 24 s) ✓ | 0.25–0.7 (cho'qqi 2 gacha) | shu |
| **APP server jami** | **~7.5–10 yadro** | **~4–5 yadro** |
| **LiveKit (MEDIA)**: 1 500 tomoshabin ~ | **~4.7** | ~4.7 (adaptive bilan kamayishi kutiladi, o'lchanmagan) |

\* tuzatishlar: (1) `web` → WSGI gthread [yangi serverlar uchun qilindi], (2) `attention` 3 s → 15 s, (3) doska so'rovini to'xtatish (WebSocket bor), (4) N+1 va tahlil so'rovlari. **RS 4000 (12 yadro) APP uchun hozirgi kodda ham yetadi (~65–85%), tuzatishdan keyin ~35–40%. RS 2000 (8 yadro) MEDIA uchun yetadi (~60%).** Test kompyuteri protsessori (AMD Zen 3+) netcup EPYC 9645 (Zen 5) dan sekinroq bo'lishi mumkin — raqamlar ehtiyotkor tomonda.

### RAM

| Komponent | Sarf |
|---|---|
| web: 8 jarayon × ~170 MB ✓ (4 jarayon = 679 MB) | ~1.4 GB |
| ws: 3 jarayon × ~210 MB ✓ + 4 000 ulanish × 34 KB ✓ | ~0.8 GB |
| PostgreSQL: ma'lumot 158 MB + 64–170 ulanish ~ | ~1.5–3 GB (`shared_buffers=8GB` ko'p, 2–4 GB yetadi) |
| Redis ✓ (1.1 MB ishlatilgan) | <0.2 GB |
| cron + transcoder + ffmpeg ~ | ~0.8 GB |
| Operatsion tizim ~ | ~0.6 GB |
| **APP jami** | **~5.5–7 GB (RS 4000 ning 32 GB'idan ~20%)** |
| **LiveKit (MEDIA)**: ~2 MB × 1 500 tomoshabin ✓/~ | **~3 GB (RS 2000 ning 16 GB'idan ~20%)** |

**Xotira hech bir serverda to'siq emas.** Asosiy to'siq — CPU.

### STORAGE

| Nima | Sarf |
|---|---|
| Baza, 10 000 foydalanuvchi boshlang'ich ✓ | **158 MB** (davomat 68 MB / 276 ming qator; bildirishnomalar 34 MB / 149 ming; chat 13 MB / 36 ming) |
| Baza o'sishi (yiliga) ~ | ~5–6 GB (eng kattasi — bildirishnomalar ~4 GB; tozalanmaydi) |
| **Dars yozuvi, 1 ta 90 daqiqalik dars** ✓ | WebM: 75–200 MB (slayd/doska; eng yomon ~800 MB) + MP4: 70–130 MB |
| 60 dars/kun uchun yozuvlar ~ | **9–20 GB/kun** (WebM+MP4, hozir) · 4–8 GB/kun (faqat MP4) |
| Yozuvlar, 1 yil ~ | **3–7 TB** (hozir) · 1.5–3 TB (faqat MP4) — **o'chirilmaydi** |
| netcup RS 4000 diski (512 GB) | **~1–4 oyga yetadi** → qo'shimcha disk yoki tashqi saqlash KERAK |

## 13. LOYIHA HOLATINING OPTIMALLIK BAHOSI

Baho — **resurs samaradorligi va yuk ostida ishonchlilik** bo'yicha, faqat o'lchovlarga tayanib.

| Yo'nalish | Ball | Asos (o'lchangan) |
|---|---|---|
| Baza ulanishlari / bir vaqtdalik | **3/10** | ASGI + `CONN_MAX_AGE=60`: 64 parallel so'rovda 199 ulanish, 3 500 xato, o'tkazuvchanlik 31 so'rov/s'ga qulaydi (prod'da hozir shunday) |
| Mijoz so'rov chastotasi (polling) | **3/10** | `attention` har 3 s (500 so'rov/s); o'qituvchi doskani har 2 s butunlay so'raydi (235 KB) — WebSocket ulangan bo'lsa ham |
| Bitta so'rov samaradorligi | **6/10** | Ko'pi 3–15 ms, 2–12 SQL; lekin darslar ro'yxati 64 SQL (N+1), tahlil 46 SQL/351 ms, davomat 158 ms |
| Real vaqt (chat/doska WebSocket) | **8/10** | 34 KB/ulanish, 0.5 ms/yetkazish, Redis qatlami; HTTP bilan bir jarayonda (yangi rejada ajratilgan) |
| Jonli video (LiveKit) | **8/10** | SFU, simulcast; 3.1 yadro/1 000 tomoshabin, 0% yo'qotish 500 gacha; `adaptiveStream` qo'shildi (haqiqiy darsda tasdiqlanmagan) |
| Dars yozuvi quvuri | **8/10** | Yozish brauzerda (server CPU yo'q); bo'lak 21 ms; birlashtirish 2 s; MP4 6–17 CPU-daq; takrorlanishdan himoya va avto-tiklash bor. Kamchilik: WebM o'chirilmaydi |
| Ma'lumotlar bazasi (sxema/indeks) | **7/10** | Yengil so'rovlar Postgres'ni deyarli yuklamaydi (0.39 yadro/890 so'rov/s); baza ixcham; og'ir agregatlar (tahlil) SQL-bog'liq |
| Saqlash (disk) boshqaruvi | **4/10** | Yozuvlar cheksiz o'sadi, WebM+MP4 ikkalasi saqlanadi, muddat/tozalash yo'q, faqat mahalliy disk |
| Autentifikatsiya narxi | **7/10** | Kirish 169 ms (PBKDF2, xavfsizlik uchun to'g'ri); yangilash 15 ms; IP bo'yicha throttle maktab (bitta IP) uchun xavfli |
| Joylashtirish / kuzatuv | **5/10** | Compose bor, yangi 2-serverli reja yozilgan lekin sinalmagan; monitoring faqat konteyner namunasi; zaxira tiklash sinalmagan |

### **UMUMIY: 5.5 / 10** (hozirgi holat)

**Nega ayni shu:** asos (arxitektura, realtime, video, yozuv) yaxshi qurilgan, lekin **uchta o'lchangan muammo** yuk ostida ishonchlilikni buzadi: baza ulanishlari, 3 soniyalik polling va doska polling'i. Ular tuzatilsa va saqlash boshqarilsa, **taxminan 8/10** bo'ladi:

1. `web` ni WSGI gthread (yoki ulanishlar puli) ga o'tkazish — **yangi serverlar uchun qilindi** (`docker-compose.app.yml`); eski prod'da hali yo'q.
2. `attention` so'rovini 3 s dan 15–20 s ga chiqarish (yoki LiveKit data kanaliga) — frontend.
3. O'qituvchi doska so'rovini to'xtatish (WebSocket ulangan paytda) — frontend.
4. Darslar ro'yxati N+1 (3 SQL/dars) va `analytics/me`, `trends`, `dashboard/teacher` so'rovlarini tezlashtirish — backend.
5. MP4 tayyor bo'lgach WebM'ni o'chirish, yozuvlar uchun qo'shimcha disk/tashqi saqlash.

**O'lchanmaganlar (halol):** (a) 1 000+ LiveKit tomoshabin (test kompyuteri chegarasi); (b) netcup EPYC 9645 protsessorida haqiqiy tezlik; (c) Redis orqali chat yetkazish narxi; (d) haqiqiy prod yuki (eski serverdan `docker stats` natijasi hali kelmagan); (e) cron ishlarining narxi.
