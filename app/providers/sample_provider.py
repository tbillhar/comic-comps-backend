from datetime import date
from decimal import Decimal

from statistics import median

from app.models import (
    CertType,
    ComicComp,
    ComicCompSearchDebugResponse,
    ComicSeriesRangeDebugResponse,
    ComicSeriesRangeResponse,
    CompDebugDecision,
    CompSale,
    IssueConditionCompGroup,
    RangeDebugDecision,
)
from app.providers.base import CompsProvider


SAMPLE_COMPS = [
    ComicComp(
        id="x-men-1-cgc-4-0-2026-04-01",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("6500.00"),
        sale_date=date(2026, 4, 1),
        source="sample",
        url="https://example.com/x-men-1-cgc-4-0-2026-04-01",
    ),
    ComicComp(
        id="x-men-1-cgc-4-0-2026-03-28",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("6800.00"),
        sale_date=date(2026, 3, 28),
        source="sample",
        url="https://example.com/x-men-1-cgc-4-0-2026-03-28",
    ),
    ComicComp(
        id="x-men-1-cgc-4-0-2026-03-18",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("7100.00"),
        sale_date=date(2026, 3, 18),
        source="sample",
        url="https://example.com/x-men-1-cgc-4-0-2026-03-18",
    ),
    ComicComp(
        id="x-men-1-raw-2026-02-10",
        title="X-Men 1 Raw",
        issue_number="1",
        grade="Raw",
        sale_price=Decimal("2200.00"),
        sale_date=date(2026, 2, 10),
        source="sample",
        url="https://example.com/x-men-1-raw-2026-02-10",
    ),
    ComicComp(
        id="asm-300-cgc-9-8-2026-01",
        title="Amazing Spider-Man 300 CGC 9.8",
        issue_number="300",
        grade="CGC 9.8",
        sale_price=Decimal("7200.00"),
        sale_date=date(2026, 1, 15),
        source="sample",
        url="https://example.com/asm-300-cgc-9-8-2026-01",
    ),
    ComicComp(
        id="batman-423-cgc-9-6-2026-02",
        title="Batman 423 CGC 9.6",
        issue_number="423",
        grade="CGC 9.6",
        sale_price=Decimal("875.00"),
        sale_date=date(2026, 2, 3),
        source="sample",
        url="https://example.com/batman-423-cgc-9-6-2026-02",
    ),
]


