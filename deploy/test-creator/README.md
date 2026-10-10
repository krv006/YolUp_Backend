# Test-creator — platformaga ulangan "Test banki" (RJalol/Test-creator, 2026-10 versiyasi)

`Test-creator` (RJalol) — material (PDF/Word/PowerPoint/Excel/matn) dan **UZBMB, IELTS Academic, Digital SAT**
standartlari bo'yicha savollar yaratadigan va savollar bankini yuritadigan xizmat. U **ichki xizmat**: alohida sayti,
domeni, DNS yozuvi YO'Q. O'qituvchi platformaning o'zida (AI sahifasi → "Test banki") materialni yuklaydi,
bizning backend Test-creator'ni ichkaridan chaqiradi va natija **qoralama test** bo'lib saqlanadi
(`POST /api/v1/quizzes/ai-generate/` + `standard`, `BACKEND_AI_QUIZ.md`).

```
o'qituvchi ──► edu backend ──(ichki tarmoq)──► tc-api ──► tc-worker (Celery) ──► OpenAI / Gemini / Claude
                  │                              └── tc-db (pgvector), tc-redis
                  └── cron: sync_ai_quizzes (har 30 s ishni bir qadam suradi)
```

Oddiy "AI bilan test yaratish" (imtihon tanlash, IELTS/SAT va h.k.) Test-creator'siz, platformaning o'z generatori bilan
ishlaydi (`apps/quizzes/ai_exam.py`). Test-creator **qo'shimcha**: standart bo'yicha reja, savollar banki, takroriy savollarni
topish, matematik javoblarni tekshirish. U o'chiq bo'lsa platforma to'liq ishlayveradi.

Oldingi versiyadan farqi: AI provayderlari (OpenAI, Gemini, Claude) Test-creator'ning o'zida bor — **patch kerak emas**;
test yaratish fonda ishlaydi; kvota tugasa darhol to'xtaydi; kunlik chaqiruv chegarasi bor.

## 1. Yangi kodni serverga olish (yopiq repo, token serverga yozilmaydi)

O'z kompyuteringizda, PowerShell:

```powershell
cd C:\Users\mathu\Desktop\Test-creator
git pull
cd ..
scp -r Test-creator root@75.119.154.71:/var/www/test-creator-new
```

