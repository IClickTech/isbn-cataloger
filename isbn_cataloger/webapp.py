"""Flask web app: enter an ISBN, run a full cataloging lookup, save to the catalog DB."""
from __future__ import annotations

import csv
import io
import os
from dataclasses import asdict

from flask import Flask, jsonify, request

from . import aggregator, db, isbn_utils, marc
from .aggregator import LookupResult
from .sources.base import BibRecord

MANUAL_SOURCE = "إدخال يدوي"


def _clean_str(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _clean_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
    db.init_db()

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/sources")
    def api_sources():
        return jsonify(aggregator.sources_info())

    @app.post("/api/lookup")
    def api_lookup():
        """Run the full multi-source lookup only — does not touch the catalog DB."""
        payload = request.get_json(silent=True) or {}
        raw_isbn = str(payload.get("isbn", ""))
        selected_names = payload.get("sources")

        try:
            normalized = isbn_utils.normalize(raw_isbn)
        except isbn_utils.InvalidISBNError as exc:
            return jsonify({"error": str(exc)}), 400

        sources = aggregator.sources_by_names(selected_names) if selected_names is not None else None
        result = aggregator.lookup(normalized.isbn13, normalized.isbn10, sources=sources)

        return jsonify({
            "isbn13": result.isbn13,
            "isbn10": result.isbn10,
            "merged": asdict(result.merged),
            "sources_used": [asdict(r) for r in result.records],
            "sources_skipped": [{"source": n, "reason": r} for n, r in result.skipped],
            "marc_text": marc.to_text(result.merged) if result.records else None,
        })

    @app.post("/api/books")
    def api_save_book():
        """Save a book to the catalog: re-runs the full lookup server-side (so the
        complete per-source detail is what gets persisted, not just what the client saw)
        and upserts it by ISBN-13."""
        payload = request.get_json(silent=True) or {}
        raw_isbn = str(payload.get("isbn", ""))
        selected_names = payload.get("sources")

        try:
            normalized = isbn_utils.normalize(raw_isbn)
        except isbn_utils.InvalidISBNError as exc:
            return jsonify({"error": str(exc)}), 400

        sources = aggregator.sources_by_names(selected_names) if selected_names is not None else None
        result = aggregator.lookup(normalized.isbn13, normalized.isbn10, sources=sources)
        saved, is_new = db.upsert_book(result)

        return jsonify({
            "isbn13": result.isbn13,
            "isbn10": result.isbn10,
            "merged": asdict(result.merged),
            "sources_used": [asdict(r) for r in result.records],
            "sources_skipped": [{"source": n, "reason": r} for n, r in result.skipped],
            "marc_text": marc.to_text(result.merged) if result.records else None,
            "saved": saved,
            "is_new": is_new,
        })

    @app.post("/api/books/manual")
    def api_save_manual_book():
        """Save a book using manually-entered bibliographic data — for when no
        source has it (common for locally-published Arabic titles). Skips the
        lookup step entirely and persists exactly what the user typed."""
        payload = request.get_json(silent=True) or {}
        raw_isbn = str(payload.get("isbn", ""))

        try:
            normalized = isbn_utils.normalize(raw_isbn)
        except isbn_utils.InvalidISBNError as exc:
            return jsonify({"error": str(exc)}), 400

        title = _clean_str(payload.get("title"))
        if not title:
            return jsonify({"error": "العنوان مطلوب"}), 400

        record = BibRecord(
            source=MANUAL_SOURCE,
            isbn10=normalized.isbn10,
            isbn13=normalized.isbn13,
            title=title,
            subtitle=_clean_str(payload.get("subtitle")),
            authors=_clean_list(payload.get("authors")),
            publisher=_clean_str(payload.get("publisher")),
            publish_place=_clean_str(payload.get("publish_place")),
            publish_date=_clean_str(payload.get("publish_date")),
            edition=_clean_str(payload.get("edition")),
            pages=_clean_str(payload.get("pages")),
            language=_clean_str(payload.get("language")),
            subjects=_clean_list(payload.get("subjects")),
            dewey=_clean_str(payload.get("dewey")),
            lcc=_clean_str(payload.get("lcc")),
            note=_clean_str(payload.get("note")),
        )
        result = LookupResult(
            isbn13=normalized.isbn13, isbn10=normalized.isbn10,
            records=[record], skipped=[], merged=record,
        )
        saved, is_new = db.upsert_book(result)

        return jsonify({
            "isbn13": result.isbn13,
            "isbn10": result.isbn10,
            "merged": asdict(result.merged),
            "sources_used": [asdict(r) for r in result.records],
            "sources_skipped": [],
            "marc_text": marc.to_text(result.merged),
            "saved": saved,
            "is_new": is_new,
        })

    @app.get("/api/books")
    def api_list_books():
        q = request.args.get("q")
        return jsonify(db.list_books(q=q))

    EXPORT_COLUMNS = [
        "isbn13", "isbn10", "title", "subtitle", "authors", "publisher",
        "publish_place", "publish_date", "edition", "pages", "language",
        "subjects", "dewey", "lcc", "note", "sources_used", "created_at", "updated_at",
    ]

    @app.get("/api/export")
    def api_export():
        q = request.args.get("q")
        fmt = request.args.get("format", "json")
        books = db.list_books_full(q=q)

        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for b in books:
                row = dict(b)
                row["authors"] = "، ".join(b.get("authors") or [])
                row["subjects"] = "، ".join(b.get("subjects") or [])
                row["sources_used"] = "، ".join(b.get("sources_used") or [])
                writer.writerow(row)
            # Leading BOM so Excel renders the Arabic text correctly.
            return ("﻿" + buf.getvalue()), 200, {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": "attachment; filename=catalog_export.csv",
            }

        return jsonify(books), 200, {
            "Content-Disposition": "attachment; filename=catalog_export.json",
        }

    @app.delete("/api/books/<isbn13>")
    def api_delete_book(isbn13: str):
        deleted = db.delete_book(isbn13)
        if not deleted:
            return jsonify({"error": "لم يُعثر على كتاب بهذا الرقم في الفهرس"}), 404
        return jsonify({"deleted": True})

    @app.get("/api/books/<isbn13>")
    def api_get_book(isbn13: str):
        book = db.get_book(isbn13)
        if book is None:
            return jsonify({"error": "لم يُعثر على كتاب بهذا الرقم في الفهرس"}), 404
        return jsonify(book)

    @app.get("/api/books/<isbn13>/marc")
    def api_get_book_marc(isbn13: str):
        book = db.get_book(isbn13)
        if book is None:
            return jsonify({"error": "لم يُعثر على كتاب بهذا الرقم في الفهرس"}), 404
        record = BibRecord(
            source="catalog",
            isbn10=book.get("isbn10"),
            isbn13=book.get("isbn13"),
            title=book.get("title"),
            subtitle=book.get("subtitle"),
            authors=book.get("authors") or [],
            publisher=book.get("publisher"),
            publish_place=book.get("publish_place"),
            publish_date=book.get("publish_date"),
            edition=book.get("edition"),
            pages=book.get("pages"),
            language=book.get("language"),
            subjects=book.get("subjects") or [],
            dewey=book.get("dewey"),
            lcc=book.get("lcc"),
            note=book.get("note"),
        )
        return marc.to_text(record), 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
