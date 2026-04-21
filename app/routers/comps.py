from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from app.models import ComicComp, ComicCompList, ComicCompQuery, ComicCompSearchResponse


router = APIRouter(prefix="/comps", tags=["comps"])


SAMPLE_COMPS = [
    ComicComp(
        id="asm-300-cgc-9-8-2026-01",
        title="Amazing Spider-Man",
        issue_number="300",
        grade="CGC 9.8",
        sale_price=Decimal("7200.00"),
        sale_date=date(2026, 1, 15),
        source="sample",
    ),
    ComicComp(
        id="batman-423-cgc-9-6-2026-02",
        title="Batman",
        issue_number="423",
        grade="CGC 9.6",
        sale_price=Decimal("875.00"),
        sale_date=date(2026, 2, 3),
        source="sample",
    ),
]


@router.get("", response_model=ComicCompList)
def list_comps(
    title: str | None = Query(default=None, description="Optional case-insensitive title filter."),
    issue_number: str | None = Query(default=None, description="Optional exact issue number filter."),
) -> ComicCompList:
    return ComicCompList(comps=_filter_comps(title=title, issue_number=issue_number))


@router.post("", response_model=ComicCompSearchResponse)
def search_comps(query: ComicCompQuery) -> ComicCompSearchResponse:
    comps = _filter_comps(
        title=query.title,
        issue_number=query.issue_number,
        grade=query.grade,
    )[: query.max_results]

    return ComicCompSearchResponse(
        query=query,
        count=len(comps),
        comps=comps,
    )


def _filter_comps(
    title: str | None = None,
    issue_number: str | None = None,
    grade: str | None = None,
) -> list[ComicComp]:
    comps = SAMPLE_COMPS

    if title:
        title_query = title.casefold()
        comps = [comp for comp in comps if title_query in comp.title.casefold()]

    if issue_number:
        comps = [comp for comp in comps if comp.issue_number == issue_number]

    if grade:
        grade_query = grade.casefold()
        comps = [comp for comp in comps if comp.grade.casefold() == grade_query]

    return comps
