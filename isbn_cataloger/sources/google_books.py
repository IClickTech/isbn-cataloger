from __future__ import annotations

import requests

from .base import BibRecord, Source, SourceUnavailable

API_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksSource(Source):
    name = "Google Books"

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        try:
            resp = requests.get(API_URL, params={"q": f"isbn:{isbn13}"}, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise SourceUnavailable(f"Google Books: تعذر الاتصال ({exc})") from exc

        data = resp.json()
        items = data.get("items") or []
        if not items:
            return None

        info = items[0].get("volumeInfo", {})
        identifiers = {
            i.get("type"): i.get("identifier") for i in info.get("industryIdentifiers", [])
        }

        return BibRecord(
            source=self.name,
            isbn10=identifiers.get("ISBN_10", isbn10),
            isbn13=identifiers.get("ISBN_13", isbn13),
            title=info.get("title"),
            subtitle=info.get("subtitle"),
            authors=info.get("authors", []),
            publisher=info.get("publisher"),
            publish_date=info.get("publishedDate"),
            pages=str(info.get("pageCount")) if info.get("pageCount") else None,
            language=info.get("language"),
            subjects=info.get("categories", []),
            raw=info,
        )
