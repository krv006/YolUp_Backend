# Server arxitekturasi — oddiy tilda

Bu hujjat **nima qayerda ishlashi, nega shunday va nima yiqilsa nima bo'lishini** tushuntiradi. Sozlash qadamlari: `SERVER_SOZLASH.md`. O'lchovlar: `SERVER_OLCHOV_NATIJALARI.md`.

## 3 ta asosiy qoida
1. **Jonli dars hech qachon och qolmasin.** Video, chat va darsga kirish eng muhim. Boshqa hech narsa ularning resursini yeb qo'ymasligi kerak.
2. **Kechiktirsa bo'ladigan ishlarga chegara qo'yamiz.** Yozuvni MP4 qilish 1 soat kechiksa hech narsa bo'lmaydi, shuning uchun u har doim cheklangan yadro va eng past ustuvorlik bilan ishlaydi.
3. **Bitta serverning muammosi ikkinchisini yiqitmasin.**

## Ikki server

```
Foydalanuvchi (telefon / kompyuter)
        │
        ├──► edu.thesofmebel.uz ──► APP server (RS 2000: 8 yadro, 16 GB)
        │                           ├─ Caddy     : kirish eshigi (HTTPS)
        │                           ├─ web       : sayt API
        │                           ├─ ws        : chat, doska (real vaqt)
        │                           ├─ Postgres  : baza
        │                           ├─ Redis     : tezkor xabar almashish
        │                           └─ cron      : eslatmalar, AI, avto-yakunlash
        │                                │  yozuv so'rovlari (/api/v1/lessons/<id>/recording...)
        │                                ▼  yopiq kanal (WireGuard 10.10.0.x)
        └──► lk.thesofmebel.uz  ──► MEDIA server (RS 4000: 12 yadro, 32 GB + qo'shimcha disk)
                                    ├─ LiveKit     : jonli dars video/ovoz      (eng ustuvor)
                                    ├─ rec         : yozuv API'si (bo'lak qabul qilish, birlashtirish, ko'rsatish)
                                    ├─ rec-cron    : qotgan yozuvni tiklash, yetim fayl tozalash, disk ogohlantirishi
                                    ├─ transcoder  : yozuvni MP4 qiladi        (eng past ustuvor, 3 yadro bilan cheklangan)
                                    └─ yozuv fayllari (katta ma'lumot shu yerda)
```

**Nega shunday bo'lindi:** eng katta yuk — jonli dars va yozuv. Shuning uchun kuchli server (RS 4000) ularga berildi. Baza kichik (0.16 GB, yiliga ~6 GB), uni sayt bilan bir joyda saqlash saytni tez qiladi. MEDIA'dagi `rec` bazaga yopiq kanal orqali ulanadi.

## Funksiyalarning og'irligi va joyi
| Funksiya | Nimani yeydi | Qachon | Joyi |
|---|---|---|---|
| Jonli video (LiveKit) | CPU va tarmoq | dars boshlanishida to'lqin | **MEDIA** |
| Yozuv bo'laklarini qabul qilish | disk yozish, CPU kam | dars davomida doimiy | **MEDIA** |
| Yozuvni MP4 qilish | CPU (og'ir) | dars tugagach to'lqin, kechiktirsa bo'ladi | **MEDIA**, 3 yadro bilan cheklangan |
| Yozuvni tomoshabinga berish | tarmoq (katta fayl) | doimiy | **MEDIA** (keyin Cloudflare) |
| Yozuv fayllari | disk | o'sib boradi | **MEDIA** (+ qo'shimcha disk) |
| Sayt API, login | CPU | to'lqin | **APP** |
| Chat, doska (WebSocket) | ko'p ulanish, CPU kam | doimiy | **APP** |
| Baza, Redis | RAM, CPU kam | doimiy | **APP** |
| Fon ishlari, AI, zaxira | CPU kam | kechiktirsa bo'ladi | **APP** |

## Ustuvorlik qanday ta'minlanadi (MEDIA serverda)
| Xizmat | CPU ustuvorligi (`cpu_shares`) | Yadro chegarasi |
|---|---|---|
| LiveKit | 4096 (eng yuqori) | cheklanmagan |
| rec (yozuv API) | 1024 | 3 yadro |
| rec-cron | 256 | – |
| transcoder | 256 + `nice 15` | 3 yadro |

CPU yetmay qolsa, Linux avval LiveKit'ga beradi, yozuvni MP4 qilish esa kutadi.

