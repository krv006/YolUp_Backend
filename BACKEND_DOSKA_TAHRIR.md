# Doska: kod muharriri (Notepad++ uslubi) va elementni tahrirlash (Zoom uslubi) — backend tayyor

Sana: 2026-11-09. Sizning ro'yxatingizdan nima backendda, nima frontendda:

| Talab | Kimda | Holat |
|---|---|---|
| Notepad++ kabi **kod bloki**, til bo'yicha **ranglash** (SQL yozsa SQL ranglanadi) | Saqlash/til ro'yxati — backend; **ranglash brauzerda** — frontend | Backend **tayyor** |
| Yozilgan obyektni **o'zgartirish** (matnni tahrirlash, ko'chirish, rang/o'lcham) — Zoom "edit mode" | Backend: yangi endpoint + socket hodisa; chizish (tutqichlar, tanlash) — frontend | Backend **tayyor** |
| Yonib-o'chib turuvchi **kursor** (caret) | **Faqat frontend** (backend kerak emas) | — |
| Dars tugagach doska PDF/rasm ham kodni **ranglangan** ko'rsatadi | Backend | **tayyor** |

---

## 1. Yangi element turi: `code`

Mavjud `POST /api/v1/board/<lesson_id>/stroke/` (yoki WebSocket `{"type":"stroke"}`) orqali qo'shiladi — boshqa elementlar bilan bir xil.

```json
{
  "sheet": 0,
  "stroke": {
    "type": "code",
    "text": "SELECT name\nFROM students\n    WHERE age > 18;",
    "language": "sql",
    "x": 80, "y": 120,
    "size": 20,
    "color": "#1c1e3a",
    "w": 520
  }
}
```

| Maydon | Qoida |
|---|---|
| `text` | Majburiy (bo'sh bo'lmasin), eng ko'pi 6000 belgi. **Boshidagi probellar (indent) saqlanadi.** `\r\n` → `\n` |
| `language` | Ro'yxatdan (pastda). Berilmasa `auto`. Noma'lum til → `400` |
| `x`, `y` | **Birinchi qatorning bazaviy chizig'i** `y` da (matn bilan bir xil). Sheet 1600 × 900 |
| `size` | 12–48, standart **20** |
| `color` | Oddiy matn rangi (ranglanmagan qismlar uchun) |
| `w` | Ixtiyoriy: quti kengligi (o'lchamini o'zgartirganda). 40 dan `sheet kengligi − x` gacha |

Javobda server `id`, `by` (ism) va **`by_id`** (muallif user id) qo'shib qaytaradi.

### Til ro'yxati — yagona manba: doska javobida

`GET /api/v1/board/<lesson_id>/` javobiga **ikkita yangi maydon** qo'shildi:

```json
"code_enabled": true,
"code_languages": [
  {"id": "auto", "label": "Avto"}, {"id": "sql", "label": "SQL"}, {"id": "python", "label": "Python"},
  {"id": "javascript", "label": "JavaScript"}, {"id": "typescript", "label": "TypeScript"},
  {"id": "html", "label": "HTML"}, {"id": "css", "label": "CSS"}, {"id": "java", "label": "Java"},
  {"id": "csharp", "label": "C#"}, {"id": "cpp", "label": "C++"}, {"id": "c", "label": "C"},
  {"id": "php", "label": "PHP"}, {"id": "json", "label": "JSON"}, {"id": "bash", "label": "Bash"},
  {"id": "plaintext", "label": "Oddiy matn"}
]
```

* `code_enabled` — **kod tugmasini ko'rsatish uchun flag**: faqat **Informatika** kursida `true` (`math_enabled`, `chemistry_enabled` kabi). Element backendda barcha fanlarda saqlanadi (zararsiz matn), tugmani ko'rsatish — sizning qaroringiz.
* Tilni qo'lda tanlash ro'yxati — `code_languages` dan oling, frontendda qattiq yozmang.

### "SQL yozsa SQL ranglansin" — frontend vazifasi

