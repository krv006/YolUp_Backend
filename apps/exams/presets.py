"""Tayyor imtihon shablonlari (IELTS, SAT, Milliy sertifikat).

Shablon — bo'limlar va tanaffuslar zanjiri + ball hisoblash qoidasi
(`scoring.py` dagi dvigatel nomi). Tayyor shablonlar kodda turadi (DB'da emas):
imtihon yaratilganda shablon nusxasi (`ExamSection` qatorlari + `Exam.scoring`)
imtihonning o'ziga ko'chiriladi, shuning uchun keyingi o'zgarishlar eski
imtihonlarga ta'sir qilmaydi.

Element turlari (`type`):
  section — vaqtli bo'lim (test biriktiriladi), `minutes` majburiy;
  break   — tanaffus (taymer ishlaydi, test yo'q);
  offline — imtihon vaqtida o'tmaydigan qism (masalan IELTS Speaking) —
            balli o'qituvchi keyin qo'lda kiritadi.
`manual: True` — bo'lim ballini o'qituvchi qo'lda qo'yadi (avtomatik tekshirib
bo'lmaydi: IELTS Writing/Speaking). `questions` — faqat tavsiya (UI uchun).
"""

SYSTEM_TEMPLATES = {
    'ielts': {
        'name': 'IELTS',
        'description': "Listening 30, Reading 60, Writing 60 daqiqa (tanaffussiz); Speaking alohida.",
        'scoring': {'type': 'ielts'},
        'items': [
            {'type': 'section', 'key': 'listening', 'title': 'Listening', 'minutes': 30, 'questions': 40},
            {'type': 'section', 'key': 'reading', 'title': 'Reading', 'minutes': 60, 'questions': 40},
            {'type': 'section', 'key': 'writing', 'title': 'Writing', 'minutes': 60, 'manual': True},
            {'type': 'offline', 'key': 'speaking', 'title': 'Speaking', 'manual': True},
        ],
    },
    'sat': {
        'name': 'SAT',
        'description': "Reading & Writing (2 modul), 10 daqiqa tanaffus, Math (2 modul).",
        'scoring': {'type': 'sat'},
        'items': [
            {'type': 'section', 'key': 'rw_1', 'title': 'Reading & Writing — 1-modul',
             'minutes': 32, 'group': 'rw', 'questions': 27},
            {'type': 'section', 'key': 'rw_2', 'title': 'Reading & Writing — 2-modul',
             'minutes': 32, 'group': 'rw', 'questions': 27},
            {'type': 'break', 'key': 'break', 'title': 'Tanaffus', 'minutes': 10},
            {'type': 'section', 'key': 'math_1', 'title': 'Math — 1-modul',
             'minutes': 35, 'group': 'math', 'questions': 22},
            {'type': 'section', 'key': 'math_2', 'title': 'Math — 2-modul',
             'minutes': 35, 'group': 'math', 'questions': 22},
        ],
    },
    'milliy': {
        'name': 'Milliy sertifikat',
        'description': "Bitta fan bo'yicha imtihon (matematika uchun 150 daqiqa — fanga qarab vaqtni o'zgartiring).",
        'scoring': {'type': 'milliy'},
        'items': [
            {'type': 'section', 'key': 'main', 'title': 'Imtihon', 'minutes': 150},
        ],
    },
}
