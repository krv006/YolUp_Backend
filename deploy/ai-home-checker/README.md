# AI-home-checker (multi-model) ni serverga ulash — uy vazifasi va Speaking audio AI tekshiruvi

`AI-home-checker-multi-model` (RJalol, yopiq repo, `main` shoxi) — **alohida xizmat**. U matn, rasm, DOCX va **Speaking audio**
(`.mp3 .wav .m4a .ogg`) ni baholaydi. Bizning backend unga ichki Docker tarmog'i orqali murojaat qiladi. Xizmat ishlamasa ham platforma
ishlayveradi: uy vazifasi o'qituvchiga qo'lda baholashga tushadi. **Yakuniy bahoni doim o'qituvchi tasdiqlaydi.**

Qaysi shoxni olish kerak: **`main`** (31-oktabrdagi tuzatishlar bilan: rasm yuklashda baholash, provayder chidamliligi, javob tili, 16 ta audit xatosi).
`claude/fix-audit-findings` shoxida faqat audio **test hisoboti** bor (kod emas) — uni ko'chirish shart emas.

Bizning backend tomoni (`apps/homework/ai_client.py`) o'zgarmagan: xizmatning `POST /submissions` va `GET /submissions/{id}` API'si avvalgi bilan bir xil,
ruxsat etilgan audio formatlar ham bir xil. Faqat shu papkadagi deploy fayllari yangi repo uchun yangilangan.

> Bu qadamlar hali **serverda sinalmagan**. Docker fayl birinchi ishga tushganda kichik tuzatish talab qilsa, xato matnini yuboring.

## 0. Nima kerak

- **Gemini API kaliti (pullik, billing yoqilgan)** — https://aistudio.google.com/apikey . Audioni FAQAT Gemini o'qiydi, shuning uchun Speaking uchun shart.
  Narx: audio ~32 token/soniya (~1 920 token/daqiqa) — qisqa Speaking javobi uchun juda arzon, lekin hisobni kuzatib boring.
- Boshqa provayder kalitlari (QWEN, GLM, ANTHROPIC, OpenAI) — **ixtiyoriy**. Bo'lmasa o'sha daraja o'tkazib yuboriladi va matnni Gemini baholaydi.
- Xizmat APP serverda ishlaydi (backend bilan bir Docker tarmog'ida). Yuklama kichik: tashqi AI'ga so'rov yuboradi, o'zi og'ir hisoblamaydi.

## 1. Kodni serverga olish (yopiq repo, token serverga yozilmaydi)

O'z kompyuteringizda (GitHub'ga kirgan holda), PowerShell:

```powershell
cd C:\Users\mathu\Desktop
git clone --branch main https://github.com/RJalol/AI-home-checker-multi-model.git AI-home-checker
scp -r AI-home-checker root@152.53.33.65:/var/www/ai-home-checker
```

(Papka nomi `AI-home-checker` bo'lib qoladi — compose fayl shu yo'lni kutadi. `.git` ham ko'chadi, zarari yo'q.)

## 2. Sozlama fayli — `/var/www/ai-home-checker/.env`

Serverda yarating (`nano /var/www/ai-home-checker/.env`):

```
GEMINI_API_KEY=YANGI_GEMINI_KALITI
INTERNAL_API_KEY=uzun-tasodifiy-matn-1
CHECKER_DB_PASSWORD=uzun-tasodifiy-matn-2
```

- Parollarni tasodifiy yaratish: `openssl rand -hex 24` (har biri uchun bir marta).
- Ixtiyoriy qo'shimchalar (bo'lsa yozing): `QWEN_API_KEY=`, `GLM_API_KEY=`, `ANTHROPIC_API_KEY=`, `CHECKER_OPENAI_API_KEY=`.
- Fikr-mulohaza tili standart **o'zbekcha (lotin)**. Boshqa til kerak bo'lsa: `FEEDBACK_LANGUAGE=Russian`.
- Bu fayl **faqat serverda** turadi, GitHub'ga va suhbatga tushmaydi.

## 3. Ishga tushirish

```bash
cd /var/www/edu_platform && git pull && docker compose -f deploy/ai-home-checker/docker-compose.ai.yml --env-file /var/www/ai-home-checker/.env up -d --build
```

Birinchi yig'ish 5-10 daqiqa (kutubxonalar ko'p). Keyin tekshirish:

