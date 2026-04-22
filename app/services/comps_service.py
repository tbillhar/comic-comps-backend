from datetime import date
from decimal import Decimal
from statistics import median

from app.models import CertType, ComicComp, ComicCompQuery, ComicCompSearchResponse, CompSale


SAMPLE_COMPS = [
    ComicComp(
        id="x-men-1-cgc-4-0-2026-04-01",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("6500.00"),
        sale_date=date(2026, 4, 1),
        source="sample",
    ),
    ComicComp(
        id="x-men-1-cgc-4-0-2026-03-28",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("6800.00"),
        sale_date=date(2026, 3, 28),
        source="sample",
    ),
    ComicComp(
        id="x-men-1-cgc-4-0-2026-03-18",
        title="X-Men 1 CGC 4.0",
        issue_number="1",
        grade="CGC 4.0",
        sale_price=Decimal("7100.00"),
        sale_date=date(2026, 3, 18),
        source="sample",
    ),
    ComicComp(
        id="x-men-1-raw-2026-02-10",
        title="X-Men 1 Raw",
        issue_number="1",
        grade="Raw",
        sale_price=Decimal("2200.00"),
        sale_date=date(2026, 2, 10),
        source="sample",
    ),
    ComicComp(
        id="asm-300-cgc-9-8-2026-01",
        title="Amazing Spider-Man 300 CGC 9.8",
        issue_number="300",
        grade="CGC 9.8",
        sale_price=Decimal("7200.00"),
        sale_date=date(2026, 1, 15),
        source="sample",
    ),
    ComicComp(
        id="batman-423-cgc-9-6-2026-02",
        title="Batman 423 CGC 9.6",
        issue_number="423",
        grade="CGC 9.6",
        sale_price=Decimal("875.00"),
        sale_date=date(2026, 2, 3),
        source="sample",
    ),
]


def list_sample_comps(title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
    comps = SAMPLE_COMPS

    if title:
        title_query = title.casefold()
        comps = [comp for comp in comps if title_query in comp.title.casefold()]

    if issue_number:
        comps = [comp for comp in comps if comp.issue_number == issue_number]

    return comps


def search_comps(query: ComicCompQuery) -> ComicCompSearchResponse:
    comps = _match_comps(query.query, query.cert_type)[: query.max_results]
    sales = [
        CompSale(
            title=comp.title,
            price=comp.sale_price,
            date=comp.sale_date,
            source=comp.source,
        )
        for comp in comps
    ]

    prices = [sale.price for sale in sales]
    return ComicCompSearchResponse(
        query=query.query,
        cert_type=query.cert_type,
        median=Decimal(str(median(prices))) if prices else None,
        low=min(prices) if prices else None,
        high=max(prices) if prices else None,
        usable_count=len(sales),
        sales=sales,
    )


def _match_comps(query: str, cert_type: CertType) -> list[ComicComp]:
    query_terms = _search_terms(query, cert_type)
    comps = [
        comp
        for comp in SAMPLE_COMPS
        if _cert_type_matches(comp, cert_type)
        and all(term in comp.title.casefold() for term in query_terms)
    ]

    return sorted(comps, key=lambda comp: comp.sale_date, reverse=True)


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
