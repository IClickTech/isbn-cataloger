"""Shared data model + interface for all cataloging-data sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BibRecord:
    source: str
    isbn10: str | None = None
    isbn13: str | None = None
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    publish_place: str | None = None
    publish_date: str | None = None
    edition: str | None = None
    pages: str | None = None
    language: str | None = None
    subjects: list[str] = field(default_factory=list)
    dewey: str | None = None
    lcc: str | None = None
    note: str | None = None
    raw: dict | None = None


class SourceUnavailable(Exception):
    """Raised when a source cannot be queried (missing credentials, network, etc.)."""


class Source(ABC):
    name: str
    configured: bool = True  # False for sources that need credentials/endpoints not yet set

    @abstractmethod
    def fetch(self, isbn13: str, isbn10: str | None) -> BibRecord | None:
        """Return a BibRecord, or None if the ISBN was not found. May raise SourceUnavailable."""
