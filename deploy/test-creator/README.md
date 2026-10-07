# Test-creator ni serverga ulash (savollar banki va test generatori)

`Test-creator` (RJalol) — **alohida ilova** (o'z sayti, bazasi va navbati). O'qituvchi o'quv material yuklaydi,
tizim bilimlar xaritasini tuzadi va **UZBMB, IELTS Academic, Digital SAT** standartlari bo'yicha savollar bankidan
test yig'adi. Tayyor testni Word/Excel/JSON/PDF ga eksport qiladi, **JSON** ni bizning "Testlar → Import"ga yuklash mumkin.

> Bu qadamlar hali **serverda sinalmagan**; birinchi ishga tushirishda kichik tuzatish kerak bo'lsa, xato matnini yuboring.
> Bizning moslashtirishlarimiz (`apply_patch.py`) uning kodiga tegadi: **Gemini provayderi** (Test-creator'da faqat
> mock va Claude bor) va **yopiq ro'yxatdan o'tish** (aks holda ochiq saytda hamma Gemini kalitingizni sarflay oladi).

## 0. DNS (birinchi!)

Domen boshqaruv panelida A yozuv: **`tests.thesofmebel.uz` → `75.119.154.71`**. U ishlamaguncha sayt ochilmaydi
(sertifikat olinmaydi). Tekshirish: `nslookup tests.thesofmebel.uz` serverning IP'sini ko'rsatishi kerak.
Boshqa domen xohlasangiz, `deploy/Caddyfile` va `.env` dagi `TC_DOMAIN` ni o'zgartiring.

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
`auth.py: qo'llandi`. Qayta ishga tushirsa takrorlamaydi (`allaqachon qo'llangan`). `XATO: ... topilmadi` chiqsa,
repo versiyasi o'zgargan — shu xabarni yuboring.

## 3. Sozlama fayli — `/var/www/test-creator/.env`

```bash
cat > /var/www/test-creator/.env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
TC_DB_PASSWORD=$(openssl rand -hex 24)
GEMINI_API_KEY=KALITNI_SHU_YERGA_QOYING
REGISTRATION_ALLOWED_EMAILS=o_qituvchi@example.com
EOF
chmod 600 /var/www/test-creator/.env
```

- `REGISTRATION_ALLOWED_EMAILS` — **ro'yxatdan o'ta oladigan** emaillar (vergul bilan). Boshqa hech kim hisob ocholmaydi.
  Haqiqiy o'qituvchi emaillarini yozing.
- Gemini kalitini (ekranda ko'rinmasdan) qo'yish:

```bash
read -rsp "Gemini kaliti: " K && echo && sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$K|" /var/www/test-creator/.env && unset K && echo "kalit yangilandi"
```

## 4. Ishga tushirish

```bash
cd /var/www/edu_platform && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env up -d --build
```

Birinchi yig'ish 5-10 daqiqa (frontend `npm install` va `next build`). Holat:

```bash
cd /var/www/edu_platform && docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env ps
```

`tc-api` `healthy` (birinchi marta 1-2 daqiqa: migratsiya va standartlarni yuklaydi), `tc-worker`, `tc-frontend`, `tc-db`, `tc-redis` `Up`.

## 5. Caddy'ni qayta yaratish (yangi sayt va papka ulanishi)

```bash
cd /var/www/edu_platform && docker compose -f docker-compose.prod.yml up -d --force-recreate caddy
```

Barcha saytlar 5-10 soniya uziladi (sertifikatlar saqlanadi). Keyin shu buyruq bilan holatni tekshiring:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://tests.thesofmebel.uz/
```

`200` chiqishi kerak. **Bu qadamdan keyin** Caddy sozlamasi `git pull` + `caddy reload` bilan ham yangilanadi (endi qayta yaratish shart emas).

## 6. Ishlatish

1. https://tests.thesofmebel.uz → "Ro'yxatdan o'tish" (faqat 3-qadamdagi emaillar) → kirish.
2. Material yuklash (PDF/DOCX/PPTX/TXT) → standartni tanlash (UZBMB, IELTS Academic, Digital SAT) → test yig'ish.
3. Tayyor testni **JSON, o'qituvchi rejimida** (`mode=teacher`, javoblar bilan) eksport qiling.
4. Bizning saytda **Testlar → Import** ga shu `.json` ni yuklang. Test javoblari bilan, **qoralama** sifatida saqlanadi; tekshirib e'lon qilasiz.
   (Word/Excel eksporti ham ishlaydi, lekin JSON eng aniq.)

Yangi o'qituvchi qo'shish: `.env` dagi `REGISTRATION_ALLOWED_EMAILS` ga emailini qo'shing va
`docker compose -f deploy/test-creator/docker-compose.tc.yml --env-file /var/www/test-creator/.env up -d --force-recreate tc-api tc-worker`.

## Bilib qo'ying

- **Sifat:** savollarni Gemini yozadi (mock emas), lekin Test-creator o'z "sifat bali" tizimiga ega: 90+ avtomatik tasdiqlanadi,
  70-89 qo'lda ko'rib chiqishga tushadi. Baribir har bir testni o'qituvchi ko'zdan kechirsin.
- **Maxfiylik:** yuklangan material va savollar Test-creator bazasida (`tc_pgdata`) saqlanadi va Gemini'ga (Google) yuboriladi.
  Bolalarning shaxsiy ma'lumotini yuklamang (faqat o'quv material).
- **Zaxira nusxa:** `tc_pgdata` va `tc_storage` volume'larini zaxiraga qo'shing.
- **Xavfsizlik:** tashqariga faqat sayt ochiq (API hujjatlari `/docs` yopilgan); baza va Redis portlari ochilmagan.
