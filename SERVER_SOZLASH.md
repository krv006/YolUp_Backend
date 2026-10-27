# Yangi netcup serverlarini sozlash — qadamma-qadam qo'llanma

**Serverlar:**
- **RS 2000** (8 yadro, 16 GB) = **APP** (CORE): sayt, chat, baza, Redis, fon ishlari.
- **RS 4000** (12 yadro, 32 GB) = **MEDIA**: jonli dars video, dars yozuvlari (qabul qilish, birlashtirish, MP4 ga o'tkazish, saqlash).

Nega shunday: eng katta yuk — jonli dars va yozuv. Shuning uchun kuchliroq server (RS 4000) ularga beriladi. Arxitekturaning to'liq tushuntirishi: `SERVER_ARXITEKTURA.md`.

Hamma tayyor fayllar loyihada bor: `docker-compose.app.yml`, `docker-compose.media.yml`, `deploy/app/`, `deploy/media/`, `deploy/new/` (bootstrap, wireguard, backup), `.env.app.example`, `.env.media.example`.
**Eslatma:** bu fayllar yozilgan va sintaksisi tekshirilgan, lekin **haqiqiy serverda hali ishga tushirilmagan.** Birinchi ishga tushirishda kichik xato chiqishi mumkin — shuning uchun avval **sinov domenida** (`edu2`) ishga tushiramiz, eski serverga tegmaymiz.

---

## 0. Qaysi server nima uchun

| Server | Roli | Ichida nimalar |
|---|---|---|
| **RS 2000** → **APP** | Sayt va ma'lumotlar | Caddy (kirish eshigi), `web` (API), `ws` (chat/doska), Postgres, Redis, `cron` (eslatmalar, AI, avto-yakunlash) |
| **RS 4000** → **MEDIA** | Video va yozuvlar | LiveKit (jonli video), `rec` (yozuv API'si), `rec-cron` (tiklash, tozalash), `transcoder` (MP4), yozuv fayllari |

Ikki server o'rtasida **yopiq kanal (WireGuard)**: baza va Redis internetga ochilmaydi, MEDIA serverdagi `rec` ularga shu kanal orqali ulanadi. Yozuv bilan bog'liq so'rovlarni (`/api/v1/lessons/<id>/recording...`) APP serverdagi Caddy MEDIA serverdagi `rec` ga yo'naltiradi.

**Ikkala serverni ham BIR XIL joyda (Vena yoki Nyurnberg) oling** — o'zaro aloqa tez bo'ladi.

---

## 1. Sizga kerak bo'ladigan ruxsatlar (access) — ro'yxat

**Hech qachon parolni chatga, Telegramga yoki fayl ichiga yozmang.** Parollar faqat parol menejeri (Bitwarden/1Password) yoki bevosita sizga yuboriladigan bir martalik havola orqali beriladi.

| № | Nima kerak | Kimdan | Nima uchun | Qanday beriladi |
|---|---|---|---|---|
| 1 | **Serverlarning IP manzillari** (ikkala server) | Team lead (buyurtmadan keyin) | Ulanish uchun | netcup yuboradigan xat yoki **SCP** (Server Control Panel) dan ko'chirib berish |
| 2 | **Server paneli (SCP)** ga kirish: `servercontrolpanel.de` | Team lead | OS o'rnatish, qayta ishga tushirish, **konsol (VNC)** — SSH buzilsa yagona qutqaruvchi | netcup foydalanuvchi qo'shishga ruxsat bersa — shaxsiy hisob; bo'lmasa team lead birga o'tiradi |
| 3 | **SSH kirish** (root parol yoki SSH kalit) | Siz o'zingiz kalit yaratasiz, team lead o'rnatishda ko'rsatadi | Serverga kirish | 3-bo'limdagi kalit — **faqat OCHIQ kalit** (`.pub`) beriladi |
| 4 | **DNS boshqaruvi** (`thesofmebel.uz` domeni qayerda boshqariladi — registrator yoki Cloudflare) | Team lead yoki domen egasi | `edu2`, `lk`, keyin `edu` yozuvlarini yangi IP'larga qo'yish | Panelga kirish yoki siz aytgan yozuvlarni o'zi qo'yadi (**qaysi yozuvlar — 7-bo'lim**) |
| 5 | **GitHub repo ruxsati** (`krv006/Education-Tech-Platform`) — **Deploy key** qo'shish huquqi | Repo egasi (krv006) | Server kodni `git pull` qilishi uchun (faqat o'qish kaliti) | Repo → Settings → Deploy keys → serveringizning ochiq kaliti (8-bo'lim) |
| 6 | **Eski server (Contabo)** ga root SSH | Sizda bor (hozir ham kirasiz) | `.env`, baza va fayllarni ko'chirish | — |
| 7 | **Eski serverdagi `.env` va Firebase JSON** | Eski serverdan o'zingiz olasiz | Yangi serverda **bir xil** kalitlar (SECRET_KEY, VAPID, OpenAI, LiveKit) bo'lishi shart | `scp` bilan (9-bo'lim) — **xabarlarda ko'rsatilmaydi** |
| 8 | netcup **hisobi 2FA** (ikki bosqichli tasdiq) | Team lead | Hisobni o'g'irlashdan himoya | Team lead yoqadi |

**Kamida kerak (bugun boshlash uchun):** №1, №2 (yoki team lead yonida), №3, №6, №7. №4 va №5 — ertaga ham bo'ladi.

---

## 2. Team lead bugun nimani tanlab buyurtma qiladi (aytib qo'ying)

- Modellar: **RS 2000 G12.5** (APP) va **RS 4000 G12.5** (MEDIA).
- **Joy:** ikkalasi uchun ham **Vena** yoki **Nyurnberg** (bir xil).
- **Operatsion tizim:** **Ubuntu 24.04 LTS**.
- **IPv4 + IPv6** (IPv4 shart).
- **MEDIA (RS 4000) uchun qo'shimcha disk** (netcup "Local Block Storage" yoki kattaroq): yozuvlar kuniga 9–20 GB qo'shadi, 512 GB 1–4 oyda to'ladi.
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

Kodni serverga olishning eng oddiy yo'li — hozircha skriptlarning o'zini nusxalash (repo yopiq bo'lgani uchun). Kompyuteringizdan (loyiha papkasida):

```powershell
scp deploy/new/bootstrap.sh deploy/new/wireguard.sh root@<APP_IP>:/root/
```
```powershell
scp deploy/new/bootstrap.sh deploy/new/wireguard.sh root@<MEDIA_IP>:/root/
```

APP serverda (RS 2000):

```bash
bash /root/bootstrap.sh app
```
MEDIA serverda (RS 4000, o'sha skript, boshqa rol):

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

## 6. Ikki server o'rtasida yopiq kanal (WireGuard)

Bu kanal orqali MEDIA serverdagi yozuv xizmati APP serverdagi bazaga ulanadi. Ikki bosqich.

**1-bosqich** — har serverda o'zining OCHIQ kalitini oling (xavfsiz, berish mumkin):

APP serverda:
```bash
sudo bash /root/wireguard.sh core
```
MEDIA serverda:
```bash
sudo bash /root/wireguard.sh media
```
Har biri bitta satr ochiq kalit chiqaradi. Ikkalasini yozib oling.

**2-bosqich** — har serverda ikkinchisining **public IP** va **ochiq kaliti** bilan ulang:

APP serverda:
```bash
sudo bash /root/wireguard.sh core <MEDIA_PUBLIC_IP> <MEDIA_OCHIQ_KALIT>
```
MEDIA serverda:
```bash
sudo bash /root/wireguard.sh media <APP_PUBLIC_IP> <APP_OCHIQ_KALIT>
```
Oxirida "OK: ... ga kanal orqali ping o'tdi" chiqishi kerak. O'tmasa, ikkala serverda ham 2-bosqich bajarilganini tekshiring. Qo'lda tekshirish: APP serverda `ping -c 3 10.10.0.2`, MEDIA serverda `ping -c 3 10.10.0.1`.

---

## 7. DNS (team lead yoki siz)

Ikkita yangi yozuv (**A** tur), TTL 300:

| Yozuv | Qiymat | Nima uchun |
|---|---|---|
| `edu2.thesofmebel.uz` | **APP** server IP'si (RS 2000) | Sinov: yangi serverni eski sayt buzilmasdan tekshirish |
| `lk.thesofmebel.uz` | **MEDIA** server IP'si (RS 4000) | Jonli dars serveri (haqiqiy ishlatiladi) |

`edu.thesofmebel.uz` ga **hozircha tegmang** (u eski serverda). Ko'chib o'tish kuni (12-bo'lim) uni yangi APP'ga yo'naltiramiz.
Tekshirish: `nslookup lk.thesofmebel.uz` — MEDIA IP'sini ko'rsatishi kerak.

---

## 8. Loyihani serverga olish (APP va MEDIA ikkalasida)

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

## 9. APP serverni ishga tushirish (RS 2000) — AVVAL shuni qiling

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
- `REDIS_PASSWORD` — yangi parol. Hosil qilish: `python3 -c "import secrets; print(secrets.token_hex(24))"` (faqat harf-raqam bo'lishi shart)
- `CORE_WG_IP=10.10.0.1`, `MEDIA_WG_IP=10.10.0.2`, `REC_UPSTREAM=10.10.0.2:8000`. **Agar MEDIA hali tayyor bo'lmasa, `REC_UPSTREAM` qatorini vaqtincha o'chirib qo'ying** — yozuv so'rovlari `web` ga boradi (yozuv ishlamaydi, qolgan hamma narsa ishlaydi).
- Baza xotira sozlamalari RS 2000 uchun standartda qoladi.

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
(Ba'zi "already exists" ogohlantirishlari bo'lishi mumkin — xato emas, agar oxirida jadvallar bo'lsa.) Endi hammasini ko'taring:

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

**Yuklangan fayllarni ko'chirish** (rasm/vazifa fayllari) — eski serverdan **APP serverga** (`rsync`, eski serverdan turib, `ssh -A` bilan; `tmux` ichida ishga tushiring):

```bash
rsync -az /var/lib/docker/volumes/edu_platform_media/_data/ deploy@<APP_IP>:/tmp/media/
```
APP serverda volume'ga qo'yish:

```bash
sudo rsync -a /tmp/media/ /var/lib/docker/volumes/edu_platform_media/_data/
```
(Volume nomlari loyiha papkasi nomidan olinadi: papka `edu_platform` bo'lsa `edu_platform_media`. Tekshirish: `docker volume ls`.)

---

## 10. MEDIA serverni ishga tushirish (RS 4000) — APP tayyor bo'lgach

Bu server LiveKit va **yozuv xizmatlarini** ishga tushiradi. Yozuv xizmatlari APP serverdagi bazaga WireGuard orqali ulanadi, shuning uchun **6-bo'lim (WireGuard) bajarilgan va 9-bo'lim (APP) ishlab turgan bo'lishi shart.**

MEDIA serverda `.env`: eng ishonchli yo'l — APP serverdagi `.env` ni shu yerga ko'chirish (kalitlar bir xil bo'lishi shart). APP serverdan:

```bash
scp /var/www/edu_platform/.env deploy@<MEDIA_IP>:/var/www/edu_platform/.env
```
So'ng MEDIA serverda `.env.media.example` dagi "MEDIA ga xos" qatorlarni qo'shing (`LK_DOMAIN`, `REC_CPUS`, `TRANSCODER_CPUS` va h.k.):

```bash
cd /var/www/edu_platform && nano .env
```
`LK_DOMAIN=lk.thesofmebel.uz`, `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` (APP bilan **aynan bir xil**). Ishga tushirish:

```bash
docker compose -f docker-compose.media.yml up -d --build
```
Tekshirish:
```bash
docker compose -f docker-compose.media.yml ps
```
```bash
docker compose -f docker-compose.media.yml logs --tail=30 caddy
```
Caddy logida "certificate obtained" (sertifikat olindi) chiqishi kerak — buning uchun `lk.` DNS yozuvi ishlayotgan bo'lishi shart. Brauzerdan `https://lk.thesofmebel.uz` ni oching: LiveKit javobi chiqsa tayyor.
Agar `manifest unknown` xatosi chiqsa: `.env` da `LIVEKIT_VERSION=1.13.4` (`v`siz) qiling.

Yozuv xizmatini tekshirish (MEDIA serverda):
```bash
docker compose -f docker-compose.media.yml logs --tail=30 rec
```
Bazaga ulana olganini ko'rsatadi. Keyin APP serverda `.env` dagi `REC_UPSTREAM=10.10.0.2:8000` qatori yoqilganini tekshirib, Caddy'ni qayta ishga tushiring:

```bash
docker compose -f docker-compose.app.yml up -d caddy
```

**Dars yozuvlarini ko'chirish** (eski serverdan **MEDIA serverga**, fayllar shu yerda turadi; `tmux` ichida):

```bash
rsync -az /var/lib/docker/volumes/edu_platform_recordings/_data/ deploy@<MEDIA_IP>:/tmp/recordings/
```
MEDIA serverda:
```bash
sudo rsync -a /tmp/recordings/ /var/lib/docker/volumes/edu_platform_recordings/_data/
```

---

## 11. Sinov ro'yxati (ko'chib o'tishdan oldin)

1. `https://edu2.thesofmebel.uz/api/docs/` ochiladi; `https://edu2.thesofmebel.uz/api/health/` — `ok`.
2. Login qilish ishlaydi (bu yangi bazada eski foydalanuvchilar bilan).
3. **Jonli dars sinovi:** ikki qurilmada (o'qituvchi + o'quvchi) dars — video, ovoz, doska, chat. Frontend sinov domenini bilishi uchun Vercel'da preview muhitida API manzilini `edu2` ga qo'ying yoki test akkaunt bilan sinang.
4. **Dars yozuvi:** o'qituvchi darsni yozib tugatadi → yozuv "tayyor" bo'ladi (bo'laklar MEDIA'dagi `rec` ga boradi) → MP4 ga o'tadi: `docker compose -f docker-compose.media.yml logs --tail=30 transcoder` (MEDIA serverda). Yozuvni ko'rish ham ishlashi kerak.
5. `docker stats --no-stream` — ikkala serverda CPU/RAM me'yorida.
6. **Zaxira nusxa** (12-bo'lim) ishlaydi va tiklash sinab ko'rilgan.
7. **Disk ogohlantirishi:** admin panelda server holati; `check_disk` 80% dan oshsa adminlarga bildirishnoma yuboradi.

---

## 12. Zaxira nusxa (APP serverda)

`deploy/new/backup.sh` har kecha bazaning nusxasini oladi va **MEDIA serverga** ko'chiradi (boshqa mashina). Sozlash yo'riqnomasi faylning boshida. Qisqasi: kalit yaratish, MEDIA'ga qo'shish, `crontab -e` ga bitta qator.
**Tiklashni albatta bir marta sinab ko'ring** — aks holda zaxira bor-yo'qligi noma'lum.

---

## 13. Ko'chib o'tish kuni (cutover) — kechqurun, dars bo'lmagan paytda

1. Bir kun oldin DNS'da `edu.thesofmebel.uz` TTL ni 300 s ga tushiring.
2. Eski serverda saytni vaqtincha to'xtating (yozuv to'xtasin): `docker compose -f docker-compose.prod.yml stop backend cron`.
3. **Oxirgi** bazani qayta dump qiling va yangi APP'ga tiklang (9-bo'lim, YANGI serverdagi bazani avval tozalab: `docker compose -f docker-compose.app.yml exec -T db psql -U edtech -d edtech -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` — **faqat yangi serverda**, hech qachon eskisida!), fayllarni (media va yozuvlar) `rsync -a` bilan yangilang.
4. APP `.env` da `DOMAIN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` ni `edu.thesofmebel.uz` ga o'zgartiring: `docker compose -f docker-compose.app.yml up -d`. **MEDIA serverdagi `.env` ga ham xuddi shu to'rt qiymatni yozing** va `docker compose -f docker-compose.media.yml up -d`.
5. DNS: `edu.thesofmebel.uz` → **APP IP**. Caddy sertifikatni bir necha soniyada oladi.
6. Tekshiring: login, chat, jonli dars, yozuv. Muammo bo'lsa — DNS'ni **eski IP**ga qaytaring (eski server o'chirilmagan).
7. 1–2 hafta eski serverni **o'chirmasdan** saqlang.

---

## 14. Kundalik ishlar

| Nima | Buyruq (`/var/www/edu_platform` ichida) |
|---|---|
| APP yangilash (AVVAL shuni) | APP serverda: `git pull && docker compose -f docker-compose.app.yml up -d --build` |
| MEDIA yangilash (APP'dan KEYIN) | MEDIA serverda: `git pull && docker compose -f docker-compose.media.yml up -d --build` |
| Holat | `docker compose -f docker-compose.app.yml ps` (APP) / `docker compose -f docker-compose.media.yml ps` (MEDIA) |
| Log | APP: `... logs --tail=100 web` (yoki `ws`, `cron`, `caddy`); MEDIA: `... logs --tail=100 rec` (yoki `transcoder`, `rec-cron`, `livekit`, `caddy`) |
| Resurs | `docker stats --no-stream` va `htop` |
| Disk | `df -h /` va `docker system df` |
| Admin yaratish | `docker compose -f docker-compose.app.yml exec web python manage.py createsuperuser` |
| Yozuv diskini tozalash (hisobot) | MEDIA: `docker compose -f docker-compose.media.yml exec rec python manage.py prune_recordings` |

**Yangilash tartibi muhim:** migratsiyani APP serverdagi `web` bajaradi, shuning uchun har doim **avval APP, keyin MEDIA**. Deploy'ni dars bo'lmagan vaqtda qiling (`ws` qayta ishga tushganda chat qisqa uziladi; video uzilmaydi).

**Ogohlantirishlar:**
- **Disk:** yozuvlar MEDIA serverda diskni to'ldiradi (~9–20 GB/kun, 60 yozilgan dars/kun bo'lsa). Admin panelda va `check_disk` (80% / 90% da bildirishnoma) orqali kuzating. To'lishiga yaqinlashsa: `prune_recordings` (hisobot, so'ng `--apply --drop-webm`) yoki netcup'da qo'shimcha disk.
- **Trafik:** 24 soatda 3 TB dan oshsa tezlik 300 Mbit/s ga tushadi (MEDIA'da ehtiyot bo'ling: video + yozuv ko'rish shu serverdan chiqadi).
- **Firewall:** Docker o'zi ochgan portlarni `ufw` dan chetlab o'tadi. Shuning uchun baza, Redis va `rec` portlari faqat WireGuard manzilida (`10.10.0.x`) ochilgan, internetda emas. Yangi port qo'shsangiz ehtiyot bo'ling.
- **MEDIA yiqilsa:** jonli video va yozuv to'xtaydi, sayt va chat ishlayveradi. **APP yiqilsa:** yangi o'quvchi darsga kira olmaydi, allaqachon ulangan video davom etadi.
- **SSH'dan chiqib ketib qolsangiz:** SCP'dagi konsol (VNC) orqali kiring.

---

## 15. Muammo bo'lsa menga yuboring

Quyidagilarni (parollarsiz!) yuboring:
- `docker compose -f docker-compose.app.yml ps` (APP) yoki `docker compose -f docker-compose.media.yml ps` (MEDIA) natijasi
- `docker compose -f docker-compose.<app|media>.yml logs --tail=80 <xizmat>` natijasi
- WireGuard muammosi bo'lsa: `sudo wg show` (maxfiy kalit ko'rsatilmaydi) va `ping -c 3 10.10.0.1` / `10.10.0.2`
- Xato matni va qaysi qadamda chiqqani
