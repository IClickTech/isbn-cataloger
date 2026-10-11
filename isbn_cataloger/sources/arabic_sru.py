"""Generic SRU client for Arabic library catalogs.

No Arabic national library (Dar al-Kutub, King Fahd National Library, the
Arab Union Catalog, ...) exposes a stable public REST API as of writing.
Many of them *do* speak the SRU/SRW protocol, so this source is a generic
SRU client: point it at a real endpoint via ARABIC_SRU_ENDPOINT and it will
run a searchRetrieve query for the ISBN and parse the returned MARCXML.
Without that env var it is skipped rather than inventing an endpoint.
"""
from __future__ import annotations

import os

from .base import BibRecord, Source, SourceUnavailable
from .sru_helpers import fetch_marcxml_record, marcxml_to_record


class ArabicSRUSource(Source):
    name = "فهرس عربي (SRU)"

    def __init__(self) -> None:
        self.endpoint = os.environ.get("ARABIC_SRU_ENDPOINT")
        self.schema = os.environ.get("ARABIC_SRU_SCHEMA", "marcxml")

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        if not self.configured:
            raise SourceUnavailable(
                "فهرس عربي: تخطّي — لم يتم ضبط ARABIC_SRU_ENDPOINT "
                "(لا توجد واجهة REST عامة موثوقة؛ يلزم عنوان خدمة SRU حقيقي)."
            )

        record = fetch_marcxml_record(
            self.endpoint, f'bath.isbn="{isbn13}"', self.schema, self.name
        )
        if record is None:
            return None
        return marcxml_to_record(record, self.name, isbn13, isbn10, raw={"endpoint": self.endpoint})
