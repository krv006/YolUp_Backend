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
