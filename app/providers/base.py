from abc import ABC, abstractmethod

from app.models import (
    CertType,
    ComicComp,
    ComicCompSearchDebugResponse,
    ComicSeriesRangeDebugResponse,
    ComicSeriesRangeResponse,
)


class CompsProvider(ABC):
    @abstractmethod
    def list_comps(self, title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
        """Return comparable sales for diagnostic or browsing endpoints."""

    @abstractmethod
    def search_comps(self, query: str, cert_type: CertType, max_results: int) -> list[ComicComp]:
        """Return provider-normalized comparable sales matching the user's query."""

    def search_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeResponse:
        raise NotImplementedError("Range search is not implemented for this provider.")

    def debug_search(self, query: str, cert_type: CertType, max_results: int) -> ComicCompSearchDebugResponse:
        raise NotImplementedError("Debug search is not implemented for this provider.")

    def debug_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeDebugResponse:
        raise NotImplementedError("Range debug search is not implemented for this provider.")
