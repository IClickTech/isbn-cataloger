"""Shared request/parsing helpers for SRU/SRW searchRetrieve library sources.

Several national-library catalogs (Library of Congress, DNB, BnF, and any
Arabic catalog pointed at by ARABIC_SRU_ENDPOINT) speak the same SRU protocol
and return MARCXML. This module factors out the one HTTP call + MARCXML
field-extraction logic so each source only has to supply its endpoint and
query string.
"""
from __future__ import annotations

from xml.etree import ElementTree as ET

import requests

from .base import BibRecord, SourceUnavailable

MARCXML_NS = {"m": "http://www.loc.gov/MARC21/slim"}
DIAG_NS = {"diag": "http://www.loc.gov/zing/srw/diagnostic/"}
OAI_DC_NS = {"oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/", "dc": "http://purl.org/dc/elements/1.1/"}


def _run_search_retrieve(
    endpoint: str, query: str, schema: str, source_name: str, version: str,
    extra_params: dict | None = None,
) -> ET.Element:
    """Run an SRU searchRetrieve query and return the parsed response root.

    Raises SourceUnavailable on a transport error or an SRU-level diagnostic
    (e.g. the target service erroring server-side) — distinct from a clean
    "no matching record" response, which callers detect themselves.
    """
    params = {
        "operation": "searchRetrieve",
        "version": version,
        "query": query,
        "recordSchema": schema,
        "maximumRecords": "1",
    }
    if extra_params:
        params.update(extra_params)
    try:
        resp = requests.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SourceUnavailable(f"{source_name}: تعذر الاتصال ({exc})") from exc

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise SourceUnavailable(f"{source_name}: استجابة غير صالحة ({exc})") from exc

    diag = root.find(".//diag:message", DIAG_NS)
    if diag is not None and diag.text:
        raise SourceUnavailable(f"{source_name}: خطأ من الخادم ({diag.text.strip().splitlines()[0]})")

    return root


def fetch_marcxml_record(
    endpoint: str, query: str, schema: str, source_name: str, version: str = "1.1",
    extra_params: dict | None = None,
) -> ET.Element | None:
    """Run an SRU searchRetrieve query and return the first MARCXML <record>, or None if absent."""
    root = _run_search_retrieve(endpoint, query, schema, source_name, version, extra_params)
    return root.find(".//m:record", MARCXML_NS)


def fetch_dc_record(
    endpoint: str, query: str, source_name: str, schema: str = "dublincore", version: str = "1.2",
    extra_params: dict | None = None,
) -> ET.Element | None:
    """Run an SRU searchRetrieve query for a Dublin-Core-family schema and return the
    <recordData> element (schema-agnostic — some catalogs wrap fields in an
    oai_dc:dc element, others put dc: fields directly under recordData; dc_to_record
    searches recursively so either shape works). Some catalogs (e.g. BnF, KB
    Netherlands) don't support MARCXML retrieval at all, only Dublin Core —
    and the exact schema name/value varies (dublincore vs dc)."""
    root = _run_search_retrieve(endpoint, query, schema, source_name, version, extra_params)
    return root.find(".//{http://www.loc.gov/zing/srw/}recordData")


def marcxml_field(record: ET.Element, tag: str, code: str) -> str | None:
    f = record.find(f".//m:datafield[@tag='{tag}']/m:subfield[@code='{code}']", MARCXML_NS)
    return f.text.strip() if f is not None and f.text else None


def marcxml_to_record(
    record: ET.Element, source_name: str, isbn13: str, isbn10: str | None, raw: dict | None = None
) -> BibRecord:
    author = marcxml_field(record, "100", "a")
    return BibRecord(
        source=source_name,
        isbn10=isbn10,
        isbn13=isbn13,
        title=marcxml_field(record, "245", "a"),
        authors=[author] if author else [],
        publisher=marcxml_field(record, "264", "b") or marcxml_field(record, "260", "b"),
        publish_date=marcxml_field(record, "264", "c") or marcxml_field(record, "260", "c"),
        pages=marcxml_field(record, "300", "a"),
        raw=raw,
    )


def _dc_texts(dc_elem: ET.Element, tag: str) -> list[str]:
    ns = OAI_DC_NS["dc"]
    # recursive (.//) so this works whether dc: fields sit directly under
    # recordData (e.g. KB Netherlands) or nested inside an oai_dc:dc wrapper (e.g. BnF)
    return [e.text.strip() for e in dc_elem.findall(f".//{{{ns}}}{tag}") if e.text]


def dc_to_record(
    dc_elem: ET.Element, source_name: str, isbn13: str, isbn10: str | None, raw: dict | None = None
) -> BibRecord:
    titles = _dc_texts(dc_elem, "title")
    return BibRecord(
        source=source_name,
        isbn10=isbn10,
        isbn13=isbn13,
        title=titles[0] if titles else None,
        authors=_dc_texts(dc_elem, "creator"),
        publisher=next(iter(_dc_texts(dc_elem, "publisher")), None),
        publish_date=next(iter(_dc_texts(dc_elem, "date")), None),
        language=next(iter(_dc_texts(dc_elem, "language")), None),
        raw=raw,
    )
