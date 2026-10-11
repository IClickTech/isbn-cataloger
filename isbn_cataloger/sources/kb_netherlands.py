"""Koninklijke Bibliotheek (KB, Dutch National Library) source — public SRU endpoint, no credentials.

The general book catalog (GGC) requires the x-collection=GGC extension param —
without it the default search profile ("ANP") won't be searched. Returns
Dublin Core with dc: fields directly under <recordData> (no oai_dc:dc wrapper,
unlike BnF) — dc_to_record's recursive field lookup handles both shapes.
"""
from __future__ import annotations

from .base import BibRecord, Source
from .sru_helpers import dc_to_record, fetch_dc_record

ENDPOINT = "https://jsru.kb.nl/sru/sru"


class KBNetherlandsSource(Source):
    name = "المكتبة الملكية الهولندية (KB)"

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        record = fetch_dc_record(
            ENDPOINT, f'dc.identifier="{isbn13}"', self.name,
            schema="dc", version="1.2", extra_params={"x-collection": "GGC"},
        )
        if record is None:
            return None
        return dc_to_record(record, self.name, isbn13, isbn10, raw={"endpoint": ENDPOINT})
