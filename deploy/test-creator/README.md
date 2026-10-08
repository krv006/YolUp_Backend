# Test-creator — platformaga ulangan "AI bilan test yaratish"

`Test-creator` (RJalol) — material (PDF/Word/PowerPoint/Excel/matn) dan **UZBMB, IELTS Academic, Digital SAT**
standartlari bo'yicha savollar yaratadigan xizmat. U **ichki xizmat**: alohida sayti, domeni, DNS yozuvi YO'Q.
O'qituvchi platformaning o'zida (login bitta) materialni yuklaydi, bizning backend Test-creator'ni ichkaridan chaqiradi
va natija **qoralama test** bo'lib saqlanadi (`POST /api/v1/quizzes/ai-generate/`, `BACKEND_AI_QUIZ.md`).

```
o'qituvchi ──► edu backend ──(ichki tarmoq)──► tc-api ──► tc-worker (Celery) ──► Gemini
                  │                              └── tc-db (pgvector), tc-redis
                  └── cron: sync_ai_quizzes (har 30 s ishni bir qadam suradi)
```

> Docker qismi hali **serverda sinalmagan** (lokal Docker yo'q); backend qismi testlar bilan qoplangan. Birinchi
> ishga tushirishda xato chiqsa, matnini yuboring.
> Moslashtirishlar (`apply_patch.py`): **Gemini provayderi** (Test-creator'da faqat mock va Claude bor) va **yopiq
> ro'yxatdan o'tish** (faqat xizmat hisobi emaili).

## 1. Kodni serverga olish (yopiq repo, token serverga yozilmaydi)

O'z kompyuteringizda, PowerShell (yangi `clone` — `node_modules` bo'lmaydi):

```powershell
cd C:\Users\mathu\Desktop
git clone https://github.com/RJalol/Test-creator.git
scp -r Test-creator root@75.119.154.71:/var/www/test-creator
```

## 2. Moslashtirishni qo'llash

```bash
cd /var/www/edu_platform && git pull && python3 deploy/test-creator/apply_patch.py /var/www/test-creator
```

Chiqishi: `gemini_provider.py: nusxalandi`, `ai_router.py: qo'llandi`, `requirements.txt: google-genai qo'shildi`,
`auth.py: qo'llandi`. Qayta ishga tushirsa takrorlamaydi. `XATO: ... topilmadi` chiqsa, repo versiyasi o'zgargan —
shu xabarni yuboring.

## 3. Test-creator sozlamasi — `/var/www/test-creator/.env`

Xizmat hisobi (platforma nomidan kiradigan) emaili va parolini o'zingiz o'ylab toping — ular **ikkala `.env`** ga
yoziladi (3 va 5-qadam). Email haqiqiy bo'lishi shart emas.

```bash
SVC_PASS=$(openssl rand -hex 16)
cat > /var/www/test-creator/.env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
TC_DB_PASSWORD=$(openssl rand -hex 24)
GEMINI_API_KEY=KALITNI_SHU_YERGA_QOYING
REGISTRATION_ALLOWED_EMAILS=platforma@edu.thesofmebel.uz
EOF
chmod 600 /var/www/test-creator/.env
echo "TEST_CREATOR_PASSWORD (5-qadamda kerak): $SVC_PASS"
```

Gemini kalitini (ekranda ko'rinmasdan) qo'yish:

```bash
read -rsp "Gemini kaliti: " K && echo && sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$K|" /var/www/test-creator/.env && unset K && echo "kalit yangilandi"
```

## 4. Test-creator'ni ishga tushirish

```bash
cd /var/www/edu_platform && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env up -d --build
```

Birinchi yig'ish 3-5 daqiqa. Holat: `docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env ps` —
`tc-api` `healthy` (birinchi marta 1-2 daqiqa: migratsiya va standartlarni yuklaydi), `tc-worker`, `tc-db`, `tc-redis` `Up`.

## 5. Platformaga ulash — `/var/www/edu_platform/.env`

Shu fayl oxiriga qo'shing (parol — 3-qadamdagi `SVC_PASS`):

```bash
TEST_CREATOR_URL=http://tc-api:8000/api/v1
TEST_CREATOR_EMAIL=platforma@edu.thesofmebel.uz
TEST_CREATOR_PASSWORD=3-QADAMDA_KOʻRSATILGAN_PAROL
```

Keyin platformani yangilang (Caddy qayta yaratilmaydi, saytlar uzilmaydi — faqat backend/cron qayta ishga tushadi):

```bash
cd /var/www/edu_platform && git pull && docker compose -f docker-compose.prod.yml up -d --build
```

Xizmat hisobi **birinchi so'rovda o'zi yaratiladi** (qo'lda ro'yxatdan o'tish shart emas). Caddy'ga o'zgartirish
kerak emas — ichki xizmatga tashqaridan kirib bo'lmaydi.

## 6. Tekshirish

1. Tizimga o'qituvchi sifatida kiring, Swagger'da (`/api/docs/`) `POST /quizzes/ai-generate/`: `file` (kichik PDF yoki Word),
   `topic`, `standard=uzbmb`, `question_count=5`, `course=<guruh id>`.
2. `GET /quizzes/ai-generate/<id>/` — `status`: `queued` → `processing` → `generating` → `done` (odatda 1-5 daqiqa).
3. `done` bo'lganda `quiz` — qoralama testning id'si; unda savollar, `GET /quizzes/<id>/`.
4. Bo'lmasa: `docker compose -f docker-compose.prod.yml logs --tail 50 cron` va `... logs --tail 50 tc-api tc-worker`.

## GPT (OpenAI) bilan ishlatish — Gemini o'rniga

Test-creator Gemini, **OpenAI (GPT)**, Claude va mock provayderlarini biladi; faol provayderni `.env` dagi `TC_AI_PROVIDER` tanlaydi
(standart `gemini`). GPT'ni yoqish:

1. Yangi kodni oling va moslashtirishni qayta qo'llang (OpenAI provayderini qo'shadi, takrorlansa zarar yo'q):

```bash
cd /var/www/edu_platform && git pull && python3 deploy/test-creator/apply_patch.py /var/www/test-creator
```

2. OpenAI kalitini `/var/www/test-creator/.env` ga yozing (ekranda ko'rinmaydi, chatga yubormang) va provayderni almashtiring:

```bash
read -rsp "OpenAI kaliti: " K && echo && sed -i '/^OPENAI_API_KEY=/d; /^TC_AI_PROVIDER=/d' /var/www/test-creator/.env && printf "OPENAI_API_KEY=%s\nTC_AI_PROVIDER=openai\n" "$K" >> /var/www/test-creator/.env && unset K && echo "tayyor"
```

3. Model nomini bering (hisobingizda ruxsat etilgan model; bo'lmasa standart `gpt-4o-mini`):

```bash
sed -i '/^OPENAI_MODEL=/d' /var/www/test-creator/.env && echo "OPENAI_MODEL=MODEL_NOMI" >> /var/www/test-creator/.env
```

4. Qayta yig'ing va ishga tushiring (yangi `openai` paketi o'rnatiladi):

```bash
cd /var/www/edu_platform && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env up -d --build
```

Gemini'ga qaytish: `.env` dan `TC_AI_PROVIDER` qatorini o'chiring (yoki `gemini` qiling) va 4-qadamni takrorlang.
Kalit va chegaralar: `OPENAI_MAX_OUTPUT_TOKENS` (standart 8192) — "reasoning" modellar uchun oshirish kerak bo'lishi mumkin.

## Bilib qo'ying

- **Material kerak:** Test-creator mavzu nomidan emas, yuklangan materialdan savol yaratadi (matn asosida). Skanerlangan
  (rasm) PDF o'qilmaydi — ish `failed` bo'ladi va sababi ko'rsatiladi.
- **Sifat:** savollarni Gemini yozadi, Test-creator o'z sifat tekshiruvidan o'tkazadi; baribir test **qoralama** bo'lib
  tushadi — o'qituvchi ko'rib chiqib e'lon qiladi.
- **Maxfiylik:** material va savollar Test-creator bazasida (`tc_pgdata`) saqlanadi va Gemini'ga (Google) yuboriladi.
  Bolalarning shaxsiy ma'lumotini yuklamang (faqat o'quv material). Platformadagi nusxa ish tugagach o'chiriladi.
- **Cheklov:** o'qituvchiga bir vaqtda 3 ta faol ish, kuniga 10 ta; fayl ≤ 20 MB; 5–60 ta savol.
- **Zaxira nusxa:** `tc_pgdata` va `tc_storage` volume'larini zaxiraga qo'shing.
- **O'chirish:** `.env` dagi `TEST_CREATOR_URL` ni bo'sh qoldirsangiz AI test yaratish o'chadi (endpoint `400` qaytaradi),
  qolgan platformaga ta'sir qilmaydi.
