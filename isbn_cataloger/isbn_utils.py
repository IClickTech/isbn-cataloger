"""Validation and conversion helpers for ISBN-10 / ISBN-13."""
from __future__ import annotations

import re
from dataclasses import dataclass


class InvalidISBNError(ValueError):
    pass


def clean(isbn: str) -> str:
    return re.sub(r"[^0-9Xx]", "", isbn or "").upper()


def isbn13_check_digit(digits12: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits12))
    return str((10 - total % 10) % 10)


def isbn10_check_digit(digits9: str) -> str:
    total = sum(int(d) * (10 - i) for i, d in enumerate(digits9))
    remainder = (11 - total % 11) % 11
    return "X" if remainder == 10 else str(remainder)


def is_valid_isbn13(isbn: str) -> bool:
    isbn = clean(isbn)
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    return isbn13_check_digit(isbn[:12]) == isbn[12]


def is_valid_isbn10(isbn: str) -> bool:
    isbn = clean(isbn)
    if len(isbn) != 10 or not isbn[:9].isdigit():
        return False
    return isbn10_check_digit(isbn[:9]) == isbn[9]


def isbn10_to_isbn13(isbn10: str) -> str:
    isbn10 = clean(isbn10)
    if not is_valid_isbn10(isbn10):
        raise InvalidISBNError(f"ISBN-10 غير صحيح: {isbn10}")
    core = "978" + isbn10[:9]
    return core + isbn13_check_digit(core)


def isbn13_to_isbn10(isbn13: str) -> str | None:
    isbn13 = clean(isbn13)
    if not is_valid_isbn13(isbn13) or not isbn13.startswith("978"):
        return None
    core = isbn13[3:12]
    return core + isbn10_check_digit(core)


@dataclass
class NormalizedISBN:
    isbn10: str | None
    isbn13: str


def normalize(raw_isbn: str) -> NormalizedISBN:
    """Validate an ISBN (10 or 13) and return both forms."""
    value = clean(raw_isbn)
    if len(value) == 13 and is_valid_isbn13(value):
        return NormalizedISBN(isbn10=isbn13_to_isbn10(value), isbn13=value)
    if len(value) == 10 and is_valid_isbn10(value):
        return NormalizedISBN(isbn10=value, isbn13=isbn10_to_isbn13(value))
    raise InvalidISBNError(f"رقم ISBN غير صحيح (فشل فحص رقم التحقق): {raw_isbn}")
