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


def _satisfies(equation: str, value: Fraction):
    """True/False: `value` tenglamaga qo'yilganda ikki tomon tengmi. Tekshirib bo'lmasa None."""
    text = str(equation or '').replace('−', '-').replace('×', '*').replace('·', '*').replace('÷', '/')
    if text.count('=') != 1 or not re.search(r'(?<![A-Za-z])x(?![A-Za-z])', text) or len(text) > MAX_EXPRESSION:
        return None
    text = re.sub(r'(\d)\s*([x(])', r'\1*\2', text)  # 3x -> 3*x, 2(x+1) -> 2*(x+1)
    text = re.sub(r'\)\s*\(', ')*(', text)          # (a)(b) -> (a)*(b)
    text = re.sub(r'\)\s*x', ')*x', text)           # (a)x -> (a)*x
    text = re.sub(r'x\s*\(', 'x*(', text)           # x(a) -> x*(a)
    text = re.sub(r'(?<![A-Za-z])x(?![A-Za-z])', f'({value.numerator}/{value.denominator})', text)
    left, right = text.split('=')
    try:
        return _close(evaluate(left), evaluate(right))
    except Unsafe:
        return None


_EQUATION_RUN = re.compile(r'[0-9x+\-*/().\s−×÷]*=[0-9x+\-*/().\s−×÷]*')
_ASKS_FOR_X = re.compile(r'\b(?:of|for|is|find|determine|solve)\s+x(?![A-Za-z0-9])|(?<![A-Za-z0-9])x\s*\?', re.IGNORECASE)
_LONE_X = re.compile(r'(?<![A-Za-z])x(?![A-Za-z])')


def equation_of(raw: dict) -> str:
    """Savoldagi tenglama: modelning `equation` maydoni; yo'q bo'lsa — savol matnida bitta tenglama bor va savol aynan `x` ni
    so'rasa ("Solve for x: 3x+5=2x+15", "What is x in 4x+2=2x+1?") shu tenglama. "If x = 3, what is 2x+1?" kabilarga tegilmaydi.
    Aniqlanmasa ''."""
    if not isinstance(raw, dict):
        return ''
    given = str(raw.get('equation') or '').strip()
    if given:
        return given
    text = str(raw.get('text') or '')
    if text.count('=') != 1:
        return ''
    runs = [run.strip() for run in _EQUATION_RUN.findall(text) if '=' in run]
    runs = [run for run in runs if _LONE_X.search(run)]
    if len(runs) != 1 or runs[0].count('=') != 1:
        return ''
    rest = _ASKS_FOR_X.sub(' ', text.replace(runs[0], ' '))
    return '' if _LONE_X.search(rest) else runs[0]


def satisfying_options(equation, options) -> list | None:
    """Tenglama (bitta noma'lum `x`, ko'paytirish aniq yoki "3x" ko'rinishida) uchun variantlardan qaysilari uni qanoatlantiradi
    (indekslar). Tenglamani/variantlarni tekshirib bo'lmasa — None (savol o'z holicha qoladi)."""
    if not isinstance(options, (list, tuple)) or not options:
        return None
    verdicts = []
    for option in options:
        value = number_in(option)
        verdicts.append(_satisfies(equation, value) if value is not None else None)
    if all(v is None for v in verdicts):
        return None
    return [index for index, ok in enumerate(verdicts) if ok]


def contradicts(raw: dict) -> bool:
    """True — savolda "check" ifodasi bor, hisoblab bo'ldi va javob bilan MOS KELMAYDI (savol yaroqsiz).
    Tekshirib bo'lmasa (ifoda yo'q/noto'g'ri, javob son emas) — False: savol o'z holicha qoladi."""
    if isinstance(raw, dict) and raw.get('kind') == 'mcq' and equation_of(raw):
        # tenglama savoli: belgilangan variant tenglamani qanoatlantirmasa — kalit xato
        try:
            index = int(raw.get('answer'))
        except (TypeError, ValueError):
            index = None
        good = satisfying_options(equation_of(raw), raw.get('options'))
        if good is not None and index is not None and index not in good:
            logger.info("AI savoli kaliti tenglamani qanoatlantirmaydi: %s", str(raw.get('text'))[:120])
            return True
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
