"""Human-readable card and JSON views of a merged BibRecord / LookupResult."""
from __future__ import annotations

import json
from dataclasses import asdict

from .aggregator import LookupResult
from .sources.base import BibRecord

NA = "غير متوفر"


def to_card_text(result: LookupResult) -> str:
    r = result.merged
    lines = ["بطاقة الفهرسة (Bibliographic Record)", "=" * 40]
    lines.append(f"العنوان: {r.title or NA}")
    if r.subtitle:
        lines.append(f"العنوان الفرعي: {r.subtitle}")
    lines.append(f"المؤلف/المؤلفون: {', '.join(r.authors) if r.authors else NA}")
    lines.append(f"الناشر: {r.publisher or NA}")
    lines.append(f"مكان النشر: {r.publish_place or NA}")
    lines.append(f"تاريخ النشر: {r.publish_date or NA}")
    lines.append(f"الطبعة: {r.edition or NA}")
    lines.append(f"عدد الصفحات: {r.pages or NA}")
    lines.append(f"اللغة: {r.language or NA}")
    lines.append(f"الردمك (ISBN-13): {r.isbn13 or NA}")
    lines.append(f"الردمك (ISBN-10): {r.isbn10 or NA}")
    lines.append(f"تصنيف ديوي: {r.dewey or NA}")
    lines.append(f"تصنيف مكتبة الكونغرس: {r.lcc or NA}")
    lines.append(f"رؤوس الموضوعات: {', '.join(r.subjects) if r.subjects else NA}")
    lines.append("")
    lines.append(f"المصادر التي أعطت بيانات: {', '.join(rec.source for rec in result.records) or 'لا يوجد'}")
    if result.skipped:
        lines.append("مصادر تم تخطيها أو لم تُعثر على الكتاب فيها:")
        for name, reason in result.skipped:
            lines.append(f"  - {name}: {reason}")
    return "\n".join(lines)


def to_json(result: LookupResult) -> str:
    payload = {
        "isbn13": result.isbn13,
        "isbn10": result.isbn10,
        "merged": asdict(result.merged),
        "sources_used": [asdict(r) for r in result.records],
        "sources_skipped": [{"source": n, "reason": r} for n, r in result.skipped],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
