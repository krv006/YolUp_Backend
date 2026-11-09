"""Doskadagi `code` elementini PDF va rasmga ranglab chizish uchun yordamchilar (Pygments bo'lmasa — oddiy rangda).

Brauzerda ranglashni frontend (highlight.js va h.k.) qiladi; bu modul faqat dars tugagach hosil bo'ladigan PDF va uy vazifasi
rasmlarida kod doskadagidek ko'rinishi uchun. Ranglar GitHub "light" uslubiga yaqin.
"""
import re
from pathlib import Path

# Frontend tanlov ro'yxati uchun: (id, ko'rinadigan nom). `auto` — til matndan aniqlanadi.
CODE_LANGUAGES = [
    ('auto', 'Avto'), ('sql', 'SQL'), ('python', 'Python'), ('javascript', 'JavaScript'), ('typescript', 'TypeScript'),
    ('html', 'HTML'), ('css', 'CSS'), ('java', 'Java'), ('csharp', 'C#'), ('cpp', 'C++'), ('c', 'C'), ('php', 'PHP'),
    ('json', 'JSON'), ('bash', 'Bash'), ('plaintext', 'Oddiy matn'),
]
CODE_LANGUAGE_IDS = {language_id for language_id, _label in CODE_LANGUAGES}

# bizning id -> Pygments lexer nomi
_LEXER_NAMES = {
    'sql': 'sql', 'python': 'python', 'javascript': 'javascript', 'typescript': 'typescript', 'html': 'html', 'css': 'css',
    'java': 'java', 'csharp': 'csharp', 'cpp': 'cpp', 'c': 'c', 'php': 'php', 'json': 'json', 'bash': 'bash',
}

COLORS = {
    'keyword': '#d73a49', 'string': '#032f62', 'comment': '#6a737d', 'number': '#005cc5', 'function': '#6f42c1',
    'type': '#e36209',
}
BACKGROUND = '#f6f8fa'
LINE_HEIGHT = 1.35  # qator oralig'i = o'lcham x 1.35 (frontend va render.py bilan bir xil)

_FONT_PATH = None


def mono_font_path():
    """Unicode'ni biladigan monospace shrift (matplotlib bilan keladi); topilmasa None."""
    global _FONT_PATH
    if _FONT_PATH is None:
        try:
            import matplotlib

            path = Path(matplotlib.get_data_path()) / 'fonts' / 'ttf' / 'DejaVuSansMono.ttf'
            _FONT_PATH = str(path) if path.exists() else ''
        except Exception:  # noqa: BLE001
            _FONT_PATH = ''
    return _FONT_PATH or None


_DETECT_RULES = [
    ('html', re.compile(r'^\s*(<!doctype html|<html|<div|<body|<head|<p[ >]|<span|<ul|<h[1-6][ >])', re.I)),
    ('sql', re.compile(r'^\s*(select\b[\s\S]*\bfrom\b|insert\s+into\b|update\b[\s\S]*\bset\b|delete\s+from\b|create\s+(table|database|index|view)\b|alter\s+table\b|drop\s+table\b)', re.I)),
    ('python', re.compile(r'^\s*(def\s+\w+\s*\(|class\s+\w+.*:|import\s+\w+|from\s+[\w.]+\s+import\b|print\s*\(|if\s+.+:\s*$|for\s+\w+\s+in\s+.+:|elif\b|#!.*python)', re.M)),
    ('java', re.compile(r'(\bpublic\s+(static\s+)?(class|void)\b|System\.out\.print)')),
    ('csharp', re.compile(r'(\busing\s+System\b|Console\.WriteLine|\bnamespace\s+\w+)')),
    ('cpp', re.compile(r'(#include\s*<\w+>|std::|cout\s*<<|using\s+namespace\s+std)')),
    ('php', re.compile(r'<\?php')),
    ('bash', re.compile(r'^(#!/bin/(ba)?sh|\s*(sudo|apt|cd|ls|echo|chmod|mkdir)\s)', re.M)),
    ('json', re.compile(r'^\s*[\[{]\s*("|\[|\{|\])')),
    ('css', re.compile(r'^\s*[.#]?[\w-]+\s*\{[^}]*:\s*[^}]*;', re.M)),
    ('typescript', re.compile(r'(:\s*(string|number|boolean)\b|\binterface\s+\w+|\btype\s+\w+\s*=)')),
    ('javascript', re.compile(r'(\b(const|let|var)\s+\w+\s*=|\bfunction\s*\w*\s*\(|=>|console\.log|document\.)')),
    ('c', re.compile(r'(#include\s*<stdio\.h>|\bprintf\s*\(|\bint\s+main\s*\()')),
]


def detect_language(code: str) -> str:
    """Til `auto` bo'lganda matndan taxmin qiladi (PDF/rasm uchun; brauzerda frontend o'zi aniqlaydi). Aniqlanmasa `plaintext`."""
    sample = (code or '')[:2000]
    for language, pattern in _DETECT_RULES:
        if pattern.search(sample):
            return language
    return 'plaintext'


def _lexer(code: str, language: str):
    from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer

    if language in _LEXER_NAMES:
        try:
            return get_lexer_by_name(_LEXER_NAMES[language])
        except Exception:  # noqa: BLE001
            return TextLexer()
    if language == 'auto':
        detected = detect_language(code)
        if detected in _LEXER_NAMES:
            return get_lexer_by_name(_LEXER_NAMES[detected])
        try:
            return guess_lexer(code)
        except Exception:  # noqa: BLE001
            return TextLexer()
    return TextLexer()


def _color_for(token_type, base: str) -> str:
    from pygments.token import Token

    if token_type in Token.Comment:
        return COLORS['comment']
    if token_type in Token.Literal.String:
        return COLORS['string']
    if token_type in Token.Literal.Number:
        return COLORS['number']
    if token_type in Token.Keyword.Type or token_type in Token.Name.Class or token_type in Token.Name.Builtin:
        return COLORS['type']
    if token_type in Token.Keyword or token_type in Token.Operator.Word:
        return COLORS['keyword']
    if token_type in Token.Name.Function:
        return COLORS['function']
    return base


def highlight_lines(code: str, language: str = 'auto', base: str = '#1c1e3a') -> list:
    """Matnni qatorlarga bo'lib, har qatorni [(bo'lak, rang), ...] ko'rinishida qaytaradi. Pygments yo'q/xato bo'lsa — bir rang."""
    code = (code or '').replace('\r\n', '\n').replace('\t', '    ')
    plain = [[(line, base)] for line in code.split('\n')]
    if language == 'plaintext':
        return plain
    try:
        tokens = list(_lexer(code, language).get_tokens(code))
    except Exception:  # noqa: BLE001 - ranglash hech qachon PDF/rasmni yiqitmasin
        return plain
    lines = [[]]
    for token_type, value in tokens:
        color = _color_for(token_type, base)
        parts = value.split('\n')
        for index, part in enumerate(parts):
            if index:
                lines.append([])
            if part:
                lines[-1].append((part, color))
    while len(lines) > 1 and not lines[-1]:  # Pygments oxiriga qo'shgan bo'sh qator
        lines.pop()
    return lines or plain
