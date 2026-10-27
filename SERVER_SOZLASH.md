# Yangi netcup serverlarini sozlash — qadamma-qadam qo'llanma

**Serverlar:** **RS 4000** (12 yadro, 32 GB) va **RS 2000** (8 yadro, 16 GB).
Hamma tayyor fayllar loyihada bor: `docker-compose.app.yml`, `docker-compose.media.yml`, `deploy/app/`, `deploy/media/`, `deploy/new/`, `.env.app.example`, `.env.media.example`.
**Eslatma:** bu fayllar yozilgan va sintaksisi tekshirilgan, lekin **haqiqiy serverda hali ishga tushirilmagan.** Birinchi ishga tushirishda kichik xato chiqishi mumkin — shuning uchun avval **sinov domenida** ishga tushiramiz, eski serverga tegmaymiz.

---

## 0. Qaysi server nima uchun

| Server | Roli | Nega |
|---|---|---|
| **RS 4000** → **APP** | Sayt (API), chat, baza (Postgres), Redis, fon ishlari, yozuv fayllari | Baza va ilova ko'p xotira (RAM) va yadro talab qiladi: 32 GB |
| **RS 2000** → **MEDIA** | Faqat jonli dars video serveri (LiveKit) | Faqat tarmoq va protsessor kerak; 8 yadro ≈ bir vaqtda ~1 000–1 500 o'quvchi videoda (hisob-kitob, sinovdan keyin aniq bo'ladi) |

