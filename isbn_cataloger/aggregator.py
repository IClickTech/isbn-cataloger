"""Query every configured source and merge the results into one record."""
from __future__ import annotations

from dataclasses import dataclass, field

from .sources.base import BibRecord, Source, SourceUnavailable
from .sources.arabic_sru import ArabicSRUSource
from .sources.bne import BNESource
from .sources.bnf import BnFSource
from .sources.dnb import DNBSource
from .sources.google_books import GoogleBooksSource
from .sources.kb_netherlands import KBNetherlandsSource
from .sources.loc import LibraryOfCongressSource
from .sources.open_library import OpenLibrarySource
from .sources.worldcat import WorldCatSource

# Priority order: earlier sources win when a field conflicts.
DEFAULT_SOURCES: list[Source] = [
    GoogleBooksSource(),
    OpenLibrarySource(),
    LibraryOfCongressSource(),
    DNBSource(),
    BnFSource(),
    BNESource(),
    KBNetherlandsSource(),
    WorldCatSource(),
    ArabicSRUSource(),
]


def sources_info() -> list[dict]:
    """List every known source with whether it's usable right now (for UI checkboxes)."""
    return [{"name": s.name, "configured": s.configured} for s in DEFAULT_SOURCES]


def sources_by_names(names: list[str]) -> list[Source]:
    """Filter DEFAULT_SOURCES down to the given source names, preserving priority order."""
    return [s for s in DEFAULT_SOURCES if s.name in names]


@dataclass
class LookupResult:
    isbn13: str
    isbn10: str | None
    records: list[BibRecord] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (source name, reason)
    merged: BibRecord | None = None


def lookup(isbn13: str, isbn10: str | None, sources: list[Source] | None = None) -> LookupResult:
    sources = sources if sources is not None else DEFAULT_SOURCES
    result = LookupResult(isbn13=isbn13, isbn10=isbn10)

    for src in sources:
        try:
            record = src.fetch(isbn13, isbn10)
        except SourceUnavailable as exc:
            result.skipped.append((src.name, str(exc)))
            continue
        if record is not None:
            result.records.append(record)
        else:
            result.skipped.append((src.name, "لم يُعثر على الكتاب في هذا المصدر"))

    result.merged = _merge(result.records, isbn13, isbn10)
    return result


def _merge(records: list[BibRecord], isbn13: str, isbn10: str | None) -> BibRecord:
    merged = BibRecord(source="مُجمَّع (" + ", ".join(r.source for r in records) + ")" if records else "لا يوجد",
                        isbn13=isbn13, isbn10=isbn10)

    scalar_fields = ["title", "subtitle", "publisher", "publish_place", "publish_date",
                      "edition", "pages", "language", "dewey", "lcc"]
    for f in scalar_fields:
        for rec in records:
            value = getattr(rec, f)
            if value:
                setattr(merged, f, value)
                break

    seen_authors: set[str] = set()
    for rec in records:
        for a in rec.authors:
            if a not in seen_authors:
                seen_authors.add(a)
                merged.authors.append(a)

    seen_subjects: set[str] = set()
    for rec in records:
        for s in rec.subjects:
            if s not in seen_subjects:
                seen_subjects.add(s)
                merged.subjects.append(s)

    return merged
