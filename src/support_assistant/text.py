"""Arabic/English text normalisation and number handling, shared by the checks and the grader."""
from __future__ import annotations

import itertools
import re

_DIACRITICS = re.compile(r"[ً-ْٰـ]")   # harakat, tanween, dagger alif, tatweel
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NUMBER = re.compile(r"\d+(?:[.,٫٬]\d+)*")


def normalize(text: str) -> str:
    """Lower-case, Western digits, no diacritics, one spelling for alif / ta marbuta / alif maqsura."""
    t = _DIACRITICS.sub("", text.translate(_DIGITS)).lower()
    t = re.sub("[أإآٱ]", "ا", t)
    return t.replace("ة", "ه").replace("ى", "ي")


def numbers(text: str) -> set[float]:
    """Every number in the text. Thousands separators are dropped ("10,000" -> 10000);
    a comma followed by other than exactly three digits is read as a list separator."""
    found: set[float] = set()
    for raw in _NUMBER.findall(text.translate(_DIGITS)):
        raw = raw.replace("٬", ",").replace("٫", ".")
        if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
            found.add(float(raw.replace(",", "")))
            continue
        for part in raw.split(","):
            found.add(float(part))
    return found


# Customers often write small numbers as words ("بعد ثلاث أيام", "two days before"). These count
# as numbers the customer gave, so an answer may use them in digits.
_WORD_NUMBERS = {
    "واحد": 1, "واحده": 1, "اثنين": 2, "اثنان": 2, "ثنتين": 2, "يومين": 2, "ساعتين": 2, "اسبوعين": 2,
    "شهرين": 2, "سنتين": 2, "ثلاث": 3, "ثلاثه": 3, "اربع": 4, "اربعه": 4, "خمس": 5, "خمسه": 5,
    "ست": 6, "سته": 6, "سبع": 7, "سبعه": 7, "ثمان": 8, "ثمانيه": 8, "تسع": 9, "تسعه": 9, "عشر": 10,
    "عشره": 10, "اسبوع": 7, "شهر": 30,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "week": 7, "weeks": 7, "fortnight": 14,
}


def question_numbers(text: str) -> set[float]:
    """Digits plus small numbers written as words."""
    found = numbers(text)
    for w in re.findall(r"\w+", normalize(text)):
        w = w[1:] if w[:1] in "وب" and w[1:] in _WORD_NUMBERS else w
        if w in _WORD_NUMBERS:
            found.add(float(_WORD_NUMBERS[w]))
    return found


def derivable(source: set[float], question: set[float]) -> set[float]:
    """Numbers an answer may contain: the policy's, the customer's, and one step of arithmetic
    that uses a number the customer gave (5000 riyals x 2 points / 10), or a doubling for two
    people named in words ("me and my wife": 300 x 2). Other arithmetic on policy numbers alone
    is not allowed — otherwise 150 + 150 would let an invented 300 through."""
    out = set(source) | set(question)
    pool = {a for a in source | question if a != 0}
    q = {a for a in question if a != 0}
    for a, b in itertools.product(pool, repeat=2):
        if a in q or b in q:
            out.update({a + b, abs(a - b), a * b, round(a / b, 4)})
    for a, b, c in itertools.product(pool, repeat=3):
        if q & {a, b, c}:
            out.add(round(a * b / c, 4))
    out.update(a * 2 for a in source)
    return out


def has_number(text: str, value: float) -> bool:
    return value in numbers(text)