Serverda eskisini yonida saqlab, yangisini o'rniga qo'ying (`.env` ko'chadi):

```bash
cd /var/www && docker compose -f edu_platform/deploy/test-creator/docker-compose.tc.yml --env-file test-creator/.env down 2>/dev/null; \
mv test-creator test-creator-old && mv test-creator-new test-creator && cp test-creator-old/.env test-creator/.env && echo "kod almashtirildi"
```

## 2. Test-creator sozlamasi — `/var/www/test-creator/.env`

Eski `.env` ishlayveradi (`SECRET_KEY`, `TC_DB_PASSWORD`, kalitlar saqlangan). Faqat provayderni aniqlang
(`gpt-4o-mini` standart; boshqa model uchun `OPENAI_MODEL`). Kalit yo'q bo'lsa, ekranda ko'rinmasdan kiriting:

```bash
grep -q '^OPENAI_API_KEY=.\+' /var/www/test-creator/.env && echo "OpenAI kaliti bor" || { read -rsp "OpenAI kaliti: " K && echo && printf "OPENAI_API_KEY=%s\n" "$K" >> /var/www/test-creator/.env && unset K && echo "kalit yozildi"; }
sed -i '/^TC_AI_PROVIDER=/d' /var/www/test-creator/.env && echo "TC_AI_PROVIDER=openai" >> /var/www/test-creator/.env
```

Gemini yoki Claude'ga o'tish: `TC_AI_PROVIDER=gemini` (kalit `GEMINI_API_KEY`) yoki `anthropic` (`ANTHROPIC_API_KEY`).
Kunlik AI chaqiruv chegarasi (xarajat uchun): `TC_AI_DAILY_LIMIT=200` (standart 200; 0 — cheksiz).

## 3. Ishga tushirish va xizmat hisobi

```bash
cd /var/www/edu_platform && git pull && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env up -d --build
```

Birinchi yig'ish 3-5 daqiqa. Holat: `... ps` — `tc-api` `healthy` (1-2 daqiqa: migratsiya va standartlarni yuklaydi).

Platforma kiradigan **xizmat hisobi** (ro'yxatdan o'tish yopiq, shuning uchun qo'lda yaratiladi). Parol — platformaning
`.env`dagi `TEST_CREATOR_PASSWORD` bilan bir xil bo'lishi shart (u allaqachon yozilgan):

```bash
cd /var/www/edu_platform && TCP=$(grep '^TEST_CREATOR_PASSWORD=' .env | cut -d= -f2-) && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env run --rm -e TC_PASSWORD="$TCP" tc-api python -m app.cli create-user --email "$(grep '^TEST_CREATOR_EMAIL=' .env | cut -d= -f2-)" --name "Edu Platform" --org "Edu Platform"; unset TCP
```

"Created admin ..." chiqadi. Qayta yuritsangiz "already exists" deydi — zarar yo'q.

## 4. AI ishlayotganini tekshirish

```bash
cd /var/www/edu_platform && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env run --rm tc-api python -m app.cli check-ai
```

`OK — the provider works. Sample question: ...` chiqishi kerak. Aks holda aniq sabab yoziladi
(`AIAuthError` — kalit noto'g'ri, `AIConfigError` — model nomi, `AIQuotaExceededError` — hisobda mablag'/limit tugagan).

## 5. Platformaga ulash — `/var/www/edu_platform/.env`

Avvalgi qadamlardan qolgan, o'zgartirish shart emas:

```bash
TEST_CREATOR_URL=http://tc-api:8000/api/v1
TEST_CREATOR_EMAIL=platforma@edu.thesofmebel.uz
TEST_CREATOR_PASSWORD=...
```

Backend yangi API'ga moslangan versiyada bo'lishi kerak (3-qadamdagi `git pull` kodni oladi), shuning uchun platformani ham yangilang:

```bash
cd /var/www/edu_platform && docker compose -f docker-compose.prod.yml up -d --build
```

## 6. Tekshirish

1. O'qituvchi sifatida AI sahifasida → "Qo'shimcha" → **Test banki** (UZBMB / IELTS Academic / Digital SAT) tanlang, bitta material fayli yuklang, savollar sonini bering.
2. Ish ro'yxatda "Test banki" deb chiqadi: `Navbatda` → `Material tahlil qilinmoqda` → `Savollar yaratilmoqda` → `Tayyor` (odatda 2-6 daqiqa).
3. `Tayyor` bo'lganda qoralama test ochiladi, tekshirib e'lon qilinadi.
4. Bo'lmasa: `docker compose -f docker-compose.prod.yml logs --tail 50 cron` va
   `docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env logs --tail 80 tc-api tc-worker`.

## Eski ma'lumotni tozalash (ixtiyoriy)

Yangi versiya yangi ma'lumot omborlaridan (`tc2_*`) foydalanadi. Eski sinov bazasi kerak bo'lmasa:

```bash
docker volume rm test_creator_tc_pgdata test_creator_tc_storage 2>/dev/null; rm -rf /var/www/test-creator-old
```

## Bilib qo'ying

- **Material kerak:** Test-creator mavzu nomidan emas, yuklangan materialdan savol yaratadi. Skanerlangan (rasm) PDF
  o'qilmaydi — ish `failed` bo'ladi va sababi ko'rsatiladi.
- **Faqat variantli (A-B-C-D) savollar.** IELTS kabi turli savol turlari va bo'limlar kerak bo'lsa, oddiy AI sahifasidagi
  imtihon tanlovidan foydalaning (platformaning o'z generatori).
- **Sifat:** test **qoralama** bo'lib tushadi — o'qituvchi ko'rib chiqib e'lon qiladi. Sifat chegaralari
  `docker-compose.tc.yml` da (55/40; Test-creator'ning asl qiymatlari 90/70 juda qattiq).
- **Maxfiylik:** material va savollar Test-creator bazasida (`tc2_pgdata`) saqlanadi va tanlangan AI provayderiga yuboriladi.
  Bolalarning shaxsiy ma'lumotini yuklamang (faqat o'quv material). Platformadagi nusxa ish tugagach o'chiriladi.
- **Cheklov:** o'qituvchiga bir vaqtda 3 ta faol ish, kuniga 10 ta; fayl ≤ 20 MB; 5–60 ta savol.
- **Xarajat nazorati:** Test-creator kunlik chaqiruv chegarasini (`TC_AI_DAILY_LIMIT`) va kvota tugaganda to'xtashni o'zi
  bajaradi; AI sarfi uning ichki hisobotida (`GET /api/v1/analytics/ai-usage`).
- **Zaxira nusxa:** `tc2_pgdata` va `tc2_storage` volume'larini zaxiraga qo'shing.
- **O'chirish:** platforma `.env`dagi `TEST_CREATOR_URL` ni bo'sh qoldirsangiz, "Test banki" o'chadi (endpoint `400` qaytaradi),
  qolgan platformaga ta'sir qilmaydi.
- **SSO (CRM orqali yagona kirish)** Test-creator'da bor, lekin bu ulanishda ishlatilmaydi (`SSO_ENABLED=false`): foydalanuvchi
  uning o'z paneliga kirmaydi.
