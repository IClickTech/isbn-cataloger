"""SQLite persistence layer for the book catalog."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from .aggregator import LookupResult

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "catalog.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    isbn13 TEXT PRIMARY KEY,
    isbn10 TEXT,
    title TEXT,
    subtitle TEXT,
    authors TEXT,
    publisher TEXT,
    publish_place TEXT,
    publish_date TEXT,
    edition TEXT,
    pages TEXT,
    language TEXT,
    subjects TEXT,
    dewey TEXT,
    lcc TEXT,
    note TEXT,
    sources_used TEXT,
    sources_skipped TEXT,
    raw_records TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""


def _db_path() -> str:
    return os.environ.get("ISBN_CATALOGER_DB", DEFAULT_DB_PATH)


def get_connection(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or _db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str | None = None) -> None:
    conn = get_connection(path)
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def upsert_book(result: LookupResult, path: str | None = None) -> tuple[bool, bool]:
    """Save result.merged into the catalog. Returns (saved, is_new).

    Does nothing (saved=False) if no source contributed any data.
    """
    if not result.records:
        return False, False

    merged = result.merged
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection(path)
    try:
        existing = conn.execute(
            "SELECT isbn13 FROM books WHERE isbn13 = ?", (result.isbn13,)
        ).fetchone()
        is_new = existing is None

        conn.execute(
            """
            INSERT INTO books (
                isbn13, isbn10, title, subtitle, authors, publisher, publish_place,
                publish_date, edition, pages, language, subjects, dewey, lcc, note,
                sources_used, sources_skipped, raw_records, created_at, updated_at
            ) VALUES (
                :isbn13, :isbn10, :title, :subtitle, :authors, :publisher, :publish_place,
                :publish_date, :edition, :pages, :language, :subjects, :dewey, :lcc, :note,
                :sources_used, :sources_skipped, :raw_records, :created_at, :updated_at
            )
            ON CONFLICT(isbn13) DO UPDATE SET
                isbn10=excluded.isbn10, title=excluded.title, subtitle=excluded.subtitle,
                authors=excluded.authors, publisher=excluded.publisher,
                publish_place=excluded.publish_place, publish_date=excluded.publish_date,
                edition=excluded.edition, pages=excluded.pages, language=excluded.language,
                subjects=excluded.subjects, dewey=excluded.dewey, lcc=excluded.lcc,
                note=excluded.note, sources_used=excluded.sources_used,
                sources_skipped=excluded.sources_skipped, raw_records=excluded.raw_records,
                updated_at=excluded.updated_at
            """,
            {
                "isbn13": merged.isbn13,
                "isbn10": merged.isbn10,
                "title": merged.title,
                "subtitle": merged.subtitle,
                "authors": json.dumps(merged.authors, ensure_ascii=False),
                "publisher": merged.publisher,
                "publish_place": merged.publish_place,
                "publish_date": merged.publish_date,
                "edition": merged.edition,
                "pages": merged.pages,
                "language": merged.language,
                "subjects": json.dumps(merged.subjects, ensure_ascii=False),
                "dewey": merged.dewey,
                "lcc": merged.lcc,
                "note": merged.note,
                "sources_used": json.dumps([r.source for r in result.records], ensure_ascii=False),
                "sources_skipped": json.dumps(result.skipped, ensure_ascii=False),
                "raw_records": json.dumps([asdict(r) for r in result.records], ensure_ascii=False),
                "created_at": now,
                "updated_at": now,
            },
        )
        conn.commit()
        return True, is_new
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("authors", "subjects", "sources_used", "sources_skipped", "raw_records"):
        if d.get(key):
            d[key] = json.loads(d[key])
    return d


def get_book(isbn13: str, path: str | None = None) -> dict | None:
    conn = get_connection(path)
    try:
        row = conn.execute("SELECT * FROM books WHERE isbn13 = ?", (isbn13,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


SEARCHABLE_COLUMNS = ("title", "subtitle", "authors", "publisher", "subjects", "isbn13", "isbn10", "note")


def _filtered_rows(conn: sqlite3.Connection, columns: str, q: str | None) -> list[sqlite3.Row]:
    sql = f"SELECT {columns} FROM books"
    params: list[str] = []
    if q:
        like = f"%{q}%"
        sql += " WHERE " + " OR ".join(f"{col} LIKE ?" for col in SEARCHABLE_COLUMNS)
        params = [like] * len(SEARCHABLE_COLUMNS)
    sql += " ORDER BY updated_at DESC"
    return conn.execute(sql, params).fetchall()


def list_books(path: str | None = None, q: str | None = None) -> list[dict]:
    """List saved books (summary columns only), optionally filtered by a free-text
    query across the searchable columns (title/authors/publisher/subjects/isbn/note)."""
    conn = get_connection(path)
    try:
        rows = _filtered_rows(conn, "isbn13, isbn10, title, authors, publisher, updated_at", q)
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_books_full(path: str | None = None, q: str | None = None) -> list[dict]:
    """Like list_books but with every stored column — used for export."""
    conn = get_connection(path)
    try:
        rows = _filtered_rows(conn, "*", q)
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def delete_book(isbn13: str, path: str | None = None) -> bool:
    """Remove a book from the catalog. Returns True if a row was actually deleted."""
    conn = get_connection(path)
    try:
        cur = conn.execute("DELETE FROM books WHERE isbn13 = ?", (isbn13,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
