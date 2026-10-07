"""Uy vazifasi: fayl qoidalari va ball -> baho yorlig'i.

(Oldin `ai.py` ichida edi — AI tekshiruv olib tashlangach, shu qoidalar saqlandi.)
"""

ALLOWED_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.docx',
    '.mp3', '.wav', '.m4a', '.ogg',
}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg'}
MAX_FILE_SIZE_MB = 25

# Til fanlari uchun ko'nikmalar (Assignment.skill_key)
SKILL_KEYS = ('writing', 'reading', 'listening', 'speaking')

# 0-100 ball -> baho yorlig'i
GRADE_SCALE = [
    (90, "A'lo"),
    (80, 'Juda yaxshi'),
    (70, 'Yaxshi'),
    (60, 'Qoniqarli'),
    (50, 'Yaxshilash kerak'),
    (0, "Jiddiy yaxshilash kerak"),
]


def grade_label(score) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return ''
    for low, label in GRADE_SCALE:
        if value >= low:
            return label
    return GRADE_SCALE[-1][1]
