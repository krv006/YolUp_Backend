"""AI yozgan hisob-kitob savollarining javobini mustaqil tekshirish.

Model savol bilan birga `"check": "3*(4+5)"` — to'g'ri javobga teng sof arifmetik ifoda — qaytaradi. Biz uni o'zimiz
hisoblaymiz va savolning javobi bilan solishtiramiz: mos kelmasa savol tashlab yuboriladi (zaxira savol o'rniga
keladi). Ifoda model chiqargan, ya'ni ishonchsiz matn, shuning uchun `eval`/`sympify` ishlatilmaydi: faqat raqamlar va
+ - * / ** ( ) sqrt() ga ruxsat beruvchi `ast` hisoblagich (aniq kasrlar, daraja va uzunlik cheklangan)."""
import ast
import logging
import math
import re
from fractions import Fraction

logger = logging.getLogger(__name__)

MAX_EXPRESSION = 160
MAX_EXPONENT = 12
MAX_ABS = 10 ** 15
_NUMBER = re.compile(r'-?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?')


class Unsafe(ValueError):
    """Ifoda ruxsat etilgan arifmetikadan tashqarida (yoki hisoblab bo'lmaydi)."""


def _num(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return Fraction(str(node.value))
    raise Unsafe('constant')


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return _num(node)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise Unsafe('division by zero')
            result = left / right
        elif isinstance(node.op, ast.Pow):
            if right.denominator != 1 or abs(right) > MAX_EXPONENT or abs(left) > MAX_ABS:
                raise Unsafe('exponent')
            if left == 0 and right < 0:
                raise Unsafe('division by zero')
            result = left ** int(right)
        else:
            raise Unsafe('operator')
        if abs(result) > MAX_ABS ** 2:
            raise Unsafe('too large')
        return result
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'sqrt' \
            and len(node.args) == 1 and not node.keywords:
        value = _eval(node.args[0])
        if value < 0:
            raise Unsafe('sqrt of negative')
        num, den = math.isqrt(value.numerator), math.isqrt(value.denominator)
        if num * num == value.numerator and den * den == value.denominator:
            return Fraction(num, den)  # to'liq kvadrat — aniq javob
        return Fraction(math.sqrt(float(value))).limit_denominator(10 ** 9)
    raise Unsafe('syntax')


def evaluate(expression) -> Fraction:
    """`"3*(4+5)"` -> Fraction(27). Ruxsatsiz/noto'g'ri ifodada `Unsafe`."""
    text = str(expression or '').strip()
    if not text or len(text) > MAX_EXPRESSION:
        raise Unsafe('length')
    text = text.replace('×', '*').replace('·', '*').replace('÷', '/').replace('−', '-').replace('^', '**')
    text = re.sub(r'(?<=\d),(?=\d)', '.', text)  # 1,5 -> 1.5
    text = re.sub(r'√\s*\(', 'sqrt(', text)
    if not re.fullmatch(r'[0-9+\-*/().\s]*(?:(?:sqrt)[0-9+\-*/().\s]*)*', text):
        raise Unsafe('characters')
    try:
        return _eval(ast.parse(text, mode='eval'))
    except (SyntaxError, RecursionError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise Unsafe(str(exc)) from exc


def number_in(text):
    """Javob matnidagi birinchi son ("27 cm", "-3,5", "3/4") yoki None."""
    match = _NUMBER.search(str(text or '').replace('−', '-'))
    if not match:
        return None
    raw = re.sub(r'\s+', '', match.group()).replace(',', '.')
    try:
        return Fraction(raw)
    except (ValueError, ZeroDivisionError):
        return None


def _close(a: Fraction, b: Fraction, tolerance: float = 0) -> bool:
    allowed = max(Fraction(str(tolerance or 0)), abs(b) * Fraction(1, 10 ** 6))  # nisbiy 1e-6 — yaxlitlash uchun
    return abs(a - b) <= allowed


def stated_answers(raw: dict) -> list:
    """Modelning o'z javob(lar)i sonlari — numeric: javoblar ro'yxati; mcq: to'g'ri variant matni. Aniqlanmasa []."""
    kind = raw.get('kind')
    if kind == 'numeric':
        answers = raw.get('answers') if raw.get('answers') is not None else raw.get('answer')
        answers = answers if isinstance(answers, (list, tuple)) else [answers]
        return [n for n in (number_in(a) for a in answers if a is not None) if n is not None]
    if kind == 'mcq':
        options, index = raw.get('options'), raw.get('answer')
        try:
            value = number_in(options[int(index)])
        except (TypeError, ValueError, IndexError, KeyError):
            return []
        return [value] if value is not None else []
    return []


def contradicts(raw: dict) -> bool:
    """True — savolda "check" ifodasi bor, hisoblab bo'ldi va javob bilan MOS KELMAYDI (savol yaroqsiz).
    Tekshirib bo'lmasa (ifoda yo'q/noto'g'ri, javob son emas) — False: savol o'z holicha qoladi."""
    if not isinstance(raw, dict) or not raw.get('check'):
        return False
    try:
        truth = evaluate(raw.get('check'))
    except Unsafe:
        return False
    answers = stated_answers(raw)
    if not answers:
        return False
    tolerance = raw.get('tolerance') if isinstance(raw.get('tolerance'), (int, float)) else 0
    if any(_close(answer, truth, tolerance) for answer in answers):
        return False
    logger.info("AI savoli javobi noto'g'ri (hisob: %s, javob: %s): %s", truth, answers, str(raw.get('text'))[:120])
    return True
