from __future__ import annotations

import requests

from .base import BibRecord, Source, SourceUnavailable

BASE_URL = "https://openlibrary.org"


class OpenLibrarySource(Source):
    name = "Open Library"

    def __init__(self) -> None:
        self._author_cache: dict[str, str] = {}

    def _get_json(self, path: str) -> dict | None:
        try:
            resp = requests.get(f"{BASE_URL}{path}", timeout=10)
        except requests.RequestException as exc:
            raise SourceUnavailable(f"Open Library: تعذر الاتصال ({exc})") from exc
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _author_name(self, author_key: str) -> str | None:
        if author_key in self._author_cache:
            return self._author_cache[author_key]
        data = self._get_json(author_key + ".json")
        name = (data or {}).get("name")
        if name:
            self._author_cache[author_key] = name
        return name

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        data = self._get_json(f"/isbn/{isbn13}.json")
        if data is None and isbn10:
            data = self._get_json(f"/isbn/{isbn10}.json")
        if data is None:
            return None

        authors = []
        for a in data.get("authors", []):
            key = a.get("key")
            if key:
                name = self._author_name(key)
                if name:
                    authors.append(name)

        languages = []
        for lang in data.get("languages", []):
            key = lang.get("key", "")
            languages.append(key.rsplit("/", 1)[-1])

        publishers = data.get("publishers", [])
        places = data.get("publish_places", [])

        return BibRecord(
            source=self.name,
            isbn10=isbn10,
            isbn13=isbn13,
            title=data.get("title"),
            subtitle=data.get("subtitle"),
            authors=authors,
            publisher=publishers[0] if publishers else None,
            publish_place=places[0] if places else None,
            publish_date=data.get("publish_date"),
            edition=data.get("edition_name"),
            pages=str(data.get("number_of_pages")) if data.get("number_of_pages") else None,
            language=languages[0] if languages else None,
            subjects=data.get("subjects", []),
            dewey=(data.get("dewey_decimal_class") or [None])[0],
            lcc=(data.get("lc_classifications") or [None])[0],
            raw=data,
        )
