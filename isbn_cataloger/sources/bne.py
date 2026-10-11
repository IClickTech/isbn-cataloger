"""Biblioteca Nacional de España (BNE) source — public SRU endpoint, no credentials needed."""
from __future__ import annotations

from .base import BibRecord, Source
from .sru_helpers import fetch_marcxml_record, marcxml_to_record

ENDPOINT = "https://catalogo.bne.es/view/sru/34BNE_INST"


class BNESource(Source):
    name = "المكتبة الوطنية الإسبانية (BNE)"

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        record = fetch_marcxml_record(ENDPOINT, f'alma.isbn="{isbn13}"', "marcxml", self.name, version="1.2")
        if record is None:
            return None
        return marcxml_to_record(record, self.name, isbn13, isbn10, raw={"endpoint": ENDPOINT})
