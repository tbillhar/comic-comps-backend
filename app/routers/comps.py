from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from app.models import ComicComp, ComicCompList


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
    comps = SAMPLE_COMPS

    if title:
        title_query = title.casefold()
        comps = [comp for comp in comps if title_query in comp.title.casefold()]

    if issue_number:
        comps = [comp for comp in comps if comp.issue_number == issue_number]

    return ComicCompList(comps=comps)