class SampleCompsProvider(CompsProvider):
    def list_comps(self, title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
        comps = SAMPLE_COMPS

        if title:
            title_query = title.casefold()
            comps = [comp for comp in comps if title_query in comp.title.casefold()]

        if issue_number:
            comps = [comp for comp in comps if comp.issue_number == issue_number]

        return comps

    def search_comps(self, query: str, cert_type: CertType, max_results: int) -> list[ComicComp]:
        query_terms = _search_terms(query, cert_type)
        comps = [
            comp
            for comp in SAMPLE_COMPS
            if _cert_type_matches(comp, cert_type)
            and all(term in comp.title.casefold() for term in query_terms)
        ]

        return sorted(comps, key=lambda comp: comp.sale_date, reverse=True)[:max_results]

    def debug_search(self, query: str, cert_type: CertType, max_results: int) -> ComicCompSearchDebugResponse:
        query_terms = _search_terms(query, cert_type)
        decisions = []

        for comp in SAMPLE_COMPS:
            reasons = []
            if not _cert_type_matches(comp, cert_type):
                reasons.append("cert_type_mismatch")
            if not all(term in comp.title.casefold() for term in query_terms):
                reasons.append("query_terms_missing")

            decisions.append(
                CompDebugDecision(
                    title=comp.title,
                    url=comp.url,
                    included=not reasons,
                    reasons=reasons or ["matched"],
                )
            )

        accepted_count = sum(1 for decision in decisions if decision.included)
        return ComicCompSearchDebugResponse(
            query=query,
            cert_type=cert_type,
            provider="sample",
            attempted_queries=[query],
            fetch_limit=max_results,
            raw_item_count=len(SAMPLE_COMPS),
            accepted_count=accepted_count,
            decisions=decisions,
        )

    def search_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeResponse:
        broad_query = _range_query(series=series, cert_type=cert_type, series_start_year=series_start_year)
        filtered_comps = [
            comp
            for comp in SAMPLE_COMPS
            if _cert_type_matches(comp, cert_type)
            and series.casefold() in comp.title.casefold()
            and comp.issue_number.isdigit()
            and issue_start <= int(comp.issue_number) <= issue_end
        ]

        groups_by_key: dict[tuple[str, str], list[ComicComp]] = {}
        for comp in filtered_comps:
            key = (comp.issue_number, comp.grade)
            groups_by_key.setdefault(key, []).append(comp)

        groups: list[IssueConditionCompGroup] = []
        for issue_number, condition in sorted(groups_by_key.keys(), key=lambda key: (int(key[0]), key[1])):
            comps = sorted(groups_by_key[(issue_number, condition)], key=lambda comp: comp.sale_date, reverse=True)[
                :max_results_per_group
            ]
            sales = [
                CompSale(
                    title=comp.title,
                    price=float(comp.sale_price),
                    date=comp.sale_date,
                    source=comp.source,
                    url=comp.url,
                )
                for comp in comps
            ]
            prices = [sale.price for sale in sales]
            groups.append(
                IssueConditionCompGroup(
                    issue_number=issue_number,
                    condition=condition,
                    median=median(prices) if prices else None,
                    low=min(prices) if prices else None,
                    high=max(prices) if prices else None,
                    usable_count=len(sales),
                    sales=sales,
                )
            )

        return ComicSeriesRangeResponse(
            series=series,
            series_start_year=series_start_year,
            issue_start=issue_start,
            issue_end=issue_end,
            cert_type=cert_type,
            broad_query=broad_query,
            raw_item_count=len(filtered_comps),
            group_count=len(groups),
            groups=groups,
        )

    def debug_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeDebugResponse:
        decisions: list[RangeDebugDecision] = []
        accepted_count = 0
        for comp in SAMPLE_COMPS:
            reasons: list[str] = []
            if not _cert_type_matches(comp, cert_type):
                reasons.append("cert_type_mismatch")
            if series.casefold() not in comp.title.casefold():
                reasons.append("series_phrase_mismatch")
            if not comp.issue_number.isdigit():
                reasons.append("issue_not_parsed")
            elif not issue_start <= int(comp.issue_number) <= issue_end:
                reasons.append(f"issue_out_of_range:{issue_start}-{issue_end}")
            included = not reasons
            if included:
                accepted_count += 1
            decisions.append(
                RangeDebugDecision(
                    title=comp.title,
                    url=comp.url,
                    included=included,
                    reasons=reasons or ["matched"],
                    parsed_issue_number=comp.issue_number or None,
                    parsed_condition=comp.grade or None,
                    parsed_price=float(comp.sale_price),
                )
            )

        return ComicSeriesRangeDebugResponse(
            series=series,
            series_start_year=series_start_year,
            issue_start=issue_start,
            issue_end=issue_end,
            cert_type=cert_type,
            provider="sample",
            broad_query=_range_query(series=series, cert_type=cert_type, series_start_year=series_start_year),
            raw_item_count=len(SAMPLE_COMPS),
            accepted_count=accepted_count,
            decisions=decisions,
        )


def _search_terms(query: str, cert_type: CertType) -> list[str]:
    ignored_terms = {"cgc", "raw"} if cert_type == CertType.CGC else {"raw"}
    return [
        term
        for term in query.casefold().replace("-", " ").split()
        if term not in ignored_terms
    ]


def _cert_type_matches(comp: ComicComp, cert_type: CertType) -> bool:
    if cert_type == CertType.CGC:
        return comp.grade.casefold().startswith("cgc")

    return comp.grade.casefold() == "raw"


def _range_query(series: str, cert_type: CertType, series_start_year: int | None = None) -> str:
    suffix = "CGC" if cert_type == CertType.CGC else "Raw"
    if series_start_year is not None:
        return f"{series} {series_start_year} {suffix}"
    return f"{series} {suffix}"
