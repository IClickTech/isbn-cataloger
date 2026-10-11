"""Bibliothèque nationale de France (BnF) source — public SRU endpoint, no credentials needed.

BnF's SRU API doesn't support MARCXML retrieval (only UNIMARC/Intermarc and
Dublin Core — confirmed via its explain response), so this uses Dublin Core.
It also requires SRU protocol version 1.2; version 1.1 is rejected outright.
"""
from __future__ import annotations

from .base import BibRecord, Source
from .sru_helpers import dc_to_record, fetch_dc_record

ENDPOINT = "http://catalogue.bnf.fr/api/SRU"


class BnFSource(Source):
    name = "المكتبة الوطنية الفرنسية (BnF)"

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        record = fetch_dc_record(ENDPOINT, f'bib.isbn all "{isbn13}"', self.name, version="1.2")
        if record is None:
            return None
        return dc_to_record(record, self.name, isbn13, isbn10, raw={"endpoint": ENDPOINT})
