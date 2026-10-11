"""Render a merged BibRecord as a MARC21 field listing.

Only fields we actually have data for are emitted — nothing is invented to
fill in a 'complete-looking' record.
"""
from __future__ import annotations

from .sources.base import BibRecord


def _leader(record: BibRecord) -> str:
    return "00000cam a2200000 i 4500"


def build_fields(record: BibRecord) -> list[tuple[str, str]]:
    """Return a list of (tag, formatted-field-text) pairs, in MARC tag order."""
    fields: list[tuple[str, str]] = [("000", _leader(record))]

    if record.isbn13:
        fields.append(("020", f"## $a {record.isbn13}"))
    if record.dewey:
        fields.append(("082", f"04 $a {record.dewey} $2 23"))
    if record.lcc:
        fields.append(("050", f"#4 $a {record.lcc}"))

    if record.authors:
        fields.append(("100", f"1# $a {record.authors[0]} $e مؤلف."))
        for extra in record.authors[1:]:
            fields.append(("700", f"1# $a {extra} $e مؤلف مشارك."))

    if record.title:
        title_field = f"10 $a {record.title}"
        if record.subtitle:
            title_field += f" : $b {record.subtitle}"
        if record.authors:
            title_field += f" / $c {record.authors[0]}."
        fields.append(("245", title_field))

    if record.edition:
        fields.append(("250", f"## $a {record.edition}."))

    if record.publisher or record.publish_date or record.publish_place:
        parts = []
        if record.publish_place:
            parts.append(f"$a {record.publish_place} :")
        if record.publisher:
            parts.append(f"$b {record.publisher},")
        if record.publish_date:
            parts.append(f"$c {record.publish_date}.")
        fields.append(("264", "#1 " + " ".join(parts)))

    if record.pages:
        fields.append(("300", f"## $a {record.pages} صفحة."))

    if record.language:
        fields.append(("041", f"0# $a {record.language}"))

    for subject in record.subjects:
        fields.append(("650", f"#4 $a {subject}"))

    return fields


def to_text(record: BibRecord) -> str:
    fields = build_fields(record)
    width = max(len(tag) for tag, _ in fields)
    lines = [f"{tag.ljust(width)}    {text}" for tag, text in fields]
    return "\n".join(lines)


def to_marc_binary(record: BibRecord) -> bytes:
    """Build a real ISO 2709 MARC record. Requires the optional `pymarc` package."""
    try:
        from pymarc import Field, Record, Subfield
    except ImportError as exc:
        raise RuntimeError("تحويل إلى MARC ثنائي (.mrc) يتطلب تثبيت الحزمة: pip install pymarc") from exc

    marc_record = Record(leader=_leader(record)[:0].ljust(24))
    for tag, text in build_fields(record):
        if tag == "000":
            continue
        indicators = list(text[:2].replace("#", " "))
        rest = text[3:]
        subfields = []
        for chunk in rest.split("$")[1:]:
            code, _, value = chunk.strip().partition(" ")
            if code:
                subfields.append(Subfield(code=code, value=value.strip()))
        marc_record.add_field(Field(tag=tag, indicators=indicators, subfields=subfields))
    return marc_record.as_marc()