Ranglash **brauzerda** bo'ladi (backend ranglangan HTML yubormaydi):

1. Foydalanuvchi tilni tanlasa (`language: "sql"`) — o'sha til bilan ranglang.
2. `language: "auto"` bo'lsa — kutubxonaning avto-aniqlashidan foydalaning (masalan **highlight.js** `highlightAuto` yoki **CodeMirror 6** til paketlari). Aniqlangan tilni element ichida `language` ga **yozib yuborish shart emas** — `auto` qolishi mumkin; lekin yozib yuborsangiz (masalan "avto-aniqlandi: sql") PDF ham aynan shu til bilan chiqadi — **tavsiya etiladi**.
3. Moslik uchun id lar: `sql, python, javascript, typescript, html, css, java, csharp, cpp, c, php, json, bash, plaintext` — highlight.js / CodeMirror nomlariga to'g'ridan-to'g'ri mos keladi (`csharp`, `cpp` ham).
4. Shrift — **monospace**; indent va bo'sh qatorlar saqlanadi (`white-space: pre`). Tab → 4 probel deb hisoblang.

Dars tugagach hosil bo'ladigan **PDF** va uy vazifasi **rasmlarida** kod serverda ranglanadi (kulrang fon `#f6f8fa`, kalit so'zlar qizil, satrlar to'q ko'k, izohlar kulrang, sonlar ko'k). Server `auto` ni matndan o'zi taxmin qiladi (SQL, Python, JS, HTML, Java, C++, JSON va h.k.).

