from __future__ import annotations

import argparse
import sys

from . import isbn_utils, marc
from .aggregator import lookup
from .formatters import to_card_text, to_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="isbn_cataloger",
        description="إعطاء ISBN والحصول على بيانات الفهرسة (Google Books / Open Library / WorldCat / فهرس عربي SRU).",
    )
    parser.add_argument("isbn", help="رقم ISBN (10 أو 13 خانة)")
    parser.add_argument(
        "--format", choices=["card", "marc", "json", "all"], default="all",
        help="شكل المخرجات (افتراضي: all)",
    )
    parser.add_argument("--out", help="حفظ المخرجات في ملف بدلاً من الطباعة")
    args = parser.parse_args(argv)

    try:
        normalized = isbn_utils.normalize(args.isbn)
    except isbn_utils.InvalidISBNError as exc:
        print(f"خطأ: {exc}", file=sys.stderr)
        return 1

    result = lookup(normalized.isbn13, normalized.isbn10)

    chunks = []
    if args.format in ("card", "all"):
        chunks.append(to_card_text(result))
    if args.format in ("marc", "all"):
        chunks.append("MARC 21\n" + "=" * 40 + "\n" + marc.to_text(result.merged))
    if args.format in ("json", "all"):
        chunks.append(to_json(result))

    output = "\n\n".join(chunks)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"تم الحفظ في: {args.out}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
