"""Imtihon ball hisoblash dvigatellari (IELTS, SAT, Milliy sertifikat, custom).

`compute(scoring, sections)` toza funksiya — DB'ga tegmaydi, shuning uchun
oson sinaladi. `sections` — bo'limlar ro'yxati, har biri:
    {key, title, group, weight, manual, earned, max, manual_score}
`earned/max` — avtomatik tekshirilgan ball (offline bo'limda None);
`manual_score` — o'qituvchi qo'lda qo'ygan ball (yoki None).

DIQQAT — aniqlik haqida:
  * IELTS Listening/Reading: to'g'ri javoblar -> band jadvali (Academic,
    ochiq ma'lumot). Rasmiy jadval test versiyasiga qarab biroz farq qilishi
    mumkin. Umumiy band 0.5 gacha yaxlitlanadi.
  * SAT: haqiqiy SAT moslashuvchan (adaptive) va rasmiy jadvali yopiq —
    bu yerda 200-800 chiziqli TAXMINIY o'tkazma (`approximate: True`).
  * Milliy sertifikat: rasmiy ball Rasch modeli bilan 75 ballik T-shkalada
    hisoblanadi (savol qiyinligi va ishtirokchilar natijasiga bog'liq) —
    bu yerda foiz * 75 TAXMINIY o'tkazma (`approximate: True`); daraja
    chegaralari rasmiy (A+ >= 70, A 65, B+ 60, B 55, C+ 50, C 46).
"""
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

# (kamida to'g'ri javob soni, band) — kamayish tartibida; 40 savolga normallashtirilgan
_IELTS_LISTENING = [
    (39, 9.0), (37, 8.5), (35, 8.0), (32, 7.5), (30, 7.0), (26, 6.5), (23, 6.0),
    (18, 5.5), (16, 5.0), (13, 4.5), (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5),
    (2, 2.0), (1, 1.0),
]
_IELTS_READING = [
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0), (27, 6.5), (23, 6.0),
    (19, 5.5), (15, 5.0), (13, 4.5), (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5),
    (2, 2.0), (1, 1.0),
]
_IELTS_TABLES = {'listening': _IELTS_LISTENING, 'reading': _IELTS_READING}
_IELTS_MANUAL = ('writing', 'speaking')
_IELTS_ALL = ('listening', 'reading', 'writing', 'speaking')

# Milliy sertifikat daraja chegaralari (rasmiy) — 75 ballik shkalada
MILLIY_MAX = 75
_MILLIY_LEVELS = [(70, 'A+'), (65, 'A'), (60, 'B+'), (55, 'B'), (50, 'C+'), (46, 'C')]

SAT_SECTION_TITLES = {'rw': 'Reading & Writing', 'math': 'Math'}


class ManualScoreError(ValueError):
    pass


def _fraction(section: dict) -> float:
    if section['max']:
        return section['earned'] / section['max']
    return 0.0


def _percent(fraction: float) -> float:
    return round(fraction * 100, 2)


def _round_decimal(value, places: str = '0.1') -> float:
    return float(Decimal(str(value)).quantize(Decimal(places), ROUND_HALF_UP))


def ielts_band(table, fraction: float) -> float:
    """Natijani 40 savollik shkalaga keltirib, jadvaldan band topadi."""
    correct = int(Decimal(str(fraction * 40)).quantize(Decimal('1'), ROUND_HALF_UP))
    for minimum, band in table:
        if correct >= minimum:
            return band
    return 0.0


def round_half_band(value) -> float:
    """IELTS umumiy band: eng yaqin 0.5 (x.25 -> x.5, x.75 -> keyingi butun)."""
    doubled = Decimal(str(value)) * 2 + Decimal('0.5')
    return float(doubled.to_integral_value(ROUND_FLOOR) / 2)