Bu 10 000 foydalanuvchining dastlabki bosqichi uchun yetarli bo'lishi kerak (hisob-kitob bo'yicha). MEDIA to'lib qolsa uni RS 4000 ga ko'taramiz (netcup'da kattasiga o'tish mumkin, kichikka qaytib bo'lmaydi).
**Ikkala serverni ham BIR XIL joyda (Vena yoki Nyurnberg) oling** — o'zaro aloqa tez va arzon bo'ladi.

---

## 1. Sizga kerak bo'ladigan ruxsatlar (access) — ro'yxat

**Hech qachon parolni chatga, Telegramga yoki fayl ichiga yozmang.** Parollar faqat parol menejeri (Bitwarden/1Password) yoki bevosita sizga yuboriladigan bir martalik havola orqali beriladi.

| № | Nima kerak | Kimdan | Nima uchun | Qanday beriladi |
|---|---|---|---|---|
| 1 | **Serverlarning IP manzillari** (ikkala server) | Team lead (buyurtmadan keyin) | Ulanish uchun | netcup yuboradigan xat yoki **SCP** (Server Control Panel) dan ko'chirib berish |
| 2 | **Server paneli (SCP)** ga kirish: `servercontrolpanel.de` | Team lead | OS o'rnatish, qayta ishga tushirish, **konsol (VNC)** — SSH buzilsa yagona qutqaruvchi | netcup foydalanuvchi qo'shishga ruxsat bersa — shaxsiy hisob; bo'lmasa team lead birga o'tiradi |
| 3 | **SSH kirish** (root parol yoki SSH kalit) | Siz o'zingiz kalit yaratasiz, team lead o'rnatishda ko'rsatadi | Serverga kirish | 3-bo'limdagi kalit — **faqat OCHIQ kalit** (`.pub`) beriladi |
| 4 | **DNS boshqaruvi** (`thesofmebel.uz` domeni qayerda boshqariladi — registrator yoki Cloudflare) | Team lead yoki domen egasi | `edu2`, `lk`, keyin `edu` yozuvlarini yangi IP'larga qo'yish | Panelga kirish yoki siz aytgan yozuvlarni o'zi qo'yadi (**qaysi yozuvlar — 6-bo'lim**) |
| 5 | **GitHub repo ruxsati** (`krv006/Education-Tech-Platform`) — **Deploy key** qo'shish huquqi | Repo egasi (krv006) | Server kodni `git pull` qilishi uchun (faqat o'qish kaliti) | Repo → Settings → Deploy keys → serveringizning ochiq kaliti (7-bo'lim) |
| 6 | **Eski server (Contabo)** ga root SSH | Sizda bor (hozir ham kirasiz) | `.env`, baza va fayllarni ko'chirish | — |
| 7 | **Eski serverdagi `.env` va Firebase JSON** | Eski serverdan o'zingiz olasiz | Yangi serverda **bir xil** kalitlar (SECRET_KEY, VAPID, OpenAI, LiveKit) bo'lishi shart | `scp` bilan (8-bo'lim) — **xabarlarda ko'rsatilmaydi** |
| 8 | netcup **hisobi 2FA** (ikki bosqichli tasdiq) | Team lead | Hisobni o'g'irlashdan himoya | Team lead yoqadi |

**Kamida kerak (bugun boshlash uchun):** №1, №2 (yoki team lead yonida), №3, №6, №7. №4 va №5 — ertaga ham bo'ladi.

---

## 2. Team lead bugun nimani tanlab buyurtma qiladi (aytib qo'ying)

- Modellar: **RS 4000 G12.5** va **RS 2000 G12.5**.
- **Joy:** ikkalasi uchun ham **Vena** yoki **Nyurnberg** (bir xil).
- **Operatsion tizim:** **Ubuntu 24.04 LTS**.
- **IPv4 + IPv6** (IPv4 shart).
- Shartnoma muddati: **birinchi buyurtmada 30 kunlik pul qaytarish bor** — avval 1 yoki 12 oy ni tanlang; 24 oylikni sinovdan keyin (shartnomani keyin o'zgartirish mumkinligini netcup'dan so'rang).
- NDS (VAT) ma'lumotini kompaniya ma'lumotlari bilan to'g'ri kiriting.
- **Savol (netcup qo'llab-quvvatlashiga):** "3 TB/24 soat trafik chegarasi faqat chiquvchimi yoki kiruvchi+chiquvchi birgami?"

---

## 3. Bugun sizning kompyuteringizda: SSH kalit yaratish (5 daqiqa)

Windows PowerShell'da (bir marta):

```powershell
ssh-keygen -t ed25519 -C "mathu-ishxona"
```
(Enter, Enter, Enter — parol ixtiyoriy, lekin qo'ysangiz yaxshi.) Ochiq kalitni ko'rish:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
```
Chiqqan **bitta satr** (`ssh-ed25519 AAAA... mathu-ishxona`) — **ochiq kalit**. Shuni team leadga bering (u SCP'da OS o'rnatishda SSH kalit sifatida qo'yadi) yoki keyingi qadamda o'zingiz qo'shasiz. **`id_ed25519` (`.pub`siz) — maxfiy kalit, uni hech kimga bermang.**

---

## 4. Serverga birinchi kirish

Serverlar tayyor bo'lgach (SCP'da Ubuntu 24.04 o'rnatilgan, IP bor):

```powershell
ssh root@<SERVER_IP>
```
Birinchi marta "fingerprint" so'rasa `yes`. **Ikkala server uchun alohida** qiling. Kira olmasangiz: SCP → server → **konsol (Screen/VNC)** orqali ko'ring.

Agar SCP'da kalit qo'yilmagan, parol bilan kirgan bo'lsangiz — ochiq kalitni qo'shing (kompyuteringizdan):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@<SERVER_IP> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

---

## 5. Serverni tayyorlash (har ikkala serverda, `bootstrap.sh`)

Bu skript yangilaydi, **Docker** o'rnatadi, `deploy` foydalanuvchisini yaratadi, **firewall**, **fail2ban**, avtomatik xavfsizlik yangilanishlarini sozlaydi.

Kodni serverga olishning eng oddiy yo'li — hozircha skriptning o'zini nusxalash (repo yopiq bo'lgani uchun). Kompyuteringizdan (loyiha papkasida):

```powershell
scp deploy/new/bootstrap.sh root@<APP_IP>:/root/
```

APP serverda:

```bash
bash /root/bootstrap.sh app
```
MEDIA serverda (o'sha skript, boshqa rol):

```bash
bash /root/bootstrap.sh media
```
Tugagach **yangi terminalda** tekshiring (parolsiz kirishi kerak):

```powershell
ssh deploy@<SERVER_IP>
```
Kirsa — serverda skriptni yana bir marta `--lock-ssh` bilan ishga tushiring (parol va root bilan kirishni o'chiradi). **Kira olmasangiz bu qadamni QILMANG.**

```bash
sudo bash /root/bootstrap.sh app --lock-ssh
```

---

## 6. DNS (team lead yoki siz)

Ikkita yangi yozuv (**A** tur), TTL 300:

| Yozuv | Qiymat | Nima uchun |
|---|---|---|
| `edu2.thesofmebel.uz` | **APP** server IP'si | Sinov: yangi serverni eski sayt buzilmasdan tekshirish |
| `lk.thesofmebel.uz` | **MEDIA** server IP'si | Jonli dars serveri (haqiqiy ishlatiladi) |

`edu.thesofmebel.uz` ga **hozircha tegmang** (u eski serverda). Ko'chib o'tish kuni (10-bo'lim) uni yangi APP'ga yo'naltiramiz.
Tekshirish: `nslookup lk.thesofmebel.uz` — MEDIA IP'sini ko'rsatishi kerak.

---

## 7. Loyihani serverga olish (APP va MEDIA ikkalasida)

`deploy` foydalanuvchisi sifatida (`ssh deploy@<IP>`). Repo yopiq bo'lgani uchun **Deploy key** ishlatamiz (faqat o'qish; parol/token serverda saqlanmaydi):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "deploy-$(hostname)"
```
```bash
cat ~/.ssh/github_deploy.pub
```
Chiqqan kalitni GitHub'da: `krv006/Education-Tech-Platform` → **Settings → Deploy keys → Add deploy key** (Allow write access **QO'YMANG**). Repo egasi qo'shadi. So'ng:

```bash
printf 'Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
```
```bash
git clone git@github.com:krv006/Education-Tech-Platform.git /var/www/edu_platform
```
(Repo asosiy tarmog'i `main`.) Kelgusi yangilashlar: `cd /var/www/edu_platform && git pull`.

---

## 8. MEDIA serverni ishga tushirish (LiveKit) — avval shuni qiling

Eski serverdan **LiveKit kalitlarini** oling (`.env` dagi `LIVEKIT_API_KEY` va `LIVEKIT_API_SECRET` qiymatlari — **ikkala yangi serverda aynan shular** bo'lishi shart):

```bash
ssh root@<ESKI_SERVER> "grep '^LIVEKIT_' /var/www/edu_platform/.env"
```
MEDIA serverda:

```bash
cd /var/www/edu_platform && cp .env.media.example .env && nano .env
```
`LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LK_DOMAIN=lk.thesofmebel.uz` ni to'ldiring (Ctrl+O, Enter, Ctrl+X). Ishga tushirish:

```bash
docker compose -f docker-compose.media.yml up -d
```
Tekshirish:
```bash
docker compose -f docker-compose.media.yml ps
```
```bash
docker compose -f docker-compose.media.yml logs --tail=30 caddy
```
Caddy logida "certificate obtained" (sertifikat olindi) chiqishi kerak — buning uchun `lk.` DNS yozuvi ishlayotgan bo'lishi shart. Brauzerdan `https://lk.thesofmebel.uz` ni oching: LiveKit javobi ("OK" yoki shunga o'xshash) chiqsa tayyor.
Agar `manifest unknown` xatosi chiqsa: `.env` da `LIVEKIT_VERSION=1.13.4` (`v`siz) qiling.

---

## 9. APP serverni ishga tushirish

Eski serverdan `.env` ni **to'g'ridan-to'g'ri** yangi serverga nusxalang (xabar orqali emas). Buning uchun eski serverga kompyuteringizdan **agent uzatish (`-A`)** bilan kiring — shunda sizning kalitingiz yangi serverga ham o'tadi:

```powershell
ssh -A root@<ESKI_SERVER>
```
Eski serverdan turib:

```bash
scp /var/www/edu_platform/.env deploy@<APP_IP>:/var/www/edu_platform/.env.old
```
(Agar `-A` ishlamasa: faylni avval o'z kompyuteringizga `scp` qiling, keyin yangi serverga. Ishlatib bo'lgach APP serverda `shred -u /var/www/edu_platform/.env.old` bilan o'chiring.)
APP serverda `.env.app.example` asosida yangi `.env` yarating va eski `.env` dan **kalitlarni ko'chiring** (`SECRET_KEY`, `VAPID_*`, `OPENAI_*`, `LIVEKIT_*` va hokazo):

```bash
cd /var/www/edu_platform && cp .env.app.example .env && nano .env
```
O'zgartiriladigan qiymatlar (sinov bosqichi):
- `DOMAIN=edu2.thesofmebel.uz`, `ALLOWED_HOSTS=edu2.thesofmebel.uz`, `CSRF_TRUSTED_ORIGINS=https://edu2.thesofmebel.uz`, `CORS_ALLOWED_ORIGINS=https://edu2.thesofmebel.uz`
- `LIVEKIT_URL=wss://lk.thesofmebel.uz` (`LIVEKIT_API_URL` ni **qo'shmang**)
- `POSTGRES_PASSWORD` — yangi kuchli parol
- APP uchun RS 4000 (32 GB) olingan, shuning uchun baza xotira sozlamalari standartda qoladi. (Agar APP vaqtincha RS 2000 ga tushsa: `PG_SHARED_BUFFERS=4GB`, `PG_EFFECTIVE_CACHE=10GB`.)

Avval bazani ko'taring:

```bash
docker compose -f docker-compose.app.yml up -d --build db redis
```
(Birinchi yig'ish 3–6 daqiqa.) Eski serverdagi **bazani ko'chirish** (yana eski serverda, `ssh -A` bilan kirilgan holda dump):

```bash
docker exec edu_platform-db-1 pg_dump -U edtech -d edtech -Fc > /root/edtech.dump
```
```bash
scp /root/edtech.dump deploy@<APP_IP>:/tmp/edtech.dump
```
APP serverda tiklash:

```bash
cat /tmp/edtech.dump | docker compose -f docker-compose.app.yml exec -T db pg_restore -U edtech -d edtech --no-owner
```
(Ba'zi "already exists" ogohlantirishlari bo'lishi mumkin — xato emas, agar oxirida jadvallar bor bo'lsa.) Endi hammasini ko'taring:

```bash
docker compose -f docker-compose.app.yml up -d --build
```
Holat va loglar:

```bash
docker compose -f docker-compose.app.yml ps
```
```bash
docker compose -f docker-compose.app.yml logs --tail=50 web
```
Tekshirish (brauzerda): `https://edu2.thesofmebel.uz/api/docs/` ochilishi kerak (Swagger).

**Fayllarni ko'chirish** (yuklangan rasm/vazifa fayllari va dars yozuvlari) — eski serverdan **APP serverga** (`rsync`, eski serverdan turib, `ssh -A` bilan; hajmi katta bo'lishi mumkin — `tmux` ichida ishga tushiring):

```bash
rsync -az /var/lib/docker/volumes/edu_platform_media/_data/ deploy@<APP_IP>:/tmp/media/
```
```bash
rsync -az /var/lib/docker/volumes/edu_platform_recordings/_data/ deploy@<APP_IP>:/tmp/recordings/
```
APP serverda ularni volume'larga qo'yish:

```bash
sudo rsync -a /tmp/media/ /var/lib/docker/volumes/edu_platform_media/_data/
```
```bash
sudo rsync -a /tmp/recordings/ /var/lib/docker/volumes/edu_platform_recordings/_data/
```
(Volume nomlari loyiha papkasi nomidan olinadi: papka `edu_platform` bo'lsa `edu_platform_media`. Tekshirish: `docker volume ls`.)

---

## 10. Sinov ro'yxati (ko'chib o'tishdan oldin)

1. `https://edu2.thesofmebel.uz/api/docs/` ochiladi; `https://edu2.thesofmebel.uz/api/health/` — `ok`.
2. Login qilish ishlaydi (bu yangi bazada eski foydalanuvchilar bilan).
3. **Jonli dars sinovi:** ikki qurilmada (o'qituvchi + o'quvchi) dars — video, ovoz, doska, chat. Frontend sinov domenini bilishi uchun Vercel'da preview muhitida API manzilini `edu2` ga qo'ying yoki test akkaunt bilan sinang.
4. Dars yozuvi yuklanadi, MP4 ga o'tadi (`docker compose -f docker-compose.app.yml logs --tail=30 transcoder`).
5. `docker stats` — CPU/RAM me'yorida.
6. **Zaxira nusxa** (11-bo'lim) ishlaydi va tiklash sinab ko'rilgan.

---

## 11. Zaxira nusxa (APP serverda)

`deploy/new/backup.sh` har kecha bazaning nusxasini oladi va **MEDIA serverga** ko'chiradi (boshqa mashina). Sozlash yo'riqnomasi faylning boshida. Qisqasi: kalit yaratish, MEDIA'ga qo'shish, `crontab -e` ga bitta qator.
**Tiklashni albatta bir marta sinab ko'ring** — aks holda zaxira bor-yo'qligi noma'lum.

---

## 12. Ko'chib o'tish kuni (cutover) — kechqurun, dars bo'lmagan paytda

1. Bir kun oldin DNS'da `edu.thesofmebel.uz` TTL ni 300 s ga tushiring.
2. Eski serverda saytni vaqtincha to'xtating (yozuv to'xtasin): `docker compose -f docker-compose.prod.yml stop backend cron`.
3. **Oxirgi** bazani qayta dump qiling va yangi APP'ga tiklang (9-bo'lim, YANGI serverdagi bazani avval tozalab: `docker compose -f docker-compose.app.yml exec -T db psql -U edtech -d edtech -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` — **faqat yangi serverda**, hech qachon eskisida!), fayllarni `rsync -a` bilan yangilang.
4. APP `.env` da `DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` ni `edu.thesofmebel.uz` ga o'zgartiring: `docker compose -f docker-compose.app.yml up -d`.
5. DNS: `edu.thesofmebel.uz` → **APP IP**. Caddy sertifikatni bir necha soniyada oladi.
6. Tekshiring: login, chat, jonli dars. Muammo bo'lsa — DNS'ni **eski IP**ga qaytaring (eski server o'chirilmagan).
7. 1–2 hafta eski serverni **o'chirmasdan** saqlang.

---

## 13. Kundalik ishlar

| Nima | Buyruq (APP serverda, `/var/www/edu_platform` ichida) |
|---|---|
| Yangilash | `git pull && docker compose -f docker-compose.app.yml up -d --build` |
| Holat | `docker compose -f docker-compose.app.yml ps` |
| Log | `docker compose -f docker-compose.app.yml logs --tail=100 web` (yoki `ws`, `cron`, `transcoder`, `caddy`) |
| Resurs | `docker stats --no-stream` va `htop` |
| Disk | `df -h /` va `docker system df` |
| Admin yaratish | `docker compose -f docker-compose.app.yml exec web python manage.py createsuperuser` |
| MEDIA yangilash | `git pull && docker compose -f docker-compose.media.yml up -d` |

**Ogohlantirishlar:**
- **Disk:** yozuvlar (`recordings`) diskni to'ldiradi (~21 GB/kun, 60 yozilgan dars/kun bo'lsa). RS 4000 da 512 GB. Haftasiga bir marta `df -h` ni tekshiring; to'lishiga yaqinlashsa netcup'da qo'shimcha disk (Local Block Storage) buyurtma qiling.
- **Trafik:** 24 soatda 3 TB dan oshsa tezlik 300 Mbit/s ga tushadi (MEDIA'da ehtiyot bo'ling).
- **Firewall:** Docker o'zi ochgan portlarni `ufw` dan chetlab o'tadi — shuning uchun compose'da faqat kerakli portlar ochiq (baza va Redis ochilmagan). Yangi port qo'shsangiz ehtiyot bo'ling.
- **SSH'dan chiqib ketib qolsangiz:** SCP'dagi konsol (VNC) orqali kiring.

---

## 14. Muammo bo'lsa menga yuboring

Quyidagilarni (parollarsiz!) yuboring:
- `docker compose -f docker-compose.app.yml ps` natijasi
- `docker compose -f docker-compose.app.yml logs --tail=80 <xizmat>` natijasi
- Xato matni va qaysi qadamda chiqqani
