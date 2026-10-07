# AI-home-checker ni serverga ulash (uy vazifasini AI bilan tekshirish)

`AI-home-checker` (RJalol) — **alohida xizmat**. U yopiq repoda; bizning backend unga ichki Docker tarmog'i
orqali murojaat qiladi. Xizmat ishlamasa ham platforma ishlayveradi: uy vazifasi o'qituvchiga qo'lda
baholashga tushadi.

> Bu qadamlar hali **serverda sinalmagan**. Docker fayl birinchi ishga tushganda kichik tuzatish talab
> qilsa, xato matnini yuboring.

## 1. Kodni serverga olish (yopiq repo, token serverga yozilmaydi)

O'z kompyuteringizda (GitHub'ga kirgan holda), PowerShell:

```powershell
cd C:\Users\mathu\Desktop
git clone https://github.com/RJalol/AI-home-checker.git
scp -r AI-home-checker root@75.119.154.71:/var/www/ai-home-checker
```

(`scp` serverda `/var/www/ai-home-checker` papkasini yaratadi. `.git` papkasi ham ko'chadi, zarari yo'q.)

## 2. Sozlama fayli — `/var/www/ai-home-checker/.env`

Serverda yarating (`nano /var/www/ai-home-checker/.env`). Uchta qiymat, **hammasi o'zingiz o'ylab topgan uzun tasodifiy matn**:

```
GEMINI_API_KEY=YANGI_GEMINI_KALITI
INTERNAL_API_KEY=uzun-tasodifiy-matn-1
CHECKER_DB_PASSWORD=uzun-tasodifiy-matn-2
```

- `GEMINI_API_KEY` — https://aistudio.google.com/apikey dan **yangi** kalit (suhbatda ko'ringan eskisini ishlatmang).
- Parollarni tasodifiy yaratish: `openssl rand -hex 24` (har biri uchun bir marta).
- Bu fayl **faqat serverda** turadi, GitHub'ga tushmaydi.

## 3. Ishga tushirish

```bash
cd /var/www/edu_platform && git pull && docker compose -f deploy/ai-home-checker/docker-compose.ai.yml --env-file /var/www/ai-home-checker/.env up -d --build
```

Birinchi yig'ish 3-6 daqiqa. Keyin tekshirish:

```bash
docker compose -f /var/www/edu_platform/deploy/ai-home-checker/docker-compose.ai.yml --env-file /var/www/ai-home-checker/.env ps
```

`checker-api`, `checker-worker`, `checker-db`, `checker-redis` hammasi `Up` (api `healthy`) bo'lishi kerak.

## 4. Tashkilotni ro'yxatdan o'tkazish (bir marta) — kalit oling

```bash
cd /var/www/edu_platform && docker compose -f deploy/ai-home-checker/docker-compose.ai.yml --env-file /var/www/ai-home-checker/.env exec -T checker-api python -c "
import os, json, urllib.request as u
req = u.Request('http://localhost:8000/organizations', data=json.dumps({'name': 'Edu Platform'}).encode(),
                headers={'Content-Type': 'application/json', 'X-Internal-Api-Key': os.environ['INTERNAL_API_KEY']})
print(u.urlopen(req).read().decode())
"
```

Javobda `api_key` (`hwck_...`) chiqadi — u **faqat bir marta** ko'rsatiladi, darhol nusxalab oling.

## 5. Bizning backendga ulash

`/var/www/edu_platform/.env` oxiriga qo'shing:

```
HOMEWORK_AI_URL=http://checker-api:8000
HOMEWORK_AI_INTERNAL_KEY=<2-qadamdagi INTERNAL_API_KEY>
HOMEWORK_AI_ORG_KEY=<4-qadamdagi hwck_... kaliti>
```

Keyin backend va cron'ni qayta ishga tushiring:

```bash
cd /var/www/edu_platform && docker compose -f docker-compose.prod.yml up -d --force-recreate backend cron
```

## 6. Sinash

1. O'quvchi bilan vazifaga fayl yuklang.
2. O'qituvchi sahifasida topshiriq avval "tekshirilmoqda", 10-60 soniyadan keyin "ko'rib chiqish kutilmoqda" bo'ladi va ball AI taklifi bilan to'ladi. O'qituvchiga bildirishnoma keladi.
3. O'qituvchi tasdiqlaydi, o'quvchi natijani ko'radi.

AI xizmati o'chiq yoki ishlamasa, 2-qadam o'rniga topshiriq darhol "ko'rib chiqish kutilmoqda" bo'ladi (qo'lda baholash).

## Xavfsizlik

- Xizmatga **tashqaridan kirib bo'lmaydi** (port ochilmagan); uni faqat backend chaqiradi.
- Tashqi API `INTERNAL_API_KEY` va tashkilot kaliti bilan himoyalangan.
- O'quvchilar fayllari xizmatning `checker_uploads` volume'ida saqlanadi (bazaviy zaxira nusxaga qo'shishni unutmang).
- Topshiriqlar Gemini'ga (Google) yuboriladi: maktab ma'lumoti uchun **pullik (billing yoqilgan)** kalit tavsiya qilinadi.
