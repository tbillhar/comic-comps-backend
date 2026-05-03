from fastapi import APIRouter, Query

from app.models import (
    ComicCompList,
    ComicCompQuery,
    ComicCompSearchDebugResponse,
    ComicCompSearchResponse,
    ComicSeriesRangeQuery,
    ComicSeriesRangeResponse,
)
from app.services.comps_service import (
    debug_search_comps as debug_search_comps_service,
    list_sample_comps,
    search_series_range as search_series_range_service,
    search_comps as search_comps_service,
)


router = APIRouter(prefix="/comps", tags=["comps"])


@router.get("", response_model=ComicCompList)
def list_comps(
    title: str | None = Query(default=None, description="Optional case-insensitive title filter."),
    issue_number: str | None = Query(default=None, description="Optional exact issue number filter."),
) -> ComicCompList:
    return ComicCompList(comps=list_sample_comps(title=title, issue_number=issue_number))


@router.post("", response_model=ComicCompSearchResponse)
def search_comps(query: ComicCompQuery) -> ComicCompSearchResponse:
    return search_comps_service(query)


@router.post("/debug", response_model=ComicCompSearchDebugResponse)
def debug_search_comps(query: ComicCompQuery) -> ComicCompSearchDebugResponse:
    return debug_search_comps_service(query)


@router.post("/range", response_model=ComicSeriesRangeResponse)
def search_series_range(query: ComicSeriesRangeQuery) -> ComicSeriesRangeResponse:
    return search_series_range_service(query)