**Chizish qoidasi (PDF bilan bir xil ko'rinishi uchun):** birinchi qator bazaviy chizig'i `y` da, qatorlar oralig'i **size × 1.35**, fon to'rtburchagi matndan chapga/o'ngga **8 px** kengroq, yuqorida ~size × 1.05, pastda ~size × 0.45.

---

## 2. Mavjud elementni tahrirlash — YANGI

Hamma element turi (`text`, `code`, `math`, `line`, `rect`, `ellipse`, qalam chizig'i) uchun bitta endpoint.

```
PATCH /api/v1/board/<lesson_id>/stroke/<stroke_id>/
```

```json
{ "sheet": 0, "changes": { "text": "Yangi matn", "color": "#ff0000", "size": 28 } }
```

```json
{ "sheet": 0, "move": [40, -15] }
```

Ikkalasini birga ham yuborish mumkin. Kamida bittasi bo'lishi shart.

| Parametr | Ma'nosi |
|---|---|
| `sheet` | Sahifa raqami |
| `changes` | O'zgargan maydonlar (faqat o'zgarganlarini yuboring): matn tahriri (`text`), `language`, `color`, `size`, `w`, shakl koordinatalari (`x, y, w, h` / `x1..y2`), `latex` (formula), `width`... Server qolgan maydonlarni saqlab qoladi |
| `move` | `[dx, dy]` — **qancha surish** (mutlaq koordinata emas). Server **hamma tur uchun** to'g'ri suradi (qalam chizig'ining barcha nuqtalarini ham — minglab nuqtani yubormaysiz). Shakl sheet chegarasidan chiqib ketmaydi: surish chegarada **kesiladi**, shakl buzilmaydi |

Javob `200`: **yangilangan to'liq element** (`id`, `by`, `by_id`, `edited_by` bilan).

### Qoidalar
* **Turi** (`type`), `id`, `by`, `by_id` o'zgarmaydi (yuborilsa e'tiborsiz; `type` boshqa qiymat bo'lsa `400`).
* **Kim tahrirlay oladi:** o'qituvchi — **hamma** elementni; chizish ruxsati olgan o'quvchi — faqat **o'zi yozgan** elementni (`by_id` o'ziniki bo'lsa). Boshqasi `403`. Ruxsati yo'q o'quvchi — `403`.
  * Eslatma: **eski elementlarda** (bu yangilanishdan oldin chizilgan) `by_id` yo'q — ularni faqat o'qituvchi tahrirlaydi.
  * UI: o'quvchi uchun boshqa birovning elementida tutqichlar/tahrirlashni ko'rsatmang (`element.by_id === me.id` yoki o'qituvchi).
* Validatsiya yaratishdagi bilan **bir xil** (bo'sh matn, noma'lum til, noto'g'ri koordinata → `400`).
* Element topilmasa `404`. Nima o'zgarishi ko'rsatilmasa `400`.
* Har tahrir jurnalga yoziladi (`board.edit`).
* **Bir vaqtda ikki kishi** bitta elementni o'zgartirsa — oxirgi yozuv g'olib (qulf yo'q). Odatdagi darsda muammo emas.

### Qachon yuborish kerak
So'rovni **tahrir tugaganda** yuboring, har tugma bosilishida emas:
* matn — kursor elementdan chiqqanda (blur) yoki tasdiqlaganda;
* ko'chirish/o'lcham — sichqoncha **qo'yib yuborilganda** (`mouseup`), sudrash davomida emas (sudrash paytida faqat o'z ekraningizda ko'rsating).

---

## 3. Real vaqt (WebSocket)

Ulanish o'sha: `wss://<domain>/ws/board/<lesson_id>/?token=<JWT>`.

**Yuborish** (REST PATCH bilan teng kuchli; xato bo'lsa faqat yuboruvchiga `{"type":"error","detail":"..."}`):

```json
{"type": "update", "sheet": 0, "stroke_id": "a1b2c3d4e5f6", "changes": {"text": "Yangi"}, "move": [10, 0]}
```

**Qabul qilish** (hamma ishtirokchiga, yuboruvchining o'ziga ham):

```json
{"type": "stroke_updated", "sheet": 0, "stroke": { "id": "a1b2c3d4e5f6", "type": "text", "text": "Yangi", "...": "..." }}
```

Mijoz `stroke.id` bo'yicha o'z ro'yxatidagi elementni **to'liq almashtiradi** (qisman emas). Element tartibi (qatlam) o'zgarmaydi.

Boshqa hodisalar o'zgarmadi (`stroke`, `erase`, `sheet`, `sheet_renamed`, `current_sheet`, ...). `GET /board/<id>/` har doim eng so'nggi holatni beradi.

---

## 4. Kursor (blinking caret) — faqat frontend

Backend'ga hech narsa kerak emas. Maslahat: matn/kod elementiga bosganda `contenteditable` yoki `<textarea>` ochiladi (brauzerning o'z yonib-o'chuvchi kursori ishlaydi); tahrir tugagach `PATCH` yuboring (2-bo'lim). Kod uchun CodeMirror 6 yoki Monaco ishlatsangiz kursor, ranglash, indent, avto-aniqlash tayyor keladi.

---

## 5. Test qilish uchun misollar

```bash
# kod qo'shish
curl -X POST .../api/v1/board/$LESSON/stroke/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"stroke":{"type":"code","text":"SELECT 1;","language":"sql","x":80,"y":120}}'

# matnni tahrirlash
curl -X PATCH .../api/v1/board/$LESSON/stroke/$ID/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"changes":{"text":"SELECT 2;"}}'

# ko'chirish
curl -X PATCH .../api/v1/board/$LESSON/stroke/$ID/ -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"sheet":0,"move":[100,50]}'
```

## 6. Aytmaganlari (halol)

* **Rotatsiya, qatlam tartibi (oldinga/orqaga), guruhlash, nusxalash/qo'yish** — hozircha yo'q. Kerak bo'lsa ayting: nusxalash uchun yangi element qo'shish (POST) yetadi, qatlam/rotatsiya esa kichik qo'shimcha.
* Elementni o'chirish eskicha: `POST /board/<id>/erase/` — **sabab majburiy**.
* Boshqa odamning kursorini (Zoom'dagi kabi "kim qayerda yozyapti") ko'rsatish hozircha yo'q.
* Bir vaqtda bitta elementni **birgalikda yozish** (Google Docs kabi) yo'q — oxirgi yozuv g'olib.
