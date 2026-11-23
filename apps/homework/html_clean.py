"""O'qituvchi yozgan vazifa matni (rich HTML) ni tozalash (2026-11-23, yangi "Yangi vazifa" muharriri).

Muharrir (TipTap) jadval, rasm, kod bloki, formula (`<span data-type="inline-math" data-latex="...">`), rang va
shrift chiqaradi. Hammasiga RUXSAT BERILADI-YU, lekin faqat o'zimiz tanigan teg/atribut/CSS xossalari va qiymat
shakllari qoladi — qolgani (script, iframe, on* hodisalar, `javascript:` va `data:` havolalar, `url()`, begona
class lar) o'chiriladi. nh3 (Rust ammonia) ishlatiladi.

Rasm manzili faqat bizning yuklash yo'limiz (`/media/homework_images/...`) bo'lishi mumkin: shunda o'quvchi
sahifasi begona saytga so'rov yubormaydi (kuzatuv piksellari, rasmni almashtirib qo'yish).
"""
import re
from urllib.parse import urlparse

IMAGE_PATH_PREFIX = '/media/homework_images/'

ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'sub', 'sup', 'code', 'pre', 'mark', 'span', 'div', 'hr',
    'h1', 'h2', 'h3', 'blockquote', 'ul', 'ol', 'li', 'a', 'img',
    'table', 'colgroup', 'col', 'thead', 'tbody', 'tr', 'th', 'td',
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'target'},
    'img': {'src', 'alt', 'style'},
    'p': {'style'}, 'h1': {'style'}, 'h2': {'style'}, 'h3': {'style'},
    'span': {'style', 'data-type', 'data-latex'},
    'mark': {'style', 'data-color'},
    'div': {'class'},
    'code': {'class'},
    'ol': {'start'},
    'table': {'style'}, 'col': {'style'},
    'td': {'style', 'colspan', 'rowspan', 'data-colwidth'},
    'th': {'style', 'colspan', 'rowspan', 'data-colwidth'},
}

DIV_CLASSES = {'callout', 'tableWrapper'}
MAX_LATEX = 2000

_COLOR = re.compile(
    r'^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d{1,3}(\.\d+)?%?\s*(,\s*\d{1,3}(\.\d+)?%?\s*){2,3}\)|[a-zA-Z]{3,20})$'
)
_FONT_FAMILY = re.compile(r"^[\w\s,'\"-]{1,120}$")
_FONT_SIZE = re.compile(r'^\d{1,3}(\.\d{1,2})?(px|em|rem|%)$')
_SIZE = re.compile(r'^\d{1,4}(\.\d{1,2})?(px|%)$')
_ALIGN = {'left', 'center', 'right', 'justify'}
_LANG_CLASS = re.compile(r'^language-[a-z0-9+#_-]{1,20}$')
_SMALL_INT = re.compile(r'^[1-9]\d{0,2}$')
_COLWIDTH = re.compile(r'^\d{1,4}(,\d{1,4}){0,30}$')
_START = re.compile(r'^\d{1,4}$')
_IMG_WITHOUT_SRC = re.compile(r'<img(?![^>]*\ssrc=)[^>]*>', re.IGNORECASE)


def _clean_style(value: str):
    kept = []
    for declaration in value.split(';'):
        if ':' not in declaration:
            continue
        prop, _, val = declaration.partition(':')
        prop, val = prop.strip().lower(), val.strip()
        if not val or len(val) > 130 or 'url(' in val.lower() or 'expression' in val.lower() or '\\' in val:
            continue
        ok = False
        if prop in ('color', 'background-color'):
            ok = bool(_COLOR.match(val))
        elif prop == 'font-family':
            ok = bool(_FONT_FAMILY.match(val))
        elif prop == 'font-size':
            ok = bool(_FONT_SIZE.match(val))
        elif prop == 'text-align':
            ok = val.lower() in _ALIGN
        elif prop in ('width', 'min-width'):
            ok = bool(_SIZE.match(val))
        if ok:
            kept.append(f'{prop}: {val}')
    return '; '.join(kept) + ';' if kept else None


def _own_image_src(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme not in ('', 'http', 'https'):
        return False
    return parsed.path.startswith(IMAGE_PATH_PREFIX) and '..' not in parsed.path


def _attribute_filter(tag: str, attr: str, value: str):
    if attr == 'style':
        return _clean_style(value)
    if attr == 'class':
        if tag == 'div':
            tokens = value.split()
            return ' '.join(t for t in tokens if t in DIV_CLASSES) or None
        if tag == 'code':
            return value.strip() if _LANG_CLASS.match(value.strip()) else None
        return None
    if tag == 'img':
        if attr == 'src':
            return value if _own_image_src(value) else None
        if attr == 'alt':
            return value[:200]
    if tag == 'a' and attr == 'target':
        return '_blank' if value == '_blank' else None
    if tag == 'span':
        if attr == 'data-type':
            return value if value == 'inline-math' else None
        if attr == 'data-latex':
            return value if len(value) <= MAX_LATEX else None
    if tag == 'mark' and attr == 'data-color':
        return value if _COLOR.match(value) else None
    if attr in ('colspan', 'rowspan'):
        return value if _SMALL_INT.match(value) else None
    if attr == 'data-colwidth':
        return value if _COLWIDTH.match(value) else None
    if tag == 'ol' and attr == 'start':
        return value if _START.match(value) else None
    return value


def clean_rich_html(html: str) -> str:
    """Tozalangan HTML. nh3 yo'q bo'lsa (o'rnatilmagan) — eng konservativ variant: atributsiz oddiy teglar."""
    html = (html or '').strip()
    if not html:
        return ''
    try:
        import nh3
    except ImportError:  # pragma: no cover - nh3 requirements.txt da bor
        return _fallback(html)
    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_attribute_filter,
        link_rel='noopener noreferrer nofollow',
        url_schemes={'http', 'https', 'mailto', 'tel'},
        strip_comments=True,
    )
    return _IMG_WITHOUT_SRC.sub('', cleaned)


_FALLBACK_TAGS = {'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'sub', 'sup', 'h1', 'h2', 'h3', 'ul', 'ol',
                  'li', 'blockquote', 'div', 'span', 'code', 'pre'}


def _fallback(html: str) -> str:  # pragma: no cover
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)

    def _tag(m):
        closing, name = m.group(1), m.group(2).lower()
        return f'<{closing}{name}>' if name in _FALLBACK_TAGS else ''

    return re.sub(r'<\s*(/?)\s*([a-zA-Z0-9]+)[^>]*>', _tag, html)
