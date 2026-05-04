from statistics import median

from fastapi import HTTPException

from app.models import (
    ComicComp,
    ComicCompQuery,
    ComicCompSearchDebugResponse,
    ComicCompSearchResponse,
    ComicSeriesRangeQuery,
    ComicSeriesRangeResponse,
    CompSale,
)
from app.providers.base import CompsProvider
from app.providers.factory import get_comps_provider


def list_sample_comps(title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
    return get_comps_provider().list_comps(title=title, issue_number=issue_number)


def search_comps(query: ComicCompQuery, provider: CompsProvider | None = None) -> ComicCompSearchResponse:
    selected_provider = provider or get_comps_provider()
    comps = selected_provider.search_comps(
        query=query.query,
        cert_type=query.cert_type,
        max_results=query.max_results,
    )
    sales = [
        CompSale(
            title=comp.title,
            price=comp.sale_price,
            date=comp.sale_date,
            source=comp.source,
            url=comp.url,
        )
        for comp in comps
    ]

    prices = [sale.price for sale in sales]
    return ComicCompSearchResponse(
        query=query.query,
        cert_type=query.cert_type,
        median=median(prices) if prices else None,
        low=min(prices) if prices else None,
        high=max(prices) if prices else None,
        usable_count=len(sales),
        sales=sales,
    )


def debug_search_comps(
    query: ComicCompQuery,
    provider: CompsProvider | None = None,
) -> ComicCompSearchDebugResponse:
    selected_provider = provider or get_comps_provider()
    try:
        return selected_provider.debug_search(
            query=query.query,
            cert_type=query.cert_type,
            max_results=query.max_results,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "debug_not_supported",
                "message": "Debug search is not implemented for the configured provider.",
            },
        ) from exc


def search_series_range(
    query: ComicSeriesRangeQuery,
    provider: CompsProvider | None = None,
) -> ComicSeriesRangeResponse:
    selected_provider = provider or get_comps_provider()
    try:
        return selected_provider.search_series_range(
            series=query.series,
            series_start_year=query.series_start_year,
            issue_start=query.issue_start,
            issue_end=query.issue_end,
            cert_type=query.cert_type,
            max_results_per_group=query.max_results_per_group,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "range_search_not_supported",
                "message": "Range search is not implemented for the configured provider.",
            },
        ) from exc
