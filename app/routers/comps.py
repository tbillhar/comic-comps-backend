from fastapi import APIRouter, Query

from app.models import ComicCompList, ComicCompQuery, ComicCompSearchResponse
from app.services.comps_service import list_sample_comps, search_comps as search_comps_service


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