# ---------------------------------------------------------------------------
# Qo'lda ball kiritish validatsiyasi
# ---------------------------------------------------------------------------
def validate_manual(scoring: dict, key: str, value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ManualScoreError('Ball son bo\'lishi kerak.')
    if scoring.get('type') == 'ielts':
        if not 0 <= number <= 9 or (number * 2) % 1:
            raise ManualScoreError("IELTS band 0 dan 9 gacha, 0.5 qadam bilan bo'lishi kerak.")
        return number
    if not 0 <= number <= 100:
        raise ManualScoreError("Ball 0 dan 100 gacha foiz bo'lishi kerak.")
    return number


# ---------------------------------------------------------------------------
# Dvigatellar
# ---------------------------------------------------------------------------
def _base_section(section: dict) -> dict:
    return {
        'key': section['key'], 'title': section['title'], 'group': section.get('group', ''),
        'manual': bool(section.get('manual')),
        'earned': section['earned'], 'max': section['max'],
        'percent': None if section['earned'] is None else _percent(_fraction(section)),
        'score': None, 'scale_max': None,
    }


def _ielts(sections: list) -> dict:
    rows, bands = [], {}
    for section in sections:
        row = _base_section(section)
        key = section['key']
        if key in _IELTS_TABLES and section['earned'] is not None:
            row['score'] = ielts_band(_IELTS_TABLES[key], _fraction(section))
        elif section.get('manual_score') is not None:
            row['score'] = float(section['manual_score'])
        row['scale_max'] = 9
        if key in _IELTS_ALL and row['score'] is not None:
            bands[key] = row['score']
        rows.append(row)
    pending = [k for k in _IELTS_ALL if k not in bands]
    total = None
    if not pending:
        total = {'score': round_half_band(sum(bands.values()) / 4), 'max': 9, 'label': 'Overall band'}
    return {'sections': rows, 'total': total, 'pending': pending, 'approximate': False}


def _sat(sections: list) -> dict:
    rows = [_base_section(s) for s in sections]
    groups: dict = {}
    for section in sections:
        group = section.get('group') or 'rw'
        bucket = groups.setdefault(group, {'earned': 0.0, 'max': 0})
        bucket['earned'] += section['earned'] or 0
        bucket['max'] += section['max'] or 0
    group_rows = []
    for key, bucket in groups.items():
        fraction = bucket['earned'] / bucket['max'] if bucket['max'] else 0.0
        scaled = 200 + int(Decimal(str(600 * fraction / 10)).quantize(Decimal('1'), ROUND_HALF_UP)) * 10
        group_rows.append({
            'key': key, 'title': SAT_SECTION_TITLES.get(key, key),
            'score': scaled, 'min': 200, 'max': 800,
        })
    total = None
    if len(group_rows) == 2:
        total = {'score': sum(g['score'] for g in group_rows), 'max': 1600, 'label': 'SAT total'}
    return {'sections': rows, 'groups': group_rows, 'total': total, 'pending': [], 'approximate': True}


def _milliy(sections: list) -> dict:
    rows = [_base_section(s) for s in sections]
    earned = sum(s['earned'] or 0 for s in sections)
    maximum = sum(s['max'] or 0 for s in sections)
    fraction = earned / maximum if maximum else 0.0
    ball = _round_decimal(fraction * MILLIY_MAX)
    level = next((name for floor, name in _MILLIY_LEVELS if ball >= floor), None)
    total = {'score': ball, 'max': MILLIY_MAX, 'label': 'Milliy sertifikat', 'level': level}
    return {'sections': rows, 'total': total, 'pending': [], 'approximate': True}


def _percent_engine(scoring: dict, sections: list) -> dict:
    rows, weighted, weights, pending = [], 0.0, 0.0, []
    for section in sections:
        row = _base_section(section)
        weight = float(section.get('weight') or 1)
        if section.get('manual') and section.get('manual_score') is not None:
            fraction = float(section['manual_score']) / 100
            row['percent'] = float(section['manual_score'])
        elif section.get('manual'):
            pending.append(section['key'])
            rows.append(row)
            continue
        else:
            fraction = _fraction(section)
        weighted += fraction * weight
        weights += weight
        rows.append(row)
    scale = scoring.get('scale') or 100
    total = None
    if not pending and weights:
        score = _round_decimal(weighted / weights * scale, '0.01')
        total = {'score': score, 'max': scale, 'label': 'Jami'}
        pass_percent = scoring.get('pass_percent')
        if pass_percent is not None:
            total['passed'] = score / scale * 100 >= pass_percent
    return {'sections': rows, 'total': total, 'pending': pending, 'approximate': False}


def compute(scoring: dict, sections: list) -> dict:
    kind = scoring.get('type')
    if kind == 'ielts':
        result = _ielts(sections)
    elif kind == 'sat':
        result = _sat(sections)
    elif kind == 'milliy':
        result = _milliy(sections)
    else:
        result = _percent_engine(scoring, sections)
    result['engine'] = kind or 'percent'
    return result