## Qanday holatlar bo'lishi mumkin
| Holat | Nima bo'ladi | Tayyorgarlik |
|---|---|---|
| 60 dars bir vaqtda boshlanadi | 1 500 o'quvchi 2–3 daqiqada kiradi: login, token, video | refresh token 7 kun (login kam); kirish tokeni arzon (~10 ms); LiveKit alohida serverda; `THROTTLE_AUTH` sozlanadi |
| 60 dars bir vaqtda tugaydi | 60 ta birlashtirish va MP4, ~5 soat navbat | navbat bitta-bitta, transcoder cheklangan; qotib qolsa avto-tiklash (`recover_recordings`); navbat vaqtida WebM ko'rinadi |
| Test yoki vazifa muddati tugashi | hamma bir daqiqada topshiradi | baza ulanishlari puli; AI alohida jarayonda. **Yuk ostida o'lchanmagan** |
| Bitta katta dars (500+) | bir xona bitta serverda | MEDIA'da zaxira bor (500 tomoshabin ≈ 1.6 yadro o'lchangan) |
| Maktab Wi-Fi'si (bitta IP) | ko'p o'quvchi bir IP'dan, kirish bloklanadi | `THROTTLE_AUTH` ni oshirish (`.env`) |
| Disk to'lishi | yozuvlar 9–20 GB/kun | `check_disk`: 80% va 90% da adminlarga bildirishnoma; `prune_recordings`; keyin Cloudflare |
| Kurs o'chiriladi | yozuv fayllari MEDIA'da qoladi | `prune_orphan_recordings` (har soat) yetim fayllarni o'chiradi (48 soatdan eski, bir martada ≤50) |
| Tarmoq limiti (3 TB/kun, so'ng 300 Mbit/s) | video va yozuv ko'rish MEDIA'dan chiqadi | yozuv ko'rishni Cloudflare'ga chiqarish (keyin) |
| Hujum, bot | login taxmin qilish, DDoS | sayt API oldiga Cloudflare (keyin). LiveKit oldiga qo'yib bo'lmaydi (video to'g'ridan-to'g'ri ulanadi) |
| Dars paytida deploy | chat uziladi | darsdan tashqari vaqtda; video uzilmaydi, chunki LiveKit alohida |

## Biri yiqilsa nima bo'ladi
| Yiqilgan | Ishlayveradi | Ishlamaydi |
|---|---|---|
| **MEDIA** | sayt, chat, baza, doska | yangi jonli dars videosi, yozuv yuklash va ko'rish. Brauzer yozuv bo'laklarini saqlab turadi va keyin yuboradi |
| **APP** | allaqachon ulangan video (LiveKit mustaqil) | saytga kirish, darsga qo'shilish, chat, yozuv API'si (baza yo'q) |
| **WireGuard kanali** | APP'ning hammasi, LiveKit | faqat yozuv bilan bog'liq: MEDIA'dagi `rec` bazaga ulana olmaydi |

**Eng xavfli nuqta:** baza APP'da bitta. Himoya: har kecha `backup.sh` bazani MEDIA serverga ko'chiradi. Tiklashni bir marta sinab ko'rish kerak.

## Ikki serverda yozuv fayllari qanday ishlaydi (muhim texnik joy)
- O'qituvchi brauzeri yozuv bo'laklarini saytga yuboradi. APP'dagi Caddy `…/recording…` so'rovlarini MEDIA'dagi `rec` ga yo'naltiradi, `rec` ularni diskka yozadi.
- Darsni **majburan yakunlash** (`auto_finish_expired_lessons`) APP serverda bajariladi, lekin fayllar u yerda yo'q. Shu uchun `RECORDINGS_LOCAL=0`: APP faqat belgilarni qo'yadi, birlashtirishni MEDIA'dagi `recover_recordings` bajaradi (fayl 5 daqiqa o'zgarmagach).
- Kurs o'chirilsa baza yozuvi o'chadi, fayllar MEDIA'da qoladi → `prune_orphan_recordings` tozalaydi. Xavfsizlik: bazada hech bir yozuv qatori bo'lmasa hech narsa o'chirmaydi.

## O'sish yo'li
1. Hozir: 10 000 foydalanuvchi, shu 2 server.
2. APP to'lsa: RS 2000 → RS 4000 (yoki RS 8000). `.env` da `PG_SHARED_BUFFERS=8GB`, `PG_EFFECTIVE_CACHE=20GB`.
3. MEDIA CPU to'lsa: ikkinchi LiveKit serveri qo'shiladi (LiveKit Redis orqali ko'p tugunni qo'llab-quvvatlaydi).
4. Disk to'lsa: yozuvlar Cloudflare R2 ga (ko'rish trafigi ham ketadi). Bu kod o'zgarishini talab qiladi (fayllarni diskka emas R2 ga yozish) — hozir qilinmagan.

## Hali tekshirilmagan (halol)
- Bu fayllar **haqiqiy serverda hali ishga tushirilmagan**. Birinchi ishga tushirishda kichik xato chiqishi mumkin, shuning uchun avval `edu2` sinov domenida sinaymiz.
- WireGuard kanali orqali bazaga ulanish tezligi o'lchanmagan (bir xil shahar ichida ~1 ms kutiladi).
- Caddy'ning yozuv so'rovlarini yo'naltirish qoidasi (`@recording`) sintaksis jihatdan to'g'ri deb hisoblangan, lekin Caddy'da ishga tushirib ko'rilmagan.
- 1 500 tomoshabinli LiveKit yuki (o'lchangan faqat 500 gacha) va netcup protsessorining haqiqiy tezligi.
