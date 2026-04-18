"""Slug generation and validation.

Handles Cyrillic via a minimal transliteration table — достаточно для русских title'ов
контента. Если встретится другой алфавит (китайский, арабский) — добавить позже.
"""
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_SLUG_RE = re.compile(r"^[a-z0-9-]{2,100}$")


def slugify(text: str) -> str:
    text = text.strip().lower()
    out = []
    for ch in text:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
        # прочее (пунктуация, эмодзи) — выкидываем
    result = "".join(out)
    # сжать серии дефисов и обрезать
    result = re.sub(r"-+", "-", result).strip("-")
    return result[:100]


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))