```bash
docker compose -f /var/www/edu_platform/deploy/ai-home-checker/docker-compose.ai.yml --env-file /var/www/ai-home-checker/.env ps
```

`checker-api`, `checker-worker`, `checker-reconciler`, `checker-db`, `checker-redis` hammasi `Up` (api `healthy`) bo'lishi kerak.

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

`/var/www/edu_platform/.env` (APP server) oxiriga qo'shing:

```
HOMEWORK_AI_URL=http://checker-api:8000
HOMEWORK_AI_INTERNAL_KEY=<2-qadamdagi INTERNAL_API_KEY>
HOMEWORK_AI_ORG_KEY=<4-qadamdagi hwck_... kaliti>
```

Keyin backend va cron'ni qayta ishga tushiring:

```bash
cd /var/www/edu_platform && docker compose -f docker-compose.app.yml up -d --force-recreate web ws cron
```

**Muhim:** `HOMEWORK_AI_URL` sozlangach BARCHA uy vazifalari (matn ham, audio ham) shu xizmatga ketadi va ichki OpenAI tekshiruvi o'chadi.
Xizmat javob bermasa topshiriq 15 daqiqadan keyin o'qituvchiga qo'lda baholashga tushadi.

## 6. Sinash

1. O'qituvchi akkauntida **ingliz tili** kursida `Speaking` ko'nikmali vazifa yarating.
2. O'quvchi bilan `.mp3` yoki `.m4a` ovoz faylini yuklang (telefon yozuvi, 1-2 daqiqa).
3. O'qituvchi sahifasida topshiriq avval "tekshirilmoqda", 10-90 soniyadan keyin "ko'rib chiqish kutilmoqda" bo'ladi va ball AI taklifi bilan to'ladi.
4. O'qituvchi eshitib tasdiqlaydi yoki tahrirlaydi, o'quvchi natijani ko'radi.
5. Oddiy matn/PDF vazifa bilan ham shuni takrorlang.

Natija chiqmasa: `docker compose ... logs checker-worker --tail 50`.

## Ma'lum cheklovlar (RJalol'ning 6-noyabrdagi audio hisobidan)

Hisob audio **texnik** yo'li sinalganini aytadi (fayl modelga buzilmay yetib boradi, tarmoq xatolarida qayta uriniladi), lekin **baholash sifati** (talaffuz,
ravonlik, ingliz imtihonchi bilan mosligi) haqiqiy nutq va haqiqiy Gemini bilan **sinalmagan**. Shuning uchun:

- AI bahosini faqat **taklif** deb qarang, o'qituvchi eshitib tasdiqlasin (bizda shunday: har doim `pending_review`).
- Ishga tushirgach 10-20 ta haqiqiy o'quvchi yozuvini o'qituvchi bahosi bilan solishtirib ko'ring.
- Faqat `.mp3 .wav .m4a .ogg` qabul qilinadi (bizning yuklash ham shularni beradi). Brauzerda yozilgan `.webm` / WhatsApp `.opus` rad etiladi.
- Juda katta WAV (taxminan 14 MB dan katta, ~1,5 daqiqa CD sifati) Gemini so'rov limitidan oshishi mumkin — o'quvchilarga `.mp3`/`.m4a` yuklashni tavsiya qiling.
- Bo'sh yoki buzuq audio ham 3 marta (pullik) yuboriladi va oxirida "baholay olmadi" bo'lib o'qituvchiga tushadi.
- iPhone `.m4a` fayli `audio/mp4` deb yuboriladi; Gemini buni qabul qiladimi — haqiqiy chaqiruv bilan tasdiqlanmagan. **Birinchi sinovni aynan iPhone yozuvi bilan qiling.**

## Xavfsizlik

- Xizmatga **tashqaridan kirib bo'lmaydi** (port ochilmagan); uni faqat backend chaqiradi.
- Tashqi API `INTERNAL_API_KEY` va tashkilot kaliti bilan himoyalangan.
- O'quvchilar fayllari xizmatning `checker_uploads` volume'ida saqlanadi (bazaviy zaxira nusxaga qo'shishni unutmang).
- Topshiriqlar (audio ham) Gemini'ga (Google) yuboriladi: maktab ma'lumoti uchun **pullik (billing yoqilgan)** kalit tavsiya qilinadi.
