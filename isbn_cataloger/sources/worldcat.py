"""WorldCat / OCLC source.

The public "xISBN"/basic WorldCat lookup API was retired by OCLC. The
replacement is the WorldCat Metadata API, which requires an OCLC institutional
subscription and OAuth client credentials. This source is therefore
credential-gated: if OCLC_CLIENT_ID / OCLC_CLIENT_SECRET are not set, it is
skipped cleanly instead of pretending to return data.
"""
from __future__ import annotations

import os
import time

import requests

from .base import BibRecord, Source, SourceUnavailable

TOKEN_URL = "https://oauth.oclc.org/token"


class WorldCatSource(Source):
    name = "WorldCat"

    def __init__(self) -> None:
        self.client_id = os.environ.get("OCLC_CLIENT_ID")
        self.client_secret = os.environ.get("OCLC_CLIENT_SECRET")
        self.region = os.environ.get("OCLC_API_REGION", "americas")
        self._token: str | None = None
        self._token_expiry = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        try:
            resp = requests.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials", "scope": "WorldCatMetadataAPI"},
                auth=(self.client_id, self.client_secret),
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise SourceUnavailable(f"WorldCat: فشل الحصول على رمز الدخول ({exc})") from exc

        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + int(payload.get("expires_in", 1200)) - 30
        return self._token

    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        if not self.configured:
            raise SourceUnavailable(
                "WorldCat: تخطّي — لم يتم ضبط OCLC_CLIENT_ID / OCLC_CLIENT_SECRET "
                "(يتطلب اشتراك مؤسسي في WorldCat Metadata API)."
            )

        token = self._get_token()
        url = f"https://{self.region}.metadata.api.oclc.org/worldcat/search/brief-bibs"
        try:
            resp = requests.get(
                url,
                params={"q": f"bn:{isbn13}"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise SourceUnavailable(f"WorldCat: تعذر الاتصال ({exc})") from exc

        data = resp.json()
        records = data.get("briefRecords") or []
        if not records:
            return None
        rec = records[0]

        return BibRecord(
            source=self.name,
            isbn10=isbn10,
            isbn13=isbn13,
            title=rec.get("title"),
            authors=[c.get("firstName", {}).get("text", "") + " " + c.get("secondName", {}).get("text", "")
                     for c in rec.get("creator", {}).get("contributors", [])] if rec.get("creator") else [],
            publisher=rec.get("publisher"),
            publish_date=str(rec.get("publicationDate")) if rec.get("publicationDate") else None,
            language=rec.get("language"),
            raw=rec,
        )
