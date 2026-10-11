"""Library of Congress source — public SRU endpoint, no credentials needed."""
from __future__ import annotations

from .base import BibRecord, Source
from .sru_helpers import fetch_marcxml_record, marcxml_to_record

ENDPOINT = "http://lx2.loc.gov:210/lcdb"


class LibraryOfCongressSource(Source):
    name = "مكتبة الكونغرس (LOC)"

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        record = fetch_marcxml_record(ENDPOINT, f'bath.isbn="{isbn13}"', "marcxml", self.name)
        if record is None:
            return None
        return marcxml_to_record(record, self.name, isbn13, isbn10, raw={"endpoint": ENDPOINT})
