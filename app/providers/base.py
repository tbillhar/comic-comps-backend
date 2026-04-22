from abc import ABC, abstractmethod

from app.models import CertType, ComicComp


class CompsProvider(ABC):
    @abstractmethod
    def list_comps(self, title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
        """Return comparable sales for diagnostic or browsing endpoints."""

    @abstractmethod
    def search_comps(self, query: str, cert_type: CertType, max_results: int) -> list[ComicComp]:
        """Return provider-normalized comparable sales matching the user's query."""
